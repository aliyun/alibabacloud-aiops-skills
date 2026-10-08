# Query-result transformations

Use `chart.search.transformers[]` to process query results before display. Each
transformation receives the preceding output; backend requests stay unchanged.

Put parameters at the top level, or in `options` when they conflict with
`name`, `type` or `disabled`. Use JSON objects rather than encoded `optionsJson`
strings.

| Group | Types and behavior |
| --- | --- |
| Align/merge | join matches explicit joinFields with leftJoin/rightJoin/fullJoin; seriesToColumns performs outer alignment; merge combines compatible rows; concatenate appends fields without keyed row matching |
| Filter | filterFields selects fields; filterFieldsByName selects names; filterByValue filters rows by value conditions |
| Calculate | calculateField derives a field; groupBy groups and calculates; groupby is a separate grouping transform |
| Organize | rename changes display names; order reorders columns; sortBy sorts rows; organize hides, renames and reorders columns |
| Reshape | classify splits results by category; labelsToFields expands labels; seriesToRows makes row records; transposeRow exchanges row/column roles |
| Types/time | convertFieldType converts data types; parseTimestamp parses textual time; convertTimestamp converts milliseconds to seconds |
| Compatibility/advanced | noop does nothing; customScript runs explicitly requested custom JavaScript |

`filterFrames` is unsupported. Concatenation aligns row positions rather than
keys. For joins, specify shared keys and missing-row behavior, and check duplicate
keys.

After transformations, update chart bindings and actions to match the output
fields. Verify or fix queries when required calculation fields are missing.
Use query aggregation when the measure requires it; chart reductions see only
returned samples.

For parameter values and result behavior, read the relevant section in
[transformation parameters](transformation-parameters.md).

## Configuration examples

- Align and combine: [join by host](#join-results-by-host),
  [align by time](#align-series-by-time), [merge rows](#merge-compatible-rows),
  [concatenate columns](#concatenate-columns-by-position).
- Filter: [select fields](#select-fields-by-name),
  [match field names](#match-field-names-with-a-pattern),
  [filter rows](#keep-rows-matching-a-value-condition).
- Calculate and group: [error rate](#calculate-an-error-rate),
  [group each query](#group-each-query-by-namespace),
  [group across queries](#group-across-queries-by-service).
- Organize: [rename fields](#rename-fields-across-queries),
  [query-specific names](#rename-fields-per-query), [order columns](#order-columns),
  [sort rows](#sort-rows-by-latency),
  [organize fields](#hide-rename-and-order-fields).
- Reshape: [split by category](#split-a-result-by-category),
  [labels as columns](#expand-labels-into-columns),
  [labels as rows](#expand-labels-into-rows), [series as rows](#stack-series-into-rows).
- Types and time: [convert types](#convert-field-types),
  [parse text time](#parse-text-timestamps),
  [convert timestamp units](#convert-timestamp-units).

### Join results by host

```json
{
  "name": "TA",
  "type": "join",
  "joinType": "leftJoin",
  "joinFields": ["host"]
}
```

### Align series by time

See [seriesToColumns parameters](transformation-parameters.md#seriestocolumns)
for key ordering, missing samples, and duplicate field names.

```json
{
  "name": "TA",
  "type": "seriesToColumns",
  "byField": "Time",
  "suffixRefId": true
}
```

For A with `Time,cpu` rows `(1,10),(2,20)` and B with rows `(2,80),(3,90)`,
this produces result `A`:

```text
Time,cpu,cpu #B
1,10,0
2,20,80
3,0,90
```

### Merge compatible rows

```json
{
  "name": "TA",
  "type": "merge"
}
```

### Concatenate columns by position

```json
{ "name": "TA", "type": "concatenate" }
```

### Select fields by name

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

### Match field names with a pattern

```json
{
  "name": "TA",
  "type": "filterFieldsByName",
  "include": { "pattern": "/^cpu_.*/" }
}
```

### Keep rows matching a value condition

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

### Calculate an error rate

```json
{
  "name": "TA",
  "type": "calculateField",
  "mode": "binary",
  "binary": { "left": "error", "operator": "/", "right": "total" },
  "alias": "error_rate",
  "replaceFields": false
}
```

### Group each query by namespace

```json
{
  "name": "TA",
  "type": "groupBy",
  "fields": {
    "namespace": { "operation": "groupby" },
    "cpu": { "operation": "aggregate", "aggregations": ["mean", "max"] }
  }
}
```

### Group across queries by service

```json
{
  "name": "TA",
  "type": "groupby",
  "fieldConfigs": [
    { "fieldName": "service", "handleType": "groupby" },
    {
      "fieldName": "latency",
      "handleType": "calculate",
      "calculationType": "Total"
    }
  ]
}
```

### Rename fields across queries

```json
{
  "name": "TA",
  "type": "rename",
  "renameByName": { "host": "Host", "value": "Utilization" }
}
```

### Rename fields per query

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

### Order columns

```json
{
  "name": "TA",
  "type": "order",
  "indexByName": { "host": 0, "cpu": 1, "memory": 2, "Time": 3 }
}
```

### Sort rows by latency

```json
{
  "name": "TA",
  "type": "sortBy",
  "sort": [{ "field": "latency", "desc": true }]
}
```

### Hide, rename, and order fields

```json
{
  "name": "TA",
  "type": "organize",
  "excludeByName": { "internal_id": true },
  "renameByName": { "host": "Host", "cpu": "CPU utilization" },
  "indexByName": { "host": 0, "cpu": 1, "internal_id": 2 }
}
```

### Split a result by category

See [classify parameters](transformation-parameters.md#classify) for output names
and retained columns.

```json
{
  "name": "TA",
  "type": "classify",
  "datasource": "A",
  "xAxis": "Time",
  "yAxis": "count",
  "aggField": "kind"
}
```

For result `A` with `Time,count,kind` rows `(1000,16,consumer)` and
`(1060,17,client)`, the category column is retained:

```text
TA-consumer: Time,consumer,kind
            1000,16,consumer
TA-client:   Time,client,kind
             1060,17,client
```

### Expand labels into columns

See [labelsToFields parameters](transformation-parameters.md#labelstofields) for
label selection and the effect of an empty `keepLabels` list in each mode.

```json
{
  "name": "TA",
  "type": "labelsToFields",
  "mode": "columns",
  "keepLabels": ["host", "env"]
}
```

### Expand labels into rows

```json
{
  "name": "TA",
  "type": "labelsToFields",
  "mode": "rows",
  "keepLabels": ["host", "env"]
}
```

Given `Time=[t0,t1]` and `cpu=[10,20]` with attached labels
`{host:"h1",env:"prod"}`, columns mode above produces
`Time=[t0,t1], cpu=[10,20], host=[h1,h1], env=[prod,prod]`.
Adding `"valueLabel": "host"` renames `cpu` to `h1` and omits the `host` column.
Rows mode instead produces result `cpu` with `label,value` rows
`(host,h1),(env,prod)` and no samples.

### Stack series into rows

```json
{ "name": "TA", "type": "seriesToRows" }
```

### Convert field types

```json
{
  "name": "TA",
  "type": "convertFieldType",
  "conversions": [
    { "targetField": "count", "destinationType": "number" },
    { "targetField": "enabled", "destinationType": "boolean" },
    {
      "targetField": "event_time",
      "destinationType": "time",
      "dateFormat": "YYYY-MM-DD HH:mm:ss"
    }
  ]
}
```

### Parse text timestamps

See [parseTimestamp parameters](transformation-parameters.md#parsetimestamp) for
output units, timezone handling, and field-type behavior.

```json
{
  "name": "TA",
  "type": "parseTimestamp",
  "datasource": "A",
  "fieldName": "event_time",
  "format": "YYYY-MM-DD HH:mm:ss"
}
```

### Convert timestamp units

```json
{
  "name": "TA",
  "type": "convertTimestamp"
}
```
