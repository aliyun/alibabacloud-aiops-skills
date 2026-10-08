# Basic shapes

Use when adding rectangles or diamonds as static annotations or value-colored shapes.

## Usage

Static shapes need no query. Query-based colors require a measure and threshold
rules.

## Configuration parameters

Paths are relative to `display.basicGraphicsOption`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `basicType` | string | Yes | — | rect for rectangle; diamond for diamond. |
| `showBorder` | boolean | No | — | false hides the border regardless of borderWidth. |
| `showBackground` | boolean | No | — | false makes the background transparent. |
| `basicStyle.borderColor` | object | No | — | Color configuration; see color fields below. |
| `basicStyle.borderWidth` | number | No | — | Border width in pixels; 0–20. |
| `basicStyle.borderStyle` | string | No | — | solid, dashed, or dotted. |
| `basicStyle.backgroundColor` | object | No | — | Background color configuration. |
| `basicStyle.opacity` | number | No | — | Fill opacity; 0–1. |
| `basicStyle.borderRadius` | number | No | — | Corner radius in pixels; 0–50, primarily for rectangles. |
| `basicStyle.borderColor.mode / basicStyle.backgroundColor.mode` | string | No | — | builtin uses the default shape color; fixed uses color; thresholds uses `display.thresholdOption.thresholds`. |
| `basicStyle.borderColor.color / basicStyle.backgroundColor.color` | string | For fixed mode | None | Explicit color. |
| `basicStyle.borderColor.seriesBy / basicStyle.backgroundColor.seriesBy` | string | For thresholds mode | — | last, min, or max from the first field of the first query result. |

## Examples

Display fragment:

### Outlined rectangle

```json
{
  "basicGraphicsOption": {
    "basicType": "rect",
    "showBorder": true,
    "showBackground": false
  }
}
```
