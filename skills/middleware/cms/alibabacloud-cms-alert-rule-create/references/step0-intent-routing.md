# Step 0: 意图路由

## 目的
识别用户的告警意图，并路由到正确的工作流（CMS 1.0 或 CMS 2.0，创建或查询）。

## 适用场景
当用户提到与告警相关的关键词时，需要判断：(1) 使用哪个版本，(2) 用户想要创建还是查询。

---

## 路由决策

| 条件 | 操作 |
|------|------|
| 云产品系统指标（ECS、RDS、SLB、OSS、Redis、MongoDB…）— **创建** | → CMS 1.0 创建流程（`step1-context-lock.md`） |
| 云产品系统指标 — **查询** | → CMS 1.0 查询流程（`step-query.md`） |
| Prometheus / PromQL / K8s / 容器 / 集群监控 — **创建** | → CMS 2.0 创建流程（`cms2-step1-context-lock.md`） |
| APM / 应用监控 / JVM / 响应时间 / 慢SQL — **创建** | → CMS 2.0 创建流程（`cms2-step1-context-lock.md`） |
| UModel / AI 监控 / Token 用量 — **创建** | → CMS 2.0 创建流程（`cms2-step1-context-lock.md`） |
| 自定义指标 / 非云产品监控 — **创建** | → CMS 2.0 创建流程（`cms2-step1-context-lock.md`） |
| Prometheus / APM / UModel 告警规则 — **查询** | → CMS 2.0 查询流程（`cms2-step-query.md`） |

---

## CMS 1.0 关键词（云产品系统指标）

| 用户关键词 | 告警类型 | Namespace |
|------------|----------|-----------|
| ECS, 云服务器, instance, server | ECS | `acs_ecs_dashboard` |
| RDS, MySQL, 数据库, database | RDS | `acs_rds_dashboard` |
| SLB, 负载均衡, load balancer | SLB | `acs_slb_dashboard` |
| Redis, 缓存, KVStore, cache | Redis | `acs_kvstore` |
| OSS, 对象存储, bucket, storage | OSS | `acs_oss_dashboard` |
| MongoDB, Mongo, 文档数据库 | MongoDB | `acs_mongodb` |
| PolarDB, 极致数据库 | PolarDB | `acs_polardb` |
| Elasticsearch, ES, 搜索 | Elasticsearch | `acs_elasticsearch` |
| NAT, NAT网关, nat gateway | NAT Gateway | `acs_nat_gateway` |
| EIP, 弹性公网IP, elastic IP | EIP | `acs_vpc_eip` |
| HBase | HBase | `acs_hbase` |
| Hologres, 实时数仓 | Hologres | `acs_hologres` |
| DRDS, 分布式数据库 | DRDS | `acs_drds` |
| OceanBase, OB | OceanBase | `acs_oceanbase` |
| AnalyticDB, GPDB, 分析型数据库 | GPDB | `acs_hybriddb` |
| RocketMQ, 消息队列 | RocketMQ | `acs_rocketmq` |
| SWAS, 轻量服务器 | SWAS | `acs_swas` |
| KMS, 密钥管理, key management | KMS | `acs_kms` |
| Milvus, 向量数据库 | Milvus | `acs_milvus` |

---

## CMS 2.0 关键词（高级监控）

| 用户关键词 | 告警子类型 |
|------------|-----------|
| Prometheus, PromQL, K8s, Kubernetes, 容器, Pod, Node, 集群, container, cluster | Prometheus |
| APM, 应用监控, JVM, 响应时间, 慢SQL, 异常率, 链路, application monitoring, response time | APM |
| UModel, 大模型, AI应用, Token, 统一模型, AI monitoring | UModel |
| 自定义指标, custom metrics, 或任何非云产品监控类型 | CMS 2.0（请用户确认子类型） |

---

## 核心规则

> **识别用户的监控目标并路由到正确的工作流。绝不混用 CMS 1.0 和 CMS 2.0 的 API。**

---

## 意图识别

### 创建告警意图

| 用户表达 | 操作 | 原因 |
|----------|------|------|
| "监控我的 ECS CPU" | → CMS 1.0 创建流程 | 明确的云资源指标 |
| "RDS 连接数超过 90% 时告警" | → CMS 1.0 创建流程 | 明确的云资源指标 |
| "为K8s集群创建Prometheus告警" | → CMS 2.0 创建流程 | Prometheus 监控 |
| "给应用配置APM响应时间告警" | → CMS 2.0 创建流程 | APM 监控 |
| "创建UModel Token消耗告警" | → CMS 2.0 创建流程 | UModel 监控 |
| "创建一个告警"（模糊表达） | 追问："您要监控什么类型的资源？云产品资源(ECS/RDS/SLB等) → CMS 1.0 流程；Prometheus/APM/UModel → CMS 2.0 流程。" | 需要澄清 |

### 查询告警意图

| 用户表达 | 操作 |
|----------|------|
| "列出所有ECS告警规则" / "List all ECS alert rules" | → CMS 1.0 查询（`step-query.md`） |
| "查看告警规则" / "Show alert rules" | → CMS 1.0 查询（`step-query.md`） |
| "哪些规则处于告警状态" / "Which rules are in ALARM state" | → CMS 1.0 查询（`step-query.md`） |
| "查看Prometheus告警规则" | → CMS 2.0 查询（`cms2-step-query.md`） |
| "列出APM应用告警规则" | → CMS 2.0 查询（`cms2-step-query.md`） |
| "查看UModel/大模型告警规则" | → CMS 2.0 查询（`cms2-step-query.md`） |

**查询关键词**：查看、列出、查询、搜索、查找、检查、list、view、query、search、find、show、check

---

## 未知产品处理

如果用户提到的产品不在关键词映射表中：
1. 请用户确认产品名称
2. 调用 `aliyun cms describe-project-meta --page-size 100` 搜索匹配的 namespace
3. 如果找到，继续 CMS 1.0 工作流
4. 如果未找到，告知用户该产品可能不支持 CMS 指标告警

---

## 日志告警场景（不支持）

如果用户描述的是基于日志的告警场景（例如"日志中 500 错误超过 10 次时告警"），回复：

```
⚠️ 本技能支持以下告警类型：
- CMS 1.0：云产品指标（ECS CPU/内存/磁盘、RDS 连接数、SLB 流量等）
- CMS 2.0：Prometheus 指标、APM 应用监控、UModel AI 模型监控

日志类告警（如错误计数、关键词监控）不在本技能支持范围内。
```

---

## 下一步

| 意图 | 版本 | 参考文档 |
|------|------|----------|
| 创建云资源告警 | CMS 1.0 | → `step1-context-lock.md` |
| 查询云资源告警规则 | CMS 1.0 | → `step-query.md` |
| 创建 Prometheus/APM/UModel 告警 | CMS 2.0 | → `cms2-step1-context-lock.md` |
| 查询 Prometheus/APM/UModel 规则 | CMS 2.0 | → `cms2-step-query.md` |
