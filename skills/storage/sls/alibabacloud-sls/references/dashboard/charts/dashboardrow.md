# Row container

Use when grouping related panels into collapsible grid sections. A row does not query data.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `basicOptions.displayName` | string | Yes | None | Section title; may reference dashboard variables. |
| `basicOptions.repeat` | string | No | None | Existing dropdown variable whose selections repeat the group. |
| `rowChartOption.collasped` | boolean | No | false | Whether the group is initially collapsed. |
| `rowChartOption.events` | object[] | No | [] | Header-button actions, such as links. |
| `xPos / yPos` | number | Yes | None | Grid position. |
| `width / height` | number | Yes | None | Grid dimensions; a full-width header normally uses width=24, height=1. |

A row header groups the charts below it in the grid, up to the next row header.
Do not add transient `state` fields to saved JSON. See [layout](../features/layout.md).

## Examples

Display fragments:

### Section row

```json
{
  "xPos": 0,
  "yPos": 1,
  "width": 24,
  "height": 1,
  "basicOptions": {
    "displayName": "Resource status"
  },
  "rowChartOption": {
    "collasped": false
  }
}
```
