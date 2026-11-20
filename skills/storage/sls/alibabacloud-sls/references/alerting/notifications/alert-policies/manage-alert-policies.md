# Manage alert policies

An alert policy routes and groups alerts, applies inhibition or silence, and
selects an [action policy](../action-policies/manage-action-policies.md). Most ordinary rules can
reuse `sls.builtin.dynamic`; custom policy authoring is needed only for requested
routing or noise-reduction behavior.

Use [ResourceRecord operations](../api/resource-records.md) with
`resource_name = sls.alert.alert_policy`. Check rules that select the policy before
deletion or changing its action target. DSL-only records may not show graphical nodes
in the console.

## Create or update

The shared [ResourceRecord operations](../api/resource-records.md) save policy values.
Updates replace that value; a diff can expose unintended changes to routing, silence,
inhibition or hierarchy settings.

### Choose the processing behavior

- [Routing](#routing): select an action policy.
- [Notification grouping](notification-grouping.md):
  choose grouping keys and notification waits.
- [Inhibition and silence](#inhibition-and-silence): suppress notifications under
  the requested conditions.

#### Routing

In `group_script`, `fire(action_policy=...)` selects an existing
[action policy](../action-policies/manage-action-policies.md). The same call sets
notification grouping. For a dynamic action policy, follow
[rule notification setup](../../rules/notifications/connect.md#advanced-mode)
to determine whether the rule supplies the action-policy ID and repeat wait.

#### Inhibition and silence

`inhibit_script` defines relationships in which alerts suppress other alerts;
`silence_script` suppresses notifications matching silence conditions. Neither
disables rule evaluation. Leave these scripts empty unless the behavior is
requested; preserve existing values on unrelated updates.

The example below covers basic routing. For conditional routing, inhibition,
or silence syntax, use a verified policy or the
[official DSL reference](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data).

### Record fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `policy_id` | string | Stable policy ID selected by alert rules. |
| `policy_name` | string | Human-readable policy name. |
| `parent_id` | string | Parent policy ID. Use an empty string for a root policy; preserve an existing hierarchy on update. |
| `is_default` | boolean | Built-in/default marker; set to `false` for a custom policy. |
| `group_script` | string | Routing and notification-grouping DSL. It selects an action policy and defines grouping/wait behavior. |
| `inhibit_script` | string | Inhibition DSL. |
| `silence_script` | string | Silence DSL. |

### Simple example

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

Check that routing, grouping, inhibition, and silence match the requested behavior.
