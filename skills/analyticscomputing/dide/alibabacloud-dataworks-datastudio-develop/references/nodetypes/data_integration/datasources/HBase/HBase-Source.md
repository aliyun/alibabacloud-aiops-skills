# Introduction

The HBase data source provides you with a bidirectional channel for reading from and writing to HBase. This article introduces the HBase data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| table | The HBase table name to read (case-sensitive). | Y | None | Y | |
| mode | The mode for reading HBase. * normal: Horizontal table (wide table mode). * multiVersionFixedColumn: Vertical table (vertical table mode / multi-version fixed columns). | N | 'normal' | Y | Linkage logic: selecting vertical table mode displays the maxVersion parameter. |
| column | The HBase fields to read. * In normal mode: name specifies the HBase column to read. Except for **rowkey**, it must be in **column family:column name** format. type specifies the source data type, format specifies the date type format. value specifies that the current type is a constant; data is not read from HBase, but the corresponding column is automatically generated based on the value. * In multiVersionFixedColumn mode: name specifies the HBase column to read. Except for **rowkey**, it must be in **column family:column name** format. type specifies the source data type, format specifies the date type format. Constant columns are not supported in multiVersionFixedColumn mode. | Y | None | Y | |
| maxVersion | Specifies the number of versions read by HBase Reader in multi-version mode. The value can only be -1 or a number greater than or equal to 2. -1 means reading all versions. | N (Y in vertical table mode) | -1 | Y | Display condition: displayed when mode is 'multiVersionFixedColumn'. |
| encoding | Encoding method, used for converting HBase byte[] stored as binary to String. | N | undefined (use database encoding) | Y | Frontend options: 'Use Database Encoding' (value is '', equivalent to not passing) and 150+ encoding list. |
| range | Specifies the rowkey range for HBase Reader to read. * startRowkey: Specifies the start rowkey. * endRowkey: Specifies the end rowkey. * isBinaryRowkey: Specifies the method for converting the configured startRowkey and endRowkey to byte[]. Default value is false. If true, the `Bytes.toBytesBinary(rowkey)` method is called for conversion. If false, `Bytes.toBytes(rowkey)` is called. | N | None | Y | |
| scanCacheSize | The number of rows read from HBase by HBase Reader each time. | N | 256 | Y | |
| scanBatchSize | The number of columns read from HBase by HBase Reader each time. When configured as -1, all columns will be returned. | N | 100 | Y | |
| hbaseConfig | Configuration information required to connect to the HBase cluster, in JSON format. The required configuration is hbase.zookeeper.quorum, which represents the HBase ZK connection address. You can also add more HBase client configurations, such as setting scan cache and batch to optimize interaction with the server. | Y | None | N |  |
| hbaseVersion | HBase version, supports 094x/11x/20x. | N | None | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"hbase",//Plugin name.
            "parameter":{
                "mode":"normal",//HBase read mode, supports normal mode and multiVersionFixedColumn mode.
                "scanCacheSize":"256",//Number of rows read by HBase client per RPC from the server.
                "scanBatchSize":"100",//Number of columns read by HBase client per RPC from the server.
                "hbaseVersion":"094x/11x",//HBase version.
                "column":[//Fields.
                    {
                        "name":"rowkey",//Field name.
                        "type":"string"//Data type.
                    },
                    {
                        "name":"columnFamilyName1:columnName1",
                        "type":"string"
                    },
                    {
                        "name":"columnFamilyName2:columnName2",
                        "format":"yyyy-MM-dd",
                        "type":"date"
                    },
                    {
                        "name":"columnFamilyName3:columnName3",
                        "type":"long"
                    }
                ],
                "range":{//Specifies the rowkey range for HBase Reader to read.
                    "endRowkey":"",//Specifies the end rowkey.
                    "isBinaryRowkey":true,//Specifies the method for converting startRowkey and endRowkey to byte[], default is false.
                    "startRowkey":""//Specifies the start rowkey.
                },
                "maxVersion":"",//Specifies the number of versions read by HBase Reader in multi-version mode.
                "encoding":"UTF-8",//Encoding format.
                "table":"",//Table name.
                "hbaseConfig":{//Configuration information required to connect to the HBase cluster, JSON format.
                    "hbase.zookeeper.quorum":"hostname",
                    "hbase.rootdir":"hdfs://ip:port/database",
                    "hbase.cluster.distributed":"true"
                }
            },
            "name":"Reader",
            "category":"reader"
        }
```
