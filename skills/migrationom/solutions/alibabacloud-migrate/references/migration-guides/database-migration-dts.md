# Database Migration with DTS (Data Transmission Service)

## Overview

Alibaba Cloud Data Transmission Service (DTS) provides comprehensive database migration capabilities supporting:

- **Schema Migration** — Automatically migrate database schemas (tables, indexes, constraints, views, stored procedures)
- **Full Data Migration** — Migrate existing data from source to destination
- **Incremental Data Synchronization** — Capture and replicate ongoing changes during migration for minimal downtime

DTS supports homogeneous migrations (same database engine) and heterogeneous migrations (different engines) with automatic type mapping.

## Supported Scenarios

| Source | Destination | Supported Migration Types |
|--------|-------------|--------------------------|
| Amazon RDS MySQL | ApsaraDB RDS MySQL | Schema + Full + Incremental |
| Amazon RDS PostgreSQL | ApsaraDB RDS PostgreSQL | Schema + Full + Incremental |
| Amazon RDS SQL Server | ApsaraDB RDS SQL Server | Schema + Full + Incremental |
| Amazon Aurora MySQL | ApsaraDB RDS MySQL | Schema + Full + Incremental |
| Amazon RDS MySQL | ApsaraDB RDS PostgreSQL | Schema + Full + Incremental (heterogeneous) |
| Self-managed MySQL on EC2 | ApsaraDB RDS MySQL | Schema + Full + Incremental |
| Self-managed PostgreSQL on EC2 | ApsaraDB RDS PostgreSQL | Schema + Full + Incremental |

## Prerequisites

### Source Database (Amazon RDS)

- **Publicly Accessible**: Set to `Yes` in RDS configuration
- **Security Group**: Allow inbound connections from DTS server IP ranges
- **Database User**: Create a dedicated migration user with sufficient privileges:
  ```sql
  -- MySQL
  CREATE USER 'dts_user'@'%' IDENTIFIED BY 'password';
  GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'dts_user'@'%';
  FLUSH PRIVILEGES;
  
  -- PostgreSQL
  CREATE USER dts_user WITH PASSWORD 'password';
  GRANT rds_superuser TO dts_user;
  ```
- **Binary Logging**: Enable for MySQL (required for incremental sync)
  ```sql
  -- Check binary log status
  SHOW VARIABLES LIKE 'log_bin';
  -- Should return: ON
  ```

### Destination Database (ApsaraDB RDS)

- **Instance Created**: Provision ApsaraDB RDS instance with sufficient storage
- **Version Compatibility**: Destination version >= source version recommended
- **Whitelist Configuration**: Add DTS server IP ranges to RDS whitelist
- **Storage**: Ensure destination has at least 1.5x source database size

### Network Requirements

- **DTS IP Ranges**: Whitelist Alibaba Cloud DTS server IP ranges in source security group
  - Check current DTS IP ranges in DTS console or documentation
  - IP ranges vary by region
- **Connectivity Test**: Verify network connectivity before starting migration

## Step 1: Purchase DTS Instance

Create a DTS migration job instance:

```bash
aliyun dts CreateMigrationJob \
  --RegionId <region-id> \
  --MigrationJobClass medium \
  --MigrationJobName "aws-rds-to-alicloud-migration" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `RegionId` | Yes | Region where DTS instance will be created | `cn-hangzhou`, `ap-southeast-1` |
| `MigrationJobClass` | Yes | Instance specification (micro, small, medium, large, xlarge) | `medium` |
| `MigrationJobName` | No | Descriptive name for the migration job | `aws-rds-to-alicloud-migration` |

**Response:**
```json
{
  "MigrationJobId": "dts-xxxxxxxxxxxxx",
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

**Save the `MigrationJobId`** — required for subsequent steps.

### 1.1 Terraform Alternative for RDS Instance

```hcl
resource "alicloud_db_instance" "migration" {
  engine                   = "<engine>"
  engine_version           = "<version>"
  instance_type            = "<instance-class>"
  instance_storage         = <storage-gb>
  instance_charge_type     = "Postpaid"
  instance_name            = "<instance-name>"
  vswitch_id               = "<vswitch-id>"
  security_group_ids       = ["<security-group-id>"]
  db_instance_storage_type = "cloud_essd"
}
```

**Note:** Use Terraform for RDS instance creation. DTS migration operations (`CreateMigrationJob`, `ConfigureMigrationJob`, `StartMigrationJob`) have no Terraform equivalent and must use CLI.

## Step 2: Configure Migration Task

Configure source and destination endpoints, migration objects, and migration types:

```bash
aliyun dts ConfigureMigrationJob \
  --MigrationJobId <migration-job-id> \
  --MigrationJobName "aws-rds-to-alicloud" \
  --SourceEndpoint.InstanceType other \
  --SourceEndpoint.EngineName MySQL \
  --SourceEndpoint.IP <aws-rds-endpoint> \
  --SourceEndpoint.Port 3306 \
  --SourceEndpoint.UserName <username> \
  --SourceEndpoint.Password <password> \
  --SourceEndpoint.DatabaseName <database-name> \
  --DestinationEndpoint.InstanceType RDS \
  --DestinationEndpoint.InstanceID <rds-instance-id> \
  --DestinationEndpoint.EngineName MySQL \
  --MigrationMode.StructureIntialization true \
  --MigrationMode.DataIntialization true \
  --MigrationMode.DataSynchronization true \
  --MigrationObject '[{"DBName":"mydb","SchemaName":"mydb","TableIncludes":[{"TableName":"*"}]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `MigrationJobId` | Yes | DTS job ID from Step 1 | `dts-xxxxxxxxxxxxx` |
| `SourceEndpoint.InstanceType` | Yes | Source type (`other` for external databases) | `other` |
| `SourceEndpoint.EngineName` | Yes | Source database engine | `MySQL`, `PostgreSQL`, `SQLServer` |
| `SourceEndpoint.IP` | Yes | Source RDS endpoint | `mydb.xxxxxx.us-east-1.rds.amazonaws.com` |
| `SourceEndpoint.Port` | Yes | Source database port | `3306` (MySQL), `5432` (PostgreSQL) |
| `SourceEndpoint.UserName` | Yes | Migration user | `dts_user` |
| `SourceEndpoint.Password` | Yes | Migration user password | `<password>` |
| `DestinationEndpoint.InstanceType` | Yes | Destination type (`RDS` for ApsaraDB) | `RDS` |
| `DestinationEndpoint.InstanceID` | Yes | Destination RDS instance ID | `rm-xxxxxxxxxxxxx` |
| `DestinationEndpoint.EngineName` | Yes | Destination database engine | `MySQL`, `PostgreSQL` |
| `MigrationMode.StructureIntialization` | Yes | Enable schema migration | `true` or `false` |
| `MigrationMode.DataIntialization` | Yes | Enable full data migration | `true` or `false` |
| `MigrationMode.DataSynchronization` | Yes | Enable incremental sync | `true` or `false` |
| `MigrationObject` | Yes | JSON array of migration objects | See below |

**MigrationObject Format:**

```json
[
  {
    "DBName": "mydb",
    "SchemaName": "mydb",
    "TableIncludes": [
      {"TableName": "*"}
    ]
  }
]
```

**Selective Table Migration:**
```json
[
  {
    "DBName": "mydb",
    "SchemaName": "mydb",
    "TableIncludes": [
      {"TableName": "users"},
      {"TableName": "orders"},
      {"TableName": "products"}
    ]
  }
]
```

## Step 3: Start Migration

After configuration passes pre-check, start the migration job:

```bash
aliyun dts StartMigrationJob \
  --MigrationJobId <migration-job-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Pre-check Items:**
- Source database connectivity
- Destination database connectivity
- Source database permissions
- Destination database permissions
- Binary log status (for incremental sync)
- Storage space on destination

**If pre-check fails:**
- Review error details in DTS console
- Fix issues (permissions, network, etc.)
- Re-run pre-check before starting

## Step 4: Monitor Progress

Monitor migration job status and progress:

```bash
aliyun dts DescribeMigrationJobStatus \
  --MigrationJobId <migration-job-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response:**
```json
{
  "MigrationJobStatus": {
    "MigrationJobId": "dts-xxxxxxxxxxxxx",
    "Status": "Synchronizing",
    "MigrationJobName": "aws-rds-to-alicloud",
    "Progress": {
      "StructureIntialization": {
        "Status": "Finished",
        "Progress": "100%"
      },
      "DataIntialization": {
        "Status": "Finished",
        "Progress": "100%"
      },
      "DataSynchronization": {
        "Status": "Synchronizing",
        "Progress": "95%",
        "Delay": "2"
      }
    },
    "CreateTime": "2024-01-15T10:30:00Z"
  }
}
```

**Status Values:**
- `NotStarted` — Job created but not started
- `Prechecking` — Running pre-checks
- `Failed` — Pre-check or migration failed
- `Initializing` — Performing initial full data sync
- `Synchronizing` — Incremental sync in progress
- `Suspending` — Job paused
- `Finished` — Migration completed

**Monitor Delay:**
- `Delay` field shows replication lag in seconds
- Wait for delay to stabilize at low values (< 10 seconds) before cutover

## Step 5: Cutover

### 5.1 Stop Application Writes

- Put application in maintenance mode
- Stop all write operations to source database
- Wait for DTS to catch up (delay = 0)

### 5.2 Verify Data Consistency

```bash
# Check row counts on source and destination
# Source (MySQL)
mysql -h <aws-rds-endpoint> -u <user> -p -e "SELECT COUNT(*) FROM mydb.users;"

# Destination (ApsaraDB RDS)
mysql -h <rds-endpoint> -u <user> -p -e "SELECT COUNT(*) FROM mydb.users;"
```

### 5.3 Stop DTS Job

```bash
aliyun dts StopMigrationJob \
  --MigrationJobId <migration-job-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 5.4 Update Application Configuration

- Update database connection strings to point to ApsaraDB RDS endpoint
- Update environment variables or configuration files
- Restart application services

### 5.5 Verify Application Functionality

- Test read operations
- Test write operations
- Verify data integrity in production

## Error Handling

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Security group blocking DTS IP | Add DTS IP ranges to source security group |
| `Access denied for user` | Insufficient permissions | Grant required permissions to migration user |
| `Binary log not enabled` | MySQL binary logging disabled | Enable binary log in RDS parameter group |
| `Schema conflict` | Table already exists on destination | Choose "Ignore Errors" or clean destination schema |
| `Data type mismatch` | Incompatible data types between engines | Review type mapping, adjust schema if needed |
| `Network timeout` | Network latency or firewall | Check network connectivity, increase timeout |
| `Insufficient storage` | Destination storage full | Expand RDS storage capacity |

### View Error Details

```bash
aliyun dts DescribeMigrationJobStatus \
  --MigrationJobId <migration-job-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

Check `ErrorMessage` and `ErrorDetails` fields in response.

### Retry Failed Jobs

```bash
# Resume migration after fixing issues
aliyun dts StartMigrationJob \
  --MigrationJobId <migration-job-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

## DTS Reverse Sync (Database Rollback)

DTS supports **bidirectional synchronization** — if issues are discovered after cutover, you can create a reverse sync task (Alibaba Cloud → AWS) to stream changes back to the source database and revert traffic.

### When to Use

- Post-cutover issues detected (data corruption, application incompatibility)
- Need to fall back to AWS RDS while keeping data written to ApsaraDB in sync
- Parallel-run validation: run both databases simultaneously and compare results

### Step 1: Create Reverse Sync Task

```bash
aliyun dts CreateMigrationJob \
  --RegionId <region-id> \
  --MigrationJobClass medium \
  --MigrationJobName "alicloud-to-aws-reverse-sync" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 2: Configure Reverse Direction

Swap source and destination — ApsaraDB RDS becomes source, AWS RDS becomes destination:

```bash
aliyun dts ConfigureMigrationJob \
  --MigrationJobId <reverse-job-id> \
  --MigrationJobName "alicloud-to-aws-reverse-sync" \
  --SourceEndpoint.InstanceType RDS \
  --SourceEndpoint.InstanceID <alicloud-rds-instance-id> \
  --SourceEndpoint.EngineName MySQL \
  --DestinationEndpoint.InstanceType other \
  --DestinationEndpoint.EngineName MySQL \
  --DestinationEndpoint.IP <aws-rds-endpoint> \
  --DestinationEndpoint.Port 3306 \
  --DestinationEndpoint.UserName <username> \
  --DestinationEndpoint.Password <password> \
  --DestinationEndpoint.DatabaseName <database-name> \
  --MigrationMode.StructureIntialization false \
  --MigrationMode.DataIntialization false \
  --MigrationMode.DataSynchronization true \
  --MigrationObject '[{"DBName":"mydb","SchemaName":"mydb","TableIncludes":[{"TableName":"*"}]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Note:** Schema and full data initialization are set to `false` — the source schema already exists on AWS. Only incremental sync is needed.

### Step 3: Start Reverse Sync and Monitor

```bash
aliyun dts StartMigrationJob \
  --MigrationJobId <reverse-job-id> \
  --user-agent AlibabaCloud-Agent-Skills

# Monitor until Delay stabilizes at 0
aliyun dts DescribeMigrationJobStatus \
  --MigrationJobId <reverse-job-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 4: Execute Rollback

Once reverse sync is caught up (`Delay: 0`):

1. Switch application traffic back to AWS RDS (DNS rollback)
2. Verify application works correctly with AWS RDS
3. Stop the reverse sync job
4. Stop the forward sync job (if still running)

### Prerequisites for Reverse Sync

| Requirement | Details |
|-------------|---------|
| ApsaraDB RDS binary logging | Must be enabled (default for most versions) |
| AWS RDS network access | ApsaraDB must be able to reach AWS RDS (public endpoint or VPN) |
| AWS RDS user permissions | Same as forward migration: `SELECT, REPLICATION SLAVE, REPLICATION CLIENT` |
| AWS RDS security group | Allow inbound from DTS IP ranges |

### Limitations

- Reverse sync adds extra cost (additional DTS instance)
- DDL changes during reverse sync may cause conflicts
- Schema changes on either side after initial migration require manual resolution
- Reverse sync only captures changes made **after** the reverse task starts — not retroactive

## Cleanup

### Delete DTS Migration Job

```bash
aliyun dts DeleteMigrationJob \
  --MigrationJobId <migration-job-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Delete DTS Instance (if no longer needed)

```bash
aliyun dts DeleteMigrationJob \
  --MigrationJobId <migration-job-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Remove Source Database Access

- Revoke DTS user permissions on source RDS
- Remove DTS IP ranges from security group
- Delete migration user if no longer needed

```sql
-- MySQL
REVOKE ALL PRIVILEGES ON *.* FROM 'dts_user'@'%';
DROP USER 'dts_user'@'%';
FLUSH PRIVILEGES;

-- PostgreSQL
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM dts_user;
DROP USER dts_user;
```

### Decommission Source RDS (Optional)

- Create final snapshot before deletion
- Delete RDS instance after successful migration verification
- Release Elastic IP if associated

## Best Practices

1. **Test Migration First**
   - Run a test migration with a subset of data
   - Validate schema, data, and application compatibility
   - Estimate migration duration

2. **Schedule Maintenance Window**
   - Plan cutover during low-traffic periods
   - Communicate downtime expectations to stakeholders
   - Prepare rollback plan

3. **Monitor Continuously**
   - Set up CloudWatch alarms for DTS metrics
   - Monitor replication lag during incremental sync
   - Track migration progress regularly

4. **Optimize Performance**
   - Choose appropriate DTS instance class based on data volume
   - Use multiple migration jobs for large databases (split by schema)
   - Enable compression for network transfer

5. **Data Validation**
   - Use DTS built-in data validation feature
   - Compare row counts and checksums post-migration
   - Run application-level validation tests

6. **Incremental Sync Strategy**
   - Start incremental sync days before cutover
   - Monitor and reduce replication lag over time
   - Plan cutover when lag is consistently minimal

## Related APIs

| API Action | Description | CLI Command |
|------------|-------------|-------------|
| `CreateMigrationJob` | Create DTS migration job | `aliyun dts CreateMigrationJob ... --user-agent AlibabaCloud-Agent-Skills` |
| `ConfigureMigrationJob` | Configure migration job | `aliyun dts ConfigureMigrationJob ... --user-agent AlibabaCloud-Agent-Skills` |
| `StartMigrationJob` | Start migration job | `aliyun dts StartMigrationJob ... --user-agent AlibabaCloud-Agent-Skills` |
| `StopMigrationJob` | Stop migration job | `aliyun dts StopMigrationJob ... --user-agent AlibabaCloud-Agent-Skills` |
| `DescribeMigrationJobStatus` | Get migration job status | `aliyun dts DescribeMigrationJobStatus ... --user-agent AlibabaCloud-Agent-Skills` |
| `DeleteMigrationJob` | Delete migration job | `aliyun dts DeleteMigrationJob ... --user-agent AlibabaCloud-Agent-Skills` |

## References

- [DTS Product Documentation](https://www.alibabacloud.com/help/en/dts)
- [DTS API Reference](https://www.alibabacloud.com/help/en/dts/api-reference)
- [Database Migration Best Practices](https://www.alibabacloud.com/help/en/dts/user-guide/migration-best-practices)
- [Supported Databases](https://www.alibabacloud.com/help/en/dts/user-guide/supported-databases)
