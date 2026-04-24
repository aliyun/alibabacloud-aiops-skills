# Region & Endpoint Configuration

## Region

By default, the region is read from the active profile configured via `aliyun configure`. To override it for a single command, add `--region <region-id>`:

```bash
aliyun sls get-logs-v2 --region cn-shanghai --project my-project ...
```

## Endpoint

By default, the CLI accesses SLS through the **public endpoint**. To use the **internal (intranet) endpoint**, specify `--endpoint` to override the default endpoint generated from `region`:

```bash
aliyun sls get-logs-v2 --endpoint cn-hangzhou-intranet.log.aliyuncs.com --project my-project ...
```

SLS internal endpoint format: `<region-id>-intranet.log.aliyuncs.com`

Examples:

- `cn-hangzhou-intranet.log.aliyuncs.com`
- `cn-shanghai-intranet.log.aliyuncs.com`
- `us-west-1-intranet.log.aliyuncs.com`

**`--endpoint` takes priority over `--region`.** When `--endpoint` is set, `--region` is ignored.

## When to use the internal endpoint

If the public endpoint is unreachable (timeout, connection refused), try switching to the internal endpoint. This is common when running inside an Alibaba Cloud VPC.

## Common error: ProjectNotExist

If a call returns `ProjectNotExist`, the project likely exists in a different region. Ask the user to confirm the correct region or endpoint for their project.
