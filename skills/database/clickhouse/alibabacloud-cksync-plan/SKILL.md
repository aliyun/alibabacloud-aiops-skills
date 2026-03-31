---
name: alibabacloud-cksync-plan
description: ClickHouse cluster migration planner. Use when planning data migration between ClickHouse clusters, including cross-cluster migrations, horizontal scaling, disk downgrade, availability zone changes, or migrating from self-built/non-Alibaba Cloud ClickHouse to Alibaba Cloud ClickHouse (Community or Enterprise Edition). Helps analyze migration conditions, select appropriate migration methods, and generate detailed migration plans.
---

# ClickHouse Sync Plan (cksync-plan)

A skill for planning ClickHouse cluster data migration solutions, including migration plans, risks, and considerations.

## When to Use

- Data migration between different ClickHouse clusters
- Horizontal scaling (adding/removing nodes) for ClickHouse clusters
- Disk downgrade operations
- Cross-availability zone migrations
- Upgrading to multi-replica, multi-AZ deployments

## Workflow

### Step 1: Gather Source Cluster Information

Ask user for **source cluster type**:
- Self-built ClickHouse or non-Alibaba Cloud ClickHouse
- Alibaba Cloud ClickHouse Community Edition
- Alibaba Cloud ClickHouse Enterprise Edition

Ask user for **source cluster version** (e.g., 20.8, 22.8, 23.8, 24.3):
- Version affects migration method compatibility
- BACKUP/RESTORE requires ≥22.8
- Incremental cksync migration requires target ≥20.8

### Step 2: Gather Target Cluster Information

Ask user for **target cluster type**:
- Alibaba Cloud ClickHouse Community Edition
- Alibaba Cloud ClickHouse Enterprise Edition
- To be determined

### Step 3: Collect Cluster Details (REQUIRED)

**This step is mandatory.** You MUST collect database and table information before proceeding to migration plan selection.

#### Required Information
1. **Database list** with engines
2. **Table list** with engines, partition counts, data sizes, and write speeds

#### Option A: User Executes SQL
Provide SQL queries from [references/sql.md](references/sql.md) section 1 for user to execute:

1. **Database Information** - Query `system.databases` for database names and engines
2. **Table Information** - Comprehensive query including table names, engines, engine_full (for TTL), partition counts, data sizes, and write speeds

Key fields to collect:
- `engine_full`: Contains TTL clause (e.g., `TTL event_time + INTERVAL 7 DAY`)
- `part_count`: Partition count per table
- `data_bytes`: Data size per shard
- `write_speed_bytes_per_sec`: Write speed calculated from part_log

For complete SQL queries, see [references/sql.md](references/sql.md) section 1.

#### Option B: Direct Query via HTTP
Request connection details from user:
- `HOST_NAME`: Cluster endpoint (e.g., `cc-xxx.clickhouse.rds.aliyuncs.com`)
- `HTTP_PORT`: HTTP port (default: `8123`)
- `USER_NAME`: Database username
- `PASSWORD`: Database password

Use secure credential handling and HTTP query examples from [references/sql.md](references/sql.md) section 5.

#### Analysis Checklist
After collecting data, verify:
- [ ] Required metadata is complete (database engine, table engine, `engine_full`, partitions, data size, write speed)
- [ ] Migration compatibility checks are completed using [references/plans.md](references/plans.md) (method-specific conditions)
- [ ] Version and read-only window constraints are mapped to candidate methods
- [ ] Risks and mitigations are identified and recorded in the plan

### Step 4: Business Requirements

Ask for **allowed read-only time**:
- 0 minutes
- Within 30 minutes
- Within 1 day
- Not sure yet

### Step 5: Select and Present Migration Plan

Based on gathered information, analyze and recommend from these migration methods:

| Method | Best For | Min Read-Only Time |
|--------|----------|-------------------|
| Console (cksync) | Most migrations to Alibaba Cloud | ~10 min |
| BACKUP/RESTORE | Large data, same edition type, version ≥22.8 | Varies by data size |
| INSERT FROM REMOTE | Flexible control, small-medium data | ~10 min per batch |
| Business Double-Write | Zero downtime required | 0 |
| Kafka Double-Write | Existing Kafka pipelines or business writes switched to Kafka | 0 |
| Big Cluster Federation | Large scale, complex scenarios | 0 |

**Hard requirement: MUST output a plan, never output empty content.**

Even when information is incomplete, you MUST output a **provisional migration plan**.
The provisional plan must include:
- assumptions used,
- missing-information checklist,
- confidence level and key uncertainties,
- next steps to finalize recommendation after user provides missing inputs.

## Migration Methods Overview

### 1. Console (cksync) Migration

Default choice for most Alibaba Cloud migration scenarios, especially in-place operations.
For support boundaries, engine constraints, TTL/write-speed checks, merge risk, and resource prerequisites, see [references/plans.md](references/plans.md) section 1.

### 2. BACKUP/RESTORE Migration

Suitable for same-edition migrations where full backup/restore workflow is acceptable.
For version/edition constraints, supported engines, command patterns, and progress monitoring, see [references/plans.md](references/plans.md) section 2.

### 3. INSERT FROM REMOTE Migration

Best when fine-grained table/partition/time-range control is needed.
For applicability boundaries and operational constraints, see [references/plans.md](references/plans.md) section 3.
For SQL templates and detailed steps, see [references/sql.md](references/sql.md) section 2.

### 4. Business Double-Write

Use when zero downtime is required and application-side dual-write is feasible.
For detailed conditions, see [references/plans.md](references/plans.md) section 4.

### 5. Kafka Double-Write

Use when dual-consumer switchover via Kafka is feasible, including both existing Kafka pipelines and cases where business writes can be switched to Kafka first.
For detailed conditions, see [references/plans.md](references/plans.md) section 5.

### 6. Big Cluster Federation

Advanced option for large/complex migrations with strong business and technical collaboration.

- Community + Enterprise: See [references/big-cluster-community-enterprise.md](references/big-cluster-community-enterprise.md)
- Self-built + Cloud: See [references/big-cluster-self-built-community.md](references/big-cluster-self-built-community.md)

## Output Format

**Default deliverable:** Produce **one migration plan** only. Structure it using [assets/migration-plan-template.md](assets/migration-plan-template.md) and include the key sections below (cluster facts and commands may appear inline in the plan; that counts as the single deliverable).

**Additional files only on request:** Do **not** create separate files for cluster-information documentation, scripts, or SQL unless the customer explicitly asks for them. When they do, use [assets/cluster-info-template.md](assets/cluster-info-template.md) for cluster documentation and place scripts/SQL in clearly named files as requested.

Key sections in the migration plan:
1. **Executive Summary** - Method, data size, duration, downtime
2. **Source Cluster Analysis** - Databases, tables, compatibility check
3. **Migration Method Selection** - Rationale and alternatives
4. **Migration Steps** - Pre/execution/post with commands
5. **Risks & Mitigations** - With probability and impact
6. **Rollback Plan** - Trigger conditions and steps
7. **Timeline** - Phase schedule with owners
8. **Reference Links** - Documentation URLs

## Method Selection Reference

For quick scenario-to-method mapping and method-specific constraints (including in-place migration priority and Enterprise → Enterprise options), see [references/plans.md](references/plans.md) section "Method Selection Priority" and related method sections.

## Additional Resources

- [references/plans.md](references/plans.md) - Detailed migration plan conditions
- [references/sql.md](references/sql.md) - SQL templates and commands
- [references/stop-merge-storm.md](references/stop-merge-storm.md) - How to stop post-sync merge storm
- [references/big-cluster-community-enterprise.md](references/big-cluster-community-enterprise.md) - Community + Enterprise federation
- [references/big-cluster-self-built-community.md](references/big-cluster-self-built-community.md) - Self-built + Cloud federation
