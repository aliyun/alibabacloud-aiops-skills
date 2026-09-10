# Connect a rule to notifications

Use this step when creating or updating a rule's notification settings. Select
the mode and existing resources, then set the policy IDs and repeat wait in the
rule. To manage a recipient, policy, or template independently, start with
[notification management](../../notifications/manage-notifications.md).

## Choose the mode

The delivery path is rule → alert policy → action policy → channel and recipient,
with a content template selected by the action policy.

| Mode | Use when | Policy selection |
| --- | --- | --- |
| Normal (default) | Reuse an action policy, including conditional or multiple channels | `sls.builtin.dynamic` plus the action-policy ID |
| Minimal | Reuse a rule-specific policy created by the console | See [coverage boundary](#minimal-mode-coverage-boundary) |
| Advanced | Custom routing, notification grouping, inhibition, or silence | See [advanced mode](#advanced-mode) |

## Normal-mode baseline

Enable `configuration.sinkAlerthub` and select an existing action policy:

```json
{
  "sinkAlerthub": {"enabled": true},
  "policyConfiguration": {
    "alertPolicyId": "sls.builtin.dynamic",
    "actionPolicyId": "example-action-policy",
    "repeatInterval": "5m"
  }
}
```

Set the repeat wait from the requirement. Reuse approved recipients and let the
action policy use `sls.builtin.cn` when its content/language is suitable.
No custom alert policy or template is required for this mode.
CLI compatibility is covered in [rule write requirements](../create-update-alert-rule.md#shared-configuration-baseline).

## Normal-mode dependency order

1. Inspect selected policies, recipients/Webhooks, and templates by ID. List only
   when IDs are unknown; confirm destinations and channel readiness from the records.
2. Create missing users/Webhooks before groups, then any custom content template.
3. Reuse or create an action policy referencing those IDs. Check the selected
   [channel's prerequisites](../../notifications/action-policies/channels.md).
4. Select `sls.builtin.dynamic`, or an advanced alert policy when required, then
   put the policy IDs and repeat wait into the rule.

## Minimal-mode coverage boundary

Minimal mode skips manual action-policy creation. It can use a rule-specific
`alert.simple.*` action-policy record instead of an inline channels payload.

`create-alert` accepts policy IDs but has no documented direct-recipient fields
for this mode. Reuse an existing policy ID. Do not fabricate `--channels`, a
recipient field, or an `alert.simple.*` ID. If no policy ID is available, use
normal mode or obtain the API payload documentation.

## Advanced mode

Read [Alert policies](../../notifications/alert-policies/manage-alert-policies.md) only when this mode is needed.
Inspect the chosen policy's routing and dynamic-action behavior before filling
`actionPolicyId`; a policy without a dynamic override can require an empty
string. When the selected alert policy uses a dynamic action policy, both the
action-policy ID and repeat wait come from the rule; the rule's
`repeatInterval` overrides the alert policy's group `repeat_interval`. Otherwise,
the alert policy's selected action and repeat behavior apply. Do not confuse
policy-side notification grouping with
[per-group query evaluation](../group-evaluation.md).

See the [official dynamic-action mechanism](https://help.aliyun.com/zh/sls/dynamic-action-policy-mechanism)
for action-policy precedence and the
[alert-grouping guide](https://help.aliyun.com/zh/sls/deduplicate-alerts)
for repeat-wait precedence.
