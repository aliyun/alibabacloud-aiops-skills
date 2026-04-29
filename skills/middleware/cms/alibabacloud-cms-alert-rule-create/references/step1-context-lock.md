# Step 1: 上下文锁定

## 目的
收集告警类型所需的定位参数，作为后续查询生成的上下文。

---

## CMS 1.0 上下文

### 必需参数

| 参数 | 必填 | 描述 | 示例 |
|------|------|------|------|
| `namespace` | 是 | 云产品命名空间 | `acs_ecs_dashboard` |
| `regionId` | 否 | 地域（默认：当前地域） | `cn-hangzhou` |
| `resources` | 是 | 实例范围 | `[{"resource":"_ALL"}]` |

### 常用 Namespace 映射

| 产品 | Namespace | 实例查询 CLI |
|------|-----------|-------------|
| ECS | `acs_ecs_dashboard` | `aliyun ecs describe-instances --region-id <region>` |
| RDS MySQL | `acs_rds_dashboard` | `aliyun rds describe-db-instances --region-id <region>` |
| SLB | `acs_slb_dashboard` | `aliyun slb describe-load-balancers --region-id <region>` |
| Redis | `acs_kvstore` | `aliyun r-kvstore describe-instances --region-id <region>` |
| OSS | `acs_oss_dashboard` | 对所有 bucket 使用 `[{"resource":"_ALL"}]` |
| MongoDB | `acs_mongodb` | `aliyun dds describe-db-instances --region-id <region>` |
| PolarDB | `acs_polardb` | `aliyun polardb describe-db-clusters --region-id <region>` |
| Elasticsearch | `acs_elasticsearch` | `aliyun elasticsearch list-instance --region-id <region>` |
| NAT Gateway | `acs_nat_gateway` | `aliyun vpc describe-nat-gateways --region-id <region>` |
| EIP | `acs_vpc_eip` | `aliyun vpc describe-eip-addresses --region-id <region>` |
| HBase | `acs_hbase` | 不适用（从控制台获取 instanceId） |
| Hologres | `acs_hologres` | 不适用（从控制台获取 instanceId） |
| DRDS | `acs_drds` | 不适用（从控制台获取 instanceId） |
| OceanBase | `acs_oceanbase` | 不适用（从控制台获取 instanceId） |
| GPDB (AnalyticDB PG) | `acs_hybriddb` | 不适用（从控制台获取 instanceId） |
| RocketMQ | `acs_rocketmq` | 不适用（从控制台获取 instanceId） |
| SWAS（轻量服务器） | `acs_swas` | 不适用（从控制台获取 instanceId） |
| Serverless | `acs_serverless` | 不适用（从控制台获取 instanceId） |
| CEN（云企业网） | `acs_cen` | 不适用（从控制台获取 instanceId） |
| KMS | `acs_kms` | 不适用（从控制台获取 instanceId） |
| IoT | `acs_iot` | 不适用（从控制台获取 instanceId） |
| CloudBox | `acs_cloudbox` | 不适用（从控制台获取 instanceId） |
| Milvus | `acs_milvus` | 不适用（从控制台获取 instanceId） |
| EMR | `acs_emr` | 不适用（从控制台获取 instanceId） |
| Shared Bandwidth | `acs_bandwidth_package` | 不适用（从控制台获取 instanceId） |

### 动态 Namespace 发现

如果用户的产品不在上述常用映射中，可动态发现 namespace：

```bash
aliyun cms describe-project-meta --page-size 100
```

在返回列表中搜索匹配的 namespace。响应包含 `Namespace` 和 `Description` 字段。

> **提示**：使用 `--labels '[{"name":"product","value":"<ProductName>"}]'` 按产品名称过滤。

### Resources 格式（重要）

**标准格式：** `[{"resource":"<instance-id>"}]`

**示例：**
| 场景 | Resources 值 |
|------|-------------|
| 所有资源（任意产品） | `[{"resource":"_ALL"}]` |
| 单个 ECS 实例 | `[{"resource":"i-bp1234567890abcdef"}]` |
| 多个实例 | `[{"resource":"i-bp123456"},{"resource":"i-bp789012"}]` |

### 全部资源监控

当用户希望监控某产品的所有实例（而非指定实例）时，使用 `_ALL`：

```bash
--resources '[{"resource":"_ALL"}]'
```

此格式适用于**所有产品**（ECS、RDS、SLB、OSS、MongoDB、Redis 等）。控制台将显示"关联全部资源"。

仅在监控**特定实例**时才指定具体的资源 ID。

---

## 参数处理规则

### 类型

| 类型 | 示例 | 处理方式 |
|------|------|----------|
| **选择已有** | 实例、联系人组 | 查询已有资源，提供列表供选择 |
| **建议 + 确认** | 告警名称、描述 | 生成建议值，请用户确认或修改 |
| **用户必须输入** | 手机号、邮箱（创建时） | 仅在创建新资源时询问 |

### 告警名称（建议 + 确认）

```
模型: "根据您的需求，建议告警名称为：
  `ECS_CPU_Utilization_Alert`
  
  您可以确认此名称或提供您偏好的名称："

用户: "改成 prod-ecs-cpu-high"

模型: "好的，使用名称：`prod-ecs-cpu-high`"
```

---

## 下一步
→ `step2-query-generation.md`
