# Topology

Use when showing explicit parent/child relationships, with optional node and edge metrics.

## Usage

- Return parent/child type and ID fields. Remove empty nodes and self-links.
- Use a Logstore query returning the complete relationship table. Do not infer links from similar names.
- Relationship queries contribute to one graph in query order. The first query with incomplete parent/child type and ID bindings stops relationship processing for itself and all subsequent queries; earlier relationships remain. Put all relationship queries before metrics-only queries.
- Repeated nodes and repeated edges in the same direction collapse to one node or edge.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.child_node_type` | string | Yes | None | Column containing child node types. |
| `queryOptionMap.<queryName>.child_node_id` | string | Yes | None | Column containing child IDs; type and ID together identify a node. |
| `queryOptionMap.<queryName>.parent_node_type` | string | Yes | None | Column containing parent node types. |
| `queryOptionMap.<queryName>.parent_node_id` | string | Yes | None | Column containing parent IDs. |
| `topoGraphOptions.layoutType` | string | No | fdp | fdp for force-directed networks; dot for hierarchies; circo for circular layouts. |
| `topoGraphOptions.nodeType` | string | No | text_node | text_node, icon_node, or metric_node. |
| `topoGraphOptions.showLabel` | boolean | No | true | Show node names. |
| `topoGraphOptions.showEdgeMetrics` | boolean | No | false | Show configured metrics on edges. |
| `nodeMetricOptions[].nodeType` | string | For node metrics | None | Node type to match, or all for every type. |
| `nodeMetricOptions[].name` | string | No | — | Configuration label; conventionally matches nodeType. |
| `nodeMetricOptions[].metrics[].metricGroup` | string | For a metric | None | Query name containing node IDs and metric values. |
| `nodeMetricOptions[].metrics[].nodeIdField` | string | For a metric | None | Column matched against node IDs. |
| `nodeMetricOptions[].metrics[].metricKey` | string | For a metric | None | Numeric metric column. |
| `nodeMetricOptions[].metrics[].metricName` | string | No | — | Metric display name. |
| `nodeMetricOptions[].metrics[].metricUnit` | string | No | — | Metric unit. |
| `nodeMetricOptions[].metrics[].metricDecimal` | number | No | 2 | Decimal places. |
| `nodeMetricOptions[].metrics[].metricFormat` | string | No | — | Number format. |
| `nodeMetricOptions[].metrics[].colorSchema.mode` | string | No | — | fixed uses color; threshold uses thresholds. |
| `nodeMetricOptions[].metrics[].colorSchema.color` | string | For fixed color | None | Metric color. |
| `nodeMetricOptions[].metrics[].colorSchema.thresholds` | object[] | For threshold color | None | Threshold color rules. |
| `nodeMetricOptions[].metrics[].openCluster` | boolean | No | false | Use metric values to group nodes; the metric is then not displayed as an ordinary value. |
| `edgeFieldOptions[].name` | string | For edge configuration | None | Query supplying the edges. |
| `edgeFieldOptions[].fields` | object[] | For edge labels | None | Edge fields with display names, units, and formats. |
| `edgeFieldOptions[].fields[].metricKey` | string | For an edge metric | None | Source value column. |
| `edgeFieldOptions[].fields[].metricName` | string | No | — | Metric label. |
| `edgeFieldOptions[].fields[].metricUnit` | string | No | — | Unit suffix. |
| `edgeFieldOptions[].fields[].metricFormat` | string | No | — | Number format. |
| `edgeFieldOptions[].fields[].metricDecimal` | number | No | 4 | Decimal places. |
| `edgeFieldOptions[].colorConfigMode` | string | No | Standard edge color | fixed uses color; threshold uses colorConfigs. |
| `edgeFieldOptions[].color` | string | For fixed color | None | Edge color. |
| `edgeFieldOptions[].colorConfigs` | object[] | For metric color | None | Field, comparison, and threshold rules for edge colors. |
| `edgeFieldOptions[].colorConfigs[].metricKey` | string | For a color rule | None | Numeric column to compare; zero values are not matched. |
| `edgeFieldOptions[].colorConfigs[].joiner` | string | For a color rule | None | Use >, >=, <, or <=. Equality and inequality are not reliable for these edge rules. |
| `edgeFieldOptions[].colorConfigs[].threshold` | number | For a color rule | None | Compared value. |
| `edgeFieldOptions[].colorConfigs[].color` | string | For a color rule | None | Applied color; the last matching rule wins. |
| `edgeFieldOptions[].widthKey` | string | No | None | Numeric column used to scale edge widths between the result's minimum and maximum. |
| `actionOptions` | object[] | No | [] | Node/query click actions; see actions. |

See [actions](../features/actions.md) and [standard formatting](../features/standard-options.md).

Node metrics attach to existing relationship nodes using the configured node type
and `nodeIdField`; metrics-only queries do not create nodes or edges.

Edge color rules and `widthKey` read values from the same relationship row in the
query named by `edgeFieldOptions[].name`. Missing or nonnumeric metric values fall
back to the default edge style.

## Examples

Display fragments:

### Directed dependency

```json
{
  "queryOptionMap": {
    "A": {
      "parent_node_type": "parent_type",
      "parent_node_id": "parent_id",
      "child_node_type": "child_type",
      "child_node_id": "child_id"
    }
  },
  "topoGraphOptions": {
    "layoutType": "dot",
    "nodeType": "text_node",
    "showLabel": true,
    "showEdgeMetrics": false
  }
}
```

### Network dependency

For a force-directed network, keep the same bindings and set `topoGraphOptions.layoutType` to `fdp`.
