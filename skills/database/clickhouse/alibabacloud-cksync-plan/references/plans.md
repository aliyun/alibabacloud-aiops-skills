# Migration Plans - Detailed Conditions

## Method Selection Priority

> **Quick Reference for Common Scenarios:**
> 
> | Scenario | Recommended Method | Notes |
> |----------|-------------------|-------|
> | In-place AZ switch | Console (cksync) | Even if BACKUP/RESTORE is possible (v≥22.8), cksync is preferred |
> | In-place horizontal scaling | Console (cksync) | Native console support, automatic endpoint handling |
> | In-place disk downgrade | Console (cksync) | Simpler than manual alternatives |
> | Community → Enterprise | Console (cksync) | BACKUP/RESTORE NOT supported (different engines) |
> | Community → Community | Console (cksync) or BACKUP/RESTORE | BACKUP/RESTORE requires v≥22.8 |
> | Enterprise → Enterprise | INSERT FROM REMOTE or BACKUP/RESTORE | cksync does NOT support E2E |
> | Zero downtime required | Double-Write | Business must support dual writes |

## 1. Console (cksync) Migration

### 1.1 Migration Type Conditions
**Supported (choose one):**
- (Cross-cluster) Alibaba Cloud ClickHouse Community → Enterprise
- (Cross-cluster) Alibaba Cloud ClickHouse Community → Community
- (Cross-cluster) Self-built/non-Alibaba Cloud → Alibaba Cloud Community
- (Cross-cluster) Self-built/non-Alibaba Cloud → Alibaba Cloud Enterprise
- (In-place) Alibaba Cloud Community: horizontal scaling, disk downgrade, **AZ switch**, multi-replica upgrade

**NOT Supported:**
- ❌ Alibaba Cloud Enterprise → Enterprise (use INSERT FROM REMOTE)

> **Why cksync for In-place Migrations?**
> 
> For in-place operations like AZ switch, horizontal scaling, or disk downgrade, always prefer Console (cksync) over BACKUP/RESTORE because:
> 1. Native Alibaba Cloud Console integration with built-in support
> 2. Automatic connection string handling (no manual endpoint updates)
> 3. Real-time progress monitoring and error handling
> 4. No OSS setup or manual data transfer required
> 5. Official Alibaba Cloud recommended approach

### 1.2 Business Impact Conditions
Must satisfy one of:
- Business allows read-only for 10+ minutes (cksync reaches 100%, then switch)
- Business allows partial data loss (switch at ~99%, accept some missing data)

Must satisfy all:
- No DDL changes during migration (no CREATE/DROP/ALTER on tables)
- Note: DELETE operations during migration may cause data count mismatch

### 1.3 Business Cooperation
For cross-cluster migrations:
- Business must modify connection strings
- If version changes, verify SQL compatibility

For in-place migrations:
- Connection string remains unchanged
- If using direct node IPs, must update IPs (node IPs change in background)

### 1.4 Database Engine Support
| Engine | Supported |
|--------|-----------|
| Ordinary | Yes |
| Atomic | Yes |
| Replicated | Yes |
| MySQL | Yes |
| PostgreSQL | Yes |
| SQLite | Yes |
| MaterializedPostgreSQL | Yes |
| MaterializedMySQL | No (use DTS) |
| MaterializeMySQL | No (use DTS) |

### 1.5 Table Engine Support
**MergeTree family:**
- TTL deletion: Check `engine_full` field for TTL clause (e.g., `TTL event_time + INTERVAL 7 DAY`)
  - If `engine_full` contains no TTL clause → No TTL deletion (data permanently retained) ✅
  - If TTL ≥3 days → Supported ✅
  - If TTL <3 days → ⚠️ **Warning**: Data count in new cluster may be **larger** than source cluster. This is because source cluster's TTL merge continues deleting data during sync, while new cluster stops all merges until sync completes.
- Partition count per table should be <10,000
- Write speed must not exceed migration speed (see speed reference below)

**View / MaterializedView:**
- ✅ Supported - cksync automatically migrates View and MaterializedView definitions

**External tables (MySQL, PostgreSQL, Redis, MaxCompute, OSS):**
- ✅ Supported - Must ensure network connectivity from target cluster to external data source

**Kafka/RabbitMQ tables:**
- NOT supported (migrate manually)

**Log family tables:**
- **Community → Community**: Supported for schema migration; tables with no data (`size_of_one_shard = 0`) can be migrated directly
- **Community → Enterprise**: NOT supported (Enterprise Edition doesn't support Log engine)
- **Self-built → Community**: Supported for schema migration; tables with no data can be migrated directly
- **Self-built → Enterprise**: NOT supported (Enterprise Edition doesn't support Log engine)
- If Log tables contain data, use INSERT FROM REMOTE for data migration after cksync completes schema sync

### 1.6 Table-Level Migration
- New cluster is Community: NOT supported
- New cluster is Enterprise: Supported

### 1.7 Version Requirements
- Source: All versions
- Target ≥20.8: Supports incremental migration
- Target <20.8: Full migration only

### 1.8 Migration Speed Reference
| Avg Part Size | Source Spec | Source Disk | Target Spec | Target Storage | Nodes | Per-Node Speed | Total Speed |
|--------------|-------------|-------------|-------------|----------------|-------|----------------|-------------|
| 402.54MB | 8C32G | PL1 | 16CCU | OSS | 16 | 47MB/s | 752MB/s |
| 402.54MB | 80C384G | PL3 | 48CCU | ESSD_L2 | 8 | 198MB/s | 1582MB/s |

**Formula:** Migration time = Data size / (Migration speed - Write speed)

### 1.9 High Write Speed Handling

**Critical Rule**: When total business write speed exceeds **20 MB/s** or source cluster shows high CPU/memory utilization, you MUST consider upgrading source and target cluster specs to increase sync speed:

**Recommended Specifications for High-Speed Migration:**

| Cluster Type | Recommended Spec | Disk/Storage |
|--------------|------------------|---------------|
| Community Edition | ≥80C kernel | PL2 or PL3 performance disk |
| Enterprise Edition | ≥32 CCU per node | OSS or high-performance object storage (both OK) |

**Validation**: If user provides cluster specifications, verify they meet these minimums for high-write scenarios.

**Speed Factors:**
- Part size (optimal range: 100MB ~ 10GB for faster migration)
- Instance specs (CPU, memory)
- Disk specs (PL1/PL2/PL3, ESSD tier)
- Data characteristics

**Migration Feasibility Check:**
| Scenario | Action |
|----------|--------|
| Migration speed < Write speed | ❌ Migration will never complete. Cancel task, use manual migration instead |
| Migration speed > Write speed | ✅ Can proceed. For higher success rate, ensure: `Data size / (Migration speed - Write speed) ≤ 5 days` |

**Note:** Actual migration speed varies by environment. Test in your environment to get accurate numbers. Monitor target cluster disk throughput during migration to verify actual speed.

### 1.10 Console (cksync) Resource Requirements

**Minimum Requirements:**
- CPU: At least **2 kernels**
- Memory: At least **4 GB**

**Recommendation:** Test in real environment to validate. You can ask user about available memory size and kernel count to verify.

### 1.11 Target Cluster Disk Size Requirements

| Target Cluster Type | Required Disk Size | Notes |
|---------------------|-------------------|-------|
| **Community Edition** | ≥ **1.5 × source cluster data size** | Must provision extra space for merge operations and data growth |
| **Enterprise Edition** | No specific requirement | Enterprise Edition uses infinite object storage (OSS) |

### 1.12 Merge Risk Warning (IMPORTANT)

⚠️ **Critical Risk**: Console (cksync) **stops ALL merges** on the target cluster during synchronization. After sync completes, all pending merges will start simultaneously, which can cause:
- **High CPU usage**
- **High I/O load**
- **High memory consumption**

**Large Merges Duration Estimation (per node):**
```
Merge Duration = Storage Size / (IO Bandwidth / 2)
```

**Disk RAID Configuration (Alibaba Cloud Community):**
| Storage Size | Disk Configuration | Notes |
|--------------|-------------------|-------|
| < 2 TB | 1 × disk | Single disk |
| ≥ 2 TB | 4 × disk RAID | Striped for higher bandwidth |

**Merge Duration Examples:**

| Example | Storage | ECS Spec | Disk Config | IO Bandwidth | Merge Duration |
|---------|---------|----------|-------------|--------------|----------------|
| 1 | 1 TB | 8C32GB | 1 × PL1 ESSD | 250 MB/s | ~2.2 hours |
| 2 | 1 TB | 16C64GB | 4 × PL1 ESSD RAID | 1,200 MB/s | ~0.5 hours |
| 3 | 1 TB | 80C384GB | 4 × PL2 ESSD RAID | 2,000 MB/s | ~0.28 hours |

*Note: In all examples above, IO bandwidth is limited by ECS disk bandwidth, not by the ESSD disk specifications.*

**How To Stop Merge Storm:**
See the dedicated "stop-merge-storm" operational guide in this skill package.

**Reference:** https://help.aliyun.com/zh/clickhouse/user-guide/migrate-table-data-from-a-self-managed-clickhouse-cluster-to-an-apsaradb-for-clickhouse-cluster#d82cf49170zd4

---

## 2. BACKUP/RESTORE Migration

> **Note**: BACKUP/RESTORE only works between **same edition types** (Community→Community or Enterprise→Enterprise) due to different underlying storage engines. For cross-edition migrations (e.g., Community→Enterprise), use Console (cksync) instead.
>
> Even if version requirements are met (≥22.8), prefer Console (cksync) for in-place operations like AZ switch.

### 2.1 Migration Type Conditions
**Supported (same edition type only):**
- (Cross-cluster) Community → Community ✅
- (Cross-cluster) Enterprise → Enterprise ✅
- (Cross-cluster) Self-built → Self-built (if both use same engine type)

**NOT Supported:**
- ❌ In-place migrations (use cksync instead)
- ❌ Community → Enterprise (different underlying engines)
- ❌ Self-built → Alibaba Cloud (use cksync or INSERT FROM REMOTE)

### 2.2 Business Impact
- Business allows read-only during entire BACKUP/RESTORE process
- Duration depends on data size and cluster resources
- Table-level: read-only on related tables
- Cluster-level: read-only on entire cluster

### 2.3 Database Engine Support
| Engine | Supported |
|--------|-----------|
| Ordinary | Yes |
| Atomic | Yes |
| Replicated | Yes |
| MaterializedMySQL | No (use DTS) |
| MySQL/PostgreSQL/SQLite | No (migrate manually) |
| MaterializedPostgreSQL | No (migrate manually) |

### 2.4 Table Engine Support
- MergeTree family: Supported
- Distributed: Supported
- View: Supported
- MaterializedView: Supported
- External tables: Migrate manually
- Kafka/RabbitMQ: Migrate manually
- Log family: NOT supported (use INSERT FROM REMOTE)

### 2.5 Version Requirements
- Both clusters must be ≥22.8 to support BACKUP/RESTORE commands

### 2.6 Storage Medium Recommendation

**Recommended: Alibaba Cloud OSS**
- **OSS** (Object Storage Service) is Alibaba Cloud's object storage, S3-compatible
- ClickHouse can access OSS directly via **S3 external engine** (no additional drivers needed)
- Data is transferred via OSS, accessible by both source and target clusters
- No manual data copy between clusters required
- Speed: up to 2GB/s to OSS

**Not Recommended: DISK**
- Requires manual copy of backup files between clusters
- More complex and error-prone

### 2.7 BACKUP/RESTORE Commands

#### Complete Syntax Reference
```sql
BACKUP | RESTORE [ASYNC]
-- What to backup/restore
TABLE [db.]table_name           [AS [db.]table_name_in_backup] |
DICTIONARY [db.]dictionary_name [AS [db.]name_in_backup] |
DATABASE database_name          [AS database_name_in_backup] |
TEMPORARY TABLE table_name      [AS table_name_in_backup] |
VIEW view_name                  [AS view_name_in_backup] |
[EXCEPT TABLES ...] |
ALL [EXCEPT {TABLES|DATABASES}...] } [,...]
-- Cluster option
[ON CLUSTER 'cluster_name']
-- Storage destination
TO|FROM 
  File('<path>/<filename>') | 
  Disk('<disk_name>', '<path>/') | 
  S3('<S3 endpoint>/<path>', '<Access key ID>', '<Secret access key>') |
  AzureBlobStorage('<connection string>/<url>', '<container>', '<path>', '<account name>', '<account key>')
[SETTINGS ...]
```

#### Table-Level Backup/Restore

**Community Edition** (requires `ON CLUSTER`):
```sql
-- Backup
BACKUP TABLE <database>.<table> ON CLUSTER default 
TO S3('https://<yourBucketName>.<yourEndpoint>/<path>/', '<yourAccessKeyID>', '<yourAccessKeySecret>');

-- Restore
RESTORE TABLE <database>.<table> ON CLUSTER default 
FROM S3('https://<yourBucketName>.<yourEndpoint>/<path>/', '<yourAccessKeyID>', '<yourAccessKeySecret>');
```

**Enterprise Edition** (no `ON CLUSTER` needed):
```sql
-- Backup
BACKUP TABLE <database>.<table> 
TO S3('https://<yourBucketName>.<yourEndpoint>/<path>/<filename>.zip', '<yourAccessKeyID>', '<yourAccessKeySecret>');

-- Restore
RESTORE TABLE <database>.<table> 
FROM S3('https://<yourBucketName>.<yourEndpoint>/<path>/<filename>.zip', '<yourAccessKeyID>', '<yourAccessKeySecret>');
```

#### Database-Level Backup/Restore

**Community Edition** (requires `ON CLUSTER`):
```sql
-- Backup entire database
BACKUP DATABASE <database_name> ON CLUSTER default 
TO S3('https://<yourBucketName>.oss-cn-hangzhou.aliyuncs.com/backup/<database_name>_full/', '<yourAccessKeyID>', '<yourAccessKeySecret>');

-- Restore entire database
RESTORE DATABASE <database_name> ON CLUSTER default 
FROM S3('https://<yourBucketName>.oss-cn-hangzhou.aliyuncs.com/backup/<database_name>_full/', '<yourAccessKeyID>', '<yourAccessKeySecret>');
```

### 2.8 Progress Monitoring

**Check BACKUP progress:**
```sql
SELECT * FROM system.backups ORDER BY start_time DESC;
-- Expected status: 'BACKUP_CREATED'
```

**Check RESTORE progress:**
```sql
SELECT * FROM system.backups WHERE name LIKE '%restore%' ORDER BY start_time DESC;
-- Expected status: 'RESTORED'
```

**Status values:**
| Status | Meaning |
|--------|---------|
| `CREATING_BACKUP` | Backup in progress |
| `BACKUP_CREATED` | Backup completed successfully |
| `BACKUP_FAILED` | Backup failed |
| `RESTORING` | Restore in progress |
| `RESTORED` | Restore completed successfully |
| `RESTORE_FAILED` | Restore failed |

### 2.9 Documentation Links
- Alibaba Cloud: https://help.aliyun.com/zh/clickhouse/user-guide/use-the-backup-and-restore-commands-for-data-backup-and-restoration
- ClickHouse Official: https://clickhouse.com/docs/operations/backup/s3_endpoint

---

## 3. INSERT FROM REMOTE Migration

> **Use Case for Enterprise → Enterprise**: Along with BACKUP/RESTORE, this is one of the two methods available for Enterprise → Enterprise migrations (cksync does NOT support this scenario). Prefer INSERT FROM REMOTE when you need fine-grained control over migration scope.

### 3.1 Migration Type Conditions
**Supported:**
- All cross-cluster migrations (including Enterprise → Enterprise)

**NOT Supported:**
- In-place migrations

### 3.2 Business Impact Conditions
Based on table design, choose one:
- Small tables (<20GB), 10min read-only: Migrate entire table during write stop
- Large tables (>20GB) with time partitions (latest <20GB), 10min read-only: Migrate historical partitions first, then stop writes for latest partition
- Large tables without time partitions: Requires full read-only during entire migration

### 3.3 Database/Table Engine Support
Same as cksync migration, except:
- Log family tables: Supported
- Enterprise → Enterprise: Supported

### 3.4 Version Requirements
- All versions supported

---

## 4. Business Double-Write

### 4.1 Migration Type Conditions
All cross-cluster migrations supported (NOT in-place)

### 4.2 Business Impact
- Zero impact during migration

### 4.3 Business Cooperation Requirements
- Must implement dual INSERT to both clusters
- Must implement dual DDL to both clusters
- Must handle exceptions for both clusters

### 4.4 Table Engine Conditions
**MergeTree family:**
- Double-write duration must cover minimum required data (TTL period)
- During double-write period (N days), pay for both clusters

**External tables:** Business creates manually

**Kafka/RabbitMQ:** Use new consumer group in new cluster

**Log family:** Supported

### 4.5 Version Requirements
All versions supported

---

## 5. Kafka Double-Write

### 5.1 Migration Type Conditions
All cross-cluster migrations supported (NOT in-place)

### 5.2 Business Impact
Zero impact during migration

### 5.3 Business Cooperation Requirements
- Transform INSERT requests to write to Kafka
- Both clusters consume from Kafka via Kafka engine + MaterializedView
- Must implement dual DDL to both clusters

### 5.4 Database Engine Support
- Supported: Ordinary, Atomic, Replicated
- NOT supported: MaterializedMySQL (use DTS)
- Use other methods: MySQL, PostgreSQL, SQLite, MaterializedPostgreSQL

### 5.5 Table Engine Conditions
**MergeTree family:**
- Must transform to receive data from Kafka
- Double-write duration must cover minimum required data

**External tables:** Business creates manually

**Kafka/RabbitMQ:** Supported

**Log family:** Must transform to receive from Kafka

### 5.6 Version Requirements
- Source cluster: ≥19.x
- Target cluster: ≥19.x (Alibaba Cloud clusters satisfy this)

---

## 6. Big Cluster Federation

Advanced method - high technical requirements.

### 6.1 Migration Type Conditions
**Supported:**
- Community → Enterprise
- Community → Community
- Self-built → Community/Enterprise

**NOT Supported:**
- In-place migrations
- Enterprise → Enterprise

### 6.2 Business Impact
Zero impact during migration

### 6.3 Business Cooperation Requirements
- INSERT to new cluster only
- SELECT from federation distributed table (contains both old and new cluster data)
- DDL to both clusters
- Eventually switch SELECT to new cluster

### 6.4 Table Engine Conditions
**MergeTree family:**
- Modify distributed table definition to include new cluster shard
- Double-run duration must cover minimum required data

**External tables:** Migrate manually

**Kafka/RabbitMQ:** Use new consumer group

**Log family:**
- New cluster is Community: Supported
- New cluster is Enterprise: NOT supported (Enterprise doesn't support Log engine)

### 6.5 Version Requirements
All versions supported
