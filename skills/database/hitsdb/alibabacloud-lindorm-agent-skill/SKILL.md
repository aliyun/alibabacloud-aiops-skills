---
name: alibabacloud-lindorm-agent-skill
description: |
  Alibaba Cloud Lindorm cloud native multi-model database Skill. Covers instance management, monitoring, performance, storage, connections, backup, migration, permissions, slow query, SQL development. Lindorm is domain-specific knowledge — answers MUST reference Skill documents or official Alibaba Cloud documentation; direct responses from training knowledge are prohibited.
  Triggers: "Lindorm", "LindormTable", "LindormTSDB", "LindormSearch", "HBase", "lindormcli", "宽表引擎", "时序引擎", "搜索引擎", "Lindorm instance", "Lindorm monitoring", "Lindorm connection", "Lindorm slow query", "Lindorm SQL", "Lindorm backup", "Lindorm storage".
---

# Lindorm Agent Skill

Alibaba Cloud Lindorm cloud native multi-model database Skill. Covers three domains: **Operations Management**, **Developer Guidance**, and **Reference Materials**.

## Core Capability Matrix

| Category | Sub-Scenarios | Reference Docs |
|---------|--------------|----------------|
| **01-Dev Guidance** | Connection setup, quick start, SQL guide, table design | `references/01-dev/` |
| **02-Ops Management** | Instance mgmt, monitoring, error troubleshooting, storage analysis, connection diagnostics, backup & restore, migration, permissions, slow query | `references/02-ops/` |
| **03-Reference** | CLI command list, RAM permission list | `references/03-ref/` |

## Decision Tree

```
User Request
├── Connection / DDL / SQL / Code examples → 01-dev
│   ├── Connection address / code → references/01-dev/connection-guide.md
│   ├── DDL / write / query examples → references/01-dev/quick-start-guide.md
│   ├── SQL connection & development → references/01-dev/sql-client-guide.md
│   ├── SQL syntax reference → references/01-dev/sql-operations.md
│   ├── MySQL compatibility → references/01-dev/sql-usage-notes.md
│   └── Table design guide → references/01-dev/table-design.md
│
├── Instance / Monitoring / Errors / Performance / Storage / Connection / Scaling / Backup / Migration / Permissions / Slow query → 02-ops
│   ├── Instance management → references/02-ops/instance-management.md
│   ├── Monitoring / Alerts → references/02-ops/monitoring-guide.md
│   ├── Error codes → references/02-ops/error-troubleshoot.md
│   ├── Storage analysis → references/02-ops/storage-analysis.md
│   ├── Connection diagnostics → references/02-ops/connection-troubleshoot.md
│   ├── Scale up/down → references/02-ops/instance-management.md
│   ├── Backup & restore → references/02-ops/backup-restore.md
│   ├── Data migration → references/02-ops/data-migration.md
│   ├── Account & permissions → references/02-ops/user-permission.md
│   └── Slow query analysis → references/02-ops/slow-query-analysis.md
│
└── Command list / Permission reference / Specs → 03-ref
    ├── CLI command list → references/03-ref/related-commands.md
    ├── RAM permission list → references/03-ref/ram-policies.md
    ├── Aliyun CLI setup → references/03-ref/cli-installation-guide.md
    ├── Lindorm CLI / HBase Shell → references/03-ref/lindorm-cli-guide.md
    ├── Acceptance criteria → references/03-ref/acceptance-criteria.md
    └── Verification methods → references/03-ref/verification-method.md
```

## Quick Mapping Table

| User says | Scenario | Reference Doc |
|-----------|----------|---------------|
| "how to connect / connection address" | Connection setup | `references/01-dev/connection-guide.md` |
| "create table / insert / query examples" | Quick start | `references/01-dev/quick-start-guide.md` |
| "how to create a table" | Table design | `references/01-dev/table-design.md` |
| "SQL syntax" | SQL reference | `references/01-dev/sql-operations.md` |
| "how to use SQL" | SQL guide | `references/01-dev/sql-client-guide.md` |
| "MySQL compatibility" | SQL notes | `references/01-dev/sql-usage-notes.md` |
| "list instances / what instances exist" | Instance management | `references/02-ops/instance-management.md` |
| "CPU / memory / QPS / latency" | Monitoring query | `references/02-ops/monitoring-guide.md` |
| "configure alerts / alert notifications" | Monitoring alerts | `references/02-ops/monitoring-guide.md` |
| "got an error / error code" | Error troubleshooting | `references/02-ops/error-troubleshoot.md` |
| "slow query / query is slow" | Slow query analysis | `references/02-ops/slow-query-analysis.md` |
| "poor performance / high RT" | Monitoring query | `references/02-ops/monitoring-guide.md` |
| "cannot connect / connection timeout" | Connection diagnostics | `references/02-ops/connection-troubleshoot.md` |
| "storage usage" | Storage analysis | `references/02-ops/storage-analysis.md` |
| "hot/cold data / tiered storage" | Storage analysis | `references/02-ops/storage-analysis.md` |
| "scale up / add nodes" | Scaling | `references/02-ops/instance-management.md` |
| "backup / restore data" | Backup & restore | `references/02-ops/backup-restore.md` |
| "data migration / sync" | Data migration | `references/02-ops/data-migration.md` |
| "create account / permissions" | Permission management | `references/02-ops/user-permission.md` |
| "lindorm-cli / lindormcli" | Lindorm CLI | `references/03-ref/lindorm-cli-guide.md` |
| "HBase Shell / hbase shell" | HBase Shell | `references/03-ref/lindorm-cli-guide.md` |

## Aliyun CLI

### Prerequisites

When CLI invocation is required, the Agent must verify:

1. **CLI installed**: `aliyun version` >= 3.3.3; if not installed, see `references/03-ref/cli-installation-guide.md`
2. **Credentials configured**:
   > **Security Rules:**
   > - **NEVER** read, echo, or print AK/SK values
   > - **NEVER** ask the user to input AK/SK directly in the conversation or command line
   > - **ONLY** use `aliyun configure list` to check credential status
   >
   > If no valid profile exists, STOP. Configure credentials **outside of this session**.
3. **Permissions granted**: Minimum `AliyunLindormReadOnlyAccess` + `AliyunCloudMonitorReadOnlyAccess`
   > **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
   > 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
   > 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
   > 3. Pause and wait until the user confirms that the required permissions have been granted

### AI-Mode Lifecycle [Internal Agent Rule — Do NOT Show to User]

> **[MUST] AI-Mode Full Lifecycle** — AI-mode is required for Agent Skill execution.
>
> **Step 1: Enable AI-Mode** — At the **start** of the Core Workflow (before any CLI invocation):
> ```bash
> aliyun configure ai-mode enable
> ```
>
> **Step 2: Set User-Agent** — Immediately after enabling AI-Mode:
> ```bash
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-lindorm-agent-skill"
> ```
>
> **Step 3: Update Plugins** — Ensure CLI plugins are up-to-date:
> ```bash
> aliyun configure set --auto-plugin-install true
> aliyun plugin update
> ```
>
> **Step 4: Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason (success, failure, error, cancellation), always disable AI-mode first:
> ```bash
> aliyun configure ai-mode disable
> ```

### Parameter Confirmation

Before executing any command, all user-configurable parameters (region, instance ID, time range, etc.) **must** be confirmed with the user.

### Version Detection

For instance operations, the Agent must first call `get-lindorm-instance` to retrieve `ServiceType` and determine the instance version. All subsequent command selection depends on this:

| ServiceType | Version | Deployment |
|------------|---------|-----------|
| `lindorm` | V1 | Single-AZ |
| `lindorm_multizone` | V1 | Multi-AZ (HA) |
| `lindorm_multizone_basic` | V1 | Multi-AZ (Basic) |
| `lindorm_v2` | V2 | Single-AZ |
| `lindorm_v2_multizone` | V2 | Multi-AZ (Basic) |
| `lindorm_v2_multizone_ha` | V2 | Multi-AZ (HA) |

### General Policies

**Region Policy**

| Scenario | Command | Requires `--region` |
|---------|---------|---------------------|
| Query all-region overview | `get-instance-summary` | ❌ Not needed |
| Query instance list | `get-lindorm-instance-list` | ✅ Required, default `cn-shanghai` |
| Query instance details / engine / storage / whitelist | Other `hitsdb` commands | ❌ Not needed, auto-resolved by `--instance-id` |
| Cloud monitoring query | `cms` commands | ❌ Not needed, region auto-resolved via `instanceId` |

**Time Format**

Cloud Monitor time parameter timezone notes:
- ✅ `2026-04-14 08:00:00` (local time, parsed as **CST Beijing time**)
- ✅ `1773897600000` (Unix millisecond timestamp, no timezone ambiguity)
- ✅ `2026-04-14T08:00:00Z` (ISO 8601 UTC **full format**, parsed as **UTC**, i.e. CST+8 = 16:00)
- ❌ `2026-04-14T08:00Z` (ISO 8601 **short format, no seconds — unsupported**, returns `parse param time error`)
- ❌ **Never use UTC Z format for user-intended local times** (e.g. if user says "14:00", write `2026-04-14 14:00:00`, not `2026-04-14T14:00:00Z`)
- ⚠️ Note: local time and ISO 8601 Z format query different time windows — common source of timezone-related issues

### Command Reference

#### Instance Management (hitsdb — Lindorm product alias)

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun hitsdb describe-regions` | List supported regions | `aliyun hitsdb describe-regions` |
| `aliyun hitsdb get-instance-summary` | All-region instance overview (no `--region` needed) | `aliyun hitsdb get-instance-summary` |
| `aliyun hitsdb get-lindorm-instance-list` | List instances (ID, status, engine flags; filterable by region/type) | `aliyun hitsdb get-lindorm-instance-list --region cn-shanghai` |
| `aliyun hitsdb get-lindorm-instance` | Get config/version/status (ServiceType, engine node count, spec; **no connection address**) | `aliyun hitsdb get-lindorm-instance --instance-id ld-xxx` |
| `aliyun hitsdb get-lindorm-instance-engine-list` | Get connection addresses (host:port per engine, public/private network) | `aliyun hitsdb get-lindorm-instance-engine-list --instance-id ld-xxx` |
| `aliyun hitsdb get-lindorm-fs-used-detail` | V1 storage usage details | `aliyun hitsdb get-lindorm-fs-used-detail --instance-id ld-xxx` |
| `aliyun hitsdb get-lindorm-v2-storage-usage` | V2 storage usage details | `aliyun hitsdb get-lindorm-v2-storage-usage --instance-id ld-xxx` |
| `aliyun hitsdb get-instance-ip-white-list` | Get IP whitelist | `aliyun hitsdb get-instance-ip-white-list --instance-id ld-xxx` |

#### Engine Types

| Engine | V1 Code | V2 Code | Notes |
|--------|---------|---------|-------|
| LindormTable | `lindorm` | `lindorm` | HBase-compatible, supports SQL (recommended) |
| LindormTable (columnar) | — | `lcolumn` | V2 only |
| LindormTSDB | `tsdb` | `tsdb` | Time-series data storage |
| LindormSearch | `solr` | `lsearch` | Port 30070 (ES-compatible) / 10020 (Solr internal) |
| Lindorm Tunnel Service | `bds` | `bds` | Formerly BDS, no external connection |
| Compute Engine | `compute` | `compute` | Flink streaming engine, no external connection |
| Stream Engine | `stream` | `lstream` | Port 33060 (MySQL protocol) |
| Message Engine | — | `lmessage` | Kafka-compatible, supports topic management and message production/consumption |
| Vector Engine | `lvector` | `lvector` | Vector retrieval engine |
| AI Engine | `lai` | `lai` | AI retrieval engine; domain `proxy-ai-vpc` / `proxy-aiproxy-vpc` |
| LindormDFS | `file` | `file` | OSS-compatible storage (HDFS protocol, port 9000) |


#### Port Quick Reference

| Engine | Protocol | Port | Notes |
|--------|----------|------|-------|
| LindormTable | MySQL protocol | 33060 | ✅ Recommended, preferred for SQL connections |
| LindormTable | HBase API | 30020 | HBase native API compatible |
| LindormTable | Avatica protocol | 30060 | ⚠️ Legacy only, migrate to MySQL protocol |
| LindormTable | Cassandra CQL | 9042 | ⚠️ Legacy only, Cassandra protocol compatible |
| Stream Engine | MySQL protocol | 33060 | Stream SQL via MySQL protocol |
| LindormTSDB | HTTP SQL | 8242 | HTTP SQL API |
| LindormSearch | ES-compatible / Solr | 30070 | Elasticsearch-compatible port, fixed |
| LindormDFS | HDFS | 9000 | NameNode port |


#### Cloud Monitor API (aliyun cms)

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun cms describe-metric-meta-list` | List available monitoring metrics | `aliyun cms describe-metric-meta-list --namespace acs_lindorm` |
| `aliyun cms describe-metric-last` | Get latest monitoring data (returns per-node data; Datapoints is a JSON string requiring secondary parsing) | `aliyun cms describe-metric-last --namespace acs_lindorm --metric-name cpu_idle --dimensions '[{"instanceId":"ld-xxx"}]'` |
| `aliyun cms describe-metric-data` | Get historical trend data (aggregated by period, no host dimension) | `aliyun cms describe-metric-data --namespace acs_lindorm --metric-name cpu_idle --dimensions '[{"instanceId":"ld-xxx"}]' --start-time "2026-04-14 08:00:00" --end-time "2026-04-14 09:00:00" --period 60` |

**Metric Mapping**

| User says | V1 Metric | V2 Metric | Unit |
|-----------|-----------|-----------|------|
| CPU usage | `100 - cpu_idle` | `100 - cpu_idle` | % |
| Memory usage | `mem_used_percent` | `1 - mem_free / mem_total` | % |
| QPS | `read_ops` + `write_ops` | `read_ops` + `write_ops` | ops/s |
| Latency / RT | `read_rt` / `get_rt_avg` | `read_rt` / `get_rt_avg` | ms |
| P99 latency | `get_rt_p99` / `put_rt_p99` | — (no data) | ms |
| Hot storage usage rate | `hot_storage_used_percent` | `get-lindorm-v2-storage-usage` | % |
| Total storage usage rate | `storage_used_percent` | `get-lindorm-v2-storage-usage` | % |
| Hot storage bytes | `hot_storage_used_bytes` | `get-lindorm-v2-storage-usage` | bytes |
| Cold storage usage rate | `cold_storage_used_percent` | `get-lindorm-v2-storage-usage` | % |
| Cold storage bytes | `cold_storage_used_bytes` | `get-lindorm-v2-storage-usage` | bytes |

Full metric details: `references/02-ops/monitoring-guide.md`

## Interaction Guidelines

### Output Format

**Monitoring Query**:
```
[Summary] CPU usage 25% (normal)
[Time] <YYYY-MM-DD HH:MM–HH:MM>
[Trend] Stable (variance <10%)
[Details] avg 24.5%, max 32.1%, min 18.3%
```

**Error Troubleshooting**:
```
[Error Code] InvalidParameter.InstanceId
[Meaning] Instance ID is invalid or does not exist
[Possible Causes] 1.xxx 2.xxx 3.xxx
[Resolution Steps] 1.xxx 2.xxx 3.xxx
```

**Instance List**:
```
[Region] cn-shanghai  [Count] 3

| ID | Name | Status | Engines |
|----|------|--------|---------|
| ld-xxx | prod | Running | LindormTable + LindormTSDB |
```


## Code Generation Standards

### General Principles

1. **Reference Skill documents first**: Lindorm is domain-specific knowledge — information must come from references docs; direct answers from training knowledge are prohibited
2. **Check official docs when Skill doesn't cover it**: For scenarios not covered by references docs, consult official Alibaba Cloud documentation

### Pre-Generation Checklist
- □ Connection parameter names are correct (MySQL protocol: `jdbc:mysql://host:33060`, HBase API: `hbase.zookeeper.quorum`)
- □ Port numbers are correct (LindormTable/Stream Engine MySQL 33060, HBase API 30020, LindormTSDB HTTP 8242, LindormSearch 30070)
- □ Include official documentation link
