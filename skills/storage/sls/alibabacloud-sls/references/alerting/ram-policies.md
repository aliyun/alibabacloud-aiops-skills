# RAM permissions for SLS alerting

These policies apply to the CLI caller. For the optional query role and
`ram:PassRole`, see [cross-account queries](rules/queries/cross-account.md).

## Required permissions

API names and RAM actions are not always identical.

| API | RAM action | Resource |
| --- | --- | --- |
| ListAlerts | `log:ListAlerts` | `*`; see scope note below |
| GetAlert | `log:GetAlert` | `*` |
| CreateAlert | `log:CreateAlert` | `*` |
| UpdateAlert | `log:UpdateAlert` | `*` |
| EnableAlert | `log:EnableAlert` | `*` |
| DisableAlert | `log:DisableAlert` | `*` |
| DeleteAlert | `log:DeleteAlert` | `*` |
| ListResourceRecord | `log:ListResourceRecords` | Resource ARN |
| GetResourceRecord | `log:GetResourceRecord` | Resource ARN |
| CreateResourceRecord | `log:CreateResourceRecord` | Resource ARN |
| UpdateResourceRecord | `log:UpdateResourceRecord` | Resource ARN |
| DeleteResourceRecord | `log:DeleteResourceRecord` | Resource ARN |
| GetProject | `log:GetProject` | Project ARN |
| GetIndex | `log:GetIndex` | Logstore ARN |
| GetLogsV2 | `log:GetLogStoreLogs` | Logstore ARN |

ARN forms (replace angle-bracket placeholders with actual values):

- Project: `acs:log:<region-id>:<account-id>:project/<project-name>`.
- Logstore: `acs:log:<region-id>:<account-id>:project/<project-name>/logstore/<logstore-name>`.
- Resource: `acs:log:*:<account-id>:resource/<resource-name>`. Use a fixed
  [resource name](notifications/api/resource-records.md#scope-and-envelope), such as
  `sls.common.user`. This scopes the namespace, not an individual record.

### Alert authorization scope

The rule-policy examples below grant account-wide access through `Resource: "*"`.
A command's `--project` selects its target; it does not narrow that permission.
See the [API authorization catalog](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-ram)
and [ListAlerts authorization](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-listalerts).

If an access denial names a Job action, use the denied action and resource with
[Job authorization](https://help.aliyun.com/zh/sls/authorized-ram-user-operation-alarm).
For ResourceRecord scopes, see the
[resource access-control guide](https://www.alibabacloud.com/help/en/sls/fine-grained-resource-control-using-resource-groups-41).

## Minimum RAM policy

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

## Complete rule management policy

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

## Optional notification resource permissions

For reading and reusing records in one namespace. Add a Resource ARN for each
needed namespace.

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

## Optional query validation permissions

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

## System policies

The [official alert authorization guide](https://help.aliyun.com/zh/sls/authorized-ram-user-operation-alarm)
provides these broader alternatives:

| Policy | Scope |
| --- | --- |
| `AliyunLogReadOnlyAccess` | Read-only access across SLS resources. |
| `AliyunLogFullAccess` | Full SLS access, including operations beyond alerting. |

## Principle of least privilege

1. Grant actions for the requested operation and its required reads only.
2. Restrict account, Project, Logstore, and resource namespace where supported;
   a CLI target does not restrict a policy containing `Resource: "*"`.

## Permission errors

On an authorization failure, stop the failed operation and report the failed operation, denied action and resource,
and request ID when available. An access failure does not mean the resource is absent.
Do not switch profiles or broaden permissions unless the user requests that change.
Follow the [credential safety rules](../../SKILL.md#safety-rules).
