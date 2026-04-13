# MongoDB Instance Management - Detailed Operations Reference

This document contains detailed CLI command examples, parameter tables, and calculation spec tables extracted from SKILL.md.

---

## Query Regions and Instances - Complete Scripts

### Cross-region lookup for specific instance

```bash
INSTANCE_ID="dds-xxxxxxxxx"
REGIONS="cn-beijing cn-shanghai ap-southeast-1 us-west-1 us-east-1 cn-hangzhou cn-shenzhen cn-chengdu cn-hongkong cn-zhangjiakou"

for region in $REGIONS; do
  result=$(aliyun dds describe-db-instances \
    --db-instance-id $INSTANCE_ID \
    --biz-region-id $region \
    --user-agent AlibabaCloud-Agent-Skills 2>&1 | grep '"DBInstanceId"')
  if [ ! -z "$result" ]; then
    instance_info=$(aliyun dds describe-db-instances \
      --db-instance-id $INSTANCE_ID \
      --biz-region-id $region \
      --user-agent AlibabaCloud-Agent-Skills)
    # Must use RegionId from the returned result as the actual region of the instance
    actual_region=$(echo "$instance_info" | jq -r '.DBInstances.DBInstance[0].RegionId')
    echo "Instance $INSTANCE_ID is located in region $actual_region"
    echo "$instance_info" | jq '.DBInstances.DBInstance[0]'
    break
  fi
done
```

### Query instances across all regions

```bash
aliyun dds DescribeRegions --user-agent AlibabaCloud-Agent-Skills 2>&1 | \
  grep '"RegionId"' | sed 's/.*"RegionId": "\([^"]*\)".*/\1/' | \
  while read region; do
    echo "=== $region ==="
    aliyun dds describe-db-instances \
      --biz-region-id $region \
      --page-size 10 \
      --user-agent AlibabaCloud-Agent-Skills 2>&1 | \
      grep -E '"DBInstanceId"|"DBInstanceType"' | head -4
  done
```

---

## Core Workflow - Detailed Steps

### Step 0 (Optional): Create Resource Group

```bash
# Query existing resource groups
aliyun resourcemanager list-resource-groups --user-agent AlibabaCloud-Agent-Skills

# Create new resource group
aliyun resourcemanager create-resource-group \
  --name "mongodb-project" \
  --display-name "MongoDB Project Resource Group" \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Limit:** A single Alibaba Cloud account can create up to 30 resource groups.

### Step 0.5 (Optional): Create KMS Instance

> KMS instances are created via Alibaba Cloud BSS OpenAPI, not directly through the KMS API.

```bash
# Subscription (China site)
aliyun bssopenapi create-instance \
  --product-code kms \
  --product-type kms_ddi_public_cn \
  --subscription-type Subscription \
  --period 12 \
  --renewal-status ManualRenewal \
  --parameter '[{"Code":"ProductVersion","Value":"3"},{"Code":"Region","Value":"cn-hangzhou"},{"Code":"Spec","Value":"1000"},{"Code":"KeyNum","Value":"1000"},{"Code":"SecretNum","Value":"0"},{"Code":"VpcNum","Value":"1"},{"Code":"log","Value":"0"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**KMS ProductType Reference:**

| Billing Type | China Site | International Site |
|-------------|------------|-------------------|
| Subscription | kms_ddi_public_cn | kms_ddi_public_intl |
| PayAsYouGo | kms_ppi_public_cn | kms_ppi_public_intl |

> **Important:** After KMS instance creation, it must be activated in the [KMS Console](https://kms.console.aliyun.com/) (configure VPC/VSwitch). This step only supports console operation.

### Step 0.6 (Optional): Cloud Disk Encryption Configuration

**KMS Key Region Constraint:** Must be in the same region as the MongoDB instance.

**Check Flow:**

| Step | Operation | Description |
|------|-----------|-------------|
| Step 1 | Query KMS keys in target region | If available keys exist, directly create encrypted instance |
| Step 2 | Query KMS instances in target region | If `TotalCount>0`, ask user whether to create a key |
| Step 3 | No KMS instance | Show options: [1] Create KMS instance via console; [2] Create non-encrypted instance |

```bash
# Query KMS keys
aliyun kms list-keys --region <region> --user-agent AlibabaCloud-Agent-Skills
# Query KMS instances
aliyun kms list-kms-instances --region <region> --user-agent AlibabaCloud-Agent-Skills
# Create key (default key / software key)
aliyun kms create-key \
  --description "MongoDB cloud disk encryption key" \
  --key-spec Aliyun_AES_256 \
  --key-usage ENCRYPT/DECRYPT \
  --protection-level SOFTWARE \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 1: Query Available Specifications

```bash
# Replica set specs (--db-type normal or omit)
aliyun dds describe-available-resource \
  --biz-region-id cn-hangzhou \
  --zone-id cn-hangzhou-g \
  --db-type normal \
  --engine-version 7.0 \
  --storage-type cloud_essd1 \
  --replication-factor 3 \
  --user-agent AlibabaCloud-Agent-Skills

# Sharded cluster specs (--db-type sharding)
aliyun dds describe-available-resource \
  --biz-region-id cn-hangzhou \
  --zone-id cn-hangzhou-g \
  --db-type sharding \
  --engine-version 6.0 \
  --storage-type cloud_essd1 \
  --user-agent AlibabaCloud-Agent-Skills

# Standalone specs (--replication-factor 1)
aliyun dds describe-available-resource \
  --biz-region-id cn-hangzhou \
  --zone-id cn-hangzhou-g \
  --db-type normal \
  --replication-factor 1 \
  --engine-version 6.0 \
  --storage-type cloud_essd1 \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Note:** `--db-type` only supports `normal` and `sharding`; `mongos`/`shard` will cause `InvalidDbType` error.

### Step 2: Query and Validate VPC and VSwitch

```bash
# Query VPC list for specified zone (DDS-specific API, also returns VSwitches under VPC)
aliyun dds describe-rds-vpcs --zone-id cn-hangzhou-g --user-agent AlibabaCloud-Agent-Skills

# Query VSwitch list under specified VPC
aliyun dds describe-rds-vswitchs \
  --vpc-id vpc-bp191olzz22cgl073**** \
  --user-agent AlibabaCloud-Agent-Skills

# Query VSwitches in specified zone
aliyun dds describe-rds-vswitchs \
  --vpc-id vpc-bp191olzz22cgl073**** \
  --zone-id cn-hangzhou-g \
  --user-agent AlibabaCloud-Agent-Skills

# Alternative: Generic VPC API query
aliyun vpc describe-vpcs --region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun vpc describe-vswitches --region-id cn-hangzhou --vpc-id vpc-xxx --user-agent AlibabaCloud-Agent-Skills
```

**When VPC/VSwitch does not exist:**
1. Notify user which ID does not exist, show query results as evidence
2. Query alternative resources (describe-rds-vpcs/vswitchs)
3. Present Option A (use existing) / Option B (create new)
4. Wait for user confirmation

```bash
# Create VPC
aliyun vpc CreateVpc --RegionId cn-hangzhou --CidrBlock 172.16.0.0/12 --VpcName "mongodb-vpc" --user-agent AlibabaCloud-Agent-Skills

# Create VSwitch (must specify zone)
aliyun vpc CreateVSwitch --VpcId vpc-bp191olzz22cgl073**** --ZoneId cn-hangzhou-g --CidrBlock 172.16.1.0/24 --VSwitchName "mongodb-vswitch" --user-agent AlibabaCloud-Agent-Skills
```

---

## Parameter Confirmation - Complete Format

### Pre-creation parameter confirmation format

```
═══════════════════════════════════════════════════════════════
          About to create MongoDB instance, please confirm parameters
═══════════════════════════════════════════════════════════════

[Basic Configuration]
  Region:                      cn-hangzhou
  Zone:                        cn-hangzhou-g
  Database Engine Version:     6.0
  Instance Type:               Replica Set

[Spec Configuration]
  Instance Class:              mdb.shard.4x.large.d
  Storage:                     40 GB
  Primary/Secondary Nodes:     3
  Readonly Nodes:              0

[Network Configuration]
  VPC ID:                      vpc-bp1xxxxxx
  VSwitch ID:                  vsw-bp1xxxxxx

[Other Configuration]
  Billing Type:                Pay-As-You-Go
  Instance Description:        test-mongodb
  Storage Type:                cloud_essd1

═══════════════════════════════════════════════════════════════
Please confirm the above parameters? (Enter Y to confirm, N to cancel and reconfigure):
═══════════════════════════════════════════════════════════════
```

### Required Parameters

| Parameter | Required | Description | Applicable Instance Types |
|-----------|----------|-------------|--------------------------|
| RegionId | Yes | Region ID | All |
| EngineVersion | Yes | Version: 8.0/7.0/6.0/5.0/4.4/4.2/4.0 | All |
| DBInstanceClass | Yes | Instance spec (query to obtain) | Standalone/Replica Set |
| DBInstanceStorage | Yes | Storage (GB) | Standalone/Replica Set |
| VpcId | Yes | VPC ID | All |
| VSwitchId | Yes | VSwitch ID | All |

### Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| ZoneId | Zone ID | Auto-select |
| ChargeType | PostPaid (Pay-As-You-Go) / PrePaid (Subscription) | PostPaid |
| Period | Duration (months), required for Subscription | 1 |
| ReplicationFactor | Primary/Secondary nodes: 3/5/7 | 3 |
| ReadonlyReplicas | Readonly nodes: 0-5 | 0 |
| StorageType | Storage type | cloud_essd1 |
| SecondaryZoneId | Secondary node zone (multi-zone) | None |
| HiddenZoneId | Hidden node zone (multi-zone) | None |
| EncryptionKey | KMS key ID (cloud disk encryption) | None |
| ResourceGroupId | Resource group ID | Default resource group |

---

## IOPS and Throughput Calculation Rules

> **Note:** When displaying to users, baseline IOPS/throughput must use the `MaxIOPS`/`MaxMBPS` fields returned by the API, not formula-calculated values (actual values may include bonus storage, so actual ≥ calculated).

**Formulas (reference):**
- IOPS = `min{ 1800 + 50×StorageGB, Spec IOPS Limit, Disk Type IOPS Limit }`
- Throughput = `min{ 120 + 0.5×StorageGB, Spec Throughput Limit, Disk Type Throughput Limit }`

### Cloud Disk Type Performance Limits

| Storage Type | Max IOPS | Max Throughput (MB/s) |
|-------------|----------|----------------------|
| cloud_essd1 (PL1) | 50,000 | 350 |
| cloud_essd2 (PL2) | 100,000 | 750 |
| cloud_essd3 (PL3) | 1,000,000 | 4,000 |
| cloud_auto (AutoPL) | 50,000 (baseline, up to 1M with burst) | 350 (baseline) |

### Dedicated Cloud Disk Spec IOPS/Throughput Limits

| Spec Code | Config | Spec IOPS Limit | Spec Throughput Limit (MB/s) |
|-----------|--------|----------------|----------------------------|
| mdb.shard.4x.large.d | 2C8GB | 10,000 | 128 |
| mdb.shard.8x.large.d | 2C16GB | 10,000 | 128 |
| mdb.shard.2x.xlarge.d | 4C8GB | 20,000 | 192 |
| mdb.shard.4x.xlarge.d | 4C16GB | 20,000 | 192 |
| mdb.shard.8x.xlarge.d | 4C32GB | 20,000 | 192 |
| mdb.shard.2x.2xlarge.d | 8C16GB | 25,000 | 256 |
| mdb.shard.4x.2xlarge.d | 8C32GB | 25,000 | 256 |
| mdb.shard.8x.2xlarge.d | 8C64GB | 25,000 | 256 |
| mdb.shard.2x.4xlarge.d | 16C32GB | 40,000 | 384 |
| mdb.shard.4x.4xlarge.d | 16C64GB | 40,000 | 384 |
| mdb.shard.4x.8xlarge.d | 32C128GB | 60,000 | 640 |
| mdb.shard.2x.16xlarge.d | 64C128GB | 300,000 | 2,048 |

### General-purpose Cloud Disk Spec IOPS/Throughput Limits

| Spec Code | Config | Spec IOPS Limit | Spec Throughput Limit (MB/s) |
|-----------|--------|----------------|----------------------------|
| mdb.shard.2x.large.c | 2C4GB | 10,500 | 128 |
| mdb.shard.4x.large.c | 2C8GB | 10,500 | 128 |
| mdb.shard.2x.xlarge.c | 4C8GB | 21,000 | 192 |
| mdb.shard.4x.xlarge.c | 4C16GB | 21,000 | 192 |
| mdb.shard.2x.2xlarge.c | 8C16GB | 26,250 | 256 |
| mdb.shard.4x.2xlarge.c | 8C32GB | 26,250 | 256 |
| mdb.shard.2x.4xlarge.c | 16C32GB | 42,000 | 384 |
| mdb.shard.4x.4xlarge.c | 16C64GB | 42,000 | 384 |
| mdb.shard.2x.8xlarge.c | 32C64GB | 50,000 | 640 |

### Calculation Examples

**Example 1 (Storage-limited):** Spec `mdb.shard.2x.2xlarge.c` (8C16GB general-purpose, 26250/256), Storage 20GB, cloud_essd1 (50000/350)
```
IOPS = min{1800+50×20, 26250, 50000} = min{2800, 26250, 50000} = 2800 (storage-limited)
Throughput = min{120+0.5×20, 256, 350} = 130 MB/s
```

**Example 2 (Spec-limited):** Spec `mdb.shard.4x.large.d` (2C8GB dedicated, 10000/128), Storage 500GB, cloud_essd1
```
IOPS = min{1800+50×500, 10000, 50000} = 10000 (spec-limited)
Throughput = min{120+0.5×500, 128, 350} = 128 MB/s (spec-limited)
```

---

## Sharded Cluster Node Management - Detailed Commands

### Query Node Information

```bash
# Query sharded cluster node details (ShardList/MongosList contain NodeId)
aliyun dds describe-db-instance-attribute \
  --db-instance-id dds-bp1sharding1234**** \
  --user-agent AlibabaCloud-Agent-Skills
```

### Batch Add Nodes - NodesInfo Format

```bash
# Batch add Shards
aliyun dds create-node-batch \
  --region ap-southeast-1 \
  --db-instance-id dds-t4nf2082c9293ba4 \
  --nodes-info '{"Shards":[{"DBInstanceClass":"mdb.shard.4x.xlarge.d","Storage":300},{"DBInstanceClass":"mdb.shard.4x.xlarge.d","Storage":300}]}' \
  --auto-pay true \
  --user-agent AlibabaCloud-Agent-Skills

# Batch add Mongos
aliyun dds create-node-batch \
  --region ap-southeast-1 \
  --db-instance-id dds-t4n098c8f691fda4 \
  --nodes-info '{"Mongos":[{"DBInstanceClass":"mdb.shard.2x.xlarge.d"},{"DBInstanceClass":"mdb.shard.2x.xlarge.d"}]}' \
  --auto-pay true \
  --user-agent AlibabaCloud-Agent-Skills

# Add Shards and Mongos simultaneously
aliyun dds create-node-batch \
  --region ap-southeast-1 \
  --db-instance-id dds-t4n098c8f691fda4 \
  --nodes-info '{"Shards":[{"DBInstanceClass":"mdb.shard.4x.xlarge.d","Storage":40,"ReadonlyReplicas":0}],"Mongos":[{"DBInstanceClass":"mdb.shard.2x.xlarge.d"}]}' \
  --auto-pay true \
  --user-agent AlibabaCloud-Agent-Skills
```

### Batch Modify Node Specs - NodesInfo Format (requires DBInstanceName)

```bash
# Batch modify Shard specs (Storage must be numeric, not string)
aliyun dds modify-node-spec-batch \
  --region ap-southeast-1 \
  --db-instance-id dds-t4n098c8f691fda4 \
  --nodes-info '{"Shards":[{"DBInstanceClass":"mdb.shard.4x.xlarge.d","DBInstanceName":"d-t4n948d542391c84","Storage":40},{"DBInstanceClass":"mdb.shard.4x.xlarge.d","DBInstanceName":"d-t4n0c21a1daa00d4","Storage":40}]}' \
  --auto-pay true \
  --effective-time "Immediately" \
  --user-agent AlibabaCloud-Agent-Skills

# Batch modify Mongos specs
aliyun dds modify-node-spec-batch \
  --region ap-southeast-1 \
  --db-instance-id dds-t4n098c8f691fda4 \
  --nodes-info '{"Mongos":[{"DBInstanceClass":"mdb.shard.4x.large.d","DBInstanceName":"s-t4n5062340aa8414"},{"DBInstanceClass":"mdb.shard.4x.large.d","DBInstanceName":"s-t4n37229302a2124"}]}' \
  --auto-pay true \
  --effective-time "Immediately" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Prerequisites for Releasing Nodes

Before releasing a Shard, confirm:
1. Remaining Shards ≥ 2
2. MongoDB Balancer is enabled
3. Remaining Shards have sufficient storage (data will be migrated when a Shard is released)
4. If duplicated key error occurs, clean orphaned documents first

---

## Modify Replica Set Instance - Detailed Parameter Description

### Modifiable Items

| Item | Field | Options | Description |
|------|-------|---------|-------------|
| Spec | DBInstanceClass | Query available spec list | Upgrade or downgrade |
| Storage | DBInstanceStorage | 20GB-3000GB | Only expansion supported |
| Node count | ReplicationFactor | 3/5/7 (odd only) | Change replica set node count |
| Readonly nodes | ReadonlyReplicas | 0-5 | Add or remove readonly nodes |

### Complete Modification Commands

```bash
# Upgrade spec (Pay-As-You-Go, immediate effect)
aliyun dds modify-db-instance-spec \
  --db-instance-id dds-bp1ee12ad351**** \
  --db-instance-class "mdb.shard.4x.large.d" \
  --db-instance-storage 40 \
  --effective-time "Immediately" \
  --user-agent AlibabaCloud-Agent-Skills

# Upgrade spec (Subscription)
aliyun dds modify-db-instance-spec \
  --db-instance-id dds-bp1ee12ad351**** \
  --db-instance-class "mdb.shard.4x.large.d" \
  --db-instance-storage 40 \
  --order-type "UPGRADE" \
  --auto-pay true \
  --effective-time "MaintainTime" \
  --user-agent AlibabaCloud-Agent-Skills

# Change node count
aliyun dds modify-db-instance-spec \
  --db-instance-id dds-bp1ee12ad351**** \
  --replication-factor "5" \
  --effective-time "MaintainTime" \
  --user-agent AlibabaCloud-Agent-Skills

# Change readonly node count
aliyun dds modify-db-instance-spec \
  --db-instance-id dds-bp1ee12ad351**** \
  --readonly-replicas "2" \
  --effective-time "Immediately" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Effective time:** `Immediately` = immediate; `MaintainTime` = during maintenance window

**Modification status:** In progress = `DBInstanceClassChanging`; Complete = `Running`

> Note: The `OrderId` returned from modification is for billing only. **Do NOT** use `bssopenapi GetOrderDetail` to query modification status.

---

## Cloud Disk Reconfiguration - Complete Parameter Description

| Parameter | Type | Required | Description | Values |
|-----------|------|----------|-------------|--------|
| `--db-instance-id` | string | Yes | Instance ID | dds-xxx |
| `--db-instance-storage-type` | string | No | Target disk type | `cloud_auto` |
| `--provisioned-iops` | integer | No | Provisioned IOPS (extra charges beyond baseline) | 0~50,000 |
| `--auto-pay` | boolean | No | Auto-pay | `true` (default) |
| `--order-type` | string | No | Subscription only | `UPGRADE`/`DOWNGRADE` |

After reconfiguration: `DBInstanceStatus=Running`, `StorageType=cloud_auto`, `ProvisionedIops` set to configured value.

---

## Security Configuration - Complete Command Examples

### IP Whitelist Complete Examples

```bash
# Cover mode (high risk)
aliyun dds modify-security-ips --db-instance-id dds-xxx --security-ips "192.168.1.100,10.0.0.0/24" --modify-mode Cover --user-agent AlibabaCloud-Agent-Skills

# Append mode (errors on duplicate IPs)
aliyun dds modify-security-ips --db-instance-id dds-xxx --security-ips "192.168.1.101" --modify-mode Append --user-agent AlibabaCloud-Agent-Skills

# Extend mode (recommended, auto-merges duplicate IPs)
aliyun dds modify-security-ips --db-instance-id dds-xxx --security-ips "192.168.1.102" --modify-mode Extend --user-agent AlibabaCloud-Agent-Skills

# Specify group
aliyun dds modify-security-ips --db-instance-id dds-xxx --security-ips "192.168.0.0/24" \
  --security-ip-group-name "app-servers" --security-ip-group-attribute "production" \
  --modify-mode Cover --user-agent AlibabaCloud-Agent-Skills
```

### Global Whitelist Complete Examples

```bash
# Create
aliyun dds create-global-security-ip-group --biz-region-id cn-hangzhou --region cn-hangzhou \
  --global-ig-name "commonaccess" --gip-list "192.168.0.0/16,10.0.0.0/8" --user-agent AlibabaCloud-Agent-Skills

# Modify
aliyun dds modify-global-security-ip-group --biz-region-id cn-hangzhou --region cn-hangzhou \
  --global-security-group-id "g-sg-xxx" --global-ig-name "commonaccess" \
  --gip-list "192.168.0.0/16,10.0.0.0/8,172.16.0.0/12" --user-agent AlibabaCloud-Agent-Skills

# Delete
aliyun dds delete-global-security-ip-group --biz-region-id cn-hangzhou --region cn-hangzhou \
  --global-security-group-id "g-sg-xxx" --user-agent AlibabaCloud-Agent-Skills
```

> **Naming convention:** Template name must start and end with a letter, can only contain lowercase letters, digits, and underscores, length 2~120 characters.

---

## Renewal - Complete Parameter Description

| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `--period` | integer | Renewal duration (months) | 1~9, 12, 24, 36 |
| `--auto-pay` | boolean | Auto-pay | `true` (default) / `false` |
| `--auto-renew` | boolean | Enable auto-renewal simultaneously | `false` (default) |

When `--auto-pay false`, payment must be completed in console: Billing > Billing & Cost Management > Orders > My Orders.

---

## Billing Type Conversion - Complete Parameter Description

| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `--charge-type` | string | Target billing type | `PrePaid` / `PostPaid` |
| `--period` | integer | Duration (months), required for Subscription | 1~9, 12, 24, 36 |
| `--pricing-cycle` | string | Duration unit | `Month` (default) / `Year` (1/2/3/5) |
| `--auto-pay` | boolean | Auto-pay | `true` (default) |
| `--auto-renew` | string | Enable auto-renewal | `false` (default) |
