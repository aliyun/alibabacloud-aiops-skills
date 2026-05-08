# Introduction

DataWorks Data Integration supports using SelectDB Writer to import table data into SelectDB. This article introduces the data synchronization capabilities of DataWorks for SelectDB.

> **Supported Direction**: This data source only supports being used as a destination (write), and does not support being used as a source (read).

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| table | The name of the selected table to be synced. | Y | None | Y |  |
| column | The fields in the destination table to write data to, separated by commas. For example `"column":["id","name","age"]`. To write all columns sequentially, use `(*)`, for example `"column":["*"]`. | Y | None | Y |  |
| preSql | The SQL statements that must be executed first before the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple SQL statements, for example, to clear old data before execution. | N | None | Y |  |
| postSql | The SQL statements executed after the data synchronization task. Currently, wizard mode only allows executing one SQL statement, while script mode supports multiple SQL statements, for example, to add a timestamp. | N | None | Y |  |
| maxBatchRows | The maximum number of rows per batch of imported data. Together with batchSize, it controls the number of imports per batch. When either threshold is reached, the batch of data starts importing. | N | 500000 | Y |  |
| batchSize | The maximum data size per batch of imported data. Together with maxBatchRows, it controls the number of imports per batch. When either threshold is reached, the batch of data starts importing. | N | 94371840 | Y |  |
| maxRetries | The number of retries after a batch data import failure. | N | 3 | Y |  |
| labelPrefix | The label prefix for each batch of uploaded files. The final label is composed of `labelPrefix + UUID` to form a globally unique label, ensuring data is not imported repeatedly. | N | datax_selectdb_writer_ | Y |  |
| loadProps | The COPY INTO request parameters, mainly used to configure the format of imported data. JSON format is used by default. If loadProps is not configured, or is configured as `"loadProps":{}`, the default JSON format is used. The configuration is as follows. (Currently, SelectDB only supports `strip_outer_array=true`). ```json "loadProps": { "format": "json", "strip_outer_array":true } ``` If you need to specify CSV format for import, you can specify the CSV format and configure row and column delimiters as follows. If you do not specify row and column delimiters, the incoming data will be converted to strings by default, with `\t` as the column delimiter and `\n` as the row delimiter, forming a CSV file for SelectDB import. ```json "loadProps": { "format":"csv", "column_separator": "\\x01", "line_delimiter": "\\x02" } ``` | N | None | Y |  |
| clusterName | SelectDB Cloud cluster name. You can view it in the [SelectDB Console](https://cn.selectdb.com/). | N | None | Y |  |
| flushInterval | The time interval for data write batches (in ms). If maxBatchRows and batchSize parameters are set to large values, the system may execute data import based on the write time interval before reaching the configured data size. | N | 30000 | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "selectdb",//Plugin name.
  "parameter":
  {
    "postSql"://SQL statements executed first after the data synchronization task.
    [],
    "preSql":
    [],//SQL statements executed first before the data synchronization task.
    "datasource":"selectdb_datasource",//Data source name.
    "table": "selectdb_table_name",//Table name.
    "column":
    [
      "id",
      "table_id",
      "table_no",
      "table_name",
      "table_status"
    ],
    "loadProps":{
      "format":"csv",//Specify CSV format
      "column_separator": "\\x01",//Specify column delimiter
      "line_delimiter": "\\x02"//Specify line delimiter
    }
  },
  "name": "Writer",
  "category": "writer"
}
```
