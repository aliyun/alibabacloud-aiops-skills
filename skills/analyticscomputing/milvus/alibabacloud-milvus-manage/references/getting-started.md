# Quick Start: Create Your First Milvus Instance from Scratch

This guide helps first-time users complete: prerequisite check → create first instance → verify running → get connection info → cleanup resources.

## Prerequisites

### 1. CLI Environment

- Alibaba Cloud CLI installed, version `>= 3.3.3`.
- Credentials configured in the active CLI profile.
- API-calling CLI commands in this guide include the required `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage` flag.

### 2. Network Resources

Creating Milvus instance requires VPC and VSwitch. **Before execution confirm RegionId with user** (e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`, etc.):

```bash
# Check if available VPC exists
aliyun vpc describe-vpcs --biz-region-id <RegionId> --region <RegionId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage

# Check if VSwitch exists under VPC, record ZoneId
aliyun vpc describe-vswitches --biz-region-id <RegionId> --vpc-id vpc-xxx --region <RegionId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage
```

> **Don't have these resources?** Please first create VPC and VSwitch via Alibaba Cloud console or CLI.

### 3. Confirm Availability Zone Info

Record the following info, will be used when creating instance:
- RegionId (e.g., `cn-hangzhou`)
- ZoneId (e.g., `cn-hangzhou-j`, from VSwitch's availability zone)
- VpcId, VSwitchId (can prepare two VSwitches in different availability zones for multi-AZ)

## Step 1: Create Test Instance

Below creates a **standalone version (standalone_pro)** minimal instance, 4 CU, pay-as-you-go:

```bash
aliyun milvus post "/webapi/instance/create?RegionId=cn-hangzhou" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou \
  --body '{
    "regionId": "cn-hangzhou",
    "zoneId": "cn-hangzhou-j",
    "instanceName": "my-first-milvus",
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

Return contains `instanceId` (e.g., `c-xxx`), record it for subsequent operations.

> **Note**: Creating instance incurs cost. Standalone 4 CU pay-as-you-go suitable for dev/test, don't use for production.

## Step 2: Verify Instance Status

Instance creation is async operation, usually takes 5-15 minutes.

```bash
# View instance status
aliyun milvus get "/webapi/instance/get?RegionId=cn-hangzhou&instanceId=c-xxx" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou --force
```

**Status Transition**: `creating` → `running`

Wait until `status` becomes `running` to indicate instance ready.

## Step 3: Get Connection Info

After instance ready, view connection address and component details:

```bash
aliyun milvus post "/webapi/cluster/detail" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force
```

Focus on key fields in return:
- `Data.ClusterInfo.IntranetUrl`: Intranet connection address
- `Data.ClusterInfo.InternetUrl`: Public network connection address (if enabled)
- `Data.ClusterInfo.ProxyPort`: Milvus service port (default 19530)
- `Data.ClusterInfo.AttuPort`: Attu visual management port

Connection example (pymilvus):
```python
from pymilvus import connections

PYMILVUS_GRPC_OPTIONS = {
    "grpc.primary_user_agent": "AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage"
}

connections.connect(
    host="c-xxx.milvus.aliyuncs.com",
    port=19530,
    user="root",
    password="YourPassword@123",
    grpc_options=PYMILVUS_GRPC_OPTIONS,
)
```

## Step 4: View Instance List

```bash
# View all instances under current region
aliyun milvus get "/webapi/instance/list?RegionId=cn-hangzhou&pageSize=50" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-milvus-manage \
  --RegionId cn-hangzhou --force
```

## Cleanup: Release Test Instance

> 🚫 **Instance deletion is NOT available through this Skill.** To release/delete a test instance, please go to the [Alibaba Cloud Milvus Console](https://milvus.console.aliyun.com/#/overview). Release promptly after use to avoid ongoing billing.

## Common Creation Failure Reasons

| Symptom | Possible Reason | Troubleshooting Method |
|---------|-----------------|------------------------|
| Creation failed | VPC/VSwitch doesn't exist or not in same availability zone | Check if VPC and VSwitch exist and in specified availability zone |
| Creation failed | VSwitch available IP insufficient | Switch to a VSwitch with sufficient available IPs |
| Creation failed | Account balance insufficient | Recharge and retry |
| Creation failed | RAM permission insufficient | Confirm AccessKey has `milvus:CreateInstance` permission |
| Long time Creating | Backend resource scheduling | Wait 15-30 minutes, if timeout contact support |

## Next Steps

- Need production-grade instance? → Refer to [Instance Full Lifecycle](instance-lifecycle.md) production config template
- Detailed creation parameters? → Refer to [Create Parameter Reference](create-params.md)
- Daily operations? → Refer to [Operations Manual](operations.md)
- API parameter query? → Refer to [API Parameter Reference](api-reference.md)
