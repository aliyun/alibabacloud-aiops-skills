# Query and analysis

For operation-specific access, see [RAM permissions](ram-policies.md).

## Query entry points

Use `aliyun sls query` for Logstores, MetricStores, and StoreViews.
Pass the target's name with `--logstore` and select the query syntax for its type:

| Resource | Further reading |
| --- | --- |
| Logstore | Choose a mode below; [execution examples](query-execution.md#logstore). |
| MetricStore | [Metric query modes and syntax](metric-store/README.md); [execution examples](query-execution.md#metricstore). |
| StoreView | Choose log or metric syntax according to the view type; [execution examples](query-execution.md#storeview). |

For native PromQL, use `aliyun sls promql query` or `promql range`;
see [PromQL execution](query-execution.md#promql) and [expressions](metric-store/promql.md).

## Typical online query steps

The following steps are for reference.

### 1. Understand fields and indexes

Index configuration explains which fields can be searched or analyzed and how text is matched.
For a Logstore, `aliyun sls index get` returns the current configuration. For a log-type
StoreView, `aliyun sls store-view get-index` returns source configurations in `indexes[]`.

| Configuration | Meaning |
| --- | --- |
| `line` | Full-text matching rules across log fields. |
| `keys` | Field indexes with types and matching rules; `doc_value: true` enables indexed SQL analysis. |
| `line.auto_text_keys` | Automatically discovered `text` field indexes with analytics enabled, even when absent from `keys`. |

Unqualified searches cover indexed `text` fields and any full-text index; field-qualified
searches use the corresponding field indexes.
For further details, see [index inspection](../index/manage-index-config.md#read-an-index)
and [index query behavior](../index/index-configuration.md#query-behavior).
MetricStore queries use the [metric schema and syntax](metric-store/README.md).

### 2. Choose a query mode

For Logstores, the preference is **index search → SQL analysis → SPL → SQL SCAN**, according
to the task and available indexes.

| Mode | Suitable tasks | Example |
| --- | --- | --- |
| [Index search](index-search.md) | Filter and retrieve raw logs using indexes. | `status:500 and reqType:write and not "bussiness"` |
| [SQL analysis](sql/README.md) | Aggregate, sort, select columns, or perform other analytical operations on fields with analytics enabled. | `status:200 \| SELECT sum(Inflow) AS inflow, method GROUP BY method LIMIT 1000` |
| [SPL](spl/README.md) | Extract, transform, and filter fields through a pipeline; can use field indexes when available. | `status:200 \| where ClientIp = '192.168.1.1' \| project method, ClientIp` |
| [SQL SCAN](sql/sql-scan.md) | Analyze fields without field indexes using SQL scan analysis. | `status:200 \| set session mode=scan; SELECT api, count(*) AS pv GROUP BY api` |

If required field indexes are missing and the data volume is small, you may ask the user whether
to use scanning. Use scanning when the user requests or approves it; see the mode references for
scan limits. Prefer SPL over SQL SCAN when both fit the task.

For MetricStores, choose among PromQL, SQL analysis, and PromQL + SQL analysis in the
[metric query reference](metric-store/README.md).

### 3. Build the statement

Filters before the first `|` use indexes to reduce the data passed to SQL or SPL. Prefer this
part for conditions expressible as index search; use `*` when no filter applies.

Read the selected mode's reference for syntax. The [SQL function navigation](sql/README.md#high-frequency-functions)
and [SPL reference](spl/README.md) provide links to detailed functions and commands.

### 4. Choose the time range

Interpret the requested range in the user's timezone, or the system timezone if none
was specified. The start is inclusive and the end exclusive.

### 5. Execute the query

See [query execution](query-execution.md) for command examples. CLI API calls use the
[shared User-Agent](../../SKILL.md#observability).

### 6. Interpret the response

With `--format json`, `query` returns rows in `data` and query information in `meta`, for example:

```json
{"meta":{"progress":"Complete","count":1},"data":[{"total":"42"}]}
```

- `meta.progress`: `Complete` means the query result is precise; other values mean it is
  imprecise. The query's result limit still applies, so `Complete` does not imply that all
  matching rows have been returned.
- `meta.count`: the number of rows reported for this response, not the total matching log count.
- `data`: raw logs or analysis result rows. Numeric values can be represented as JSON strings.

PromQL commands have [different result structures](query-execution.md#metricstore-result-fields).

## Console query links

To generate a SLS Logstore console query link for human access, use [the query-link script](query-link.md).

## Troubleshooting

For command, authentication, permission, or connection errors, see
[common troubleshooting](../troubleshooting.md).
For query syntax, matching, indexes, and result precision, see
[query troubleshooting](troubleshooting.md).
