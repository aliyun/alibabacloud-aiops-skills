# Troubleshooting

For CLI, authentication, permission, region or connection issues, see
[common troubleshooting](../troubleshooting.md).

## Dashboard operations

| Symptom | What to check | Details |
| --- | --- | --- |
| Python script or package missing | Script path, Python interpreter and the missing package named in the error. | [Plan construction](model/plan.md#build), [validation tools](validation/checks.md) |
| Unexpected command argument | The target and JSON input shape. | [CLI commands](related-apis.md) |
| Configuration validation error | Reported field path, type, value and relationships. | [Validation tools](validation/checks.md), [chart settings](charts/charts.md) |
| Timeout or uncertain write | Current dashboard configuration from `dashboard get`, compared with the intended update. | [Dashboard operations](workflows/publish.md) |
| Subscription configuration or delivery issue | Current subscription state, schedule, recipients, query window and delivery evidence. | [Subscription guide](integrations/subscriptions.md) |

For data, display, or interaction issues, use [dashboard diagnosis](workflows/diagnose.md).
