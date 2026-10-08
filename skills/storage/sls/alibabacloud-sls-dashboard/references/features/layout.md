# Layout and sections

Use `grid` as the recommended layout. Choose `free` only when a custom layout
requires free positioning or overlapping panels.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `attribute.type` | string or null | Yes for new dashboards | free when omitted | grid uses 24 columns; free allows free positioning and overlap. An omitted or null attribute, or an omitted, null or empty-string type, selects free. Other values are invalid. |
| `display.xPos` | number | Yes for grid panels | None | Horizontal position in columns; non-negative integer. |
| `display.yPos` | number | Yes for grid panels | None | Vertical position in rows; non-negative integer. |
| `display.width` | number | Yes for grid panels | None | Width in columns; positive integer, with xPos + width <= 24. |
| `display.height` | number | Yes for grid panels | None | Height in rows; positive integer. |
| `display.zIndex` | number | No | — | Stacking order in free layout; higher values appear in front. |

Write the layout type explicitly for new dashboards. Validation warns about empty
layout settings without inserting a type or converting coordinates.

Use `attribute.type=grid` for a 24-column layout. Set integer
`display.xPos/yPos/width/height`: positions are non-negative, sizes are positive,
and `xPos + width <= 24`. Avoid unintended overlap. Typical widths are 6, 8, 12
and 24. Start the next row after the largest preceding `yPos + height`.

`dashboardrow` is a full-width section header without a datasource. Preserve its
collapse setting and child references.

## Free layout

Free layout supports custom positioning and overlapping panels. Preserve an
existing free layout during unrelated edits; changing its layout requires
repositioning panels.

Read [free-layout coordinates](free-layout.md) when positioning free panels or
static annotations. Plan `layout.x/y/w/h` maps to
`display.xPos/yPos/width/height`.

Top-fixed controls appear in the variable area above the grid.
