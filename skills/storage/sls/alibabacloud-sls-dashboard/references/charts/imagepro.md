# Image

Chart type: `imagePro`. Use when adding a logo, illustration, or other static image.

## Usage

- Include a builtin query in `search.chartQueries` as shown below so the image
  displays. An empty query list shows "No data". Builtin generates simulated data
  locally and needs no Logstore or SQL. Use the supplied image URL and descriptive
  alternative text.
- Main, dark-theme, and fallback image URLs support [dashboard variables](../features/variables.md).
- Supporting links use `display.documentLinkOption`; see [documentation links](../features/actions.md). Query-field settings, thresholds, and chart click actions do not apply.

## Configuration parameters

Paths are relative to `display.imageOption`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `imageSrc` | string | Yes | None | Default image URL. |
| `imageSrcInDark` | string | No | imageSrc | Image URL used in dark theme. |
| `imageReSrc` | string | No | Built-in empty image | Fallback URL if the main image cannot load. |
| `imageAlt` | string | No | Chart title | Alternative text. |
| `imageFill` | string | No | — | fill stretches to the panel; scale preserves proportions and shows the complete image. |

## Examples

Use the [complete grid example](../../assets/dashboards/charts/imagepro.json) as a
starting configuration. Replace its sample image URL and alternative text.

Chart fragment:

### Provided image

```json
{
  "type": "imagePro",
  "display": {
    "imageOption": {
      "imageSrc": "<user-provided-image-url>",
      "imageAlt": "<concise-image-description>",
      "imageFill": "scale"
    }
  },
  "search": {
    "chartQueries": [
      {"name": "A", "datasource": "builtin", "type": "random_time_line"}
    ],
    "start": "-900s",
    "end": "now",
    "dataSourceType": "current"
  }
}
```

For a Plan, supply `display.imageOption` and omit `queries` or use `queries: []`.
The builder adds this builtin query automatically. Existing queries are retained.
See [builtin configuration](../datasources/builtin.md).
