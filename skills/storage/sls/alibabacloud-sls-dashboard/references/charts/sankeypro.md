# Sankey

Use when showing directed flows between stages.

Start with the [directed flow dashboard](../../assets/dashboards/charts/sankeypro.json)
for a complete example.

## Usage

- Supply non-empty source/target names and non-negative flow values.
- The graph must be acyclic. Exclude self-links and cycles, and bound nodes and edges. Use topology for general dependencies.
- All queries contribute edges to one graph, not separate layers, and are not joined. Bind source, target, and weight within the same query.
- Rows with empty endpoints, duplicate edges, and reverse edges of already-seen edges are filtered out. Only the first occurrence is retained; weights are not summed. Aggregate flows in the query before charting.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.sourceKey` | string | Yes | None | Source-node column. |
| `queryOptionMap.<queryName>.targetKey` | string | Yes | None | Target-node column. |
| `queryOptionMap.<queryName>.numFieldKey` | string | Yes | None | Flow weight column; invalid or missing weights become 1, so validate input in the query. |
| `sankeyOptions.linkColorMode` | string | No | static | static uses the value-field color; source or target follows that node; source-target uses a gradient. |
| `sankeyOptions.nodeAlignment` | string | No | center | left, right, center, or justify; justify places source and sink nodes at opposite ends. |

## Examples

Display fragments:

### Directed flow

```json
{
  "isTimeSeries": false,
  "queryOptionMap": {
    "A": {
      "sourceKey": "source",
      "targetKey": "target",
      "numFieldKey": "value"
    }
  },
  "sankeyOptions": {
    "linkColorMode": "source-target",
    "nodeAlignment": "justify"
  }
}
```
