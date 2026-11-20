# Manage alert rules

An alert rule runs queries on a schedule, evaluates their results, and selects
how triggered alerts enter notification processing. A rule belongs to a Project.

- For creation or configuration changes, see [create or update a rule](create-update-alert-rule.md).
- Resolve a supplied display name to a unique rule ID by listing and inspecting matches.

## List and inspect

See [rule reads](../cli-execution.md#list-and-inspect-rules) for commands and pagination.
The rule's `status` is `ENABLED` or `DISABLED`.

## Enable, disable, or delete

`alert enable` and `alert disable` change the rule's enabled state. `alert delete`
removes the rule; shared users, policies and templates remain separate resources.

## Mute or unmute

Use [mute/unmute commands](../cli-execution.md#mute-or-unmute-a-rule) to pause
notifications until the requested end time or cancel an existing mute. The rule
keeps its configured schedule and enabled state.

Choose the mute end time from the requested duration or timestamp. Ask for timing
information if it is missing.

`configuration.muteUntil` stores the mute end time in Unix seconds; unmute removes it.
The enabled state and other rule settings are unchanged.
