# Introduction

The Memcache (formerly OCS) data source provides you with the ability to write data from other data sources to Memcache. Currently, only script mode is supported for configuring synchronization tasks. This article introduces the Memcache (OCS) data synchronization capabilities of DataWorks.

> **Supported Direction**: This data source only supports being used as a Destination (write), and does not support being used as a Source (read).

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | N |  |
| writeMode | Memcache Writer write method, details are as follows: * set: Store this data. * add: Store this data if and only if this key does not exist (currently not supported). * replace: Store this data if and only if this key exists (currently not supported). * append: Place the data after the content corresponding to the existing key, ignoring exptime (currently not supported). * prepend: Place the data before the content corresponding to the existing key, ignoring exptime (currently not supported). | Y | None | N |  |
| writeFormat | The format in which Memcache Writer outputs data. Currently, only TEXT data writing mode is supported. TEXT serializes the source data into text format, where the first field is used as the Memcache write key, and subsequent fields are serialized to String type and concatenated using the specified fieldDelimiter as the separator before being written to Memcache. | N | None | N | |
| expireTime | Memcache value cache expiration time. Currently, MemCache supports two types of expiration times. * Unix time (seconds since 1970.1.1), this time specifies data expiration at a future point in time. * Seconds relative to the current time, this time specifies how long from now the data will expire. **Note** If the expiration time in seconds is greater than 60\*60\*24\*30 (i.e., 30 days), the server considers it a Unix time. | N | 0, 0 means permanently valid | N |  |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and MySQL, and improve overall throughput. If this value is set too large, it may cause OOM exceptions in the data synchronization runtime process. | N | 1,024 | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"ocs",//Plugin name
            "parameter":{
                "writeFormat":"text",//Memcache Writer output data format.
                "expireTime":1000,//Memcache value cache expiration time.
                "indexes":0,
                "datasource":"",//Data source.
                "writeMode":"set",//Write mode.
                "batchSize":"256"//The number of records submitted in a single batch.
            },
            "name":"Writer",
            "category":"writer"
        }
```
