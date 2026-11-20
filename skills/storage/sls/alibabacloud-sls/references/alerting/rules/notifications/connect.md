# Connect a rule to notifications

The rule's policy IDs and repeat wait connect it to notification resources.
For managing a recipient, policy or template independently, see
[notification management](../../notifications/manage-notifications.md).

## Choose the mode

The delivery path is rule → alert policy → action policy → channel and recipient,
with a content template selected by the action policy.

| Mode | Use when | Policy selection |
| --- | --- | --- |
| Normal (default) | Reuse an action policy, including conditional or multiple channels | `sls.builtin.dynamic` plus the action-policy ID |
| Minimal | Reuse a rule-specific policy created by the console | See [minimal mode](#minimal-mode) |
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

Set the repeat wait and recipients from the requirement. Use `sls.builtin.cn`
when its content and language are suitable.
No custom alert policy or template is required for this mode.

## Referenced resources

Groups reference notification-user IDs. Action policies reference recipients or Webhook
integrations and content templates; the rule references the selected policies.
Existing resources can be reused, with new objects needed only for missing dependencies.
List/get can resolve unknown IDs or inspect destinations and
[channel prerequisites](../../notifications/action-policies/channels.md) when useful.

## Minimal mode

Minimal mode reuses an existing rule-specific `alert.simple.*` action policy.
Read the policy and use its actual ID. For a new setup without an existing
rule-specific policy, use normal mode.

## Advanced mode

Inspect the selected [alert policy](../../notifications/alert-policies/manage-alert-policies.md).
When it uses a dynamic action policy, set the rule's `actionPolicyId` and
`repeatInterval`; these select the action policy and override the group's
`repeat_interval`. Otherwise, set `actionPolicyId` to an empty string and use
the action policy and repeat behavior configured in the alert policy.
See [policy configuration](https://help.aliyun.com/zh/ros/developer-reference/aliyun-sls-alert)
for the field settings.

See the [official dynamic-action mechanism](https://help.aliyun.com/zh/sls/dynamic-action-policy-mechanism)
for action-policy precedence and the
[alert-grouping guide](https://help.aliyun.com/zh/sls/deduplicate-alerts)
for repeat-wait precedence.
