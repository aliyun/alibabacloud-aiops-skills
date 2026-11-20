# Select notification actions by condition

## Conditional, simultaneous notifications

Use the [SLS severity mapping](../../rules/triggering/define-alert-triggering.md#severity-order-is-semantic)
for routing: Critical is `10` and High is `8`, so Critical/High matches `>= 8`.
Medium is `6` and does not belong in that branch.

An action list can choose SMS/voice based on severity and send several channels
in the same branch. For example, after resolving an existing SMS/voice-capable
group and DingTalk integration:

```text
if alert.severity >= 8:
    fire(type="sms", users=[], groups=["example-team"], oncall_groups=[], template_id="sls.builtin.cn", period="any")
    fire(type="voice", users=[], groups=["example-team"], oncall_groups=[], template_id="sls.builtin.cn", period="any")
    stop()
fire(type="webhook_integration", integration_type="dingtalk", webhook_id="example-dingtalk", template_id="sls.builtin.cn", period="any")
```

Put this text into `primary_policy_script` as a JSON string; preserve newlines
and quoting using a JSON serializer. `stop()` is after both high-severity
actions, so the intended channels are selected before the branch ends.

In this DSL, `if alert.<field>` matches when any alert in the notification set
meets the condition; `if alerts.<field>` requires all alerts to meet it. This is
notification routing, not the rule's row-level evaluation expression. The
[official DSL reference](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
documents this distinction. See also the
[action-policy guide](https://help.aliyun.com/zh/sls/create-an-action-policy/)
for channel selection and conditional routing.

For more complex routing or lifecycle escalation, use a verified exported
policy and additional documentation.
