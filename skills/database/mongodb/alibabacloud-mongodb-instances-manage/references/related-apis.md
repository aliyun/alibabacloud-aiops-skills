# Related APIs - MongoDB Instance Management

This document lists all APIs and CLI commands involved in MongoDB instance management (Standalone/Replica Set/Sharded Cluster).

## DDS (ApsaraDB for MongoDB)

### Instance Management APIs

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun dds create-db-instance` | CreateDBInstance | Create or clone a Replica Set instance | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-createdbinstance) |
| `aliyun dds create-sharding-db-instance` | CreateShardingDBInstance | Create a Sharded Cluster instance | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-createshardingdbinstance) |
| `aliyun dds describe-db-instances` | DescribeDBInstances | Query instance list | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describedbinstances) |
| `aliyun dds describe-db-instance-attribute` | DescribeDBInstanceAttribute | Query instance details | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describedbinstanceattribute) |
| `aliyun dds describe-sharding-network-address` | DescribeShardingNetworkAddress | Query Sharded Cluster network addresses | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describeshardingnetworkaddress) |
| `aliyun dds delete-db-instance` | DeleteDBInstance | Delete instance | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-deletedbinstance) |
| `aliyun dds modify-db-instance-description` | ModifyDBInstanceDescription | Modify instance name | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifydbinstancedescription) |
| `aliyun dds modify-db-instance-spec` | ModifyDBInstanceSpec | Modify instance specification | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifydbinstancespec) |
| `aliyun dds modify-db-instance-disk-type` | ModifyDBInstanceDiskType | Cloud disk reconfiguration (ESSD → ESSD AutoPL / adjust provisioned IOPS) | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifydbinstancedisktype) |
| `aliyun dds modify-db-instance-maintain-time` | ModifyDBInstanceMaintainTime | Modify instance maintenance window | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifydbinstancemaintaintime) |
| `aliyun dds renew-db-instance` | RenewDBInstance | Manually renew Subscription instance | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-renewdbinstance) |
| `aliyun dds transform-instance-charge-type` | TransformInstanceChargeType | Convert billing type (Pay-As-You-Go ↔ Subscription) | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-transforminstancechargetype) |
| `aliyun dds modify-instance-auto-renewal-attribute` | ModifyInstanceAutoRenewalAttribute | Enable/disable auto-renewal | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifyinstanceautorenewalattribute) |
| `aliyun dds restart-db-instance` | RestartDBInstance | Restart instance | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-restartdbinstance) |

### Sharded Cluster Node Management APIs

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun dds create-node` | CreateNode | Add a single node | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-createnode) |
| `aliyun dds create-node-batch` | CreateNodeBatch | Batch add nodes | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-createnodebatch) |
| `aliyun dds modify-node-spec` | ModifyNodeSpec | Modify single node spec | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifynodespec) |
| `aliyun dds modify-node-spec-batch` | ModifyNodeSpecBatch | Batch modify node specs | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifynodespecbatch) |
| `aliyun dds delete-node` | DeleteNode | Release node | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-deletenode) |

### Resource Query APIs

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun dds describe-regions` | DescribeRegions | Query available regions and zones | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describeregions) |
| `aliyun dds describe-available-resource` | DescribeAvailableResource | Query available instance specs and storage | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describeavailableresource) |
| `aliyun dds describe-rds-vpcs` | DescribeRdsVpcs | Query MongoDB-available VPC list | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describerdsvpcs) |
| `aliyun dds describe-rds-vswitchs` | DescribeRdsVSwitchs | Query MongoDB-available VSwitch list | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describerdsvswitchs) |

### Backup and Restore APIs

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun dds describe-backups` | DescribeBackups | Query backup list | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describebackups) |
| `aliyun dds create-backup` | CreateBackup | Create backup | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-createbackup) |

### Network Configuration APIs

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun dds modify-security-ips` | ModifySecurityIps | Modify IP whitelist | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifysecurityips) |
| `aliyun dds describe-security-ips` | DescribeSecurityIps | Query IP whitelist | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describesecurityips) |
| `aliyun dds modify-security-group-configuration` | ModifySecurityGroupConfiguration | Modify ECS security group binding | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifysecuritygroupconfiguration) |
| `aliyun dds describe-security-group-configuration` | DescribeSecurityGroupConfiguration | Query ECS security group binding | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describesecuritygroupconfiguration) |
| `aliyun dds create-global-security-ip-group` | CreateGlobalSecurityIPGroup | Create global whitelist template | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-createglobalsecurityipgroup) |
| `aliyun dds describe-global-security-ip-group` | DescribeGlobalSecurityIPGroup | Query global whitelist template | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describeglobalsecurityipgroup) |
| `aliyun dds modify-global-security-ip-group` | ModifyGlobalSecurityIPGroup | Modify global whitelist template | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifyglobalsecurityipgroup) |
| `aliyun dds delete-global-security-ip-group` | DeleteGlobalSecurityIPGroup | Delete global whitelist template | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-deleteglobalsecurityipgroup) |
| `aliyun dds modify-global-security-ip-group-relation` | ModifyDBInstanceGlobalSecurityIPGroup | Associate global whitelist template with instance | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifydbinstanceglobalsecurityipgroup) |
| `aliyun dds allocate-public-network-address` | AllocatePublicNetworkAddress | Allocate public network address | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-allocatepublicnetworkaddress) |
| `aliyun dds release-public-network-address` | ReleasePublicNetworkAddress | Release public network address | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-releasepublicnetworkaddress) |
| `aliyun dds allocate-db-instance-srv-network-address` | AllocateDBInstanceSrvNetworkAddress | Allocate SRV address (cloud disk Replica Set/Sharded Cluster only) | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-allocatedbinstancesrvnetworkaddress) |
| `aliyun dds describe-replica-set-role` | DescribeReplicaSetRole | Query Replica Set network addresses | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describereplicasetrole) |
| `aliyun dds describe-sharding-network-address` | DescribeShardingNetworkAddress | Query Sharded Cluster network addresses | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describeshardingnetworkaddress) |

### Account Management APIs

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun dds reset-account-password` | ResetAccountPassword | Reset password | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-resetaccountpassword) |

### Tag Management APIs

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun dds tag-resources` | TagResources | Bind tags | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-tagresources) |
| `aliyun dds untag-resources` | UntagResources | Unbind tags | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-untagresources) |
| `aliyun dds list-tag-resources` | ListTagResources | Query tags | [Doc](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-listtagresources) |

## VPC (Virtual Private Cloud)

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun vpc describe-vpcs` | DescribeVpcs | Query VPC list | [Doc](https://help.aliyun.com/zh/vpc/developer-reference/api-vpc-2016-04-28-describevpcs) |
| `aliyun vpc describe-vswitches` | DescribeVSwitches | Query VSwitch list | [Doc](https://help.aliyun.com/zh/vpc/developer-reference/api-vpc-2016-04-28-describevswitches) |
| `aliyun vpc create-vpc` | CreateVpc | Create VPC | [Doc](https://help.aliyun.com/zh/vpc/developer-reference/api-vpc-2016-04-28-createvpc) |
| `aliyun vpc create-vswitch` | CreateVSwitch | Create VSwitch | [Doc](https://help.aliyun.com/zh/vpc/developer-reference/api-vpc-2016-04-28-createvswitch) |

## KMS (Key Management Service)

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun kms create-key` | CreateKey | Create master key | [Doc](https://help.aliyun.com/zh/kms/key-management-service/developer-reference/api-createkey) |
| `aliyun kms list-keys` | ListKeys | Query key list | [Doc](https://help.aliyun.com/zh/kms/developer-reference/api-kms-2016-01-20-listkeys) |
| `aliyun kms list-kms-instances` | ListKmsInstances | Query KMS instance list | [Doc](https://help.aliyun.com/zh/kms/key-management-service/developer-reference/api-kms-2016-01-20-listkmsinstances) |
| `aliyun kms describe-key` | DescribeKey | Query key details | [Doc](https://help.aliyun.com/zh/kms/developer-reference/api-kms-2016-01-20-describekey) |
| `aliyun kms schedule-key-deletion` | ScheduleKeyDeletion | Schedule key deletion | [Doc](https://help.aliyun.com/zh/kms/developer-reference/api-kms-2016-01-20-schedulekeydeletion) |

## ResourceManager (Resource Management)

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun resourcemanager create-resource-group` | CreateResourceGroup | Create resource group | [Doc](https://help.aliyun.com/zh/resource-management/resource-group/developer-reference/api-resourcemanager-2020-03-31-createresourcegroup-rg) |
| `aliyun resourcemanager list-resource-groups` | ListResourceGroups | Query resource group list | [Doc](https://help.aliyun.com/zh/resource-management/resource-group/developer-reference/api-resourcemanager-2020-03-31-listresourcegroups-rg) |
| `aliyun resourcemanager get-resource-group` | GetResourceGroup | Query resource group details | [Doc](https://help.aliyun.com/zh/resource-management/resource-group/developer-reference/api-resourcemanager-2020-03-31-getresourcegroup-rg) |
| `aliyun resourcemanager delete-resource-group` | DeleteResourceGroup | Delete resource group | [Doc](https://help.aliyun.com/zh/resource-management/resource-group/developer-reference/api-resourcemanager-2020-03-31-deleteresourcegroup-rg) |

## BssOpenApi (Billing and Order Management)

| CLI Command | API Action | Description | Documentation |
|-------------|------------|-------------|---------------|
| `aliyun bssopenapi create-instance` | CreateInstance | Create KMS instance | [Doc](https://help.aliyun.com/zh/kms/key-management-service/developer-reference/createinstance) |
| `aliyun bssopenapi query-available-instances` | QueryAvailableInstances | Query available instances | [Doc](https://help.aliyun.com/zh/bssopenapi/developer-reference/api-bssopenapi-2017-12-14-queryavailableinstances) |

---

## CreateDBInstance Parameter Details

### Required Parameters

| Parameter | Type | CLI Parameter | Description |
|-----------|------|---------------|-------------|
| RegionId | string | `--region-id` | Region ID |
| EngineVersion | string | `--engine-version` | Database version: 8.0/7.0/6.0/5.0/4.4/4.2/4.0 |
| DBInstanceClass | string | `--db-instance-class` | Instance specification |
| DBInstanceStorage | integer | `--db-instance-storage` | Storage capacity (GB) |

### Network Configuration Parameters

| Parameter | Type | CLI Parameter | Description |
|-----------|------|---------------|-------------|
| NetworkType | string | `--network-type` | Network type, fixed as VPC |
| VpcId | string | `--vpc-id` | VPC ID |
| VSwitchId | string | `--v-switch-id` | VSwitch ID |
| ZoneId | string | `--zone-id` | Zone ID |
| SecondaryZoneId | string | `--secondary-zone-id` | Secondary node zone (multi-zone deployment) |
| HiddenZoneId | string | `--hidden-zone-id` | Hidden node zone (multi-zone deployment) |

### Node Configuration Parameters

| Parameter | Type | CLI Parameter | Description |
|-----------|------|---------------|-------------|
| ReplicationFactor | string | `--replication-factor` | Primary/secondary node count: 3/5/7 |
| ReadonlyReplicas | string | `--readonly-replicas` | Readonly node count: 0-5 |

### Storage Configuration Parameters

| Parameter | Type | CLI Parameter | Description |
|-----------|------|---------------|-------------|
| StorageType | string | `--storage-type` | Storage type |
| StorageEngine | string | `--storage-engine` | Storage engine, fixed as WiredTiger |

**StorageType Options:**
- `cloud_essd1` - ESSD PL1 cloud disk
- `cloud_essd2` - ESSD PL2 cloud disk
- `cloud_essd3` - ESSD PL3 cloud disk
- `cloud_auto` - ESSD AutoPL cloud disk
- `local_ssd` - Local SSD disk

### Billing Parameters

| Parameter | Type | CLI Parameter | Description |
|-----------|------|---------------|-------------|
| ChargeType | string | `--charge-type` | Billing type: PostPaid (Pay-As-You-Go) / PrePaid (Subscription) |
| Period | integer | `--period` | Duration (months), required for Subscription |
| AutoRenew | string | `--auto-renew` | Auto-renewal: true/false |

### Other Parameters

| Parameter | Type | CLI Parameter | Description |
|-----------|------|---------------|-------------|
| DBInstanceDescription | string | `--db-instance-description` | Instance name |
| AccountPassword | string | `--account-password` | Root account password |
| SecurityIPList | string | `--security-ip-list` | IP whitelist |
| ResourceGroupId | string | `--resource-group-id` | Resource group ID |
| Engine | string | `--engine` | Database engine, fixed as MongoDB |

### Clone/Restore Parameters

| Parameter | Type | CLI Parameter | Description |
|-----------|------|---------------|-------------|
| SrcDBInstanceId | string | `--src-db-instance-id` | Source instance ID (for cloning) |
| BackupId | string | `--backup-id` | Backup ID (clone from backup point) |
| RestoreTime | string | `--restore-time` | Restore time point (clone from time point) |

---

## Common CLI Command Examples

### Create Basic Replica Set Instance

```bash
aliyun dds create-db-instance \
  --region-id cn-hangzhou \
  --zone-id cn-hangzhou-g \
  --engine-version "6.0" \
  --db-instance-class "dds.mongo.standard" \
  --db-instance-storage 20 \
  --vpc-id "vpc-bp175iuvg8nxqraf2****" \
  --v-switch-id "vsw-bp1gzt31twhlo0sa5****" \
  --network-type VPC \
  --replication-factor "3" \
  --storage-type cloud_essd1 \
  --charge-type PostPaid \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Instance List

```bash
aliyun dds describe-db-instances \
  --biz-region-id cn-hangzhou \
  --db-instance-type replicate \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Instance Details

```bash
aliyun dds describe-db-instance-attribute \
  --db-instance-id dds-bp1ee12ad351**** \
  --user-agent AlibabaCloud-Agent-Skills
```

### Delete Instance

```bash
aliyun dds delete-db-instance \
  --db-instance-id dds-bp1ee12ad351**** \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## KMS Key Management CLI Command Examples

### Create Symmetric Encryption Key

```bash
aliyun kms create-key \
  --description "MongoDB cloud disk encryption key" \
  --key-spec Aliyun_AES_256 \
  --key-usage ENCRYPT/DECRYPT \
  --protection-level SOFTWARE \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Key List

```bash
aliyun kms list-keys \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Key Details

```bash
aliyun kms describe-key \
  --key-id key-hzz62f1cb66fa42qo**** \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Resource Group Management CLI Command Examples

### Create Resource Group

```bash
aliyun resourcemanager create-resource-group \
  --name "mongodb-project" \
  --display-name "MongoDB Project Resource Group" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Resource Group List

```bash
aliyun resourcemanager list-resource-groups \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## KMS Instance Creation CLI Command Examples

### Create Subscription Software Key Management Instance

```bash
aliyun bssopenapi create-instance \
  --product-code kms \
  --product-type kms_ddi_public_cn \
  --subscription-type Subscription \
  --period 12 \
  --renewal-status ManualRenewal \
  --parameter '[{"Code":"ProductVersion","Value":"3"},{"Code":"Region","Value":"cn-hangzhou"},{"Code":"Spec","Value":"1000"},{"Code":"KeyNum","Value":"1000"},{"Code":"SecretNum","Value":"0"},{"Code":"VpcNum","Value":"1"},{"Code":"log","Value":"0"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Create Pay-As-You-Go Software Key Management Instance

```bash
aliyun bssopenapi create-instance \
  --product-code kms \
  --product-type kms_ppi_public_cn \
  --subscription-type PayAsYouGo \
  --parameter '[{"Code":"ProductVersion","Value":"3"},{"Code":"Region","Value":"cn-hangzhou"},{"Code":"Spec","Value":"1000"},{"Code":"KeyNum","Value":"1000"},{"Code":"SecretNum","Value":"0"},{"Code":"VpcNum","Value":"1"},{"Code":"log","Value":"0"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Reference Documentation

| Document | Description |
|----------|-------------|
| [Create Replica Set Instance](https://help.aliyun.com/zh/mongodb/user-guide/create-a-replica-set-instance) | Official operation guide |
| [Create MongoDB Using CLI](https://help.aliyun.com/zh/mongodb/developer-reference/integrate-apsaradb-for-mongodb-by-using-cli) | CLI integration guide |
| [CreateDBInstance API](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-createdbinstance) | Create Replica Set instance |
| [DescribeAvailableResource API](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describeavailableresource) | Query available resource specs |
| [DescribeRdsVpcs API](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describerdsvpcs) | Query MongoDB-available VPCs |
| [DescribeRdsVSwitchs API](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describerdsvswitchs) | Query MongoDB-available VSwitches |
| [TransformInstanceChargeType API](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-transforminstancechargetype) | Convert billing type |
| [RenewDBInstance API](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-renewdbinstance) | Manual renewal |
| [ModifyInstanceAutoRenewalAttribute API](https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-modifyinstanceautorenewalattribute) | Set auto-renewal |
| [Manual Renewal Guide](https://help.aliyun.com/zh/mongodb/user-guide/manually-renew-an-apsaradb-for-mongodb-subscription-instance) | Manual renewal operation guide |
| [Auto-Renewal Guide](https://help.aliyun.com/zh/mongodb/user-guide/enable-auto-renewal) | Auto-renewal operation guide |
| [Purchase and Enable KMS Instance](https://help.aliyun.com/zh/kms/key-management-service/getting-started/purchase-and-enable-a-kms-instance) | KMS instance configuration |
| [ListKmsInstances API](https://help.aliyun.com/zh/kms/key-management-service/developer-reference/api-kms-2016-01-20-listkmsinstances) | Query KMS instance list |
| [CreateKey API](https://help.aliyun.com/zh/kms/key-management-service/developer-reference/api-createkey) | KMS key creation |
| [Create Resource Group](https://help.aliyun.com/zh/resource-management/resource-group/user-guide/create-a-resource-group) | Resource group management |
| [CreateResourceGroup API](https://help.aliyun.com/zh/resource-management/resource-group/developer-reference/api-resourcemanager-2020-03-31-createresourcegroup-rg) | Resource group creation |
