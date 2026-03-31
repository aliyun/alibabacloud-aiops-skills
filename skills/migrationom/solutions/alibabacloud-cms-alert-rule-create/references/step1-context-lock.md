# Step 1: Context Lock

## Purpose
Collect location parameters required for the alert type as context for subsequent query generation.

---

## CMS 1.0 Context

### Required Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `namespace` | Yes | Cloud product namespace | `acs_ecs_dashboard` |
| `regionId` | No | Region (default: current) | `cn-hangzhou` |
| `resources` | Yes | Instance scope | `[{"resource":"_ALL"}]` |

### Common Namespace Mapping

| Product | Namespace | Instance Query CLI |
|---------|-----------|-------------------|
| ECS | `acs_ecs_dashboard` | `aliyun ecs DescribeInstances --RegionId <region>` |
| RDS MySQL | `acs_rds_dashboard` | `aliyun rds DescribeDBInstances --RegionId <region>` |
| SLB | `acs_slb_dashboard` | `aliyun slb DescribeLoadBalancers --RegionId <region>` |
| Redis | `acs_kvstore` | `aliyun r-kvstore DescribeInstances --RegionId <region>` |
| OSS | `acs_oss_dashboard` | Use `[{"resource":"_ALL"}]` for all buckets |
| MongoDB | `acs_mongodb` | `aliyun dds DescribeDBInstances --RegionId <region>` |
| PolarDB | `acs_polardb` | `aliyun polardb DescribeDBClusters --RegionId <region>` |
| Elasticsearch | `acs_elasticsearch` | `aliyun elasticsearch ListInstance --RegionId <region>` |
| NAT Gateway | `acs_nat_gateway` | `aliyun vpc DescribeNatGateways --RegionId <region>` |
| EIP | `acs_vpc_eip` | `aliyun vpc DescribeEipAddresses --RegionId <region>` |
| HBase | `acs_hbase` | N/A (use instanceId from console) |
| Hologres | `acs_hologres` | N/A (use instanceId from console) |
| DRDS | `acs_drds` | N/A (use instanceId from console) |
| OceanBase | `acs_oceanbase` | N/A (use instanceId from console) |
| GPDB (AnalyticDB PG) | `acs_hybriddb` | N/A (use instanceId from console) |
| RocketMQ | `acs_rocketmq` | N/A (use instanceId from console) |
| SWAS (轻量服务器) | `acs_swas` | N/A (use instanceId from console) |
| Serverless | `acs_serverless` | N/A (use instanceId from console) |
| CEN (云企业网) | `acs_cen` | N/A (use instanceId from console) |
| KMS | `acs_kms` | N/A (use instanceId from console) |
| IoT | `acs_iot` | N/A (use instanceId from console) |
| CloudBox | `acs_cloudbox` | N/A (use instanceId from console) |
| Milvus | `acs_milvus` | N/A (use instanceId from console) |
| EMR | `acs_emr` | N/A (use instanceId from console) |
| Shared Bandwidth | `acs_bandwidth_package` | N/A (use instanceId from console) |

### Dynamic Namespace Discovery

If the user's product is NOT in the common mapping above, discover the namespace dynamically:

```bash
aliyun cms describe-project-meta --page-size 100
```

Search the returned list for a matching namespace. The response includes `Namespace` and `Description` fields.

> **TIP**: Use `--labels '[{"name":"product","value":"<ProductName>"}]'` to filter by product name.

### Resources Format (IMPORTANT)

**Standard format:** `[{"resource":"<instance-id>"}]`

**Examples:**
| Scenario | Resources Value |
|----------|----------------|
| ALL resources (any product) | `[{"resource":"_ALL"}]` |
| Single ECS instance | `[{"resource":"i-bp1234567890abcdef"}]` |
| Multiple instances | `[{"resource":"i-bp123456"},{"resource":"i-bp789012"}]` |

### All Resources Monitoring

When user wants to monitor ALL instances of a product (not specific instances), use `_ALL`:

```bash
--resources '[{"resource":"_ALL"}]'
```

This format applies to **ALL products** (ECS, RDS, SLB, OSS, MongoDB, Redis, etc.). The console will display "关联全部资源" (Associated with All Resources).

Only specify individual resource IDs when monitoring **specific instances**.

---

## Parameter Handling Rules

### Types

| Type | Examples | Handling |
|------|----------|----------|
| **Select existing** | Instances, contact groups | Query existing resources, provide list for selection |
| **Suggest + Confirm** | Alert name, description | Generate suggested value, ask user to confirm or modify |
| **User must input** | Phone, email (when creating) | Only ask when creating new resources |

### Alert Name (Suggest + Confirm)

```
Model: "Based on your requirements, I suggest the alert name:
  `ECS_CPU_Utilization_Alert`
  
  You can confirm this name or provide your preferred name:"

User: "Change to prod-ecs-cpu-high"

Model: "OK, using name: `prod-ecs-cpu-high`"
```

---

## Next Step
→ `step2-query-generation.md`
