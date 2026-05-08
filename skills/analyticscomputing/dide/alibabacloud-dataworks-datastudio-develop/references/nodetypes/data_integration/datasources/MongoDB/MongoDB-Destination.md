# Introduction

The MongoDB data source provides you with a bidirectional channel for reading from and writing to MongoDB. This article introduces the MongoDB data synchronization capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| collectionName | MongoDB collection name. | Y | None | Y |  |
| column | MongoDB document column names, configured as an array to represent multiple columns in MongoDB. * name: The name of the Column. * type: The type of the Column. * int: Represents a 32-bit integer. * string: Represents a string. * array: `splitter` must be configured, used to split the source string, for example: if the source data is `a,b,c`, and `splitter` is configured as English comma `,`, the data will be split into array `["a","b","c"]` and written to MongoDB. ```json {"type":"array","name":"col_split_array","splitter":",","itemtype":"string"} ``` **Note** The `itemtype` parameter of the `array` type supports enumeration types including `double`, `int`, `long`, `bool`, `bytes`, and `string`. * json: Represents JSON string format. * long: Represents a long integer. * date: Represents a date. * double: Represents a floating-point number. **Note** MongoDB Writer configuration also supports writing nested types. The `type` configuration adds a `document.` prefix to indicate writing nested types, and `name` can be configured with cascading, for example: ```json {"type":"document.string","name":"col_nest.col_string"} {"type":"document.array","name":"col_nest.col_split_array","splitter":",","itemtype":"string"} ``` * splitter: Special delimiter. This parameter is used only when the string to be processed needs to be split by a delimiter into a character array. Through the delimiter specified by this parameter, the string is split and stored in a MongoDB array. | Y | None | Y |  |
| writeMode | Specifies whether to overwrite data during transmission, including isReplace and replaceKey: * isReplace: When set to true, it means performing an overwrite operation for the same replaceKey. When set to false, it means no overwrite. * replaceKey: replaceKey specifies the business primary key of each row record, used for overwriting (replaceKey does not support multiple keys, usually refers to the primary key in MongoDB). **Note** When isReplace is set to true and a non-`_id` field is configured as replaceKey, an error similar to the following will occur during subsequent runs: ```shell After applying the update, the (immutable) field '_id' was found to have been altered to _id: "2" ``` The reason is that there is data in the written data where the `_id` does not match the replaceKey. For details, please refer to FAQ: **Error: After applying the update, the (immutable) field '_id' was found to have been altered to _id: "2"** . | N | None | Y |  |
| preSql | Indicates the pre-operation before writing data to MongoDB, such as cleaning up historical data, etc. If preSql is empty, it means no pre-operation is configured. When configuring preSql, you need to ensure that preSql conforms to JSON syntax requirements. | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "mongodb",//Plugin name.
            "parameter": {
                "datasource": "",//Data source name.
                "column": [
                    {
                        "name": "_id",//Column name.
                        "type": "ObjectId"//Data type. If replacekey is _id, the type here must be configured as ObjectID. If configured as string, replacement will not work.
                    },
                    {
                        "name": "age",
                        "type": "int"
                    },
                    {
                        "name": "id",
                        "type": "long"
                    },
                    {
                        "name": "wealth",
                        "type": "double"
                    },
                    {
                        "name": "hobby",
                        "type": "array",
                        "splitter": " "
                    },
                    {
                        "name": "valid",
                        "type": "boolean"
                    },
                    {
                        "name": "date_of_join",
                        "format": "yyyy-MM-dd HH:mm:ss",
                        "type": "date"
                    }
                ],
                "writeMode": {//Write mode.
                    "isReplace": "true",
                    "replaceKey": "_id"
                },
                "collectionName": "datax_test"//Connection name.
            },
            "name": "Writer",
            "category": "writer"
        }
```
