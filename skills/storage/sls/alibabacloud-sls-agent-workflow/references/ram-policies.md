# RAM Policies - SLS Agent Workflow

These permissions apply to the CLI caller for this skill's direct resource-creation and sample-log writes. Index management, queries, collection setup, and alerting use the selected specialist's own RAM permission documentation.

## Required permissions

Grant only the actions needed for the requested steps. Metadata reads are needed only when checking existing resources or verifying creation.

| API | CLI command | RAM action | Resource scope |
| --- | --- | --- | --- |
| [CreateProject](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createproject) | `create-project` | `log:CreateProject` | Project ARN |
| [CreateLogStore](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createlogstore) | `create-log-store` | `log:CreateLogStore` | Logstore ARN |
| PutLogs | `put-json-logs` | `log:PostLogStoreLogs` | Logstore ARN |
| [GetProject](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getproject) | `get-project` | `log:GetProject` | Project ARN; optional metadata read |
| [GetLogStore](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogstore) | `get-log-store` | `log:GetLogStore` | Logstore ARN; optional metadata read |

API names and RAM actions can differ: JSON log writes use `log:PostLogStoreLogs`, as documented in the [SLS write-permission policy](https://help.aliyun.com/zh/sls/log-service-ram-access-control-permissions-configuration).

Replace placeholders in these ARN forms with the target region, owning account, and resource names:

- Project: `acs:log:<region-id>:<account-id>:project/<project-name>`.
- Logstore: `acs:log:<region-id>:<account-id>:project/<project-name>/logstore/<logstore-name>`.

## Scoped policy example

For creating and inspecting one Project and Logstore, then writing sample logs:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:CreateProject", "log:GetProject"],
      "Resource": "acs:log:<region-id>:<account-id>:project/<project-name>"
    },
    {
      "Effect": "Allow",
      "Action": [
        "log:CreateLogStore",
        "log:GetLogStore",
        "log:PostLogStoreLogs"
      ],
      "Resource": "acs:log:<region-id>:<account-id>:project/<project-name>/logstore/<logstore-name>"
    }
  ]
}
```

Remove creation actions when reusing resources and metadata-read actions when they are not needed. Writing to an existing Logstore requires only `log:PostLogStoreLogs` for the write itself. This policy does not grant index, query, collection, alert, deletion, or RAM administration permissions.

## Permission failures

On `Unauthorized` or `AccessDenied`, report the denied action and resource when available, the failed operation, and the request ID. Stop the affected operation; a permission failure does not mean the resource is absent. Do not switch identities or broaden RAM policies automatically. For an operation performed by a specialist, follow that specialist's permission guidance.
