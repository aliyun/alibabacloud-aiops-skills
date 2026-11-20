# Region and endpoint configuration

## Region

For CLI commands, region selection uses `--region` first, then the selected
profile's region, then fallback environment values. Use an override for the task
without changing saved profile settings.

| Operation | Target Project and region |
| --- | --- |
| Query and alert-history reads | Project and region containing the requested data; these can differ from the alert rule or dashboard location. |
| Index operations | Project and region owning the target Logstore. |
| Alert rules | Owning Project and its region; query `region` and `project` describe the data source. |
| Dashboard operations | Destination dashboard's Project and region. |
| Subscription management | Project and region owning the dashboard and subscription. |
| ResourceRecords | Global account resources: use `--region cn-shanghai` by default, without `--project`. |

## Endpoint

Without an endpoint override, the CLI selects a public SLS endpoint from the region.
An override changes the request address without replacing the signing region. Use a
service host such as `cn-hangzhou.log.aliyuncs.com`, rather than a Project-prefixed host.

### Internal access

When internal access is needed and the caller can reach the target region's
internal network, use `--endpoint <REGION_ID>-intranet.log.aliyuncs.com`.
Keep the target Project and region unchanged.

## Cross-region discovery

If the Project's region is unknown, or a request reports `ProjectNotExist`,
check the Project name and selected account, then use cross-region discovery
when the region needs verification.

This request requires `log:GetProject` permission and a plugin supporting
`--cross-region`. It is available only through the `cn-zhangjiakou` endpoint:

```bash
aliyun sls project get \
  --project PROJECT_NAME \
  --cross-region true \
  --region cn-zhangjiakou \
  --endpoint cn-zhangjiakou.log.aliyuncs.com
```

Use the returned `region` for operations on that Project.
Use `internetEndpoint` for public access or `internalEndpoint` when internal
access is needed and reachable. Keep any explicit endpoint override consistent
with the target location and the user's routing requirements.

`cn-zhangjiakou` is the discovery endpoint; it does not replace the Project's
actual region for subsequent operations.

See [GetProject](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getproject)
for metadata fields and [capability permissions](troubleshooting.md#capability-specific-troubleshooting) for access requirements.

Global ResourceRecords keep their operation-specific route; they do not use the
discovered Project's region.
