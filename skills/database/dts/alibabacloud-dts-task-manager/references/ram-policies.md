# RAM Permission Configuration

## Recommended: Use System Policy

Grant the RAM user or role the system policy `AliyunDTSFullAccess` for full DTS operation permissions.

## Least Privilege

For least privilege control, grant the following permissions:

### Core DTS Permissions

- `dts:CreateDtsInstance` — Create a DTS instance
- `dts:ConfigureDtsJob` — Configure a DTS task (source, destination, migration objects, etc.)
- `dts:StartDtsJob` — Start or resume a DTS task
- `dts:SuspendDtsJob` — Suspend a DTS task
- `dts:DeleteDtsJob` — Release (delete) a DTS task
- `dts:DescribeDtsJobs` — Query DTS task list
- `dts:DescribeDtsJobDetail` — Query DTS task details

### Required Permissions by Operation Mode

| Operation Mode | Required Actions |
|---------------|-----------------|
| Create task | dts:CreateDtsInstance, dts:ConfigureDtsJob, dts:StartDtsJob, dts:DeleteDtsJob (for rollback on failure) |
| View task list | dts:DescribeDtsJobs |
| View task status | dts:DescribeDtsJobDetail |
| Stop task | dts:SuspendDtsJob, dts:DescribeDtsJobDetail |
| Start/Resume task | dts:StartDtsJob |
| Release task | dts:DeleteDtsJob, dts:DescribeDtsJobDetail (for pre-check) |

### Additional Permissions for Querying Cloud Instances

When creating tasks, if you need to list RDS/MongoDB/Redis/PolarDB instances for selection, the following read-only permissions are also required:

- `rds:DescribeDBInstances` — Query RDS instance list (MySQL/PostgreSQL/SQL Server/MariaDB)
- `dds:DescribeDBInstances` — Query MongoDB instance list
- `r-kvstore:DescribeInstances` — Query Redis/Tair instance list
- `polardb:DescribeDBClusters` — Query PolarDB cluster list
- `alikafka:GetInstanceList` — Query Kafka instance list

Or directly grant the corresponding product system read-only policies: AliyunRDSReadOnlyAccess, AliyunMongoDBReadOnlyAccess, AliyunKvstoreReadOnlyAccess, AliyunPolardbReadOnlyAccess, AliyunKafkaReadOnlyAccess.
