# Lines, points, and axes

Use when adjusting LinePro, MetricsPro, or grouped line/area/bar presentation.
Parameters are relative to `display`. Other chart types use their own style options.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `graphOptions.seriesStyle` | string | No | lines | lines, bars, or points; LinePro and MetricsPro only. |
| `graphOptions.lineInterpolation` | string | No | linear | linear or smooth; line segments only. |
| `graphOptions.barStyle` | string | No | middle | left, middle, or right relative to each X position; bars only. |
| `graphOptions.lineWidth` | number | No | 1.5 | Line or bar-border width in pixels; 0–10. |
| `graphOptions.showPoint` | string | No | never | auto, always, or never; controls point markers. |
| `graphOptions.fillOpacity` | number | No | 20 | Area or bar fill opacity, 0–100. |
| `graphOptions.lineStyle` | string | No | solid | solid, dash, or dot; line segments only. |
| `graphOptions.pointSize` | number | No | 0 | Point size in pixels; 0–50. |
| `graphOptions.gradientMode` | string | No | opacity | opacity, hue, scheme, or none; fill gradient mode. |
| `xAxisOption.show` | boolean | No | — | Show the X axis. |
| `xAxisOption.label` | string | No | None | Axis title. |
| `xAxisOption.timeRangeMode` | string | No | — | searchTime uses the selected query window; dataTime uses the returned time extent. |
| `xAxisOption.format` | string | No | Automatic | Time-axis display format; does not change source timestamps. |
| `xAxisOption.height` | number | No | Automatic | Space for the X axis in pixels. |
| `xAxisOption.zoomTarget` | string | No | — | global updates dashboard time; single zooms only this chart. |
| `yAxisOption.show` | boolean | No | — | Show the Y axis. |
| `yAxisOption.label` | string | No | None | Axis title. |
| `yAxisOption.tickCount` | number | No | Automatic | Requested number of ticks; at least 2. |
| `yAxisOption.position` | number | No | — | 5: automatic; 3: left; 1: right; 4: hidden. |
| `yAxisOption.stackingMode` | string | No | none | normal stacks series at each X position; none leaves them independent. |
| `yAxisOption.height` | number | No | Automatic | Width of the Y-axis label area in pixels. |
| `yAxisOption.min / max` | number | No | Data-dependent | Hard limits; values outside them may be clipped. |
| `yAxisOption.softMin / softMax` | number | No | None | Suggested limits; the axis expands if data exceeds them. |
| `yAxisOption.id` | string | No | — | Axis identity; use field overrides to assign series to separate axes. |
| `yAxisOption.showGrid` | boolean | No | First axis only | Show horizontal grid lines. |

Stack only additive measures with compatible units. Use
[legend](legend.md), [tooltip](tooltip.md), [standard options](standard-options.md),
and [field overrides](field-overrides.md) for shared presentation settings.

A series with only one point still shows a marker even when showPoint=never.
