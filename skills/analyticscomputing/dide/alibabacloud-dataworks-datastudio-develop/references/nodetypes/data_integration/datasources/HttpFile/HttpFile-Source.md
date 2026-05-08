# Introduction

DataWorks Data Integration supports the HttpFile data source, which can download files via the HTTP protocol and synchronize files to the target data source.

> **Supported Direction**: This data source only supports being used as a source (read), and does not support being used as a destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. This name must be consistent with the HttpFile data source name created in the data source management interface. | Y | None | Y | |
| fileName | File path. When the file path contains special characters or Chinese, you need to input the URL-escaped value. For example: special character space must be escaped as %20. The final access path is formed by concatenating the "data source URL domain" with the "file path". | Y | None | Y | Linkage logic: when modified, resets fileFormat to 'csv'. |
| fileFormat | The source file type. | Y | 'csv' | Y | Frontend options: 'csv'/'text', when readerConfig.featureControl.supportInferenceType exists, 'json'/'jsonl' are additionally provided; Linkage logic: determines the display of other parameters, triggers onTableChange and resets isSchemaConfirmed when modified. |
| fieldDelimiter | The field delimiter for reading. | Y | ',' | Y | Display condition: displayed when fileFormat is 'csv' or 'text'; supports Unicode encoding input (e.g., \u001b, \u007c). |
| lineDelimiter | The line delimiter for reading. | N | None | Y | Display condition: displayed when fileFormat is 'text'; supports Unicode encoding input. |
| encoding | The encoding configuration for reading files. | N | 'UTF-8' | Y | Display condition: displayed when fileFormat is 'csv'/'text'/'json'/'jsonl'; Frontend options: 'Use Database Encoding' (value is '') and 150+ encoding list. |
| nullFormat | In text files, standard strings cannot define null (null pointer). Data Synchronization provides nullFormat to define which strings can represent null. | N | undefined (no processing) | Y | Display condition: displayed when fileFormat is 'csv' or 'text'; Frontend options: no processing (value: undefined) / visible characters (default 'null') / invisible characters (Unicode encoding). |
| compress | Text compression type. By default, it is not filled in (i.e., no compression). | N | '' (no compression) | Y | Display condition: displayed when fileFormat is 'csv'/'text'/'json'/'jsonl'; Frontend options: '' → 'No Compression'; 'gzip'; 'bzip2'; 'zip'. |
| skipHeader | CSV-like format files may have headers as titles. During data synchronization, you can choose whether to skip the header. * true: Skip. * false: Do not skip. | N | 'false' | Y | Display condition: displayed when fileFormat is 'csv' or 'text'; Frontend options: 'true' → 'Yes'; 'false' → 'No'. |
| requestHeaders | Request headers, filled in as key-value pairs, for example: `{"Content-Type": "application/json"}` | N | None | Y | Free input of HTTP request headers in JSON format. |
| requestMethod | Request method. Supports GET, POST, and PUT. | N | 'GET' | Y | Frontend options: 'GET'/'POST'/'PUT'; Linkage logic: when GET, displays requestParam; when POST/PUT, displays requestBody. |
| requestParam | Request parameters. Only takes effect when requestMethod is configured as GET. When parameter values contain special characters or Chinese, the parameter values need to be URL-escaped. | N | None | Y | Display condition: displayed when requestMethod is 'GET'; format like param1=x&param2=y... |
| requestBody | Request content. Only takes effect when requestMethod is configured as POST or PUT. It also needs to be used in conjunction with Content-Type in requestHeaders. | N | None | Y | Display condition: displayed when requestMethod is 'POST' or 'PUT'; format like JSON. |
| connectTimeoutSeconds | The timeout for establishing an HTTP connection, in seconds. When this configuration item is exceeded, the task fails. | N | 60 | Y | Unit: seconds, minimum value: 1. |
| socketTimeoutSeconds | HTTP connection response timeout, in seconds. When the interval between preceding and succeeding message transmissions exceeds this configuration item, the task fails. | N | 3600 | Y | Unit: seconds, minimum value: 1. |
| bufferByteSizeInKB | The buffer size for file download, in KB. | N | 1024 | Y | Unit: KB, minimum value: 1. |
| column | List of fields to read: * type specifies the source data type. * index specifies which column from the text the current column comes from (starting from 0). * value specifies that if the current column's field type is a constant, then when Reader processes data, instead of reading data from the source file to fill this column, it automatically generates all data for this column based on the fixed value you specify. By default, you can read all data as String type, configured as `"column": ["*"]`. | Y | None | Y | |

> Y = Yes, N = No

## Configuration Example

```json
{
      "stepType": "httpfile",
      "parameter": {
        "datasource": "",
        "fileName": "/f/z/1.csv",
        "requestMethod": "GET",
        "requestBody": "",
        "requestHeaders": {
          "header1": "v1",
          "header2": "v2"
        },
        "socketTimeoutSeconds": 3600,
        "connectTimeoutSeconds": 60,
        "bufferByteSizeInKB": 1024,
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
