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

If a call returns `ProjectNotExist`, the project likely exists in a different region. Two options:

1. Ask the user to confirm the correct region or endpoint for their project.
2. Use **cross-region discovery** (see below) to programmatically locate the project.

---

## Cross-Region Discovery

When `ProjectNotExist` is returned — or the user does not know which region a project belongs to — use `get-project` with `--cross-region true` to locate the project across all regions in a single call.

**Constraint:** This API is **only** available via the `cn-zhangjiakou` endpoint. Do not use any other endpoint with `--cross-region true`.

### Prerequisites

- **SLS plugin version** >= `0.5.2`. Upgrade if needed:

```bash
aliyun plugin update sls
```

- **RAM permission**: action `log:GetProject`, resource `acs:log:{#regionId}:{#accountId}:project/{#ProjectName}`.

### Usage

```bash
aliyun sls get-project \
  --project <project-name> \
  --cross-region true \
  --endpoint cn-zhangjiakou.log.aliyuncs.com  # fixed endpoint, cross-region query only available in cn-zhangjiakou
```

### Response (key fields)

| Field | Type | Description |
|-------|------|-------------|
| `region` | string | Region ID where the project actually resides, e.g. `cn-shanghai` |
| `internetEndpoint` | string | Public endpoint for the project, e.g. `cn-shanghai.log.aliyuncs.com` |

### Workflow After Discovery

Once the project is found, use the returned `internetEndpoint` as `--endpoint` in subsequent commands:

```bash
aliyun sls get-logs-v2 \
  --endpoint cn-shanghai.log.aliyuncs.com \
  --project <project-name> --logstore <logstore-name> \
  --from ... --to ... --query '...'
```

### When to Use

1. A CLI call returns `ProjectNotExist` and the user cannot confirm the region.
2. The user explicitly asks "which region is my project in?".
3. The configured `--region` / `--endpoint` does not match the project's actual location.

### Limitations

- Only the `cn-zhangjiakou` endpoint supports cross-region discovery.
- The command queries project metadata only — it does **not** return Logstore data.
- Network access to `cn-zhangjiakou.log.aliyuncs.com` must be available from the caller's environment.
