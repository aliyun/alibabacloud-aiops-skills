# Introduction

The OSS data source provides you with a bidirectional channel for reading from and writing to OSS. It supports reading TXT/CSV, ORC, Parquet, and JSONLine format files, and supports writing TXT/CSV, Parquet format files. OSS is an unstructured data source that stores file-type data, so when using synchronization, you need to first confirm whether the synchronized field structure meets your expectations.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| object | OSS Object information. Multiple Objects can be filled in here. Supports using wildcards to match multiple Objects. Supports using scheduling parameters to flexibly generate Object file names and paths in conjunction with scheduling. | Y | None | Y | Display condition: fileFormat != parquet. The data synchronization system treats all Objects synchronized under one job as the same data table. You must ensure that all Objects can adapt to the same Schema; please control the number of files in a single directory, otherwise it may trigger a system OutOfMemoryError |
| path | Parquet file path. | Required for parquet format | None | Y | Display condition: fileFormat = parquet. Parquet format uses a special path, using the ParquetPathInput component (path input + automatic schema fetching), the object field is not displayed |
| column | The list of fields to be read. type specifies the source data type, index specifies which column in the text the current column comes from (starting from 0), and value specifies the current type as a constant, not reading data from the source file but automatically generating the corresponding column based on the value. | Y | Read all as STRING type | Y | type must be filled in, index/value must choose one |
| fileFormat | Text type, the file type of the source OSS. | Y | csv | Y | Frontend options: public cloud displays all (csv, text, parquet, orc, jsonl); linkage logic: switching fileFormat clears object and table structure confirmation state |
| fieldDelimiter | The field delimiter for reading. | Y | , | Frontend prerequisite: fileFormat is csv or text. If the delimiter is invisible, please fill in the Unicode encoding, such as `\u001b`, `\u007c`. Frontend default value: `,` |
| lineDelimiter | The line delimiter for reading. | N | None | Y | Display condition: fileFormat is text. Only effective when fileFormat is text |
| compress | Text compression type. Default is not filled in, meaning no compression. | N | No compression | Y | Display condition: fileFormat is csv or text. Supports gzip, bzip2, and zip. A single compressed package does not allow multi-file packaging and compression |
| encoding | The encoding configuration for reading files. | N | UTF-8 | Y | Display condition: fileFormat is csv or text. Frontend default value: UTF-8 |
| nullFormat | In text files, null cannot be defined using standard strings. Data synchronization provides nullFormat to define which strings can represent null. | N | None | Y | Display condition: fileFormat != parquet. If not configured, source data is written directly to the destination without conversion |
| skipHeader | CSV-like format files may have headers as titles that need to be skipped. | N | false | Y | Display condition: fileFormat is csv or text. Skip header is not supported in compressed file mode. Frontend default value: false |
| parquetSchema | Configured when reading OSS in Parquet file format, representing the type description of parquet storage. | N | None | N | Display condition: fileFormat is parquet. Only effective when fileFormat is parquet |
| csvReaderConfig | Parameter configuration for reading CSV type files, Map type. Uses CsvReader for reading CSV type files; if not configured, default values are used. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

General read example:

```json
{
  "stepType": "oss",
  "parameter": {
    "datasource": "oss_source",
    "column": [
      {"index": 0, "type": "string"},
      {"index": 1, "type": "long"},
      {"index": 2, "type": "double"},
      {"index": 3, "type": "boolean"},
      {"index": 4, "type": "date", "format": "yyyy-MM-dd HH:mm:ss"}
    ],
    "fieldDelimiter": ",",
    "fileFormat": "csv",
    "object": ["path/to/file.txt"],
    "encoding": "utf-8",
    "nullFormat": "",
    "skipHeader": "false"
  },
  "name": "Reader",
  "category": "reader"
}
```

ORC file read example:

```json
{
  "stepType": "oss",
  "parameter": {
    "datasource": "oss_source",
    "fileFormat": "orc",
    "path": "/tests/case61/orc__691b6815_9260_4037_9899_****",
    "column": [
      {"index": 0, "type": "long"},
      {"index": "1", "type": "string"},
      {"index": "2", "type": "string"}
    ]
  },
  "name": "Reader",
  "category": "reader"
}
```

Parquet file read example:

```json
{
  "stepType": "oss",
  "parameter": {
    "datasource": "oss_source",
    "fileFormat": "parquet",
    "path": "/*",
    "parquetSchema": "message m { optional BINARY registration_dttm (UTF8); optional Int64 id; optional BINARY first_name (UTF8); optional BINARY last_name (UTF8); optional DOUBLE salary; }",
    "column": [
      {"index": "0", "type": "string"},
      {"index": "1", "type": "long"},
      {"index": "2", "type": "string"},
      {"index": "3", "type": "string"},
      {"index": "4", "type": "double"}
    ],
    "object": ["wpw_demo/userdata1.parquet"],
    "fieldDelimiter": ",",
    "encoding": "UTF-8"
  },
  "name": "Reader",
  "category": "reader"
}
```

JSONLine format file read example:

```json
{
  "stepType": "oss",
  "parameter": {
    "datasource": "oss_source",
    "column": [
      {"name": "chunk_text", "index": 0, "type": "string"}
    ],
    "fieldDelimiter": ",",
    "encoding": "UTF-8",
    "fileFormat": "jsonl",
    "object": ["embedding/chunk1.jsonl"]
  },
  "name": "Reader",
  "category": "reader"
}
```
