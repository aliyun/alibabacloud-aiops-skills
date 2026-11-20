# Troubleshooting

For CLI, authentication, permission, region or connection issues, see
[common troubleshooting](../troubleshooting.md).

## Alert operations

| Symptom | What to check | Details |
| --- | --- | --- |
| Command parameters or request construction fail | Command help, parameter mapping, JSON encoding, and the generated request. | [CLI execution](cli-execution.md), [API definitions](related-apis.md) |
| Local validation rejects a payload | The reported field, type, required value, range, and applicable configuration type. | [Rule configuration](rules/create-update-alert-rule.md), [ResourceRecord configuration](notifications/api/resource-records.md) |
| A bundled script cannot run | Python runtime and the absolute script/input paths. | [Rule validator](rules/verify-alert-rule.md), [resource validator](notifications/api/resource-records.md#local-validation) |

For trigger causes, frequency, duration, or alert outcomes, use
[event diagnosis](diagnosis/diagnose.md).
