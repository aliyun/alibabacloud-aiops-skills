# Introduction

Simple Storage Service (S3 for short) is an object storage built for storing and retrieving any amount of data from any location. DataWorks Data Integration supports reading data from S3 databases using the Amazon S3 Reader plugin. This article introduces DataWorks' Amazon S3 data reading capabilities.

> **Supported Direction**: This data source only supports being used as a source (read), and does not support being used as a destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| fileFormat | Text type, the file type of the source S3. | Y | csv | Y | Frontend default value: `csv`; Linkage logic: Switching fileFormat clears object/path and table schema confirmation status |
| object | S3 Object information, supports specifying multiple Objects. Supports using wildcards to match multiple Objects. | Y when fileFormat != parquet | None | Y | Display condition: fileFormat != parquet; The data synchronization system treats all Objects synchronized under one job as the same data table, so you must ensure all Objects can adapt to the same Schema; Please control the number of files in a single directory, otherwise an OutOfMemoryError may occur |
| path | Parquet file path. | Required when parquet format | None | Y | Display condition: fileFormat = parquet; Parquet format uses a special path; getTableColumn is automatically called on path input/blur to retrieve column information, no SchemaConfirm needed |
| column | List of fields to read. type specifies the source data type, index specifies which column in the text the current column comes from (starting from 0), value specifies the current type as a constant, which is not read from the source file but auto-generated based on the value. | Y | Read all as STRING type | Y | type must be specified, and either index or value must be selected |
| fieldDelimiter | Field delimiter for reading. | Y when fileFormat is csv/text | , | Y | Display condition: fileFormat is csv or text; If the delimiter is not visible, please use Unicode encoding, such as `\u001b`, `\u007c`; Frontend default value: `,` |
| lineDelimiter | Line delimiter for reading. | N | None | Y | Display condition: fileFormat is text |
| compress | Text compression type. Default is no compression when not specified. | N | No compression | Y | Display condition: fileFormat is csv or text; Supports gzip, bzip2, and zip |
| encoding | Encoding configuration for reading files. | N | UTF-8 | Y | Display condition: fileFormat is csv or text; Frontend default value: UTF-8 |
| nullFormat | In text files, null cannot be defined using standard strings. Data synchronization provides nullFormat to define which strings can represent null. | N | None | Y | Display condition: fileFormat != parquet; If not configured, source data is written directly to the destination without conversion |
| skipHeader | CSV-like format files may have a header row that needs to be skipped. | N | false | Y | Display condition: fileFormat is csv or text; skipHeader is not supported in compressed file mode; Frontend default value: false |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"s3",//Plugin name.
            "parameter":{
                "nullFormat":"",//Defines the string that can represent null.
                "compress":"",//Text compression type.
                "datasource":"",//Data source.
                "column":[//Fields.
                    {
                        "index":0,//Column sequence number.
                        "type":"string"//Data type.
                    },
                    {
                        "index":1,
                        "type":"long"
                    },
                    {
                        "index":2,
                        "type":"double"
                    },
                    {
                        "index":3,
                        "type":"boolean"
                    },
                    {
                        "format":"yyyy-MM-dd HH:mm:ss", //Date format.
                        "index":4,
                        "type":"date"
                    }
                ],
                "skipHeader":"",//CSV-like format files may have a header row that needs to be skipped.
                "encoding":"",//Encoding format.
                "fieldDelimiter":",",//Field delimiter.
                "fileFormat": "",//Text type.
                "object":[]//Object prefix.
            },
            "name":"Reader",
            "category":"reader"
        }
```
