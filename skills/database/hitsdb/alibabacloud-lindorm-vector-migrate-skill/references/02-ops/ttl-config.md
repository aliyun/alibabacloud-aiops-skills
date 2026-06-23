# Lindorm Row-Level TTL Configuration

## Overview

Lindorm search engine supports **row-level TTL**: each row carries an independent expiration timestamp and is automatically deleted after the expiration time.

> **Kernel version requirement**: `lindorm-lvector >= 1.3.3-20250519`, `lindorm-lsearch >= 1.3.3-20250519`

## TTL Field Data Format

**The TTL field stores an expiration timestamp (absolute time), not a time-to-live duration.**

| Correct | Incorrect |
|---------|-----------|
| `expire_time = 1718000000` (this row expires at 2024-06-10 12:00:00 UTC) | `expire_time = 3600` (expires after 3600 seconds ❌) |

- `doc_ttl.unit = "s"`: field value is a **second-level** epoch timestamp (e.g. `1718000000`)
- `doc_ttl.unit = "ms"`: field value is a **millisecond-level** epoch timestamp (e.g. `1718000000000`)

## DDL Configuration

Add `doc_ttl.field` and `doc_ttl.unit` to index settings:

```json
{
  "settings": {
    "index": {
      "knn": true,
      "doc_ttl.field": "expire_time",
      "doc_ttl.unit": "s"
    }
  },
  "mappings": {
    "_source": {"excludes": ["embedding"]},
    "properties": {
      "embedding": { "...knn_vector definition..." },
      "expire_time": {"type": "long"},
      "title": {"type": "keyword"}
    }
  }
}
```

**Key points**:
- The field specified by `doc_ttl.field` must be declared as `long` type in mappings
- `doc_ttl.unit` only supports `s` (seconds) and `ms` (milliseconds)

## Source TTL → Lindorm Row-Level TTL Conversion

### Lindorm Source (Direct Pass-Through)

When the source already has row-level TTL, settings and data are copied as-is; no additional calculation needed.

```bash
# Pre-check: read source TTL configuration
curl -s -u <user>:<pass> "http://<source_host>:30070/<index>/_settings" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); idx=list(d.values())[0]; print(idx.get('settings',{}).get('index',{}).get('doc_ttl.field','')); print(idx.get('settings',{}).get('index',{}).get('doc_ttl.unit',''))"
```

The migration script does not need to inject fields; the source `scan()` returns data already containing the expiration timestamp.

### Milvus Source (Script Calculation Injection)

Milvus's `collection.ttl.seconds = N` is a collection-level uniform expiration. Conversion: inject an expiration timestamp for each row during migration. The time unit (`s` or `ms`) is determined by the user's selection in Step 2; the script MUST use the corresponding unit's calculation formula.

```python
# Pre-check: read collection TTL (properties may be None/empty dict/empty list)
stats = client.describe_collection(collection_name="<collection>")
_props = stats.get("properties")
ttl_seconds = int(_props.get("collection.ttl.seconds", 0)) if isinstance(_props, dict) else 0

# Migration script injection (second-level doc_ttl.unit = "s")
import time
TTL_FIELD = "expire_time"

def inject_ttl(batch):
    expire_ts = int(time.time()) + ttl_seconds
    for row in batch:
        row[TTL_FIELD] = expire_ts
    return batch
```

> **Millisecond-level (doc_ttl.unit = "ms")**: `expire_ts = int(time.time() * 1000) + ttl_seconds * 1000`. The injection unit MUST strictly match the DDL's `doc_ttl.unit`; otherwise data will **expire immediately**.

### Elasticsearch Source (ILM Conversion)

The ES ILM policy delete phase `min_age` represents how long after index creation it is deleted. Conversion: calculate `expire_time = document_timestamp + min_age` for each row.

#### Pre-check: Read ILM Policy

```python
import re

def parse_es_duration(duration_str):
    """Parse ES time unit string into seconds. Supports d(days), h(hours), m(minutes), s(seconds)."""
    if not duration_str:
        return 0
    total = 0
    for match in re.finditer(r'(\d+)([dhms])', str(duration_str)):
        value, unit = int(match.group(1)), match.group(2)
        if unit == 'd':
            total += value * 86400
        elif unit == 'h':
            total += value * 3600
        elif unit == 'm':
            total += value * 60
        elif unit == 's':
            total += value
    return total

# Read ILM policy name
settings = es_client.indices.get_settings(index="<index_name>")
ilm_policy = list(settings.values())[0]["settings"]["index"].get("lifecycle", {}).get("name", "")

# Read policy details
min_age_seconds = 0
if ilm_policy:
    try:
        policy = es_client.ilm.get_lifecycle(policy=ilm_policy)
        delete_phase = policy[ilm_policy]["policy"]["phases"].get("delete", {})
        min_age = delete_phase.get("min_age", "")
        min_age_seconds = parse_es_duration(min_age)
    except Exception as e:
        # Policy may have been deleted or access denied; treat as no TTL detected
        print(f"[WARN] ILM policy '{ilm_policy}' read failed (may have been deleted): {e}, skipping TTL detection")
        ilm_policy = ""
```

#### Migration Script: Inject Expiration Timestamp

```python
from datetime import datetime, timezone

TTL_FIELD = "expire_time"
TIMESTAMP_FIELD = "created_at"  # User-selected or Agent-identified from mapping
MIN_AGE_SECONDS = min_age_seconds  # Value obtained during pre-check

def to_epoch_seconds(value):
    """Convert various time formats to epoch seconds. MUST use timezone-aware parsing to avoid local timezone drift."""
    import time
    if isinstance(value, (int, float)):
        # Already a timestamp
        if value > 1e12:  # Millisecond-level
            return int(value / 1000)
        return int(value)
    if isinstance(value, str):
        # ISO 8601: replace Z → +00:00 then parse with fromisoformat (Python 3.7+), enforce timezone
        try:
            normalized = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)  # Default to UTC when no timezone info
            return int(dt.timestamp())
        except (ValueError, AttributeError):
            pass
    return int(time.time())  # Fallback: use current time (WARNING: timestamp format could not be parsed, TTL value may be inaccurate)

def inject_ttl(batch):
    import time
    for row in batch:
        row_ts = row.get(TIMESTAMP_FIELD)
        row[TTL_FIELD] = (to_epoch_seconds(row_ts) if row_ts else int(time.time())) + MIN_AGE_SECONDS
    return batch
```

> **Millisecond unit (doc_ttl.unit = "ms")**: `to_epoch_seconds` return value × 1000, `MIN_AGE_SECONDS` also × 1000. Ensure the injected value unit matches the DDL's `doc_ttl.unit`.

### Qdrant / Manual Configuration

When the source has no TTL mechanism, if the user manually configures row-level TTL, they must ensure the source data already contains the TTL field (with absolute timestamp values). The migration script does not need to inject; just pass through directly.

## Difference from Partition-Level TTL

| Feature | Row-level TTL (currently supported) | Partition-level TTL (not yet supported) |
|---------|-------------------------------------|----------------------------------------|
| Granularity | Each row expires independently | Entire time partition expires as a whole |
| Configuration | `doc_ttl.field` + `doc_ttl.unit` | `time_partition` + `partition.ttl` |
| Index type | Regular index | data_stream + index_template |
| Data requirement | Each row contains expiration timestamp field | Contains time partition field |
| Use case | General purpose | Logs, time-series, and other time-generated data |

> For partition-level TTL, refer to `https://help.aliyun.com/zh/lindorm/user-guide/time-partition-api-usage`

## TTL Decision Matrix

| User selection | DDL `settings.index` | DDL mappings | Script injection |
|---------------|---------------------|-------------|-----------------|
| **Accept recommendation** | Add `doc_ttl.field` + `doc_ttl.unit` | Auto-add TTL field (`long`); if source already has it, map normally | Inject per source type (Milvus: `time+N`, ES: `ts+min_age`, Lindorm: no injection) |
| **Custom** | Add user-specified `doc_ttl.field` + `doc_ttl.unit` | Add field with user-specified name (`long`) | Same as accept, but use user-specified field name and unit |
| **Do not configure TTL** | Do not add `doc_ttl` | Do not add TTL field | No injection |

> When customizing, if the user changes `doc_ttl.unit` (e.g. `s` → `ms`), the script injection formula MUST synchronize the unit change (`time.time()*1000 + N*1000`).
