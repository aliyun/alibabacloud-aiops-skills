# Region & Endpoint Configuration

## Region

By default, use the configured region. Add `--region <region-id>` when the
operation targets a different region.

| Operation | Target |
| --- | --- |
| Alert rules | Owning Project and its region. The query's `region` and `project` describe the data source, not the rule's owner. |
| Query or alert-history reads | Project and region containing the requested data. |
| ResourceRecords | Global account resources: use `--region cn-shanghai` by default, without `--project`. |

Honor explicit routing overrides without changing global profile settings.

## Endpoint

The CLI selects a public endpoint from the region; normally omit `--endpoint`.
Use it only for an explicit endpoint override, such as internal access or the
discovery request below. It takes priority over `--region` and accepts a service
host, not a Project-prefixed host.

## When to Use the Internal Endpoint

When public access is unavailable and the caller can reach the region's internal
network, use `--endpoint <region-id>-intranet.log.aliyuncs.com`, keeping the same
target Project and region.

## Cross-Region Discovery

If the Project's region is unknown or a regional request reports
`ProjectNotExist`, use cross-region discovery:

```bash
aliyun sls get-project \
  --user-agent "$SLS_ALERT_USER_AGENT" \
  --project "$SLS_PROJECT" \
  --cross-region true --endpoint cn-zhangjiakou.log.aliyuncs.com
```

This operation requires a plugin supporting `--cross-region` and `log:GetProject`
permission. **Only the `cn-zhangjiakou` endpoint supports this discovery request**;
it is not the endpoint for subsequent rule or data operations.

For subsequent operations, use the returned `region`; add `--region` only if
it differs from the configured region. Let the CLI select the public endpoint,
or use `internalEndpoint` when internal access is needed.

See the [GetProject API reference](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getproject)
for Project metadata and [RAM policies](ram-policies.md) for permissions.
