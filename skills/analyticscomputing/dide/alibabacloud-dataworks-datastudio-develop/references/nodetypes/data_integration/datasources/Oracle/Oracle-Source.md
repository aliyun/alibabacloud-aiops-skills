# Introduction

The Oracle data source provides you with a bidirectional channel for reading from and writing to Oracle, making it convenient for you to configure data synchronization tasks through wizard mode and script mode. This article introduces the Oracle data synchronization capabilities of DataWorks.

# Source
## Parameter Description
| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. | Y | None | Y | |
| selectedDatabase | The schema of the database to be synchronized. | Depends on data source type | None | Y | Display condition: displayed when the data source supports it; linkage logic: switching clears table and triggers table switch event |
| table | The name of the table to be synchronized. | Y | None | Y | After selecting a table, column information is automatically fetched |
| column | Synchronization column collection (JSON array). Supports column pruning, column reordering, and constant configuration. Must be explicitly specified and cannot be empty. | Y | None | Y | |
| splitPk | The field used for data sharding, which can start concurrent tasks to improve efficiency. Using the table primary key is recommended. Only supports numeric or string types. | N | None | Y | |
| splitMode | Split mode, used in conjunction with splitPk. averageInterval (average sampling, suitable for numeric splitPk), randomSampling (random sampling, suitable for string splitPk). | Y | randomSampling | Y | Frontend option; frontend default value: randomSampling |
| where | Filter condition. The system assembles SQL based on column, table, and where for extraction. Can be effectively used for business incremental synchronization; when not configured or empty, full table synchronization is performed. | N | None | Y | |
| fetchSize | The number of data records fetched in each batch between the plugin and the database server, determining the number of network interactions and affecting extraction performance. | N | 1000 | Y | Frontend default value: 1000 |
| encoding | Encoding format. | N | None | Y | |
| socketTimeout | Socket timeout (milliseconds). | N | None | Y | |
| session | Session parameter configuration. | N | None | Y | Supports multiple entries |
| masterSlave | Master/slave database selection. | Y | None | Y | Display condition: in-elastic environment; frontend option |
| checkSlave | Slave priority selection check. | Y | None | Y | Display condition: in-elastic environment |
| hint | SQL Hint. | N | None | Y | Example: `/*+parallel(@table,4)*/` |
| splitFactor | Split factor, configuring the number of splits for synchronized data. When using multi-concurrency, splits are made by `concurrency × splitFactor`. | N | 5 | N | Recommended value range 1~100, too large may cause out of memory |
| querySql | Custom filter SQL. When configured, table, column, and where conditions will be directly ignored. Suitable for complex scenarios such as multi-table joins. | N | None | N | Advanced mode |

## Configuration Example

```json
{
  "stepType": "oracle",
  "parameter": {
  "selectedDatabase": "AUTOTEST",
  "datasource": "oracle_test",
  "envType": 0,
  "column": [
      "id"
  ],
  "where": "",
  "splitPk": "id",
  "table": "AUTOTEST.table01"
  },
  "name": "Reader",
  "category": "reader"
 }
```
