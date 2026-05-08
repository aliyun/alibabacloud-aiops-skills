# Introduction

DataWorks Data Integration supports using Redis Writer to write data to Redis. This article introduces the offline write capabilities of DataWorks for Redis data.

> **Supported Direction**: This data source only supports being used as a destination (write), and does not support being used as a source (read).

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| keyFieldDelimiter | The delimiter for writing keys to Redis. For example, key=key1\u0001id. This is required when multiple keys need to be concatenated. If there is only one key, this configuration item can be ignored. | N | \u0001 | Y |  |
| dateFormat | The Date format when writing to Redis, as yyyy-MM-dd HH:mm:ss. | N | None | Y |  |
| datasource | Data source name. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| selectDatabase | The database selection for writing to Redis ("0"~"databases"). Redis clusters cannot perform database selection. | N | Defaults to database 0 | Y |  |
| writeMode | The value types that Redis Writer can write to Redis include the following 5 types: * String (string) * String list (list) * String set (set) * Sorted string set (zset) * Hash (hash) Different value types have slightly different writeMode configurations. For details, see **writeMode Parameter Description** below. **Note** When configuring Redis Writer, you need to configure writeMode as one of the 5 supported write data types, and only one type can be configured. If you do not configure it, the writeMode value defaults to `string`. | N | string | Y |  |
| keyIndexes | Specifies the column index of the source columns to be used as keys. Column indexes start from 0 (i.e., the index of the 1st column is 0, the index of the 2nd column is 1, and so on). * When a single column from the source is used as the Redis key: Configure the corresponding column index. For example, if the 1st column is used as the key, configure it as `0`. * When consecutive multiple columns from the source are combined as the Redis key: Configure an array of the corresponding column indexes. For example, if the 2nd to 4th columns are combined as the key, configure it as `[1,3]`. **Note** After configuring keyIndexes, Redis Writer will use the remaining columns as the Value. If you only want to sync certain columns from the source table as Key and certain columns as Value, you don't need to sync all fields. Just specify the column selection in the Reader plugin. | Y | None | Y |  |
| batchSize | The number of records submitted in a single batch. This value can greatly reduce the number of network interactions between the data synchronization system and Redis, and improve overall throughput. If this value is set too large, it may cause OOM exceptions in the data synchronization process. | N | 1,000 | Y |  |
| timeout | The timeout for writing to Redis, in milliseconds. | N | 30,000 | Y |  |
| redisMode | The running mode of Redis. Details are as follows: * Cluster direct connection mode: redisMode value is clusterDirectMode. In cluster mode, when other data sources write to Redis, they communicate directly with the Redis cluster. Typically, self-built Redis cluster addresses and Alibaba Cloud Redis direct connection addresses need to use this mode. * Non-cluster mode: redisMode value is empty (i.e., no value is configured), indicating non-cluster mode. Typically, Alibaba Cloud Redis cluster proxy addresses, read-write separation addresses, and standard edition addresses use this mode. **Note** Exclusive data integration resource groups are supported. | N | None | Y |  |
| column | The column configuration for writing to Redis. When the Redis type is string or set: * If there is no column configuration, the value format is a delimiter-joined string. Assuming the data name has a value of "Xiao Wang", age has a value of 18, and sex has a value of male, the Redis value result example is "Xiao Wang:18:male"; * If column is configured, the value format is JSON. For example, configure "column": [{"index":"0", "name":"id", "type":"long"}, {"index":"1", "name":"name"}]. Assuming the data ID has a value of 1 and name has a value of "Xiao Wang", the Redis value result example is {"id":1,"name":"Xiao Wang"}. When type is not configured, the default is string format. Supported type values are: int, long, double, string, bool. | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{// The following is a write-side code sample.
            "stepType":"redis",                    // Redis Writer plugin name, configured as redis.
            "parameter":{                          // The following are the main parameters of Redis Writer.
                "expireTime":{                     // Redis value cache expiration time, can be configured as seconds type or unixtime type. "seconds":"1000"
                            },
                "keyFieldDelimiter":"u0001",       // The delimiter for the key written to Redis.
                "dateFormat":"yyyy-MM-dd HH:mm:ss",// The Date format when writing to Redis.
                "datasource":"xc_mysql_demo2",     // Data source name, must be consistent with the added data source name.
                "envType": 0,                      // Environment type, development environment: 1, production environment: 0.
                "writeMode":{                      // Write mode.
                    "type":"string"                // Value type.
                    "mode":"set",                  // When the value is of a certain type, the write mode.
                    "valueFieldDelimiter":"u0001", // The delimiter between values.
                             },
                "keyIndexes":[0,1],                // Used for source-to-Redis mapping, specifying the source columns to be used as keys (the 1st column starts from 0). If the 1st and 2nd columns of the source are combined as the Redis key, configure it as [0,1].
                "batchSize":"1000"                 // The number of records submitted in a single batch.
        "column": [                        // For Redis type string and set operations, if this column is not configured, the value format is a delimiter-joined string (CSV format, assuming ID value is 1, name value is "Xiao Wang", age value is 18, sex value is male, Redis value result example: "18::male"); if column is configured in the following format, Redis will write the original column names and values as JSON format. Assuming ID value is 1, name value is "Xiao Wang", age value is 18, sex value is male, Redis value result example: {"id":1,"name":"Xiao Wang","age":18,"sex":"male"}
                {
                "name": "id",
                "index": "0"

                },
                {
                "name": "name",
                "index": "1"
                },
                {
                "name": "age",
                "index": "2"
                },
                {
                "name": "sex",
                "index": "3"
                }
            ]
            },
            "name":"Writer",
            "category":"writer"
        }
```
