# Introduction

The MaxCompute data source serves as a data hub, providing you with a bidirectional channel for reading from and writing to MaxCompute. The DataWorks MaxCompute data source can use the Tunnel Endpoint address to access the Tunnel service of the corresponding MaxCompute project, thereby synchronizing the project's data through upload and download methods. Upload and download operations using the Tunnel service involve DownloadTable operations.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| schema | The schema name of the data table to be written (case-insensitive). Only required when the MaxCompute project uses a three-layer model, otherwise not filled. | N (Y for three-layer model) | None | Y | Display condition: when the MaxCompute project uses a three-layer model; linkage logic: switching clears table and partition |
| table | The table name of the data table to be written (case-insensitive), does not support filling in multiple tables. If an external table is selected, a warning "MaxCompute external tables are not supported" will be displayed. | Y | None | Y | Linkage logic: after selecting a table, partition information is fetched and default values are filled in; supports auto-creating the destination table from the source table structure |
| partition | The partition information of the data table to be written, must be specified down to the last level partition. For example, to write data to a three-level partitioned table, you must configure it to the last level partition, for example `pt=20150101,type=1,biz=2`. For non-partitioned tables, do not fill in this value. MaxCompute Writer does not support data routing writes, so for partitioned tables, please ensure that data is written to the last level partition. | Required for partitioned tables, not filled for non-partitioned tables | None | Y | Display condition: displayed for partitioned tables; destination does not support multiple partition groups |
| column | The list of fields to be imported. When importing all fields, you can configure it as `["*"]`. When you need to insert some MaxCompute columns, fill in the partial columns, for example `["id","name"]`. MaxCompute Writer supports column selection and column reordering. For example, if a table has three fields a, b, and c, and you only want to synchronize fields c and b, you can configure it as `["c","b"]`. During the import process, field a will automatically be padded with null. The collection of columns to be synchronized must be explicitly specified and cannot be empty. | Y | None | Y | Configuring as `["*"]` is not recommended |
| truncate | Pre-write data cleanup strategy. | Y | true | Y | Frontend options: `Clear existing data before writing (Insert Overwrite)` → `true`; `Keep existing data before writing (Insert Into)` → `false`; frontend default value: true |
| emptyAsNull | When the source is an empty string, whether to convert it to NULL when writing to MaxCompute. | N | false | Y | Frontend options: `Yes` → `true`; `No` → `false`; frontend default value: false |
| tunnelQuota | MaxCompute dedicated Tunnel. When not specified, the default shared Tunnel is used. | N | None | Y | |
| overLengthRule | Processing strategy when a MaxCompute String field exceeds the limit (exceeds the maxOdpsFieldLength setting). | N | Backend controlled | Y | Frontend options: `Truncate to 8MB` → `truncate`; `Write normally` → `keepOn`; `Set to NULL` → `setNull` |
| consistencyCommit | Whether data is visible after synchronization is complete. | N | false | Y | Frontend options: `Yes` → `true`; `No` → `false`; when "Yes" is selected, a prompt displays "The amount of written data cannot exceed 1TB, otherwise the task will fail" |

## Configuration Example

```json
{
  "stepType": "odps",
  "parameter": {
    "datasource": "odps_project_name",
    "schema": "schema_name",
    "table": "delta_target_table",
    "partition": "pt=20240101",
    "column": [
      "id", 
      "name", 
      "value"
    ],
    "truncate": false,
    "emptyAsNull": false,
    "consistencyCommit": true,
    "overLengthRule": "truncate",
    "maxOdpsFieldLength": 8388608
  },
  "name": "Writer",
  "category": "writer"
}
```
