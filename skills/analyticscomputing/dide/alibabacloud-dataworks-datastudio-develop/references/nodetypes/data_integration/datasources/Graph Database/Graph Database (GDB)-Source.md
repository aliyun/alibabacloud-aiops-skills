# Introduction

The Graph Database data source provides you with a bidirectional channel for reading from and writing to Graph Database. This article introduces the Graph Database data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| host | The connection domain of the GDB instance. You can view the **Internal Network Address** (i.e., host) by going to the [Graph Database GDB Console](https://gdb.console.aliyun.com/?accounttraceid=b2e3929cd5bc46c38cd944aaf6abc6a9bzwz#/InstanceList?regionId=cn-shanghai), and clicking **Manage** next to the corresponding instance. | Y | None | N |  |
| port | The connection port of the GDB instance. | Y | 8182 | N |  |
| username | The account name of the GDB instance. | Y | None | N |  |
| password | The password of the GDB instance account. | Y | None | N |  |
| labels | The type name, i.e., the name of a vertex or edge. Supports reading data from multiple names, represented using an array, for example \["label1", "label2"\]. | Y | None | N |  |
| labelType | The Label type of the data: * Enum value VERTEX represents a vertex. * Enum value EDGE represents an edge. | Y | None | N |  |
| column | Vertex or edge field mapping configuration. | Y | None | N |  |
| column -\> name | The field name of the vertex or edge mapping relationship. Required when reading properties, please provide the property name. | Y | None | N |  |
| column -\> type | The field value type of the vertex or edge mapping relationship: * The primary key ID and type name Label are both STRING types in GDB. If you configure them as STRING type, the conversion will fail. * Ordinary properties support INT, LONG, FLOAT, DOUBLE, BOOLEAN, STRING, and other types. * GDB Reader will try to convert the read data to the configured type, but conversion failure will result in an error for that record. | Y | None | N |  |
| column -\> columnType | The vertex or edge mapping field corresponding to the GDB vertex or edge data, including the following enum values: * Common enum values: * primaryKey: Indicates that the field is the primary key ID. * primaryLabel: Indicates that the field is the name Label. * Vertex enum values: * vertexProperty: When labelType is vertex, indicates that the field is a vertex property. * vertexJsonProperty: When labelType is vertex, indicates that the field is a collection of vertex properties, encapsulated in JSON format. When this type is configured, all properties will be packed into this column, and the column cannot contain other property types. The vertexJsonProperty format is as follows. ```json { "properties":[ {"k":"name","t":"string","v":"tom","c":"set"}, {"k":"name","t":"string","v":"jack","c":"set"}, {"k":"sex","t":"string","v":"male","c":"single"} ] } ``` The exported properties above include a multi-valued property name with two property values and a single-valued property. If a multi-valued property in GDB contains only one property value, it will be exported as a single-valued property. * Edge enum values when labelType is edge: * srcPrimaryKey: Indicates that the field is the source vertex primary key ID. * dstPrimaryKey: Indicates that the field is the destination vertex primary key ID. * srcPrimaryLabel: Indicates that the field is the source vertex name Label. * dstPrimaryLabel: Indicates that the field is the destination vertex name Label. * edgeProperty: Indicates that the field is an edge property. * edgeJsonProperty: Indicates that the field is a collection of edge properties, encapsulated in JSON format. When this type is configured, all properties will be packed into this column, and the column cannot contain other property types. The edgeJsonProperty format is as follows. ```json { "properties":[ {"k":"name","t":"string","v":"tom"}, {"k":"sex","t":"string","v":"male"} ] } ``` Edges do not support multi-valued properties and have no c field. | Y | None | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "gdb",
  "parameter": {
    "host": "",
    "port": 1024,
    "username": "",
    "password": "",
    "labels": "",
    "labelType": "",
    "column": [],
    "column -\\> name": "",
    "column -\\> type": "",
    "column -\\> columnType": ""
  },
  "name": "Reader",
  "category": "reader"
}
```
