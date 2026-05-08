# Introduction

The Graph Database data source provides you with a bidirectional channel for reading from and writing to Graph Database. This article introduces the Graph Database data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | N |  |
| label | Type name, i.e., vertex/edge name. label supports reading from the source column, for example #{0}, which means taking the 1st column field as the label name. Source column index starts from 0. | Y | None | N |  |
| labelType | The type of label: * Enum value VERTEX represents a vertex. * Enum value EDGE represents an edge. | Y | None | N |  |
| srcLabel | * When label is an edge, represents the source vertex name. When label is an edge and srcIdTransRule is none, this can be left blank; otherwise it is required. * When label is a vertex, leave blank. | N | None | N |  |
| dstLabel | * When label is an edge, represents the destination vertex name. When label is an edge and dstIdTransRule is none, this can be left blank; otherwise it is required. * When label is a vertex, leave blank. | N | None | N |  |
| writeMode | The processing mode when importing duplicate IDs. * Enum value INSERT means an error will be reported and the error record count increases by 1. * Enum value MERGE means overwriting old values with new values. | Y | INSERT | N |  |
| idTransRule | The transformation rule for the primary key ID. * Enum value labelPrefix means converting the mapped value to `{label name}-{source field}`. * Enum value none means the mapped value is not transformed. | Y | none | N |  |
| srcIdTransRule | When label is an edge, represents the transformation rule for the source vertex primary key ID. * Enum value labelPrefix means converting the mapped value to `{label name}-{source field}`. * Enum value none means the mapped value is not transformed, and srcLabel can be left blank. | Required when label is edge | none | N |  |
| dstIdTransRule | When label is an edge, represents the transformation rule for the destination vertex primary key ID. * Enum value labelPrefix means converting the mapped value to `{label name}-{source field}`. * Enum value none means the mapped value is not transformed, and dstLabel can be left blank. | Required when label is edge | none | N |  |
| column | Vertex/edge field mapping configuration. * name: Vertex/edge field name. * value: Vertex/edge field mapping value. Only script mode supports custom string concatenation. * #{N} means directly mapping the source value, where N is the source column index starting from 0. * #{0} means mapping the 1st field of the source column. * test-#{0} means concatenating and transforming the source value; fixed strings can be added before/after the #{0} value. * #{0}-#{1} means concatenating multiple fields; fixed strings can also be added at any position, for example `test-#{0}-test1-#{1}-test2`. * type: The type of the vertex/edge field mapping value. The primary key ID only supports STRING type. GDB Writer will perform forced conversion; the source ID must be convertible to STRING type. Ordinary properties support types: INT, LONG, FLOAT, DOUBLE, BOOLEAN, and STRING. * columnType: The classification of vertex/edge mapping fields. The supported enum values are as follows. * Common enum values primaryKey: When label is vertex/edge, indicates that the field is the primary key ID. * Vertex enum values * vertexProperty: When label is vertex, indicates that the field is a vertex ordinary property. * vertexJsonProperty: When label is vertex, indicates a vertex JSON property. For the value structure, refer to the properties example. * Edge enum values * srcPrimaryKey: When label is edge, indicates that the field is the source vertex primary key ID. * dstPrimaryKey: When label is edge, indicates that the field is the destination vertex primary key ID. * edgeProperty: When label is edge, indicates that the field is an edge ordinary property. * edgeJsonProperty: When label is edge, indicates an edge JSON property. For the value structure, refer to the properties example. properties example ```json {"properties":[ {"k":"name","t":"string","v":"tom"}, {"k":"age","t":"int","v":"20"}, {"k":"sex","t":"string","v":"male"} ]} ``` | Y | None | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "gdb",
  "parameter": {
    "datasource": "",
    "label": "",
    "labelType": "",
    "srcLabel": "",
    "dstLabel": "",
    "writeMode": "",
    "idTransRule": "",
    "srcIdTransRule": "",
    "dstIdTransRule": "",
    "column": []
  },
  "name": "Writer",
  "category": "writer"
}
```
