# Azure Database Services -> Alibaba Cloud Mapping

## Azure SQL Server / SQL Database -> ApsaraDB RDS SQL Server

| Azure Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|----------------|------------------------|----------------------|-------|
| `azurerm_mssql_server` | `alicloud_db_instance` | Medium | Preserve SQL Server engine family |
| `azurerm_mssql_database` | `alicloud_db_database` | Medium | Create the SQL Server database on the mapped RDS instance |

### Mapping Semantics

`azurerm_mssql_server` is an Azure SQL logical server, not a VM-hosted SQL Server machine. The closest Alibaba Cloud Terraform target is an ApsaraDB RDS SQL Server instance: `alicloud_db_instance` with `engine = "SQLServer"`.

`azurerm_mssql_database` is a database under that logical server. Map it to `alicloud_db_database` attached to the mapped SQL Server RDS instance. Use `data_base_name` for the database name; `name` is deprecated in the Alibaba Cloud provider.

Azure SQL `version = "12.0"` is a logical Azure SQL Database version. Do not treat it as SQL Server 2012 or SQL Server 2019. Select the closest supported Alibaba Cloud RDS SQL Server engine version and record the compatibility difference in the assessment report and migration guide.

### Required Target Properties and Forbidden Mappings

When Phase 2 maps Azure MSSQL resources, keep the database engine family. Do not infer MySQL/PostgreSQL from generic RDS examples.

| Source Pattern | Target Resource | Required `target_resources[].properties` | Forbidden |
|----------------|----------------|-------------------------------------------|-----------|
| `azurerm_mssql_server` | `alicloud_db_instance` | `engine = "SQLServer"`, `engine_version`, instance class/storage properties, `vswitch_id`, security settings, admin account variable references when required | `engine = "MySQL"`, `engine = "PostgreSQL"` |
| `azurerm_mssql_database` | `alicloud_db_database` | `instance_id` referencing the SQL Server `alicloud_db_instance`, `data_base_name`, charset/collation notes when applicable | MySQL-only database assumptions, deprecated `name` argument |

If the exact Azure SQL version cannot be represented one-to-one, choose the closest supported SQL Server engine version and record the version difference in the assessment report and migration guide. Never silently change SQL Server to MySQL or PostgreSQL.
