# Migration Workflow

This document defines the complete migration execution flow (Step 1-7), including interaction rules and MUST constraints for each step.

---

## Step 1: Collect Migration Information

Collect the following parameters through conversation. Use the **AskUserQuestion tool** to ask for each missing required item. Even if the user has already provided some parameters in the initial message, the Agent MUST confirm all key parameters one by one via AskUserQuestion (source type, connection info, target info), and MUST NOT directly use unconfirmed parameter values.

**1.1 Source Type**: Milvus / Elasticsearch / Lindorm / Qdrant / CSV file (OSS) / Export to CSV (export from source then upload to OSS)

> **When "Export to CSV" is selected**: The Agent first asks the user via AskUserQuestion for the export source type (Milvus / Elasticsearch / Lindorm / Qdrant), then executes the export following that source's parameter collection flow (see "Export to CSV flow" below). After export completes and the file is uploaded to OSS, proceed to Step 2.

**1.2 Source Connection Parameters**

| Parameter | Milvus | Elasticsearch | Lindorm | Qdrant |
|-----------|--------|---------------|---------|--------|
| Address | URI (Lite: local file; Server: http://host:port) | Host + Port (default 9200) | Host + Port (default 30070) | URL or Host+Port (default 6333) |
| Collection name | Collection name | Index name | Index name | Collection name |
| Authentication | Token (optional) | Username/Password (optional) | Username/Password (optional) | API Key (optional) |

**When index/collection name is unknown**: If the user is unsure which index or collection to migrate, the Agent MUST first connect to the source and list all available indices/collections, then present the list via AskUserQuestion for user selection. The list APIs and response parsing for each source are detailed in:
- Milvus → `references/01-dev/milvus-migrate.md` (List all Collections)
- Elasticsearch → `references/01-dev/elasticsearch-migrate.md` (List all indices)
- Lindorm → `references/01-dev/lindorm-migrate.md` (List all indices)
- Qdrant → `references/01-dev/qdrant-migrate.md` (List all Collections)

**CSV file (OSS) source connection parameters**:

| Parameter | Description |
|-----------|-------------|
| OSS Endpoint | Internal: `oss-<region>-internal.aliyuncs.com` (same-region ECS, no traffic fee); Public: `oss-<region>.aliyuncs.com` |
| Bucket name | OSS Bucket name |
| Object Key | CSV file path, e.g. `data/vectors.csv` |
| Access Key ID | Alibaba Cloud AK |
| Access Key Secret | Alibaba Cloud SK |
| **Original data source** | Which database the CSV was exported from: Milvus / Elasticsearch / Lindorm / Qdrant (required, Agent refuses to process "Other" sources) |

The `original data source` determines which migration guide all subsequent steps follow. CSV is the data reading layer; type mapping, DDL generation, TTL detection, migration script logic, etc. are all delegated to the original source's migration guide:

| Original Source | Delegated Guide |
|----------------|----------------|
| **Milvus** | `references/01-dev/milvus-migrate.md` |
| **Elasticsearch** | `references/01-dev/elasticsearch-migrate.md` |
| **Lindorm** | `references/01-dev/lindorm-migrate.md` |
| **Qdrant** | `references/01-dev/qdrant-migrate.md` |

> When the user selects "Other" as the source, the Agent MUST reject processing, informing the user: "Other sources are not currently supported. Only CSV files exported from Milvus / Elasticsearch / Lindorm / Qdrant are supported."

When internal network is selected, MUST prompt:
> Please use `oss-<region>-internal.aliyuncs.com` format for the endpoint (e.g., `oss-cn-hangzhou-internal.aliyuncs.com`). Same-region ECS access has no traffic charges and higher bandwidth.

**Export to CSV flow** (executed only when source type is "Export to CSV"):

The Agent follows the complete flow in `references/01-dev/csv-export.md`: ask for export source → collect parameters → pre-check (disk estimation) → execute export script → prompt user to upload to OSS → confirm upload and collect OSS parameters → connect to CSV import flow.

Key constraints:
- **Original data source is auto-inherited**: The source type from the export phase (Milvus/ES/Lindorm/Qdrant) is automatically filled in; MUST NOT re-ask
- After export completes, switch to CSV-OSS source; all subsequent steps follow `references/01-dev/csv-import.md`

**1.3 Target parameters** (Lindorm): Host (required), Port (default 30070), Index name (required), Username/Password (optional)

**1.4 Migration options** (ask one by one via AskUserQuestion)

> **Exclude fields**: Before asking, MUST first connect to the source to retrieve the schema, then present all field names via AskUserQuestion for user selection with multi-select support (multiSelect: true). The method for retrieving schemas from each source is detailed in the corresponding `<source>-migrate.md`. For Milvus sources, dynamic fields must also be displayed (refer to the dynamic field discovery section in `references/01-dev/milvus-migrate.md`).

> **Individual confirmation vs. batch confirmation**: Exclude fields and clear target MUST be asked individually via AskUserQuestion (high-risk operations). Other parameters (index method, shard count, routing field, batch size, concurrency, max errors) can be presented in a single AskUserQuestion **showing default and recommended values for batch confirmation**. The user can choose "Use all defaults" or "Adjust individually." When "Adjust individually" is selected, ask about each parameter that needs modification one by one.

| Parameter | Description | Default | Recommended |
|-----------|-------------|---------|-------------|
| Exclude fields | Column names to exclude from migration, via AskUserQuestion multi-select (**ask separately**) | Empty (no fields selected) | — |
| Clear target | Whether to clear the target index before migration (**ask separately**) | No | — |
| Index method | HNSW / IVFPQ / IVFBQ | HNSW | Sub-million: HNSW; over million: IVFPQ/IVFBQ |
| Shard count | Target index primary shard count (cannot be modified after creation) | 1 | Sub-million: 1; over million: 3~5 |
| Routing field | Optional, specify a source field name as routing key so documents with the same value land in the same shard (for multi-tenant isolation) | Empty | — |
| Batch size | Records per batch read | 1000 | Adjust based on vector dimension (see below) |
| Concurrency | Write thread count (1 = serial, >= 2 enables parallel write + backpressure control) | 1 | Public network: 1; Internal network: 4~10 |
| Max errors | Maximum tolerated errors (0 = stop on first error) | 0 | Test environment: 0; Production: 100~1000 |
| Migration mode | Full migration / Incremental migration | Full migration | First migration: full; delta compensation: incremental |

> **batch_size and vector dimension**: Each vector data item size ≈ `dimension × 4 bytes` (float32). The Agent should recommend a reasonable batch_size based on the vector dimension obtained during pre-checks, keeping each `_bulk` request size between 10~50MB:
>
> | Vector dimension | Per-vector size | Recommended batch_size | Approx. batch size |
> |-----------------|----------------|----------------------|-------------------|
> | 128 | 512 B | 5000 | ~2.5 MB |
> | 768 | 3 KB | 3000 | ~9 MB |
> | 1536 | 6 KB | 2000 | ~12 MB |
> | 4096 | 16 KB | 500 | ~8 MB |
>
> The vector dimension is obtained during Step 2 pre-checks. The Agent MUST adjust the default recommendation based on the actual dimension.

> **Incremental migration parameters** (ask only when user selects "Incremental migration"):
> - `incremental_field`: The timestamp/date field name used for filtering on the source side. The Agent filters fields of `date` / `long` / `INT64` type from the source schema and presents them via AskUserQuestion for user selection. If no usable timestamp field exists on the source side, inform the user that incremental migration is not possible and suggest full migration
> - `incremental_since`: Start value (inclusive), format must match the field type (epoch seconds/milliseconds or ISO 8601 string). Agent asks user for input
> - In incremental mode, progress displays "N records scanned" instead of percentage (total count is unknown)
> - Specific incremental filtering implementation for each source is detailed in: `milvus-migrate.md` (Expression filter), `elasticsearch-migrate.md` (Range filter), `lindorm-migrate.md` (Range filter), `qdrant-migrate.md` (Filter)

**1.5 Network type** (ask via AskUserQuestion)

| Option | Description |
|--------|-------------|
| Public network | Suitable for small data volumes (< 100,000 records) import or demos |
| Internal network (VPC) | Suitable for production environments & large batch migration imports |

- When **public network** is selected, MUST output prompt:
  > Currently using public network connection, suitable for small data volume imports or demos. For production large batch migrations, internal network (VPC) connection is recommended for higher bandwidth and lower latency.
- When **internal network** is selected, output confirmation:
  > Currently using internal network (VPC) connection, suitable for production large batch migrations.

---

## Step 2: Pre-checks

The Agent executes pre-checks to verify migration feasibility:

0. **Dependency check** (all sources): Verify required Python packages are installed. If not installed, prompt user to install and retry

   | Source | Required dependencies | Install command |
   |--------|----------------------|-----------------|
   | All | `elasticsearch==7.17.13` (for connecting to Lindorm target) | `pip install "elasticsearch==7.17.13"` |
   | Milvus | `pymilvus==3.0.0` | `pip install "pymilvus==3.0.0"` |
   | Qdrant | `qdrant-client==1.18.0` | `pip install "qdrant-client==1.18.0"` |
   | CSV/OSS | `oss2==2.19.1` | `pip install "oss2==2.19.1"` |
   | ES / Lindorm source | (no additional dependency, reuses target elasticsearch-py) | — |

   > **Version conflict note**: If the user's environment already has a different version of `elasticsearch` (e.g. 8.x), installing `7.17.13` will downgrade it. Suggest using a virtual environment for isolation: `python -m venv venv && source venv/bin/activate && pip install "elasticsearch==7.17.13"`
   >
   > **Python version requirement**: Python >= 3.9. Agent runs `python3 --version` to check; if below 3.9, prompt user to upgrade

1. Connect to source, retrieve schema and row count (refer to `references/01-dev/<source>-migrate.md`)
2. Connect to Lindorm target (`elasticsearch==7.17.13`, port 30070)
3. Retrieve target storage information (cluster stats API)
4. Estimate data size (**MUST execute, MUST NOT skip**): Randomly sample 100 source records, calculate average document size (bytes), multiply by total row count to get estimated raw data volume. Then multiply by index expansion factor to get estimated storage requirement (HNSW ~1.5x~2x, IVFPQ/IVFBQ ~1.2x~1.5x), compare against target available storage space, WARN if insufficient
5. Check field type compatibility: Iterate source fields, check each field type against the `references/03-ref/type-mapping.md` mapping table for mappability (skip excluded fields). FAIL if any unmappable type is found. **Nested type compatibility**: If the source contains `nested` (ES) or `object` with nested structure (Qdrant payload nested dict) fields, MUST WARN the user about compatibility risks for this type in Lindorm, and proceed only after AskUserQuestion confirmation
5.5. **Routing field validation** (executed when user specified a routing field): Check if the routing field exists in the source schema. If not found, FAIL with message: "Routing field '{field}' does not exist in source schema, please verify the field name"
6. **Qdrant source extra checks** (only when source is Qdrant):
   - Check if qdrant-client dependency is installed; if not, prompt user to install
   - After connecting to Qdrant, retrieve payload schema. If schema is empty or incomplete (Qdrant auto-inference may miss fields), display the identified field list and WARN prompting user to confirm
   - Sample the first batch of data, compare actual payload fields against schema. If fields not in the schema are found, append and display them with a WARN
   - **Multi-vector detection**: Check if `config.params.vectors` is a dict (not a `{size, distance}` structure). If in multi-vector mode (Named Vectors), display all vector names, dimensions, and distance metrics, and confirm via AskUserQuestion whether the user wants to migrate all named vectors (user can choose to exclude some). Each named vector maps to an independent `knn_vector` field in Lindorm (see the multi-vector mode section in `references/01-dev/qdrant-migrate.md`)

6.5. **ES source Scroll sort key detection** (only when source is ES and Scroll API is needed):
   - Trigger condition: ES version < 7.10, or ES version >= 8.x with elasticsearch-py version 7.x (PIT cursor bug)
   - Search the schema for a `type: keyword` field with unique values to use as the Scroll sort key (`sort_field`). Prefer business primary key fields (e.g. `id`, `article_id`, `title`, etc.)
   - Uniqueness check: Aggregation query `{"size": 0, "aggs": {"uniq": {"cardinality": {"field": "<field>"}}}}`, compare the returned unique count with the `_count` result; difference < 1% is considered passing
   - If check fails, FAIL with message: "ES 8.x does not support `_id` as sort key, and no unique keyword field was found in the current index. Please choose: 1) Manually specify a unique field; 2) Temporarily enable `PUT /<index>/_settings {"index.id_field_data.enabled": true}` on the source; 3) Abort migration"
   - After passing, write `sort_field` into DDL generation parameters; the migration script and checkpoint resume both use this field

7. **CSV/OSS source extra checks** (only when source is CSV file (OSS)):
   - Check if oss2 dependency is installed; if not, prompt user `pip install oss2`
   - Connect to OSS bucket, call `get_object_meta(object_key)` to verify file exists and get file size
   - **Export flow connection**: If the current migration went through the "Export to CSV" flow (user selected "Export to CSV" in Step 1), the original data source parameter is already auto-filled (inherited from the export phase); MUST NOT re-ask the user
   - Parse header, extract all column type declarations (see `references/01-dev/csv-import.md`)
   - Display the schema (column names, types, vector dimensions) to the user, AskUserQuestion to confirm or modify
   - Check for `knn_vector` fields; if none, WARN (user may have forgotten to include a vector column)
   - **Full scan CSV once**, completing both format validation and exact row count simultaneously (see the pre-check section in `references/01-dev/csv-import.md`). Full scan and format validation are merged; the OSS stream is opened only once without repeated reads. All columns must declare types in the header; missing or invalid type declarations result in format error and FAIL. If `date` type columns exist, MUST sample the first 100 rows to detect date format; DDL uses multi-format compatibility. Row count result is used for Step 4 progress display. **Note**: Large files (> 100MB) require reading the entire OSS stream for full scan; duration is proportional to file size. The Agent MUST use `timeout_ms=600000` (10 minutes) for this step, or use `run_in_background: true` for files > 500MB and poll for results

8. **TTL detection** (all sources):

> **Lindorm version requirement**: Row-level TTL requires `lindorm-lvector >= 1.3.3-20250519` and `lindorm-lsearch >= 1.3.3-20250519`. The Agent MUST check the version via the Lindorm cluster info endpoint before TTL detection:
> ```bash
> curl -s -u <user>:<pass> "http://<host>:30070/"
> ```
> The `version.lindorm_version` in the response (note: NOT `version.number`, which is the ES-compatible version like `7.10.2`). If `lindorm_version` is below `1.3.3`, MUST WARN the user: "The current Lindorm search engine version does not support row-level TTL. Configuring TTL may be ineffective or cause errors. Recommend upgrading before configuring TTL, or selecting 'Do not configure TTL'."

TTL detection methods and recommended approaches for each source are detailed in `references/02-ops/ttl-config.md`. Summary:

| Source | Detection Method | Recommended Approach |
|--------|-----------------|---------------------|
| Lindorm | Read `doc_ttl.field` / `doc_ttl.unit` | Pass through the same configuration directly |
| Milvus | Read `collection.ttl.seconds` | Convert to row-level injection: `expire_time = now + N` |
| ES | Read ILM delete phase `min_age` | Convert to row-level injection: `expire_time = document_timestamp + min_age` |
| Qdrant | No built-in TTL | Inform user there is no TTL |
| CSV/OSS | Cannot auto-detect; ask user based on original source | Process according to original source rules |

- After detecting TTL, use AskUserQuestion to provide three options: **Accept recommendation** / **Custom** (field name + unit) / **Do not configure TTL**
- When customizing, if the unit is changed from `s` to `ms`, MUST remind that the script will use millisecond-level calculations
- When no TTL is detected, ask the user whether they want to manually configure row-level TTL

Interpret output results:
- **PASS** → Recommend migration, proceed with Step 3
- **WARN** → Display all warnings, MUST use AskUserQuestion to ask user whether to confirm and continue (options: Continue / Abort). Proceed to Step 3 only after user confirms
- **FAIL** → Display failure reasons, do not proactively suggest continuing, wait for user instructions

---

## Step 3: Generate DDL and Display Migration Plan

The Agent generates Lindorm ES-compatible mapping JSON based on the source schema and the cross-source comparison table in `references/03-ref/type-mapping.md`.

**Rules**:
- Skip user-specified excluded fields
- Milvus dynamic fields are not written into the mapping (Lindorm dynamic mapping auto-infers), but MUST annotate in the DDL display: "The following dynamic fields will be auto-inferred by Lindorm dynamic mapping: {field list}"
- ES `_id` meta field is not written into mapping properties
- ES `nested` type fields MUST be skipped and the user must be informed during DDL display
- Qdrant vector fields need to be manually added (not in payload)
- **CSV/OSS source**: Schema comes from the header type declarations confirmed by the user in Step 2; vector field dimensions and distance metrics are read directly from the header; subsequent DDL generation logic is the same as other sources
- When user specifies shard count > 1, add `number_of_shards` to `settings.index` (cannot be modified after creation)
- When user specifies a routing field, add `knn_routing: true` to `settings.index` (requires `number_of_shards > 1`); if user has not specified shard count, MUST prompt user to set shard count greater than 1 to enable routing
- **For IVFPQ/IVFBQ index methods**, MUST add `"knn.offline.construction": true` to `settings.index` (refer to the IVFPQ/IVFBQ section in `references/03-ref/bulk-write.md`)
- When user enables TTL (Step 2 detection recommendation or manual configuration), add `doc_ttl.field` and `doc_ttl.unit` to `settings.index` (refer to `references/02-ops/ttl-config.md`)
- When user enables TTL, ensure the TTL field is declared as `long` type in mappings properties. If the source schema does not contain this field, add it automatically
- When DDL display includes TTL configuration, MUST annotate the configuration source ("source detection recommendation" or "manual configuration") and remind the user to confirm that the TTL field exists in the data and its value is an expiration timestamp (absolute time)

**Display to user (MUST execute, MUST NOT skip)**:

> **DDL confirmation is a mandatory interaction step**. The Agent MUST present the complete DDL JSON to the user via **AskUserQuestion tool** and wait for explicit user confirmation before executing Step 4. MUST NOT substitute a brief description like "DDL has been generated" for the full display, and MUST NOT create the index without user confirmation.

1. **Display complete DDL JSON** (MUST use AskUserQuestion): Present the generated complete `PUT /<index>` request body (including settings and mappings) as AskUserQuestion description content. Options: Confirm using this DDL / Need modifications (user can describe modification needs; regenerate DDL and confirm again)
2. **Display migration summary** (MUST use AskUserQuestion): Present the following information in table or list format for final user confirmation:
   - Source type + connection address + index/collection name
   - Target connection address + index name
   - Excluded fields list (if any)
   - Index method (HNSW / IVFPQ / IVFBQ)
   - Shard count, batch size, concurrency
   - Whether to clear target
   - Network type (public/internal)
   - TTL configuration (if any)
   - Options: Confirm and start migration / Cancel

---

## Step 4: Create Target Index

The Agent creates the target index (refer to `references/03-ref/bulk-write.md`):

1. **Check if target index already exists**: `curl -s -o /dev/null -w "%{http_code}" "http://<host>:30070/<index_name>"` (200=exists, 404=does not exist)
2. If clear target is selected and the index exists, delete it first (MUST require second confirmation before deletion)
3. **If clear target is not selected but index exists**:
   - Get the existing index document count: `GET /<index>/_count`
   - Get the existing index mapping, check compatibility with the generated DDL (field types, vector dimensions consistency)
   - Inform the user via AskUserQuestion: `"Target index '{index}' already exists with {count} documents. Continuing migration will write in upsert mode (documents with the same _id will be overwritten, documents with different _id will be appended)."` Options: Continue / Clear and recreate / Abort
   - If mapping is incompatible, FAIL with message: "The existing index mapping is incompatible with the migration source schema. Recommend clearing and recreating."
4. Create the index using the user-confirmed DDL (when index does not exist)
5. Output creation result

---

## Step 5: Execute Data Migration

> **Stop writes recommendation** (only applicable when source is an active database: Milvus / Elasticsearch / Lindorm / Qdrant. **Skip this step for CSV/OSS source**, as CSV files are static data with no source write concerns):
> Before migration begins, MUST prompt the user:
>
> > It is recommended to stop writes on the source during migration to ensure data consistency. If the source continues to receive writes, the target may be missing data added during the migration period. To migrate incremental data, you can use incremental migration mode (filtering by timestamp field) to compensate for delta data after full migration completes. See the "Incremental migration" section in each source migration guide. If writes cannot be stopped and the source has no timestamp field, a full comparison is recommended after migration to compensate for any differences.
>
> MUST use AskUserQuestion (options: Writes stopped, start migration / Writes not stopped, continue knowing the risk / Cancel). If user cancels, stop and do not execute the migration script.

The Agent executes the migration script, completing source scan → Lindorm bulk write.

**Reference documents**:
- Source scan: `references/01-dev/<source>-migrate.md` (data scan section)
- Target write: `references/03-ref/bulk-write.md` (bulk write section)
- Checkpoint resume: `references/02-ops/checkpoint-resume.md`

**Execution notes**: Migration scripts may run for extended periods (millions of records take tens of minutes). The Agent MUST use `run_in_background: true` for background execution and poll for progress; if running in foreground, set timeout to `3600000` (1 hour) to match actual runtime.

**Log file**: The script MUST initialize TeeWriter at startup, writing all stdout output to both the console and a log file simultaneously. The log file name is determined by the Agent and MUST be explicitly defined in the script and communicated to the user after execution. See `references/02-ops/checkpoint-resume.md`.

**Progress reporting requirements**: The script MUST print a `[PROGRESS]` line after each batch write, including current migrated count, total, and percentage. For large data volumes (> 10,000 records), the Agent MUST proactively report current progress percentage and estimated remaining time (ETA) when polling progress. ETA calculation: `elapsed_time / migrated_count × remaining_count`.

**Script structure**: Log initialization → parameter section (including checkpoint resume parameters) → signal handler registration → connect source + target → loop (scan → filter → TTL injection → bulk write → print progress) → completion/interruption output → IVFPQ/IVFBQ trigger build. See `references/02-ops/checkpoint-resume.md`.

**CSV/OSS source specifics**: The script parameter section additionally includes OSS configuration (credentials read from environment variables) and `RESUME_OFFSET` (row offset, 0 means start from beginning). The CSV source migration loop (re-pull stream → skip processed rows → bulk write) is detailed in `references/01-dev/csv-import.md`. CSV source also supports concurrent writes; backpressure control logic is detailed in `references/03-ref/bulk-write.md`.

**Credential security rules**: All migration/export scripts generated by the Agent MUST read credentials from environment variables; MUST NOT write them in plaintext into scripts:

| Source | Environment variable | Purpose |
|--------|---------------------|---------|
| Milvus | `MILVUS_TOKEN` | Token |
| Elasticsearch | `ES_USERNAME`, `ES_PASSWORD` | Basic Auth |
| Lindorm | `LINDORM_USERNAME`, `LINDORM_PASSWORD` | Basic Auth |
| Qdrant | `QDRANT_API_KEY` | API Key |
| OSS | `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET` | AK/SK |

> The Agent MUST confirm required environment variables are set before executing the script. If not set, prompt the user to set them via `export VAR=value`; MUST NOT fall back to plaintext hardcoding.

**TTL injection (when user confirmed TTL configuration in Step 2)**:

The migration script injects or passes the expiration timestamp before writing each row, depending on the source type. See `references/02-ops/ttl-config.md`.

| Source | Injection method | Script logic |
|--------|-----------------|--------------|
| **Lindorm** | Pass through directly | Source data already contains expiration timestamp field |
| **Milvus** | Script calculates | `expire_time = int(time.time()) + N` (for millisecond-level, both values × 1000) |
| **Elasticsearch** | Script calculates | `expire_time = to_epoch_seconds(row[timestamp_field]) + min_age_seconds` (for millisecond-level, × 1000) |
| **Manual config** | Pass through directly | User has ensured data contains TTL field |
| **CSV/OSS** | Depends on original data source | Process according to original source rules |

**Concurrent writes (concurrency >= 2)**: MUST use thread pool + backpressure control. Core pattern (backpressure logic, rate-limit retry, write function) is detailed in `references/03-ref/bulk-write.md` (parallel writes and backpressure control section).

**Checkpoint resume operations**: See `references/02-ops/checkpoint-resume.md`.

---

## Step 6: Post-Migration Validation

Post-migration validation MUST be executed, MUST NOT be skipped, and does not require asking the user whether to execute.

> **IVFPQ/IVFBQ prerequisite**: If the index method is IVFPQ or IVFBQ, the Agent MUST confirm Build status is `ready` before executing post-migration validation. KNN search returns empty results or errors when Build is not complete, causing vector sampling validation to fail. Build polling rules are detailed in `references/03-ref/bulk-write.md` (IVFPQ/IVFBQ offline index building section).

The Agent directly executes all validation items to verify data consistency. All validation items (refresh index, row count validation, random sampling, index build status, TTL validation) rules and thresholds are detailed in `references/02-ops/postcheck.md`.

After validation completes:
- All check items pass (row count matches, vector similarity meets threshold, TTL configuration correct) → proceed directly to Step 7
- Any inconsistency or failure → MUST use AskUserQuestion to display issue details and ask user (options: Need investigation / Ignore issues and continue). If user selects "Need investigation," assist with troubleshooting; proceed to Step 7 only after user confirms

---

## Step 7: Application Code Migration Advice

After migration completes, the Agent MUST provide the user with advice for migrating application code from the source to Lindorm. The Agent MUST select the corresponding **source-specific migration checklist** based on the source type (Milvus→Lindorm / ES→Lindorm / Qdrant→Lindorm / Lindorm cross-instance), displaying specific API replacement code examples. MUST NOT provide only generic advice (e.g., "replace client"). All migration points (connection layer, query syntax, write interface, pagination) and source-specific checklists are detailed in `references/03-ref/code-migration.md`.
