# RAM Policies - SLS Alerting

These policies apply to the CLI caller. For the optional query role and
`ram:PassRole`, see [cross-account queries](rules/queries/cross-account.md).

## Required Permissions

API names and RAM actions are not always identical.

| API | CLI Command | RAM Action | Resource Permission |
| --- | --- | --- | --- |
| ListAlerts | `list-alerts` | `log:ListAlerts` | `*`; see scope note below |
| GetAlert | `get-alert` | `log:GetAlert` | `*` |
| CreateAlert | `create-alert` | `log:CreateAlert` | `*` |
| UpdateAlert | `update-alert` | `log:UpdateAlert` | `*` |
| EnableAlert | `enable-alert` | `log:EnableAlert` | `*` |
| DisableAlert | `disable-alert` | `log:DisableAlert` | `*` |
| DeleteAlert | `delete-alert` | `log:DeleteAlert` | `*` |
| ListResourceRecord | `list-resource-record` | `log:ListResourceRecords` | Resource ARN |
| GetResourceRecord | `get-resource-record` | `log:GetResourceRecord` | Resource ARN |
| CreateResourceRecord | `create-resource-record` | `log:CreateResourceRecord` | Resource ARN |
| UpdateResourceRecord | `update-resource-record` | `log:UpdateResourceRecord` | Resource ARN |
| DeleteResourceRecord | `delete-resource-record` | `log:DeleteResourceRecord` | Resource ARN |
| GetProject | `get-project` | `log:GetProject` | Project ARN |
| GetIndex | `get-index` | `log:GetIndex` | Logstore ARN |
| GetLogsV2 | `get-logs-v2` | `log:GetLogStoreLogs` | Logstore ARN |

ARN forms (replace angle-bracket placeholders with actual values):

- Project: `acs:log:<region-id>:<account-id>:project/<project-name>`.
- Logstore: `acs:log:<region-id>:<account-id>:project/<project-name>/logstore/<logstore-name>`.
- Resource: `acs:log:*:<account-id>:resource/<resource-name>`. Use a fixed
  [resource name](notifications/api/resource-records.md#scope-and-envelope), such as
  `sls.common.user`. This scopes the namespace, not an individual record.

### Alert authorization scope

The alert actions above follow the [SLS API authorization catalog](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-ram).
It lists `*` for individual rule operations. For ListAlerts, it lists
`acs:log:<region-id>:<account-id>:project/<project-name>/alert/*`, while the
[ListAlerts API reference](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-listalerts)
lists `*`. The examples below use the API reference's scope; they do **not**
restrict rule access to one Project, even when the command uses `--project`.

The [alert authorization guide](https://help.aliyun.com/zh/sls/authorized-ram-user-operation-alarm)
also documents Job actions, such as `log:GetJob` and `log:ListJobs`, on
`acs:log:*:*:project/<project-name>/job/*`. If a denial names a Job action,
use that guide and the actual denied resource; do not assume the Alert and Job
actions are interchangeable or grant both sets automatically.

ResourceRecord action names and resource scopes are documented in the
[resource access-control guide](https://www.alibabacloud.com/help/en/sls/fine-grained-resource-control-using-resource-groups-41)
and the [official resource-management policy](https://help.aliyun.com/zh/ram/developer-reference/aliyunccmanagedlogrolepolicy).
`ListResourceRecord` requires **`log:ListResourceRecords`**; the RAM action
uses the plural `Records`.

## Minimum RAM Policy

For listing and inspecting rules only. Remove `log:ListAlerts` if the caller
only gets a known rule ID. This minimizes actions; its resource scope is broad
as described above.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:ListAlerts", "log:GetAlert"],
      "Resource": "*"
    }
  ]
}
```

## Complete Rule Management Policy

For the seven rule lifecycle APIs. Notification resources, query validation,
runtime roles, and Project/Logstore provisioning are outside this policy.
Remove writes the caller does not need, especially deletion.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "log:ListAlerts",
        "log:GetAlert",
        "log:CreateAlert",
        "log:UpdateAlert",
        "log:EnableAlert",
        "log:DisableAlert",
        "log:DeleteAlert"
      ],
      "Resource": "*"
    }
  ]
}
```

## Optional Notification Resource Permissions

For reading and reusing records in one namespace. Add a Resource ARN for each
needed namespace; do not replace it with `resource/*` merely for convenience.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:ListResourceRecords", "log:GetResourceRecord"],
      "Resource": "acs:log:*:<account-id>:resource/<resource-name>"
    }
  ]
}
```

For resource management, add only the required write actions from the table:
`log:CreateResourceRecord`, `log:UpdateResourceRecord`, or
`log:DeleteResourceRecord`.
These permissions apply to all records in the selected namespace, including
records shared by rules in other Projects.

## Optional Query Validation Permissions

For optional source-query validation by the CLI caller.
This does not grant the scheduled rule's runtime identity access.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:GetIndex", "log:GetLogStoreLogs"],
      "Resource": "acs:log:<region-id>:<account-id>:project/<project-name>/logstore/<logstore-name>"
    }
  ]
}
```

Add `log:GetProject` on the Project ARN only when metadata discovery is needed.
Query scopes refer to the data source, which can differ from the rule's Project.

## System Policies

The [official alert authorization guide](https://help.aliyun.com/zh/sls/authorized-ram-user-operation-alarm)
provides these broader alternatives:

| Policy Name | Scope |
| --- | --- |
| `AliyunLogReadOnlyAccess` | Read-only access across SLS resources. |
| `AliyunLogFullAccess` | Full SLS access, including operations beyond alerting. |

## Principle of Least Privilege

1. Grant actions for the requested operation and its required reads only.
2. Restrict account, Project, Logstore, and resource namespace where supported;
   a CLI target does not restrict a policy containing `Resource: "*"`.
3. On `Unauthorized`, report the denied action, resource, profile, and operation.
   Stop that operation; an access failure does not mean the object is absent.
   Do not switch profiles or create or broaden RAM policies unless the user
   explicitly requests that change.
