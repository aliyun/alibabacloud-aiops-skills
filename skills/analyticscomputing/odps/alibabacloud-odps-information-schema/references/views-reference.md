# Information Schema Views Reference

> Related: [entities.md](entities.md), [joins.md](joins.md), [SKILL.md](../SKILL.md)

All views are in `SYSTEM_CATALOG.INFORMATION_SCHEMA`. Must run `SET odps.namespace.schema=true;` before querying.

**Index:** [TABLES](#tables) · [COLUMNS](#columns) · [PARTITIONS](#partitions) · [PARTITION_ACCESS_INFO](#partition_access_info) · [TABLE_ACCESS_INFO](#table_access_info) · [TASKS_HISTORY](#tasks_history) · [TASKS](#tasks) · [TUNNELS_HISTORY](#tunnels_history) · [TABLE_PRIVILEGES](#table_privileges) · [COLUMN_PRIVILEGES](#column_privileges) · [CATALOG_PRIVILEGES](#catalog_privileges) · [TABLE_LABELS](#table_labels) · [TABLE_LABEL_GRANTS](#table_label_grants) · [COLUMN_LABELS](#column_labels) · [COLUMN_LABEL_GRANTS](#column_label_grants) · [USERS](#users) · [ROLES](#roles) · [USER_ROLES](#user_roles) · [UDFS](#udfs) · [UDF_RESOURCES](#udf_resources) · [UDF_PRIVILEGES](#udf_privileges) · [RESOURCES](#resources) · [RESOURCE_PRIVILEGES](#resource_privileges) · [INSTALLED_PACKAGES](#installed_packages) · [PACKAGE_OBJECTS](#package_objects) · [PACKAGE_PRIVILEGES](#package_privileges) · [QUOTA_USAGE](#quota_usage) · [CATALOGS](#catalogs) · [SCHEMAS](#schemas) · [VOLUMES](#volumes) · [FOREIGN_SERVERS](#foreign_servers)

## Real-Time Views (~3 hour delay)

> **Note**: TASKS is a live view with seconds-level delay (Preview). All other views in this section have ~3 hour delay.

### CATALOGS

**MCP:** `get_project` | **SQL:** `execute_sql` + hints

Project list.

| Column | Type | Description |
|---|---|---|
| catalog_name | STRING | Project name |
| status | STRING | Project status: Allowed (normal), Denied (frozen) |
| create_time | DATETIME | Project creation time |
| owner_id | STRING | Project owner ID |
| owner_name | STRING | Project owner Aliyun account name |
| settings | STRING | Project settings (JSON format) |
| region | STRING | Project region |

**settings common keys:**
- `odps.timemachine.retention.days` - Backup retention days
- `odps.security.ip.whitelist` - IP whitelist
- `odps.sql.metering.value.max` - Single SQL cost limit

### CATALOG_PRIVILEGES

**MCP:** `execute_sql` + hints

Project-level privileges (e.g., CreateInstance, ListTable).

| Column | Type | Description |
|---|---|---|
| catalog_name | STRING | Project name |
| user_catalog | STRING | Authorized user's project |
| user_name | STRING | Authorized user name |
| user_id | STRING | Authorized user ID |
| grantor | STRING | Grantor account (reserved field) |
| privilege_type | STRING | Privilege type |

### COLUMNS

**MCP:** `get_table_schema` | **SQL:** `execute_sql` + hints

Column-level metadata for all tables.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name (currently NULL) |
| table_name | STRING | Table name |
| column_name | STRING | Column name |
| ordinal_position | BIGINT | Column order |
| column_default | STRING | Column default value |
| is_nullable | BOOLEAN | Whether nullable |
| data_type | STRING | Data type (e.g., STRING, BIGINT) |
| column_comment | STRING | Column comment |
| is_partition_key | BOOLEAN | Whether partition key |
| is_primary_key | BOOLEAN | Whether primary key |

### COLUMN_LABEL_GRANTS

**MCP:** `execute_sql` + hints

Column LABEL grant information.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name |
| table_name | STRING | Table name |
| column_name | STRING | Column name |
| user_catalog | STRING | User's project |
| user_name | STRING | User name |
| user_id | STRING | User ID |
| grantor | STRING | Grantor account (reserved field) |
| label_level | STRING | Granted label level |
| expired | DATETIME | Expiration time |

### COLUMN_LABELS

**MCP:** `execute_sql` + hints

Column-level LABEL information.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name (currently NULL) |
| table_name | STRING | Table name |
| column_name | STRING | Column name |
| label_type | STRING | Label type |
| label_level | STRING | Label level |

### COLUMN_PRIVILEGES

**MCP:** `execute_sql` + hints

Column-level privileges.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name |
| table_name | STRING | Table name |
| column_name | STRING | Column name |
| user_catalog | STRING | User's project |
| user_name | STRING | User name |
| user_id | STRING | User ID |
| grantor | STRING | Grantor account (reserved field) |
| privilege_type | STRING | Privilege type |

### INSTALLED_PACKAGES

**MCP:** `execute_sql` + hints

Installed Package information per project.

| Column | Type | Description |
|---|---|---|
| installed_package_catalog | STRING | Project where package is installed |
| package_catalog | STRING | Package source project |
| package_name | STRING | Package name |
| installed_time | STRING | Installation time |
| allowed_label | STRING | Shared label settings |

### PACKAGE_PRIVILEGES

**MCP:** `execute_sql` + hints

Package authorization information.

| Column | Type | Description |
|---|---|---|
| package_catalog | STRING | Package source project |
| package_name | STRING | Package name |
| user_catalog | STRING | Authorized user's project |
| user_name | STRING | Authorized user name |
| user_id | STRING | Authorized user ID |
| grantor | STRING | Grantor account (reserved field) |
| privilege_type | STRING | Privilege type |

### PACKAGE_OBJECTS

**MCP:** `execute_sql` + hints

Objects within a Package.

| Column | Type | Description |
|---|---|---|
| package_catalog | STRING | Package source project |
| package_name | STRING | Package name |
| object_schema | STRING | Object schema within package |
| object_type | STRING | Package object type |
| object_name | STRING | Package object name |
| column_name | STRING | Column name (only when object_type is table) |
| allowed_privilege | STRING | Shared privilege settings |
| allowed_label | STRING | Shared label settings |

### PARTITIONS

**MCP:** `get_partition_info` | **SQL:** `execute_sql` + hints

Partition-level metadata for all tables.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name |
| table_name | STRING | Table name |
| partition_name | STRING | Partition spec (e.g., ds=20240101) |
| create_time | DATETIME | Partition creation time |
| last_modified_time | DATETIME | Partition last modification time |
| last_access_time | DATETIME | Partition last access time (reference value, up to 24h difference; not collected for ALGO jobs or Hologres direct reads) |
| data_length | BIGINT | Partition data size in bytes |
| is_archived | BOOLEAN | Reserved field, no meaning |
| is_exstore | BOOLEAN | Reserved field, no meaning |
| storage_tier | STRING | Storage tier: standard (standard), lowfrequency (low-frequency), longterm (long-term) |
| cluster_type | STRING | Cluster type: HASH, RANGE |
| number_buckets | BIGINT | Number of buckets for clustered table (0 = dynamic) |
| lifecycle_enabled | BOOLEAN | Whether partition lifecycle is enabled |

### PARTITION_ACCESS_INFO

**MCP:** `execute_sql` + hints

Partition access statistics.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name (non-3-tier project is default) |
| table_name | STRING | Table name |
| partition_name | STRING | Partition name |
| access_count | BIGINT | Access count on archive date |
| access_bytes | BIGINT | Data volume accessed on archive date (bytes) |
| ds | STRING | Data archive date |

### RESOURCES

**MCP:** `execute_sql` + hints

Resource information per project.

| Column | Type | Description |
|---|---|---|
| resource_catalog | STRING | Project where resource exists |
| resource_schema | STRING | Schema name |
| resource_name | STRING | Resource name |
| resource_type | STRING | Resource type: archive, py, jar, table |
| owner_id | STRING | Resource owner ID |
| owner_name | STRING | Resource owner Aliyun account name |
| create_time | DATETIME | Resource creation time |
| last_modified_time | DATETIME | Resource last modification time |
| size | BIGINT | Resource size in bytes |
| comment | STRING | Resource comment |
| is_temp_resource | BOOLEAN | Whether temporary resource |

### RESOURCE_PRIVILEGES

**MCP:** `execute_sql` + hints

Resource privileges.

| Column | Type | Description |
|---|---|---|
| resource_catalog | STRING | Project name |
| resource_schema | STRING | Schema name |
| resource_name | STRING | Resource name |
| user_catalog | STRING | Authorized user's project |
| user_name | STRING | Authorized user name |
| user_id | STRING | Authorized user ID |
| grantor | STRING | Grantor account (reserved field) |
| privilege_type | STRING | Privilege type |

### ROLES

**MCP:** `execute_sql` + hints

Project-level and account-level roles.

| Column | Type | Description |
|---|---|---|
| role_catalog | STRING | Project name (NULL for tenant-level roles) |
| role_name | STRING | Role name |
| role_label | STRING | Role label |
| comment | STRING | Role comment |

### TABLES

**MCP:** `list_tables` / `get_table_schema` | **SQL:** `execute_sql` + hints

Table-level metadata for all projects.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name |
| table_name | STRING | Table name |
| table_type | STRING | Table type: MANAGED_TABLE, VIRTUAL_VIEW, EXTERNAL_TABLE, MATERIALIZED_VIEW, METADATA_TABLE, OBJECT_TABLE |
| is_partitioned | BOOLEAN | Whether partitioned |
| owner_id | STRING | Table owner ID |
| owner_name | STRING | Table owner Aliyun account name |
| create_time | DATETIME | Table creation time |
| last_modified_time | DATETIME | Table data last modification time |
| last_access_time | DATETIME | Table last access time (NULL for partitioned tables; reference value up to 24h difference; not collected for ALGO jobs or Hologres direct reads) |
| data_length | BIGINT | Data size in bytes (for non-partitioned tables; NULL for partitioned tables -- see PARTITIONS view) |
| table_comment | STRING | Table comment |
| lifecycle | BIGINT | Lifecycle in days |
| lifecycle_enabled | BOOLEAN | Whether lifecycle recycling is enabled |
| is_archived | BOOLEAN | Reserved field, no meaning |
| table_exstore_type | STRING | Extreme storage indicator: EXSTORE_TABLE_VIRTUAL, EXSTORE_TABLE_PHYSICAL |
| storage_tier | STRING | Storage tier: standard (standard), lowfrequency (low-frequency), longterm (long-term) |
| cluster_type | STRING | Cluster type: HASH, RANGE |
| number_buckets | BIGINT | Number of buckets for clustered table (0 = dynamic) |
| view_original_text | STRING | View definition for VIRTUAL_VIEW type |
| has_primary_key | BOOLEAN | Whether has primary key columns |
| is_transactional | BOOLEAN | Whether transactional table |
| is_delta_table | BOOLEAN | Whether Delta Table |
| table_storage | STRING | Table storage service |
| table_format | STRING | Table storage format (e.g., ORC, Parquet) |

### TABLE_ACCESS_INFO

**MCP:** `execute_sql` + hints

Table access statistics.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name (non-3-tier project is default) |
| table_name | STRING | Table name |
| access_count | BIGINT | Access count on archive date |
| access_bytes | BIGINT | Data volume accessed on archive date (bytes) |
| ds | STRING | Data archive date |

### TABLE_LABEL_GRANTS

**MCP:** `execute_sql` + hints

TABLE LABEL grant information.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name |
| table_name | STRING | Table name |
| user_catalog | STRING | Authorized user's project |
| user_name | STRING | Authorized user name |
| user_id | STRING | Authorized user ID |
| grantor | STRING | Grantor account (reserved field) |
| label_level | STRING | Label level |
| expired | DATETIME | Expiration time |

### TABLE_LABELS

**MCP:** `execute_sql` + hints

Table LABEL information.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name (currently NULL) |
| table_name | STRING | Table name |
| label_type | STRING | Label type |
| label_level | BIGINT | Label level |

> **Type mismatch warning:** `TABLE_LABELS.label_level` is BIGINT, but `TABLE_LABEL_GRANTS.label_level`, `COLUMN_LABELS.label_level`, and `COLUMN_LABEL_GRANTS.label_level` are STRING. When JOINing these views on `label_level`, use explicit CAST:
> ```sql
> JOIN TABLE_LABEL_GRANTS g ON CAST(t.label_level AS STRING) = g.label_level
> ```

### TABLE_PRIVILEGES

**MCP:** `execute_sql` + hints

Table-level privileges.

| Column | Type | Description |
|---|---|---|
| table_catalog | STRING | Project name |
| table_schema | STRING | Schema name (currently NULL) |
| table_name | STRING | Table name |
| user_catalog | STRING | Authorized user's project |
| user_name | STRING | Authorized user name |
| user_id | STRING | Authorized user ID |
| grantor | STRING | Grantor account (reserved field) |
| privilege_type | STRING | Privilege type |
| expired | DATETIME | Privilege expiration time |

### UDF_PRIVILEGES

**MCP:** `execute_sql` + hints

UDF authorization information.

| Column | Type | Description |
|---|---|---|
| udf_catalog | STRING | Project name |
| udf_schema | STRING | Schema name |
| udf_name | STRING | UDF name |
| user_catalog | STRING | Authorized user's project |
| user_name | STRING | Authorized user name |
| user_id | STRING | Authorized user ID |
| grantor | STRING | Grantor account (reserved field) |
| privilege_type | STRING | Privilege type |

### UDFS

**MCP:** `execute_sql` + hints

UDF information.

| Column | Type | Description |
|---|---|---|
| udf_catalog | STRING | Project name |
| udf_schema | STRING | Schema name (currently NULL) |
| udf_name | STRING | UDF name |
| owner_id | STRING | UDF owner ID |
| owner_name | STRING | UDF owner Aliyun account name |
| create_time | DATETIME | Creation time |
| last_modified_time | DATETIME | Last modification time |

### UDF_RESOURCES

**MCP:** `execute_sql` + hints

UDF resource dependencies.

| Column | Type | Description |
|---|---|---|
| udf_catalog | STRING | UDF project name |
| udf_schema | STRING | UDF schema name |
| udf_name | STRING | UDF name |
| resource_catalog | STRING | Resource project |
| resource_schema | STRING | Resource schema |
| resource_name | STRING | Resource name |

### USERS

**MCP:** `execute_sql` + hints

User list.

| Column | Type | Description |
|---|---|---|
| user_catalog | STRING | User's project name (NULL for tenant-level users) |
| identity_provider | STRING | Account type: ALIYUN, RAM, RAMRole |
| user_name | STRING | User name |
| user_id | STRING | User ID |
| user_label | STRING | User label |

### USER_ROLES

**MCP:** `execute_sql` + hints

User role assignments.

| Column | Type | Description |
|---|---|---|
| user_role_catalog | STRING | Role's project name (NULL for tenant-level roles) |
| role_name | STRING | Role name |
| user_name | STRING | User name |
| user_id | STRING | User ID |

### SCHEMAS

**MCP:** `list_schemas` | **SQL:** `execute_sql` + hints

Schema information within a project.

| Column | Type | Description |
|---|---|---|
| schema_catalog | STRING | Schema's project name |
| schema_name | STRING | Schema name |
| owner_id | STRING | Schema owner Aliyun account ID |
| owner_name | STRING | Schema owner Aliyun account name |
| create_time | DATETIME | Schema creation time |
| last_modified_time | DATETIME | Schema last modification time |
| schema_type | STRING | Schema type |
| comment | STRING | Schema comment |

### QUOTA_USAGE

**MCP:** `execute_sql` + hints

Real-time snapshot of Subscription compute Quota resource usage.

> **Note:** QUOTA_USAGE only returns data for Subscription (包年包月) quota groups. Pay-as-you-go projects will show zero values. If all values are zero, verify the project has subscription quota configured.

| Column | Type | Description |
|---|---|---|
| name | STRING | Quota name |
| create_time | DATETIME | Quota creation time |
| last_modified_time | DATETIME | Quota last modification time |
| cpu_elastic_quota_max | BIGINT | Non-reserved CPU upper limit (core*100) |
| cpu_elastic_quota_min | BIGINT | Non-reserved CPU lower limit (core*100) |
| cpu_elastic_quota_used | BIGINT | Non-reserved CPU usage (core*100) |
| mem_elastic_quota_max | BIGINT | Non-reserved memory upper limit (MB) |
| mem_elastic_quota_min | BIGINT | Non-reserved memory lower limit (MB) |
| mem_elastic_quota_used | BIGINT | Non-reserved memory usage (MB) |
| cpu_adhoc_quota | BIGINT | Elastic reserved CPU (core*100) |
| cpu_adhoc_quota_used | BIGINT | Elastic reserved CPU usage (core*100) |
| mem_adhoc_quota | BIGINT | Elastic reserved memory (MB) |
| mem_adhoc_quota_used | BIGINT | Elastic reserved memory usage (MB) |
| cpu_quota_max | BIGINT | Reserved CPU upper limit (core*100) |
| cpu_quota_min | BIGINT | Reserved CPU lower limit (core*100) |
| cpu_quota_used | BIGINT | Reserved CPU usage (core*100) |
| mem_quota_max | BIGINT | Reserved memory upper limit (MB) |
| mem_quota_min | BIGINT | Reserved memory lower limit (MB) |
| mem_quota_used | BIGINT | Reserved memory usage (MB) |
| region | STRING | Resource region |

### VOLUMES

**MCP:** `execute_sql` + hints

MaxCompute Volume view.

| Column | Type | Description |
|---|---|---|
| volume_catalog | STRING | Volume project name |
| volume_name | STRING | Volume name |
| volume_type | STRING | Volume type: INTERNAL, EXTERNAL |
| owner_id | STRING | Volume owner ID |
| owner_name | STRING | Volume owner Aliyun account name |
| create_time | DATETIME | Volume creation time |
| last_modified_time | DATETIME | Volume data last modification time |
| location | STRING | Volume storage path |
| comment | STRING | Volume comment |
| storage_provider | STRING | Volume storage engine |
| role_arn | STRING | Volume storage access role ARN |
| lifecycle | BIGINT | Volume lifecycle in days |
| options | STRING | Volume options |

### FOREIGN_SERVERS

**MCP:** `execute_sql` + hints

MaxCompute ForeignServer view.

| Column | Type | Description |
|---|---|---|
| server_name | STRING | Server name |
| server_type | STRING | Server type |
| owner_id | STRING | Server owner ID |
| owner_name | STRING | Server owner Aliyun account name |
| create_time | DATETIME | Server creation time |
| last_modified_time | DATETIME | Data last modification time |
| options | STRING | Server options |

### TASKS

**MCP:** `execute_sql` + hints

Real-time snapshot of running tasks for monitoring (Preview, no SLA).

| Column | Type | Description |
|---|---|---|
| task_catalog | STRING | Project name |
| task_name | STRING | Job name |
| task_type | STRING | Job type: SQL, CUPID (Spark/Mars), SQLCost (SQL estimate), SQLRT (accelerated query), LOT (MapReduce), PS (PAI Parameter Server), AlgoTask (ML) |
| inst_id | STRING | Instance ID |
| status | STRING | Job status: Running, Waiting |
| owner_id | STRING | Submitter Aliyun account ID |
| owner_name | STRING | Submitter Aliyun account name |
| start_time | DATETIME | Job start time |
| priority | BIGINT | Job priority |
| signature | STRING | Job signature |
| quota_name | STRING | Compute Quota name |
| cpu_usage | BIGINT | Current CPU usage (core*100) |
| mem_usage | BIGINT | Current memory usage (MB) |
| gpu_usage | BIGINT | Current GPU usage (card*100) |
| total_cpu_usage | BIGINT | Cumulative CPU usage (core*100*seconds) |
| total_mem_usage | BIGINT | Cumulative memory usage (MB*seconds) |
| total_gpu_usage | BIGINT | Cumulative GPU usage (card*100*seconds) |
| cpu_min_ratio | BIGINT | CPU ratio for queue guarantee level |
| mem_min_ratio | BIGINT | Memory ratio for queue guarantee level |
| gpu_min_ratio | BIGINT | GPU ratio for queue guarantee level |
| cpu_max_ratio | BIGINT | CPU ratio for highest elastic level |
| mem_max_ratio | BIGINT | Memory ratio for highest elastic level |
| gpu_max_ratio | BIGINT | GPU ratio for highest elastic level |
| settings | STRING | Scheduling or user input (JSON): USERAGENT, BIZID, SKYNET_ID, SKYNET_NODENAME |
| ext_platform_id | STRING | External scheduling platform ID |
| ext_node_id | STRING | External scheduling node ID |
| ext_bizdate | STRING | External scheduling business date |
| ext_task_id | STRING | External scheduling node instance ID |
| ext_dagtype | STRING | External scheduling instance run mode |
| ext_node_name | STRING | External scheduling node name |
| ext_node_onduty | STRING | External scheduling node owner ID |
| ext_node_priority | BIGINT | External scheduling node priority |
| ext_node_cyctype | STRING | External scheduling node cycle type |
| ext_subtask_id | STRING | External scheduling sub-task ID |
| additional_info | STRING | Additional info (reserved field) |

## Historical Views (~5 min delay, 14-day retention)

### TASKS_HISTORY

**MCP:** `execute_sql` + hints

Completed job history, partitioned by `ds` (date string 'YYYYMMDD'), retains ~14 days.

| Column | Type | Description |
|---|---|---|
| task_catalog | STRING | Project name |
| task_name | STRING | Job name |
| task_type | STRING | Job type: SQL, CUPID (Spark/Mars), SQLCost (SQL estimate), SQLRT (accelerated query), LOT (MapReduce), PS (PAI Parameter Server), AlgoTask (ML, no resource/scan info) |
| inst_id | STRING | Instance ID |
| status | STRING | Job status at data collection moment: Terminated (finished), Failed, Cancelled |
| owner_id | STRING | Submitter Aliyun account ID |
| owner_name | STRING | Submitter Aliyun account name |
| result | STRING | Job execution error message |
| priority | BIGINT | Job priority |
| submit_time | DATETIME | Job submit time (Instance creation time) |
| start_time | DATETIME | Job start time (e.g., SQL compile time) |
| end_time | DATETIME | Job end time |
| input_records | BIGINT | Input record count (NULL when SQL hits query acceleration cache) |
| output_records | BIGINT | Output record count (NULL when SQL hits query acceleration cache) |
| input_bytes | BIGINT | Standard storage input in bytes (NULL when SQL hits query acceleration cache) |
| lowfrequency_storage_input_bytes | BIGINT | Low-frequency storage input in bytes (NULL when SQL hits query acceleration cache) |
| longterm_storage_input_bytes | BIGINT | Long-term storage input in bytes (NULL when SQL hits query acceleration cache) |
| oss_input_bytes | BIGINT | OSS external table input in bytes (NULL when SQL hits query acceleration cache) |
| tablestore_input_bytes | BIGINT | Tablestore external table input in bytes (NULL when SQL hits query acceleration cache) |
| output_bytes | BIGINT | Output data volume in bytes (NULL when SQL hits query acceleration cache) |
| input_tables | STRING | Input table list (SQL jobs only, NULL when hits query acceleration cache) |
| output_tables | STRING | Output table list (SQL jobs only, NULL when hits query acceleration cache) |
| operation_text | STRING | Job statement (max 256 KB) |
| signature | STRING | Job signature |
| quota_name | STRING | Compute Quota name |
| complexity | DOUBLE | SQL job complexity |
| cost_cpu | DOUBLE | CPU consumption (100 = 1 core*1s, e.g., 10 cores for 5s = 5000) |
| cost_mem | DOUBLE | Memory consumption (MB*seconds) |
| cost_indicators | STRING | Job resource info for optimization analysis |
| settings | STRING | Scheduling or user input (JSON): USERAGENT, BIZID, SKYNET_ID, SKYNET_NODENAME |
| ext_platform_id | STRING | External scheduling platform ID |
| ext_node_id | STRING | External scheduling node ID |
| ext_bizdate | STRING | External scheduling business date |
| ext_task_id | STRING | External scheduling node instance ID |
| ext_dagtype | STRING | External scheduling instance run mode |
| ext_node_name | STRING | External scheduling node name |
| ext_node_onduty | STRING | External scheduling node owner ID |
| ext_node_priority | BIGINT | External scheduling node priority |
| ext_node_cyctype | STRING | Reserved field, no meaning |
| ext_subtask_id | STRING | External scheduling sub-task ID |
| ds | STRING | Data archive date (partitioned by end_time in UTC+8) |

### TUNNELS_HISTORY

**MCP:** `execute_sql` + hints

Tunnel batch upload/download history, partitioned by `ds`, retains ~14 days.

| Column | Type | Description |
|---|---|---|
| tunnel_catalog | STRING | Resource project name |
| tunnel_schema | STRING | Schema name (currently NULL) |
| session_id | STRING | Session ID |
| operate_type | STRING | Operation type: UPLOADLOG, DOWNLOADLOG, DOWNLOADINSTANCELOG, STORAGEAPIREAD, STORAGEAPIWRITE |
| tunnel_type | STRING | Tunnel type: TUNNEL LOG, TUNNEL INSTANCE LOG |
| request_id | STRING | Request ID |
| object_type | STRING | Object type: TABLE, INSTANCE |
| object_name | STRING | Object name (table name or instance ID) |
| partition_spec | STRING | Partition spec for partitioned table (e.g., time=20130222,loc=beijing) |
| data_size | BIGINT | Data size in bytes |
| block_id | BIGINT | Tunnel upload block number (valid for UPLOADLOG only) |
| offset | BIGINT | Download start offset (record index, 0-based) |
| length | BIGINT | Number of records downloaded/uploaded |
| owner_id | STRING | Operator Aliyun account ID |
| owner_name | STRING | Operator Aliyun account name |
| start_time | DATETIME | Request start time |
| end_time | DATETIME | Request end time |
| client_ip | STRING | Client IP address for Tunnel request |
| user_agent | STRING | User Agent for Tunnel request (e.g., Java version, OS) |
| columns | STRING | Column list for Tunnel download data |
| quota_name | STRING | Tunnel Quota group name |
| app_tag | STRING | Custom label |
| ds | STRING | Data collection date (partitioned by end_time in UTC+8) |
