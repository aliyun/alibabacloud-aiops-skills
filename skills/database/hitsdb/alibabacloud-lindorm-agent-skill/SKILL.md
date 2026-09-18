---
name: alibabacloud-lindorm-agent-skill
description: |
  Use this Skill for Alibaba Cloud Lindorm work: instance lifecycle and configuration, networking and access control, monitoring, performance, storage, connection diagnosis, backup, migration, permissions (including Lindorm SQL user management with `CREATE USER` and `GRANT`), slow queries, SQL development, and Search, vector, graph, AI, multimodal, or knowledge-base workflows. Trigger on Lindorm product or CLI terms such as LindormTable, LindormTSDB, LindormSearch, Lindorm AI, HBase/AliHBase, lindormcli, Lindorm CLI, `aliyun lindorm`, or Chinese requests mentioning 宽表引擎、时序引擎、搜索引擎、向量检索、图引擎、白名单、实例创建/扩缩容/释放. Use this Skill's references or official Alibaba Cloud documentation; do not invent Lindorm-specific facts from general training knowledge.
metadata:
  openclaw:
    requires:
      bins: ["aliyun"]
    homepage: https://clawhub.ai/sdk-team/alibabacloud-lindorm-agent-skill
---

# Lindorm Agent Skill

Alibaba Cloud Lindorm cloud native multi-model database Skill. Covers three domains: **Operations Management**, **Developer Guidance**, and **Reference Materials**. Developer guidance includes classic SQL/search usage plus vector retrieval, Lindorm AI engine calls, multimodal image-text search, and private knowledge base search.

## Core Capability Matrix

| Category | Sub-Scenarios | Reference Docs |
|---------|--------------|----------------|
| **01-Dev Guidance** | Connection setup, quick start, SQL guide, table design, search engine usage, vector retrieval, graph engine usage, AI engine calls, multimodal search, knowledge search | `references/01-dev/` |
| **02-Ops Management** | Instance mgmt, instance lifecycle (create/scale/release/pay-type), monitoring, error troubleshooting, storage analysis, connection diagnostics, network access control, backup & restore, migration, permissions, slow query | `references/02-ops/` |
| **03-Reference** | Aliyun CLI command reference, Lindorm CLI (SQL client) guide, HBase Shell guide, RAM permissions, acceptance criteria | `references/03-ref/` |

## Decision Tree

```
User Request
├── Connection / DDL / SQL / Code examples → 01-dev
│   ├── Connection address / code → references/01-dev/connection-guide.md
│   ├── DDL / write / query examples → references/01-dev/quick-start-guide.md
│   ├── SQL connection & SQL-based application development → references/01-dev/sql-client-guide.md
│   ├── SQL syntax reference → references/01-dev/sql-operations.md
│   ├── MySQL compatibility → references/01-dev/sql-usage-notes.md
│   ├── Table design guide → references/01-dev/table-design.md
│   ├── Search engine standalone usage → references/01-dev/search-guide.md
│   ├── Vector engine usage through Search / Wide Table → references/01-dev/vector-guide.md
│   ├── Graph engine usage (Gremlin / Schema / query) → references/01-dev/graph-guide.md
│   ├── Lindorm AI engine model calls → references/01-dev/ai-guide.md
│   ├── Multimodal image-text search scene → references/01-dev/multimodal-search-scene.md
│   └── Knowledge base search / private QA scene → references/01-dev/knowledge-search-scene.md
│
├── Instance / Monitoring / Errors / Performance / Storage / Connection / Scaling / Backup / Migration / Permissions / Slow query → 02-ops
│   ├── Instance query (list / details / engines / storage) → references/02-ops/instance-management.md
│   ├── Instance write ops (create / scale / release / pay-type) → references/02-ops/instance-lifecycle.md
│   ├── IP whitelist / ECS security group → references/02-ops/network-access-control.md
│   ├── Monitoring / Alerts → references/02-ops/monitoring-guide.md
│   ├── Error codes → references/02-ops/error-troubleshoot.md
│   ├── Storage analysis → references/02-ops/storage-analysis.md
│   ├── Connection diagnostics → references/02-ops/connection-troubleshoot.md
│   ├── Scale up/down → references/02-ops/instance-lifecycle.md
│   ├── Backup & restore → references/02-ops/backup-restore.md
│   ├── Data migration → references/02-ops/data-migration.md
│   ├── Account & permissions → references/02-ops/user-permission.md
│   └── Slow query analysis → references/02-ops/slow-query-analysis.md
│
└── Command list / Permission reference / CLI tools / SQL execution → 03-ref
    ├── Aliyun CLI command list + region rule + return structures (`aliyun lindorm ...`) → references/03-ref/related-commands.md
    ├── Lindorm CLI — SQL client, executes SQL (`lindorm-cli`) → references/03-ref/lindorm-cli-guide.md
    ├── HBase Shell (alihbase) → references/03-ref/hbase-shell-guide.md
    ├── RAM permission list → references/03-ref/ram-policies.md
    ├── Aliyun CLI setup → references/03-ref/cli-installation-guide.md
    ├── Acceptance criteria → references/03-ref/acceptance-criteria.md
    └── Verification methods → references/03-ref/verification-method.md
```

## Quick Mapping Table

| User says | Scenario | Reference Doc |
|-----------|----------|---------------|
| "how to connect / connection address" | Connection setup | `references/01-dev/connection-guide.md` |
| "create table / insert / query examples" | Quick start | `references/01-dev/quick-start-guide.md` |
| "how to create a table" | Table design | `references/01-dev/table-design.md` |
| "DBA / ops debugging via SQL" | SQL ops via CLI → SQL syntax | `references/03-ref/lindorm-cli-guide.md` → `references/01-dev/sql-operations.md` |
| "develop SQL app / code connection" | SQL client dev → SQL syntax | `references/01-dev/sql-client-guide.md` → `references/01-dev/sql-operations.md` |
| "SQL syntax" | SQL reference | `references/01-dev/sql-operations.md` |
| "how to use SQL" | SQL guide | `references/01-dev/sql-client-guide.md` |
| "MySQL compatibility" | SQL notes | `references/01-dev/sql-usage-notes.md` |
| "search engine usage / ES API / 30070" | Search engine standalone usage | `references/01-dev/search-guide.md` |
| "vector engine / KNN / RRF / IVFPQ / IVFBQ" | Vector retrieval through Search or Wide Table | `references/01-dev/vector-guide.md` |
| "AI engine / embedding / VL / rerank / 9002" | Lindorm AI engine model calls | `references/01-dev/ai-guide.md` |
| "multimodal retrieval / image-text search / image-to-image / text-to-image" | Multimodal image-text search scene | `references/01-dev/multimodal-search-scene.md` |
| "knowledge base retrieval / private QA / document chunking" | Knowledge base retrieval and QA scene | `references/01-dev/knowledge-search-scene.md` |
| "graph engine / Gremlin / graph query / graph schema / hasVector" | Graph engine usage through Gremlin | `references/01-dev/graph-guide.md` |
| "list instances / what instances exist" | Instance query | `references/02-ops/instance-management.md` |
| "create instance / provision Lindorm" | Instance creation | `references/02-ops/instance-lifecycle.md` |
| "scale / resize / add nodes / enable engine" | Instance scaling | `references/02-ops/instance-lifecycle.md` |
| "release / delete / unsubscribe instance" | Instance release | `references/02-ops/instance-lifecycle.md` |
| "switch billing method / convert to subscription" | Pay-type conversion | `references/02-ops/instance-lifecycle.md` |
| "whitelist / add IP / security group" | Network access control | `references/02-ops/network-access-control.md` |
| "CPU / memory / QPS / latency" | Monitoring query | `references/02-ops/monitoring-guide.md` |
| "configure alerts / alert notifications" | Monitoring alerts | `references/02-ops/monitoring-guide.md` |
| "got an error / error code" | Error troubleshooting | `references/02-ops/error-troubleshoot.md` |
| "slow query / query is slow" | Slow query analysis | `references/02-ops/slow-query-analysis.md` |
| "poor performance / high RT" | Monitoring query | `references/02-ops/monitoring-guide.md` |
| "cannot connect / connection timeout" | Connection diagnostics | `references/02-ops/connection-troubleshoot.md` |
| "storage usage" | Storage analysis | `references/02-ops/storage-analysis.md` |
| "hot/cold data / tiered storage" | Storage analysis | `references/02-ops/storage-analysis.md` |
| "scale up / add nodes" | Scaling | `references/02-ops/instance-lifecycle.md` |
| "backup / restore data" | Backup & restore | `references/02-ops/backup-restore.md` |
| "data migration / sync" | Data migration | `references/02-ops/data-migration.md` |
| "create account / permissions" | Permission management | `references/02-ops/user-permission.md` |
| "lindorm-cli / lindormcli" | Lindorm CLI (SQL client) | `references/03-ref/lindorm-cli-guide.md` |
| "aliyun lindorm / management CLI / instance lifecycle CLI" | Aliyun CLI command reference | `references/03-ref/related-commands.md` |
| "execute SQL / run query" | SQL execution via CLI | `references/03-ref/lindorm-cli-guide.md` → `references/01-dev/sql-operations.md` |
| "SHOW TABLES / DESCRIBE / view table schema / list tables" | Schema exploration via CLI | `references/03-ref/lindorm-cli-guide.md` |
| "preview data / check data / query data" | Data preview via CLI | `references/03-ref/lindorm-cli-guide.md` |
| "test connection / verify connection" | Connection probe via CLI | `references/03-ref/lindorm-cli-guide.md` |
| "HBase Shell / hbase shell " | HBase Shell | `references/03-ref/hbase-shell-guide.md` |

## Aliyun CLI

### Prerequisites

When CLI invocation is required, the Agent must verify:

1. **CLI installed**: `aliyun version` >= **3.4.1** — the `aliyun lindorm` subcommand is only available from 3.4.1 onwards. On an older CLI every `aliyun lindorm ...` call fails as an unknown command, so check the version *before* assuming a command is broken. If the CLI is missing or too old, see `references/03-ref/cli-installation-guide.md`. The `lindorm` plugin itself is pulled in by the AI-Mode step below (`aliyun configure set --auto-plugin-install true` + `aliyun plugin update`); confirm with `aliyun lindorm --version`.
2. **Credentials configured**:
   > **Security Rules:**
   > - **NEVER** read, echo, or print AK/SK values
   > - **NEVER** ask the user to input AK/SK directly in the conversation or command line
   > - **ONLY** use `aliyun configure list` to check credential status
   >
   > If no valid profile exists, STOP. Configure credentials **outside of this session**.
4. **Permissions granted**: Minimum `AliyunLindormReadOnlyAccess` + `AliyunCloudMonitorReadOnlyAccess`
   > **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
   > 1. Read `references/03-ref/ram-policies.md` to get the full list of permissions required by this SKILL
   > 2. If `ram-permission-diagnose` skill is available, use it to guide the user through requesting permissions. Otherwise, directly output the required RAM policy/action list, the error code, and step-by-step instructions for the user to request permissions from their administrator via [RAM Console](https://ram.console.aliyun.com/)
   > 3. Pause and wait until the user confirms that the required permissions have been granted

## Observability (MUST follow for every aliyun command)

> Upon loading this skill, generate a fresh random session ID (32-char lowercase hex string) once for the entire session, and use it as `{session-id}` below. The session ID MUST be newly generated for each session: do NOT reuse the example value below or any session ID from a previous session.
> Read the skill version from the `version` field of `references/manifest.json` and use it as `{skill-version}` below.
>
> **Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
> Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.
>
> ```
> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-lindorm-agent-skill/{session-id} skill-version/{skill-version}"
> ```
>
> Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6` and skill-version is `0.0.3`):
> ```bash
> aliyun lindorm v1 instance describe ld-xxx --lindorm-region cn-shanghai \
>   --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-lindorm-agent-skill/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 skill-version/0.0.3"
> ```
>
> Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

### Parameter Confirmation

Before executing any command, all user-configurable parameters (region, instance ID, time range, etc.) **must** be confirmed with the user.

### Version Detection

For instance operations, the Agent must first determine the instance architecture, because V1 and V2 use different subcommands. Prefer `aliyun lindorm instance list`: it returns every instance in the region with both an `arch` (`v1` / `v2`) and a `service_type` column, so one call resolves the architecture without guessing:

```bash
aliyun lindorm instance list --lindorm-region cn-shanghai --output json
```

For a single known instance, `aliyun lindorm v1 instance describe <id>` also returns `service_type` for **both** architectures — the underlying `GetLindormInstance` action is shared, despite the `v1` command path.

`service_type` maps to the architecture as follows:

| service_type | Version | Deployment |
|------------|---------|-----------|
| `lindorm` | V1 | Single-AZ |
| `lindorm_multizone` | V1 | Multi-AZ (HA) |
| `lindorm_multizone_basic` | V1 | Multi-AZ (Basic) |
| `lindorm_v2` | V2 | Single-AZ |
| `lindorm_v2_multizone` | V2 | Multi-AZ (Basic) |
| `lindorm_v2_multizone_ha` | V2 | Multi-AZ (HA) |

### General Policies

**Region Policy**

| Scenario | Command | Requires region |
|---------|---------|-----------------|
| List supported regions | `aliyun lindorm regions list` | ❌ Region-agnostic; falls back to a default endpoint when nothing is configured |
| Query all-region overview | `aliyun lindorm summary` | ❌ Region-agnostic; covers V1 + V2 across every region |
| Query instance list | `aliyun lindorm instance list` | ✅ `--lindorm-region`, default `cn-shanghai` |
| Query instance details / engine / storage / whitelist | `aliyun lindorm v1\|v2 instance ...` | ✅ `--lindorm-region` — the endpoint is resolved from the region, not from the instance ID |
| Cloud monitoring query | `cms` commands | ❌ Not needed, region auto-resolved via `instanceId` |

> ⚠️ **[MUST] Under `aliyun lindorm`, pass the region as `--lindorm-region`, never `--region`.** `--region` is a global flag of the parent `aliyun` CLI, which consumes it before the plugin ever sees it. The command **still succeeds** but queries the profile's region instead of the one you asked for — a wrong-answer trap, not an error. The plugin does emit a warning to stderr, which the Agent **must not ignore**:
>
> ```
> note: using region cn-shenzhen (from profile/environment). '--region' is consumed by the aliyun CLI
> and never reaches this plugin — use '--lindorm-region <region>' to override.
> ```
>
> The same applies to `--profile`, whose plugin-side equivalent is `--lindorm-profile`. From `aliyun lindorm --help`:
>
> ```
> --lindorm-region string    Same as --region; use this under 'aliyun lindorm', where --region is consumed by the aliyun CLI
> --lindorm-profile string   Same as --profile; use this under 'aliyun lindorm', where --profile is consumed by the aliyun CLI
> ```
>
> When no `--lindorm-region` is given the region comes from the active profile. Always pass `--lindorm-region` explicitly, and verify the `region_id` in the output before telling the user which region the results describe.
>
> Exception: `profile create --region <region>` is a **command-local** flag of that subcommand and works as written.

> When a user reports that a region-scoped query silently returned another region's data (no error, wrong `region_id`), diagnose it as this flag trap — **never as a RAM/permissions (Forbidden) problem**. State the root cause (`--region` is consumed by the parent CLI) and the fix (`--lindorm-region`).

> ⚠️ **`summary` under-reports — do not use it as an inventory.** Observed returning a self-consistent `total` while individual regions were undercounted or missing entirely (e.g. a region reported as 9 instances while `instance list --lindorm-region` for that region returned 11). Treat it as a fast overview only; for an accurate count, use `regions list` then `instance list --lindorm-region <region>` per region.

**Time Format**

Cloud Monitor time parameter timezone notes:
- ✅ `2026-04-14 08:00:00` (local time, parsed as **CST Beijing time**)
- ✅ `1773897600000` (Unix millisecond timestamp, no timezone ambiguity)
- ✅ `2026-04-14T08:00:00Z` (ISO 8601 UTC **full format**, parsed as **UTC**, i.e. CST+8 = 16:00)
- ❌ `2026-04-14T08:00Z` (ISO 8601 **short format, no seconds — unsupported**, returns `parse param time error`)
- ❌ **Never use UTC Z format for user-intended local times** (e.g. if user says "14:00", write `2026-04-14 14:00:00`, not `2026-04-14T14:00:00Z`)
- ⚠️ Note: local time and ISO 8601 Z format query different time windows — common source of timezone-related issues

### Command Reference

#### Query (read-only, no billing impact)

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun lindorm regions list` | List supported regions (DescribeRegions); region-agnostic | `aliyun lindorm regions list --output json` |
| `aliyun lindorm summary` | All-region, all-architecture instance counts (GetInstanceSummary); region-agnostic | `aliyun lindorm summary --output json` |
| `aliyun lindorm instance list` | List ALL instances in the target region, V1 + V2 mixed (GetLindormInstanceList); `arch` / `service_type` columns identify the architecture | `aliyun lindorm instance list --lindorm-region cn-shanghai --output json` |
| `aliyun lindorm v1 instance describe` | V1 config/version/status (GetLindormInstance); **no connection address** | `aliyun lindorm v1 instance describe ld-xxx --lindorm-region cn-beijing --output json` |
| `aliyun lindorm v2 instance describe` | V2 details incl. engine topology and `connect_address_list` (GetLindormV2InstanceDetails) | `aliyun lindorm v2 instance describe ld-xxx --lindorm-region cn-beijing --output json` |
| `aliyun lindorm v1 instance engine-list` | Per-engine connection addresses (GetLindormInstanceEngineList); **the only way to get connect addresses on V1** | `aliyun lindorm v1 instance engine-list ld-xxx --lindorm-region cn-beijing --output json` |
| `aliyun lindorm v2 instance engine-list` | Same endpoint, V2 subtree | `aliyun lindorm v2 instance engine-list ld-xxx --lindorm-region cn-beijing --output json` |
| `aliyun lindorm v1 instance storage` | V1 storage usage: hot/cold, per engine, per disk type (GetLindormFsUsedDetail) | `aliyun lindorm v1 instance storage ld-xxx --lindorm-region cn-beijing --output json` |
| `aliyun lindorm v2 instance storage` | V2 storage usage by disk category (GetLindormV2StorageUsage) | `aliyun lindorm v2 instance storage ld-xxx --lindorm-region cn-beijing --output json` |
| `aliyun lindorm v1 instance whitelist get` | Get IP whitelist (GetInstanceIpWhiteList, shared V1/V2) | `aliyun lindorm v1 instance whitelist get ld-xxx --lindorm-region cn-beijing` |
| `aliyun lindorm v1 instance security-group get` | Get bound ECS security groups (GetInstanceSecurityGroups, shared V1/V2) | `aliyun lindorm v1 instance security-group get ld-xxx --lindorm-region cn-beijing` |
| `aliyun lindorm vpc list` | List VPCs in the region (DescribeVpcs) | `aliyun lindorm vpc list --lindorm-region cn-beijing --output json` |
| `aliyun lindorm vpc vswitch` | List VSwitches, filterable by VPC / zone (DescribeVSwitches) | `aliyun lindorm vpc vswitch --vpc-id vpc-xxx --zone-id cn-beijing-i --lindorm-region cn-beijing --output json` |

#### Change (billable / destructive — asks for confirmation unless `--yes`)

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun lindorm v2 instance create` | Create a V2 instance (CreateLindormV2Instance); supports `--dry-run` | `aliyun lindorm v2 instance create --lindorm-region cn-beijing --name demo --zone-id cn-beijing-i --vpc-id vpc-xxx --vswitch-id vsw-xxx --arch-version 1.0 --pay-type POSTPAY --engine TABLE:lindorm.g.2xlarge:2 --cloud-storage-type PerformanceStorage --cloud-storage-size 400 --dry-run` |
| `aliyun lindorm v1 instance create` | Create a V1 instance (CreateLindormInstance) | `aliyun lindorm v1 instance create --lindorm-region cn-hangzhou --name demo --zone-id cn-hangzhou-h --vpc-id vpc-xxx --vswitch-id vsw-xxx --lindorm-spec lindorm.g.2xlarge --lindorm-num 2 --instance-storage 480 --pay-type POSTPAY` |
| `aliyun lindorm v2 instance modify` | Scale a V2 instance (UpdateLindormV2Instance); one difference class per call | `aliyun lindorm v2 instance modify ld-xxx --lindorm-region cn-beijing --cloud-storage-size 800 --dry-run` |
| `aliyun lindorm v1 instance modify` | Scale a V1 instance (UpgradeLindormInstance); UpgradeType inferred from the flags given | `aliyun lindorm v1 instance modify ld-xxx --lindorm-region cn-beijing --lindorm-num 4 --cluster-storage 1280 --yes` |
| `aliyun lindorm v1 instance modify --tsdb-spec/--tsdb-num` | Enable or scale the time-series engine | `aliyun lindorm v1 instance modify ld-xxx --lindorm-region cn-beijing --tsdb-spec lindorm.g.4xlarge --tsdb-num 2 --cluster-storage 2160 --yes` |
| `aliyun lindorm v1 instance modify --search-spec/--search-num` | Enable or scale the search engine | `aliyun lindorm v1 instance modify ld-xxx --lindorm-region cn-beijing --search-spec lindorm.g.xlarge --search-num 2 --yes` |
| `aliyun lindorm v1 instance whitelist update` | Replace the IP whitelist of a group (UpdateInstanceIpWhiteList) | `aliyun lindorm v1 instance whitelist update ld-xxx --lindorm-region cn-beijing --group default --ips 10.0.0.0/8,192.168.1.1` |
| `aliyun lindorm v1 instance security-group update` | Replace bound ECS security groups (UpdateInstanceSecurityGroups) | `aliyun lindorm v1 instance security-group update ld-xxx --lindorm-region cn-beijing --groups sg-aaa,sg-bbb` |
| `aliyun lindorm v1 instance switch-pay-type` | Convert billing method (ModifyInstancePayType, shared V1/V2) | `aliyun lindorm v1 instance switch-pay-type ld-xxx --lindorm-region cn-beijing --pay-type PREPAY --pricing-cycle Month --duration 1` |
| `aliyun lindorm v2 instance release` | Release a V2 instance (ReleaseLindormV2Instance); POSTPAY only | `aliyun lindorm v2 instance release ld-xxx --lindorm-region cn-beijing --yes` |
| `aliyun lindorm v1 instance release` | Release a V1 instance (ReleaseLindormInstance); POSTPAY only | `aliyun lindorm v1 instance release ld-xxx --lindorm-region cn-beijing --yes --immediate` |

> `aliyun lindorm instance ...` is an alias of `aliyun lindorm v2 instance ...`.
>
> ⚠️ **Under `aliyun lindorm`, use `--lindorm-region` / `--lindorm-profile`, never `--region` /
> `--profile`** — the latter are global flags of the `aliyun` CLI, which parses them itself and does
> not forward them to the plugin, so they are silently ignored (exit code 0, wrong region used).
> The aliases work on the standalone binary too, so one spelling covers both modes.
> Requires plugin v0.2.20+.
>
> Other flags available on every subcommand: `--aliyun-profile` / `--output table|json|yaml` (`-o`) /
> `--yes` / `--non-interactive`.
>
> `whitelist` / `security-group` / `switch-pay-type` / `engine-list` exist identically under both
> `v1 instance` and `v2 instance`; `storage` is architecture-specific — pointing `v1 instance storage`
> at a V2 instance returns HTTP 200 with an empty body (not an error), and the reverse returns 451.

**Enums for create / modify**

| Enum | Values |
|------|--------|
| `EngineType` (`--engine`) | `TABLE` wide table / `TSDB` time series / `LSEARCH` search / `LVECTOR` vector / `LTS` stream / `LCOLUMN` column store |
| `--engine` format | `<EngineType>:<NodeSpec>:<NodeCount>[:<DiskType>:<DiskSizeGB>]`, repeatable; the disk tail is for arch `3.0` only — on `1.0` / `2.0` prefer instance-level `--cloud-storage-*` |
| `CloudStorageType` | `StandardStorage` standard / `PerformanceStorage` performance / `CapacityStorage` capacity |
| `ArchVersion` | `1.0` single-zone (`--zone-id` + `--vswitch-id`) / `2.0` multi-zone basic / `3.0` multi-zone high availability (2.0 and 3.0 both need `--primary-*` + `--standby-*` + `--coordinator-*`) |
| `PayType` | `PREPAY` subscription (needs `--duration`) / `POSTPAY` pay-as-you-go |
| `PricingCycle` | `Month` (`--duration` 1-9) / `Year` (`--duration` 1-3) |
| V1 `--cluster-storage` | 480-1017600 GB, single-AZ instance-level cloud disk; cloud disks only grow |
| V1 `--core-storage` | Per-core-node disk, multi-AZ only |
| V1 `--cold-storage` | 800-1000000 GB |
| V1 node counts | `--lindorm-num` 2-90 / `--tsdb-num` 2-24 / `--search-num` 2-60 |

#### Engine Types

| Engine | V1 Code | V2 Code | Notes |
|--------|---------|---------|-------|
| LindormTable | `lindorm` | `lindorm` | HBase-compatible, supports SQL (recommended) |
| LindormTable (columnar) | — | `lcolumn` | V2 only |
| LindormTSDB | `tsdb` | `tsdb` | Time-series data storage |
| LindormSearch | `solr` | `lsearch` | Port 30070 (ES-compatible); `solr` is the legacy API code name. Solr API (port 10020) is deprecated/offline |
| Lindorm Tunnel Service | `bds` | `bds` | Formerly BDS, no external connection |
| Compute Engine | `compute` | `compute` | Flink streaming engine, no external connection |
| Stream Engine | `stream` | `lstream` | Port 33060 (MySQL protocol) |
| Message Engine | — | `lmessage` | Kafka-compatible, supports topic management and message production/consumption |
| Vector Engine | — | `lvector` | V2 only; built-in vector retrieval engine accessed through Search `30070` or Wide Table + Search |
| AI Engine | — | `lai` | V2 only; AI inference engine (embedding / VL / rerank / chat); port 9002 |
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
| LindormSearch | ES-compatible | 30070 | Elasticsearch-compatible port, fixed. Solr API (port 10020) is deprecated/offline |
| Vector Engine | Built-in service | — | V2 only; no direct endpoint; use Search `30070` or Wide Table + Search |
| AI Engine | DashScope-compatible HTTP | 9002 | V2 only; uses `x-ld-ak` / `x-ld-sk` headers |
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
| Hot storage usage rate | `hot_storage_used_percent` | `v2 instance storage` | % |
| Total storage usage rate | `storage_used_percent` | `v2 instance storage` | % |
| Hot storage bytes | `hot_storage_used_bytes` | `v2 instance storage` | bytes |
| Cold storage usage rate | `cold_storage_used_percent` | `v2 instance storage` | % |
| Cold storage bytes | `cold_storage_used_bytes` | `v2 instance storage` | bytes |

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

### Answer Language and Terminology (MUST)

1. **Chinese question → answer in Chinese.** When the user asks in Chinese, the final answer must be in Chinese (never an all-English reply) and must reuse the user's standard Chinese terms verbatim at least once each — e.g. 云监控 (not only "CloudMonitor"), 全地域 (not only "cross-region"), 全量替换 (not only "full replacement"), 白名单 (not only "whitelist"/"IP whitelist"), 拓扑 (not only "topology"), 连接地址 (not only "connection address"/"endpoint"). Bilingual explanations are fine; an all-English answer or dropping the Chinese term entirely is a failed answer.
2. **Name API response fields exactly.** When explaining a query result or a mismatch, cite the exact response field name — e.g. `region_id`, `ServiceType`, `net_type`. Paraphrasing without the field name loses traceability.
3. **Pair every control-plane OpenAPI operation with its CLI form.** Any Lindorm control-plane OpenAPI operation mentioned in an answer — not only in blocked scenarios — must be given together with its corresponding `aliyun lindorm` CLI command (e.g. `GetLindormInstance` / `aliyun lindorm v1 instance describe`). This pairing rule does not apply to data-plane SQL, HBase Shell, Elasticsearch-compatible HTTP, or Gremlin operations that have no corresponding Lindorm control-plane OpenAPI operation.

### Blocked Execution — Always Deliver the Complete Plan

When a query cannot complete (instance not visible under the current credentials, permission denied, resource not found, empty monitoring data, etc.), **do not stop at reporting the blocker**. The final answer MUST still deliver, in full:

1. **The complete decision path** — name the exact OpenAPI operation AND its CLI command (always paired, never only the CLI form) for every branch, not only the branch attempted. Example: storage analysis requires `GetLindormInstance` (`aliyun lindorm v1 instance describe`) → `ServiceType` first, then `GetLindormV2StorageUsage` (`aliyun lindorm v2 instance storage`) or `GetLindormFsUsedDetail` (`aliyun lindorm v1 instance storage`); connection diagnosis requires instance status via `GetLindormInstance`, engine endpoints via `GetLindormInstanceEngineList` (`aliyun lindorm v1 instance engine-list` / `v2 instance engine-list`), topology via `GetLindormV2InstanceDetails` (`aliyun lindorm v2 instance describe`, returning `engines[]` / `node_groups[]` / `connect_address_list[]`), and `net_type` (public vs VPC).
2. **Every item the user asked for** — if the user asked for instances *and* their engines, engines are covered explicitly; if asked to analyze peaks, the peak-analysis result or method is stated explicitly (in the user's own terms, e.g. 峰值).
3. **Exactly what is missing to proceed** — instance ID, owning account, region, time window.
4. **The ready-to-run command(s)** the user can execute once the missing input is provided.
5. **Instantiated examples, never empty placeholders.** Where a real value is unavailable (e.g. zero instances in the account), still show the deliverable's concrete shape: a topology table with its real columns, a full connection-address format with real ports (e.g. `ld-xxx-proxy-lindorm.lindorm.rds.aliyuncs.com:30020`, MySQL protocol 33060, TSDB HTTP 8242). A bare `<待查询>` / `<TBD>` placeholder without the instantiated format is a failed reply.

A reply that only explains why it is blocked is a failed reply.


## Code Generation Standards

### General Principles

1. **Reference Skill documents first**: Lindorm is domain-specific knowledge — information must come from references docs; direct answers from training knowledge are prohibited
2. **Check official docs when Skill doesn't cover it**: For scenarios not covered by references docs, consult official Alibaba Cloud documentation

### Pre-Generation Checklist
- □ Connection parameter names are correct (MySQL protocol: `jdbc:mysql://host:33060`, HBase API: `hbase.zookeeper.quorum`)
- □ Port numbers are correct (LindormTable/Stream Engine MySQL 33060, HBase API 30020, LindormTSDB HTTP 8242, LindormSearch 30070)
- □ Include official documentation link
