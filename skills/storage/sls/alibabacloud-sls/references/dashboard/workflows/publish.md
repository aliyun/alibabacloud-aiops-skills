# Dashboard operations

The CLI provides `dashboard create`, `update`, `get`, `list` and `delete`.
[Command parameters](../related-apis.md#dashboard-parameters) map to Dashboard JSON
fields. Profile, region and endpoint select the [destination](../../regions.md).

## Commands

| Command | Purpose |
| --- | --- |
| `dashboard list` / `dashboard get` | Inspect dashboards and their configuration. |
| `dashboard create` | Create a dashboard. |
| `dashboard update` | Replace an existing dashboard's configuration. |
| `dashboard delete` | Remove a dashboard. |

## Complete Dashboard JSON

`--from-file` accepts a complete Dashboard JSON object, including Plan-generated output.
For create, `dashboardName` can be in the file or supplied with `--dashboard`; if both
are present they must agree. For update, `--dashboard` selects the existing dashboard.
File input takes all body fields from the file. When an update needs writable fields
that file input cannot preserve, replace `--from-file` with `--raw-body-file final.json`.
If the raw JSON object omits `dashboardName`, the CLI adds the `--dashboard` value;
an existing `dashboardName` is retained, while `--dashboard` selects the target.
Create makes a new dashboard; update sends the replacement configuration for the
selected dashboard. A diff against the existing configuration can expose unintended changes.

## Existing configuration

A JSON response from `dashboard get` can supply existing configuration for editing or export.

Charts can be compared by stable `title` IDs because the service may reorder the
array. The dashboard page can be used to inspect layout and interactions. Source
queries can be used to check the data behind the charts.

After a timeout or uncertain write, `dashboard get` can establish the current state.
