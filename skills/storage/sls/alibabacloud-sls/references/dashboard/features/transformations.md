# Query-result transformations

Use `chart.search.transformers[]` to process query results in order before display.
After a transformation, update chart bindings and actions to match its output fields.
Query aggregation determines the business measure; chart reductions see returned samples.

| Task | Reference |
| --- | --- |
| Join by keys, align series, merge rows or concatenate columns | [Align and combine](transformations/combine.md) |
| Filter rows/fields, rename, sort or reorder | [Filter and organize](transformations/filter-organize.md) |
| Calculate values, group or reshape results | [Calculate and reshape](transformations/calculate-reshape.md) |
| Convert values or timestamps | [Types and time](transformations/types-time.md) |

## Common fields

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | None | Transformation ID, such as TA. |
| `type` | string | Yes | None | Transformation type listed below. |
| `disabled` | boolean | No | false | Skip this transformation while keeping its configuration. |
| `options` | object | No | None | Parameters that cannot be placed at the top level, such as filterByValue's own type. |


Put parameters at the top level, or in `options` when they conflict with `name`,
`type` or `disabled`. Use JSON objects for options.
