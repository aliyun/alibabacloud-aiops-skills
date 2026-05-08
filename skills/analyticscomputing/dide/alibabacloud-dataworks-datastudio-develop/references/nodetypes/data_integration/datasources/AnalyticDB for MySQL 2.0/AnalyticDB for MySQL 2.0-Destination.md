# Introduction

The AnalyticDB for MySQL 2.0 data source provides you with a bidirectional channel for reading from and writing to AnalyticDB for MySQL 2.0. This article introduces DataWorks' support for AnalyticDB for MySQL 2.0 data synchronization capabilities.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| Connection URL | AnalyticDB for MySQL 2.0 connection information, format is Address:Port. | Y | None | N |  |
| Database | The database name of AnalyticDB for MySQL 2.0. | Y | None | N |  |
| Access Id | The AccessKey Id for AnalyticDB for MySQL 2.0. | Y | None | N |  |
| Access Key | The AccessKey Secret for AnalyticDB for MySQL 2.0. | Y | None | N |  |
| datasource | Data source name. Script mode supports adding data sources, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | N |  |
| table | The table name of the destination table. | Y | None | N |  |
| partition | The partition name of the destination table. This field must be specified when the destination table is a regular table. | N | None | N |  |
| writeMode | AnalyticDB for MySQL 2.0 Writer implements two modes for importing data into AnalyticDB for MySQL 2.0. * Insert mode: When primary key conflict occurs, the new record overwrites the old record. * Load mode: Data is imported through a third-party system relay. | Y | None | N |  |
| column | The column list of the destination table. Can be \["\*"\], or a specific column list, for example \["a", "b", "c"\]. | Y | None | N |  |
| suffix | The AnalyticDB for MySQL 2.0 URL configuration format is `ip:port`. This part is a customized connection string and is an optional parameter. When actually accessing the AnalyticDB for MySQL 2.0 database, it becomes a JDBC database connection string. For example, configure suffix as `autoReconnect=true&failOverReadOnly=false&maxReconnects=10`. | N | None | N |  |
| batchSize | The batch size for AnalyticDB for MySQL 2.0 data write submission. This value only takes effect when writeMode is insert. | Required when writeMode is insert. | None | N |  |
| bufferSize | DataX data collection buffer size. The purpose of the buffer is to accumulate a larger Buffer. Source data first enters this Buffer for sorting, and after sorting is complete, it is submitted to AnalyticDB for MySQL 2.0. Sorting is based on the partition column mode of AnalyticDB for MySQL 2.0, and the purpose of sorting is to make the data order more friendly to the AnalyticDB for MySQL 2.0 server (for performance reasons). Data in the BufferSize buffer is submitted to AnalyticDB for MySQL 2.0 in batches of batchSize. Typically, bufferSize needs to be set to a multiple of the batchSize. This value only takes effect when writeMode is insert. | Required when writeMode is insert. | Not configured by default, this feature is not enabled. | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"ads",//Plugin name.
            "parameter":{
                "partition":"",//Partition name of the destination table.
                "datasource":"",//Data source.
                "column":[//Fields.
                     "id"
                ],
                "writeMode":"insert",//Write mode.
                "batchSize":"256",//The batch size for one-time submission.
                "table":"",//Table name.
                "overWrite":"true"//Whether AnalyticDB for MySQL 2.0 overwrites the currently written table. true means overwrite, false means append. This value only takes effect when writeMode is Load.
                "options.ignoreEmptySource":true//Ignore source data empty file error messages, the task will not report an error. Default is true. If not configured, the default is true. When set to false, the task will report an error if source data cannot be read.
            },
            "name":"Writer",
            "category":"writer"
        }
```
