# Introduction

DataWorks Data Integration supports using Doris Writer to import table data into Doris. This article introduces the Doris data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The name of the table selected for synchronization. | Y | None | Y | |
| column | The fields in the target table that need to be written with data, separated by English commas. For example, `"column":["id","name","age"]`. To write all columns sequentially, use `*`, for example, `"column":["*"]`. | Y | None | Y | |
| preSql | SQL statements executed before the data synchronization task starts. | N | None | Y | |
| postSql | SQL statements executed after the data synchronization task completes. | N | None | Y | |
| loadProps | StreamLoad request parameters, used to configure the data format for import. | N | None | Y | `format` frontend default value: `csv`; frontend options: `CSV` → `csv`, `JSON` → `json`. Linkage logic: switching format displays the corresponding sub-parameters.<br/><br/>**When format=csv**:<br/>```json<br/>{ "format": "csv", "column_separator": "\\t", "line_delimiter": "\\n" }<br/>```<br/>• `column_separator`: Column separator, default `\t`<br/>• `line_delimiter`: Line delimiter, default `\n`<br/><br/>**When format=json**:<br/>```json<br/>{ "format": "json", "strip_outer_array": true }<br/>```<br/>• `strip_outer_array`: Whether to strip the outermost array structure, default `true` |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "doris",//Plugin name.
  "parameter":
  {
    "postSql"://SQL statements executed after the data synchronization task.
    [],
    "preSql":
    [],//SQL statements executed before the data synchronization task.
    "datasource":"doris_datasource",//Data source name.
    "table": "doris_table_name",//Table name.
    "column":
    [
      "id",
      "table_id",
      "table_no",
      "table_name",
      "table_status"
    ],
    "loadProps":{
      "column_separator": "\\x01",//Specify the column separator for CSV format
      "line_delimiter": "\\x02"//Specify the line delimiter for CSV format
    }
  },
  "name": "Writer",
  "category": "writer"
}
```
