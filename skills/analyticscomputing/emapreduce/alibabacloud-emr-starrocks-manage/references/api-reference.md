# API Parameter Reference

All APIs use version `2022-10-19` with RPC-style requests.

## Table of Contents

- [Instance Management](#instance-management): CreateInstanceV1, DescribeInstances, DescribeNodeGroups, DescribeInstanceConfigs, RestartInstance, RestartNodeGroup, RestartNodes, ResumeInstance, ModifyChargeType, ChangeResourceGroup, EnableSSLConnection, DisableSSLConnection, RestoreInstance
- [Scaling Management](#scaling-management): ModifyCu, ModifyCuPreCheck, ModifyDiskSize, ModifyDiskNumber, ModifyDiskPerformanceLevel, ModifyDiskType, ModifyNodeNumber, ModifyNodeNumberPreCheck
- [Version Management](#version-management): QueryUpgradableVersions
- [Configuration Management](#configuration-management): ModifyInstanceConfig, DescribeConfigHistory, ModifyInstanceConfigPreCheck, RollbackConfigModification
- [Gateway Management](#gateway-management): ListGateway, TogglePublicSlb, IsolateLeader


## Instance Management

### CreateInstanceV1 - Create Instance

**Passing Method**: `--RegionId` via named parameter, all other parameters via `--body` JSON.

**Request Parameters** (body JSON):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | string | Yes | Region ID (must be in body, cannot rely solely on CLI --RegionId) |
| InstanceName | string | Yes | Instance name |
| AdminPassword | string | Yes | Admin password (8-30 characters, containing at least three of: uppercase letters, lowercase letters, digits, special characters `@#$%^*_+-.`) |
| Version | string | Yes | StarRocks version (e.g., "3.2", "3.3") |
| RunMode | string | Yes | Architecture type: `shared_nothing` (shared-nothing edition) / `shared_data` (shared-data edition) |
| PackageType | string | Yes | Version series: `official` (Standard Edition) / `trial` (Trial Edition). **Must be explicitly specified**; omitting it will cause creation failure |
| PayType | string | Yes | Payment type: `postPaid` (pay-as-you-go) / `prePaid` (subscription) |
| VpcId | string | Yes | VPC ID |
| ZoneId | string | Yes | Availability zone ID (must match the ZoneId in VSwitches) |
| VSwitchId | string | Yes | VSwitch ID (must match the VswId in VSwitches) |
| VSwitches | array | Yes | VSwitch list `[{"VswId":"vsw-xxx","ZoneId":"cn-hangzhou-h","Primary":true}]` |
| SecurityGroupId | string | Yes | Security group ID |
| OssAccessingRoleName | string | Yes | OSS access role name, required for all architecture types, typically `AliyunEMRDefaultRole` |
| Cu | integer | Yes | CU count (minimum 8) |
| FrontendNodeGroups | array | Yes | FE node group configuration, required for all architecture types (see node group parameters below) |
| BackendNodeGroups | array | Yes | BE/CN node group configuration, required for all architecture types (see node group parameters below) |
| Duration | integer | No | Purchase duration (required for subscription) |
| PricingCycle | string | No | Duration unit: `Month` / `Year` |
| AutoRenew | boolean | No | Whether to auto-renew |
| AutoRenewPeriod | integer | No | Auto-renewal duration |
| ClientToken | string | No | Idempotency token |

**Node Group Parameters** (FrontendNodeGroups / BackendNodeGroups array elements):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| NodeGroupName | string | Yes | Node group name (FE typically `defaultFeNodeGroup`, BE typically `default_warehouse`) |
| Cu | integer | Yes | Node group CU count. FE Cu available values: `[8, 16, 32, 64]` (4 is not supported) |
| SpecType | string | Yes | Spec type: FE only supports `standard`; BE/CN supports `standard` / `ramEnhanced` (Memory Enhanced) / `networkEnhanced` (Network Enhanced) / `localSSD` (High-performance Storage) / `bigData` (Large-scale Storage) |
| ResidentNodeNumber | integer | Yes | Resident node count (typically 1) |
| DiskNumber | integer | Yes | Disk count per node (typically 1) |
| StorageSize | integer | Yes | Size per disk (GB), minimum 200 GB, maximum 65000 GB |
| StoragePerformanceLevel | string | Yes | Disk performance level: `pl0` / `pl1` / `pl2` / `pl3` |

**Example (Shared-data Edition)**:

```bash
aliyun starrocks CreateInstanceV1 --RegionId cn-hangzhou --body '{
  "RegionId": "cn-hangzhou",
  "InstanceName": "my-starrocks",
  "AdminPassword": "MyP@ssw0rd123",
  "Version": "3.3",
  "RunMode": "shared_data",
  "PackageType": "official",
  "PayType": "postPaid",
  "VpcId": "vpc-xxx",
  "ZoneId": "cn-hangzhou-h",
  "VSwitchId": "vsw-xxx",
  "VSwitches": [{"VswId": "vsw-xxx", "ZoneId": "cn-hangzhou-h", "Primary": true}],
  "SecurityGroupId": "sg-xxx",
  "OssAccessingRoleName": "AliyunEMRDefaultRole",
  "Cu": 8,
  "FrontendNodeGroups": [
    {
      "NodeGroupName": "defaultFeNodeGroup",
      "Cu": 8,
      "SpecType": "standard",
      "ResidentNodeNumber": 1,
      "DiskNumber": 1,
      "StorageSize": 200,
      "StoragePerformanceLevel": "pl1"
    }
  ],
  "BackendNodeGroups": [
    {
      "NodeGroupName": "default_warehouse",
      "Cu": 8,
      "SpecType": "standard",
      "ResidentNodeNumber": 1,
      "DiskNumber": 1,
      "StorageSize": 200,
      "StoragePerformanceLevel": "pl1"
    }
  ],
  "ClientToken": "uuid-xxx"
}'
```

**Example (Shared-nothing Edition)**:

```bash
aliyun starrocks CreateInstanceV1 --RegionId cn-hangzhou --body '{
  "RegionId": "cn-hangzhou",
  "InstanceName": "my-starrocks",
  "AdminPassword": "MyP@ssw0rd123",
  "Version": "3.3",
  "RunMode": "shared_nothing",
  "PackageType": "official",
  "PayType": "postPaid",
  "VpcId": "vpc-xxx",
  "ZoneId": "cn-hangzhou-h",
  "VSwitchId": "vsw-xxx",
  "VSwitches": [{"VswId": "vsw-xxx", "ZoneId": "cn-hangzhou-h", "Primary": true}],
  "SecurityGroupId": "sg-xxx",
  "OssAccessingRoleName": "AliyunEMRDefaultRole",
  "Cu": 8,
  "FrontendNodeGroups": [
    {
      "NodeGroupName": "defaultFeNodeGroup",
      "Cu": 8,
      "SpecType": "standard",
      "ResidentNodeNumber": 1,
      "DiskNumber": 1,
      "StorageSize": 200,
      "StoragePerformanceLevel": "pl1"
    }
  ],
  "BackendNodeGroups": [
    {
      "NodeGroupName": "default_warehouse",
      "Cu": 8,
      "SpecType": "standard",
      "ResidentNodeNumber": 1,
      "DiskNumber": 1,
      "StorageSize": 200,
      "StoragePerformanceLevel": "pl1"
    }
  ],
  "ClientToken": "uuid-xxx"
}'
```

---

### DescribeInstances - Query Instances

**Passing Method**: Named parameters.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | string | Yes | Region ID |
| InstanceId | string | No | Instance ID |
| InstanceName | string | No | Instance name (fuzzy match) |
| InstanceStatus | string | No | Instance status (note: it is InstanceStatus, not InstanceState) |
| PageNumber | integer | No | Page number, default 1 |
| PageSize | integer | No | Items per page, default 10 |

**Examples**:

```bash
# Query all instances
aliyun starrocks DescribeInstances --RegionId cn-hangzhou

# Query a specific instance
aliyun starrocks DescribeInstances --RegionId cn-hangzhou --InstanceId c-xxx

# Filter by status
aliyun starrocks DescribeInstances --RegionId cn-hangzhou --InstanceStatus running
```

---

### DescribeNodeGroups - Query Compute Groups

**Passing Method**: All parameters via `--body` JSON. CLI does not support `--InstanceId` named parameter.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | string | Yes | Instance ID |
| RegionId | string | No | Region ID |
| ClusterId | string | No | Cluster ID |
| PageNumber | integer | No | Page number |
| PageSize | integer | No | Items per page |

**Example**:

```bash
aliyun starrocks DescribeNodeGroups --body '{"InstanceId": "c-xxx", "RegionId": "cn-hangzhou"}'
```

---

### DescribeInstanceConfigs - Query Configuration

**Passing Method**: Named parameters.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | string | Yes | Instance ID |
| ConfigType | string | No | Configuration type (e.g., fe, be, cn) |
| ConfigKey | string | No | Configuration item name |
| AllowModify | boolean | No | Query only modifiable configurations |
| PageNumber | integer | No | Page number |
| PageSize | integer | No | Items per page |

**Examples**:

```bash
# Query all configurations
aliyun starrocks DescribeInstanceConfigs --InstanceId c-xxx

# Query configurations of a specific type
aliyun starrocks DescribeInstanceConfigs --InstanceId c-xxx --ConfigType fe

# Query only modifiable configurations
aliyun starrocks DescribeInstanceConfigs --InstanceId c-xxx --AllowModify true
```

---


## Related Documents

- [Getting Started](getting-started.md) - Simplified workflow for creating your first instance
- [Instance Full Lifecycle](instance-lifecycle.md) - Planning, creation, management
- [Daily Operations](operations.md) - Configuration changes, maintenance, diagnostics
