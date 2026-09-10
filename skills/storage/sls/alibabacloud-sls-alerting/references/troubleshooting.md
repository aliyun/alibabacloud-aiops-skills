# Skill usage troubleshooting

Use when a CLI command or bundled script fails while carrying out a task.
For an alert that fired, use [alert event diagnosis](diagnosis/diagnose.md).

## Locate the failing operation

- CLI/plugin installation or authentication: [CLI installation guide](cli-installation-guide.md).
- Request parameters or payload validation: [create or update a rule](rules/create-update-alert-rule.md)
  or [ResourceRecord operations](notifications/api/resource-records.md), according to
  the operation.
- Region or endpoint routing: [region configuration](regions.md).
- Caller permission errors: [RAM policies](ram-policies.md).
- Bundled script cannot run: check its runtime and script path. A validator rejecting a payload
  calls for configuration changes; it does not establish a script defect.
