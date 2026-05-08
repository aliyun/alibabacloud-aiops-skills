# Introduction

The Milvus data source provides you with a channel for writing to the Milvus vector database. This article introduces the Milvus data synchronization capabilities of DataWorks.

> **Supported Direction**: This data source only supports being used as a Destination (write), and does not support being used as a Source (read).

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| collection | The collection name to write to in Milvus. | Y | None | Y | Linkage logic: after selecting a table, the partition field is cleared, and the partition list is fetched as the source for partition options. |
| partition | The partition of the Milvus collection to write to. If not specified, the default _default partition is used. | N | undefined | Y | Linkage logic: reset to undefined when collection is switched; option data comes from the collection's partitionList. |
| writeMode | Milvus database supports upsert and insert write methods: * upsert: In non-autoid tables, updates an Entity in the Collection based on the primary key; in autoid tables, Milvus replaces the primary key in the Entity with an auto-generated primary key and inserts the data. * insert: Mostly used for autoid tables where Milvus auto-generates the primary key. Using insert on non-autoid tables will cause data duplication. | Y | 'upsert' | Y | Frontend options: 'insert' → 'Mostly used for autoid tables to let Milvus auto-generate primary keys'; 'upsert' → 'Update Entity based on primary key in non-autoid tables'. |
| batchSize | The batch size for a single write to Milvus. | Y | '1024' | Y | |
| schemaCreateMode | Performs a collection check before synchronization, and performs collection operations according to the configured mode. Supports the following three modes: * createIfNotExist: When the collection does not exist, creates the corresponding collection based on the configured column and other information for synchronization. * ignore: When the collection does not exist, ignores it. * recreate: For each synchronization, first deletes the original collection, then recreates the collection based on column and other information for synchronization. | Y | 'ignore' | Y | Frontend options: 'createIfNotExist' → 'Create if not exists'; 'ignore' → 'Ignore'; 'recreate' → 'Recreate'; linkage logic: displays enableDynamicSchema when not 'ignore'. |
| enableDynamicSchema | Whether to enable dynamic Schema when creating the collection. | Y | true | Y | Display condition: displayed when schemaCreateMode is not 'ignore'; frontend options: true → 'Yes'; false → 'No'. |
| column | Milvus synchronization write Field columns, configured as an array. Single field information is configured in JSON format, including: * name: Field name * type: Field type * Field attributes: such as the dimension of vector fields `"dimension":3` | Y | None | Y | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "milvus",
            "parameter": {
                "schemaCreateMode": "createIfNotExist",     //Collection creation mode
                "enableDynamicSchema": true,            //Whether to enable dynamic Schema when creating the collection
                "envType": 1,
                "datasource": "zm_test",
                "column": [  //Synchronization fields
                    {
                        "name": "floatv1",
                        "type": "FloatVector",
                        "dimension": "3"
                    },
                    {
                        "name": "incol",
                        "type": "Int16"
                    }
                ],
                "writeMode": "insert",  //Write method
                "collection": "test",  //Write collection
                "batchSize": 1024      // Single write batch size
            },
            "name": "Writer",
            "category": "writer"
        }
```
