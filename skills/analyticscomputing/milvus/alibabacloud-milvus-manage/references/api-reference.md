# API Parameter Reference

All APIs version `2023-10-12`, Endpoint is `milvus.<RegionId>.aliyuncs.com`.

**Calling Method**: Use `aliyun` CLI REST style, **must add `--force`** (bypass local path validation).

> **Prerequisite**: Before executing any aliyun command, ensure User-Agent environment variable is set:
> ```bash
> export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills"
> ```

⚠️ **Critical Limitation**: Milvus API has two parameter passing methods, must choose according to API type:
- **GET / DELETE**: All business parameters concatenated to URL query string (e.g., `"/path?RegionId=xx&instanceId=c-xxx"`)
- **POST / PUT (body type)**: Pass JSON with `--body '{...}'` (CreateInstance, UpdateInstance)
- **POST (query type)**: Business parameters passed with `--Flag value` (other POST APIs)
- All requests keep `--RegionId <region>` for endpoint routing

## Table of Contents

- [Instance Management](#instance-management): ListInstancesV2, GetInstance, GetInstanceDetail, CreateInstance, DeleteInstance, UpdateInstance, UpdateInstanceName
- [Configuration Management](#configuration-management): DescribeInstanceConfigs, ModifyInstanceConfig
- [Network and Security](#network-and-security): UpdatePublicNetworkStatus, DescribeAccessControlList, UpdateAccessControlList
- [Resource Group](#resource-group): ChangeResourceGroup
- [Others](#others): CreateDefaultRole
- [Network Resource Query](#network-resource-query): DescribeVpcs, DescribeVSwitches, DescribeSecurityGroups

---

## Instance Management

### ListInstancesV2 — Query Instance List

**Path**: `GET /webapi/instance/list`

**Request Parameters** (CLI flag):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | String | Yes | Region ID |
| instanceName | String | No | Filter by instance name |
| instanceId | String | No | Filter by instance ID |
| pageNumber | Integer | No | Page number, default 1 |
| pageSize | Integer | No | Page size, default 10, max 100 |

**Key Return Fields**: `instances[]` (instanceId, instanceName, regionId, zoneId, status, dbVersion, ha, paymentType, createTime, vpcId)

⚠️ **Note**: Returned `total` field may be inaccurate (returns 0 but actually has data), should directly check `instances` array.

```bash
aliyun milvus GET "/webapi/instance/list?RegionId=cn-hangzhou&pageNumber=1&pageSize=50" \
  --RegionId cn-hangzhou --force
```

---

### GetInstance — Query Instance Basic Info

**Path**: `GET /webapi/instance/get`

**Request Parameters** (CLI flag):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | String | Yes | Region ID |
| instanceId | String | Yes | Instance ID |

**Key Return Fields**: `instance` (instanceId, instanceName, regionId, zoneId, status, dbVersion, ha, paymentType, createTime, vpcId)

```bash
aliyun milvus GET "/webapi/instance/get?RegionId=cn-hangzhou&instanceId=c-xxx" \
  --RegionId cn-hangzhou --force
```

---

### GetInstanceDetail — Query Instance Details

Get component specs, connection addresses (intranet/public), storage usage, HA config and other detailed info.

**Path**: `POST /webapi/cluster/detail`

**Request Parameters** (query type, pass with `--Flag`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |

**Key Return Fields**:
- `Data.InstanceId` / `ClusterName` / `RegionId` / `ZoneId` / `InstanceStatus`
- `Data.Version` / `EnableHa` / `PayType` (0=PayAsYouGo, 1=Subscription)
- `Data.ClusterInfo.IntranetUrl` / `InternetUrl` / `ProxyPort` / `AttuPort`
- `Data.ClusterInfo.TotalCuNum` / `TotalDiskSize` / `OssStorageSize`
- `Data.ClusterInfo.MilvusResourceInfoList[]` (ComponentType, Replica, CuNum, DiskSize)

```bash
aliyun milvus POST "/webapi/cluster/detail" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force
```

---

### CreateInstance — Create Instance

**Path**: `POST /webapi/instance/create`

**Request Parameters** (`RegionId` is CLI flag, others are body camelCase):

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| RegionId | CLI flag | String | Yes | Region ID |
| clientToken | CLI flag | String | No | Idempotent token, max 64 ASCII characters |
| regionId | body | String | Yes | Region ID, must match RegionId in CLI flag |
| zoneId | body | String | Yes | Primary availability zone |
| instanceName | body | String | Yes | Instance name |
| dbVersion | body | String | Yes | Kernel version: `2.3` / `2.4` / `2.5` / `2.6` |
| vpcId | body | String | Yes | VPC ID |
| vSwitchIds | body | Array | Yes | VSwitch list, see structure description |
| paymentType | body | String | Yes | `PayAsYouGo` / `Subscription` |
| ha | body | Boolean | Yes | false=standalone, true=cluster |
| components | body | Array | Yes | Component config list, see structure description |
| dbAdminPassword | body | String | Yes | Admin password |
| autoBackup | body | Boolean | No | Auto backup, default false |
| loadReplicas | body | Integer | No | Load replica count, default 1 |
| encrypted | body | Boolean | No | Data encryption, default false |
| isMultiAzStorage | body | Boolean | No | Multi-AZ storage, default true |
| multiZoneMode | body | String | No | `single` (default) / `Active-Active` |
| autoRenew | body | Boolean | No | Auto renew (Subscription only) |

**vSwitchIds Structure**: `[{"vswId":"vsw-xxx","zoneId":"cn-hangzhou-j"}]`

**components Structure**: `[{"type":"...","replica":N,"cuNum":N,"cuType":"general","diskSizeType":"Normal"}]`
- type options: `standalone_pro` (standalone) / `proxy` / `mix_coordinator` / `data` / `query` / `streaming` (cluster)
- ⚠️ streaming/data/mix_coordinator/query minimum 4 CU, proxy minimum 2 CU

**Key Return Fields**: `data.instanceId`, `data.orderId`, `requestId`

```bash
# Standalone (Development & Testing)
aliyun milvus POST "/webapi/instance/create?RegionId=cn-hangzhou" \
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
    "dbAdminPassword": "YourPass@123",
    "autoBackup": true
  }' \
  --force

# Cluster (Production, 36 CU)
aliyun milvus POST "/webapi/instance/create?RegionId=cn-hangzhou" \
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
    "dbAdminPassword": "YourPass@123",
    "autoBackup": true
  }' \
  --force
```

---

### DeleteInstance — Release Instance

⚠️ **Destructive Operation**: Irreversible, all data will be permanently deleted.

**Path**: `DELETE /webapi/instance/delete`

**Request Parameters** (CLI flag):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | String | Yes | Region ID |
| instanceId | String | Yes | Instance ID |

**Key Return Fields**: `instanceId`, `orderId`

```bash
aliyun milvus DELETE "/webapi/instance/delete?RegionId=cn-hangzhou&instanceId=c-xxx" \
  --RegionId cn-hangzhou --force
```

---

### UpdateInstance — Update Instance (Scaling)

**Path**: `PUT /webapi/instance/update`

**Request body** (camelCase):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| instanceId | String | Yes | Instance ID |
| instanceName | String | No | New instance name |
| ha | Boolean | No | Enable high availability |
| components | Array | No | Updated component config list |

```bash
aliyun milvus PUT "/webapi/instance/update?RegionId=cn-hangzhou" \
  --RegionId cn-hangzhou \
  --body '{
    "instanceId": "c-xxx",
    "components": [
      {"type":"query","replica":3,"cuNum":8,"cuType":"cap","diskSizeType":"Normal"}
    ]
  }' \
  --force
```

---

### UpdateInstanceName — Modify Instance Name

**Path**: `POST /webapi/cluster/update_name`

**Request Parameters** (query type, pass with `--Flag`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |
| ClusterName | String | Yes | New instance name |

```bash
aliyun milvus POST "/webapi/cluster/update_name" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --ClusterName new-name \
  --force
```

---

## Configuration Management

### DescribeInstanceConfigs — Get Instance Custom Config

**Path**: `POST /webapi/config/describe_milvus_user_config`

**Request Parameters** (query type, pass with `--Flag`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |

**Return Fields**: `Data` (YAML format config string), `Success`

```bash
aliyun milvus POST "/webapi/config/describe_milvus_user_config" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force
```

---

### ModifyInstanceConfig — Update Instance Config

**Path**: `POST /webapi/config/modify_milvus_config`

**Request Parameters** (query type, pass with `--Flag`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |
| Reason | String | Yes | Update reason |
| UserConfig | String | No | YAML format user custom config |

```bash
aliyun milvus POST "/webapi/config/modify_milvus_config" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --Reason "Adjust proxy max task count" \
  --UserConfig "proxy:
  maxTaskNum: 1024
" \
  --force
```

---

## Network and Security

### UpdatePublicNetworkStatus — Enable/Disable Public Network Access

**Path**: `POST /webapi/network/updatePublicNetworkStatus`

**Request Parameters** (query type, pass with `--Flag`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |
| ComponentType | String | Yes | Component type, enter `Proxy` |
| PublicNetworkEnabled | Boolean | Yes | true=enable, false=disable |
| Cidr | String | No | Allowed access CIDR (recommended to fill when enabling) |

```bash
# Enable public network access and set whitelist
aliyun milvus POST "/webapi/network/updatePublicNetworkStatus" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --ComponentType Proxy \
  --PublicNetworkEnabled true \
  --Cidr "10.0.0.0/8" \
  --force
```

---

### DescribeAccessControlList — Query Public Network Whitelist

**Path**: `POST /webapi/milvus/describe_access_control_list`

**Request Parameters** (query type, pass with `--Flag`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |

**Return Fields**: `Data` (AclId, Cidr[])

```bash
aliyun milvus POST "/webapi/milvus/describe_access_control_list" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --force
```

---

### UpdateAccessControlList — Update Public Network Whitelist

**Path**: `POST /webapi/milvus/update_access_control_list`

**Request Parameters** (query type, pass with `--Flag`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |
| AclId | String | Yes | Public network access control ID (obtain via DescribeAccessControlList) |
| Cidr | String | No | CIDR block |

```bash
aliyun milvus POST "/webapi/milvus/update_access_control_list" \
  --RegionId cn-hangzhou \
  --InstanceId c-xxx \
  --Cidr "192.168.1.0/24" \
  --AclId acl-xxx \
  --force
```

---

## Resource Group

### ChangeResourceGroup — Transfer Resource Group

**Path**: `POST /webapi/resourceGroup/change`

**Request Parameters** (query type, pass with `--Flag`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| NewResourceGroupId | String | Yes | Target resource group ID |
| ResourceId | String | No | Resource ID |
| RegionId | String | No | Region ID |

```bash
aliyun milvus POST "/webapi/resourceGroup/change" \
  --RegionId cn-hangzhou \
  --NewResourceGroupId rg-xxx \
  --ResourceId c-xxx \
  --force
```

---

## Others

### CreateDefaultRole — Create Service Role

**Path**: `POST /webapi/user/create_default_role`

Creates service role needed for Milvus to access other cloud products (like OSS), no request parameters.

```bash
aliyun milvus POST "/webapi/user/create_default_role" \
  --RegionId cn-hangzhou --force
```

---

## Network Resource Query

### DescribeVpcs — Query VPC List

**Product**: `vpc`, **Version**: `2016-04-28`

```bash
aliyun vpc DescribeVpcs --RegionId cn-hangzhou
```

**Key Return Fields**: `Vpcs.Vpc[]` (VpcId, VpcName, CidrBlock, Status)

---

### DescribeVSwitches — Query VSwitch List

**Product**: `vpc`, **Version**: `2016-04-28`

```bash
aliyun vpc DescribeVSwitches --RegionId cn-hangzhou --VpcId vpc-xxx
```

**Key Return Fields**: `VSwitches.VSwitch[]` (VSwitchId, VSwitchName, ZoneId, CidrBlock, AvailableIpAddressCount)

---

### DescribeSecurityGroups — Query Security Group List

**Product**: `ecs`, **Version**: `2014-05-26`

```bash
aliyun ecs DescribeSecurityGroups --RegionId cn-hangzhou --VpcId vpc-xxx
```