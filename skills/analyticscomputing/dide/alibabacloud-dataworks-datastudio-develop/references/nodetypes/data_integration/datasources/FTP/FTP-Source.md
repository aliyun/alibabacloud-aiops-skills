# Introduction

The FTP data source provides you with a bidirectional channel for reading from and writing to FTP. This article introduces the FTP data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| fileFormat | The file type to read. By default, files are read as CSV format, and the content is parsed as a logical two-dimensional table structure. If configured as binary, it means copying and transferring in pure binary format. | Y | 'csv' | Y | Frontend options: 'csv', 'text'; when readerConfig?.featureControl?.jsonSupportTypes exists, 'json' and 'jsonl' are additionally provided; Linkage logic: determines the display of other parameters, resets Schema confirmation state when modified. |
| path | The path and file name information of the remote FTP file system. You need to fill in the complete file path and file name including the path and file suffix. Supports multiple paths, and supports using asterisks (*) as file wildcards. | Y | None | Y | The component supports adding multiple paths, stored as a string[] array. |
| fieldDelimiter | The field delimiter for reading. | Y | ',' | Y | Display condition: fileFormat is 'csv' or 'text'; supports Unicode encoding input (e.g., \u001b, \u007c). |
| lineDelimiter | The line delimiter for reading. | N | None | Y | Display condition: fileFormat is 'text' and in non-elastic environment. |
| encoding | The encoding configuration for reading files. | N | 'UTF-8' | Y | Display condition: fileFormat is one of 'csv', 'text', 'json', 'jsonl'; Frontend options: 'Use Database Encoding' (value is '', equivalent to not passing) and 150+ encoding list. |
| nullFormat | In text files, standard strings cannot define null (null pointer). Data Synchronization provides nullFormat to define which strings can represent null. | N | undefined (no processing) | Y | Display condition: fileFormat is not 'json' or 'jsonl'; Three modes: no processing (value: undefined), visible characters (default 'null'), invisible characters (Unicode encoding). |
| compress | Compression format. | N | '' (no compression) | Y | Display condition: fileFormat is one of 'csv', 'text', 'json', 'jsonl'; Frontend options: '' → 'No Compression'; 'gzip' → 'Gzip'; 'bzip2' → 'Bzip2'; 'zip' → 'Zip'. |
| skipHeader | CSV-like format files may have headers as titles that need to be skipped. By default, headers are not skipped. Compressed file mode does not support skipHeader. | N | 'false' | Y | Display condition: fileFormat is 'csv' or 'text'; Frontend options: 'true' → 'Yes'; 'false' → 'No'. |
| csvReaderConfig | Configuration for reading CSV type files, Map type. CSV files are read using CsvReader, which has many configuration options. If not configured, default values are used. | N | None | Y | Display condition: fileFormat is 'csv'. |
| column | List of fields to read. type specifies the source data type, index specifies which column from the text the current column comes from (starting from 0), and value specifies that the current type is a constant. By default, all data can be read as STRING type, configured as `"column": ["*"]`. | Y | None | Y | |
| markDoneFileName | Marker file name. Before data synchronization, the marker file is checked. If the marker file does not exist, it waits for a period of time and rechecks. If the marker file is found, the synchronization task starts. | N | None | Y | |
| maxRetryTime | Indicates the number of retries for checking the marker file. Default is 60 retries, with a 1-minute interval between each retry, totaling 60 minutes. | N | 60 | Y | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"ftp",//Plugin name.
            "parameter":{
                "path":[],//File path.
                "nullFormat":"",//Null value.
                "compress":"",//Compression format.
                "datasource":"",//Data source.
                "column":[//Fields.
                    {
                        "index":0,//Sequence number.
                        "type":""//Field type.
                    }
                ],
                "skipHeader":"",//Whether to include header.
                "fieldDelimiter":",",//Column delimiter.
                "encoding":"UTF-8",//Encoding format.
                "fileFormat":"csv"//Text type.
            },
            "name":"Reader",
            "category":"reader"
        }
```
