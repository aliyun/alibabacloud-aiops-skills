# Transformation parameters

Use when configuring `chart.search.transformers[]`; see the
[transformation overview](transformations.md) for pipeline behavior.

## Contents

- [Common fields](#common-fields)
- [Align and combine](#align-and-combine)
- [Filter](#filter)
- [Calculate and group](#calculate-and-group)
- [Organize fields](#organize-fields)
- [Reshape](#reshape)
- [Convert types and time](#convert-types-and-time)

## Common fields

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | None | Transformation ID, such as TA. |
| `type` | string | Yes | None | Transformation type listed below. |
| `disabled` | boolean | No | false | Skip this transformation while keeping its configuration. |
| `options` | object | No | None | Parameters that cannot be placed at the top level, such as filterByValue's own type. |

Parameters below belong to the transformation unless otherwise specified.
See [examples](transformations.md#configuration-examples) for complete JSON.

## Align and combine

### join

Use when matching queries by explicit keys.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `joinType` | string | Yes | None | leftJoin keeps keys from the first result; rightJoin from the last; fullJoin from every result. |
| `joinFields` | string[] | Yes | None | Key columns shared by participating results. |

Unmatched cells are missing, not zero. A result lacking the key fields cannot
supply joined values. For A=(h1,10),(h2,20) and B=(h2,80),(h3,70), a left join
on host yields h1 with 10/missing and h2 with 20/80.

### seriesToColumns

Use when aligning series by time or another single key.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `byField` | string | No | Time | Exact original name of the outer-join key. |
| `suffixRefId` | boolean | No | false | The first occurrence keeps its name. Later duplicates receive ` #<query ID>` when true, or ` 2`, ` 3`, etc. when false. true also orders input results by ascending query ID; false preserves input order. |

With at least two input results, matching results combine into a result named `A`.
The key is the first output column; all key values are retained in lexicographic
order, even for numeric keys. Missing samples are filled with 0.
Results missing the key are excluded if any result matches; if none match, inputs
stay unchanged. For repeated keys, each column retains its last non-null value.

### merge

No parameters. Match on fields common to all results, then combine compatible
rows. Conflicting values remain separate rows. Use `join` when keys and join type
must be controlled explicitly.

### concatenate

No parameters. Append columns by row position; duplicate names keep the first
column. No key alignment or missing-value filling occurs. Use only when row
positions already correspond.

## Filter

### filterFields

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `include / exclude` | object | Yes, one mode | None | Keep or remove matching columns in each result. |
| `include.id / exclude.id` | string | Yes | None | Use byNames for a field-name list. |
| `include.options.names / exclude.options.names` | string[] | Yes | None | Match original or current display names; prefer stable original names. A base name also matches generated numeric suffixes: `cpu` matches `cpu 2`. |

Rows stay unchanged. Results with no remaining columns are removed.

### filterFieldsByName

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `include.pattern` | string | Yes | None | Exact original field name, or /pattern/flags for a regular expression. |

Do not combine a names list with a pattern. Validate regular expressions before
use to avoid unintentionally retaining all fields.

### filterByValue

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `options.type` | string | Yes | None | include keeps matching rows; exclude removes them. |
| `options.match` | string | Yes | None | all requires every condition; any requires one. |
| `options.filters[].fieldName` | string | Yes | None | Field name or display name. |
| `options.filters[].config.id` | string | Yes | None | isNull, isNotNull, equal, notEqual, greater, greaterOrEqual, lower, lowerOrEqual, or regex. |
| `options.filters[].config.options.value` | any | For value comparisons | None | Comparison value or regex pattern. |

For example, `include` with `status >= 500` retains error rows and all their columns.

## Calculate and group

### calculateField

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

### groupBy

Use when grouping each query independently; aggregate output names have the form
`field (aggregation)`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `fields.<fieldName>.operation` | string | Yes | None | groupby selects a grouping key; aggregate calculates values for that group. |
| `fields.<fieldName>.aggregations` | string[] | For aggregate | None | Functions such as mean and max; one output column per function. |

Keys are original field names. For namespace=prod with cpu=1 and cpu=3,
mean(cpu)=2 and max(cpu)=3.

### groupby

Use when grouping rows across all input queries into one result. This is a distinct
configuration from `groupBy`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `fieldConfigs[].fieldName` | string | Yes | None | Original column name, consistent across inputs. |
| `fieldConfigs[].handleType` | string | Yes | None | groupby, calculate, or ignore. |
| `fieldConfigs[].calculationType` | string | For calculate | None | Total, first, firstNotNull, last, lastNotNull, max, min, mean, or minAboveZero. |

At least one grouping field is needed. Only grouping and calculated fields remain;
calculated columns retain their original names.

## Organize fields

### rename

Change display names without changing original field names, values, or order.
Subsequent field references continue to use original names.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `renameByName` | object | No | None | Map original names to display names across queries. |
| `renameByMatcher` | object[] | No | None | Query-specific mappings; take precedence over renameByName. |
| `renameByMatcher[].matcher` | object | For a mapping | None | {id:"byName", options:"field", refId:"A"} identifies a query field. |
| `renameByMatcher[].displayName` | string | For a mapping | None | New display name. |

### order

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `indexByName` | object | Yes | None | Map exact original field names to zero-based integer column positions. Unspecified columns follow configured columns, preserving their relative order. |

The mapping applies to every result, so identically named fields receive the same
position. Rows and values stay unchanged.

### sortBy

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `sort` | object[] | Yes | None | Use one entry; only the first sort key is applied. |
| `sort[].field` | string | Yes | None | Field to sort; an absent field leaves order unchanged. |
| `sort[].desc` | boolean | No | false | true sorts descending; false ascending. |

Whole rows move together. Numbers, times and strings use numeric, chronological,
and lexical order respectively.

### organize

Use on one result; combine multiple queries first.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `excludeByName` | object | No | None | Map original names to true to hide columns. |
| `renameByName` | object | No | None | Map original names to display names. |
| `indexByName` | object | No | None | Map original names to column positions. |

## Reshape

### classify

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

### labelsToFields

Use for labels attached to metric series, not ordinary category columns.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `mode` | string | Yes | None | columns retains samples, adds constant label columns, and removes attached labels. rows produces one result per labeled field, named after that field, containing only `label`/`value` pairs without original samples. |
| `keepLabels` | string[] | No | All labels | Labels to retain; list order determines row order in rows mode. An explicit `[]` retains all labels in columns mode but produces no results in rows mode. |
| `valueLabel` | string | No | None | In columns mode, use this label's value as the value-field name instead of adding a constant column for that label. Include it in keepLabels when that list is non-empty. |

### seriesToRows

No parameters. Stack at least two time-plus-value results into `Time/Metric/Value`.
Each input must have at most two fields, including a time field. Wide inputs leave
the transformation ineffective. Rows are appended without sorting or filling gaps;
`Metric` is the original value-field name.

### transposeRow

Transpose one result into `_col0`, `_col1`, and subsequent columns, up to 100.
Each original row becomes a column.

## Convert types and time

### convertFieldType

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `conversions[].targetField` | string | Yes | None | Original field name; matches across all results. |
| `conversions[].destinationType` | string | Yes | None | number, string, boolean, or time. |
| `conversions[].dateFormat` | string | For non-ISO time text | None | Input date format, such as YYYY-MM-DD HH:mm:ss. |

Invalid numbers become null; empty strings and null convert to 0. Non-empty strings,
including "false" and "0", convert to boolean true. Time output uses milliseconds;
text dates without a timezone use browser local time. Invalid dates become null.

### parseTimestamp

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `datasource` | string | Yes | None | Exact result name to process. |
| `fieldName` | string | Yes | None | Exact original name of the text-time field. |
| `format` | string | Yes | None | Input format, such as YYYY-MM-DD HH:mm:ss; supply explicitly in Dashboard JSON. |

The console uses the first field value for format detection and validation. Use
the edit button to enter a custom format.

Unmatched result or field names leave data unchanged. Output is Unix seconds;
invalid values become null. Text without a timezone uses browser local time.
This changes values but does not mark the field as time-typed; use
`convertFieldType` when both the type and millisecond values are needed.

### convertTimestamp

No parameters. Convert 13-digit millisecond timestamps in time-typed fields to
seconds. Ten-digit seconds remain unchanged; date strings are not parsed.
