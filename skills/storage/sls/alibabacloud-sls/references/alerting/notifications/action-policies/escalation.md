# Escalate notifications

Escalation uses the secondary action list for follow-up notifications. It is
separate from simultaneous `fire(...)` calls in one action branch.

For a policy without escalation, keep all three `escalation*_enabled` switches
false and preserve existing timeout values on unrelated updates. The
[write example](manage-action-policies.md#simple-example) uses a nonempty
secondary fallback; replace it with the intended follow-up actions before
enabling escalation.

For requested escalation, resolve the follow-up actions, the condition that
starts the wait, and its duration. Use an existing policy or the
[policy documentation](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
to map that behavior to `escalation_start_*`, `escalation_inprogress_*`, and
`escalation_*`; confirm when timers start or reset before changing them.
