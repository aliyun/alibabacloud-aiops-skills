# Free-layout coordinates

Use when positioning panels or static annotations in a dashboard with
`attribute.type="free"`. See [grid layout](layout.md) for the usual 24-column layout.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `display.xPos` | number | Yes for positioned panels | None | 0 starts at the left edge; positive positions are (100 × xPos + 5) / 1000 of the dashboard width. |
| `display.yPos` | number | Yes for positioned panels | None | 0 starts at the top edge; positive positions are 88 × yPos + 5 pixels down. |
| `display.width` | number | Yes for positioned panels | None | (100 × width - 10) / 1000 of the dashboard width; width=8 occupies 79%. |
| `display.height` | number | Yes for positioned panels | None | 88 × height - 10 pixels; height=2 is 166 pixels. |
| `display.zIndex` | number | No | — | Stacking order; higher values appear in front when panels overlap. |

Plan `layout.x/y/w/h` maps to these four position and size fields. Preserve saved
coordinates during unrelated changes to an existing free-layout dashboard.
