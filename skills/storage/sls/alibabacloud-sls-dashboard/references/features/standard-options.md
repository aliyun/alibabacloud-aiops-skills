# Standard formatting and colors

Use when changing numeric formats, units, missing-value text, or field colors.
Parameters belong to `display.standardOption`; use [field overrides](field-overrides.md)
for individual columns or series.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `format` | string | No | none | Interpret and format the source value using the formats below; does not change query data. |
| `unit` | string or object | No | No suffix | Append a unit without scaling the value. Prefer {"unit":"none"} or {"unit":"custom","customUnit":"requests"}. |
| `decimals` | number | No | Automatic | Decimal places, 0–10; 0 displays integers. |
| `displayName` | string | No | Field name | Displayed label; does not rename the query output. |
| `noValue` | string | No | — | Empty-query-result text for barpro, treemappro, and scatterchart; statpro also uses it for null values. Does not change query data. |
| `colorSchame` | object | No | — | Color configuration; preserve this spelling. |
| `colorSchame.schema` | string | No | — | builtin assigns palette colors; single uses color; threshold uses thresholdOption.thresholds. |
| `colorSchame.color` | string | For single | None | Fixed color, such as #7570ff. |
| `colorSchame.seriesBy` | string | No | — | For supported series coloring: last, min, or max selects the value tested against thresholds. |
| `filterable` | boolean | No | Depends on field | Table cell action for filtering by the clicked value; distinct from column search. |

## Formats

Numeric strings are formatted as numbers; nonnumeric strings retain their text.

| Value | Input and display |
| --- | --- |
| `none` | No scaling; apply decimals and optional unit suffix. |
| `KMB` | Abbreviate counts using powers of 1000: K, Mil, Bil. |
| `milli` | Thousands separators without scaling. |
| `byte_ies` / `byte_si` | Bytes; scale by 1024 / 1000. |
| `byte_ies_sec` / `byte_si_sec` | Bytes per second; scale by 1024 / 1000. |
| `bps_ies` / `bps_si` | Bits per second; scale by 1024 / 1000, using bps labels. |
| `bps_ies_sec` / `bps_si_sec` | Bits per second; scale by 1024 / 1000, using b/s labels. |
| `percent` | 0–100 value; append %. |
| `percent_decimal` | 0–1 fraction; multiply by 100 and append %. |
| `localtime`, `UTC+0` through `UTC+12`, `UTC-1` through `UTC-11` | Unix seconds as `YYYY-MM-DD HH:mm:ss`; `localtime` uses the browser timezone, and UTC formats use fixed whole-hour offsets in the listed ranges. |
| `dtdhms` / `dthms` | Duration in seconds as days and hh:mm:ss / hh:mm:ss. |
| `ns`, `µs`, `ms`, `s`, `m`, `h`, `d` | Duration in the selected input unit; convert to a readable duration unit. |
| `iops` / `reqps` | Operations / requests per second; scale by powers of 1000. |

For example, `format="ms"` interprets 1500 as milliseconds and displays about
`1.50 s`. To display `1500 ms`, use `format="none"` with a custom `ms` unit.
When a format already supplies a unit, keep `unit={"unit":"none"}`.
`time` is not a format value. Keep preformatted query strings at `format="none"`.
Matched [value mappings](value-mapping.md) take precedence over normal formatting.

### Example: format one field

```json
{"fieldOptions":[{"queryName":"A","name":"cpu","overrides":[{"optionKeys":["standardOption","format"],"value":"percent_decimal"},{"optionKeys":["standardOption","decimals"],"value":1}]}]}
```
