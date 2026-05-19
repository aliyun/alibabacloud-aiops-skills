# Entities Reference

> Related: [views-reference.md](views-reference.md), [terminology.md](terminology.md), [SKILL.md](../SKILL.md)

Entity-to-table mappings for INFORMATION_SCHEMA views. All queries use `SYSTEM_CATALOG.INFORMATION_SCHEMA.*`.

## Entity-Table Mapping

| Entity ID | Entity Name | Source Table | Primary Key | Time Field | Purpose | MCP Tool |
|---|---|---|---|---|---|---|
| entity_table_asset | Table Asset | TABLES | table_name | last_modified_time | Table-level metadata, storage, lifecycle | `list_tables` + `get_table_schema` |
| entity_column | Column | COLUMNS | column_name | — | Column definitions, types, comments | `get_table_schema` |
| entity_partition | Table Partition | PARTITIONS | partition_name | create_time | Partition details, sizes, counts | `get_partition_info` |
| entity_privilege | Privilege Grant | TABLE_PRIVILEGES | user_id | — | Table-level grants | `execute_sql` + hints |
| entity_column_privilege | Column Privilege | COLUMN_PRIVILEGES | — | — | Column-level grants | `execute_sql` + hints |
| entity_task | Compute Task | TASKS_HISTORY | inst_id | start_time | Historical query analysis | `execute_sql` + hints |
| entity_running_task | Running Task | TASKS | inst_id | start_time | Live running job monitoring | `execute_sql` + hints |
| entity_catalog | Project (Catalog) | CATALOGS | catalog_name | create_time | Project-level info and properties | `get_project` |
| entity_catalog_privilege | Project Privilege | CATALOG_PRIVILEGES | — | — | Project-level permissions | `execute_sql` + hints |
| entity_schema | Schema | SCHEMAS | schema_name | — | Schema metadata | `list_schemas` |
| entity_user | User | USERS | user_id | — | Project users | `execute_sql` + hints |
| entity_role | Role | ROLES | role_name | — | Project roles | `execute_sql` + hints |
| entity_user_role | User Role | USER_ROLES | — | — | User-role assignments | `execute_sql` + hints |
| entity_udf | UDF | UDFS | udf_name | — | User-defined functions | `execute_sql` + hints |
| entity_udf_privilege | UDF Privilege | UDF_PRIVILEGES | — | — | UDF permissions | `execute_sql` + hints |
| entity_udf_resource | UDF Resource | UDF_RESOURCES | — | — | Resources used by UDFs | `execute_sql` + hints |
| entity_resource | Resource | RESOURCES | resource_name | — | Uploaded resources | `execute_sql` + hints |
| entity_resource_privilege | Resource Privilege | RESOURCE_PRIVILEGES | — | — | Resource permissions | `execute_sql` + hints |
| entity_tunnel_history | Tunnel History | TUNNELS_HISTORY | session_id | ds | Data transfer audit trail | `execute_sql` + hints |
| entity_quota_usage | Quota Usage | QUOTA_USAGE | name | last_modified_time | Resource quota monitoring | `execute_sql` + hints |
| entity_volume | Volume Storage | VOLUMES | volume_name | — | Volume filesystem metadata | `execute_sql` + hints |
| entity_foreign_server | Foreign Server | FOREIGN_SERVERS | server_name | — | External data source definitions | `execute_sql` + hints |
| entity_installed_package | Installed Package | INSTALLED_PACKAGES | package_name | — | Installed packages | `execute_sql` + hints |
| entity_package_privilege | Package Privilege | PACKAGE_PRIVILEGES | — | — | Package permissions | `execute_sql` + hints |
| entity_package_object | Package Object | PACKAGE_OBJECTS | — | — | Objects within packages | `execute_sql` + hints |
| entity_table_access_info | Table Access Info | TABLE_ACCESS_INFO | — | ds | Table access patterns and statistics | `execute_sql` + hints |
| entity_table_label | Table Security Label | TABLE_LABELS | — | — | Table-level LABEL security | `execute_sql` + hints |
| entity_table_label_grant | Table Label Grant | TABLE_LABEL_GRANTS | — | — | Table label grants | `execute_sql` + hints |
| entity_column_label | Column Security Label | COLUMN_LABELS | — | — | Column-level LABEL security | `execute_sql` + hints |
| entity_column_label_grant | Column Label Grant | COLUMN_LABEL_GRANTS | — | — | Column label grants | `execute_sql` + hints |
| entity_partition_access_info | Partition Access Info | PARTITION_ACCESS_INFO | — | ds | Partition access patterns | `execute_sql` + hints |
