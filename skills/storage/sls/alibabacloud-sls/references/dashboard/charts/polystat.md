# Polystat

Use when summarizing many metric series as status nodes, optionally grouped by labels.

## Usage

- Supply one numeric field or metric series per status node. A label/value row table does not automatically become multiple nodes.
- Group by labels attached to the series.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `dataOptions.showValue` | boolean | No | true | Show each node's reduced value. |
| `dataOptions.calculationType` | string | No | first | Reduce each numeric field or series to a node value: first, firstNotNull, last, lastNotNull, max, min, mean, minAboveZero, or Total. |
| `dataOptions.decimals` | number | No | 2 | Displayed decimal places; 0–10. |
| `groupOptions.enabled` | boolean | No | false | Group nodes by a series label; group area is proportional to node count. |
| `groupOptions.groupKey` | string | When grouping | default | Label key defining groups, not an ordinary result column. Nodes missing this label enter the group named `default`. |
| `groupOptions.showTitle` | boolean | No | false | Show each group value and node count. |
| `layoutOptions.autoColumnCount` | boolean | No | true | Choose column count from panel size and node count. |
| `layoutOptions.columnCount` | number | No | 8 | Column count when autoColumnCount=false. |
| `layoutOptions.autoRowCount` | boolean | No | true | Choose row count automatically. |
| `layoutOptions.rowCount` | number | No | 8 | Row count when autoRowCount=false. |
| `layoutOptions.limitCount` | number | No | 10000 | Display the first N nodes after sorting. |
| `nodeOptions.autoPolygenSize` | boolean | No | true | Calculate node radius from available space. |
| `nodeOptions.polygenSize` | number | No | 25 | Radius in pixels when autoPolygenSize=false. |
| `nodeOptions.polygonBorderSize` | number | No | 2 | Node-border width in pixels. |
| `nodeOptions.shape` | string | No | hexagon_pointed_top | hexagon_pointed_top, circle, or square. |
| `nodeOptions.gradientsEnabled` | boolean | No | true | Shade nodes from their fill color toward a darker color. |
| `nodeOptions.fillColor` | string | No | #5F99F9 | Color when neither threshold nor field color applies. |
| `nodeOptions.borderColor` | string | No | green | Node-border color. |
| `textOptions.showText` | boolean | No | false | Show node names. |
| `textOptions.autoFontSize` | boolean | No | true | Fit a common font size to names, values, and node size. |
| `textOptions.fontSize` | number | No | 12 | Font size in pixels when autoFontSize=false. |
| `textOptions.textColor` | string | No | #24292e | Name and value color. |
| `textOptions.ellipseEnabled` | boolean | No | false | Truncate long names with fixed font size. |
| `textOptions.ellipseCharacters` | number | No | 18 | Characters retained before truncation. |
| `textOptions.emptyDataText` | string | No | OK | Text displayed when there are no nodes. |
| `tooltipOptions.enabled` | boolean | No | true | Show node hover details. |
| `tooltipOptions.showTime` | boolean | No | false | Show the latest query-result time, or current time if no time field exists. |
| `thresholdOptions.thresholds` | object[] | No | [] | Value/color/rule entries for node colors; see thresholds. |

See [threshold rules](../features/thresholds.md).
See [reducer meanings](../features/reducers.md) for the functions listed above;
this chart spells the sum reducer `Total`, not `total`.

The default input limit is 200 non-time fields across all queries, including
nonnumeric fields. `layoutOptions.limitCount` limits the resulting nodes after
sorting by group name; it does not raise the input limit or prioritize unhealthy
nodes. With grouping off and both row and column counts fixed, ensure
`rowCount × columnCount` covers the displayed node count; excess nodes overlap.

[Field overrides](../features/field-overrides.md) can customize `dataOptions`,
`thresholdOptions.thresholds`, and these node styles: `nodeOptions.polygonBorderSize`,
`nodeOptions.shape`, `nodeOptions.gradientsEnabled`, `nodeOptions.fillColor`, and
`nodeOptions.borderColor`. Node sizing (`nodeOptions.autoPolygenSize` and
`nodeOptions.polygenSize`) remains chart-wide.

## Examples

Display fragments:

### Health nodes

```json
{
  "layoutOptions": {
    "autoColumnCount": true,
    "autoRowCount": true,
    "limitCount": 100
  },
  "dataOptions": {
    "showValue": true,
    "calculationType": "lastNotNull",
    "decimals": 2
  },
  "textOptions": {
    "showText": true
  },
  "thresholdOptions": {
    "thresholds": [
      {
        "rule": ">=",
        "value": 0,
        "color": "#67cf98"
      },
      {
        "rule": ">=",
        "value": 1,
        "color": "#ffb96e"
      },
      {
        "rule": ">=",
        "value": 2,
        "color": "#f2887e"
      }
    ]
  }
}
```

### Grouped labeled series

```json
{
  "groupOptions": {
    "enabled": true,
    "groupKey": "group_key",
    "showTitle": true
  },
  "dataOptions": {
    "calculationType": "lastNotNull"
  },
  "textOptions": {
    "showText": true
  }
}
```
