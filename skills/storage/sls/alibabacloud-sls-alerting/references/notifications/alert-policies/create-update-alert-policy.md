# Create or update an alert policy

Read the existing policy before updates. Preserve routing, silence, inhibition,
and hierarchy settings unrelated to the requested change.

## Choose the processing behavior

- [Routing](#routing): select an action policy.
- [Notification grouping](notification-grouping.md):
  choose grouping keys and notification waits.
- [Inhibition and silence](#inhibition-and-silence): suppress notifications under
  the requested conditions.

### Routing

In `group_script`, `fire(action_policy=...)` selects an existing
[action policy](../action-policies/manage-action-policies.md). The same call sets
notification grouping. For a dynamic action policy, follow
[rule notification setup](../../rules/notifications/connect.md#advanced-mode)
to determine whether the rule supplies the action-policy ID and repeat wait.

### Inhibition and silence

`inhibit_script` defines relationships in which alerts suppress other alerts;
`silence_script` suppresses notifications matching silence conditions. Neither
disables rule evaluation. Leave these scripts empty unless the behavior is
requested; preserve existing values on unrelated updates.

The example below covers basic routing. For conditional routing, inhibition,
or silence syntax, use a verified policy or the
[official DSL reference](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data).

## Record fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `policy_id` | string | Stable policy ID selected by alert rules. |
| `policy_name` | string | Human-readable policy name. |
| `parent_id` | string | Parent policy ID. Use an empty string for a root policy; preserve an existing hierarchy on update. |
| `is_default` | boolean | Built-in/default marker; set to `false` for a custom policy. |
| `group_script` | string | Routing and notification-grouping DSL. It selects an action policy and defines grouping/wait behavior. |
| `inhibit_script` | string | Inhibition DSL. |
| `silence_script` | string | Silence DSL. |

## Simple example

Illustrative routing policy using an already-resolved action policy:

```json
{
  "policy_id": "example-alert-policy",
  "policy_name": "Example routing policy",
  "parent_id": "",
  "is_default": false,
  "group_script": "fire(action_policy=\"example-action-policy\", group={\"alert.project\": alert.project, \"alert.alert_id\": alert.alert_id}, group_by_all_labels=true, group_wait=\"15s\", group_interval=\"5m\", repeat_interval=\"1h\")",
  "inhibit_script": "",
  "silence_script": ""
}
```

Save this decoded object as `SLS_RESOURCE_VALUE_FILE`; use the
[common create command](../api/resource-records.md#create) with
`resource_name = sls.alert.alert_policy`.

For updates, use [record replacement](../api/resource-records.md#update-an-existing-record).
Outer ID/tag map to `policy_id` / `policy_name`. Validate before writing and read back afterwards.
Check the intended routing and noise-reduction behavior separately from JSON
structure; a stored DSL script is not proof of the intended decisions.
