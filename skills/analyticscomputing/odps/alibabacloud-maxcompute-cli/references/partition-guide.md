> Loaded on demand — partition-discovery commands and filter formats. Skip unless the agent is querying a partitioned table and needs the latest partition value or the right filter shape.

# Partition query strategy

## When to read this file

Read this file when working with partitioned MaxCompute tables — before constructing SQL with partition filters, when `meta describe` shows `partition_columns`, or when the user asks about "latest data" or "recent records".

## Partition columns

Names such as `ds`, `dt`, `pt`, `hh`, or `region` do not define a partition's
business meaning, format, or completeness. Determine snapshot, incremental,
and completeness semantics from table or column comments, documented business
context, or the user.

## Discover partitions with `aliyun maxc`

### Step 1: Check whether the table is partitioned

```bash
aliyun maxc meta describe <table> --json
```

Inspect `data.table.partition_columns` in the response. If empty or absent, no
partition filter is needed. Add `LIMIT` only when the requested output is a
preview or otherwise bounded.

### Step 2: List available partition values

```bash
aliyun maxc meta partitions <table> --json
```

Inspect the returned partition values and metadata to understand the visible
range and format. Large tables can have many partitions, so use the command's
runtime help to check for available limiting options before requesting a broad
listing.

### Step 3: Get the latest partition

```bash
aliyun maxc meta latest-partition <table> --json
```

Returns the latest visible partition according to the CLI's partition ordering.
Use the exact returned key and value format; do not assume `YYYYMMDD` versus
`YYYY-MM-DD`.

### Step 4: Check data freshness

```bash
aliyun maxc meta freshness <table> --json
```

Returns a heuristic freshness assessment. The CLI first tries to derive a
reference time from parseable latest-partition values; if that fails, it can
fall back to table `updated_at`. It does not discover the table's actual refresh
schedule. Inspect `data.freshness.freshness_source`,
`data.freshness.status_thresholds`, and warnings before interpreting
`data.freshness.freshness_status`.

## Query patterns

### Preview the latest complete snapshot

Use this bounded-preview pattern only after table documentation or the user
confirms that one partition represents a complete snapshot. Resolve the preview
row count from the request before execution.

```bash
# 1. Get the latest partition value
aliyun maxc meta latest-partition <qualified-table> --json
# Response fields include:
# {"data":{"partition":{"latest_partition":"ds=20260415","latest_partition_values":{"ds":"20260415"},...}}}

# 2. Query using the returned key and value
aliyun maxc query "SELECT col1, col2 FROM <qualified-table> WHERE ds = '20260415' LIMIT <preview-row-count>" --json
```

### Preview a bounded date range

```bash
aliyun maxc query "SELECT col1, col2 FROM <qualified-table> WHERE ds >= '20260410' AND ds <= '20260415' LIMIT <preview-row-count>" --json
```

### Cross-partition aggregation

```bash
aliyun maxc query "SELECT ds, COUNT(1) AS cnt FROM <qualified-table> WHERE ds >= '20260401' AND ds <= '20260415' GROUP BY ds" --json
```

### Multi-level partition pruning

For tables with partitions like `(ds, hh)`:

```bash
aliyun maxc query "SELECT col1, col2 FROM <qualified-table> WHERE ds = '20260415' AND hh = '12' LIMIT <preview-row-count>" --json
```

Angle-bracket values are templates. Resolve them from verified metadata and the
user's request before execution; do not send unresolved placeholders.

## `MAX_PT()` guidance

`MAX_PT('table_name')` resolves the largest level-1 partition value. Use it only
when lexicographic ordering matches the table's intended recency order and the
selected level-1 partition is sufficient for the query.

### When `MAX_PT()` works well

- The table uses one partition level.
- The partition value's lexical order matches chronological or business order.
- Table documentation confirms that the largest visible partition is complete.

### When `MAX_PT()` is unreliable

- **Unconfirmed completeness**: The largest partition may still be loading.
- **Multi-level partitions**: `MAX_PT` only resolves the first partition level.
- **Specific historical dates**: You need a fixed date, not "whatever is latest"
- **Non-lexical recency**: The largest string value may not represent the intended latest period.
- **Incremental semantics**: One partition may not contain the complete result.

### CLI inspection

For ad hoc work, inspect `aliyun maxc meta latest-partition <table> --json`,
confirm its meaning, and use the returned literal in the partition filter.

## Partition ambiguity handling

When the user says "latest data" or "most recent records" and the partition semantics are unclear:

1. **Check `partition_columns[*].comment`** — the column comment may describe the semantics
2. **Check the table comment** via `meta describe` — it may describe the refresh pattern
3. **Sample partition values** with `meta partitions` — check if values look like dates, and whether they cover recent days
4. **Ask the user** if the above steps do not establish whether the table is a full snapshot or incremental

Do not execute a query whose partition range depends on unresolved snapshot or
incremental semantics. Ask the user, or stop after presenting a cost estimate
and query draft.

## Cost impact

Querying a partitioned table without a partition filter can scan every visible
partition.

- Use `aliyun maxc query cost "..." --json` before executing an unfamiliar,
  broad, or cross-partition query.
- Use the narrowest partition range that satisfies the user's request.
