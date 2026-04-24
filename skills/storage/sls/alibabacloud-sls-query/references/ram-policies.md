# RAM Policies - SLS Query Analysis

## Required Permissions

The following RAM permissions are required to execute the APIs used by this skill:

| API | CLI Command | API Action | Resource Permission | Description |
|-----|-------------|------------|---------------------|-------------|
| GetLogsV2 | `get-logs-v2` | `log:GetLogStoreLogs` | `acs:log:{#regionId}:{#accountId}:project/{#ProjectName}/logstore/{#LogstoreName}` | Query logs from a Logstore using index query, SQL analysis, or SPL pipelines |
| GetIndex | `get-index` | `log:GetIndex` | `acs:log:{#regionId}:{#accountId}:project/{#ProjectName}/logstore/{#LogstoreName}` | Get the index configuration of a Logstore, used to verify index settings before running queries or analysis |

Placeholders in the resource ARN:

- `{#regionId}` -- SLS region, e.g. `cn-hangzhou`. Use `*` to match all regions.
- `{#accountId}` -- Alibaba Cloud account ID (UID). Use `*` to match all accounts.
- `{#ProjectName}` -- SLS Project name. Use `*` to match all projects.
- `{#LogstoreName}` -- Logstore name. Use `*` to match all Logstores under the project.

In the examples below, `regionId` and `accountId` are left as `*` for simplicity. Replace `<project-name>` and `<logstore-name>` with your real values, or use `*` to broaden the scope.

## Minimum RAM Policy

Use this policy when only `get-logs-v2` is used.

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

## Complete RAM Policy

Use this policy when both `get-logs-v2` and `get-index` are used.

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

## Recommended System Policy

| Policy Name | Description |
|-------------|-------------|
| `AliyunLogReadOnlyAccess` | Read only access to all aliyun log resource |

## Principle of Least Privilege

It is recommended to select permissions based on actual needs following the principle of least privilege:

1. **Action Scope**: Prefer the Minimum RAM Policy when your use case only involves querying logs, and grant `log:GetIndex` only when your workflow needs to read index configuration.
2. **Resource Scope**: Prefer to narrow the `Resource` field to specific projects and Logstores whenever possible.
