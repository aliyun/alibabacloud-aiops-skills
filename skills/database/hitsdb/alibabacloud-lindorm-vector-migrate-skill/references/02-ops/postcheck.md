# Post-Migration Validation

## Overview

Executed after migration completes to verify data consistency. Includes row count validation, random sampling, and index build status check. When row-level TTL is configured, additional TTL-specific validations are performed (settings consistency, field value reasonableness, source-to-target consistency).

## Refresh Index

Written data may still be in the refresh interval and not yet visible; force refresh first:

```bash
curl -s -u <username>:<password> -X POST "http://<host>:30070/<index_name>/_refresh"
```

## Row Count Validation

```bash
curl -s -u <username>:<password> "http://<host>:30070/<index_name>/_count" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}}'
```

Response: `{"count": 100000, ...}`

Compare `count` against source `total_count`.

## Random Sampling

### Sample Size

Sample size is dynamically determined based on total data volume, balancing validation coverage and execution time:

| Total data volume | Sample size | Description |
|-------------------|-------------|-------------|
| ≤ 100 | All | Small volume; compare every record |
| 101 ~ 10,000 | 20% and ≥ 50 records | Small dataset by proportion |
| 10,001 ~ 1,000,000 | 1% and ≥ 200 records | Medium dataset; 200 records provide sufficient coverage |
| > 1,000,000 | 200 ~ 500 records | Large dataset; sampling capped |

The Agent automatically determines sample size based on the `_count` result.

### Query Method

Use `function_score` + `random_score` to randomly sample from the target, then compare against source data:

```bash
curl -s -u <username>:<password> "http://<host>:30070/<index_name>/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "size": <sample_size>,
    "query": {
      "function_score": {
        "query": {"match_all": {}},
        "random_score": {"seed": 42}
      }
    }
  }'
```

> **Note**: `random_score` without a `field` parameter calculates the random score based on the document's internal `_id` and seed, providing better compatibility. Lindorm search engine may not support the `_seq_no` field, so `field` is not specified.

Extract `hits.hits` from response; for each sample, query the source for comparison. If `size` exceeds the single-request limit (1000), make multiple requests with different `seed` values.

### Source Query-Back Methods

| Source | Query-back method | Notes |
|--------|-------------------|-------|
| Milvus | `client.query(collection_name, filter=f"{pk_field} == {repr(pk_val)}", output_fields=["*"], limit=1)` | Lindorm `_id` is string; Milvus primary key may be int, need `int(doc_id)` conversion. Requires PyMilvus SDK |
| Elasticsearch | `curl -s -u user:pass "http://<es_host>:9200/<source_index>/_doc/<doc_id>"` | Direct lookup by `_id` |
| Lindorm | `curl -s -u user:pass "http://<src_host>:30070/<source_index>/_doc/<doc_id>"` | Same as ES |
| Qdrant | `curl -s "http://<qd_host>:6333/collections/<col>/points/<point_id>"` | point id may be int or UUID str |
| CSV/OSS | Cannot query-back original file by `_id`; skip source query-back | See "CSV/OSS Source Validation Strategy" below |

### CSV/OSS Source Validation Strategy

CSV files do not support random query-back by `_id`; validation strategy is adjusted as follows:

1. **Row count validation**: Execute normally. Compare target `_count` against the CSV total row count from Step 2 pre-check
2. **Vector sampling validation (dimension + non-zero check)**: After randomly sampling from target, only validate that vector fields have **correct dimensions** and **values are not all-zero vectors** (all-zero typically indicates a parsing error); do not perform source query-back comparison
3. **Scalar field validation**: Skip source comparison (cannot query-back CSV); only check whether scalar fields in target samples **are empty/null** (WARN if empty value ratio is abnormally high)
4. **TTL validation**: Execute normally (validates target settings and field value reasonableness; does not depend on source query-back)
5. **Index build status**: Execute normally

> CSV/OSS source validation coverage is lower than other sources (cannot perform field-by-field comparison). The Agent MUST note this limitation in the validation report.

### Comparison Logic

- **Scalar fields**: Compare field by field; `str(src_val) != str(tgt_val)` is considered inconsistent
- **Vector fields**: Calculate cosine similarity `cosine(a, b) = dot(a,b) / (norm(a)*norm(b))`; similarity ≥ 0.95 passes; below 0.95 is considered inconsistent and the difference is recorded
  - For lossy compression indices like IVFPQ/IVFBQ, threshold can be relaxed to 0.90
  - For lossless indices like HNSW, threshold recommended at 0.99
- Exclude user-specified `exclude_fields`
- Summary report: scalar inconsistency count, vector similarity minimum / average

## IVFPQ/IVFBQ Index Build Status

HNSW does not need checking. IVFPQ/IVFBQ require polling the build status. Build command and response parsing are detailed in `references/03-ref/bulk-write.md` (IVFPQ/IVFBQ offline index building section). The Agent should poll every 30 seconds, waiting up to 1 hour maximum.

## Output Format

```json
{
    "data_validation": {
        "count_match": true,
        "source_count": 100000,
        "target_count": 100000,
        "sample_size": 200,
        "scalar_mismatches": [],
        "vector_check": {
            "checked": 200,
            "passed": 198,
            "min_cosine_similarity": 0.923,
            "avg_cosine_similarity": 0.997,
            "failed_docs": ["doc_id_123", "doc_id_456"]
        },
        "ttl_check": {
            "checked": true,
            "settings_consistent": true,
            "field_values_valid": true,
            "source_target_consistent": true,
            "details": "doc_ttl.field=expire_time, doc_ttl.unit=s, 200 samples all valid"
        }
    },
    "index_build": "ready"
}
```

`index_build` values: `ready` / `building` / `failed` / `not_applicable`

`failed_docs` in vector validation lists document IDs with similarity below threshold (display max 10).

`ttl_check.checked` is `false` when TTL is not configured; subsequent fields are skipped.

---

## TTL Validation (executed when TTL is configured)

When row-level TTL was configured during migration (Step 2 detection or manual configuration), TTL-specific validation is performed after row count and vector validation.

### 1. Target Settings Consistency

```bash
curl -s -u <username>:<password> "http://<host>:30070/<index_name>/_settings" \
  -H "Content-Type: application/json"
```

Extract `settings.index.doc_ttl.field` and `settings.index.doc_ttl.unit`, compare against the values confirmed during migration:

| Validation item | Expected value | Verdict |
|-----------------|---------------|---------|
| `doc_ttl.field` exists | Matches field name confirmed in Step 2 | Mismatch → FAIL |
| `doc_ttl.unit` exists | Matches unit (`s` or `ms`) confirmed in Step 2 | Mismatch → FAIL |

### 2. TTL Field Value Reasonableness

Extract TTL field values from random sample results and check whether they are valid future timestamps:

```python
import time

def validate_ttl_value(value, unit):
    now = int(time.time()) if unit == "s" else int(time.time() * 1000)
    ten_years = 10 * 365 * 86400 if unit == "s" else 10 * 365 * 86400 * 1000

    if value <= 0: return False, "Value is 0 or negative"
    if unit == "s" and value > 1e12: return False, "Appears to be millisecond-level timestamp, but unit=s"
    if unit == "ms" and value < 1e12: return False, "Appears to be second-level timestamp, but unit=ms; data will expire immediately"
    if value < now: return False, f"Value {value} has already expired"
    if value > now + ten_years: return False, f"Value {value} is more than 10 years in the future; unit may be wrong"
    return True, "valid"
```

> **Unit mismatch detection**: If `doc_ttl.unit = "ms"` but the field value is a second-level timestamp (e.g. `1718000000`), the value would be interpreted as 1970-06-20, and data **expires immediately**. The validation logic above detects this error via `value < 1e12`.

### 3. Source-to-Target TTL Consistency

Verify TTL field value conversion correctness based on source type and migration method:

| Migration method | Expected formula | Allowed drift | Verification method |
|-----------------|-----------------|---------------|---------------------|
| Lindorm → Lindorm (pass-through) | `target_value == source_value` | None | Query-back source same `_id` TTL field value; should be exactly equal |
| Milvus (second-level injection) | `target_value ≈ int(time.time()) + N` | ±60s | Check if value is within `[now + N - 60, now + N + 60]` range |
| Milvus (millisecond-level injection) | `target_value ≈ int(time.time() * 1000) + N * 1000` | ±60000ms | Same as above, millisecond-level |
| ES ILM (second-level) | `target_value ≈ to_epoch_seconds(source_ts) + min_age` | ±60s | Query-back source same `_id` timestamp field, calculate expected value for comparison |
| ES ILM (millisecond-level) | `target_value ≈ to_epoch_millis(source_ts) + min_age * 1000` | ±60000ms | Same as above, millisecond-level |
| Manual configuration | No expected formula | — | Skip consistency check; only validate value reasonableness (step 2) |

### 4. Negative Validation When TTL Is Not Configured

When user selected "Do not configure TTL," confirm that the target settings **do not contain** `doc_ttl` configuration:

```bash
curl -s -u <username>:<password> "http://<host>:30070/<index_name>/_settings" \
  -H "Content-Type: application/json"
```

If the response contains `doc_ttl.field` or `doc_ttl.unit`, report WARN: unexpected TTL configuration exists on target.

### Output Format

`ttl_check` field appended to the `data_validation` object:

```json
{
    "ttl_check": {
        "checked": true,
        "settings_consistent": true,
        "field_values_valid": true,
        "source_target_consistent": true,
        "details": "doc_ttl.field=expire_time, doc_ttl.unit=s, 200 samples all valid, ±3s drift"
    }
}
```

| Field | Description |
|-------|-------------|
| `checked` | Whether TTL validation was executed (`false` when TTL not configured; subsequent fields skipped) |
| `settings_consistent` | Whether target `doc_ttl` settings match the migration plan |
| `field_values_valid` | Whether sampled TTL field values are valid future timestamps |
| `source_target_consistent` | Whether source-to-target TTL values match expected conversion formula |
| `details` | Validation summary description |
