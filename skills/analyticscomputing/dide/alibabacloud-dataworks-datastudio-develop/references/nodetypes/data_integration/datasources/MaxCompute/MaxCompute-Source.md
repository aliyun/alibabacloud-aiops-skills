# Introduction

The MaxCompute data source serves as a data hub, providing you with a bidirectional channel for reading from and writing to MaxCompute. The DataWorks MaxCompute data source can use the Tunnel Endpoint address to access the Tunnel service of the corresponding MaxCompute project, thereby synchronizing the project's data through upload and download methods. Upload and download operations using the Tunnel service involve DownloadTable operations.

# Source
## Parameter Description
| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| schema | The schema name of the data table to be read. | N | None | Y | Display condition: when the MaxCompute project uses a three-layer model; linkage logic: switching clears table and partition |
| table | The table name of the data table to be read (case-insensitive). | Y | None | Y | Linkage logic: after selecting a table, partition information is fetched and default values are filled in |
| partition | The partition information where the data to be read is located. ODPS partition configuration supports Linux Shell wildcards, `*` represents 0 or more characters, `?` represents any single character. The partition must exist; if the partition does not exist, the task will report an error. | Required for partitioned tables, not filled for non-partitioned tables | None | Y | Display condition: enableWhere=false |
| column | The column information of the MaxCompute source table to be read. For example, if the fields of table test are id, name, and age: if you need to read id, name, and age in order, you should configure it as `["id","name","age"]` or `["*"]`; if you want to read name and id in order, you should configure it as `["name","id"]`; if you want to add a constant field, you should configure it as `["age","name","'1988-08-08 08:08:08'","id"]` (constant columns are wrapped with `'` at both ends). When using data filter mode, MaxCompute functions can be used in column. The collection of columns to be synchronized must be explicitly specified and cannot be empty. | Y | None | Y | Configuring as `["*"]` is not recommended |
| enableWhere | Filter method. false=partition filter, true=data filter. | N | false for partitioned tables, true for non-partitioned tables | Y | Linkage logic: when enableWhere=false, partition is displayed and where is cleared; when enableWhere=true, where is displayed and partition is cleared. **⚠️ When the frontend default value is auto-filled, it must be determined: if it is a non-partitioned table, it must be set to true** |
| where | When using WHERE data filtering, fill in the specific WHERE clause content. Supports using ODPS SQL built-in functions (such as `now`, `GETDATE`, `DATEADD` and other time functions), which can implement incremental data filtering based on time ranges. Example: `"gmt_modified >= DATEADD(now(), -1, 'dd')"` means filtering data modified within the last 1 day. | N | None | Y | Prerequisite: enableWhere=true |
| tunnelQuota | MaxCompute dedicated Tunnel. When not specified, the default shared Tunnel is used. | N | None | Y | |

## Configuration Example

```json
{
  "stepType": "odps",
  "parameter": {
    "datasource": "odps_project_name",
    "table": "source_table",
    "partition": "pt=20240101,ds=hangzhou",
    "column": ["id", "name", "'1988-08-08 08:08:08' as constant_col", "age"],
    "enableWhere": false
  },
  "name": "Reader",
  "category": "reader"
}
```
