# Filters, tokens and Adhoc

| Mode | Effect | Suitable use |
| --- | --- | --- |
| filter | Append a field predicate to a supported log search | Proven indexed log dimensions |
| token | Replace explicit placeholders in a query or supported resource/content field | Query or content parameter |
| adhoc | Add metric label matchers | User-selected metric label/operator/value |

A token consumer must contain the matching placeholder. For multiple selected metric
labels, use a regex matcher with a pipe-joined value and allValue='.*'; an exact matcher
does not interpret that list. Sampled label values do not provide a complete dynamic
list. Labels must be valid for the queried metrics.

Dependent option queries must consume parent tokens and must not form a cycle.
`search.isInheritFilter` lets log-backed candidate queries inherit other field
filters. It does not control normal chart filtering, token substitution or Adhoc.

Adhoc binds a metric resource and obtains current labels; it has no token
placeholder, static candidates or preset token defaults. Its metric-query scope can
be dashboard-wide.
Keep fixed resource constraints in queries; controls add optional filters.

For [StoreViews](../datasources/storeview.md), test the selected filter or Adhoc
control against the view.

For the saved JSON parameters, see [dropdown controls](../charts/droplistpro.md).

For new controls in a Plan, use [controls](../model/plan.md#controls).

## Chart-local variables

Use static local selectors to replace placeholders only in the current chart's
query or content. Define them in `display.innerTokenOption[]` and reference their
keys. Use dashboard controls for filter predicates, dynamic
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
