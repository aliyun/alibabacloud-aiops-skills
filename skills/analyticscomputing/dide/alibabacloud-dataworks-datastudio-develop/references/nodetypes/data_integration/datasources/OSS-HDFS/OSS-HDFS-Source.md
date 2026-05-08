# Introduction

OSS-HDFS Service (JindoFS Service) is a cloud-native data lake storage product. The OSS-HDFS data source provides you with a bidirectional channel for reading from and writing to OSS-HDFS. This article introduces the OSS-HDFS data synchronization capabilities of DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| path | The file path to be read. If you need to read multiple files, you can use the regular expression *. Note that multiple paths can be filled in here. | Y | None | Y | |
| fileFormat | The file type. Currently, only text, orc, csv, and parquet are supported for user configuration. | Y | None | Y | Frontend options: 'csv'/'text'/'orc'/'parquet'; linkage logic: when fileFormat is 'text' or 'csv', fieldDelimiter is displayed. |
| fieldDelimiter | The field delimiter for reading. OSS-HDFS Reader needs to specify the field delimiter when reading TextFile data. If not specified, the default is comma (,). When OSS-HDFS Reader reads ORC/PARQUET, you do not need to specify a field delimiter. | N | ',' | Y | Display condition: displayed when fileFormat is 'text' or 'csv'; supports Unicode encoding input (such as \u001b, \u007c). |
| encoding | The encoding configuration for reading files. | N | 'UTF-8' | Y | |
| nullFormat | In text files, null (null pointer) cannot be defined using standard strings. Data integration provides nullFormat to define which strings can represent null. For example, if you configure `nullFormat:"null"`, if the source data is null, data integration will treat it as a null field. | N | None | Y | Frontend options: No processing (default) / Visible character (default 'null') / Invisible character (Unicode encoding). |
| column | The list of fields to be read. By default, you can read all data as STRING type, configured as `"column": ["*"]`. You can also specify column field information, configured as follows. Where: * type: Specifies the type of source data. * index: Specifies which column in the text the current column comes from (starting from 0). * value: Specifies the current type as a constant, not reading data from the source file but automatically generating the corresponding column based on the value. | Y | None | Y | |
| compress | Currently, only gzip, bzip2, and snappy compression are supported. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "oss_hdfs",//Plugin name
            "parameter": {
                "path": "",//File path to be read
                "datasource": "",//Data source
                "column": [
                    {
                        "index": 0,//Serial number, index starts from 0 (subscript index counts from 0), meaning reading data starting from the first column of the local text file.
                        "type": "string"//Field type
                    },
                    {
                        "index": 1,
                        "type": "long"
                    },
                    {
                        "index": 2,
                        "type": "double"
                    },
                    {
                        "index": 3,
                        "type": "boolean"
                    },
                    {
                        "format": "yyyy-MM-dd HH:mm:ss", //Date format
                        "index": 4,
                        "type": "date"
                    }
                ],
                "fieldDelimiter": ",",//Column delimiter
                "encoding": "UTF-8",//Encoding format
                "fileFormat": ""//Text type
            },
            "name": "Reader",
            "category": "reader"
        }
```
