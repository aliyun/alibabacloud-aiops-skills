# Introduction

HDFS is a distributed file system that provides you with a bidirectional channel for reading from and writing to HDFS. This article introduces the HDFS data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| path | The path information stored in the Hadoop HDFS file system. HDFS Writer will write multiple files under the Path directory based on the concurrency configuration. | Y | None | Y | |
| fileType | The file type. Currently, you can only configure it as text, orc, and parquet: * text: Represents a storage table in Hive, TextFile format. * orc: Represents a compressed table in Hive, ORCFile format. * parquet: Represents a regular Parquet File format. | Y | None | Y | Frontend options: 'text'/'orc'/'parquet'; Linkage logic: when fileType is 'text', displays fieldDelimiter and compress; when 'orc', displays compress; when 'parquet', displays parquetSchema and dataxParquetMode. |
| fileName | The file name written by HDFS Writer. During actual execution, a random suffix will be added to this file name as the actual file name written by each thread. | Y | None | Y | |
| writeMode | HDFS Writer data cleanup processing mode before writing: * append: Does no processing before writing. Data Integration HDFS Writer directly writes using filename, and ensures the file name does not conflict. * nonConflict: If there are files with the fileName prefix in the directory, an error is reported directly. **Note** Parquet format files do not support Append, so only nonConflict is allowed. | Y | None | Y | Frontend options: 'append' → 'Append'; 'nonConflict' → 'Exit with Error'. |
| fieldDelimiter | The field delimiter used by HDFS Writer when writing. You need to ensure it is consistent with the field delimiter of the created Hive table; otherwise, you will not be able to query data in the Hive table. | N | None | Y | Display condition: displayed when fileType is 'text'. |
| compress | HDFS file compression type. By default, it is not filled in, which means no compression. | N | None | Y | Display condition: displayed when fileType is 'text' or 'orc'; Frontend options: 'gzip'/'bzip2'/'SNAPPY'. text supports gzip/bzip2, orc supports SNAPPY. |
| parquetSchema | Required when writing Parquet format files, used to describe the structure of the target file. | N | Built-in Thrift schema example string | Y | Display condition: displayed and required when fileType is 'parquet'. |
| encoding | The encoding configuration for writing files. | N | 'UTF-8' | Y | |
| haveKerberos | Whether there is Kerberos authentication, default is false. If you configure it as true, then the configuration items kerberosKeytabFilePath and kerberosPrincipal are required. | N | 'false' | Y | Frontend options: 'true' → 'Yes'; 'false' → 'No'; Linkage logic: when 'true', displays kerberosKeytabFilePath and kerberosPrincipal. |
| kerberosKeytabFilePath | The absolute path of the Kerberos authentication keytab file. | N | None | Y | Display condition: displayed when haveKerberos is 'true'. |
| kerberosPrincipal | Kerberos authentication Principal name, such as ***/hadoopclient@*.***. Since Kerberos requires configuring the absolute path of the keytab authentication file, you need to use this feature on a custom resource group. | N | None | Y | Display condition: displayed when haveKerberos is 'true'. |
| dataxParquetMode | The mode for synchronizing Parquet files. Using fields supports complex types such as array, map, and struct. | N | 'columns' | N | Display condition: displayed when fileType is 'parquet'; Frontend options: 'fields' → 'fields mode (supports complex types)'; 'columns' → 'columns mode'. When configured as 'fields', HDFS over OSS is supported, and OSS-related parameters can be added in hadoopConfig. |
| column | The fields for writing data. Partial column writing is not supported. To associate with a table in Hive, you need to specify all field names and field types in the table, where name specifies the field name and type specifies the field type. | Y (not required in Parquet mode) | None | Y | |
| hadoopConfig | hadoopConfig can be used to configure some advanced parameters related to Hadoop, such as HA configuration. Public resource groups do not support Hadoop advanced parameter HA configuration. | N | None | Y | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "hdfs",//Plugin name.
            "parameter": {
                "path": "",//Path information stored in the Hadoop HDFS file system.
                "fileName": "",//File name written by HDFS Writer.
                "compress": "",//HDFS file compression type.
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
                "fileType": "text"//Text type.
            },
            "name": "Writer",
            "category": "writer"
        }
```
