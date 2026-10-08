# SLS commands and connection options

Use the scripts from the skill directory after completing [CLI
setup](../cli-installation-guide.md) and checking the required [RAM
permissions](../ram-policies.md). Cloud commands accept optional `--profile` and
`--endpoint` alongside `--region` and `--project`:

```sh
python3 scripts/sls.py dashboard-get --region cn-hangzhou --project example-project --name example-dashboard --profile production --endpoint https://cn-hangzhou-intranet.log.aliyuncs.com
```

## Connection options

- `--profile` selects an existing Alibaba Cloud CLI profile.
- `--aliyun` selects the CLI executable, such as `--aliyun "$HOME/.local/bin/aliyun"`
  for an installation in your own directory. Use the same path for doctor and
  subsequent cloud commands.
- `--endpoint` selects the SLS service address, including intranet addresses. It does
  not change the Project/Region or a subscription's notification URL.
- These options apply to resource reads, query verification, publishing, readback
  and online subscription operations. Offline commands do not need them.
- For `--endpoint`, supply a service host or HTTP(S) base URL without an API path,
  query string or embedded credentials.

Publish/delete and subscription mutations make no cloud request without `--execute`.

## Operations

Standard SLS CLI command names use kebab-case. Use `--body-file` for complete
Dashboard JSON when calling create/update directly.

| Capability | SLS CLI commands |
| --- | --- |
| Logstores | list-log-stores, get-log-store, get-index |
| Metricstores | list-metric-stores, get-metric-store |
| StoreViews | list-store-views, get-store-view, get-store-view-index |
| Queries | get-logs-v2 |
| Dashboards | list-dashboard, get-dashboard, create-dashboard, update-dashboard, delete-dashboard |

For metric StoreView queries and Report subscriptions, use the skill's commands with
the [optional Python dependencies](../cli-installation-guide.md#python-dependencies) installed.

Resource lists return the requested offset/size page. Subscription listing fetches
all matching pages.

## Queries and limits

GetLogsV2 uses Unix seconds with an exclusive end. `meta.progress=Complete` means
execution completed. A row limit can still bound the result.

For SQL, put `LIMIT` in the statement. For raw search, the helper requests at most
100 records in one call. `requestedLimit` and `effectiveLimit` distinguish the
requested bound from the bound used for that call; `limitReached` flags a full result
at that bound. It does not prove more records exist. `truncated` indicates additional
returned rows were omitted from the helper's `rows` output.

A named log StoreView uses `get-logs-v2` with its name in `--logstore`. Its index is
read with `get-store-view-index --name VIEW_NAME`, not `get-index`.

Metric StoreViews support instant/range PromQL, metric-name lookup and
label-series sampling. Range end is inclusive. Metadata lookups provide bounded
samples rather than complete historical inventories. See [StoreView](storeview.md).

## Report subscriptions

Report operations are ListJobs, CreateJob, UpdateJob and DeleteJob. ListJobs selects
`jobType=Report` and `resourceProvider=DASHBOARD_ID`. These API names are distinct
from CLI command names; JSON fields keep their documented spelling.

Use the [subscription workflow](../integrations/subscriptions.md) for commands,
configuration, scheduling and delivery limits.

## Product references

- [GetLogsV2](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogsv2)
- [GetStoreViewIndex](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getstoreviewindex)
- [CreateDashboard](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createdashboard)
- [Metric StoreView queries](https://help.aliyun.com/zh/sls/cross-metricstore-query)
