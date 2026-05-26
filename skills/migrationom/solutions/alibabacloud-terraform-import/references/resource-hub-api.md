# ResourceCenter 接口使用指南

四个接口构成完整的资源发现和关系构建链路，原生产品 API 作为降级兜底。

API 文档入口：`https://api.aliyun.com/api/ResourceCenter/2022-12-01/`

---

## 前置接口：IaCService ListResourceTypes

**在 Phase 3 初始化阶段调用一次，建立 `terraformResourceType ↔ ResourceCode` 映射表，缓存到 `.import/resource-type-mapping.json`，供全程使用。**

```bash
aliyun iacservice list-resource-types \
  --endpoint iacservice.aliyuncs.com \
  --status Available \
  --maxResults 200
```

若结果超过 200 条，使用 `nextToken` 分页获取全量数据。

**关键返回字段：**

```json
{
  "resourceTypes": [
    {
      "terraformResourceType": "alicloud_eip_address",
      "resourceType": "ALIYUN::EIP::Address",
      "product": "EIP",
      "supportTerraformer": true,
      "status": "Available"
    }
  ]
}
```

**映射规则：**

`resourceType` 字段将 `ALIYUN` 前缀替换为 `ACS`，即得到 ResourceCenter 接口所需的 ResourceCode：

```
ALIYUN::EIP::Address  →  ACS::EIP::Address
ALIYUN::VPC::VPC      →  ACS::VPC::VPC
ALIYUN::ECS::Instance →  ACS::ECS::Instance
```

**映射表结构（`.import/resource-type-mapping.json`）：**

```json
{
  "byTerraformType": {
    "alicloud_eip_address": {
      "resourceCode": "ACS::EIP::Address",
      "product": "EIP",
      "supportTerraformer": true
    },
    "alicloud_vpc": {
      "resourceCode": "ACS::VPC::VPC",
      "product": "VPC",
      "supportTerraformer": true
    }
  },
  "byResourceCode": {
    "ACS::EIP::Address": "alicloud_eip_address",
    "ACS::VPC::VPC": "alicloud_vpc"
  }
}
```

**使用方式：**
- Phase 4：已知 `terraformResourceType` → 查 `byTerraformType` → 得到 `resourceCode` → 调用 search-resources
- Phase 6：ResourceCenter 返回的 `ResourceType` → 查 `byResourceCode` → 得到 `terraformResourceType` → 生成正确的 HCL 资源类型

**降级条件：**
- 调用失败或权限不足 → 降级使用本文件末尾的静态映射表
- 映射表中找不到对应关系 → 跳过接口 A/B，直接使用原生产品 API

---

## 接口一：list-resource-types

查询 ResourceCenter 支持的资源类型，用于判断接口 A（search-resources）和接口 B（list-resource-relationships）各自的支持范围。

**在 Phase 4 开始前调用一次，结果缓存供全程使用。**

```bash
aliyun resourcecenter list-resource-types --endpoint resourcecenter.aliyuncs.com
```

**关键返回字段：**

```json
{
  "ResourceTypes": [
    {
      "ResourceType": "ACS::ECS::Instance",
      "SupportedFeatures": ["ListResources", "GetResourceRelationships"]
    }
  ]
}
```

- `SupportedFeatures` 包含 `ListResources` → 该资源类型支持接口 A（search-resources）
- `SupportedFeatures` 包含 `GetResourceRelationships` → 该资源类型支持接口 B（list-resource-relationships）

**降级条件：**
- 调用返回权限错误（`AccessDenied`）→ 全程降级，跳过接口 A 和接口 B
- 调用超时或返回空列表 → 同上

---

## 接口 A：search-resources

搜索当前账号下有权限访问的资源。**返回的是资源基础元数据，不包含资源的业务属性**（如 VPC 的 CidrBlock、ECS 的 InstanceType 等）。Phase 6 生成 HCL 时仍需调用原生产品 API 获取完整属性，search-resources 仅用于 Phase 4 资源发现阶段。

**基本用法：**
```bash
aliyun resourcecenter search-resources \
  --filter '[{"Key":"ResourceType","MatchType":"Equals","Values":["ACS::ECS::Instance"]}]' \
  --max-results 50
```

**支持的过滤条件：**

| 过滤参数 | 支持的匹配方式 |
|---------|-------------|
| `ResourceType` | Equals |
| `RegionId` | Equals |
| `ResourceId` | Equals、Prefix |
| `ResourceName` | Equals、Contains |
| `Tag` | Contains、NotContains、NotExists（JSON 格式：`{"key":"k","value":"v"}`）|
| `VpcId` | Equals |
| `VSwitchId` | Equals |
| `IpAddress` | Equals、Contains |
| `ResourceGroupId` | Equals、Exists、NotExists |

多个过滤条件之间是 AND 关系，同一条件内多个值是 OR 关系。

**按 Region + 资源类型过滤：**
```bash
aliyun resourcecenter search-resources \
  --filter '[{"Key":"ResourceType","MatchType":"Equals","Values":["ACS::ECS::Instance"]},{"Key":"RegionId","MatchType":"Equals","Values":["cn-hangzhou"]}]' \
  --max-results 50
```

**按资源 ID 查询（用于确认资源类型）：**
```bash
aliyun resourcecenter search-resources \
  --filter '[{"Key":"ResourceId","MatchType":"Equals","Values":["vpc-bp1xxx"]}]' \
  --max-results 1
```

**分页：**
```bash
aliyun resourcecenter search-resources \
  --filter '[...]' \
  --max-results 50 \
  --next-token <上一页返回的 NextToken>
```
返回结果中不存在 `NextToken` 时表示没有更多数据，MaxResults 最大值为 500。

**返回字段：**

```json
{
  "Resources": [
    {
      "AccountId": "151266687691****",
      "ResourceId": "vtb-bp1xxx",
      "ResourceType": "ACS::VPC::RouteTable",
      "ResourceName": "group1",
      "RegionId": "cn-hangzhou",
      "ZoneId": "cn-hangzhou-k",
      "ResourceGroupId": "rg-acfmzawhxxc****",
      "CreateTime": "2021-06-30T09:20:08Z",
      "ExpireTime": "2021-07-30T09:20:08Z",
      "IpAddresses": ["192.168.1.2"],
      "IpAddressAttributes": [
        {"IpAddress": "192.168.1.2", "NetworkType": "Public", "Version": "Ipv4"}
      ],
      "Tags": [{"Key": "test_key", "Value": "test_value"}],
      "Deleted": false
    }
  ],
  "NextToken": "eyJzZWFyY2hBZnRlcnMiOlsiMTAwMTU2Nzk4MTU1OSJd****"
}
```

注意：`ZoneId`、`CreateTime`、`IpAddresses` 等字段是否返回由各云服务决定，不保证所有资源类型都有。

**资源类型格式（`ACS::<Product>::<ResourceType>`）：**

| 云产品 | ResourceCenter 类型 |
|--------|-------------------|
| VPC | `ACS::VPC::VPC` |
| VSwitch | `ACS::VPC::VSwitch` |
| 路由表 | `ACS::VPC::RouteTable` |
| EIP | `ACS::VPC::EipAddress` |
完整列表通过 `iacservice list-resource-types` 动态获取，以下为静态兜底映射表：

| Terraform 资源类型 | ResourceCode |
|-------------------|-------------|
| `alicloud_vpc` | `ACS::VPC::VPC` |
| `alicloud_vswitch` | `ACS::VPC::VSwitch` |
| `alicloud_route_table` | `ACS::VPC::RouteTable` |
| `alicloud_eip_address` | `ACS::EIP::Address` |
| `alicloud_nat_gateway` | `ACS::VPC::NatGateway` |
| `alicloud_instance` | `ACS::ECS::Instance` |
| `alicloud_security_group` | `ACS::ECS::SecurityGroup` |
| `alicloud_db_instance` | `ACS::RDS::DBInstance` |
| `alicloud_kvstore_instance` | `ACS::KVStore::Instance` |
| `alicloud_mongodb_instance` | `ACS::DDS::DBInstance` |
| `alicloud_oss_bucket` | `ACS::OSS::Bucket` |
| `alicloud_slb_load_balancer` | `ACS::SLB::LoadBalancer` |
| `alicloud_cs_managed_kubernetes` | `ACS::CS::KubernetesCluster` |

**降级条件：**
- 资源类型不在 `list-resource-types` 返回的支持列表中
- 调用返回 `NoPermission` 或其他错误
- 以上情况降级到 `references/api-commands.md` 的原生产品 API

---

## 接口 B：list-resource-relationships

查询指定资源与其关联资源的关系，用于动态构建资源依赖图。**`RegionId`、`ResourceType`、`ResourceId` 三个参数均为必填。**

返回结果是一个扁平列表，每条记录表示"当前资源"与"某个相关资源"之间存在关联，**不区分方向**（不区分父子或横向关联），由调用方根据业务语义判断依赖方向。

**基本用法：**
```bash
aliyun resourcecenter list-resource-relationships \
  --region-id cn-hangzhou \
  --resource-type ACS::VPC::VPC \
  --resource-id vpc-bp1xxx
```

**按相关资源类型过滤（只查 VSwitch）：**
```bash
aliyun resourcecenter list-resource-relationships \
  --region-id cn-hangzhou \
  --resource-type ACS::VPC::VPC \
  --resource-id vpc-bp1xxx \
  --related-resource-filter '[{"Key":"RelatedResourceType","MatchType":"Equals","Value":["ACS::VPC::VSwitch"]}]'
```

**分页：**
```bash
aliyun resourcecenter list-resource-relationships \
  --region-id cn-hangzhou \
  --resource-type ACS::VPC::VPC \
  --resource-id vpc-bp1xxx \
  --max-results 50 \
  --next-token <上一页返回的 NextToken>
```
MaxResults 取值范围 1~500，默认 20。

**支持的 RelatedResourceFilter 过滤参数：**

| 参数 | 描述 | 支持的匹配方式 |
|------|------|-------------|
| `RelatedResourceRegionId` | 相关资源地域 ID | Equals |
| `RelatedResourceType` | 相关资源类型 | Equals |
| `RelatedResourceId` | 相关资源 ID | Equals |

**返回字段：**

```json
{
  "ResourceRelationships": [
    {
      "RegionId": "cn-hangzhou",
      "ResourceType": "ACS::ACK::Cluster",
      "ResourceId": "m-eb3hji****",
      "RelatedResourceRegionId": "cn-shanghai",
      "RelatedResourceType": "ACS::VPC::VPC",
      "RelatedResourceId": "vpc-uf6m5okksddm6c9lh7***"
    }
  ],
  "NextToken": "eyJzZWFyY2hBZnRlcnMiOlsiMTAwMTU2Nzk4MTU1OSJd****"
}
```

注意：相关资源可能在不同 Region（`RelatedResourceRegionId` 与请求的 `RegionId` 不同），跨 Region 关联时需注意。

**Phase 5 使用方式：**

1. 从 Phase 4 发现的资源中识别根资源（VPC、OSS Bucket、DNS 域名、RAM 用户等无父依赖的资源）
2. 对每个根资源调用接口 B，获取其所有关联资源
3. 对关联资源递归调用接口 B，直到没有新资源出现，构建完整关系图
4. 依赖方向由业务语义判断：VPC → VSwitch（VSwitch 依赖 VPC），VSwitch → ECS（ECS 依赖 VSwitch）等，参考 `references/dependency-rules.md`
5. 对关系图做拓扑排序，生成导入顺序

**Phase 6 使用方式：**

通过接口 B 查询到的关联资源，其依赖关系已确定。结合 Phase 3 提取的引用字段白名单，找到当前资源中对应的 `_id` 字段，直接替换为 terraform resource address，无需猜测。

**降级条件：**
- 资源类型不在 `list-resource-types` 返回的支持列表中
- 调用返回 `NoPermission` 或其他错误
- 以上情况降级到 `references/dependency-rules.md` 的静态规则
