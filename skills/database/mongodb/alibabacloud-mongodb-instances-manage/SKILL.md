---
name: alibabacloud-mongodb-instances-manage
description: |
  Alibaba Cloud MongoDB full lifecycle management: create/query/scale/delete standalone, replica set, sharded cluster instances.
  Covers node management, security (whitelist/security group), public & SRV address, password reset, renewal, billing conversion, cloud disk reconfiguration, maintenance window.
  Triggers: "MongoDB", "create MongoDB", "dds instance", "list instances", "MongoDB scaling", "add Mongos/Shard node",
  "MongoDB whitelist", "reset password", "allocate public address", "SRV address", "MongoDB renewal",
  "billing type conversion", "cloud disk reconfiguration", "delete MongoDB instance", "maintenance window"
---

# Alibaba Cloud MongoDB Instance Management

Create and manage Alibaba Cloud ApsaraDB for MongoDB instances: Standalone (dev/test), Replica Set (read-heavy), Sharded Cluster (high concurrency).

## Installation Requirements

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify. If needed, see `references/cli-installation-guide.md`.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
aliyun version
aliyun plugin install --names dds kms resourcemanager bssopenapi
```

## Information Display Standards

> **[MUST] All information displayed to the user must comply with:**
>
> 1. **No fabricated output**: All displayed information must come from actual API query results. Speculation, fabrication, or splicing is strictly prohibited
> 2. **Truncation handling**: If API response is truncated (e.g., omitted), must re-query completely before displaying
> 3. **Count validation**: Displayed count must match TotalCount/actual count returned by API
> 4. **No speculative time estimates**: Do not provide time estimates without official documentation basis; only confirm status via API polling
> 5. **Write operation response standard**: After issuing any write operation (create, modify spec, cloud disk reconfiguration, add/delete node, etc.), **only display** `RequestId` (and `DBInstanceId`/`OrderId` if available), then **ask the user whether to poll instance status**. **Do NOT start polling automatically before user confirmation.**
> 6. **Auto-polling rules after instance creation**:
>    - It typically takes **10-25 minutes** for a newly created instance to reach Running status
>    - **Scenario A**: User only creates an instance with no follow-up operations → ask whether to poll
>    - **Scenario B**: User has follow-up operations after creation (e.g., modify spec, configure whitelist, etc.) and **has NOT explicitly stated they will check status manually** → **MUST auto-poll**, querying `describe-db-instance-attribute` every 30 seconds until status is `Running` or timeout (30 minutes)
>    - **Scenario C**: User explicitly states "I'll check myself", "handle it later", etc. → do not auto-poll, handle as Scenario A
> 7. **Security configuration guidance after instance creation**: After instance creation completes (status is Running), **MUST proactively ask** whether to perform security configuration (see security configuration menu in "Parameter Confirmation" section)
> 8. **Subscription instance display**: Must show remaining days; instances expiring within 10 days must display a warning below the list and guide toward renewal

## Instance Status Pre-check Standard

> **[MUST] Must check instance status before executing non-query operations:**
> 1. Call `describe-db-instance-attribute` to check `DBInstanceStatus`
> 2. **Operations can only be issued when status is `Running`**
>
> | Status | Description | Can Issue |
> |--------|-------------|-----------|
> | `Running` | Running | ✅ |
> | `DBInstanceClassChanging` | Changing spec | ❌ |
> | `NodeCreating` / `NodeDeleting` | Creating/Deleting node | ❌ |
> | `Creating` | Creating | ❌ |
> | `Locked` | Locked | ❌ Investigate cause first |
>
> **Locked status diagnosis** (check `LockMode` field):
> - `LockByDiskQuota`: Disk usage exceeded; auto-unlocks after expanding storage or cleaning data
> - Other values: Overdue or expired; renew or recharge
>
> ```bash
> aliyun dds describe-db-instance-attribute --db-instance-id <id> --region <region> \
>   --user-agent AlibabaCloud-Agent-Skills 2>&1 | grep '"DBInstanceStatus"'
> ```

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
> - **NEVER** read/echo/print AK/SK values (do NOT run `echo $ALIBABA_CLOUD_ACCESS_KEY_ID`)
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> If no valid profile exists, obtain credentials from [RAM Console](https://ram.console.aliyun.com/manage/ak) and configure outside this session.

## RAM Permissions

This skill requires the following RAM permissions. See [references/ram-policies.md § Full Permission Quick Reference](references/ram-policies.md) for the complete list.

> **[MUST] Permission error handling:** When detecting `Forbidden.RAM`/`NoPermission`/`Forbidden`/`SubAccountNoPermission`:
> 1. Identify the missing permission (extract Action and Resource from the error message)
> 2. Guide the user to refer to `references/ram-policies.md` to request permissions
> 3. Wait for user confirmation that permission has been granted before retrying; **do NOT continue execution before the permission issue is resolved**

---

## Query Regions and Instances

> **[MUST] Region confirmation standard:**
> 1. When the user has not specified a region, **ask for the region first**; do not iterate and search directly
> 2. Only iterate in the following order when the user explicitly states they are unsure: cn-beijing → cn-shanghai → ap-southeast-1 → us-west-1 → us-east-1 → cn-hangzhou → cn-shenzhen → cn-chengdu → cn-hongkong; if still not found, call `DescribeRegions` to get remaining regions
> 3. **Query routing**: Querying via cn-hangzhou may return instances from other regions; when displaying, RegionId must be based on the `RegionId` field returned by the API, not the query parameter
> 4. **List display**: Must be categorized by instance type; Subscription instances must show remaining days; instances expiring within 10 days must display a warning below the list and guide toward renewal

```bash
# Query instance list (must query separately in two calls, otherwise sharded clusters will be missed)
aliyun dds describe-db-instances --biz-region-id <region> --db-instance-type replicate --page-size 50 --user-agent AlibabaCloud-Agent-Skills
aliyun dds describe-db-instances --biz-region-id <region> --db-instance-type sharding --page-size 50 --user-agent AlibabaCloud-Agent-Skills
# ⚠️ Without --db-instance-type, only replicate is returned by default; sharded clusters will be missed

# Query single instance details
aliyun dds describe-db-instance-attribute --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills

# Query all supported regions
aliyun dds DescribeRegions --user-agent AlibabaCloud-Agent-Skills
```

> Cross-region lookup scripts and full-region scan scripts: see [references/operations.md § Query Regions and Instances](references/operations.md)

## Parameter Confirmation

> **[MUST] Before executing any create/modify operation, must display a complete parameter list to the user and obtain Y/Yes confirmation**

**Workflow:** Collect parameters → Display parameter list → Wait for Y confirmation → Execute → Only display RequestId/DBInstanceId → Ask whether to poll → Display security configuration guidance after completion

**Security configuration guidance menu must be displayed after instance creation:**

```
[0] Set root password         - Cannot connect without password (priority)
[1] Set IP whitelist          - Configure allowed access IPs
[2] Bind ECS security group   - Control access via security group
[3] Associate global whitelist template - Use unified whitelist template
[4] Modify maintenance window - Set maintenance window
[5] Allocate public address   - Enable public access (dev/test only)
[N] Skip
```

> Full parameter confirmation format and required/optional parameter tables: see [references/operations.md § Parameter Confirmation](references/operations.md)

## Core Workflow

| Step | Name | Type | Description |
|------|------|------|-------------|
| 0 | Create resource group | Optional | Execute when resource group management is needed |
| 0.5 | Create KMS instance | Optional | Execute when cloud disk encryption is needed |
| 1 | Query VPC/VSwitch | Optional | Execute when user has not provided VPC |
| 2 | Validate VPC/VSwitch | Required | Ensure VPC/VSwitch are available |
| 3 | Validate zone | Required for standalone | Confirm target zone supports standalone |
| 4 | Parameter confirmation | Required | Must confirm before creation |
| 5 | Create instance | Required | Core operation |
| 6 | Verify creation | Required | Confirm instance creation succeeded |

| Step | Skip Condition |
|------|---------------|
| Create resource group | Using default resource group |
| Create KMS instance | Using default key or no encryption |
| Query VPC/VSwitch | User already provided VPC/VSwitch ID (but validation is still required) |
| Validate zone | Creating replica set or sharded cluster instance |

> **[MUST] Mandatory validation when user provides VPC/VSwitch:**
> Even if the user has provided VPC ID and VSwitch ID, **must first call the following APIs to validate correctness and availability**:
> 1. `describe-rds-vpcs`: Validate whether VPC ID exists and is available
> 2. `describe-rds-vswitchs`: Validate whether VSwitch ID exists in the specified VPC and matches the target zone
> 3. If any validation fails, must inform the user of the specific error and guide correction; **do NOT directly use unvalidated VPC/VSwitch to create instances**

> **[MUST] VPC/VSwitch validation must use DDS-specific APIs; generic VPC APIs (`vpc DescribeVpcs`/`vpc DescribeVSwitches`) are prohibited:**

```bash
# Step 1: Query available VPC list for specified zone (DDS-specific)
aliyun dds describe-rds-vpcs --zone-id <zone> --region <region> --user-agent AlibabaCloud-Agent-Skills

# Step 2: Query available VSwitches under specified VPC (DDS-specific)
aliyun dds describe-rds-vswitchs --vpc-id <vpc-id> --zone-id <zone> --region <region> --user-agent AlibabaCloud-Agent-Skills
```

> Detailed commands and parameters: see [references/operations.md § Step 2: Query and Validate VPC and VSwitch](references/operations.md)

---

## Create Replica Set Instance

> - `--db-instance-class` must be queried via `describe-available-resource` (specs differ by region/zone/version/storage type)
> - `--zone-id` must match the zone of `--vswitch-id`, otherwise `InvalidVpcIdRegion.NotSupported` error
> - Multi-zone deployment requires `--secondary-zone-id` and `--hidden-zone-id`

```bash
aliyun dds create-db-instance \
  --biz-region-id <region> --zone-id <zone> --engine-version <ver> \
  --db-instance-class <class> --db-instance-storage <GB> \
  --vpc-id <vpc> --vswitch-id <vsw> --network-type VPC \
  --replication-factor 3 --storage-type cloud_essd1 --charge-type PostPaid \
  --db-instance-description <name> --user-agent AlibabaCloud-Agent-Skills
# Optional: --secondary-zone-id --hidden-zone-id --readonly-replicas --encryption-key --resource-group-id
# Subscription: --charge-type PrePaid --period 1 --auto-renew true
```

## Create Standalone Instance

> - `--replication-factor 1 --db-type replicate`, storage type fixed to `cloud_essd1`
> - Must use standalone-specific specs (ending with `.1` like `dds.sn2.large.1`, or containing `.single`); cannot use replica set specs
> - Not supported in some regions/zones; must query `describe-available-resource --replication-factor 1` before creation
> - When `InvalidDBInstanceNodeCount` error occurs, try other zones or suggest switching to replica set

```bash
aliyun dds create-db-instance ... --db-type replicate --replication-factor 1 \
  --db-instance-class <standalone-specific-spec> --storage-type cloud_essd1 --user-agent AlibabaCloud-Agent-Skills
```

## Create Sharded Cluster Instance

> - Minimum 2 Mongos and 2 Shards each (max 32); each Shard is a 3-node replica set by default
> - `--mongos` / `--replica-set` parameters need to be repeated (specifying one node each time)
> - Use `--db-type sharding` to query sharded cluster specs (`--db-type normal` is for replica sets only)

```bash
aliyun dds create-sharding-db-instance \
  --biz-region-id <region> --zone-id <zone> --engine MongoDB --engine-version <ver> \
  --vpc-id <vpc> --vswitch-id <vsw> --network-type VPC \
  --mongos Class=<class> --mongos Class=<class> \
  --replica-set Class=<class> ReadonlyReplicas=0 Storage=20 \
  --replica-set Class=<class> ReadonlyReplicas=0 Storage=20 \
  --config-server Class=<class> Storage=20 \
  --storage-type cloud_essd1 --charge-type PostPaid --user-agent AlibabaCloud-Agent-Skills
```

## Instance Creation Error Diagnosis

| Error Code | Solution |
|------------|----------|
| `InvalidDBInstanceNodeCount` | Current region/zone does not support standalone; switch region/zone or use replica set |
| `InvalidVPCId.NotFound` | VPC does not exist; query available VPC list |
| `InvalidZoneId.NotFound` | Zone does not exist; query supported zones |
| `InvalidVpcIdRegion.NotSupported` | zone-id does not match the zone of vswitch-id |
| `QuotaExceeded` | Instance quota exceeded; release idle instances or request quota increase |
| `InvalidDBInstanceClass.NotFound` | Spec does not exist; query available spec list |
| `InvalidDBInstanceStorage` | Storage space invalid (minimum/step not met) |
| `DBInstancePreCheckError` | Pre-check failed; check if instance status is Running |
| `INSUFFICIENT_RESOURCE_ERROR` | Insufficient resources; retry in order: switch zone → switch spec → switch region (max 3 times) |
| `InvalidDbType` | --db-type only supports `normal` or `sharding` |
| `SYSTEM.SALE_VALIDATE_NO_SPECIFIC_CODE_FAILED` | Sales validation failed; switch zone or spec, check account balance |

---

## Modify Replica Set Instance Configuration

> **[MUST] Before modification:**
> 1. Query current configuration (`describe-db-instance-attribute`), extract `DBInstanceStatus`/`DBInstanceClass`/`DBInstanceStorage`/`ReplicationFactor`/`ReadonlyReplicas`/`StorageType`
> 2. Display "Current vs. New" comparison table and obtain user Y confirmation
> 3. **Do NOT execute modification command before user confirmation**
>
> **Limitations:** Storage downsizing, instance type change, and storage type change are not supported (for ESSD conversion, use the Cloud Disk Reconfiguration section)
> **Impact:** Modification may cause 1-2 brief disconnections of ~30 seconds; recommended during off-peak hours
>
> After successful modification command, only display RequestId/OrderId; **do NOT auto-poll**; must ask user for confirmation before starting

```bash
aliyun dds modify-db-instance-spec --db-instance-id <id> \
  [--db-instance-class <class>] [--db-instance-storage <GB>] \
  [--replication-factor 3/5/7] [--readonly-replicas 0-5] \
  [--order-type UPGRADE/DOWNGRADE] [--auto-pay true] \
  --effective-time Immediately/MaintainTime --user-agent AlibabaCloud-Agent-Skills
```

> Full parameter description: see [references/operations.md § Modify Replica Set Instance](references/operations.md)

## Delete Instance

> **[MUST]** Must confirm billing type before deletion:
> - `PostPaid` (Pay-As-You-Go): Can be deleted directly
> - `PrePaid` (Subscription): **Cannot be deleted directly**; must wait for expiration or request refund via console
>
> Before deletion, must display confirmation information to the user (instance ID, region, billing type, irreversible data loss warning), requiring the user to reply "confirm delete {instance ID}"

```bash
aliyun dds DeleteDBInstance --DBInstanceId <id> --region <region> --user-agent AlibabaCloud-Agent-Skills
```

---

## Sharded Cluster Node Management

> **[MUST] Key limitations:**
> - Must retain at least 2 Mongos/Shards each, max 32
> - New Shard configuration (spec + storage) must be ≥ the highest-configured existing Shard
> - `modify-node-spec` **strictly serial**: must wait for previous modification to complete (`Running`) before issuing the next
> - Batch modification `modify-node-spec-batch` **does NOT support** changing Shard readonly replica count; use individual modification instead
> - When modifying multiple Shards, must confirm spec mapping and execution order with the user
> - `Storage` in `NodesInfo` must be a **numeric type** (not string), otherwise `InvalidParameter` error

```bash
# Query sharded cluster node details (ShardList/MongosList contain NodeId)
aliyun dds describe-db-instance-attribute --db-instance-id <id> --user-agent AlibabaCloud-Agent-Skills

# Add single node
aliyun dds create-node --db-instance-id <id> --node-type mongos/shard --node-class <class> [--node-storage <GB>] --user-agent AlibabaCloud-Agent-Skills

# Batch add nodes (JSON format)
aliyun dds create-node-batch --db-instance-id <id> --nodes-info '{"Shards":[{"DBInstanceClass":"spec","Storage":40}],"Mongos":[{"DBInstanceClass":"spec"}]}' --auto-pay true --user-agent AlibabaCloud-Agent-Skills

# Single node modification (strictly serial)
aliyun dds modify-node-spec --db-instance-id <id> --node-id <node-id> --node-class <class> [--node-storage <GB>] [--readonly-replicas 0-5] --effective-time Immediately/MaintainTime --user-agent AlibabaCloud-Agent-Skills

# Batch modification (does not support readonly replica changes, requires DBInstanceName)
aliyun dds modify-node-spec-batch --db-instance-id <id> --nodes-info '{"Shards":[{"DBInstanceClass":"spec","DBInstanceName":"d-xxx","Storage":40}]}' --auto-pay true --effective-time Immediately --user-agent AlibabaCloud-Agent-Skills

# Release node
aliyun dds delete-node --db-instance-id <id> --node-id <node-id> --user-agent AlibabaCloud-Agent-Skills
```

> Detailed command examples and NodesInfo format: see [references/operations.md § Sharded Cluster Node Management](references/operations.md)

---

## Cloud Disk Reconfiguration (Disk Type Upgrade)

> **[MUST]** Independent from instance spec modification; used for disk type change or provisioned IOPS adjustment:
> - Only supports ESSD PL1/PL2/PL3 → ESSD AutoPL (`cloud_auto`), **one-way irreversible**
> - Prerequisite: Replica set storage > 40GB; Sharded cluster Shard storage > 40GB
> - Provisioned IOPS range: 0~50000; interval between two modifications must be > 1 hour
> - Before execution, must query and display `MaxIOPS`/`MaxMBPS`/`StorageType`, obtain user Y confirmation
> - **Do NOT execute before user confirmation**

```bash
aliyun dds modify-db-instance-disk-type --db-instance-id <id> \
  --db-instance-storage-type cloud_auto [--provisioned-iops <0~50000>] \
  --region <region> --user-agent AlibabaCloud-Agent-Skills
```

> Full parameter description: see [references/operations.md § Cloud Disk Reconfiguration](references/operations.md)

## IOPS and Throughput Calculation Rules

> **[MUST] Applicable only to cloud disk instances (not applicable to local disk):**
> - When displaying baseline IOPS/throughput, must use `MaxIOPS`/`MaxMBPS` fields returned by API, **NOT** formula-calculated values (actual values ≥ formula values)
> - Formula (reference): `IOPS = min{1800+50×StorageGB, spec limit, disk type limit}`
> - IOPS improvement priority: Expand storage > Upgrade spec > Change disk type
>
> Full spec limit tables and calculation examples: see [references/operations.md § IOPS and Throughput Calculation Rules](references/operations.md)

---

## Reset root Password

> **[MUST] For sharded clusters, must ask the user before resetting password:**
>
> ```
> Which node type's password do you want to reset?
> [1] db node (mongod, stores business data)
> [2] cs node (configServer, stores cluster metadata)
> [3] Reset both (execute twice separately)
> ```
>
> Determine execution count based on user's answer; **do NOT auto-execute twice without user confirmation**
>
> **Password rules:** 8-32 characters, must contain at least three of: uppercase letters/lowercase letters/digits/special characters (`!@#$%^&*()_+-=`)

```bash
# Replica set / Standalone
aliyun dds reset-account-password --db-instance-id <id> --account-name root \
  --account-password <pwd> --region <region> --user-agent AlibabaCloud-Agent-Skills

# Sharded cluster (--character-type db or cs, required)
aliyun dds reset-account-password --db-instance-id <id> --account-name root \
  --account-password <pwd> --character-type db --region <region> --user-agent AlibabaCloud-Agent-Skills
```

---

## Instance Security Configuration

### Manage IP Whitelist

> **[MUST] Before modifying whitelist:**
> 1. First query current whitelist (`describe-security-ips`) and display to user
> 2. Ask for modification mode: **Cover** (overwrite, ⚠️ deletes existing IPs) / **Append** (add, errors on duplicate IPs) / **Extend** (extend, recommended)
> 3. **Do NOT use Cover mode without asking the user**

```bash
aliyun dds describe-security-ips --db-instance-id <id> --user-agent AlibabaCloud-Agent-Skills
aliyun dds modify-security-ips --db-instance-id <id> --security-ips <IPs> --modify-mode Extend --user-agent AlibabaCloud-Agent-Skills
# Specify group: add --security-ip-group-name <name>
```

### Manage ECS Security Groups

> **Note:** ECS security groups bound to sharded clusters only apply to Mongos nodes.

```bash
aliyun dds modify-security-group-configuration --db-instance-id <id> --security-group-id <sg-id> --user-agent AlibabaCloud-Agent-Skills
aliyun dds describe-security-group-configuration --db-instance-id <id> --user-agent AlibabaCloud-Agent-Skills
```

### Manage Global Whitelist Templates

> **[MUST]** All global whitelist commands must specify both `--region` and `--biz-region-id` (same value)
> Use `--db-cluster-id` (**NOT** `--db-instance-id`) when associating with instances

```bash
# Create
aliyun dds create-global-security-ip-group --biz-region-id <region> --region <region> --global-ig-name <name> --gip-list <IPs> --user-agent AlibabaCloud-Agent-Skills
# Query
aliyun dds describe-global-security-ip-group --biz-region-id <region> --region <region> --user-agent AlibabaCloud-Agent-Skills
# Associate with instance
aliyun dds modify-global-security-ip-group-relation --db-cluster-id <id> --global-security-group-id <gid> --biz-region-id <region> --region <region> --user-agent AlibabaCloud-Agent-Skills
```

---

## Manage Public Network Address

> **[MUST] Prerequisites for SRV address:**
> 1. Instance must be **cloud disk** type (`StorageType` starts with `cloud_`). Local disk instances do not support SRV addresses
> 2. For **public SRV** address: must allocate **public network address first** (`allocate-public-network-address`), then apply for SRV
> 3. For **sharded clusters**: must first allocate public address for **Mongos node** (`--node-id <s-xxx>`), then call `allocate-db-instance-srv-network-address --srv-connection-type public`
> 4. After each allocation, wait for instance to return to `Running` before next operation
>
> **Check flow for sharded cluster public SRV:**
> 1. `describe-sharding-network-address` → check if Mongos has `NetworkType=Public` address
> 2. If no public address → `allocate-public-network-address --node-id <mongos-s-xxx>` → wait Running
> 3. `allocate-db-instance-srv-network-address --srv-connection-type public` → wait Running
> 4. `describe-sharding-network-address` → confirm `NodeType=logic` with `srv` in address
>
> **Query addresses:** Use `describe-replica-set-role` for replica sets; for sharded clusters, must use `describe-sharding-network-address` (`describe-db-instance-attribute` does not return sharded cluster network addresses)
> In results, `NetworkType=Public` indicates public network; `NodeType=logic` with `srv` indicates SRV address

```bash
# Allocate public address (add --node-id <s-xxx> for sharded clusters)
aliyun dds allocate-public-network-address --db-instance-id <id> [--node-id <s-xxx>] --region <region> --user-agent AlibabaCloud-Agent-Skills
# Release public address
aliyun dds release-public-network-address --db-instance-id <id> [--node-id <s-xxx>] --region <region> --user-agent AlibabaCloud-Agent-Skills
# Allocate SRV address (vpc=private, public=public; public SRV requires public network address first)
aliyun dds allocate-db-instance-srv-network-address --db-instance-id <id> --srv-connection-type vpc/public --region <region> --user-agent AlibabaCloud-Agent-Skills
# Query (replica set)
aliyun dds describe-replica-set-role --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills
# Query (sharded cluster)
aliyun dds describe-sharding-network-address --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills
```

---

## Manage Instance Renewal

> Renewal only applies to Subscription instances; auto-renewal takes effect the next day; no immediate charge on the day of activation. See [references/operations.md](references/operations.md) for charge retry schedules.

```bash
# Manual renewal (--period: 1~9, 12, 24, 36 months)
aliyun dds renew-db-instance --db-instance-id <id> --period <months> --auto-pay true --region <region> --user-agent AlibabaCloud-Agent-Skills
# Enable auto-renewal (--duration required, in months)
aliyun dds modify-instance-auto-renewal-attribute --db-instance-id <id> --auto-renew true --duration 1 --biz-region-id <region> --user-agent AlibabaCloud-Agent-Skills
# Disable auto-renewal
aliyun dds modify-instance-auto-renewal-attribute --db-instance-id <id> --auto-renew false --biz-region-id <region> --user-agent AlibabaCloud-Agent-Skills
```

## Convert Instance Billing Type

> Prerequisites: Instance status `Running`, and not a legacy spec (discontinued specs must be migrated to active specs first)

```bash
# Pay-As-You-Go → Subscription
aliyun dds transform-instance-charge-type --instance-id <id> --charge-type PrePaid --period 1 --pricing-cycle Month --auto-pay true --region <region> --user-agent AlibabaCloud-Agent-Skills
# Subscription → Pay-As-You-Go (no period needed, may involve refund)
aliyun dds transform-instance-charge-type --instance-id <id> --charge-type PostPaid --region <region> --user-agent AlibabaCloud-Agent-Skills
```

## Manage Instance Maintenance Window

```bash
aliyun dds modify-db-instance-maintain-time --db-instance-id <id> --maintain-start-time "01:00Z" --maintain-end-time "02:00Z" --user-agent AlibabaCloud-Agent-Skills
```

---

## Features Not Available via CLI

| Feature | Description |
|---------|-------------|
| **KMS instance activation** | After KMS instance creation, must be activated in [KMS Console](https://kms.console.aliyun.com/), configuring VPC/VSwitch |
| **Free trial application** | Must apply on [Alibaba Cloud Free Trial](https://free.aliyun.com/) page |

## Verification Methods

See [references/verification-method.md](references/verification-method.md) for details.

## Best Practices

1. Choose the same region as ECS, use VPC network to reduce network latency
2. Multi-zone deployment for production (`--secondary-zone-id` + `--hidden-zone-id`)
3. Storage type: ESSD PL2/PL3 for high performance, ESSD PL1/AutoPL for cost-sensitive scenarios
4. Password: At least three of uppercase/lowercase/digits/special characters, 8-32 characters; sharded clusters require separate password reset for db and cs nodes
5. Whitelist: `0.0.0.0/0` is prohibited in production; prefer Extend mode for whitelist modifications

## References
| Reference | Description |
|-----------|-------------|
| [references/operations.md](references/operations.md) | Detailed CLI command examples, parameter tables, IOPS calculation spec tables |
| [references/related-apis.md](references/related-apis.md) | Complete API and CLI command list with external documentation links |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/verification-method.md](references/verification-method.md) | Verification methods |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Test acceptance criteria |