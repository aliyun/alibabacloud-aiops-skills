# Entity ID Format Reference

All DataWorks Data Map entities use structured IDs with the format:
`${EntityType}:${InstanceId}:${CatalogId}:${DatabaseName}:${SchemaName}:${TableName}`

For levels that don't exist, use empty string as placeholder.

## MaxCompute

| Entity Level | ID Format | Example |
|---|---|---|
| Project (database) | `maxcompute-project:::project_name` | `maxcompute-project:::my_project` |
| Schema | `maxcompute-schema:::project_name:schema_name` | `maxcompute-schema:::my_project:default` |
| Table (no schema) | `maxcompute-table:::project_name::table_name` | `maxcompute-table:::my_project::my_table` |
| Table (with schema) | `maxcompute-table:::project_name:schema_name:table_name` | `maxcompute-table:::my_project:default:my_table` |
| Column | `maxcompute-column:::project_name::table_name:column_name` | `maxcompute-column:::my_project::my_table:id` |

> **Note**: For MaxCompute, `InstanceId` and `CatalogId` are empty (use empty string placeholder).
> `DatabaseName` = MaxCompute project name. Schema is only needed when the project has enabled the three-level model.

## DLF (Data Lake Formation)

| Entity Level | ID Format | Example |
|---|---|---|
| Catalog | `dlf-catalog::catalog_id` | `dlf-catalog::my_catalog` |
| Database | `dlf-database::catalog_id:database_name` | `dlf-database::my_catalog:my_db` |
| Table | `dlf-table::catalog_id:database_name::table_name` | `dlf-table::my_catalog:my_db::my_table` |
| Column | `dlf-column::catalog_id:database_name::table_name:column_name` | `dlf-column::my_catalog:my_db::my_table:id` |

## Hologres

| Entity Level | ID Format | Example |
|---|---|---|
| Database | `holo-database:instance_id::database_name` | `holo-database:hgprecn-xxx::my_db` |
| Schema | `holo-schema:instance_id::database_name:schema_name` | `holo-schema:hgprecn-xxx::my_db:public` |
| Table | `holo-table:instance_id::database_name:schema_name:table_name` | `holo-table:hgprecn-xxx::my_db:public:my_table` |

## MySQL

| Entity Level | ID Format | Example |
|---|---|---|
| Database | `mysql-database:(instance_id|encoded_jdbc_url)::database_name` | `mysql-database:rm-xxx::my_db` |
| Table | `mysql-table:(instance_id|encoded_jdbc_url)::database_name::table_name` | `mysql-table:rm-xxx::my_db::my_table` |

## HMS (Hive Metastore / EMR)

| Entity Level | ID Format | Example |
|---|---|---|
| Database | `hms-database:instance_id::database_name` | `hms-database:c-xxx::my_db` |
| Table | `hms-table:instance_id::database_name::table_name` | `hms-table:c-xxx::my_db::my_table` |

## StarRocks

| Entity Level | ID Format | Example |
|---|---|---|
| Catalog | `starrocks-catalog:(instance_id|encoded_jdbc_url):catalog_name` | `starrocks-catalog:sr-xxx:default_catalog` |
| Database | `starrocks-database:(instance_id|encoded_jdbc_url):catalog_name:database_name` | `starrocks-database:sr-xxx:default_catalog:my_db` |
| Table | `starrocks-table:(instance_id|encoded_jdbc_url):catalog_name:database_name::table_name` | `starrocks-table:sr-xxx:default_catalog:my_db::my_table` |

## Quick Lookup: User Input → Entity ID

When a user provides a table name like `project_name.table_name`:

1. **MaxCompute**: Try `maxcompute-table:::project_name::table_name` first, then `maxcompute-table:::project_name:default:table_name` (if three-level model enabled)
2. **DLF**: Need `catalog_id` — use `list-catalogs` to find it first
3. **Hologres/MySQL/HMS**: Need `instance_id` — ask the user or look up from DataWorks workspace bindings
