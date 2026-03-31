# Migration Plan Template

Use this template when generating migration plans. Copy and fill in the sections below.

## Template Constraints

> **IMPORTANT:** When generating migration plans based on this template:
> - **Output language** - If not explicitly specified, use the same language as the main conversation (e.g., if user speaks Chinese, output in Chinese; if English, output in English)
> - **DO NOT modify any hyperlinks** - Keep all 'help.aliyun.com' URLs exactly as provided to avoid broken links
> - **Local references → Read, analyze, write as needed** - When referencing local files (e.g., `references/*.md`), read and analyze the content, then write relevant parts into the output file as needed; referenceing local files is not allowed in the chapter *Reference Links*.
> - **Public URLs → Link directly** - Public web URLs (e.g., `help.aliyun.com`) can be directly linked without copying content
> - **Non-Console migration + SQL/script** - If the **Recommended Method** is **not** Console (cksync) **and** the migration relies on SQL or scripts (e.g., `INSERT FROM REMOTE`, `BACKUP`/`RESTORE`, double-write, big-cluster paths), the generated plan **must** include the **SQL and/or scripts** that correspond to that method and this migration (steps, commands, parameters; use placeholders for secrets). Derive accurate syntax via the **Local references** rule above. If the chosen path is Console (cksync) only, this requirement does not apply.

---

## Migration Plan: [Cluster Name / Instance ID]

**Generated:** [YYYY-MM-DD]  
**Planner:** cksync-plan skill  
**Source:** [Source Cluster Type] v[Version] ([Instance ID])  
**Target:** [Target Cluster Type] ([Instance ID or "To be created"])

---

### 1. Executive Summary

| Item | Value |
|------|-------|
| Recommended Method | [Console (cksync) / BACKUP/RESTORE / INSERT FROM REMOTE / Double-Write / Big Cluster] |
| Total Data Size | [X.XX TB / GB] |
| Total Tables | [N tables across M databases] |
| Total Write Speed | [XX MB/s] |
| Estimated Migration Time | [X hours / days] |
| Required Downtime | [X minutes / hours / Zero] |
| Risk Level | [Low / Medium / High] |

---

### 2. Source Cluster Analysis

#### 2.1 Cluster Information
| Item | Value |
|------|-------|
| Cluster Type | [Self-built / Alibaba Cloud Community / Alibaba Cloud Enterprise] |
| Version | [e.g., 24.3.1] |
| Node Count | [N nodes] |
| Instance Spec | [e.g., 8C32G] |

#### 2.2 Database Summary
| Database | Engine | Tables | Total Size | Status |
|----------|--------|--------|------------|--------|
| [db_name] | [Atomic/Ordinary/...] | [N] | [X GB] | ✅ Supported / ⚠️ Warning / ❌ Not Supported |

#### 2.3 Table Details
| Table | Engine | Size | Partitions | Write Speed | TTL | Status |
|-------|--------|------|------------|-------------|-----|--------|
| [db.table] | [MergeTree/...] | [X GB] | [N] | [X MB/s] | [N days] | ✅/⚠️/❌ |

#### 2.4 Compatibility Check
| Check Item | Result | Action Required |
|------------|--------|------------------|
| MaterializedMySQL engines | ✅ None / ❌ Found | [Use DTS instead] |
| TTL check | ✅ No TTL (permanent) / ✅ TTL ≥3 days / ⚠️ TTL <3 days | [If <3 days: new cluster data count may be larger due to merge stopping] |
| Partitions < 10,000 | ✅ Pass / ❌ Fail | [Merge partitions first] |
| Kafka/RabbitMQ tables | ✅ None / ⚠️ Found | [Manual migration required] |
| View/MaterializedView | ✅ Supported | [Automatically migrated by cksync] |
| External tables (MaxCompute, etc.) | ✅ Supported | [Verify network connectivity from target cluster] |
| Write speed < Migration speed | ✅ Pass / ⚠️ Warning | [Upgrade cluster specs] |
| Cluster spec for high-write | ✅ Adequate / ⚠️ Insufficient | [Community: ≥80C/PL2-PL3, Enterprise: ≥32CCU] |

#### 2.5 Target Cluster Sizing (For cksync)
| Check Item | Requirement | Actual | Status |
|------------|-------------|--------|--------|
| Disk Size (Community) | ≥1.5 × [Source Data Size] | [X GB] | ✅/❌ |
| Disk Size (Enterprise) | N/A (infinite OSS) | N/A | ✅ |
| CPU (cksync runner) | ≥2 kernels | [X kernels] | ✅/❌ |
| Memory (cksync runner) | ≥4 GB | [X GB] | ✅/❌ |

---

### 3. Migration Method Selection

#### 3.1 Selected Method
**[Method Name]**

#### 3.2 Selection Rationale
| Factor | Evaluation |
|--------|------------|
| Migration type support | ✅ [Source] → [Target] supported |
| Version compatibility | ✅ Source v[X] / Target v[Y] compatible |
| Downtime requirement | ✅ [X minutes] within allowed [Y minutes] |
| Data volume | ✅ [X TB] manageable with this method |
| Write speed | ✅ Migration speed ([X MB/s]) > Write speed ([Y MB/s]) |

#### 3.3 Alternatives Considered
| Method | Reason Not Selected |
|--------|---------------------|
| [Method 1] | [Reason - e.g., "Version < 22.8, BACKUP/RESTORE not supported"] |
| [Method 2] | [Reason - e.g., "Zero downtime not required, simpler method preferred"] |

---

### 4. Migration Steps

#### 4.1 Pre-Migration Checklist
- [ ] Verify source cluster accessibility
- [ ] Create target cluster with appropriate specs
- [ ] Configure network connectivity between clusters
- [ ] Verify SQL compatibility (if version differs)
- [ ] Back up critical data
- [ ] Notify stakeholders of migration window

#### 4.2 Migration Execution
| Step | Action | Command/Details | Estimated Time |
|------|--------|-----------------|----------------|
| 1 | [Action] | [SQL/Command] | [X min] |
| 2 | [Action] | [SQL/Command] | [X min] |
| 3 | [Action] | [SQL/Command] | [X min] |

#### 4.2.1 SQL and Scripts (Required when NOT Console/cksync)

> **Skip this subsection** if the Recommended Method is **Console (cksync)** and no manual SQL/scripts are used.

State briefly how SQL/scripts map to the chosen method, if not already fully covered by the **Section 4.2** table. The **Command/Details** column must contain the **actual SQL and/or script content** (or clearly scoped snippets) needed for this migration, not only step titles.

#### 4.3 Post-Migration Verification

Verify row counts using methods from [references/sql.md](../references/sql.md) Section 3:
- **Section 3.1** Table-Level Row Count (for MergeTree/ReplicatedMergeTree without DROP/TRUNCATE/DELETE/TTL)
- **Section 3.2** Partition-Level Row Count (when table-level may not match)
- **Section 3.3** Accurate Count with FINAL (for merging engines, data operations, TTL)
- **Section 3.4** Query Result Verification (hash comparison)

- [ ] Verify row counts match between source and target
- [ ] Run sample queries on target cluster
- [ ] Verify application connectivity to target
- [ ] Monitor target cluster performance

#### 4.4 Merge Storm Mitigation (Only for Console/cksync)

> **Skip this section if NOT using Console (cksync) migration method.**

> **IMPORTANT:** cksync stops ALL merges during sync. After completion, pending merges start simultaneously causing high CPU/IO/memory.

**Step 1: Pre-analyze part sizes on source cluster (before migration)**

See [references/stop-merge-storm.md](../references/stop-merge-storm.md) Step 1 for SQL.

| Table | p10 Uncompressed (MB) | Storage % | Recommended Limit |
|-------|----------------------|-----------|-------------------|
| [db.table1] | [X] | [Y%] | [2X MB] |
| [db.table2] | [...] | [...] | [...] |

**Step 2: Apply merge limits on target cluster (immediately after sync)**

See [references/stop-merge-storm.md](../references/stop-merge-storm.md) Step 3 for SQL.

- [ ] Applied merge limits to top 5 tables
- [ ] Verified CPU/IO/memory stable

**Step 3: Gradually restore merge settings (after stabilization)**

See [references/stop-merge-storm.md](../references/stop-merge-storm.md) Step 4 for approach.

| Restoration Phase | Limit Value | Status |
|-------------------|-------------|--------|
| Initial | [X GB] | ✅/⏳ |
| +1-2 hours | [2X GB] | ⏳ |
| +1-2 hours | [4X GB] | ⏳ |
| Final (target ≤10GB) | [10 GB] | ⏳ |

#### 4.5 Traffic Switchover
- [ ] Stop writes to source cluster
- [ ] Wait for final sync completion
- [ ] Update application connection strings
- [ ] Verify application functionality
- [ ] Monitor for errors

---

### 5. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Migration speed < write speed | [Low/Med/High] | High | Upgrade cluster specs; reduce write load during migration |
| Network interruption | Low | Medium | Configure retry mechanism; use incremental sync |
| Data inconsistency | Low | High | Verify row counts; run checksum queries |
| Application compatibility | [Low/Med/High] | High | Pre-test queries on target; use compatibility settings |
| DDL changes during migration | Medium | High | Freeze DDL operations; coordinate with dev team |
| **TTL ≤3 days data count mismatch** | [If applicable] | Medium | New cluster may have more data (source TTL merge deletes during sync, target merges stopped). Inform business; verify after TTL period. |
| **Post-sync merge storm** | High (cksync) | High | cksync stops all merges during sync. After completion, pending merges cause high CPU/IO/memory. Schedule during low-traffic window. Estimated merge duration per node: `Storage Size / (IO Bandwidth / 2)` |
| Insufficient target disk (Community) | [Low/Med/High] | High | Ensure target disk ≥1.5× source data. Enterprise uses infinite OSS (no risk). |
| Insufficient cksync resources | [Low/Med/High] | High | Need ≥2 kernels and ≥4GB memory. Test in real environment. |

---

### 6. Rollback Plan

#### 6.1 Trigger Conditions
- Data verification fails (row count mismatch > X%)
- Application errors exceed threshold
- Performance degradation on target cluster
- Business-critical functionality broken

#### 6.2 Rollback Steps
| Step | Action | Command/Details |
|------|--------|-----------------|
| 1 | Stop writes to target | [Coordinate with application team] |
| 2 | Revert connection strings | [Update to source cluster endpoint] |
| 3 | Sync new data back to source | [INSERT FROM REMOTE if needed] |
| 4 | Verify source cluster | [Run verification queries] |

#### 6.3 Rollback Time Estimate
[X minutes / hours]

---

### 7. Timeline

| Phase | Start | End | Duration | Owner |
|-------|-------|-----|----------|-------|
| Pre-migration prep | [Date] | [Date] | [X days] | [Team/Person] |
| Migration execution | [Date/Time] | [Date/Time] | [X hours] | [Team/Person] |
| Verification | [Date/Time] | [Date/Time] | [X hours] | [Team/Person] |
| Traffic switchover | [Date/Time] | [Date/Time] | [X min] | [Team/Person] |
| Monitoring period | [Date] | [Date] | [X days] | [Team/Person] |

---

### 8. Reference Links

- Alibaba Cloud ClickHouse Documentation: [URL]
- Migration method guide: [URL]
- Compatibility verification: https://help.aliyun.com/zh/clickhouse/user-guide/analysis-and-solution-of-cloud-compatibility-and-performance-bottleneck-of-self-built-clickhouse
