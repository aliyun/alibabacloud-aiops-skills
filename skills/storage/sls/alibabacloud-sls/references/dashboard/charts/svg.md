# SVG image

Use when placing an SVG image in a free layout. No query is required.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `svg` | string | Yes | None | SVG source URL or data URL; not raw XML. |
| `zIndex` | number | No | — | Stacking order; higher values appear above lower values. |

## Example

Display fragment for a simple circle:

```json
{
  "svg": "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20100%20100'%3E%3Ccircle%20cx='50'%20cy='50'%20r='40'%20fill='%237570ff'/%3E%3C/svg%3E"
}
```

Keep the image's intended proportions. These free-layout components have limited
offline validation; check appearance after saving.
