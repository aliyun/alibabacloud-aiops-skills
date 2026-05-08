# Introduction

The FTP data source provides you with a bidirectional channel for reading from and writing to FTP. This article introduces the FTP data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| fileFormat | The format of the file to write. CSV is a strict CSV format. If the data to be written contains column delimiters, it will be escaped according to CSV escaping syntax, with the escape symbol being double quotes. TEXT format uses column delimiters to simply split the data to be written, and does not perform escaping when the data contains column delimiters. | Y | 'csv' | Y | Frontend options: 'csv', 'text'; Linkage logic: determines the display of lineDelimiter, triggers column mapping table update when modified. |
| path | The path information of the FTP file system. FTP Writer will write multiple files under the Path directory. | Y | None | Y | |
| fileName | The file name written by FTP Writer. A random suffix will be added to this file name as the actual file name written by each thread. | Y | None | Y | |
| fieldDelimiter | The field delimiter for writing. | Y | ',' | Y | Supports Unicode encoding input (e.g., \u001b, \u007c). |
| lineDelimiter | The line delimiter for writing. | N | None | Y | Display condition: fileFormat is 'text' and in non-elastic environment. |
| encoding | The encoding configuration for writing files. | N | 'UTF-8' | Y | Frontend options: 'Use Database Encoding' (value is '', equivalent to not passing) and 150+ encoding list. |
| nullFormat | In text files, standard strings cannot define null (null pointer). Data Integration provides nullFormat to define which strings can represent null. | N | undefined (no processing) | Y | Three modes: no processing (value: undefined), visible characters (default 'null'), invisible characters (Unicode encoding). |
| dateFormat | The format for serializing date type data into files, for example "yyyy-MM-dd". | N | None | Y | |
| writeMode | FTP Writer data cleanup processing mode before writing: * truncate: Clears files with the same name in the directory before writing. * append: Does no processing before writing, directly writes using fileName, and ensures the file name does not conflict. * nonConflict: If there are files with the fileName prefix in the directory, an error is reported directly. | Y | 'truncate' | Y | Frontend options: 'truncate' → 'Replace Existing Files'; 'append' → 'Keep Existing Files'; 'nonConflict' → 'Exit with Error'. |
| markDoneFileName | Marker file name. A marker file is generated after the synchronization task completes. Based on this marker file, you can determine whether the synchronization task was successful. This should be configured as an absolute path. In offline periodic task scenarios, it is recommended that the marker file includes scheduling parameters. | N | None | Y | |
| timeout | FTP server connection timeout in milliseconds. | N | 60,000 | N | |
| skipHeader | CSV-like format files may have headers as titles that need to be skipped. By default, headers are not skipped. | N | 'false' | N | |
| compress | Supports gzip and bzip2 compression formats. | N | None | N | |
| header | The header for txt text output (including csv, text, etc.), for example ["id","name","age"], which means writing id, name, and age as the header in the first line of the FTP file. | N | None | N | |
| escapeChar | If fileFormat is csv mode, used to configure the CSV escape character. The default value is the English double quote ", and generally does not need to be configured. | N | '"' | N | |
| singleFileOutput | The file name written by FtpWriter is controlled by fileName. By default, a random suffix is added as the actual file name written by each thread. If you do not need the default random suffix, you can set singleFileOutput to true, and the output file name will be the complete file name you specified. | N | false | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"ftp",//Plugin name.
            "parameter":{
                "path":"",//File path.
                "fileName":"",//File name.
                "nullFormat":"null",//Null value.
                "dateFormat":"yyyy-MM-dd HH:mm:ss",//Date format.
                "datasource":"",//Data source.
                "writeMode":"",//Write mode.
                "fieldDelimiter":",",//Column delimiter.
                "encoding":"",//Encoding format.
                "fileFormat":""//Text type.
            },
            "name":"Writer",
            "category":"writer"
        }
```
