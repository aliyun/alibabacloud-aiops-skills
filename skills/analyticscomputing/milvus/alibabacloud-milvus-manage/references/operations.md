# Daily Operations: Inspection, Configuration, Network, Troubleshooting

## Table of Contents

- [1. Instance Inspection](#1-instance-inspection): Quick inspection checklist
- [2. Configuration Management](#2-configuration-management): View config, modify config
- [3. Network Management](#3-network-management): Public network access, whitelist
- [4. Resource Group Management](#4-resource-group-management): Resource transfer
- [5. Troubleshooting](#5-troubleshooting): Creation failure, instance abnormality, operation rejected

> **Prerequisite**: Before executing any aliyun command, ensure User-Agent environment variable is set:
> ```bash
> export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills"
> ```

## 1. Instance Inspection

### Quick Inspection Checklist

```bash
# 1. View all instance status (focus on non-running status)
aliyun milvus get "/webapi/instance/list?RegionId=cn-hangzhou&pageSize=50" \
  --RegionId cn-hangzhou --force

# 2. View specific instance details (component specs, connection addresses, storage usage)
aliyun milvus post "/webapi/cluster/detail" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force

# 3. Confirm connection address available (extract IntranetUrl)
aliyun milvus post "/webapi/cluster/detail" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force | jq '.Data.ClusterInfo.IntranetUrl'
```

### Inspection Focus Points

| Check Item | Normal Standard | Action When Abnormal |
|------------|-----------------|----------------------|
| Instance status | running | Non-running needs troubleshooting |
| Connection address | IntranetUrl not empty | Empty means instance may not be ready |
| Component CU | Matches expected config | Mismatch may mean scaling incomplete |
| Storage usage | No abnormal growth | Continuous growth needs data cleanup attention |

## 2. Configuration Management

### View Instance Config

```bash
aliyun milvus post "/webapi/config/describe_milvus_user_config" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force
```

Returns `Data` field as YAML format user custom config.

### Modify Instance Config

⚠️ **Note**: Config changes may affect service stability, before modifying must confirm current config and understand change impact.

```bash
# 1. First view current config
aliyun milvus post "/webapi/config/describe_milvus_user_config" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force

# 2. Modify config (need to fill change reason)
aliyun milvus post "/webapi/config/modify_milvus_config" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --Reason "Adjust proxy max task count" \
  --UserConfig "proxy:
  maxTaskNum: 1024
" \
  --force
```

## 3. Network Management

### Public Network Access

```bash
# View public network access status and whitelist
aliyun milvus post "/webapi/milvus/describe_access_control_list" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force

# Enable public network access and set whitelist
aliyun milvus post "/webapi/network/updatePublicNetworkStatus" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --ComponentType Proxy \
  --PublicNetworkEnabled true \
  --Cidr "10.0.0.0/8" \
  --force

# ⚠️ Disable public network access (confirm no external services depend on public network address before operation)
aliyun milvus post "/webapi/network/updatePublicNetworkStatus" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --ComponentType Proxy \
  --PublicNetworkEnabled false \
  --force
```

### Whitelist Management

```bash
# View current whitelist
aliyun milvus post "/webapi/milvus/describe_access_control_list" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force

# Update whitelist (AclId required, first obtain via DescribeAccessControlList)
aliyun milvus post "/webapi/milvus/update_access_control_list" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --AclId acl-xxx \
  --Cidr "192.168.1.0/24" \
  --force
```

## 4. Resource Group Management

```bash
# Transfer instance to target resource group
aliyun milvus post "/webapi/resourceGroup/change" \
  --RegionId cn-hangzhou \
  --NewResourceGroupId rg-xxx \
  --ResourceId c-xxx \
  --force
```

## 5. Troubleshooting

### Instance Creation Failure

```bash
# View instance status and error info
aliyun milvus get "/webapi/instance/get?RegionId=cn-hangzhou&instanceId=c-xxx" \
  --RegionId cn-hangzhou --force
```

| Common Reason | Troubleshooting Method |
|---------------|------------------------|
| VPC/VSwitch doesn't exist or not in same availability zone | `aliyun vpc describe-vswitches --RegionId cn-hangzhou --VpcId vpc-xxx` to confirm |
| VSwitch available IP exhausted | Check `AvailableIpAddressCount` field |
| RAM permission insufficient | Confirm AccessKey has `milvus:CreateInstance` permission |
| Account balance insufficient | Recharge and retry |
| Kernel version not supported | Confirm dbVersion is 2.3/2.4/2.5/2.6 |
| Component config invalid (pricing plan price result not found) | HA mode must have 5 components, streaming/data/mix_coordinator/query minimum 4 CU |
| Region not supported | Confirm RegionId is in supported list |
| InternalError (general server error) | 1. Confirm account has enabled Milvus service (check console access) 2. Confirm account balance sufficient and not overdue 3. Record RequestId and submit ticket for investigation |

### Instance Cannot Connect

```bash
# 1. Confirm instance status
aliyun milvus get "/webapi/instance/get?RegionId=cn-hangzhou&instanceId=c-xxx" \
  --RegionId cn-hangzhou --force

# 2. Get connection address
aliyun milvus post "/webapi/cluster/detail" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force
```

| Common Reason | Troubleshooting Method |
|---------------|------------------------|
| Instance status not running | Wait for instance ready |
| Network unreachable | Confirm client and instance in same VPC, or public network access enabled |
| Password error | Confirm using dbAdminPassword set during creation |
| Port incorrect | Use ProxyPort (default 19530) |
| Public network not enabled | Enable public network access via UpdatePublicNetworkStatus |
| Whitelist not allowing | Check whitelist config via DescribeAccessControlList |
| Security group rule not allowing | Confirm VPC security group allows port 19530 |

### Operation Rejected

| Error | Reason | Solution |
|-------|--------|----------|
| OperationDenied | Instance status doesn't allow current operation | Wait for instance to become running then retry |
| OperationDenied.Subscription | Annual/monthly instance limitation | Need to operate in console |
| Forbidden.RAM | RAM permission insufficient | Contact admin for authorization |

### API Rate Limiting

| Error | Description | Solution |
|-------|-------------|----------|
| Throttling | Request rate exceeded | Wait 5-10 seconds then retry, max 3 times |

## Related Documentation

- [Instance Full Lifecycle](instance-lifecycle.md) — Create, scale and release instances
- [Quick Start](getting-started.md) — First time creating instance
- [Create Parameter Reference](create-params.md) — Complete creation parameters
- [API Parameter Reference](api-reference.md) — Complete API documentation