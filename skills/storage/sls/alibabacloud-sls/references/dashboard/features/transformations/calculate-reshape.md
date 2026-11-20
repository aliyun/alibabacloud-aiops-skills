# Calculate and reshape

Use these objects in `chart.search.transformers[]`. See the [common fields](../transformations.md#common-fields).

- [calculateField](#calculatefield)
- [groupBy](#groupby)
- [groupby](#groupby)
- [classify](#classify)
- [labelsToFields](#labelstofields)
- [seriesToRows](#seriestorows)
- [transposeRow](#transposerow)

## calculateField

Use when deriving one value per row.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `mode` | string | Yes | None | reduceRow combines fields within a row; binary combines two operands. |
| `reduce.include` | string[] | No | All numeric fields | Select reduceRow inputs by exact original name. An empty list also selects all numeric fields. Selected fields are processed in input-column order, not list order. |
| `reduce.reducer` | string | For reduceRow | None | count, lastNotNull, last, firstNotNull, first, Total, min, max, mean, range, difference, allValues, or uniqueValues. |
| `binary.left / binary.right` | string | For binary | None | Exact original operand names within the same result. |
| `binary.operator` | string | For binary | None | +, -, *, or /. |
| `alias` | string | Yes | None | New field name. |
| `replaceFields` | boolean | No | false | Keep only the first time field, if present, and the calculated field when true. |

Each result is calculated independently. A missing binary operand or no selected
reduction fields leaves that result unchanged. With input columns `a=2, b=9`,
`reduce.include: ["b", "a"]` still gives `first=2` and `difference=7` because input
columns determine the order.

### Example: Calculate an error rate

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

## groupBy

Use when grouping each query independently; aggregate output names have the form
`field (aggregation)`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `fields.<fieldName>.operation` | string | Yes | None | groupby selects a grouping key; aggregate calculates values for that group. |
| `fields.<fieldName>.aggregations` | string[] | For aggregate | None | Functions such as mean and max; one output column per function. |

Keys are original field names. For namespace=prod with cpu=1 and cpu=3,
mean(cpu)=2 and max(cpu)=3.

### Example: Group each query by namespace

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

## groupby

Use when grouping rows across all input queries into one result. This is a distinct
configuration from `groupBy`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `fieldConfigs[].fieldName` | string | Yes | None | Original column name, consistent across inputs. |
| `fieldConfigs[].handleType` | string | Yes | None | groupby, calculate, or ignore. |
| `fieldConfigs[].calculationType` | string | For calculate | None | Total, first, firstNotNull, last, lastNotNull, max, min, mean, or minAboveZero. |

At least one grouping field is needed. Only grouping and calculated fields remain;
calculated columns retain their original names.

### Example: Group across queries by service

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

## classify

Split one query into series by a category without aggregation.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `datasource` | string | Yes | None | Exact result name to split. |
| `xAxis` | string | Yes | None | Time or category-axis column; does not restrict which columns are retained. |
| `yAxis` | string | Yes | None | Exact original name of the numeric column to rename to each category value. |
| `aggField` | string | Yes | None | Exact original name of the category column defining the split. |

Output results are named `<transformation name>-<category>`. Each retains all
original columns, including `aggField` and extra columns, with only `yAxis`
renamed. Row order within each category is preserved; other results stay unchanged.

### Example: Split a result by category

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

## labelsToFields

Use for labels attached to metric series, not ordinary category columns.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `mode` | string | Yes | None | columns retains samples, adds constant label columns, and removes attached labels. rows produces one result per labeled field, named after that field, containing only `label`/`value` pairs without original samples. |
| `keepLabels` | string[] | No | All labels | Labels to retain; list order determines row order in rows mode. An explicit `[]` retains all labels in columns mode but produces no results in rows mode. |
| `valueLabel` | string | No | None | In columns mode, use this label's value as the value-field name instead of adding a constant column for that label. Include it in keepLabels when that list is non-empty. |

### Example: Expand labels into columns

```json
{
  "name": "TA",
  "type": "labelsToFields",
  "mode": "columns",
  "keepLabels": ["host", "env"]
}
```

### Example: Expand labels into rows

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

## seriesToRows

No parameters. Stack at least two time-plus-value results into `Time/Metric/Value`.
Each input must have at most two fields, including a time field. Wide inputs leave
the transformation ineffective. Rows are appended without sorting or filling gaps;
`Metric` is the original value-field name.

### Example: Stack series into rows

```json
{ "name": "TA", "type": "seriesToRows" }
```

## transposeRow

Transpose one result into `_col0`, `_col1`, and subsequent columns, up to 100.
Each original row becomes a column.
