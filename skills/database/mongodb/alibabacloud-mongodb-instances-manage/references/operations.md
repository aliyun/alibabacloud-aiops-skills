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
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage 2>&1 | grep '"DBInstanceId"')
  if [ ! -z "$result" ]; then
    instance_info=$(aliyun dds describe-db-instances \
      --db-instance-id $INSTANCE_ID \
      --biz-region-id $region \
      --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage)
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
aliyun dds describe-regions --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage 2>&1 | \
  grep '"RegionId"' | sed 's/.*"RegionId": "\([^"]*\)".*/\1/' | \
  while read region; do
    echo "=== $region ==="
    aliyun dds describe-db-instances \
      --biz-region-id $region \
      --page-size 10 \
      --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage 2>&1 | \
      grep -E '"DBInstanceId"|"DBInstanceType"' | head -4
  done
```

---

## Core Workflow - Detailed Steps

### Step 0 (Optional): Create Resource Group

```bash
# Query existing resource groups
aliyun resourcemanager list-resource-groups --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Create new resource group
aliyun resourcemanager create-resource-group \
  --name "mongodb-project" \
  --display-name "MongoDB Project Resource Group" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
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
aliyun kms list-keys --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
# Query KMS instances
aliyun kms list-kms-instances --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
# Create key (default key / software key)
aliyun kms create-key \
  --description "MongoDB cloud disk encryption key" \
  --key-spec Aliyun_AES_256 \
  --key-usage ENCRYPT/DECRYPT \
  --protection-level SOFTWARE \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Sharded cluster specs (--db-type sharding)
aliyun dds describe-available-resource \
  --biz-region-id cn-hangzhou \
  --zone-id cn-hangzhou-g \
  --db-type sharding \
  --engine-version 6.0 \
  --storage-type cloud_essd1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Standalone specs (--replication-factor 1)
aliyun dds describe-available-resource \
  --biz-region-id cn-hangzhou \
  --zone-id cn-hangzhou-g \
  --db-type normal \
  --replication-factor 1 \
  --engine-version 6.0 \
  --storage-type cloud_essd1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

> **Note:** `--db-type` only supports `normal` and `sharding`; `mongos`/`shard` will cause `InvalidDbType` error.

### Step 2: Query and Validate VPC and VSwitch

```bash
# Query VPC list for specified zone (DDS-specific API, also returns VSwitches under VPC)
aliyun dds describe-rds-vpcs --zone-id cn-hangzhou-g --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Query VSwitch list under specified VPC
aliyun dds describe-rds-vswitchs \
  --vpc-id vpc-bp191olzz22cgl073**** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Query VSwitches in specified zone
aliyun dds describe-rds-vswitchs \
  --vpc-id vpc-bp191olzz22cgl073**** \
  --zone-id cn-hangzhou-g \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Alternative: Generic VPC API query
aliyun vpc describe-vpcs --region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
aliyun vpc describe-vswitches --region-id cn-hangzhou --vpc-id vpc-xxx --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

**When VPC/VSwitch does not exist:**
1. Notify user which ID does not exist, show query results as evidence
2. Query available resources in the target zone via `describe-rds-vpcs` / `describe-rds-vswitchs`
3. Present available VPC/VSwitch options to the user and ask them to select one
4. If no VPC/VSwitch is available in the target zone, inform the user that VPC/VSwitch creation is outside the scope of this skill and guide them to create VPC/VSwitch through the Alibaba Cloud console or administrator before retrying

> **Note:** This skill manages MongoDB instances only. VPC and VSwitch creation require separate permissions and are not handled by this skill.

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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

### Batch Add Nodes - NodesInfo Format

```bash
# Batch add Shards
aliyun dds create-node-batch \
  --region ap-southeast-1 \
  --db-instance-id dds-t4nf2082c9293ba4 \
  --nodes-info '{"Shards":[{"DBInstanceClass":"mdb.shard.4x.xlarge.d","Storage":300},{"DBInstanceClass":"mdb.shard.4x.xlarge.d","Storage":300}]}' \
  --auto-pay true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Batch add Mongos
aliyun dds create-node-batch \
  --region ap-southeast-1 \
  --db-instance-id dds-t4n098c8f691fda4 \
  --nodes-info '{"Mongos":[{"DBInstanceClass":"mdb.shard.2x.xlarge.d"},{"DBInstanceClass":"mdb.shard.2x.xlarge.d"}]}' \
  --auto-pay true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Add Shards and Mongos simultaneously
aliyun dds create-node-batch \
  --region ap-southeast-1 \
  --db-instance-id dds-t4n098c8f691fda4 \
  --nodes-info '{"Shards":[{"DBInstanceClass":"mdb.shard.4x.xlarge.d","Storage":40,"ReadonlyReplicas":0}],"Mongos":[{"DBInstanceClass":"mdb.shard.2x.xlarge.d"}]}' \
  --auto-pay true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Batch modify Mongos specs
aliyun dds modify-node-spec-batch \
  --region ap-southeast-1 \
  --db-instance-id dds-t4n098c8f691fda4 \
  --nodes-info '{"Mongos":[{"DBInstanceClass":"mdb.shard.4x.large.d","DBInstanceName":"s-t4n5062340aa8414"},{"DBInstanceClass":"mdb.shard.4x.large.d","DBInstanceName":"s-t4n37229302a2124"}]}' \
  --auto-pay true \
  --effective-time "Immediately" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Upgrade spec (Subscription)
aliyun dds modify-db-instance-spec \
  --db-instance-id dds-bp1ee12ad351**** \
  --db-instance-class "mdb.shard.4x.large.d" \
  --db-instance-storage 40 \
  --order-type "UPGRADE" \
  --auto-pay true \
  --effective-time "MaintainTime" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Change node count
aliyun dds modify-db-instance-spec \
  --db-instance-id dds-bp1ee12ad351**** \
  --replication-factor "5" \
  --effective-time "MaintainTime" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Change readonly node count
aliyun dds modify-db-instance-spec \
  --db-instance-id dds-bp1ee12ad351**** \
  --readonly-replicas "2" \
  --effective-time "Immediately" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
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
aliyun dds modify-security-ips --db-instance-id dds-xxx --security-ips "192.168.1.100,10.0.0.0/24" --modify-mode Cover --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Append mode (errors on duplicate IPs)
aliyun dds modify-security-ips --db-instance-id dds-xxx --security-ips "192.168.1.101" --modify-mode Append --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Extend mode (recommended, auto-merges duplicate IPs)
aliyun dds modify-security-ips --db-instance-id dds-xxx --security-ips "192.168.1.102" --modify-mode Extend --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Specify group
aliyun dds modify-security-ips --db-instance-id dds-xxx --security-ips "192.168.0.0/24" \
  --security-ip-group-name "app-servers" --security-ip-group-attribute "production" \
  --modify-mode Cover --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

### Global Whitelist Complete Examples

```bash
# Create
aliyun dds create-global-security-ip-group --biz-region-id cn-hangzhou --region cn-hangzhou \
  --global-ig-name "commonaccess" --gip-list "192.168.0.0/16,10.0.0.0/8" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Modify
aliyun dds modify-global-security-ip-group --biz-region-id cn-hangzhou --region cn-hangzhou \
  --global-security-group-id "g-sg-xxx" --global-ig-name "commonaccess" \
  --gip-list "192.168.0.0/16,10.0.0.0/8,172.16.0.0/12" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Delete
aliyun dds delete-global-security-ip-group --biz-region-id cn-hangzhou --region cn-hangzhou \
  --global-security-group-id "g-sg-xxx" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
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

---

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

## Best Practices

1. Choose the same region as ECS, use VPC network to reduce network latency
2. Multi-zone deployment for production (`--secondary-zone-id` + `--hidden-zone-id`)
3. Storage type: ESSD PL2/PL3 for high performance, ESSD PL1/AutoPL for cost-sensitive scenarios
4. Password: At least three of uppercase/lowercase/digits/special characters, 8-32 characters; sharded clusters require separate password reset for db and cs nodes
5. Whitelist: `0.0.0.0/0` is prohibited in production; prefer Extend mode for whitelist modifications

---

## Delete Instance - Pre-deletion Checklist

> **[MUST] Step 1: Confirm ChargeType**
> - `PostPaid`: can delete directly
> - `PrePaid`: **cannot delete** — must wait for expiry or request refund via console
>
> **[MUST] Step 2 (Cloud disk instances only): Check BackupRetentionPolicyOnClusterDeletion**
>
> | Value | Meaning |
> |-------|---------|
> | `0` | Delete all backups immediately when instance is released |
> | `1` | Auto-backup on release, keep **last backup only** (long-term retention) |
> | `2` | Auto-backup on release, keep **all backups** (long-term retention) |
>
> Query current policy, then **ask the user if they want to change it** before deleting:
> - Only applies to cloud disk replica set / sharded cluster (`StorageType=cloud_*`)
> - Local disk instances (`local_ssd`) do not support this field
> - Retention cost: free for first 7 days after release; charged after 7 days (see pricing in help docs)
>
> **[MUST] Step 3: Final confirmation**
> Display instance ID, region, billing type, irreversible warning; require user to reply "confirm delete {instance ID}"

```bash
# Step 1: Check billing type
aliyun dds describe-db-instance-attribute --db-instance-id <id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage | jq '.DBInstances.DBInstance[0] | {DBInstanceId, ChargeType, StorageType}'

# Step 2 (cloud disk only): Check current backup retention policy on deletion
aliyun dds describe-backup-policy --db-instance-id <id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage | jq '{BackupRetentionPolicyOnClusterDeletion}'

# Step 2b (if user wants to change): Modify backup retention policy before deletion
# **[MUST]** modify-backup-policy requires --preferred-backup-time AND --preferred-backup-period even when only changing backup-retention-policy-on-cluster-deletion
# First query current values via describe-backup-policy, then pass them through unchanged
aliyun dds modify-backup-policy --db-instance-id <id> \
  --backup-retention-policy-on-cluster-deletion 2 \
  --preferred-backup-time "<current-value>" \
  --preferred-backup-period "<current-value>" \
  --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Step 3: Delete instance (PostPaid only)
aliyun dds delete-db-instance --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

## Additional Operations

### Restart Instance / Node

> **Constraints:**
> - Instance must be in `Running` status
> - Restart causes approximately 30 seconds of disconnection
> - Recommended during off-peak hours or maintenance window
> - `restart-db-instance`: Restarts the **entire instance**; supports optional `--node-id` for sharded cluster to restart a specific node (e.g., `s-xxx`, `d-xxx`)
> - `restart-node`: Restarts an **individual node**, requires both `--node-id` and `--role-id` (both are required parameters); supports **replica set** and **sharded cluster** (not standalone)
> - **[MUST]** `restart-node` only supports **cloud disk instances** (`StorageType=cloud_*`); local disk instances (`local_ssd`) return `InsType.NotSupport` — use `restart-db-instance` instead
> - **Sharded cluster**: both `--node-id` (shard NodeId, e.g. `d-xxx`, from `describe-db-instance-attribute`) AND `--role-id` are required; omitting `--node-id` returns `InvalidParameter: NodeId is not valid`
> - Query `RoleId`: **[MUST]** use `describe-role-zone-info` for all instance types — this returns ALL nodes including Hidden; `describe-replica-set-role` only returns Primary/Secondary and **does NOT include Hidden node**

```bash
# Restart entire instance
aliyun dds restart-db-instance --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Restart sharded cluster specific node via restart-db-instance (optional --node-id)
aliyun dds restart-db-instance --db-instance-id <id> --node-id <node-id> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Restart specific node (replica set or sharded cluster, both --node-id and --role-id required)
# **[MUST]** Query RoleId via describe-role-zone-info (returns ALL nodes including Hidden)
# describe-replica-set-role does NOT return Hidden node
aliyun dds describe-role-zone-info --db-instance-id <id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
aliyun dds restart-node --db-instance-id <id> --node-id <node-id> --role-id <role-id> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--db-instance-id` | Yes | Instance ID |
| `--node-id` | Yes (restart-node); Optional (restart-db-instance, for sharded cluster node restart) | Node ID (e.g., `s-xxx` for mongos, `d-xxx` for shard) |
| `--role-id` | Yes (restart-node) | Role ID; **[MUST]** query via `describe-role-zone-info` (supports all types, returns Hidden node); do NOT use `describe-replica-set-role` which omits Hidden node |
| `--switch-mode` | No | 0 = immediate (default); 1 = during maintenance window |

### Backup Management

> **Backup method by instance type:**
>
> | Instance Type | Storage Type | Supported BackupMethod |
> |--------------|-------------|----------------------|
> | Replica Set / Sharded Cluster | Cloud disk (`cloud_*`) | **Snapshot only** |
> | Replica Set / Sharded Cluster | Local disk (`local_ssd`) | Physical (default) / Logical |
> | Standalone | Any | Snapshot (fixed, no parameter needed) |
>
> **[MUST]** Cloud disk instances (`StorageType` starts with `cloud_`) must use `--backup-method Snapshot`. Using Physical/Logical will fail.
>
> **⚠️ WARNING:** Cloud disk instances **must explicitly pass** `--backup-method Snapshot`. If omitted, the default is `Physical`, which causes `IncorrectBackupSetMethod` error on cloud disk instances.
>
> **Time format:** `yyyy-MM-ddTHH:mmZ` (UTC time)
>
> **Backup retention:** 7-730 days, or -1 for permanent retention
>
> **`--backup-retention-period` parameter:**
> - Applicable to **cloud disk replica set and sharded cluster only** (not standalone, not local disk)
> - If omitted: follows the default retention policy configured in the backup policy
> - Values: `7`-`730` (days) or `-1` (permanent retention)
> - Use when user specifies a custom retention period or requests permanent retention
>
> **create-backup response:**
> - Use `BackupJobId` field (NOT `BackupId` — that field is deprecated)
> - `BackupJobId` is used to poll `describe-backup-tasks` and query `describe-backups`
>
> **Post-creation polling flow:**
> 1. Call `describe-backup-tasks` → poll field `BackupJobs[].BackupjobId` (note: lowercase `j`) until job disappears from list (means completed)
>    - Response structure: `BackupJobs[].BackupSetStatus` / `.Progress` / `.BackupjobId` (int, not string)
> 2. Once completed, call `describe-backups --backup-job-id <BackupJobId>` to retrieve the final backup record
>    - Response structure: `Backups.Backup[]` (NOT `Items.Backup`)
>    - The `BackupId` in describe-backups is a different value from `BackupJobId`

```bash
# Create manual backup — cloud disk instance (Snapshot only, default retention)
aliyun dds create-backup --db-instance-id <id> --backup-method Snapshot --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
# Response: { "BackupJobId": "xxx", ... }  ← use BackupJobId (BackupId is deprecated)

# Create manual backup — cloud disk replica set/sharded cluster with custom retention (7-730 days or -1 for permanent)
aliyun dds create-backup --db-instance-id <id> --backup-method Snapshot --backup-retention-period 30 --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
aliyun dds create-backup --db-instance-id <id> --backup-method Snapshot --backup-retention-period -1 --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Create manual backup — local disk instance (Physical or Logical)
aliyun dds create-backup --db-instance-id <id> --backup-method Physical --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Poll backup task status (until job disappears from list = completed)
aliyun dds describe-backup-tasks --db-instance-id <id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
# Response: BackupJobs[].BackupjobId (int, lowercase j) / .BackupSetStatus / .Progress

# Query final backup record by BackupJobId
aliyun dds describe-backups --db-instance-id <id> --backup-job-id <BackupJobId> --start-time "<BackupStartTime - buffer>" --end-time "<BackupEndTime + buffer>" --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
# Response: Backups.Backup[] (NOT Items.Backup)

# Query backup list by time range
aliyun dds describe-backups --db-instance-id <id> --start-time "2025-01-01T00:00Z" --end-time "2025-12-31T23:59Z" --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Query backup list — sharded cluster (must specify --node-id for the shard node)
aliyun dds describe-backups --db-instance-id <sharding-id> --node-id <shard-d-xxx> --start-time "2025-01-01T00:00Z" --end-time "2025-12-31T23:59Z" --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Query backup policy
aliyun dds describe-backup-policy --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Modify backup policy — set retention days and preferred backup window
aliyun dds modify-backup-policy --db-instance-id <id> \
  --backup-retention-period 30 \
  --preferred-backup-time "03:00Z-04:00Z" \
  --preferred-backup-period "Monday,Wednesday,Friday" \
  --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Modify backup policy — enable log backup (sharded cluster cannot disable)
aliyun dds modify-backup-policy --db-instance-id <id> \
  --enable-backup-log 1 \
  --log-backup-retention-period 30 \
  --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Modify backup policy — enable high-frequency backup
aliyun dds modify-backup-policy --db-instance-id <id> \
  --backup-interval 30 \
  --snapshot-backup-type Flash \
  --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

**ModifyBackupPolicy key parameters:**

| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `--preferred-backup-time` | string | Backup window (UTC, 1-hour range) | e.g., `03:00Z-04:00Z` |
| `--preferred-backup-period` | string | Backup days (comma-separated) | Monday~Sunday |
| `--backup-retention-period` | integer | Full backup retention days | 7-730 (default: 7 or 30) |
| `--enable-backup-log` | integer | Enable log backup | 0 (off) / 1 (on); **sharded cluster cannot set to 0** |
| `--log-backup-retention-period` | integer | Log backup retention days | 7-730 |
| `--snapshot-backup-type` | string | Snapshot backup type | Flash / Standard |
| `--backup-interval` | integer | High-frequency backup interval (min) | -1(off), 30, 60, 120, 180, 240, 360, 480, 720 |
| `--backup-retention-policy-on-cluster-deletion` | integer | Backup retention on instance deletion | 0 (delete all) / 1 (keep latest) / 2 (keep all) |

> **Parameter dependency:** When modifying `--preferred-backup-time`, **must** also pass `--preferred-backup-period` in the same request. Otherwise the API returns `InvalidParameter: PreferredBackupPeriod is not valid`.

> **Flash high-frequency backup — cloud disk only:** `--snapshot-backup-type Flash` is only effective on cloud disk instances (`StorageType` starts with `cloud_`). Local disk instances (`local_ssd`) calling with `--snapshot-backup-type Flash` will **not** return an error, but the setting is **silently ignored** and does not take effect.

> **Cross-region backup** (only for cloud disk replica set / sharded cluster): Use `--cross-backup-type`, `--src-region`, `--dest-region` parameters. See [official documentation](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifybackuppolicy) for details.
>
> **Cross-region backup is asynchronous:** Enabling or deleting cross-region backup is an async operation that requires backend processing time. When deleting cross-region backup, the request may return `DBS.Cross.Backup.BuyInstance.Failed` if backend route registration has not completed. In this case, **wait and retry** after a short interval.

**DescribeBackupPolicy key return fields:**

| Field | Description |
|-------|-------------|
| PreferredBackupPeriod | Backup cycle (days of week) |
| PreferredBackupTime | Backup time window |
| BackupRetentionPeriod | Backup retention days |
| PreferredNextBackupTime | Next scheduled backup time |
| EnableBackupLog | Log backup status (0/1) |
| LogBackupRetentionPeriod | Log backup retention days |
| SnapshotBackupType | Snapshot type (Flash/Standard) |
| BackupInterval | High-frequency backup interval |
| BackupRetentionPolicyOnClusterDeletion | Deletion backup policy (0/1/2); **cloud disk instances only** |
| HighFrequencyBackupRetention | High-frequency backup retention days (cloud disk sharded cluster, AdvancedBackup mode); **cloud disk instances only** |
| PreserveOneEachHour | Whether to keep one backup per hour; **cloud disk instances only** |

> **Local disk vs cloud disk return field differences:** Local disk instances (`local_ssd`) do **not** return the following fields: `BackupRetentionPolicyOnClusterDeletion`, `HighFrequencyBackupRetention`, `PreserveOneEachHour`. These fields are only present in cloud disk instance responses.

> **Advanced backup mode (AdvancedBackup):** Cloud disk sharded cluster instances support high-frequency backup (Flash snapshot). When enabled via `--backup-interval` and `--snapshot-backup-type Flash`, the backup policy returns additional fields such as `HighFrequencyBackupRetention`. Use `describe-backup-policy` to check the current advanced backup configuration.

> **Important:** Once a cloud disk instance is upgraded to AdvancedBackup mode, the standard `describe-backup-policy` and `modify-backup-policy` commands become unavailable (returns `BackupTypeAlreadyUpgrade` error). Use `DescribeAdvancedBackupPolicy` / `ModifyAdvancedBackupPolicy` API instead. Note: these advanced backup commands are not yet available in the CLI.

### Version Upgrade

> **UpgradeDBInstanceEngineVersion (major version upgrade):**
> - One-way irreversible (cannot downgrade)
> - Instance will **automatically restart 2-3 times** during upgrade
> - Applicable to all instance types (replica set, sharded cluster, standalone)
> - **[MUST]** Query available versions via `DescribeAvailableEngineVersion` before upgrade
> - Recommended to create a backup before upgrading
> - Must execute during off-peak hours
>
> **UpgradeDBInstanceKernelVersion (kernel/minor version upgrade):**
> - Minor version patch with single restart
> - **Only supports replica set and sharded cluster** (NOT standalone)
> - No version number parameter needed — auto-selects latest available kernel version
> - `--switch-mode`: 0 = immediate (default), 1 = during maintenance window
>
> **DescribeAvailableEngineVersion:**
> - Returns list of versions the instance can upgrade to
> - **Empty result** means instance is already on the latest version
> - Versions must be upgraded **sequentially** (e.g., 4.2→5.0→6.0, NOT 4.2→6.0 directly)

```bash
# Query available upgrade versions for an instance
aliyun dds describe-available-engine-version --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
# Empty EngineVersions list = already on latest version

# Upgrade major engine version (e.g., 5.0 → 6.0) — will restart 2-3 times
aliyun dds upgrade-db-instance-engine-version --db-instance-id <id> --engine-version <target-version> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Upgrade kernel (minor) version — auto-selects latest, single restart
aliyun dds upgrade-db-instance-kernel-version --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Upgrade kernel version during maintenance window
aliyun dds upgrade-db-instance-kernel-version --db-instance-id <id> --switch-mode 1 --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

### HA Switchover

> **Constraints:**
> - Triggers primary/secondary role switch with brief connectivity interruption
> - **[MUST]** Must confirm with user before execution
> - Only applicable to **replica set and sharded cluster** instances (NOT standalone)
> - **Replica set**: `--node-id` is **NOT required** — switches primary/secondary at instance level
> - **Sharded cluster**: `--node-id` is **REQUIRED** — specifies the shard ID (`d-xxx`) to perform switchover
> - `--role-ids` (optional): comma-separated role IDs to switch; if omitted, all roles switched
> - `--switch-mode`: 0 = immediate (default), 1 = during maintenance window

```bash
# HA switchover — replica set (no --node-id needed)
aliyun dds switch-db-instance-ha --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# HA switchover — sharded cluster (--node-id specifies shard ID d-xxx)
aliyun dds switch-db-instance-ha --db-instance-id <id> --node-id <shard-d-xxx> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# HA switchover during maintenance window
aliyun dds switch-db-instance-ha --db-instance-id <id> --switch-mode 1 --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

### Account Management

> **CreateAccount scope:** Only for **cloud disk sharded cluster** instances (creates Shard accounts).
> For replica set/standalone, use `reset-account-password` for root account (see SKILL.md § Reset root Password).
>
> **AccountName rules:** 3-16 characters, lowercase letters + digits + underscores, must start with a lowercase letter. Created accounts have **read-only** permission.
>
> **⚠️ Reserved keywords:** Some names (e.g., `test`, `admin`, `root`) are reserved and will return `InvalidAccountName.Forbid` error. Choose a different name if this occurs.
>
> **AccountPassword rules:** 8-32 characters, must contain at least three of: uppercase/lowercase/digits/special characters (`!@#$%^&*()_+-=`)
>
> **ModifyAccountDescription:** Does **NOT** support sharded cluster instances. Only for replica set/standalone root account.

```bash
# Create database account (cloud disk sharded cluster only)
aliyun dds create-account --db-instance-id <id> --account-name <name> --account-password <pwd> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Create database account with description (--account-description is optional)
aliyun dds create-account --db-instance-id <id> --account-name <name> --account-password <pwd> --account-description <desc> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Query database accounts
aliyun dds describe-accounts --db-instance-id <id> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Modify account description (replica set/standalone only, NOT sharded cluster)
aliyun dds modify-account-description --db-instance-id <id> --account-name root --account-description <desc> --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--account-name` | Yes | 3-16 chars, lowercase + digits + underscore, starts with letter |
| `--account-password` | Yes | 8-32 chars, 3 of 4 types required |
| `--account-description` | No | Account description |
| `--character-type` | No | `db` (default, shard account), `cs` (config server), `normal` (replica set) |

### Tag Management

> **Constraints:**
> - Up to 20 tags per instance
> - `--resource-type` must be `INSTANCE`
> - Tag key and value: max 128 characters each
> - Tags are auto-created if they don't exist; duplicate keys overwrite existing values
> - When a tag is unbound from all instances, it is automatically deleted

```bash
# Bind tags to instance (--resource-id takes space-separated list; --tag takes Key=<k> Value=<v>, repeatable)
aliyun dds tag-resources --biz-region-id <region> --resource-type INSTANCE --resource-id <instance-id> --tag Key=<key> Value=<value> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Bind multiple tags to multiple instances
aliyun dds tag-resources --biz-region-id <region> --resource-type INSTANCE --resource-id <id1> <id2> --tag Key=<k1> Value=<v1> --tag Key=<k2> Value=<v2> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Unbind specific tags from instance (--tag-key takes space-separated list)
aliyun dds untag-resources --biz-region-id <region> --resource-type INSTANCE --resource-id <instance-id> --tag-key <key> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Unbind ALL tags from instance
aliyun dds untag-resources --biz-region-id <region> --resource-type INSTANCE --resource-id <instance-id> --all true --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Query tags bound to specific instance
aliyun dds list-tag-resources --biz-region-id <region> --resource-type INSTANCE --resource-id <instance-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Query instances by tag key/value
aliyun dds list-tag-resources --biz-region-id <region> --resource-type INSTANCE --tag Key=<key> Value=<value> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage

# Query all existing tags
aliyun dds describe-tags --biz-region-id <region> --resource-type INSTANCE --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mongodb-instances-manage
```

> **Note:** For `list-tag-resources`, must provide at least one of `--resource-id` or `--tag`.
