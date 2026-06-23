# CSV File (OSS) Data Reading Interface

## Positioning and Responsibility Boundary

CSV is a **data reading layer**, not an independent migration source type. The complete flow when the Agent handles CSV import:

```
1. Collect CSV connection parameters (OSS Endpoint/Bucket/Object Key/AK/SK)
2. Ask user: which database the CSV was exported from (Milvus/ES/Lindorm/Qdrant) ← MUST ask; reject if "Other" is selected
3. Read CSV header → parse schema
4. Delegate schema to the original source's migration guide:
   ├── Original source=Milvus      → references/01-dev/milvus-migrate.md (type mapping, TTL detection, DDL generation)
   ├── Original source=Elasticsearch → references/01-dev/elasticsearch-migrate.md
   ├── Original source=Lindorm      → references/01-dev/lindorm-migrate.md
   ├── Original source=Qdrant       → references/01-dev/qdrant-migrate.md
   └── Original source=Other        → Agent refuses to process, informs user "Other sources not currently supported"
5. All subsequent steps (DDL generation, TTL handling, migration execution, post-migration validation) follow the original source's rules
```

**The only difference** is the data reading method: reading from a CSV file instead of a database API. Type mapping, distance metrics, TTL detection rules, DDL generation rules, migration script logic (exclude fields, TTL injection, routing writes, etc.) all reuse the original source's migration guide.

This document (csv-import.md) only covers CSV-specific parts: OSS connection, streaming read, header parsing, format validation, checkpoint resume (by row offset). For all other aspects, refer to the corresponding `<source>-migrate.md`.

---

## Original Data Source

The user MUST specify which database the CSV file was exported from in Step 1. This parameter does not affect CSV reading itself but determines which migration guide all subsequent steps follow:

| Original source | Delegated guide | Special handling |
|----------------|----------------|-----------------|
| **Milvus** | `milvus-migrate.md`: type mapping, TTL (collection-level → row-level injection), DDL generation rules | None |
| **Elasticsearch** | `elasticsearch-migrate.md`: type mapping, TTL (ILM min_age), DDL generation rules | `_id`/`_doc_id` column if present is used as Lindorm document `_id`, not written to properties |
| **Lindorm** | `lindorm-migrate.md`: type mapping, TTL (row-level doc_ttl), DDL generation rules | `_id`/`_doc_id` column if present is used as Lindorm document `_id`, not written to properties |
| **Qdrant** | `qdrant-migrate.md`: type mapping, DDL generation rules (vector fields need manual addition) | No built-in TTL; directly inform user |

> **`_id` / `_doc_id` column identification**: In CSVs exported from ES/Lindorm sources, the source document `_id` is injected as a CSV column to restore it during import. Import identification rules:
> - `id` column exists → use as Lindorm document `_id`, do not write to properties
> - `_doc_id` column exists → same as above (during export, source already had an `id` field, so `_doc_id` was used to avoid conflict; see `csv-export.md`)
> - Both columns exist (should not happen) → prioritize `_doc_id`, WARN prompting user to confirm
> - Neither column exists → do not set document `_id`; let Lindorm auto-generate

> When the user selects "Other" as the source, the Agent MUST reject processing, informing the user: "Other sources are not currently supported. Only CSV files exported from Milvus / Elasticsearch / Lindorm / Qdrant are supported."

---

## CSV File Format Specification

See `references/03-ref/csv-format.md` (typed header format, type identifiers, vector field serialization, `parse_header` function).

---

## OSS Connection

```python
import oss2

# Credentials MUST be read from environment variables; MUST NOT be written in plaintext into script
access_key_id = os.environ.get("OSS_ACCESS_KEY_ID", "")
access_key_secret = os.environ.get("OSS_ACCESS_KEY_SECRET", "")

auth = oss2.Auth(access_key_id, access_key_secret)
bucket = oss2.Bucket(auth, endpoint, bucket_name)
```

- **Internal endpoint** (same-region ECS, no traffic fee): `https://oss-<region>-internal.aliyuncs.com`
  - Example: `https://oss-cn-hangzhou-internal.aliyuncs.com`
- **Public endpoint**: `https://oss-<region>.aliyuncs.com`
  - Example: `https://oss-cn-hangzhou.aliyuncs.com`

### Pre-check: Confirm File Exists and Get Size

```python
meta = bucket.get_object_meta(object_key)
file_size = meta.content_length   # bytes
```

If file does not exist, `oss2.exceptions.NoSuchKey` exception is raised; prompt user to verify the object key.

---

## Streaming CSV Read

**Do not download the entire file locally**; directly wrap the OSS stream as TextIOWrapper for constant memory usage:

> **Note**: `bucket.get_object()` returns a `GetObjectResult` that does not implement the `io.RawIOBase` interface (missing `readable()` / `readinto()`); it cannot be passed directly to `io.TextIOWrapper`. The underlying `obj.resp.response.raw` (`urllib3.HTTPResponse`) implements `io.IOBase` but produces "I/O operation on closed file" errors during long stream reads (thousands of rows or more). MUST use the `OssRawReader` adapter to wrap `GetObjectResult.read()` as standard `io.RawIOBase`.

```python
import oss2, csv, io

class OssRawReader(io.RawIOBase):
    """Adapter: wraps oss2.GetObjectResult.read() into io.RawIOBase for TextIOWrapper."""
    def __init__(self, oss_result, chunk_size=65536):
        self._oss = oss_result
        self._chunk_size = chunk_size
        self._buf = b''

    def readable(self):
        return True

    def readinto(self, b):
        try:
            while not self._buf:
                chunk = self._oss.read(self._chunk_size)
                if not chunk:
                    return 0
                self._buf = chunk
            n = min(len(b), len(self._buf))
            b[:n] = self._buf[:n]
            self._buf = self._buf[n:]
            return n
        except Exception:
            return 0

obj = bucket.get_object(object_key)
stream = io.TextIOWrapper(io.BufferedReader(OssRawReader(obj)), encoding='utf-8-sig')  # utf-8-sig auto-removes BOM

# Read raw header line first, parse clean_names (column names with type suffix removed)
raw_reader = csv.reader(stream)
raw_header = next(raw_reader)  # e.g. ['id:long', 'title:text', 'embedding:knn_vector:128:cosine']
clean_names, schema = parse_header(raw_header)

# MUST pass clean_names as fieldnames; otherwise DictReader uses 'embedding:knn_vector:128:cosine' as key
reader = csv.DictReader(stream, fieldnames=clean_names)
for row in reader:
    # row keys are column names from clean_names (e.g. 'embedding'), not raw header with type suffix
    process(row)
```

> **Common mistake**: Without passing `fieldnames=clean_names`, `csv.DictReader` uses the raw header (with type suffix) as keys, causing `row['embedding']` to raise KeyError. MUST parse header first to get `clean_names`, then pass to `DictReader`.

### Header Parsing

See the `parse_header` function in `references/03-ref/csv-format.md`.

---

## CSV Format Validation

The Agent performs a **full scan once** during the pre-check phase, completing both format validation and total row count simultaneously without re-opening the stream. Issues found cause immediate termination with a structured error report.

### Validation Rules

| Validation item | Error condition | Error description |
|-----------------|-----------------|-------------------|
| File not empty | File is empty | "CSV file is empty; must contain at least one header row" |
| First row is header | A column in the first row parses as a pure number or JSON array | "First row should be header; column {N} detected as pure number/array. Please confirm the first row is a header" |
| Delimiter | Header has only 1 column and no comma | "Only 1 column detected. Please confirm the delimiter is a comma (,)" |
| **Column name uniqueness** | Header contains duplicate column names | "Column name '{col}' is duplicated. Please ensure all header column names are unique" |
| **Type required** | A header column has no `:` type declaration | "Column '{col}' is missing type declaration. All columns must declare types in format: {col}:type, e.g. {col}:keyword" |
| Valid type identifier | Type after `:` is not in the supported list | "Column '{col}' type '{type}' is invalid. Supported: long/integer/float/double/boolean/keyword/text/date/knn_vector" |
| knn_vector dimension | `knn_vector` without dimension specified | "Vector column '{col}' is missing dimension. Correct format: {col}:knn_vector:128 or {col}:knn_vector:128:cosine" |
| Column count consistency | A row's column count differs from header | "Row {row} has {actual} columns, which differs from header column count {expected}" |
| Valid vector value | Vector column value cannot be json.loads'd or elements are not numeric | "Column '{col}' row {row} vector format error: '{val}'. Expected format: [0.1, 0.2, ...]" |
| Vector dimension match | Actual vector length differs from header-declared dimension | "Vector column '{col}' row {row} actual dimension {actual} differs from header-declared {declared}" |
| Vector dimension consistency | Same vector column has different actual dimensions across rows | "Vector column '{col}' dimension inconsistent: row {r1}={d1}, row {r2}={d2}" |
| File encoding | Contains non-UTF-8 characters | "File contains non-UTF-8 characters. Please re-export with UTF-8 encoding" |
| **Date format sampling** | Date type column values cannot be parsed by the DDL `format` | "Column '{col}' row {row} date format '{val}' is incompatible with DDL format declaration. Recommend DDL use multi-format: `yyyy-MM-dd HH:mm:ss\|\|strict_date_optional_time\|\|epoch_millis`" |

> **Date type MUST be sample-validated**: When CSV contains `date` type columns, the Agent MUST sample the first 100 rows during pre-check to detect date format (ISO 8601 / `yyyy-MM-dd HH:mm:ss` / epoch, etc.). DDL MUST use multi-format compatibility: `"format": "yyyy-MM-dd HH:mm:ss||strict_date_optional_time||epoch_millis"` rather than a single `strict_date_optional_time`.

### Error Output Format

When format issues are found, the Agent outputs a structured prompt and **does not continue to subsequent steps**:

```
CSV format validation failed, {N} issues found:

[ERROR 1] Row 1024 column count inconsistent
  Actual columns: 5, expected: 6
  Raw content: 1,Product A,99.9,"[0.1, 0.2]"

[ERROR 2] Vector column 'embedding' row 2048 format error
  Raw value: 0.1 0.2 0.3
  Expected format: [0.1, 0.2, 0.3] (JSON array string, numeric elements, must be quoted if containing commas)

[ERROR 3] Header column 'vec' type 'vector' is invalid
  Raw header: id:long,vec:vector:128
  Supported types: long / integer / float / double / boolean / keyword / text / date / knn_vector

Correct CSV format:
  id:long,title:text,price:float,embedding:knn_vector:128:cosine
  1,Product A,99.9,"[0.1, 0.2, 0.3, 0.4]"
  2,Product B,199.0,"[0.5, 0.6, 0.7, 0.8]"

Format notes:
  - First row is header, format: column_name:type (all columns must declare type)
  - Vector column format: column_name:knn_vector:dimension:distance_metric, e.g. embedding:knn_vector:128:cosine
  - Distance metric can be omitted (default cosine); options: cosine / l2 / innerproduct
  - Vector values are JSON array strings: [0.1, 0.2, 0.3], must be quoted if containing commas
  - Comma-separated, UTF-8 encoding, each row's column count matches header
  - Supported types: long / integer / float / double / boolean / keyword / text / date / knn_vector
```

### Validation Timing

- **Pre-check phase (Step 2)**: Full scan CSV once, completing both format validation (all rules) and total row count simultaneously. Full scan and format validation are merged; the OSS stream is opened only once without repeated reads. Report error immediately on format issues; do not proceed to subsequent steps
- **Migration execution phase (Step 5)**: Continue per-row validation during full read; on parse errors, skip or terminate based on max errors threshold

---

## Schema Reading

The Agent parses the schema directly from the CSV header row; all column types are declared by the user in the header.

The Agent displays the parsed schema to the user for confirmation:

```
Detected the following fields (4 columns total):

  Column Name   Type          Notes
  ──────────────────────────────────────────
  id            long
  title         text
  price         float
  embedding     knn_vector    dim=128, space=cosine

To modify a column type, provide the column name and target type. After confirmation, Lindorm DDL will be generated.
```

### Pre-check: Full Scan (row count + format validation merged)

The following code opens the OSS stream once, completing both total row count and format validation simultaneously without re-opening:

```python
obj = bucket.get_object(object_key)
stream = io.TextIOWrapper(io.BufferedReader(OssRawReader(obj)), encoding='utf-8-sig')

raw_reader = csv.reader(stream)
raw_header = next(raw_reader)
clean_names, schema = parse_header(raw_header)  # Validate header (type declarations, uniqueness, etc.)
expected_cols = len(raw_header)

total = 0
errors = []

# Use csv.reader (not DictReader) for format validation to accurately detect each row's actual column count
for i, row in enumerate(raw_reader, start=2):  # Row numbers start at 2 (1 is header)
    total += 1
    # Column count consistency (csv.reader returns list; len accurately reflects actual column count)
    if len(row) != expected_cols:
        errors.append(f"Row {i} has {len(row)} columns, differs from header column count {expected_cols}")
    # Vector value validation: access row[col_index] via clean_names index
    # Dimension matching, date format sampling, etc...
    # (Check each rule per validation rule table, append errors)

# After validation
if errors:
    # Output structured error report; do not continue
    report_csv_errors(errors)
else:
    print(f"Format validation passed, total rows: {total}")
    # total is used for Step 4 progress display; no need to scan again
```

> **Large file note**: Full scan requires reading the entire OSS stream; duration is proportional to file size (files > 100MB may take several minutes). The scan result (`total`) is used for subsequent migration progress display, avoiding another full scan for counting during migration. The Agent MUST use `timeout_ms=600000` (10 minutes) for this step, or use `run_in_background: true` for files > 500MB and poll for progress.

---

## Vector Field Parsing

See the `parse_vector` function in `references/03-ref/csv-format.md`.

---

## Checkpoint Resume (by Row Offset)

> **MUST rule**: CSV import migration scripts MUST use TeeWriter to write all output to both stdout and a log file simultaneously, and MUST include `[PROGRESS]`/`[INTERRUPTED]`/`[DONE]` structured output. TeeWriter initialization is detailed in `references/02-ops/checkpoint-resume.md`.

CSV streams do not support random access; on resume, re-pull the stream and skip already-processed rows. **Note**: Skipped rows still need to be sequentially read from OSS; the time cost is proportional to the number of already-processed rows (e.g. if 900,000 rows were processed, resuming requires first reading and skipping 900,000 rows):

```python
obj = bucket.get_object(object_key)
reader = csv.DictReader(io.TextIOWrapper(io.BufferedReader(OssRawReader(obj)), encoding='utf-8-sig'))

for i, row in enumerate(reader):
    if i < resume_offset:   # Skip already successfully written rows
        continue
    # Process current row ...
```

- `resume_offset`: Number of data rows successfully written to Lindorm (excluding header); corresponds to the `cursor` field in the output protocol
- Output protocol (`[PROGRESS]` / `[INTERRUPTED]` / `[DONE]`) is detailed in `references/02-ops/checkpoint-resume.md`; the CSV source's `cursor` value is an integer row offset
- On interruption, the Agent extracts the last `[INTERRUPTED]` line from the log file, taking the `cursor` value as the resume row offset
- On resume, regenerate the script with the `cursor` value filled into the `RESUME_OFFSET` parameter

---

## Rate Limiting and Error Handling

| Scenario | Handling |
|----------|----------|
| OSS connection failure | Catch `oss2.exceptions.RequestError`; display full error; do not silently retry |
| OSS file not found | Catch `oss2.exceptions.NoSuchKey`; prompt user to check object key |
| OSS stream interruption | Re-call `get_object` and skip first `cursor` rows (already-processed count) |
| CSV row parse failure (column count mismatch, etc.) | Record row number and content; skip the row; accumulate to `parse_errors`; terminate if exceeding max errors |
| Vector parse failure | Record row number and raw value; skip the row; accumulate to `parse_errors` |
| Lindorm write 429 | Exponential backoff retry (0.5s → 1s → 2s → 4s), max 5 retries |

---

## CSV Value Type Conversion and Null Handling

All values in CSV are strings; MUST convert by schema type before writing to Lindorm. During export, source `None` / `null` values are written as empty string `""`; during import, these need special handling, otherwise Lindorm rejects empty strings written to numeric/boolean fields.

```python
def convert_csv_value(val, col_name, col_schema):
    """Convert CSV string value to Lindorm-compatible type. Returns None for empty values (skip field during write)."""
    if val is None or val == "":
        return None  # Empty value: omit this field from _source during write

    if isinstance(col_schema, dict) and col_schema.get("type") == "knn_vector":
        return parse_vector(val, col_name, 0)  # json.loads → list

    type_name = col_schema if isinstance(col_schema, str) else col_schema.get("type", "keyword")

    if type_name in ("long", "integer"):
        return int(float(val))  # "123.0" → 123
    elif type_name in ("float", "double"):
        return float(val)
    elif type_name == "boolean":
        return val.lower() in ("true", "1", "yes")
    else:
        return val  # keyword / text / date: keep as string
```

**When building `_source` in the migration script**:

```python
doc = {}
for col_name in clean_names:
    if col_name in EXCLUDE_FIELDS:
        continue
    converted = convert_csv_value(row[col_name], col_name, schema[col_name])
    if converted is not None:  # Empty values not written to _source; Lindorm uses defaults
        doc[col_name] = converted
```

> **Alignment with export format**: `csv-export.md` writes `None` as empty string (CSV spec does not support null); `csv-import.md` restores empty strings to missing fields (not written to `_source`) during import. The two sides cooperate to ensure correct null value propagation.

---

## Dependencies

```
oss2==2.19.1
```

Install: `pip install "oss2==2.19.1"`
