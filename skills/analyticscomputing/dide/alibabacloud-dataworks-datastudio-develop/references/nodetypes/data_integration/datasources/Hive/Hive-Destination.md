# Introduction

The Hive data source provides you with a bidirectional channel for reading from and writing to Hive. This article introduces the Hive data synchronization capabilities supported by DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name, must be consistent with the name of the added data source. | Y | None | Y | |
| table | The Hive table name to write to. Please note case sensitivity. | Y | None | Y | Linkage logic: selecting a table triggers tableColumn update, which then loads partition information; prerequisite: tables can be selected only after the data source connection is established. |
| partition | Hive table partition information: * If the Hive table you are writing to is a partitioned table, you need to configure partition information. The synchronization task will write data to the corresponding partition. * If your Hive table is a non-partitioned table, you do not need to configure partition. | N | None | Y | Linkage logic: after table selection, partition column information is automatically fetched and a default partition template is generated. |
| writeMode | The write mode for Hive table data. After data is written to the HDFS file, the Hive Writer plugin will execute `LOAD DATA INPATH` to load data into the Hive table. * truncate: Clears data first, then loads. * append: Retains existing data. * Other: Indicates that data is written to the HDFS file, and no loading into the Hive table is needed. | Y | 'append' | Y | Frontend options: 'truncate' → 'Clear Existing Data Before Writing (load overwrite)'; 'append' → 'Retain Existing Data Before Writing (load)'. |
| column | The field columns to write, for example `"column": ["id", "name"]`. * Supports column pruning: you can export partial columns. * column must explicitly specify the set of columns to synchronize and cannot be empty. * Does not support column reordering. | Y | None | Y | |
| parquetSchema | Schema configuration for Parquet tables. | N | None | Y | |
| hiveConfig | You can configure further Hive extension parameters in hiveConfig, including hiveCommand, jdbcUrl, username, and password. * hiveCommand: Represents the full path of the Hive client tool. After executing `hive -e`, the `LOAD DATA INPATH` data loading operation associated with writeMode will be executed. * jdbcUrl, username, and password represent the Hive JDBC access information. | Y | None | N | |
| fileSystemUsername | When writing data to a Hive table, the user configured on the page is used by default. If the data source page is configured for anonymous login, the admin account is used by default. If permission issues occur during the synchronization task, you need to switch to script mode for configuration. | N | None | N | |
| enableColumnExchange | When this parameter is configured as True, column reordering is enabled. Only supports Text format. | N | None | N | |
| nullFormat | Data Integration provides nullFormat to define which strings can represent null. For example: configuring `nullFormat:"null"`, if the source data is null, Data Integration will treat it as a null field. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "hive",
            "parameter": {
                "partition": "year=a,month=b,day=c", // Partition configuration
                "datasource": "hive_ha_shanghai", // Data source
                "table": "partitiontable2", // Target table
                "column": [ // Column configuration
                    "id",
                    "name",
                    "age"
                ],
                "writeMode": "append" ,// Write mode
                "fileSystemUsername" : "hdfs"
            },
            "name": "Writer",
            "category": "writer"
        }
```
