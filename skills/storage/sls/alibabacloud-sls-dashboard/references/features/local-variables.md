# Chart-local variables

Use static local selectors to replace placeholders only in the current chart's
query or content. Define them in `display.innerTokenOption[]` and reference their
keys. Use [dashboard controls](variables.md) for filter predicates, dynamic
candidates, multiple selection, All, or cascading filters.
A single dropdown appears above the chart content; multiple dropdowns share a
filter-icon menu.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `key` | string | Yes | None | Variable name, referenced as ${{key\|default}}; supported alternatives include $key, [[key]], and ${key}. |
| `alias` | string | No | No label | Text shown beside the selector. |
| `values` | object[] | Yes | None | Static candidate list. |
| `values[].name` | string | Yes | None | Candidate label. |
| `values[].value` | string | Yes | None | Value substituted into the query or content. |
| `values[].isDefault` | boolean | No | First candidate if none marked | Select this candidate initially. |

```json
{"innerTokenOption":[{"key":"interval","alias":"Interval","values":[{"name":"1 minute","value":"60","isDefault":true},{"name":"5 minutes","value":"300"}]}]}
```

The query must reference `interval`, for example `${{interval|60}}`.
