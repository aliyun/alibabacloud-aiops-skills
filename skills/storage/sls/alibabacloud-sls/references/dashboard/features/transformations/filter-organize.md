# Filter and organize

Use these objects in `chart.search.transformers[]`. See the [common fields](../transformations.md#common-fields).

- [filterFields](#filterfields)
- [filterFieldsByName](#filterfieldsbyname)
- [filterByValue](#filterbyvalue)
- [rename](#rename)
- [order](#order)
- [sortBy](#sortby)
- [organize](#organize)

## filterFields

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `include / exclude` | object | Yes, one mode | None | Keep or remove matching columns in each result. |
| `include.id / exclude.id` | string | Yes | None | Use byNames for a field-name list. |
| `include.options.names / exclude.options.names` | string[] | Yes | None | Match original or current display names; prefer stable original names. A base name also matches generated numeric suffixes: `cpu` matches `cpu 2`. |

Rows stay unchanged. Results with no remaining columns are removed.

### Example: Select fields by name

```json
{
  "name": "TA",
  "type": "filterFields",
  "include": {
    "id": "byNames",
    "options": { "names": ["Time", "cpu"] }
  }
}
```

## filterFieldsByName

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `include.pattern` | string | Yes | None | Exact original field name, or /pattern/flags for a regular expression. |

Do not combine a names list with a pattern. Validate regular expressions before
use to avoid unintentionally retaining all fields.

### Example: Match field names with a pattern

```json
{
  "name": "TA",
  "type": "filterFieldsByName",
  "include": { "pattern": "/^cpu_.*/" }
}
```

## filterByValue

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `options.type` | string | Yes | None | include keeps matching rows; exclude removes them. |
| `options.match` | string | Yes | None | all requires every condition; any requires one. |
| `options.filters[].fieldName` | string | Yes | None | Field name or display name. |
| `options.filters[].config.id` | string | Yes | None | isNull, isNotNull, equal, notEqual, greater, greaterOrEqual, lower, lowerOrEqual, or regex. |
| `options.filters[].config.options.value` | any | For value comparisons | None | Comparison value or regex pattern. |

For example, `include` with `status >= 500` retains error rows and all their columns.

### Example: Keep rows matching a value condition

```json
{
  "name": "TA",
  "type": "filterByValue",
  "options": {
    "type": "include",
    "match": "all",
    "filters": [
      {
        "fieldName": "status",
        "config": {
          "id": "greaterOrEqual",
          "options": { "value": 500 }
        }
      }
    ]
  }
}
```

## rename

Change display names without changing original field names, values, or order.
Subsequent field references continue to use original names.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `renameByName` | object | No | None | Map original names to display names across queries. |
| `renameByMatcher` | object[] | No | None | Query-specific mappings; take precedence over renameByName. |
| `renameByMatcher[].matcher` | object | For a mapping | None | {id:"byName", options:"field", refId:"A"} identifies a query field. |
| `renameByMatcher[].displayName` | string | For a mapping | None | New display name. |

### Example: Rename fields across queries

```json
{
  "name": "TA",
  "type": "rename",
  "renameByName": { "host": "Host", "value": "Utilization" }
}
```

### Example: Rename fields per query

```json
{
  "name": "TA",
  "type": "rename",
  "renameByMatcher": [
    {
      "matcher": { "id": "byName", "options": "value", "refId": "A" },
      "displayName": "CPU utilization"
    },
    {
      "matcher": { "id": "byName", "options": "value", "refId": "B" },
      "displayName": "Memory utilization"
    }
  ]
}
```

## order

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `indexByName` | object | Yes | None | Map exact original field names to zero-based integer column positions. Unspecified columns follow configured columns, preserving their relative order. |

The mapping applies to every result, so identically named fields receive the same
position. Rows and values stay unchanged.

### Example: Order columns

```json
{
  "name": "TA",
  "type": "order",
  "indexByName": { "host": 0, "cpu": 1, "memory": 2, "Time": 3 }
}
```

## sortBy

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `sort` | object[] | Yes | None | Use one entry; only the first sort key is applied. |
| `sort[].field` | string | Yes | None | Field to sort; an absent field leaves order unchanged. |
| `sort[].desc` | boolean | No | false | true sorts descending; false ascending. |

Whole rows move together. Numbers, times and strings use numeric, chronological,
and lexical order respectively.

### Example: Sort rows by latency

```json
{
  "name": "TA",
  "type": "sortBy",
  "sort": [{ "field": "latency", "desc": true }]
}
```

## organize

Use on one result; combine multiple queries first.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `excludeByName` | object | No | None | Map original names to true to hide columns. |
| `renameByName` | object | No | None | Map original names to display names. |
| `indexByName` | object | No | None | Map original names to column positions. |

### Example: Hide, rename, and order fields

```json
{
  "name": "TA",
  "type": "organize",
  "excludeByName": { "internal_id": true },
  "renameByName": { "host": "Host", "cpu": "CPU utilization" },
  "indexByName": { "host": 0, "cpu": 1, "internal_id": 2 }
}
```
