# Introduction

The Azure Blob Storage data source provides you with the ability to read files. You can use this data source to obtain files stored in Azure Blob Storage, parse them, and synchronize them to any destination data source. This article introduces DataWorks' support for Azure Blob Storage data synchronization capabilities.

> **Supported Direction**: This data source only supports being used as a source (read), and does not support being used as a destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| fileFormat | Source file type. | Y | csv | Y | Frontend default value: `csv`; Linkage logic: Switching fileFormat clears object and table schema confirmation status |
| object | File path, supports wildcards and arrays. For example, `a/b/*.csv` or configure multiple file paths simultaneously. | Required when fileFormat != parquet | None | Y | Display condition: fileFormat != parquet; The data synchronization system treats all files synchronized under one job as the same data table, so you must ensure all files can adapt to the same Schema |
| path | Parquet/ORC file path, supports wildcards and arrays. | Required when parquet format | None | Y | Display condition: fileFormat = parquet; Parquet format uses a special path; getTableColumn is automatically called on path input/blur to retrieve column information, no SchemaConfirm needed |
| column | List of fields to read. type specifies the source data type, index specifies which column in the text the current column comes from (starting from 0), value specifies the current type as a constant, which is not read from the source file but auto-generated based on the value. | Y | Read all as STRING type | Y | type must be specified, and either index or value must be selected |
| fieldDelimiter | Field delimiter for reading. | Y when fileFormat is csv/text | , | Y | Display condition: fileFormat is csv or text; If the delimiter is not visible, please use Unicode encoding, such as `\u001b`, `\u007c`; Frontend default value: `,` |
| lineDelimiter | Line delimiter for reading. | N | None | Y | Display condition: fileFormat is text |
| compress | Text compression type. Default is no compression when not specified. | N | No compression | Y | Display condition: fileFormat is csv or text; Supports gzip, bzip2, and zip |
| encoding | Encoding configuration for reading files. | N | UTF-8 | Y | Display condition: fileFormat is csv or text; Frontend default value: UTF-8 |
| nullFormat | In text files, null cannot be defined using standard strings. Data synchronization provides nullFormat to define which strings can represent null. | N | None | Y | Display condition: fileFormat != parquet; If not configured, source data is written directly to the destination without conversion |
| skipHeader | CSV-like format files may have a header row that needs to be skipped. | N | false | Y | Display condition: fileFormat is csv or text; skipHeader is not supported in compressed file mode; Frontend default value: false |
| parquetSchema | Configured when reading Azure Blob Storage in Parquet file format. Takes effect only when **fileFormat** is **parquet**, specifically representing the type description of Parquet storage. | N | None | N | |
| csvReaderConfig | Parameter configuration for reading CSV type files, configured as Map type. Uses CsvReader for reading CSV type files; if not configured, default values are used. | N | None | N | |
| maxRetryTimes | Maximum number of retries when file download fails. | N | 0 | N | |
| retryIntervalSeconds | Retry interval when file download fails, in seconds. | N | 5 | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
      "stepType": "azureblob",
      "parameter": {
        "datasource": "",
        "object": ["f/z/1.csv"],
        "fileFormat": "csv",
        "encoding": "utf8/gbk/...",
        "fieldDelimiter": ",",
        "useMultiCharDelimiter": true,
        "lineDelimiter": "\n",
        "skipHeader": true,
        "compress": "zip/gzip",
        "column": [
          {
            "index": 0,
            "type": "long"
          },
          {
            "index": 1,
            "type": "boolean"
          },
          {
            "index": 2,
            "type": "double"
          },
          {
            "index": 3,
            "type": "string"
          },
          {
            "index": 4,
            "type": "date"
          }
        ]
      },
      "name": "Reader",
      "category": "reader"
    }
```
