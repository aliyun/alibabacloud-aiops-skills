# Create or update an action policy

For updates, read the exact policy and preserve settings outside the requested
change. Resolve the referenced objects and templates before writing.

## Define the notification behavior

- [Actions](actions.md): combine channels, recipients, templates, and sending periods.
- [Conditions](action-conditions.md): select actions by severity or other alert attributes,
  including simultaneous channels in one branch.
- [Escalation](escalation.md): configure secondary actions and waiting times only
  when follow-up notifications are required.

## Record fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `action_policy_id` | string | Stable policy ID selected by alert rules or alert-policy DSL. |
| `action_policy_name` | string | Human-readable policy name. |
| `labels` | object | Reserved field; set to `{}` for a custom policy. |
| `is_default` | boolean | Built-in/default marker; set to `false` for a custom policy. |
| `primary_policy_script` | string | DSL for the first action list: channel, recipients, template, time period, and optional routing conditions. |
| `secondary_policy_script` | string | DSL for the second action list used by enabled escalation settings. Official error documentation identifies an empty primary or secondary policy as `ActionPolicyEmpty`; do not assume an empty string is accepted. Preserve an existing valid script or provide a valid explicit fallback. |

## Simple example

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

Save this decoded object as `SLS_RESOURCE_VALUE_FILE`; use the
[common create command](../api/resource-records.md#create) with
`resource_name = sls.alert.action_policy`.

The example group must exist and have approved email recipients. `template_id`
can refer to `sls.builtin.cn` without creating a custom template. The secondary script duplicates the primary action as a nonempty fallback;
all escalation switches are off. Redesign it before enabling escalation.

For updates, use [record replacement](../api/resource-records.md#update-an-existing-record).
Keep outer ID/tag consistent with
`action_policy_id` / `action_policy_name`. Validate before writing and read back
afterwards. Check which channels each requested severity selects, including
fallthrough and escalation; structure validation does not verify DSL semantics.
