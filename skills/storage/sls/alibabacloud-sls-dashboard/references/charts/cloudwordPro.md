# Word cloud

Chart type: `cloudwordPro`. Word size reflects numeric weight.

Use for top search terms, error types or tag frequencies. Choose a bar chart
for precise comparisons.

## Query results and field bindings

Only the first query result is used. Bind its output columns under
`display.queryOptionMap.<queryName>`.

Return non-empty words and finite, positive weights; exclude invalid rows in the
query. Duplicate words have their weights summed. Compute averages, maxima, or
other measures in the query and return one row per word.

Font size uses a logarithmic scale relative to this result's summed weights; sizes are
not comparable across panels. `fontSize` and `layoutFormat` are not supported
configuration fields.

## Configuration parameters

Paths below are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.wordColumn` | string | Yes | None | Name of the output column containing words. |
| `queryOptionMap.<queryName>.numberColumn` | string | Yes | None | Name of the output column containing weights; numeric strings are converted to numbers. |
| `wordCloudConfig.spiral` | string | No | `archimedean` | Placement path: `rectangular` uses a rectangular spiral; `archimedean` uses an Archimedean spiral. Neither guarantees the outer shape of the word cloud. |
| `wordCloudConfig.fontStyle` | string | No | `normal` | `normal`: upright; `italic`: italic; `oblique`: slanted. |
| `wordCloudConfig.font` | string | No | `PingFang SC` font | Font key, such as `PingFang`, `AlibabaPuHuiTi`, `Helvetica`, `SourceHanSans`, or `SourceHanSerifCN`. Unrecognized keys select `PingFang SC`. Appearance depends on browser font availability. |
| `wordCloudConfig.colorPalette` | string | No | `builtinColors` | `builtinColors`, `classicsColor`, or `softColor`. Colors cycle through the selected palette in displayed-word order; they do not encode weight ranges or provide stable category colors. An unrecognized key uses `builtinColors`. |
| `wordCloudConfig.rotateMode` | string | No | `random` | `random`: independently select each word's angle from -90°, -60°, -30°, 0°, 30°, or 60°, ignoring `rotate`. `custom`: randomly select each word's angle from `rotate`. |
| `wordCloudConfig.rotate` | number[] | No | In `custom` mode, one random angle from the six listed above, shared by all words | Angles in degrees; used only with `rotateMode="custom"`. `[0]` keeps all words horizontal. Empty or non-array values behave as if omitted. |

## Readability and limitations

- For readability, start with 20–50 terms and limit the result in the query.
- Words that cannot fit in the available space may be omitted; long words, large
  vocabularies, and rotation increase this risk.
- Positions are randomized, even with `rotate: [0]`; query order does not fix them.
- A highly skewed weight distribution can make smaller words hard to distinguish.

For selectors inside the chart, see [local variables](../features/local-variables.md).

## Example: horizontal top terms

Display fragment for query `A`, returning `word:string` and `weight:number`:

```json
{
  "queryOptionMap": {
    "A": {
      "wordColumn": "word",
      "numberColumn": "weight"
    }
  },
  "wordCloudConfig": {
    "spiral": "rectangular",
    "rotateMode": "custom",
    "rotate": [0]
  }
}
```
