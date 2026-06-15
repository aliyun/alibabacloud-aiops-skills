# Data Migration Scenarios

## Trigger Conditions

- "How do I import data from MySQL to Lindorm?"
- "How can I migrate HBase cluster data to Lindorm?"
- "What are the steps to synchronize data from Kafka to Lindorm in real time?"
- "Can you help me plan a data migration solution?"

## Core Principles

**⚠️ Safety boundary: read-only + guidance. Direct migration operations are strictly prohibited.**

Migration involves source database connection information such as accounts and passwords. Direct execution may leak sensitive information or cause data loss. The Agent only provides plans and steps, and guides users to operate through the console.

---

## Official Documentation

- LTS, formerly BDS, service introduction: https://help.aliyun.com/zh/lindorm/user-guide/bds-introduction
- MySQL/RDS → Lindorm, DTS: https://help.aliyun.com/zh/dts/user-guide/migrate-data-from-an-apsaradb-rds-for-mysql-instance-to-a-lindorm-instance
- HBase → Lindorm, LTS: https://help.aliyun.com/zh/lindorm/user-guide/synchronize-full-and-incremental-data
- Lindorm data subscription, export to Kafka: https://help.aliyun.com/zh/lindorm/user-guide/real-time-data-subscription/
- Field type mapping: https://help.aliyun.com/zh/lindorm/developer-reference/basic-data-types

---

## Migration Solution Selection

| Source | Recommended Solution | Supports Full + Incremental | Key Limits |
|------|---------|-------------|---------|
| MySQL/RDS | **DTS**, recommended for new users | ✅ | ⚠️ Automatic table schema migration is not supported. Tables must be manually created in Lindorm in advance. |
| HBase 1.x/2.x | **LTS** | ✅ | Data written through Bulkload is not incrementally synchronized. |
| Lindorm → Lindorm | **LTS** | ✅ | Network connectivity must be ensured. |
| Kafka → Lindorm | **LTS streaming channel** | ✅ | — |
| Self-managed or special requirements | Open-source tools, such as Canal, Sqoop, or scripts | Depends on the tool | Lindorm is not fully compatible with MySQL. Some tools may fail because of DDL differences. |

> ⚠️ The original RDS synchronization feature of LTS was discontinued on March 10, 2023. LTS instances purchased after that date no longer support MySQL migration. New users should use DTS.

---

## Solution A: DTS Migration (MySQL/RDS → Lindorm)

### Steps

1. **Go to the DTS console** → https://dts.console.aliyun.com/ → Data Migration → Create Task.
2. **Configure the source and destination databases**: Source database type is MySQL, and destination database type is Lindorm. The wide table engine MySQL-compatible address must be enabled.
3. **Manually create tables in Lindorm in advance**. ⚠️ DTS does not support automatic table schema migration. Handle type conversions such as ENUM→VARCHAR based on the field type mapping.
4. **Precheck**: The system automatically checks source database connectivity, account permissions, and binlog configuration. Incremental migration requires `binlog_format=ROW`.
5. **Start migration**: View progress and data volume in real time in the console.
6. **Verify data**: Run `SELECT COUNT(*) FROM your_table;` in Lindorm and compare it with the source database.

### Notes

- Do not modify the source table schema during full migration.
- Incremental synchronization requires binlog to be enabled on the MySQL side, with `binlog_format=ROW`.
- It is recommended to execute migration during off-peak hours.

---

## Solution B: LTS Migration (HBase → Lindorm)

### Steps

1. **Enable LTS service**: Lindorm console → target instance → Data Ecosystem Service → Enable LTS.
2. **Create a migration task**: LTS operation page → Import Lindorm/HBase → One-click Migration → Create Task.
3. **Configure source and destination**: Source is the HBase cluster, which must have network connectivity with LTS. Destination is the Lindorm wide table engine. Select ☑️ table schema migration + ☑️ historical data migration + ☑️ real-time data replication.
4. **Monitor and verify**: View migration progress in real time, perform LTS data sampling verification, and switch traffic after business verification.

### Notes

- Make sure network connectivity among LTS, the source HBase cluster, and the destination Lindorm instance is established.
- Incremental synchronization is based on HBase WAL. Data written through Bulkload is not synchronized.
- Confirm that the destination instance has sufficient storage space before migration.

---

## Solution C: Open-source Tool Migration

### C-1: Canal (MySQL → Lindorm Real-time Synchronization)

Parse MySQL binlog and synchronize data to Lindorm in real time.

1. Deploy Canal Server.
2. Configure Canal to listen to MySQL binlog.
3. Use Canal Adapter to write data to Lindorm.

Reference: https://github.com/alibaba/canal

### C-2: Sqoop (Hadoop → Lindorm Batch Import)

> ⚠️ The Lindorm wide table engine is MySQL-compatible but not fully compatible with MySQL. Sqoop may fail because of DDL differences.

```bash
# Select the connection address based on the instance ServiceType. See sql-client-guide.md → "Connection domain name format".
# The V1/V2 MySQL protocol port is 33060.
sqoop export \
  --connect jdbc:mysql://<connection_address>:<port>/default \
  --table my_table \
  --export-dir /user/hive/warehouse/my_table \
  --input-fields-terminated-by '\t'
```

### C-3: Custom Script

Applicable to small data volumes or special transformation requirements. Example:

1. Export data from the source database, such as mysqldump or HBase Export.
2. Clean and transform data formats.
3. Use the Lindorm SDK or MySQL protocol to write data in batches.

Python example (MySQL → Lindorm):

```python
import pymysql

# 1. Read MySQL data.
mysql_conn = pymysql.connect(host='...', user='...', password='...', database='source_db')
cursor = mysql_conn.cursor()
cursor.execute("SELECT * FROM source_table")

# 2. Write to Lindorm through the MySQL protocol.
# Select the connection address based on the instance ServiceType. See sql-client-guide.md.
# The V1/V2 MySQL protocol port is 33060. For domain name format, see sql-client-guide.md.
lindorm_conn = pymysql.connect(
    host='<connection_address>',
    port=<port>,
    user='root',
    password='your-password',
    database='default'
)
lindorm_cursor = lindorm_conn.cursor()

for row in cursor:
    placeholders = ','.join(['%s'] * len(row))
    lindorm_cursor.execute(f"INSERT INTO target_table VALUES ({placeholders})", row)
lindorm_conn.commit()
```

---

## FAQ

| Question | Cause | Solution |
|------|------|---------|
| Connectivity check failed | Network is unreachable or whitelist is not configured | Confirm that the source and destination are in the same VPC or public access is configured. Add the source database IP to the Lindorm whitelist. |
| Table schema is incompatible | MySQL type has no corresponding Lindorm type | Convert ENUM to VARCHAR. Split TEXT/BLOB values larger than 2 MB. A primary key is required. |
| Incremental synchronization is disconnected | MySQL binlog was cleaned up | Increase binlog retention time and reconfigure the DTS task. |
| Destination storage is insufficient | Data volume exceeds expectations | Confirm Lindorm storage space before migration. It is recommended to reserve 20 GB or more. |

---

## Related Scenarios

- Performance comparison after migration → `monitoring-guide.md`
- Verify data consistency → Query write metrics in `monitoring-guide.md`
- Migration task monitoring → View in the LTS console in real time. No API support is currently available.