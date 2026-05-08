# Introduction

The Hive data source provides you with a bidirectional channel for reading from and writing to Hive. This article introduces the Hive data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name, must be consistent with the name of the added data source. | Y | None | Y | |
| readMode | Read mode: * Read data based on HDFS file mode. * Read data based on Hive JDBC mode (supports data condition filtering). **Note** When reading data based on Hive JDBC mode, WHERE conditions are supported for data filtering, but in this scenario, the Hive engine may generate MapReduce tasks at the underlying level, which is slower. When reading data based on HDFS file mode, WHERE conditions for data filtering are not supported. HDFS file mode does not support reading view (VIEW) tables. | N | 'hdfs' | Y | Frontend options: 'hdfs' → 'Read Data Based on HDFS Files'; 'jdbc' → 'Read Data Based on Hive JDBC'; Linkage logic: determines the display of all downstream parameters, clears table and removes partition field when switching to JDBC. |
| table | Table name, used to specify the table for synchronization. Please note case sensitivity. | Y | None | Y | Linkage logic: selecting a table triggers tableColumn update, which then loads partition information. |
| partition | Hive table partition information: * If you are reading data based on Hive JDBC, you do not need to configure this parameter. * If the Hive table you are reading is a partitioned table, you need to configure partition information. The synchronization task will read the data from the corresponding partition. Hive Reader supports using asterisks (*) as wildcards for single-level partitions; multi-level partitions do not support wildcards. * If your Hive table is a non-partitioned table, you do not need to configure partition. | N | None | Y | Display condition: displayed when readMode is not 'jdbc'. |
| where | When you read data based on Hive JDBC mode, you can filter data by setting the where condition. | N | None | Y | Display condition: displayed when readMode is 'jdbc'. |
| session | Hive JDBC read session-level configuration, for example: SET hive.exec.parallel=true | N | None | Y | Display condition: displayed when readMode is 'jdbc'. |
| splitPk | Split key. You can use a column from the source data table as the split key; it is recommended to use a primary key or an indexed column as the split key. | N | None | Y | Display condition: displayed when readMode is 'jdbc'. |
| parquetSchema | Schema configuration for Parquet tables. | N | None | Y | Display condition: displayed when readMode is 'hdfs'. Tooltip: 'Parquet tables automatically read the Schema; if there are no special requirements, you do not need to configure this parameter' |
| successOnNoFile | Whether to ignore when the source file does not exist. | N | false | Y | Display condition: displayed when readMode is 'hdfs' and the feature toggle is enabled; Frontend options: 'true' → 'Yes'; 'false' → 'No'. |
| successOnNoPartition | Whether to ignore when the source partition does not exist. | N | false | Y | Display condition: displayed when readMode is 'hdfs' and the feature toggle is enabled; Frontend options: 'true' → 'Yes'; 'false' → 'No'. |
| column | The field columns to read, for example `"column": ["id", "name"]`. * Supports column pruning: you can export partial columns. * Supports column reordering: you can export columns in an order different from the table Schema. * Supports configuring partition columns. * Supports configuring constants. * column must explicitly specify the set of columns to synchronize and cannot be empty. | Y | None | Y | |
| querySql | When you read data based on Hive JDBC mode, you can directly configure querySql to read data. | N | None | N | |
| fileSystemUsername | When reading data based on HDFS mode, the user configured on the page is used by default. If the data source page is configured for anonymous login, the admin account is used by default. If permission issues occur during the synchronization task, you need to switch to script mode for configuration. | N | None | N | |
| hivePartitionColumn | If you want to synchronize partition field values downstream, you can switch to script mode for configuration. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "hive",
  "parameter": {
    "datasource": "",
    "table": "",
    "readMode": "",
    "partition": "",
    "column": [],
    "querySql": "",
    "where": "",
    "fileSystemUsername": "",
    "hivePartitionColumn": ""
  },
  "name": "Reader",
  "category": "reader"
}
```
