# Instance Full Lifecycle: Planning → Creation → Query → Scaling → Release

## Table of Contents

- [1. Planning Phase](#1-planning-phase): Version selection, component planning, network preparation
- [2. Creation Phase](#2-creation-phase): Dev/test / Production cluster / Custom component three templates
- [3. Query and Monitoring](#3-query-and-monitoring): Instance list, details, state machine
- [4. Scaling and Management](#4-scaling-and-management): Scale up/down, rename
- [5. Release Instance](#5-release-instance): Console only (not available via Skill)

## 1. Planning Phase

### Version Selection

| Instance Version | Applicable Scenario | Components | Recommended Config |
|------------------|---------------------|------------|--------------------|
| **Standalone** (standalone_pro) | Dev/test, feature verification, small data | 1 | 4-8 CU (general) |
| **Cluster** (HA) | Production, large data, high concurrency | 5 | 30 CU minimum |

> **Not sure which to choose?** Use standalone for dev/test (low cost), cluster for production (high availability).

### Network Planning

Before creation confirm target RegionId and check network resources. **Every `aliyun` CLI invocation must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage`**:

```bash
# List available VPCs
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage

# List VSwitches under VPC (record ZoneId and available IP count)
aliyun vpc describe-vswitches --biz-region-id cn-hangzhou --vpc-id vpc-xxx --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage

# List security groups (for reference only, CreateInstance doesn't require passing security group)
aliyun ecs describe-security-groups --biz-region-id cn-hangzhou --vpc-id vpc-xxx --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage
```

**Recommended Practice**: List VPC → User selects → List VSwitches → User selects → Create instance.

For multi-AZ scenarios select one VSwitch in each of different availability zones to improve availability.

### Payment Decision

| Payment Method | Applicable Scenario | Release Method |
|-----------------|--------------------|-----------------|
| **PayAsYouGo** | Dev/test, short-term use | API direct release |
| **Subscription** | Production, long-term running | Need to request refund in console to release |

## 2. Creation Phase

### Template 1: Dev/Test Instance (Standalone, Minimum Cost)

Standalone + pay-as-you-go + 4 CU, suitable for feature verification and dev debugging.

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
    "autoBackup": true,
    "aiFunction": true,
    "encrypted": false,
    "isMultiAzStorage": false,
    "multiZoneMode": "single"
  }' \
  --force
```

### Template 2: Production Instance (Cluster HA, 5 Components 36 CU)

Cluster + 5-component distributed deployment, suitable for production environment.

⚠️ **Note**: streaming, data, mix_coordinator, query minimum 4 CU.

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
    "aiFunction": true,
    "encrypted": false,
    "isMultiAzStorage": false,
    "multiZoneMode": "single"
  }' \
  --force
```

Total CU = 4×2 + 4×2 + 2×2 + 4×2 + 4×2 = **36 CU**

### Template 3: Custom Component (Query Large Spec, Multi-AZ)

Suitable for search-intensive scenarios, QueryNode uses cap type large memory, dual-AZ high-availability storage.

```bash
aliyun milvus post "/webapi/instance/create?RegionId=cn-hangzhou" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou \
  --body '{
    "regionId": "cn-hangzhou",
    "zoneId": "cn-hangzhou-j",
    "instanceName": "milvus-search-heavy",
    "dbVersion": "2.6",
    "vpcId": "vpc-xxx",
    "vSwitchIds": [
      {"vswId":"vsw-xxx","zoneId":"cn-hangzhou-j"},
      {"vswId":"vsw-yyy","zoneId":"cn-hangzhou-b"}
    ],
    "paymentType": "PayAsYouGo",
    "ha": true,
    "components": [
      {"type":"streaming",       "replica":2,"cuNum":4,"cuType":"general"},
      {"type":"data",            "replica":2,"cuNum":4,"cuType":"general"},
      {"type":"proxy",           "replica":2,"cuNum":4,"cuType":"general"},
      {"type":"mix_coordinator", "replica":2,"cuNum":4,"cuType":"general"},
      {"type":"query",           "replica":3,"cuNum":8,"cuType":"cap","diskSizeType":"Normal"}
    ],
    "dbAdminPassword": "YourPassword@123",
    "autoBackup": true,
    "aiFunction": true,
    "isMultiAzStorage": true,
    "multiZoneMode": "Active-Active"
  }' \
  --force
```

> For complete parameter description refer to [Create Parameter Reference](create-params.md)

## 3. Query and Monitoring

### Instance List

```bash
aliyun milvus get "/webapi/instance/list?RegionId=cn-hangzhou&pageSize=50" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou --force
```

⚠️ **Important**: `total` field may be inaccurate (returns 0 but actually has data), directly check `instances` array.

### Instance Basic Info

```bash
aliyun milvus get "/webapi/instance/get?RegionId=cn-hangzhou&instanceId=c-xxx" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou --force
```

Focus on return fields: `instanceId`, `instanceName`, `status`, `dbVersion`, `ha`, `paymentType`, `createTime`, `vpcId`, `zoneId`.

### Instance Details (Component Specs, Connection Addresses, Storage Usage)

```bash
aliyun milvus post "/webapi/cluster/detail" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force
```

Focus on return fields:
- `Data.ClusterInfo.IntranetUrl` / `InternetUrl`: Connection addresses
- `Data.ClusterInfo.ProxyPort`: Service port (19530)
- `Data.ClusterInfo.TotalCuNum`: Total CU count
- `Data.ClusterInfo.MilvusResourceInfoList`: Each component spec details
- `Data.ClusterInfo.OssStorageSize`: OSS storage usage

### Instance State Machine

| State | Meaning | Follow-up Action |
|-------|---------|------------------|
| `creating` | Creating | Wait, usually 5-15 minutes |
| `running` | Instance ready | Can use normally |
| `updating` | Scaling (scale up/down) | Wait to return to running |
| `modifying_config` | Modifying config | Wait to return to running |
| `enable_public_network` | Enabling public network | Wait to return to running |
| `deleting` | Releasing | Wait |
| `deleted` | Released | No action needed |

> **Note**: In transitional state (updating / modifying_config / enable_public_network), cannot execute other write operations, need to wait instance returns to running before operating.

## 4. Scaling and Management

### Scale Up/Down (UpdateInstance)

Adjust component CU count or replica count via UpdateInstance. Before scaling use GetInstanceDetail to confirm current specs.

```bash
# 1. View current component specs
aliyun milvus post "/webapi/cluster/detail" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force

# 2. Scale up query component to 3 replicas × 8 CU
aliyun milvus put "/webapi/instance/update?RegionId=cn-hangzhou" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou \
  --body '{
    "instanceId": "c-xxx",
    "components": [
      {"type":"query","replica":3,"cuNum":8,"cuType":"cap","diskSizeType":"Normal"}
    ]
  }' \
  --force
```

**Scaling Notes**:
- Only need to pass components to modify, unpassed components remain unchanged
- ⚠️ streaming/data/mix_coordinator/query minimum 4 CU, proxy minimum 2 CU
- During scaling instance status briefly becomes non-running, wait to recover before operating
- Before scaling down confirm current load can handle fewer resources

### Modify Instance Name

```bash
aliyun milvus post "/webapi/cluster/update_name" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --ClusterName new-name \
  --force
```

## 5. Release Instance

> 🚫 **Instance deletion is NOT available through this Skill.** To release/delete a Milvus instance, please use the [Alibaba Cloud Milvus Console](https://milvus.console.aliyun.com/#/overview).

### Before Releasing (Checklist)

1. **Data Backup**: Confirm important data backed up (Collection data, indexes)
2. **Confirm Dependencies**: No other services depend on this instance's connection address
3. **Instance Status**: Confirm instance status is running

## Related Documentation

- [Quick Start](getting-started.md) — Simplified process for first-time instance creation
- [Create Parameter Reference](create-params.md) — Complete creation parameter description
- [Operations Manual](operations.md) — Configuration, network management and troubleshooting
- [API Parameter Reference](api-reference.md) — Complete API documentation
