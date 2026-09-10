# Group alert notifications

Within `group_script`, `fire(...)` defines the group and its waiting behavior:

| DSL argument | Meaning |
| --- | --- |
| `action_policy` | Existing action-policy ID used for notification. |
| `group` | Dictionary of alert attributes forming the merge/group key. |
| `group_by_all_labels` | Whether every alert label is also included in that key. |
| `group_wait` | Initial wait before notifying a new group. |
| `group_interval` | Wait before notifying changes to an existing group. |
| `repeat_interval` | Wait before repeating an unchanged notification. |

These are policy-side notification settings, not query schedules or
query-result group evaluation. When this alert policy selects a dynamic action
policy, the rule's `policyConfiguration.repeatInterval` overrides this
policy-side `repeat_interval`. The policy value applies only when it is not
dynamically overridden; see [notification modes](../../rules/notifications/connect.md) and
the [official alert-grouping guide](https://help.aliyun.com/zh/sls/deduplicate-alerts).

The [write example](create-update-alert-policy.md#simple-example) includes both Project and
rule ID to avoid merging same-named rules from different Projects. Choose broader grouping
only when the user requests it. Preserve existing routing, silence, and
inhibition settings during unrelated changes.
