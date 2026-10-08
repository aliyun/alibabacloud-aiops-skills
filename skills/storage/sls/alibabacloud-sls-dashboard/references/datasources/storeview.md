# StoreView

Use an existing named StoreView over log or metric stores. This workflow does not
create views. Preserve the view's project, region, name and type; member metadata
does not authorize redirecting queries to a member store.

Log views support log querying/analysis and predefined processing. Metric views
support PromQL; official documentation excludes SQL and predefined processing for
metric views.

## Discovery and queries

- Use list/describe to find and inspect existing views.
- Log view index discovery uses get-store-view-index --name VIEW_NAME, not the
  physical Logstore get-index operation. It reads indexes[] and storeViewErrors[],
  preserving member source/field differences without inferring uniform indexing.
- Named log views use get-logs-v2 with the view name in --logstore for discovery
  sampling and query verification. Query results, saved facts and dashboard JSON
  retain type=logstore_storeview.
- Metric view instant/range queries, metric names and label series use the documented
  metric query interface. Install the [optional Python dependencies](../cli-installation-guide.md#python-dependencies)
  and select the required profile.
  Metadata lookups follow the documented lookback windows, rather than providing
  arbitrary historical inventories.

For example, from the skill root:

    python3 scripts/sls.py query --type logstore_storeview --region REGION --project PROJECT --name VIEW_NAME --from START --to END --language sql --query '* | select count(*) as requests'

The equivalent query uses get-logs-v2 with --project PROJECT --logstore VIEW_NAME,
the given time window and unchanged query. SQL row limits belong in SQL; raw
search uses the normal line/offset parameters. A view query failure is returned
as-is without retrying against member stores.

Do not combine incompatible field types, ignore failed members or widen access.
Report unverified query or control behavior; JSON validation does not verify
filter or Adhoc behavior on a view.

## MetricsQL StoreView entries

`metricsql_storeview` is a SQL-mode identifier found in saved Dashboard JSON.
Its `project`, `logstore` and `region` locate the view; `logstore` is the view name,
not a member Metricstore. A non-empty `tokenQuery` takes precedence over `query`.
The SQL text determines returned columns, limits and any embedded PromQL step;
query-level `interval` and `limit` do not replace those SQL settings.

This skill does not generate or execute that mode. Use `metricstore_storeview`
for supported metric-view queries; preserve the identity of existing entries when
reviewing JSON. See [tool support](overview.md#other-dashboard-json-sources).

Official sources:
- [Overview](https://help.aliyun.com/zh/sls/dataset-storeview-overview)
- [Log views](https://help.aliyun.com/zh/sls/cross-logstore-query-and-analysis)
- [Metric views and HTTP API](https://help.aliyun.com/zh/sls/cross-metricstore-query)
