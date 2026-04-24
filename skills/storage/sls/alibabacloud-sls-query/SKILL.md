---
name: alibabacloud-sls-query
description: |
  Alibaba Cloud SLS (Simple Log Service) log query & analysis skill. Use this skill to help users write, explain, optimize, execute, or troubleshoot SLS index search, SQL analytics, and SPL scan/pipeline statements through the aliyun CLI.
  Triggers: "SLS 查询", "SLS 分析", "日志查询", "日志分析", "SLS 排障", "log query", "analyze logs", "aliyun log query".
---

# Alibaba Cloud SLS Query & Analysis

## Scenario Description

Use this skill when the user wants to:

- Explain, rewrite, optimize or execute an existing query
- Translate a natural-language requirement into an SLS **index query**, **SQL**, or **SPL** statement

---

## Prerequisites

### Install Aliyun CLI

Run `aliyun version` to verify if version >= `3.3.8`. If not installed or outdated, follow the doc [references/cli-installation-guide.md](references/cli-installation-guide.md) to install or update.

### Ensure AI Mode Enabled

Before executing any CLI commands, enable AI-Mode, set User-Agent, and update plugins:

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sls-query"
aliyun plugin update
```

### Check Alibaba Cloud credentials configured

Run `aliyun configure list` to check if credentials configured.
If no valid profile is shown, **STOP** here and ask the user to run `aliyun configure` outside of this session.

**Security rules:**

- **NEVER** read, echo, or print AK/SK values
- **NEVER** ask the user to paste AK/SK into the conversation
- **ONLY** use `aliyun configure list` to check credential status

---

## RAM Permission Requirements

| API | CLI | Action | Purpose |
|-----|-----|--------|---------|
| GetLogsV2 | `get-logs-v2` | `log:GetLogStoreLogs` | Run query / SQL / SPL and read results |
| GetIndex  | `get-index`   | `log:GetIndex`        | Read index config to verify prerequisites |

For the minimum and complete RAM policy JSON, see [references/ram-policies.md](references/ram-policies.md).

> **Permission failure handling:** If a call returns `Unauthorized` permission error, stop and surface [references/ram-policies.md](references/ram-policies.md) to the user. Do **not** retry with a different account without explicit user confirmation.

---

## Core Workflow

1. Read index configuration (GetIndex)
2. Pick query mode
3. Build statement
4. Resolve time range
5. Execute query
6. Extract data from response
7. Present CLI command and results

### Step 1: Read the Index Configuration (Mandatory)

Always call `get-index` first — the index config decides which query modes are available in Step 2.

```bash
aliyun sls get-index \
  --project <project> --logstore <logstore>
```

Two sections in the response drive every later decision:

| Section | Meaning |
|---------|---------|
| `line`  | **Full-text index** — absence means full-text search is disabled |
| `keys`  | **Field indexes** — map of field → `{ type, doc_value, token, caseSensitive, chn, ... }`. `doc_value: true` means statistics are enabled on that field |

If the call returns `IndexConfigNotExist` (HTTP 404), or the response has neither `line` nor `keys` populated, the Logstore has no index at all — stop immediately and tell the user they must create an index before any query / SQL / SPL can run.

- **The response can be large** — extract only the fields relevant to the current query. Cache per `logstore` and reuse within the session.

For field types, tokenization, and how `get-index` maps to capabilities, see [references/related-apis.md](references/related-apis.md) and [references/query-analysis.md](references/query-analysis.md).

---

### Step 2: Pick the Query Mode (Critical)

The query statement takes one of the following forms:

| Priority | Mode | Statement Form | Use when | Requires |
|----------|------|----------------|----------|----------|
| 1 | **Index search** | `<index-search>` | Filtering raw logs; return time-ordered and paginated logs | Full-text (`line`) or any field index (`keys.<field>`) |
| 2 | **SQL** | `<index-search> \| <SQL>` | Aggregation, `GROUP BY`, sort, window, top-N, projection, and other analytical operations | Target field has `keys.<field>` with `doc_value: true` |
| 3 | **SQL scan** | `<index-search> \| <SQL scan>` | User requested | None |
| 4 | **SPL** | `<index-search> \| <SPL>` | User requested | None |

**Selection rule:**

- Always prefer **Index search** for fastest speed.
- Use **Index search + SQL** when the user needs analytical operations or field projection rather than full raw-log retrieval, such as aggregation, `GROUP BY`, sorting, window analysis, top-N, or returning only the required fields/columns.
- Do **not** proactively choose **SQL scan** or **SPL**; use them only when the user explicitly requests.

For the full decision guide, see [references/query-analysis.md](references/query-analysis.md).

---

### Step 3: Write the Statement

#### 3.1 Build the index-search segment first (left of `|`)

Collect every filter that can be expressed in index-search syntax and place it before the first `|`. Use `*` if no filter applies.

```text
* and "payment failed" and status: "500" and not path: "/healthz"
```

- `*` matches all; `"..."` is full-text (needs full-text index).
- `key: "value"` is a field filter (needs field index).
- Combine with `and` / `or` / `not`; group with parentheses.
- `key: *` means field exists. Range (`>`, `>=`, `[a, b]`) works only on `long` / `double`.

If the requirement can be fully answered without aggregation or row-level processing, stop here — this is already a complete index search. For full index-search syntax, see [references/query-analysis.md](references/query-analysis.md).

#### 3.2 Append SQL — for aggregation / analytics

```sql
status: 500 | SELECT date_trunc('minute', __time__) AS minute,
                    count(*) AS errors
              FROM log
              GROUP BY minute
              ORDER BY minute
```

- Read [references/query-analysis.md](references/query-analysis.md) for Query & SQL rules
- Table name is `log` (recommended to omit).
- SQL respects the indexed field type from `get-index` — a `long` / `double` field can be compared directly (`status >= 500`). Cast only when a field is indexed as `text` but numeric semantics are needed (`try_cast` to suppress errors).
- Read [references/functions-guide.md](references/functions-guide.md) for unusual Function selection (aggregate, JSON, regex, datetime, IP geo …)

#### 3.3 Append SPL — for row-level processing / flexible filtering

```spl
status: 500 and service: payment
| where try_cast(latency as BIGINT) > 1000
| extend latency_ms = try_cast(latency as BIGINT)
| project service, latency_ms, message
```

For SPL syntax, pipeline commands, and field-handling rules, read [references/spl-guide.md](references/spl-guide.md).

#### 3.4 Append SQL scan — fallback when the target field has no index / statistics

Syntax follows regular SQL (see 3.2), with one difference: **every field is `varchar`**, so always `cast()` / `try_cast()` before numeric comparison or arithmetic. See [references/query-analysis.md](references/query-analysis.md) for scan semantics.

```sql
* | set session mode=scan; SELECT api, count(1) AS pv FROM log GROUP BY api
```

---

### Step 4: Resolve the Time Range

Generate `--from` / `--to` as **Unix timestamps in seconds** before building the CLI command. `--from` is inclusive and `--to` is exclusive.

Choose one of three input patterns:

1. **Relative time** — user says "recent / last N minutes|hours|days".
2. **Natural-language absolute time without timezone** — normalize to `YYYY-MM-DD HH:MM:SS`, then parse using the machine's local timezone.
3. **Absolute time with explicit timezone** — parse using the customer-provided timezone or UTC offset.

**1. Relative time**

```bash
# recent 15 minutes
FROM=$(($(date +%s) - 900))
TO=$(date +%s)
```

**2. Natural-language absolute time without timezone**

If the user gives a date/time but no timezone, use the machine's local timezone. First normalize natural language such as `2026年3月13日12点` to `2026-03-13 12:00:00`, then parse it as local time.

```bash
# Example: 2026年3月13日12点 -> 2026-03-13 12:00:00

# Linux (GNU date): local timezone
FROM=$(date -d "2026-03-13 12:00:00" +%s)

# macOS (BSD date): local timezone
FROM=$(date -j -f "%Y-%m-%d %H:%M:%S" "2026-03-13 12:00:00" +%s)
```

For a time range such as "2026年3月13日12点到13点", compute both endpoints the same way. For a single point-in-time request, infer a practical window from the user's intent; if unclear, ask for the range before executing.

**3. Absolute time with explicit timezone**

To convert a local date/time to a Unix timestamp: parse the input as UTC with `date -u`, then **subtract** the timezone's UTC offset in seconds.

Formula: `unix_ts = date_utc_parse(input) − (UTC_offset_hours × 3600)`

```bash
# Example: 2025-01-15 10:30:00 Beijing Time (UTC+8)
# Beijing is UTC+8, so subtract 8 × 3600 = 28800

# Linux (GNU date)
FROM=$(( $(date -u -d "2025-01-15 10:30:00" +%s) - 28800 ))

# macOS (BSD date)
FROM=$(( $(date -u -j -f "%Y-%m-%d %H:%M:%S" "2025-01-15 10:30:00" +%s) - 28800 ))
```

```bash
# Example: 2025-01-15 10:30:00 New York Time (UTC-5)
# New York is UTC-5, so subtract -5 × 3600 = subtract -18000 = add 18000

# Linux (GNU date)
FROM=$(( $(date -u -d "2025-01-15 10:30:00" +%s) + 18000 ))

# macOS (BSD date)
FROM=$(( $(date -u -j -f "%Y-%m-%d %H:%M:%S" "2025-01-15 10:30:00" +%s) + 18000 ))
```

Common UTC offsets (value to subtract):

| Timezone         | UTC offset hours | Seconds to subtract |
|------------------|------------------|---------------------|
| Beijing (UTC+8)  | +8               | `28800`             |
| Tokyo (UTC+9)    | +9               | `32400`             |
| London (UTC)     | 0                | `0`                 |
| New York (UTC-5) | -5               | `-18000`            |

---

### Step 5: Execute via `get-logs-v2`

Use `aliyun sls get-logs-v2` to execute queries. Run `aliyun help sls get-logs-v2` to see CLI parameter usage; read [references/related-apis.md](references/related-apis.md) for detailed API parameter descriptions.

**Required CLI flags:**

- `--project`: SLS project name
- `--logstore`: Logstore name within the project
- `--from`: Start of time range, **Unix timestamp in seconds** (inclusive)
- `--to`: End of time range, **Unix timestamp in seconds** (exclusive)
- `--query`: Statement built in Step 3

Pagination works differently depending on whether the statement has a `|`:

#### 5.1 Index-search only — paginate with `--offset` / `--line`

```bash
aliyun sls get-logs-v2 \
  --project my-project --logstore my-logstore \
  --from 1740000000 --to 1740003600 \
  --query '* and "payment failed" and status: "500"' \
  --line 100 --offset 0 --reverse true
```

- Pagination: `--line` is page size (`1–100`, required); `--offset` is the start row (optional, default `0`).
- Ordering: `--reverse true` returns newest first; default `false` is oldest first.

#### 5.2 With SQL — paginate with `LIMIT` inside the statement

```bash
aliyun sls get-logs-v2 \
  --project my-project --logstore my-logstore \
  --from 1740000000 --to 1740003600 \
  --query 'status: "500" | SELECT request_uri, count(*) AS cnt FROM log GROUP BY request_uri ORDER BY cnt DESC LIMIT 20'
```

- SQL default result cap is **100 rows**. To get more results or paginate:
  - `LIMIT count` — raise the cap (e.g., `LIMIT 500` returns up to 500 rows)
  - `LIMIT offset, count` — paginate (e.g., `LIMIT 20, 20` for rows 21–40; `LIMIT 40, 20` for rows 41–60). Max offset+count is 1000000.
  - **Do not** use `LIMIT count OFFSET offset` syntax — it is **not supported**. Always use `LIMIT offset, count`.
- Ordering: use `ORDER BY <field> DESC/ASC` to sort.

**Result completeness check:** every response contains `meta.progress`. If it is `Incomplete`, **re-issue the same request** until it returns `Complete`.

---

### Step 6: Extract Data from the Response

`get-logs-v2` returns:

```json
{
  "meta": { "progress": "Complete", "count": 10, ... },
  "data": [ { "field1": "value1", ... }, ... ]
}
```

| Field | Meaning |
|-------|---------|
| `meta.progress` | `Complete` or `Incomplete` (see Step 5) |
| `meta.count` | Number of rows returned |
| `data` | Array of log entries or aggregation rows; may contain `__time__` (Unix seconds, string) |

Use `jq` (preferred) or `--cli-query` (JMESPath) to extract the fields the user needs:

| Extract | `jq` | `--cli-query` (JMESPath) |
|---------|------|--------------------------|
| Data rows | `\| jq '.data'` | `--cli-query 'data'` |
| Progress | `\| jq '.meta.progress'` | `--cli-query 'meta.progress'` |
| Row count | `\| jq '.meta.count'` | `--cli-query 'meta.count'` |
| Specific fields | `\| jq '.data[] \| {LogStore, read_mb}'` | `--cli-query 'data[].{LogStore: LogStore, read_mb: read_mb}'` |

---

### Step 7: Present the CLI Command and Results

**CLI command** — always show the full, copy-paste-ready `aliyun sls get-logs-v2 ...` command. Redact any AK/SK. If the query was not executed (write / explain scenario), present the command the user should run.

**Results** — when a query was executed, use Step 6 to extract `data` and format according to the user's request (table, list, summary, etc.). Append one sentence explaining the query mode choice.

---

## Cleanup

**Whether operations succeed or fail, you MUST disable AI-Mode before ending the session:**

```bash
aliyun configure ai-mode disable
```

---

## Global Rules

- **Always prefer Index search for fastest raw-log retrieval, and use Index search + SQL for analysis or field projection.**
- **When the user only needs specific fields, use `SELECT` to project them** rather than fetching full raw logs — this reduces network overhead. Requires `doc_value: true` on the target fields (confirmed in Step 1).
- **Do not** hard-code `__time__` filters — pass time range via `--from` / `--to`.
- **Deprecated API**: never call `get-logs`; always use `get-logs-v2`.

---

## Troubleshooting

When the user reports "no data", "wrong result", or a CLI error, walk through the checklist in this exact order:

1. **Time range** — wrong `--from`/`--to`? Milliseconds instead of seconds? Recent writes still indexing?
2. **Index configuration** — field index missing? Full-text index off? Target field not in `keys`?
3. **Field type / statistics** — range query on a `text` field? SQL on a field without `doc_value`?
4. **Syntax** — mixed SQL and SPL? Leading `*` in fuzzy match? SPL string escaping?
5. **Mode choice** — scanning when an index-based query would do? Aggregating in SPL instead of SQL?
6. **Completeness** — `meta.progress = Incomplete`, caller did not retry (see Step 5).
7. **ProjectNotExist** — region or endpoint is wrong. See [references/regions.md](references/regions.md).
8. **Network failure** (timeout, connection refused) — try switching to internal endpoint. See [references/regions.md](references/regions.md).

For the full catalog of failure modes and error codes, see [references/troubleshooting.md](references/troubleshooting.md) and the `Common Errors` table in [references/related-apis.md](references/related-apis.md).

---

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/query-analysis.md](references/query-analysis.md) | Mode decision, index-search / SQL rules, scan semantics |
| [references/spl-guide.md](references/spl-guide.md) | SPL pipeline syntax, common commands, field handling |
| [references/functions-guide.md](references/functions-guide.md) | Function categories, SQL/SPL differences, templates |
| [references/troubleshooting.md](references/troubleshooting.md) | "No data / wrong result / error" playbook |
| [references/related-apis.md](references/related-apis.md) | `GetLogsV2` and `GetIndex` API & CLI reference |
| [references/ram-policies.md](references/ram-policies.md) | Minimum and complete RAM policies |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI install, auth modes, profiles |
| [references/regions.md](references/regions.md) | Region / endpoint configuration, internal endpoint, ProjectNotExist troubleshooting |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | CLI invocation acceptance tests |
| `references/query_analysis/*.yaml` · `references/spl/*.yaml` · `references/functions/*.yaml` | Source-of-truth YAMLs bundled with this skill |
