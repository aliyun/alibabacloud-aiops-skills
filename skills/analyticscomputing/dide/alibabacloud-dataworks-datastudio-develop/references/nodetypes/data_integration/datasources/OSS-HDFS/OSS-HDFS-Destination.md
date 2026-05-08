# Introduction

OSS-HDFS Service (JindoFS Service) is a cloud-native data lake storage product. The OSS-HDFS data source provides you with a bidirectional channel for reading from and writing to OSS-HDFS. This article introduces the OSS-HDFS data synchronization capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| path | The path information stored in the OSS-HDFS file system. OSS-HDFS Writer will write multiple files under the Path directory according to the concurrency configuration. When associating with a Hive table, please fill in the storage path of the Hive table on OSS-HDFS. | Y | None | Y | |
| fileFormat | The file type. Currently, only text, orc, and parquet are supported for your configuration. * text: Indicates the file write type is text file format. * orc: Indicates the file write type is ORC file format. * parquet: Indicates the file write type is parquet file format. | Y | None | Y | Frontend options: 'text'/'orc'/'parquet'; linkage logic: when fileFormat is 'text', fieldDelimiter is displayed; when 'orc' or 'parquet', fieldDelimiter is hidden. |
| fileName | The file name when OSS-HDFS Writer writes. During actual execution, a random suffix will be added to this file name as the actual file name written by each thread. | Y | None | Y | |
| writeMode | OSS-HDFS Writer pre-write data cleanup processing mode: * append: No processing before writing. Data integration OSS-HDFS Writer directly uses filename for writing and ensures no file name conflicts. * nonConflict: If there are files with the fileName prefix in the directory, an error is reported directly. * truncate: Before writing, clears all files matching the fileName prefix. | Y | None | Y | Frontend options: 'append' → 'Keep original files'; 'truncate' → 'Replace existing files'; 'nonConflict' → 'Exit with error'. Parquet format only supports nonConflict. |
| fieldDelimiter | The field delimiter when OSS-HDFS Writer writes. Only single-character delimiters are supported. Entering multiple characters will cause a runtime error. | N | ',' | Y | Display condition: displayed when fileFormat is 'text'; supports Unicode encoding input (such as \u001b, \u007c). |
| encoding | The encoding configuration for writing files. | N | 'UTF-8' | Y | |
| column | The fields of the data to be written. Writing to partial columns is not supported. When associating with a table in Hive, you need to specify all field names and field types in the table, where name specifies the field name and type specifies the field type. | Y | None | N | |
| compress | OSS-HDFS file compression type. Default is not filled in, which means no compression. Text type files support gzip and bzip2 compression types. | N | None | N | |
| parquetSchema | Required when writing Parquet format files, used to describe the structure of the destination file. This item is effective only when fileFormat is parquet. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "oss_hdfs",//Plugin name.
            "parameter": {
                "path": "",//Path information stored in the OSS-HDFS file system.
                "fileName": "",//File name when OSS-HDFS Writer writes.
                "compress": "",//OSS-HDFS file compression type.
                "datasource": "",//Data source.
                "column": [
                    {
                        "name": "col1",//Field name.
                        "type": "string"//Field type.
                    },
                    {
                        "name": "col2",
                        "type": "int"
                    },
                    {
                        "name": "col3",
                        "type": "double"
                    },
                    {
                        "name": "col4",
                        "type": "boolean"
                    },
                    {
                        "name": "col5",
                        "type": "date"
                    }
                ],
                "writeMode": "",//Write mode.
                "fieldDelimiter": ",",//Column delimiter.
                "encoding": "",//Encoding format.
                "fileFormat": "text"//Text type.
            },
            "name": "Writer",
            "category": "writer"
        }
```
