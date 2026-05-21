---
name: alibabacloud-tair-devtoolset
description: |
  Alibaba Cloud Tair development toolkit — 7 capabilities covering architecture selection, data structure design, instance creation & configuration, connection management, performance monitoring, error troubleshooting, and backup & recovery.
  Executes real cloud operations via aliyun CLI (creating instances, modifying whitelists, managing backups, restoring data). Restore operations are high-risk and will overwrite current data. Ensure the RAM account has required permissions (see references/ram-policies.md).
  Triggers: "tair", "create tair instance", "tair instance", "redis", "data structure", "backup", "PITR", "tair architecture", "tair connection", "tair error".
---

# Tair DevToolset — Full-Lifecycle Tair Development Assistant

This Skill provides operational capabilities and development guidelines for **Alibaba Cloud Tair (Redis OSS-Compatible)** database, covering architecture selection, data structure design, instance creation, connection management, performance monitoring, error troubleshooting, and backup & recovery.

> **Note:** This Skill executes real cloud operations via aliyun CLI. Restore operations are high-risk and will overwrite current data. Ensure the RAM account has the [required permissions](references/ram-policies.md) before use.

### Supported Capabilities

| Capability | Description |
|------------|-------------|
| Architecture Selection | Choose the right Tair architecture (Standard vs Cluster) and edition (Memory-optimized, Persistent memory, Disk-based) |
| Data Structure Design | Select optimal Redis and Tair extended data structures for your use case |
| Instance Creation | Create and configure Tair instances via aliyun CLI |
| Connection Management | Connect via standalone/proxy/cluster modes with TLS support |
| Performance Monitoring | Intelligent diagnostics via alibabacloud-tair-ai-assistant skill |
| Error Troubleshooting | Diagnose and resolve common Tair connection, cluster, memory, and client errors |
| Backup and Recovery | Configure backup policies, perform PITR, and restore data |

---

# Part I — Cross-Cutting Concerns

## 1. Prerequisites

### 1.1 CLI Installation & Version

**Aliyun CLI >= 3.3.3 required.** Run `aliyun version` to verify. If not installed or version too low, see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

```bash
# Enable automatic plugin installation (required for r-kvstore plugin)
aliyun configure set --auto-plugin-install true

# Update existing plugins to latest version
aliyun plugin update

# Verify jq is installed (required for JSON parsing in scripts)
jq --version
```

### 1.2 Authentication

All credential configurations follow existing aliyun CLI settings.

**Security Rules:**
- **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
- **NEVER** ask the user to input AK/SK directly in the conversation or command line
- **NEVER** use `aliyun configure set` with literal credential values
- **ONLY** use `aliyun configure list` to check credential status

```bash
aliyun configure list
```

**If no valid profile exists, STOP here.** Configure credentials outside of this session, then return.

### 1.3 AI-Mode Configuration

> **[MUST] Enable AI-Mode at the start** of any workflow (before any CLI invocation):
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-tair-devtoolset"
> ```

> **[MUST] Disable AI-Mode at EVERY exit point** — before delivering the final response for ANY reason (success, failure, error, user cancellation, etc.). AI-mode MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

## 2. Security & Compliance

### 2.1 User-Agent Requirement

Every `aliyun` CLI command invocation must include:
```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-devtoolset
```

### 2.2 RAM Permissions

This Skill requires R-KVStore RAM permissions for instance management, backup, and recovery operations. See [references/ram-policies.md](references/ram-policies.md) for the full permission table and policy document.

> **[MUST] Permission Failure Handling:** When any command fails due to permission errors:
> 1. Read `references/ram-policies.md` to get the full list of required permissions
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 3. Parameter Confirmation Rule

Before executing any command or API call, ALL user-customizable parameters (e.g., RegionId, instance names, passwords, resource specifications) **MUST be confirmed with the user**. Do NOT assume or use default values without explicit user approval.

---

# Part II — Capabilities

## 4. Architecture Selection

Choose the right Tair architecture based on data volume, throughput requirements, and read/write ratio.

### When to Use

- Deciding between Standard and Cluster architecture
- Determining whether read/write splitting is needed
- Selecting edition type (Memory-optimized, Persistent memory, Disk-based)
- Evaluating Tair vs Open Source Redis for a new project

### Key Guidance

**Key Concepts:**

| Component | Description |
|-----------|-------------|
| Node | Smallest unit, runs Redis-compatible process |
| Shard | Group of nodes storing a subset of data |
| Master node | Handles write operations |
| Replica node | Copy of master, provides failover |
| Read-only node | Serves read traffic only (read/write splitting) |
| Proxy node | Routes requests to appropriate nodes |

**Architecture Comparison:**

| Dimension | Standard | Cluster |
|-----------|----------|---------|
| Structure | One master + replicas | Multiple shards, each with master + replicas |
| Data partitioning | No (single shard) | Yes (distributed across shards) |
| Best for | Small data, stable QPS | Large data, high QPS, throughput-intensive |
| Read/write splitting | Supported | Supported |

**Selection Decision Tree:**

```
Data volume > single-node capacity?
├── Yes → Cluster architecture
│   └── Read-heavy? → Enable read/write splitting
└── No → Standard architecture
    └── Read-heavy? → Enable read/write splitting
```

### References

- [references/architecture-selection/arch-selection.md](references/architecture-selection/arch-selection.md) — Architecture selection decision guide
- [references/architecture-selection/arch-compare-oss-redis.md](references/architecture-selection/arch-compare-oss-redis.md) — Tair vs Open Source Redis comparison and edition selection

---

## 5. Data Structure Design

Choose the appropriate data structure based on your access patterns and business requirements.

### When to Use

- Selecting data structures for a new feature or application
- Choosing between Redis native and Tair extended data structures
- Migrating data models and evaluating structure alternatives

### Key Guidance

**Redis Data Structures:**

| Name | Use Case |
|------|----------|
| String | Caching, counters, distributed locks, session storage, rate limiting |
| Hash | Object storage (user profiles, product info), grouped field-value pairs |
| List | Message queues, latest feeds, task queues, stack/queue operations |
| Set | Unique collections, tagging, social graph (followers/friends), set operations |
| Sorted Set | Leaderboards, ranking systems, priority queues, range queries by score |
| Stream | Event sourcing, log streaming, message queues with consumer groups |
| Bitmap | Feature flags, online status tracking, daily active user counting |
| Bitfield | Compact counters, fixed-width integer encoding, atomic increment |
| Geospatial | Location-based services, nearby search, geofencing |
| HyperLogLog | Unique visitor counting, cardinality estimation with minimal memory |

**Tair Data Structures:**

| Name | Use Case |
|------|----------|
| exString / TairString (String enhancement) | Versioned strings, bounded INCRBY, CAS/CAD for distributed locks |
| exHash / TairHash (Hash enhancement) | Field-level TTL, field versioning, multi-device login management |
| exZset / TairZset (Zset enhancement) | Multi-dimensional scoring (256 dims), multi-criteria ranking |
| GIS / TairGis (Geospatial enhancement) | Point/line/polygon queries, spatial relationship checks |
| Doc / TairDoc (JSON) | JSON with binary tree indexing, fast sub-element access |
| Search / TairSearch | ES-like full-text search, multi-column index, tokenization |
| TS / TairTs (TimeSeries) | Real-time monitoring, IoT data, two-level timeline aggregation |
| Bloom / TairBloom | Probabilistic membership testing, deduplication, URL filtering |
| Cpc / TairCpc | Compressed cardinality estimation, streaming analytics |
| Roaring / TairRoaring (Bitmap enhancement) | User segmentation, audience targeting, multi-bitmap operations |
| Vector / TairVector | Vector similarity search, LLM Chatbot, multimodal retrieval |

### References

- [references/data-structure-design/data-structure-design.md](references/data-structure-design/data-structure-design.md) — Detailed data structure use case descriptions
- [Redis Data Types](https://redis.io/docs/latest/develop/data-types/)
- [Tair Extended Data Structures](https://help.aliyun.com/zh/redis/developer-reference/extended-data-structures-of-apsaradb-for-redis-enhanced-edition)

---

## 6. Instance Creation

Create and configure Tair instances on Alibaba Cloud, including whitelist configuration and public endpoint allocation.

### When to Use

- Creating a new Tair instance for testing, development, or production
- Configuring network access (whitelist, public endpoint) for an instance
- Setting up a Tair benchmark or PoC environment

### 6.1 Choosing Instance Specifications

**Required Parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| VPC_ID | VPC ID | `vpc-bp1xxx` |
| VSWITCH_ID | VSwitch ID | `vsw-bp1xxx` |

**Optional Parameters (with defaults):**

| Parameter | Default | Description |
|-----------|---------|-------------|
| REGION_ID | `cn-hangzhou` | Region ID |
| ZONE_ID | `cn-hangzhou-h` | Zone ID |
| INSTANCE_TYPE | `tair_rdb` | Instance series: `tair_rdb` (DRAM), `tair_scm` (Persistent memory), `tair_essd` (ESSD disk) |
| INSTANCE_CLASS | `tair.rdb.1g` | Instance specification (see table below) |
| INSTANCE_NAME | `tair-benchmark-<timestamp>` | Instance name |
| CHARGE_TYPE | `PostPaid` | Billing method: `PostPaid` (pay-as-you-go), `PrePaid` (subscription) |

**Common Specifications (Standard Architecture):**

| InstanceClass | Memory | Bandwidth | Max Connections | QPS Reference |
|---------------|--------|-----------|-----------------|---------------|
| tair.rdb.1g | 1 GB | 768 Mbps | 30,000 | 300,000 |
| tair.rdb.2g | 2 GB | 768 Mbps | 30,000 | 300,000 |
| tair.rdb.4g | 4 GB | 768 Mbps | 40,000 | 300,000 |
| tair.rdb.8g | 8 GB | 768 Mbps | 40,000 | 300,000 |
| tair.rdb.16g | 16 GB | 768 Mbps | 40,000 | 300,000 |
| tair.rdb.24g | 24 GB | 768 Mbps | 50,000 | 300,000 |
| tair.rdb.32g | 32 GB | 768 Mbps | 50,000 | 300,000 |
| tair.rdb.64g | 64 GB | 768 Mbps | 50,000 | 300,000 |

### 6.2 Automated Workflow (Script)

For quick end-to-end instance creation with public network access, use the all-in-one script:

> **Execution Constraints:**
> - **MUST** use `scripts/create-and-connect-test.sh` for this workflow — do NOT bypass the script to directly call individual `aliyun r-kvstore` commands
> - **DO NOT** write or concatenate aliyun CLI commands to replace script functionality
> - Model's responsibility: collect parameters → set environment variables → run script

```bash
export VPC_ID="<user-confirmed VPC_ID>"
export VSWITCH_ID="<user-confirmed VSWITCH_ID>"

# Optional parameters
export REGION_ID="cn-hangzhou"
export ZONE_ID="cn-hangzhou-h"
export INSTANCE_TYPE="tair_rdb"
export INSTANCE_CLASS="tair.rdb.1g"
# For NAT environment, manually set public IP
# export MY_PUBLIC_IP="your-public-ip"

bash scripts/create-and-connect-test.sh
```

The script will automatically complete: Create instance → Wait for ready → Configure whitelist → Allocate public endpoint → Get public connection info.

### 6.3 Manual CLI Steps

For custom requirements (PrePaid subscription, no public endpoint, custom security groups, etc.), use manual CLI steps:

**Step 1 — Create instance:**
```bash
aliyun r-kvstore create-tair-instance \
  --biz-region-id "$REGION_ID" --zone-id "$ZONE_ID" \
  --vpc-id "$VPC_ID" --vswitch-id "$VSWITCH_ID" \
  --instance-type "$INSTANCE_TYPE" --instance-class "$INSTANCE_CLASS" \
  --password "$PASSWORD" --charge-type "$CHARGE_TYPE" \
  --shard-type "MASTER_SLAVE" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-devtoolset
```

**Step 2 — Wait for instance ready** (poll until `InstanceStatus` is `Normal`):
```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id "$INSTANCE_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-devtoolset
```

**Step 3 — Configure whitelist:**
```bash
aliyun r-kvstore modify-security-ips \
  --instance-id "$INSTANCE_ID" --security-ips "$MY_PUBLIC_IP" \
  --security-ip-group-name "default" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-devtoolset
```

**Step 4 — Allocate public endpoint:**
```bash
aliyun r-kvstore allocate-instance-public-connection \
  --instance-id "$INSTANCE_ID" \
  --connection-string-prefix "${INSTANCE_ID}pub" --port "6379" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-devtoolset
```

### 6.4 Success Verification

```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id "$INSTANCE_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-devtoolset
```

Confirm `InstanceStatus` is `Normal` and public endpoint is allocated. For the full 3-step verification (instance status, whitelist, public endpoint), see [references/verification-method.md](references/verification-method.md).

### References

- [references/instance-creation/connect-create-instance.md](references/instance-creation/connect-create-instance.md) — End-to-end instance creation and connection guide with redis-cli examples
- [references/related-commands.md](references/related-commands.md) — Complete CLI command and parameter reference
- [references/verification-method.md](references/verification-method.md) — Detailed success verification steps
- [references/acceptance-criteria.md](references/acceptance-criteria.md) — CLI command correctness standards

---

## 7. Connection Management

Connect to Tair instances using various Redis-compatible clients in standalone, proxy, cluster, or TLS modes.

### When to Use

- Connecting to a Tair instance from application code
- Choosing the right client library and connection mode
- Configuring TLS/SSL encryption for secure connections
- Troubleshooting connection issues

### Key Guidance

**Connection Modes:**

| Mode | Architecture | Description |
|------|-------------|-------------|
| Standalone/Proxy | Standard or Cluster (proxy mode) | Connect via proxy node; supports all Redis commands including cross-slot multi-key |
| Cluster Direct | Cluster (direct mode) | Connect directly to data nodes; requires cluster-aware client; cross-slot multi-key commands not supported |
| TLS | Any (overlay) | Encrypt connections with TLS/SSL; supports both Proxy and Direct modes |

**Authentication Format:**
- Default account: password only
- Custom account: `<user>:<password>`
- redis-cli: use `REDISCLI_AUTH` environment variable — `export REDISCLI_AUTH='InstanceID:Password'`

**Supported Clients:** Jedis, Lettuce, Redisson (Java); redis-py (Python); Predis, phpredis (PHP); StackExchange.Redis (.NET); go-redis (Go); node-redis (Node.js); Spring Data Redis

### References

- [references/connection-management/connect-standalone-or-proxy.md](references/connection-management/connect-standalone-or-proxy.md) — Standalone/proxy connection examples in Java, Python, PHP, .NET, Go, Spring Data Redis
- [references/connection-management/connect-cluster.md](references/connection-management/connect-cluster.md) — Cluster connection examples (JedisCluster, RedisCluster, LettuceCluster, go-redis cluster, redis-cli)
- [references/connection-management/connect-with-tls.md](references/connection-management/connect-with-tls.md) — TLS/SSL connection examples for all client types (Proxy + Direct)

---

## 8. Performance Monitoring

Intelligent performance monitoring and diagnostics via the Tair AI Assistant (DAS API).

### When to Use

- Diagnosing slow queries or performance degradation
- Analyzing memory usage and identifying big keys / hotspot keys
- Tuning instance parameters and connection settings
- Monitoring instance health and resource utilization

### Key Guidance

For intelligent diagnostics, install and use the **alibabacloud-tair-ai-assistant** skill:

```bash
npx skills add aliyun/alibabacloud-aiops-skills --skill alibabacloud-tair-ai-assistant --agent <your-agent-platform>
```

The AI Assistant provides natural language based diagnostics covering: instance management, performance analysis, slow queries, memory analysis, big key / hotspot key detection, parameter tuning, and connection troubleshooting.

### References

- [references/performance-monitoring/perf-monitoring.md](references/performance-monitoring/perf-monitoring.md) — Performance monitoring reference
- [alibabacloud-tair-ai-assistant](https://skills.aliyun.com/skills/alibabacloud-tair-ai-assistant)

---

## 9. Error Troubleshooting

Diagnose and resolve common Tair errors across authentication, connection, cluster, memory, proxy, Lua/transactions, and client-specific issues.

### When to Use

- Encountering authentication or connection errors
- Resolving cluster-related errors (cross-slot, moved, read-only)
- Handling memory exhaustion or command errors
- Debugging client-specific issues (Jedis, Lettuce, Redisson, go-redis, etc.)

### Key Guidance

**Common Error Categories:**

| Category | Example Errors | Typical Cause |
|----------|---------------|---------------|
| Authentication | `NOAUTH Authentication required`, `WRONGPASS` | Password not provided, incorrect password, or Lettuce CLIENT SETINFO bug |
| Connection | `ERR illegal address`, `max number of clients reached` | Client IP not in whitelist, connection pool leak, DNS failure |
| Cluster | `CROSSSLOT Keys in request don't hash to the same slot`, `MOVED` | Multi-key command across slots, key moved to another node |
| Memory/Command | `OOM command not allowed`, `WRONGTYPE`, `ERR unknown command` | Memory exceeded, wrong data type, command not supported |
| Proxy Mode | `client ip is not in whitelist`, `redis temporary failure` | Proxy whitelist, sub-instance timeout, request queue overflow |
| Lua/Transaction | `BUSY Redis is busy running a script`, `NOSCRIPT` | Long-running Lua script, script SHA not in cache |
| Client-specific | Jedis `Could not get a resource from the pool`, Lettuce `NOAUTH` with correct password, go-redis cluster format panic | Pool exhaustion, version incompatibility, RESP2/RESP3 mismatch |

### References

- [references/error-troubleshooting/errors-troubleshooting.md](references/error-troubleshooting/errors-troubleshooting.md) — Complete error tables with causes and solutions for all error categories and client libraries
- [Common errors and troubleshooting](https://www.alibabacloud.com/help/en/redis/support/common-errors-and-troubleshooting)

---

## 10. Backup and Recovery

Configure backup policies, create manual backups, restore data from backups, and perform point-in-time recovery (PITR).

### When to Use

- Configuring automatic backup policies
- Creating a manual backup before high-risk operations
- Restoring data from a backup set
- Performing point-in-time recovery (PITR) or key-filtered recovery

### Key Guidance

**Persistence Policies:**

| Policy | Mechanism | Key Feature |
|--------|-----------|-------------|
| RDB | Periodic snapshots | Small files, non-blocking backup |
| AOF | Logs all write operations | Fsync every second by default, AOF rewrite reduces disk usage |
| Tair-Binlog | Incremental AOF archiving (Enterprise DRAM only) | Prevents AOF rewrite degradation, enables PITR accurate to the second |

**Key CLI Operations:**
- `modify-backup-policy` — Modify automatic backup schedule
- `create-backup` — Create a manual backup
- `describe-backups` — Query available backup sets
- `restore-instance` — Restore from backup set or point-in-time
  - Full backup: `--backup-id "$BACKUP_ID"`
  - PITR: `--restore-type 1 --restore-time "2024-01-15T10:30:00Z"`
  - Key-filtered PITR: add `--filter-key "session:*,user:*"`

> **⚠️ HIGH-RISK OPERATION — `restore-instance` overwrites current data and cannot be undone.**
> Before executing any restore:
> 1. **Verify current write traffic** — Check if the instance has active writes; notify the user if so
> 2. **Create a latest backup** — Run `create-backup` to preserve current data as a rollback point
> 3. **Confirm with the user** — Explicitly inform that data will be overwritten and obtain confirmation

### References

- [references/backup-and-recovery/backup-recovery.md](references/backup-and-recovery/backup-recovery.md) — Complete backup/recovery guide with CLI examples and data protection details
- [Data backup and restoration policies](https://www.alibabacloud.com/help/en/redis/user-guide/backup-and-restoration-solutions)

---

# References Index

| Reference | Description | Scope |
|-----------|-------------|-------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide | Cross-cutting |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy document | Cross-cutting |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | CLI command correctness standards | Cross-cutting (QA) |
| [references/related-commands.md](references/related-commands.md) | Complete CLI command and parameter reference | Instance Creation |
| [references/verification-method.md](references/verification-method.md) | Success verification steps | Instance Creation |
| [references/architecture-selection/arch-selection.md](references/architecture-selection/arch-selection.md) | Architecture selection decision guide | Architecture Selection |
| [references/architecture-selection/arch-compare-oss-redis.md](references/architecture-selection/arch-compare-oss-redis.md) | Tair vs Open Source Redis comparison | Architecture Selection |
| [references/data-structure-design/data-structure-design.md](references/data-structure-design/data-structure-design.md) | Detailed data structure use cases | Data Structure Design |
| [references/instance-creation/connect-create-instance.md](references/instance-creation/connect-create-instance.md) | End-to-end instance creation and connection guide | Instance Creation |
| [references/connection-management/connect-standalone-or-proxy.md](references/connection-management/connect-standalone-or-proxy.md) | Standalone/proxy connection examples | Connection Management |
| [references/connection-management/connect-cluster.md](references/connection-management/connect-cluster.md) | Cluster connection examples | Connection Management |
| [references/connection-management/connect-with-tls.md](references/connection-management/connect-with-tls.md) | TLS connection examples (Proxy + Direct) | Connection Management |
| [references/performance-monitoring/perf-monitoring.md](references/performance-monitoring/perf-monitoring.md) | Performance monitoring and diagnostics | Performance Monitoring |
| [references/error-troubleshooting/errors-troubleshooting.md](references/error-troubleshooting/errors-troubleshooting.md) | Complete error tables with causes and solutions | Error Troubleshooting |
| [references/backup-and-recovery/backup-recovery.md](references/backup-and-recovery/backup-recovery.md) | Backup and recovery strategies with CLI examples | Backup and Recovery |
