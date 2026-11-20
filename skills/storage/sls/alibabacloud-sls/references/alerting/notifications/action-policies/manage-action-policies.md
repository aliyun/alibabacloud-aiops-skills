# Manage action policies

An action policy defines how to notify: channels, recipients, templates,
conditional selection, and optional escalation. Rules or alert policies select
it; actions reference [notification objects](../manage-notifications.md#notification-objects) and
[templates](../templates/manage-content-templates.md).

Use [ResourceRecord operations](../api/resource-records.md) with
`resource_name = sls.alert.action_policy`. Prefer reusing a suitable policy; check
rules and alert policies that select it before changing or deleting it.

## Create or update

Resolve referenced objects and templates, and follow the shared
[ResourceRecord operations](../api/resource-records.md) for the write.

### Define the notification behavior

- [Actions](actions.md): combine channels, recipients, templates, and sending periods.
- [Conditions](action-conditions.md): select actions by severity or other alert attributes,
  including simultaneous channels in one branch.
- [Escalation](escalation.md): configure secondary actions and waiting times only
  when follow-up notifications are required.

### Record fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `action_policy_id` | string | Stable policy ID selected by alert rules or alert-policy DSL. |
| `action_policy_name` | string | Human-readable policy name. |
| `labels` | object | Reserved field; set to `{}` for a custom policy. |
| `is_default` | boolean | Built-in/default marker; set to `false` for a custom policy. |
| `primary_policy_script` | string | DSL for the first action list: channel, recipients, template, time period, and optional routing conditions. |
| `secondary_policy_script` | string | DSL for escalation actions. Keep a nonempty script to avoid `ActionPolicyEmpty`; preserve existing actions or provide an explicit fallback. |

### Simple example

```json
{
  "action_policy_id": "example-action-policy",
  "action_policy_name": "Example team notification",
  "is_default": false,
  "labels": {},
  "primary_policy_script": "fire(type=\"email\", users=[], groups=[\"example-team\"], oncall_groups=[], receiver_type=\"static\", external_url=\"\", external_headers={}, template_id=\"sls.builtin.cn\", period=\"any\")",
  "secondary_policy_script": "fire(type=\"email\", users=[], groups=[\"example-team\"], oncall_groups=[], receiver_type=\"static\", external_url=\"\", external_headers={}, template_id=\"sls.builtin.cn\", period=\"any\")",
  "escalation_start_enabled": false,
  "escalation_start_timeout": "10m",
  "escalation_inprogress_enabled": false,
  "escalation_inprogress_timeout": "30m",
  "escalation_enabled": false,
  "escalation_timeout": "1h"
}
```

The example group must exist and contain the intended email recipients. `template_id`
can refer to `sls.builtin.cn` without creating a custom template. The secondary script duplicates the primary action as a nonempty fallback;
all escalation switches are off. Redesign it before enabling escalation.

Check which channels each requested severity selects, including branch
fallthrough and escalation.
