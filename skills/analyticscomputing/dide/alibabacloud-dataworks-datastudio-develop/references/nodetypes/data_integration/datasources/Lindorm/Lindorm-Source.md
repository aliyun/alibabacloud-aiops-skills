# Introduction

DataWorks Data Integration supports using the Lindorm Reader and Lindorm Writer plugins to read from and write to Lindorm via a bidirectional channel. This article introduces the Lindorm data reading and writing capabilities of DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| configuration | The configuration information provided by each Lindorm cluster for the DataX client connection. You can query it through the Lindorm cluster console. After obtaining the configuration information, you can contact the Lindorm database administrator to convert it to the following JSON format: *{"key1":"value1","key2":"value2"}* . For example: *{"lindorm.zookeeper.quorum":"????","lindorm.zookeeper.property.clientPort":"????"}* **Note** If you are writing JSON code manually, you need to escape the double quotes in the *value* of the JSON format as *\\"* . | Y | None | Y |  |
| mode | Indicates the data reading mode, including FixedColumn mode and DynamicColumn mode. FixedColumn is selected by default. | Y | FixedColumn | Y |  |
| tableMode | Includes normal table mode (table) and wide column mode (wideColumn). The default is table. If you select table mode, you do not need to fill it in. | N | Default not filled | Y |  |
| table | The name of the Lindorm table to be read. Lindorm table names are case-sensitive. | Y | None | Y |  |
| namespace | The namespace of the Lindorm table to be read. Lindorm table namespaces are case-sensitive. | Y | None | Y |  |
| encoding | Encoding method, values are UTF-8 or GBK. Generally used to convert Lindorm byte[] type stored in binary to String type. | N | UTF-8 | Y |  |
| caching | The number of records fetched in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and Lindorm, and improve overall throughput. If this value is set too large, it may cause excessive pressure on the Lindorm server or OOM exceptions in the data synchronization runtime process. | N | 100 | Y |  |
| selects | The current Table type data read does not support automatic shard splitting, and runs with single concurrency by default. Therefore, you need to manually configure the selects parameter for data slicing. Only primary key columns and index columns are allowed as query conditions; when a table contains multiple primary key columns, the query conditions must follow the leftmost matching principle of primary keys. | N | None | Y | |
| columns | The list of fields to be read. Supports column pruning and column reordering. For table type tables, just fill in the column names; for widecolumn type tables, fill in the format `"STRING\|rowkey"`, `"INT\|f:a"`, `"DOUBLE\|f:b"`. | Y | None | Y | |
| hint | Lindorm query optimization parameter, generally used to control index access. Available options are NO_INDEX, USE_INDEX, and NO_SEARCHINDEX, which mean no index, use index, and no search index respectively. | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "lindorm",
  "parameter": {
    "configuration": "",
    "mode": "",
    "tableMode": "",
    "table": "",
    "namespace": "",
    "encoding": "",
    "caching": "",
    "selects": "",
    "columns": [],
    "hint": ""
  },
  "name": "Reader",
  "category": "reader"
}
```
