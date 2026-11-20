# RAM permissions for SLS queries

## Required permissions

Grant the actions needed for the requested operation and its required reads.
API names and RAM actions are not always identical.

| API | CLI Command | RAM action | Resource | Description |
|-----|-------------|------------|---------------------|-------------|
| GetLogsV2 | `query` | `log:GetLogStoreLogs` | `acs:log:<region-id>:<account-id>:project/<project-name>/logstore/<logstore-name>` | Query logs from a Logstore using index query, SQL analysis, or SPL pipelines |
| GetIndex | `index get` | `log:GetIndex` | `acs:log:<region-id>:<account-id>:project/<project-name>/logstore/<logstore-name>` | Get the index configuration of a Logstore, used to verify index settings before running queries or analysis |
| GetProject | `project get` | `log:GetProject` | `acs:log:<region-id>:<account-id>:project/<project-name>` | Get project metadata; supports cross-region discovery to locate a project's actual region |

Placeholders in the resource ARN:

- `<region-id>` -- SLS region, e.g. `cn-hangzhou`. Use `*` to match all regions.
- `<account-id>` -- Alibaba Cloud account ID (UID). Use `*` to match all accounts.
- `<project-name>` -- SLS Project name. Use `*` to match all projects.
- `<logstore-name>` -- Logstore name. Use `*` to match all Logstores under the project.

In the examples below, `regionId` and `accountId` are left as `*` for simplicity. Replace `<project-name>` and `<logstore-name>` with your real values, or use `*` to broaden the scope.

## Minimum RAM policy

Use this policy when only `query` is used.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "log:GetLogStoreLogs"
      ],
      "Resource": "acs:log:*:*:project/<project-name>/logstore/<logstore-name>"
    }
  ]
}
```

## Complete RAM policy

Use this policy when both `query` and `index get` are used.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "log:GetLogStoreLogs",
        "log:GetIndex"
      ],
      "Resource": "acs:log:*:*:project/<project-name>/logstore/<logstore-name>"
    }
  ]
}
```

**Example: Allow All Logstores Under a Project**

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "log:GetLogStoreLogs",
        "log:GetIndex"
      ],
      "Resource": "acs:log:*:*:project/my-project/logstore/*"
    }
  ]
}
```

**Example: Allow All Projects**

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "log:GetLogStoreLogs",
        "log:GetIndex"
      ],
      "Resource": "acs:log:*:*:project/*"
    }
  ]
}
```

## System policies

| Policy | Description |
|-------------|-------------|
| `AliyunLogReadOnlyAccess` | Read only access to all aliyun log resource |

## Principle of least privilege

It is recommended to select permissions based on actual needs following the principle of least privilege:

1. **Action Scope**: Prefer the Minimum RAM Policy when your use case only involves querying logs, and grant `log:GetIndex` only when your workflow needs to read index configuration.
2. **Resource Scope**: Prefer to narrow the `Resource` field to specific projects and Logstores whenever possible.

System policies grant broader access than an operation-specific policy.

## Permission errors

On an authorization failure, report the failed operation, denied action and resource,
and request ID when available. An access failure does not mean the resource is absent.
Do not switch profiles or broaden permissions unless the user requests that change.
Follow the [credential safety rules](../../SKILL.md#safety-rules).
