# Value mapping

Use `display.valueMappingOption[]` to replace displayed values. Query data stays
unchanged. For individual fields, use [field overrides](field-overrides.md) with
`optionKeys: ["valueMappingOption"]`. The first matching rule wins.

## Configuration parameters

Each entry belongs to `display.valueMappingOption[]`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `matchType` | string | Yes | None | value, range, regex, or special. |
| `matchValue` | string | For value/special | None | Exact string value, or a special value listed below. |
| `from / to` | number or null | At least one for range | Open bound | Inclusive numeric limits; two empty bounds make the rule ineffective. |
| `pattern` | string | For regex | None | Regular expression applied to the value as text. |
| `replaceType` | string | Yes | None | text or icon. |
| `replaceText` | string | For text | None | Replacement text; regex matches support $0, $1, $2 capture references. |
| `replaceIcon` | string | For icon | None | Replacement icon identifier. |
| `color` | string | No | None | Color of the mapped result. State timeline segment fills use [threshold colors](../charts/timelinepro.md#mapped-state-colors). |

## Match types

| matchType | Meaning |
| --- | --- |
| value | Exact equality against `matchValue` after converting the value to text. |
| range | Compare numbers and numeric strings by numeric value against inclusive `from`/`to` limits; a missing bound is open-ended. Empty or whitespace-only strings, booleans, and null values do not match. |
| regex | Match the value as text; supports pattern captures in replacement text. |
| special | Match one of the special values below. |

| Special value (`matchValue`) | Meaning |
| --- | --- |
| `true` | Boolean true or the exact string `"true"`. |
| `false` | Boolean false or the exact string `"false"`. |
| `null` | Null or missing values, or the exact string `"null"`. |
| `nan` | Numeric NaN or the exact string `"NaN"`. |
| `null+nan` | Any value matched by `null` or `nan`. |
| `empty` | Only the empty string; excludes whitespace, null, missing values, and NaN. |

Text mappings take precedence over unit and decimal formatting. Use thresholds
for continuous severity colors and transformations to change returned data.
