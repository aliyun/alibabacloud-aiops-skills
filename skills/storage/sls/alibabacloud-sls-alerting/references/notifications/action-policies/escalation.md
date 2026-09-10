# Escalate notifications

Escalation uses the secondary action list for follow-up notifications. It is
separate from simultaneous `fire(...)` calls in one action branch.

For a policy without escalation, keep all three `escalation*_enabled` switches
false and preserve existing timeout values on unrelated updates. The
[write example](create-update-action-policy.md#simple-example) uses a nonempty
secondary fallback; replace it with the intended follow-up actions before
enabling escalation.

For requested escalation, resolve the follow-up actions, the condition that
starts the wait, and its duration. The
[official policy schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
lists `escalation_start_*`, `escalation_inprogress_*`, and `escalation_*` pairs,
but delegates their meaning to console settings. Use a verified console payload
or documentation mapping the requested behavior to those fields before writing;
the field names alone do not establish when timers start or reset.
