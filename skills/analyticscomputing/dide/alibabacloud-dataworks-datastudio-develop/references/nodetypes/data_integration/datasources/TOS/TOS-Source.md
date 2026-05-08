# Introduction

The TOS data source provides you with the ability to read TOS files. You can use this data source to obtain files stored in TOS, parse them, and sync them to any destination data source. This article introduces the data synchronization capabilities of DataWorks for TOS.

> **Supported Direction**: This data source only supports being used as a source (read), and does not support being used as a destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| fileFormat | Source file type. Supports `csv`, `text`, `parquet`, `orc`. | Y | None | Y |  |
| object | File path. Used when fileFormat is `csv` or `text`. **Note** This parameter supports `*` wildcards and can be configured as an array. For example: If you need to sync both `a/b/1.csv` and `a/b/2.csv`, you can configure it as `a/b/*.csv`. | Y (Required when fileFormat is `csv` or `text`) | None | Y |  |
| column | The list of fields to read. type specifies the data type of the source, index specifies which column in the text the current column comes from (starting from 0), and value specifies that the current type is a constant, not reading data from the source file but auto-generating the corresponding column based on the value. * By default, you can read all data as String type, configured as follows. ```json column": ["*"] ``` * You can specify column field information, configured as follows. ```json "column": { "type": "long", "index": 0 //Get the int field from the first column of the TOS text. }, { "type": "string", "value": "alibaba" //Generate an "alibaba" string field from within TOS as the current field. } ``` **Note** For the **column** information you specify, type must be filled in, and you must choose either index or value. | Y | Read all as `STRING` type. | Y |  |
| fieldDelimiter | The field delimiter for reading. **Note** * TOS Reader needs to specify a field delimiter when reading data. If not specified, the default is (,), and the interface configuration will also default to (,). * If the delimiter is invisible, please fill in the Unicode encoding. For example: `\u001b`, `\u007c`. | Y | `,` | Y |  |
| lineDelimiter | The line delimiter for reading. **Note** This parameter is effective when fileFormat is text. | N | None | Y |  |
| compress | Text compression type. Default is not filled in (i.e., no compression). Supported compression types are `gzip`, `bzip2`, and `zip`. | N | `No compression` | Y |  |
| encoding | The encoding configuration for reading files. | N | `utf-8` | Y |  |
| nullFormat | In text files, null (null pointer) cannot be defined using standard strings. The data synchronization system provides nullFormat to define which strings can represent null. For example: * Configure `nullFormat:"null"`, which is equivalent to a "visible character". If the source data is null, data synchronization treats it as a null field. * Configure `nullFormat:"\u0001"`, which is equivalent to an "invisible character". If the source data is the string "\\u0001", data synchronization treats it as a null field. * Not writing the `"nullFormat"` parameter is equivalent to "not configured", meaning whatever data comes from the source is written to the destination as-is, without any conversion. | N | None | Y |  |
| skipHeader | For CSV format files, configure whether to read the header content via **skipHeader**. * True: Read the header content when syncing the data source. * False: Do not read the header content when syncing the data source. **Note** Compressed file mode does not support **skipHeader**. | N | `false` | Y |  |
| parquetSchema | Configured when reading TOS in Parquet file format. Only takes effect when **fileFormat** is **parquet**. It specifically describes the type specification for Parquet storage. You need to ensure that after filling in the parquetSchema, the overall configuration conforms to JSON syntax. ```json message MessageType name { Required/Optional, Data type, Column name; ......................; } ``` * parquetSchema configuration format description: * MessageType name: Fill in the name. * Required/Optional: required means non-null, optional means can be null. It is recommended to fill in optional for all. * Data type: Parquet files support BOOLEAN, Int32, Int64, Int96, FLOAT, DOUBLE, BINARY (for string types, fill in BINARY), and fixed_len_byte_array types. * Each line setting must end with a semicolon, and the last line must also have a semicolon. * Configuration example: ```json "parquetSchema": "message m { optional int32 minute_id; optional int32 dsp_id; optional int32 adx_pid; optional int64 req; optional int64 res; optional int64 suc; optional int64 imp; optional double revenue; }" ``` | N | None | Y |  |
| csvReaderConfig | Configuration parameters for reading CSV type files, configured as Map type. CSV type files are read using csvReader. If not configured, default values are used. | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
      "stepType": "tos",
      "parameter": {
        "datasource": "",
        "object": ["f/z/1.csv"],
        "fileFormat": "csv",
        "encoding": "utf8/gbk/...",
        "fieldDelimiter": ",",
        "useMultiCharDelimiter": true,
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
