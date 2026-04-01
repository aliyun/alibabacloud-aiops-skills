# Instance Full Lifecycle: Plan → Create → Manage

## Table of Contents

- [1. Planning Phase](#1-planning-phase): Spec selection, payment method, capacity planning, network planning
- [2. Creation Phase](#2-creation-phase): Pay-as-you-go / Subscription / Shared-nothing edition
- [3. Query and Monitoring](#3-query-and-monitoring): Instance list, details, state machine
- [4. Property Management](#4-property-management): Rename

## 1. Planning Phase

### Architecture Type Selection

| Architecture Type | RunMode Value | Node Composition | Data Storage | Data Disk Type | Use Cases |
|-------------------|---------------|------------------|--------------|----------------|-----------|
| **Shared-nothing Edition** | `shared_nothing` | FE + BE | Cloud disk or local disk | ESSD cloud disk or local disk | OLAP multi-dimensional analysis, high-concurrency queries, real-time data analysis, latency-sensitive |
| **Shared-data Edition** | `shared_data` | FE + CN | OSS object storage | ESSD cloud disk (cache) | Highly cost-sensitive storage with relatively lower query efficiency requirements, such as data warehouse applications |

### Version Series Selection

| Version Series | PackageType Value | Features | Spec Support | Region Restrictions |
|---------------|-------------------|----------|--------------|---------------------|
| **Standard Edition** | `official` | Full functionality, production-grade stability | Supports all spec types | Available in all regions |
| **Trial Edition** | `trial` | Simplified configuration, quick start | Only supports standard specs | Limited to certain regions (e.g., Beijing, Shanghai) |

> **Important**: `PackageType` must be explicitly specified when creating an instance; omitting it will cause creation failure.

### Compute Spec Selection

| Spec Type | BE SpecType Value | Features | Use Cases |
|-----------|-------------------|----------|-----------|
| **Standard** | `standard` | Balanced compute and memory configuration | General OLAP analysis |
| **Memory Enhanced** | `ramEnhanced` | Higher memory ratio | Complex queries, high concurrency |
| **Network Enhanced** | `networkEnhanced` | Higher network bandwidth | External table analysis with large data scan volumes |
| **High-performance Storage** | `localSSD` | High-performance local SSD storage | High I/O scenarios with strict storage I/O performance requirements |
| **Large-scale Storage** | `bigData` | Large capacity local HDD storage | Extremely large data volumes, cost-sensitive |

> **Note**: The spec types above are mutually exclusive; only one SpecType can be chosen when creating an instance. FE node group SpecType only supports `standard`.

### Storage Specifications

| Storage Type | Performance Level | Max IOPS | Max Throughput | Use Cases |
|-------------|-------------------|----------|----------------|-----------|
| ESSD PL0 | Entry-level | 10,000 | 180 MB/s | Development and testing |
| ESSD PL1 | Standard | 50,000 | 350 MB/s | General production |
| ESSD PL2 | High-performance | 100,000 | 750 MB/s | High-performance requirements |
| ESSD PL3 | Ultra-performance | 1,000,000 | 4,000 MB/s | Ultra-performance requirements |

### Payment Method

| Payment Method | PayType Value | Description |
|---------------|---------------|-------------|
| **Pay-as-you-go** | `postPaid` | Pay after use, billing generated hourly, suitable for short-term needs/testing |
| **Subscription** | `prePaid` | Pay before use, suitable for long-term needs, more cost-effective |

> **Payment Method Conversion**: Only subscription to pay-as-you-go is supported (via ModifyChargeType API). Pay-as-you-go cannot be converted to subscription (requires recreating the instance).

### Usage Limits

- **Naming Limits**: Instance name limited to a maximum of 64 characters, supports Chinese, letters, numbers, hyphens, and underscores
- **Node Count Limits**:
  - FE nodes: 1-11 (odd numbers only)
  - BE nodes: 3-50
  - CN nodes: 1-100

### Capacity Planning

#### CU Count Selection

| Scenario | Recommended CU | Description |
|----------|---------------|-------------|
| Development and testing | 8 CU | Minimum configuration, feature validation |
| Small-scale production | 16-32 CU | Supports moderate concurrency |
| Medium-scale | 64-128 CU | Supports higher concurrency and complex queries |
| Large-scale | 256+ CU | High concurrency, complex analytics scenarios |

#### Disk Capacity Selection (Shared-nothing Edition)

| Scenario | Recommended Disk | Description |
|----------|-----------------|-------------|
| Development and testing | 100 GB | Feature validation |
| Small-scale production | 500 GB - 1 TB | Small data volumes |
| Medium-scale | 1-5 TB | Medium data volumes |
| Large-scale | 5+ TB | Large data volumes |

> **Shared-data Edition**: Data is stored in OSS; no need to pre-plan disk capacity, only consider cache space.

### Network Planning

- **VPC**: Same VPC as the business system for internal network access
- **VSwitch**: Choose an availability zone with sufficient inventory; use `VSwitches` array format when creating: `[{"VswId":"vsw-xxx","ZoneId":"cn-hangzhou-h","Primary":true}]`
- **Security Group**: Configure necessary port rules (MySQL port, HTTP port, etc.)
- **OSS Access Role** (required for all architecture types): Provide a RAM Role name (`OssAccessingRoleName`) to authorize StarRocks to access OSS. Typically use `AliyunEMRDefaultRole`; if not created yet, complete service authorization in the RAM console

## 2. Creation Phase

> **Important**: `AdminPassword` must be set when creating an instance; this password is used for the admin account to log in to StarRocks. Password requirements: 8-30 characters, containing at least three of the following: uppercase letters, lowercase letters, digits, and special characters (`@#$%^*_+-.`).

### Template 1: Pay-as-you-go Development and Testing

Shared-data edition + Standard specs + 8 CU, suitable for development testing and feature validation:

```bash
aliyun starrocks CreateInstanceV1 --RegionId cn-hangzhou --body '{
  "RegionId": "cn-hangzhou",
  "InstanceName": "dev-starrocks",
  "AdminPassword": "YourP@ssw0rd",
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

### Template 2: Subscription Production Environment

Shared-data edition + Standard specs + 16 CU, suitable for production environments:

```bash
aliyun starrocks CreateInstanceV1 --RegionId cn-hangzhou --body '{
  "RegionId": "cn-hangzhou",
  "InstanceName": "prod-starrocks",
  "AdminPassword": "YourP@ssw0rd",
  "Version": "3.3",
  "RunMode": "shared_data",
  "PackageType": "official",
  "PayType": "prePaid",
  "Duration": 1,
  "PricingCycle": "Month",
  "AutoRenew": true,
  "AutoRenewPeriod": 1,
  "VpcId": "vpc-xxx",
  "ZoneId": "cn-hangzhou-h",
  "VSwitchId": "vsw-xxx",
  "VSwitches": [{"VswId": "vsw-xxx", "ZoneId": "cn-hangzhou-h", "Primary": true}],
  "SecurityGroupId": "sg-xxx",
  "OssAccessingRoleName": "AliyunEMRDefaultRole",
  "Cu": 16,
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
      "Cu": 16,
      "SpecType": "standard",
      "ResidentNodeNumber": 1,
      "DiskNumber": 1,
      "StorageSize": 200,
      "StoragePerformanceLevel": "pl1"
    }
  ],
  "Tags": [
    {"Key": "env", "Value": "production"},
    {"Key": "team", "Value": "data-platform"}
  ],
  "ClientToken": "uuid-xxx"
}'
```

### Template 3: Shared-nothing High-performance

Shared-nothing edition + Memory Enhanced + 32 CU, suitable for high-performance low-latency scenarios:

```bash
aliyun starrocks CreateInstanceV1 --RegionId cn-hangzhou --body '{
  "RegionId": "cn-hangzhou",
  "InstanceName": "high-perf-starrocks",
  "AdminPassword": "YourP@ssw0rd",
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
  "Cu": 32,
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
      "Cu": 32,
      "SpecType": "ramEnhanced",
      "ResidentNodeNumber": 1,
      "DiskNumber": 1,
      "StorageSize": 500,
      "StoragePerformanceLevel": "pl1"
    }
  ],
  "ClientToken": "uuid-xxx"
}'
```

## 3. Query and Monitoring

### Instance List

```bash
# All instances
aliyun starrocks DescribeInstances --RegionId cn-hangzhou

# Filter by status
aliyun starrocks DescribeInstances --RegionId cn-hangzhou --InstanceStatus running

# Search by name
aliyun starrocks DescribeInstances --RegionId cn-hangzhou --InstanceName "prod"

# Paginated query
aliyun starrocks DescribeInstances --RegionId cn-hangzhou --PageNumber 1 --PageSize 20
```

### Instance Details

```bash
aliyun starrocks DescribeInstances --RegionId cn-hangzhou --InstanceId c-xxx
```

### Compute Group Query

```bash
aliyun starrocks DescribeNodeGroups --body '{"InstanceId": "c-xxx", "RegionId": "cn-hangzhou"}'
```

### Configuration Query

```bash
# Query all configurations
aliyun starrocks DescribeInstanceConfigs --RegionId cn-hangzhou --InstanceId c-xxx

# Query configurations of a specific type
aliyun starrocks DescribeInstanceConfigs --RegionId cn-hangzhou --InstanceId c-xxx --ConfigType fe
```

### Instance State Machine

| Status | English | Description |
|--------|---------|-------------|
| Not initialized | not_init | Not initialized |
| Creating | creating | Instance is being created |
| Creation failed | creating_failed | Creation failed |
| Running | running | Running normally |
| Agent creating | agent_creating | Agent is being created |
| Gateway updating | gateway_updating | Gateway operations such as toggling public SLB are in progress; most write operations are rejected during this period, typically lasting a few minutes |
| Deleting | deleting | Instance is being released |
| Deletion failed | deleting_failed | Deletion failed |
| Deleted with error | deleted_with_error | Ended after creation failure |
| Deleted | deleted | Deleted |

## Related Documents

- [Getting Started](getting-started.md) - Simplified workflow for creating your first instance
- [Daily Operations](operations.md) - Configuration changes, maintenance, diagnostics
- [API Parameter Reference](api-reference.md) - Complete parameter documentation
