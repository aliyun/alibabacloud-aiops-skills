# Alerting

For operation-specific access, see [RAM permissions](ram-policies.md).

Scripts in `scripts/alerting/` validate rules and notification records locally.
See [validation results](validation-results.md) for report fields and exit codes.

## Select the operation

| Task | Further reading |
| --- | --- |
| Find, inspect, create, update, enable, disable, delete, or mute/unmute a rule | [Alert rules](rules/manage-alert-rules.md) |
| Manage recipients, policies, and message content | [Notification resources](notifications/manage-notifications.md) |
| Explain trigger causes, frequency, duration, or alert history | [Event diagnosis](diagnosis/diagnose.md) |

Rules define when alerts fire; notification resources determine how they are handled
and sent. Read the matching entry and only the references needed for the task.

Commands, parameter mapping, and request construction are covered in
[CLI execution](cli-execution.md). Each operation's reference provides
its configuration and verification steps.

## Troubleshooting

For command, authentication, permission, or connection errors, see
[common troubleshooting](../troubleshooting.md).
For rule, notification, or validator issues, see
[alerting troubleshooting](troubleshooting.md).
For trigger causes and alert outcomes, see [event diagnosis](diagnosis/diagnose.md).
