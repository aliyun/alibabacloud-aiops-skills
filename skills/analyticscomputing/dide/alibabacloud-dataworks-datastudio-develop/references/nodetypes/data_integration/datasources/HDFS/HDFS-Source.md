# Introduction

HDFS is a distributed file system that provides you with a bidirectional channel for reading from and writing to HDFS. This article introduces the HDFS data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| path | The path and file name information of the remote HDFS file system. | Y | None | Y | |
| fileType | File type. | Y | None | Y | Frontend options: 'text'/'orc'/'rc'/'seq'/'csv'/'parquet'; Linkage logic: determines the display of compress, csvReaderConfig, and parquetSchema. |
| fieldDelimiter | The field delimiter for reading. When HDFS Reader reads TextFile data, you need to specify the field delimiter. If not specified, the default is comma (,). When HDFS Reader reads ORCFile, you do not need to specify the field delimiter. The default delimiter of Hive is \u0001. | N | ',' | Y | |
| encoding | The encoding configuration for reading files. | N | 'UTF-8' | Y | |
| nullFormat | In text files, standard strings cannot define null (null pointer). Data Integration provides nullFormat to define which strings can represent null. | N | None | Y | |
| compress | File compression method. | N | None | Y | Display condition: displayed when fileType is 'csv'; Frontend options: 'gzip'/'bz2'/'zip'/'lzo'/'lzo_deflate'/'hadoop-snappy'/'framing-snappy'. |
| csvReaderConfig | Configuration for reading CSV type files, Map type. CSV files are read using CsvReader, which has many configuration options. If not configured, default values are used. | N | '{"safetySwitch":false,"useTextQualifier":false,"skipEmptyRecords":false}' | Y | Display condition: displayed when fileType is 'csv'. |
| parquetSchema | If your file format type is Parquet, you need to configure parquetSchema, which represents the type description of parquet storage. | N | Built-in Thrift schema example string | Y | Display condition: displayed and required when fileType is 'parquet'. |
| haveKerberos | Whether there is Kerberos authentication, default is false. For example, if you configure it as true, then the configuration items kerberosKeytabFilePath and kerberosPrincipal are required. | N | 'false' | Y | Frontend options: 'true' → 'Yes'; 'false' → 'No'; Linkage logic: when 'true', displays kerberosKeytabFilePath and kerberosPrincipal. |
| kerberosKeytabFilePath | Kerberos authentication keytab file path. Required if haveKerberos is true. | N | None | Y | Display condition: displayed when haveKerberos is 'true'. |
| kerberosPrincipal | Kerberos authentication Principal name, such as ***/hadoopclient@*.***. Required if haveKerberos is true. | N | None | Y | Display condition: displayed when haveKerberos is 'true'. |
| successOnNoFile | Whether to ignore when the file does not exist. | N | 'false' | Y | Frontend options: 'true' → 'Yes'; 'false' → 'No'. |
| hadoopConfig | hadoopConfig can be used to configure some advanced parameters related to Hadoop, such as HA configuration. | N | None | Y | |
| column | List of fields to read. type specifies the source data type, index specifies which column from the text the current column comes from (starting from 0), and value specifies that the current type is a constant. By default, all data can be read as STRING type, configured as `"column": ["*"]`. | Y | None | Y | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "hdfs",//Plugin name
            "parameter": {
                "path": "",//File path to read
                "datasource": "",//Data source
                "hadoopConfig":{
                "dfs.data.transfer.protection": "integrity",
               "dfs.datanode.use.datanode.hostname" :"true",
                "dfs.client.use.datanode.hostname":"true"
                 },
                "column": [
                    {
                        "index": 0,//Sequence number, index starts from 0 (subscript index starts from 0), meaning reading data from the first column of the local text file.
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
                "fileType": ""//Text type
            },
            "name": "Reader",
            "category": "reader"
        }
```
