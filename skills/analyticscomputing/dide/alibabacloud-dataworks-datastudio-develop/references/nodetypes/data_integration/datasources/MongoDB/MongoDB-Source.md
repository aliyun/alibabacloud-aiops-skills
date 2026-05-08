# Introduction

The MongoDB data source provides you with a bidirectional channel for reading from and writing to MongoDB. This article introduces the MongoDB data synchronization capabilities of DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | N | None | Y |  |
| collectionName | MongoDB collection name. | N | None | Y |  |
| hint | MongoDB supports the hint parameter, which causes the query optimizer to use a specific index to complete the query. In some cases, this can improve query performance. For details, please refer to [hint parameter](https://www.mongodb.com/docs/v4.2/reference/operator/meta/hint/index.html). Example is as follows: ```json { "collectionName":"test_collection", "hint":"{age:1}" } ``` | N | None | Y |  |
| column | MongoDB document column names, configured as an array to represent multiple columns in MongoDB. * name: The name of the column. * Supported types include: * string: Represents a string. * long: Represents an integer. * double: Represents a floating-point number. * date: Represents a date. * bool: Represents a boolean value. * bytes: Represents a binary sequence. * arrays: Read out in JSON string format, for example \["a","b","c"\]. * array: Read out using the splitter delimiter, for example `a,b,c`, using arrays format is recommended. * combine: When using the MongoDB Reader plugin to read data, supports merging multiple fields in a MongoDB document into one JSON string. * splitter: Because MongoDB supports array types, but the data integration framework itself does not support array types, the array type read from MongoDB needs to be merged into a string through this delimiter. | N | None | Y |  |
| batchSize | The number of records fetched in a batch. This parameter is optional. The default value is `1000` records. | N | None | Y |  |
| cursorTimeoutInMs | Cursor timeout time. This parameter is optional. The default value is `1000 * 60 * 10 = 600000`. If cursorTimeoutInMs is configured as a negative value, it means the cursor never times out. **Note** * Setting the cursor to never time out is not recommended. If the client program unexpectedly exits, the never-timeout cursor will always exist in the MongoDB server until the service restarts. * If a cursor timeout occurs, you can perform the following operations: * Reduce the batch fetch record count batchSize. * Increase the cursor timeout time cursorTimeoutInMs. | N | None | Y |  |
| query | You can use this configuration item to limit the scope of MongoDB data returned. Only the following time formats are supported; directly using timestamp type formats is not supported. **Note** * query does not support JS syntax. * Currently, reading specified column data is not supported. Common query examples are as follows: * Query data with status equal to normal ```json { ... "query":"{ status: "normal"}" ... } ``` * status: "normal" ```json { ... "query":"{ status: { $in: [ "normal", "forbidden" ] }}" ... } ``` * AND syntax, status is normal and age is less than 30 ```json { ... "query":"{ status: "normal", age: { $lt: 30 }}" ... } ``` * Date syntax, creation time greater than or equal to 2022-12-01 00:00:00.000, +0800 represents East 8 time zone ```json { ... "query":"{ createTime:{$gte:ISODate('2022-12-01T00:00:00.000+0800')}}" ... } ``` * Date syntax, using scheduling parameter placeholders, query creation time greater than or equal to a certain time point ```json { ... "query":"{ createTime:{$gte:ISODate('$[yyyy-mm-dd]T00:00:00.000+0800')}}" ... } ``` **Note** Scheduling parameters use offline sync incremental sync implementation. * Non-time type incremental field synchronization. You can use an assignment node to process the field into the target data type, and then pass it to data integration for data synchronization. For example, when the incremental field stored in MongoDB is a timestamp, you can use an assignment node to convert the time type field to a timestamp through an engine function, and then pass it to the offline sync task. For more information about using assignment nodes. **Note** For more MongoDB query syntax, please refer to the [MongoDB Official Documentation](https://www.mongodb.com/docs/v4.4/tutorial/query-documents/). | N | None | Y |  |
| splitFactor | If there is significant data skew, you can consider increasing splitFactor to achieve finer-grained splitting without increasing the number of concurrent tasks. | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "category": "reader",
            "name": "Reader",
            "parameter": {
                "datasource": "datasourceName", //Data source name.
                "collectionName": "tag_data", //Collection name.
                "query": "", // Data query filter.
                "column": [
                    {
                        "name": "unique_id", //Field name.
                        "type": "string" //Field type.
                    },
                    {
                        "name": "sid",
                        "type": "string"
                    },
                    {
                        "name": "user_id",
                        "type": "string"
                    },
                    {
                        "name": "auction_id",
                        "type": "string"
                    },
                    {
                        "name": "content_type",
                        "type": "string"
                    },
                    {
                        "name": "pool_type",
                        "type": "string"
                    },
                    {
                        "name": "frontcat_id",
                        "type": "array",
                        "splitter": ""
                    },
                    {
                        "name": "categoryid",
                        "type": "array",
                        "splitter": ""
                    },
                    {
                        "name": "gmt_create",
                        "type": "string"
                    },
                    {
                        "name": "taglist",
                        "type": "array",
                        "splitter": " "
                    },
                    {
                        "name": "property",
                        "type": "string"
                    },
                    {
                        "name": "scorea",
                        "type": "int"
                    },
                    {
                        "name": "scoreb",
                        "type": "int"
                    },
                    {
                        "name": "scorec",
                        "type": "int"
                    },
                    {
                        "name": "a.b",
                        "type": "document.int"
                    },
                    {
                        "name": "a.b.c",
                        "type": "document.array",
                        "splitter": " "
                    }
                ]
            },
            "stepType": "mongodb"
        }
```
