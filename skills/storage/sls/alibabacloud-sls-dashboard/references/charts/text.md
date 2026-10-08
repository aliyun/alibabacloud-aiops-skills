# Static text

Use when adding static annotations in a free layout. For dynamic Markdown, use
[rich text](textpro.md).

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `text` | string | Yes | None | Static annotation text. |
| `fontSize` | number | No | — | Font size in pixels. |
| `lineHeight` | number | No | — | Line-height multiplier. |
| `align` | string | No | — | left, center, or right. |
| `isBold / isItalic` | boolean | No | false | Bold / italic text. |
| `isLineThrough / isUnderLine` | boolean | No | false | Strike-through / underline. |
| `color` | object | No | — | RGBA color with r/g/b components and alpha a. |
| `zIndex` | number | No | — | Stacking order in a free layout; larger values place the annotation above overlapping panels. |

## Example

Display fragment:

```json
{
  "text": "Service overview",
  "fontSize": 18,
  "lineHeight": 1.5,
  "align": "left",
  "isBold": true,
  "color": {"r": 102, "g": 102, "b": 102, "a": 1}
}
```

Set position and size using [free-layout coordinates](../features/free-layout.md).
These free-layout components have
limited offline validation; check appearance after saving.
