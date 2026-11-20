# Layout and sections

`grid` uses a 24-column layout. `free` provides custom positioning and overlapping
panels. `attribute.type` selects the layout.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `attribute.type` | string or null | No | free when omitted | grid uses 24 columns; free allows free positioning and overlap. An omitted or null attribute, or an omitted, null or empty-string type, selects free. |
| `display.xPos` | number | Yes for grid panels | None | Horizontal position in columns; non-negative integer. |
| `display.yPos` | number | Yes for grid panels | None | Vertical position in rows; non-negative integer. |
| `display.width` | number | Yes for grid panels | None | Width in columns; positive integer, with xPos + width <= 24. |
| `display.height` | number | Yes for grid panels | None | Height in rows; positive integer. |
| `display.zIndex` | number | No | — | Stacking order in free layout; higher values appear in front. |

Typical grid widths are 6, 8, 12 and 24. The largest preceding `yPos + height`
gives the start of the next row.
Plan builds use grid layout; `layout.x/y/w/h` maps to these position and size fields.

`dashboardrow` is a full-width section header with collapse settings and child references.

## Free layout

Use `attribute.type="free"` for custom positioning or overlapping panels.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `display.xPos` | number | Yes for positioned panels | None | 0 starts at the left edge; positive positions are (100 × xPos + 5) / 1000 of the dashboard width. |
| `display.yPos` | number | Yes for positioned panels | None | 0 starts at the top edge; positive positions are 88 × yPos + 5 pixels down. |
| `display.width` | number | Yes for positioned panels | None | (100 × width - 10) / 1000 of the dashboard width; width=8 occupies 79%. |
| `display.height` | number | Yes for positioned panels | None | 88 × height - 10 pixels; height=2 is 166 pixels. |
| `display.zIndex` | number | No | — | Stacking order; higher values appear in front when panels overlap. |

Configure free layouts directly in Dashboard JSON. Preserve saved coordinates
during unrelated changes to an existing free-layout dashboard.
