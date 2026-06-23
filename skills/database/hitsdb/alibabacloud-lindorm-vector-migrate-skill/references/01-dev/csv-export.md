# CSV Data Export Interface

## Positioning and Architecture

CSV export adds a **new write endpoint** on top of the existing read-write decoupled architecture. The read side reuses existing source scanning; the write side adds a CSV writer to replace the Lindorm bulk writer. **Data is exported as-is**: no type mapping, TTL injection, or DDL generation.

```
Source scan (reused)         Write endpoint (choose one)
├─ Milvus ────────┬─ Lindorm _bulk writer (existing)
├─ ES ────────────┤
├─ Lindorm ───────┤
├─ Qdrant ────────┘─ CSV writer (new)
```

---

## Export CSV Format

Follows the format specification in `references/03-ref/csv-format.md` (typed header, type identifiers, vector JSON serialization, `parse_header` / `parse_vector`).

---

## Typed Header Serialization

All sources share the same set of CSV type identifiers. The writer serializes each field as `column_name:type` based on the source schema.

### Common Type Mapping

| Source type | CSV type | Notes |
|-------------|----------|-------|
| INT64 / long | `long` | |
| INT32 / INT16 / INT8 / integer / short / byte | `integer` | |
| FLOAT / float | `float` | |
| DOUBLE / double | `double` | |
| BOOL / boolean | `boolean` | |
| VARCHAR / keyword | `keyword` | |
| text | `text` | |
| date / datetime | `date` | |
| JSON / ARRAY / object | `keyword` | Serialized as JSON string (`json.dumps()`) |
| FLOAT_VECTOR / dense_vector / knn_vector | `knn_vector:{dim}:{metric}` | See distance metric below |

### Distance Metric Mapping

| Source value | CSV distance metric |
|-------------|-------------------|
| COSINE / cosine / cosinesimil | `cosine` |
| L2 / l2_norm / l2 / Euclid | `l2` |
| IP / dot_product / innerproduct / Dot | `innerproduct` |

### Source-Specific Differences

| Source | Vector field origin | Special handling |
|--------|-------------------|-----------------|
| Milvus | `describe_collection` fields | Dynamic fields inferred via sampling: `bool→boolean`, `int→long`, `float→double`, `str→keyword` |
| Elasticsearch | mapping `dense_vector` | `_id` injected as `id:keyword` (if source already has an `id` field, use `_doc_id:keyword` instead and WARN); `nested` skipped |
| Lindorm | mapping `knn_vector` | Dimension key is `dimension`, metric in `method.space_type`; `_id` injected as `id:keyword` (if source already has an `id` field, use `_doc_id:keyword` instead and WARN) |
| Qdrant | collection config `vectors` | Vector not in payload; must inject from `point.vector`; `payload_schema` may be incomplete; multi-vector mode (Named Vectors): each named vector exported as an independent `knn_vector` column |

> **_id injection conflict handling**: ES/Lindorm source `_id` metadata needs to be injected as a CSV column to restore the document `_id` during import. Before injection, check if the source mapping already has a field named `id`:
> - Does not exist → inject as `id:keyword`
> - Already exists → use `_doc_id:keyword` instead, and output `[WARN] Source already has id field, _id injected as _doc_id to avoid conflict` to stdout
>
> During import (csv-import.md), the `_doc_id` column must be recognized and used as the Lindorm document `_id`.

---

## CSV Writer Template

Single-threaded, consumes `list[dict]` batch data, writes to a local CSV file.

```python
import csv, json, os, sys, signal

# ==================== Parameters ====================
OUTPUT_FILE = "export_output.csv"
BATCH_SIZE = 1000
EXCLUDE_FIELDS = set()
RESUME_CURSOR = None
RESUME_MIGRATED = 0

HEADER_FIELDS = ["id:long", "title:text", "embedding:knn_vector:128:cosine"]  # Agent generates based on schema
HEADER_NAMES = [h.split(":")[0] for h in HEADER_FIELDS if h.split(":")[0] not in EXCLUDE_FIELDS]
VECTOR_FIELDS = {h.split(":")[0] for h in HEADER_FIELDS if "knn_vector" in h and h.split(":")[0] not in EXCLUDE_FIELDS}

# ==================== Logging + Signal ====================
# TeeWriter initialization (follows checkpoint-resume.md output protocol)
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkpoint.log")

class TeeWriter:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            try: s.write(data); s.flush()
            except ValueError: pass
    def flush(self):
        for s in self.streams:
            try: s.flush()
            except ValueError: pass

_log_file = open(LOG_FILE, "w")
sys.stdout = TeeWriter(sys.__stdout__, _log_file)

cursor = RESUME_CURSOR
migrated = RESUME_MIGRATED
total = 0  # Agent fills in

def signal_handler(sig, frame):
    print(f"[INTERRUPTED] cursor={cursor} migrated={migrated} total={total}")
    _log_file.close(); sys.exit(1)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# ==================== Main Loop ====================
write_mode = "a" if RESUME_CURSOR is not None else "w"
f = open(OUTPUT_FILE, write_mode, newline="", encoding="utf-8")
writer = csv.writer(f)

if write_mode == "w":
    clean_header = [h for h in HEADER_FIELDS if h.split(":")[0] not in EXCLUDE_FIELDS]
    writer.writerow(clean_header)

for batch in source_scan(resume_cursor=RESUME_CURSOR, batch_size=BATCH_SIZE):
    for row in batch:
        csv_row = []
        for name in HEADER_NAMES:
            if name in EXCLUDE_FIELDS: continue
            val = row.get(name, "")
            if name in VECTOR_FIELDS and isinstance(val, list):
                val = json.dumps(val)
            csv_row.append(val)
        writer.writerow(csv_row)
    migrated += len(batch)
    cursor = batch[-1].get("_cursor")  # Agent MUST inject _cursor field into each doc when generating source_scan: Milvus=primary key value, ES=hit["_id"], Lindorm=hit["_id"], Qdrant=point["id"]
    pct = (migrated / total * 100) if total else 0
    print(f"[PROGRESS] cursor={cursor} migrated={migrated} total={total} pct={pct:.1f}%")

f.close()
print(f"[DONE] migrated={migrated}")
_log_file.close()
```

`source_scan()` is replaced with the specific source scanning code, reusing `<source>-migrate.md`:
- Milvus → `milvus-migrate.md` (query_iterator)
- ES → `elasticsearch-migrate.md` (PIT + search_after / Scroll)
- Lindorm → `lindorm-migrate.md` (Scroll API)
- Qdrant → `qdrant-migrate.md` (REST scroll)

> **Credential security**: Source credentials in export scripts MUST be read from environment variables (see credential security rules in `workflow.md`); MUST NOT be written in plaintext into the script parameter section.

---

## Checkpoint Resume

> **MUST rule**: All export scripts (regardless of data volume) MUST use TeeWriter to write output to both stdout and a log file simultaneously, and MUST include `[PROGRESS]`/`[INTERRUPTED]`/`[DONE]` structured output. Even if the export data volume is only a few hundred records, checkpoint resume support MUST NOT be omitted. This is a mandatory Skill specification.

Reuses the mechanism from `checkpoint-resume.md`. Log file name is determined by the Agent; output protocol and cursor types for each source are detailed in `references/02-ops/checkpoint-resume.md`.

Resume: fill in `RESUME_CURSOR` / `RESUME_MIGRATED`; open CSV in append mode.

---

## Export Pre-checks

1. **Connection validation**: Reuses each source's connection logic
2. **Exclude fields**: AskUserQuestion (multiSelect) displays all fields for user selection
3. **Disk estimation**: Sample 100 records with excluded fields removed, calculate average row size × total rows, compare against `shutil.disk_usage`. WARN + AskUserQuestion if exceeding 80%
4. **Schema display**: Qdrant `payload_schema` may be incomplete; sample first batch to supplement

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Source connection failure | Display error; do not retry |
| Scan/write interruption | Output `[INTERRUPTED]` then exit |
| 429 rate limiting | Exponential backoff (0.5s→1s→2s→4s), max 5 retries |
| None values | Write as empty string |

---

## Post-Export Steps

1. Inform user of CSV file path and size
2. Prompt to upload via Alibaba Cloud OSS console
3. AskUserQuestion to wait for confirmation
4. Collect OSS parameters (original data source auto-inherited), enter CSV import flow

---

## Dependencies

No new dependencies. Each source reuses existing SDKs (`pymilvus==3.0.0` / `elasticsearch==7.17.13` / `qdrant-client==1.18.0`) + standard library `csv` / `json` / `signal`.
