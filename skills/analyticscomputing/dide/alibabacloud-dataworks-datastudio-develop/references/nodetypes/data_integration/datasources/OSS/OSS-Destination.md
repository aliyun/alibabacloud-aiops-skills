# Introduction

The OSS data source provides you with a bidirectional channel for reading from and writing to OSS. It supports reading TXT/CSV, ORC, Parquet, and JSONLine format files, and supports writing TXT/CSV, ORC, and Parquet format files. OSS is an unstructured data source that stores file-type data, so when using synchronization, you need to first confirm whether the synchronized field structure meets your expectations.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| fileFormat | The format of the file output. | Y | csv | Y | Frontend options: public cloud displays all (csv, text, parquet, orc); linkage logic: switching fileFormat clears object/path/fileName and resets table structure state |
| object | The file name (including path) written by OSS Writer. OSS uses file names to simulate directories. | Required when fileFormat != parquet | None | Y | Display condition: fileFormat != parquet. Objects written using `"object": "datax"` start with datax and have a random UUID suffix added; if you do not need a random suffix, it is recommended to configure writeSingleObject as true |
| path | Parquet file path. | Required when fileFormat = parquet | None | Y | Display condition: fileFormat = parquet. Fill in the path of the parquet file on OSS, for example compute/disk01/pub |
| fileName | Parquet file name. | Required when fileFormat = parquet | None | Y | Display condition: fileFormat = parquet. Only effective when fileFormat is parquet |
| writeMode | OSS Writer pre-write data processing method. truncate=clear all Objects matching the prefix; append=no processing, write directly, using random UUID suffix to ensure no file name conflicts; nonConflict=if an Object with a matching prefix appears at the specified path, report an error directly. | Y | truncate | Y | Frontend options: truncate (clear) / append (append) / nonConflict (conflict error). Frontend default value: truncate (replace existing files) |
| writeHeader | Output header on the first line. Select "Yes/No" through Radio. When selected, writeHeader will be written to the targetExtend of the column mapping component. | N | false | Y | Display condition: fileFormat is csv or text. Linkage logic: after switching, notifies the column mapping component to recalculate |
| fieldDelimiter | The field delimiter for writing. | Required when fileFormat is csv/text | , | Y | Display condition: fileFormat is csv or text. Frontend default value: ,. If the delimiter is invisible, please fill in the Unicode encoding |
| lineDelimiter | The line delimiter for writing. | N | None | Y | Display condition: fileFormat is text |
| encoding | The encoding configuration for writing files. | N | UTF-8 | Y | Display condition: fileFormat is csv or text. Frontend default value: UTF-8 |
| nullFormat | In text files, null cannot be defined using standard strings. nullFormat is provided to define strings that can represent null. | N | None | Y | Display condition: fileFormat is csv, text, or orc. If not configured, source data is written directly to the destination without conversion |
| dateFormat | The output format for date type fields. | N | None | Y | Display condition: fileFormat is csv or text |
| compress | The compression format for data files written to OSS. | N | Empty (no compression) | Y | Display condition: fileFormat is parquet or orc. Frontend default value: empty (no compression). csv/text does not support compression; parquet/orc supports gzip, snappy, etc. |
| writeSingleObject | Whether to write a single file when writing data to OSS. true=write a single file, no empty file is generated when no data can be read; false=write multiple files, an empty file is output when no data can be read. | N | false | Y | Display condition: fileFormat is csv or text. This parameter does not take effect when writing ORC or parquet type data |
| maxFileSize | The maximum size of a single Object file when OSS writes out. | N | 10000 | Y | Display condition: fileFormat is csv or text. Frontend default value: 10000 (MB). Advanced configuration, based on task process memory-level statistics, cannot precisely control the actual size of the destination file |
| parquetSchema | Describes the structure of the destination file when writing to OSS in Parquet file format. | Required when fileFormat = parquet | None | N | Display condition: fileFormat is parquet. Only effective when fileFormat is parquet |
| ossBlockSize | OSS block size. | N | 16 | Y | Default unit is MB, only parquet/orc format is supported; OSS block upload supports up to 10000 blocks, default single file size limit is 160GB |
| generateEmptyFile | Whether to generate an empty file when the source has no data during OSS data writing. | N | true | Y | |

> Y = Yes, N = No

## Configuration Example

General write example:

```json
{
  "stepType": "oss",
  "parameter": {
    "datasource": "oss_target",
    "object": "datax",
    "writeMode": "append",
    "fileFormat": "csv",
    "fieldDelimiter": ",",
    "encoding": "utf-8",
    "nullFormat": "",
    "writeSingleObject": "false"
  },
  "name": "Writer",
  "category": "writer"
}
```

ORC file write example:

```json
{
  "stepType": "oss",
  "parameter": {
    "datasource": "oss_target",
    "fileFormat": "orc",
    "path": "/tests/case61",
    "fileName": "orc",
    "writeMode": "append",
    "column": [
      {"name": "col1", "type": "BIGINT"},
      {"name": "col2", "type": "DOUBLE"},
      {"name": "col3", "type": "STRING"}
    ],
    "fieldDelimiter": "\t",
    "compress": "NONE",
    "encoding": "UTF-8"
  },
  "name": "Writer",
  "category": "writer"
}
```

Parquet file write example:

```json
{
  "stepType": "oss",
  "parameter": {
    "datasource": "oss_target",
    "fileFormat": "parquet",
    "path": "/tests/case61",
    "fileName": "test",
    "writeMode": "append",
    "fieldDelimiter": "\t",
    "compress": "SNAPPY",
    "encoding": "UTF-8",
    "parquetSchema": "message test { required int64 int64_col; required binary str_col (UTF8); }",
    "dataxParquetMode": "fields"
  },
  "name": "Writer",
  "category": "writer"
}
```
