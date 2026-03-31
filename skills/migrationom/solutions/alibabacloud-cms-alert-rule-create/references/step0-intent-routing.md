# Step 0: Intent Routing

## Purpose
Identify user alert intent and confirm it is a CMS 1.0 cloud resource monitoring scenario.

## When to Use
When user says "create alert", "setup monitoring", "add alarm" or similar expressions.

## Core Rule

> **Identify user's monitoring target and confirm it matches CMS 1.0 cloud resource metrics.**

---

## Type Identification

| User Says | Action | Reason |
|-----------|--------|--------|
| "Monitor my ECS CPU" | ✅ Proceed | Clear cloud resource metric |
| "Alert when RDS connections exceed 90%" | ✅ Proceed | Clear cloud resource metric |
| "Setup monitoring for my OSS" | ✅ Proceed | Clear cloud resource metric |
| "Create an alert" | Ask for target | Need clarification on what to monitor |
| "Alert me if something goes wrong" | Ask for target | Non-specific description |

---

## Keyword Mapping

| Keywords | → Product | Namespace |
|----------|-----------|-----------|
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

## Unknown Product Handling

If the user mentions a product NOT in the keyword mapping:
1. Ask the user to confirm the product name
2. Call `aliyun cms describe-project-meta --page-size 100` to search for matching namespaces
3. If found, proceed with the matched namespace
4. If not found, inform the user that the product may not support CMS metric alerting

---

## Log Alert Scenario (Not Supported)

If user describes a log-based alert scenario (e.g., "alert when 500 errors in logs exceed 10", "monitor error keywords in logs"), respond:

```
⚠️ This skill only supports CMS 1.0 cloud resource monitoring alerts.

CMS 1.0 supports:
- Cloud product metrics: ECS CPU/memory/disk, RDS connections, SLB traffic, etc.
- Infrastructure metrics: Instance status, network latency, etc.

Log-based alerts (such as error count in logs, keyword monitoring) are not supported by this skill.
```

---

## Next Step
→ `step1-context-lock.md`
