# Tooltip

Use when changing hover details or linking cursors across time charts.
Parameters belong to `display.tooltipOption`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `mode` | string | No | all for line/bar/histogram | all shows series at the hovered X value; single shows only the selected point. |
| `sortOrder` | string | No | none for line/bar/histogram | none, asc, or desc; sort hovered values, not query results. |
| `labelFormat` | string | No | Empty | Additional hover text; supports multiple lines. |
| `cursorSync` | boolean | No | false | Synchronize cursors on supported time charts. |
| `cursorSyncKey` | string | No | sync_key | Charts with the same key synchronize when cursorSync is true. |

Line, grouped-series, bar, and histogram charts support the main hover options.
Use [actions](actions.md) for click navigation and [standard options](standard-options.md)
for value formatting.
