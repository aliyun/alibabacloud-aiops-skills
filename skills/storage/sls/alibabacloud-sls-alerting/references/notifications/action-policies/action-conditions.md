# Select notification actions by condition

## Conditional, simultaneous notifications

Use the [SLS severity mapping](../../rules/triggering/severity.md#severity-order-is-semantic)
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

After creation or update, read back the policy and check which channels each
requested severity selects, including branch fallthrough and escalation.
Compare those selections with the user's requirements. The local resource
validator checks JSON structure, not DSL routing semantics; successful storage
alone does not establish that the routing is correct.

In this DSL, `if alert.<field>` matches when any alert in the notification set
meets the condition; `if alerts.<field>` requires all alerts to meet it. This is
notification routing, not the rule's row-level evaluation expression. The
[official DSL reference](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
documents this distinction. See also the
[action-policy guide](https://help.aliyun.com/zh/sls/create-an-action-policy/)
for channel selection and conditional routing.

DSL-only policies need not have a graphical editor representation in the
console. More complex routing or lifecycle escalation should be based on a
verified exported policy and additional documentation, not guessed UI fields.
