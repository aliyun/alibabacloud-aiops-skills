# Dropdown control

Use when users need a dashboard-wide field filter, query variable, or metric-label
filter. Choose the mode in [variables](../features/variables.md).

## Configuration parameters

Paths are relative to `display` unless prefixed with `search`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `basicOptions.displayName` | string | No | — | Visible control title. |
| `basicOptions.showTime` | boolean | No | false | Show the query time in the header. |
| `fixedTop` | boolean | No | false | Place the control in the dashboard's top variable area. |
| `fixedTopOrder` | number | No | — | Order among top-fixed controls. |
| `showDropListChart` | boolean | No | — | Show the control; hiding it does not remove its saved configuration. |
| `bindQuery` | boolean | No | false | Query dynamic candidates for filter or token mode. |
| `search.chartQueries` | object[] | For dynamic or adhoc | None | Candidate query for filter/token; metric resource for adhoc. |
| `search.isInheritFilter` | boolean | No | — | Let a log-backed candidate query inherit other field filters, excluding its own. |
| `dropListOption.type` | string | Yes | None | filter appends search predicates; token substitutes placeholders; adhoc adds metric label matchers. |
| `dropListOption.key` | string | Yes, except globalFilter | None | Field name for filter, variable name for token, stable group key for adhoc. |
| `dropListOption.alias` | string | No | — | Control label; does not change the key. |
| `dropListOption.list` | string[] | For static candidates | [] | Actual filter or substitution values. |
| `dropListOption.listAlias` | string[] | No | — | Candidate labels aligned by index with list. |
| `dropListOption.listDefault` | boolean[] | For filter defaults | [] | Selected flags aligned with list; multiple selected values are ORed. |
| `dropListOption.tokenDefault` | boolean[] | For token defaults | [] | Selected flags aligned with list; external or URL values take precedence. |
| `dropListOption.logic` | string | For filter | — | and includes selected values; not excludes them. |
| `dropListOption.globalFilter` | boolean | No | false | Use selected values as full-text terms without a field-name prefix. |
| `dropListOption.autoFilter` | boolean | No | — | For non-global filter mode, restrict selections to candidate values; false allows custom values. |
| `dropListOption.refresh` | number | No | 1 | Dynamic query timing: 1 on page load; 2 on dashboard time-range changes. |
| `dropListOption.regex` | string | No | None | Filter or extract dynamic candidate values; does not filter business-chart rows. |
| `dropListOption.showType` | string | For token | — | select uses a dropdown; auto allows free input. Multi-select uses a dropdown. |
| `dropListOption.multipleToken` | boolean | No | false | Select among several variable keys using tokenKeys. |
| `dropListOption.tokenKeys` | string[] | For multipleToken | None | Available variable keys. |
| `dropListOption.multiSelect` | boolean | No | false | Select multiple token values; their joined string is substituted into queries. |
| `dropListOption.includeAll` | boolean | No | false | Offer All, represented by $__all. |
| `dropListOption.allValue` | string | When includeAll=true | — | Substitution for All; use .* for PromQL regex matchers. |
| `dropListOption.customTemplate` | string | No | <%= data.join("\|") %> | Multi-select joining template; data is the selected-value array and key is the variable name. |
| `dropListOption.multipleTokenKey` | string | For multi-column dynamic values | — | Column used as the candidate value; other columns remain available for token expansion. |

Dynamic and static candidates are combined, excluding empty and duplicate values. Prefer
a single non-empty string column; candidate results are bounded to 8,000 values.
Candidate queries use dashboard time when active, otherwise their saved
`search.start/end/timeSpanType`; `refresh` controls when they run.

`multipleToken=true` does not support top-fixed placement, multiple selection, All,
or custom joining templates. For top-fixed dynamic single tokens, candidate lookup
and initial selection precede dependent charts; a valid external value wins,
otherwise the first candidate is selected.

Adhoc uses a metric resource to obtain labels and values. Its key is a group ID,
not a label name; use letters, digits, and underscores. Operators are `=`, `!=`,
`>`, `<`, `=~`, and `!~`. Static lists and token defaults do not apply.

## Example: static field filter

Display fragment for an indexed `request_method` field:

```json
{
  "bindQuery": false,
  "dropListOption": {
    "type": "filter",
    "key": "request_method",
    "alias": "Request method",
    "logic": "and",
    "globalFilter": false,
    "list": ["GET", "POST"],
    "listDefault": [true, false]
  }
}
```

GET is initially selected. A log query such as `* | select count(*) as requests`
receives the method predicate without a token placeholder.

## Example: static token

Display fragment; the consumer query references `${{interval|60}}`:

```json
{"bindQuery":false,"dropListOption":{"type":"token","key":"interval","showType":"select","list":["60","300"],"listAlias":["1 minute","5 minutes"],"tokenDefault":[true,false]}}
```

For a Plan, define `controls[]` and a visible chart with `control=id`; see the
[Plan contract](../model/plan.md). Plan default values are converted to boolean flags
in Dashboard JSON.
