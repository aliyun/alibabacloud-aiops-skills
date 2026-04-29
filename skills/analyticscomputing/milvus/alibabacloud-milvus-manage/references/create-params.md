# CreateInstance Parameter Reference

**Path**: `POST /webapi/instance/create`, version `2023-10-12`.

Calling method: `RegionId` must be placed in both **URL query string** (`?RegionId=<region>`) and **CLI flag** (`--RegionId <region>`), other parameters placed in `--body` JSON (camelCase).

> **User-Agent requirement**: Every `aliyun` CLI invocation must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage`.

## Table of Contents

1. [Required Parameters](#required-parameters)
2. [Component Spec Configuration](#component-specification-configuration)
3. [Network Configuration](#network-configuration)
4. [Payment and High Availability](#payment-and-high-availability)
5. [Other Parameters](#other-parameters)
6. [Typical Configuration Examples](#typical-configuration-examples)

---

## Required Parameters

| body field | Type | Description |
|------------|------|-------------|
| `regionId` | String | Region ID (e.g., `cn-hangzhou`), must match RegionId in CLI flag and URL |
| `zoneId` | String | Primary availability zone (e.g., `cn-hangzhou-j`) |
| `instanceName` | String | Instance name |
| `dbVersion` | String | Kernel version: `2.3` / `2.4` / `2.5` / `2.6` (recommend `2.6`) |
| `vpcId` | String | VPC ID |
| `vSwitchIds` | Array | VSwitch list, see structure description |
| `paymentType` | String | Payment type: `PayAsYouGo` / `Subscription` |
| `ha` | Boolean | `false`=standalone, `true`=cluster |
| `components` | Array | Component config list, see structure description |
| `dbAdminPassword` | String | Admin password |
| `aiFunction` | Boolean | Enable AI embedding functions (auto `true` when `dbVersion` is `2.6`) |

**CLI flag**:
- `--RegionId`: Region ID (required)
- `--clientToken`: Idempotent token, max 64 ASCII characters (optional, prevent duplicate creation)

## Component Specification Configuration

### ⚠️ Component CU Minimum Limit (Important!)

When creating cluster instances, each component has **minimum CU requirements**:

| Component | Minimum CU | Notes |
|-----------|------------|-------|
| streaming | **4 CU** | Does not support 2 CU |
| data | **4 CU** | Does not support 2 CU |
| proxy | **2 CU** | Supports 2 CU |
| mix_coordinator | **4 CU** | Does not support 2 CU |
| query | **4 CU** | Does not support 2 CU |

**Error Example**: If using 2 CU configuration for streaming/data/mix_coordinator/query, you will get an error:
> `Error.InternalError code: 500, pricing plan price result not found`

### Standalone Version (standalone_pro, suitable for dev/test)

When `ha=false` creates standalone version, component type is `standalone_pro`:

```bash
aliyun milvus post "/webapi/instance/create?RegionId=cn-hangzhou" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou \
  --body '{
    "regionId": "cn-hangzhou",
    "zoneId": "cn-hangzhou-j",
    "instanceName": "milvus-dev",
    "dbVersion": "2.6",
    "vpcId": "vpc-xxx",
    "vSwitchIds": [{"vswId":"vsw-xxx","zoneId":"cn-hangzhou-j"}],
    "paymentType": "PayAsYouGo",
    "ha": false,
    "components": [{"type":"standalone_pro","replica":1,"cuNum":4,"cuType":"general"}],
    "dbAdminPassword": "YourPassword@123",
    "aiFunction": true
  }' \
  --force
```

**CU Spec Reference**:

| cuNum | Memory | Applicable Scenario |
|-------|--------|---------------------|
| 4 | ~16GB | Personal dev/test (default) |
| 8 | ~32GB | Small-medium scale |
| 16 | ~64GB | Medium scale |
| 32 | ~128GB | Large scale |

### Cluster Version (HA mode, suitable for production)

When `ha=true` creates cluster version, need to configure 5 components:

```bash
aliyun milvus post "/webapi/instance/create?RegionId=cn-hangzhou" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou \
  --body '{
    "regionId": "cn-hangzhou",
    "zoneId": "cn-hangzhou-j",
    "instanceName": "milvus-prod",
    "dbVersion": "2.6",
    "vpcId": "vpc-xxx",
    "vSwitchIds": [{"vswId":"vsw-xxx","zoneId":"cn-hangzhou-j"}],
    "paymentType": "PayAsYouGo",
    "ha": true,
    "components": [
      {"type":"streaming",       "replica":2,"cuNum":4,"cuType":"general"},
      {"type":"data",            "replica":2,"cuNum":4,"cuType":"general"},
      {"type":"proxy",           "replica":2,"cuNum":2,"cuType":"general"},
      {"type":"mix_coordinator", "replica":2,"cuNum":4,"cuType":"general"},
      {"type":"query",           "replica":2,"cuNum":4,"cuType":"general","diskSizeType":"Normal"}
    ],
    "dbAdminPassword": "YourPassword@123",
    "autoBackup": true,
    "aiFunction": true
  }' \
  --force
```

Total CU = 4×2 + 4×2 + 2×2 + 4×2 + 4×2 = **36 CU**

### Component Type Description

| Type | Responsibility | Scaling Trigger |
|------|----------------|-----------------|
| `proxy` | Request entry point, load balancing | High request QPS |
| `mix_coordinator` | Coordination node (RootCoord + QueryCoord + DataCoord merged) | Many metadata operations |
| `query` | Vector search execution (memory-intensive) | Memory watermark > 70% or high search latency |
| `data` | Data write and flush (CPU-intensive) | CPU watermark > 90% |
| `streaming` | Stream message processing (WAL / message queue replacement layer) | High write throughput |

### cuType Options

| Value | Description | Applicable Scenario |
|-------|-------------|---------------------|
| `general` | General type (CPU:Memory = 1:4) | Default, most scenarios |
| `perf` | Performance type (CPU-intensive) | Index building, high-concurrency writes |
| `cap` | Capacity type (large memory) | QueryNode large data search |

### diskSizeType (query component only)

| Value | Description |
|-------|-------------|
| `Normal` | Normal disk (default) |
| `Large` | Large disk |

## Network Configuration

### Single Availability Zone (multiZoneMode: single)

```json
{
  "vSwitchIds": [{"vswId":"vsw-xxx","zoneId":"cn-hangzhou-j"}],
  "multiZoneMode": "single"
}
```

### Multi Availability Zone (multiZoneMode: Active-Active)

Need to specify one VSwitch in each of two availability zones:

```json
{
  "vSwitchIds": [
    {"vswId":"vsw-primary","zoneId":"cn-hangzhou-j"},
    {"vswId":"vsw-secondary","zoneId":"cn-hangzhou-b"}
  ],
  "isMultiAzStorage": true,
  "multiZoneMode": "Active-Active"
}
```

### Network Resource Discovery

Before creating instance, query available network resources:

```bash
# List VPCs
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage

# List VSwitches (includes availability zone and available IP count)
aliyun vpc describe-vswitches --biz-region-id cn-hangzhou --vpc-id vpc-xxx --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage
```

## Payment and High Availability

### paymentType

| Value | Description | Notes |
|-------|-------------|-------|
| `PayAsYouGo` | Pay-as-you-go | Release anytime, suitable for testing |
| `Subscription` | Annual/monthly subscription | Need console refund to release, can use `autoRenew: true` |

### autoBackup

When `autoBackup: true` is enabled, data is automatically backed up to OSS daily.

### loadReplicas

`loadReplicas: N` (default 1), load replica count, improves search concurrency performance.

## Other Parameters

| body field | Default | Description |
|------------|---------|-------------|
| `autoBackup` | `false` | Auto backup |
| `loadReplicas` | `1` | Load replica count |
| `encrypted` | `false` | Data encryption switch |
| `kmsKeyId` | — | KMS Key ID used for encryption |
| `isMultiAzStorage` | `true` | Multi-AZ storage |
| `multiZoneMode` | `single` | Multi availability zone mode |
| `autoRenew` | `false` | Auto renew (Subscription only) |

## Complete Creation Template

For complete creation templates (dev/test / production cluster / search-intensive), please refer to [Instance Full Lifecycle](instance-lifecycle.md#二创建阶段).

---

## API Endpoint Reference

- **Endpoint**: `milvus.<RegionId>.aliyuncs.com`
- **API Version**: `2023-10-12`
- **OpenAPI Meta**: `https://api.aliyun.com/meta/v1/products/milvus/versions/2023-10-12/api-docs.json`
