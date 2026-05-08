# Introduction

The HBase data source provides you with a bidirectional channel for reading from and writing to HBase. This article introduces the HBase data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| table | The HBase table name to write to (case-sensitive). | Y | None | Y | |
| writeMode | The mode for writing to HBase. | N | 'api' | Y | Frontend options: 'api' → 'API Mode'. |
| mode | The column mode for writing to HBase. * normal: Fixed column mode. | N | 'normal' | Y | Frontend options: 'normal' → 'Fixed Columns'. |
| versionColumn | Specifies the timestamp for writing to HBase. Supports current time, specified time column, or specified time (choose one of the three). If not configured, the current time is used. * index: Specifies the index corresponding to the Reader column, starting from 0. Must be convertible to LONG. If specifying a time, index is -1. * value: Specifies the time value, LONG type. | N | Current time | Y | Frontend options: CURRENT_TIMESTAMP → 'Current Time'; SPECIFIC_TIMESTAMP → 'Specified Time'; SPECIFIC_TIMESTAMP_COLUMN → 'Specified Time Column' (options from the reader field list). |
| column | The HBase fields to write: * index: Specifies the index corresponding to the Reader column, starting from 0. * name: Specifies the column in the HBase table. The format must be column family:column name. * type: Specifies the data type for writing, used for converting HBase byte[]. | Y | None | Y | |
| encoding | Encoding method, used for encoding when converting STRING to HBase byte[]. | N | None | Y | Frontend options: 'Use Database Encoding' (value is '') and 150+ encoding list. |
| nullMode | The processing method when the read data is null: * skip: Indicates not writing this column to HBase. * empty: Writes HConstants.EMPTY_BYTE_ARRAY, i.e., new byte [0]. | N | 'skip' | Y | Frontend options: 'skip' → 'Skip Null Values'; 'empty' → 'Insert Null Values'. |
| walFlag | When the HBase Client submits data to the RegionServer in the cluster (Put/Delete operations), it first writes a WAL (Write Ahead Log) entry. Disabling (false) abandons writing WAL logs, thereby improving data write performance. | N | 'true' | Y | Frontend options: 'true' → 'Yes'; 'false' → 'No'. |
| writeBufferSize | Sets the write buffer size of the HBase Client, in bytes. | N | 2097152 | Y | |
| hbaseConfig | Configuration information required to connect to the HBase cluster, in JSON format. The required configuration is hbase.zookeeper.quorum, which represents the HBase ZK connection address. | Y | None | N |  |
| rowkeyColumn | The rowkey column of HBase to write: * index: Specifies the index corresponding to the Reader column, starting from 0. If it is a constant, index is -1. * type: Specifies the data type for writing, used for converting HBase byte[]. * value: Configures a constant. HBase Writer will concatenate all columns in rowkeyColumn in the configured order as the rowkey written to HBase. Not all columns can be constants. | Y | None | N | Maintained by the column mapping panel, cleared when mode is switched. |
| hbaseVersion | HBase version, supports 094x/11x/20x. | N | None | N |  |
| rowkeyType | The rowkey type in dynamic column mode. | N | 'BOOLEAN' | N |  |
| hbaseBulkLoadControl | Whether to execute bulkload. | N | true | N |  |
| hbaseOutput | HBase write directory. | N | None | N |  |
| bucketNum | The bucket_num configuration for Phoenix tables. | N | None | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"hbase",//Plugin name.
            "parameter":{
                "mode":"normal",//HBase write mode.
                "walFlag":"false",//Disable (false) to abandon writing WAL logs.
                "hbaseVersion":"094x",//HBase version.
                "rowkeyColumn":[//The rowkey column of HBase to write.
                    {
                        "index":"0",//Sequence number.
                        "type":"string"//Data type.
                    },
                    {
                        "index":"-1",
                        "type":"string",
                        "value":"_"
                    }
                ],
                "nullMode":"skip",//How to handle null values when reading.
                "column":[//HBase fields to write.
                    {
                        "name":"columnFamilyName1:columnName1",//Field name.
                        "index":"0",//Index number.
                        "type":"string"//Data type.
                    },
                    {
                        "name":"columnFamilyName2:columnName2",
                        "index":"1",
                        "type":"string"
                    },
                    {
                        "name":"columnFamilyName3:columnName3",
                        "index":"2",
                        "type":"string"
                    }
                ],
                "encoding":"utf-8",//Encoding format.
                "table":"",//Table name.
                "hbaseConfig":{//Configuration information required to connect to the HBase cluster, JSON format.
                    "hbase.zookeeper.quorum":"hostname",
                    "hbase.rootdir":"hdfs: //ip:port/database",
                    "hbase.cluster.distributed":"true"
                }
            },
            "name":"Writer",
            "category":"writer"
        }
```
