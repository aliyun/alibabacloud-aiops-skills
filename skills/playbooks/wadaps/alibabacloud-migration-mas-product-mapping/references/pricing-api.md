# Alibaba Cloud Pricing API Index

The pricing service (`scripts/pricing_service.py`) encapsulates pricing capabilities for 33 Alibaba Cloud products. This document lists product_code, API path, required parameters, and pricing method by category.

---

## 1. Compute

| Product | product_code | API Path | Required Parameters | Pricing Method |
|------|--------------|---------|---------|---------|
| ECS Cloud Server | `ecs` | `GET /api/pricing/ecs` | instance_type, region_id, period, data_disk_size, data_disk_pl | ECS DescribePrice real-time |
| ECS Pay-As-You-Go | `ecs` | `GET /api/pricing/ecs/payg` | instance_type, region_id | ECS DescribePrice real-time |
| ACK Container Service | `ack` | `GET /api/pricing/ack` | edition (pro/standard/serverless), worker_count | Management fee reference |
| ECI Elastic Container Instance | `eci` | `GET /api/pricing/eci` | cpu, memory_gb, hours_per_month | Pay-as-you-go reference |
| Function Compute FC | `fc` | `GET /api/pricing/fc` | memory_mb, invocations_million, duration_seconds | Pay-as-you-go reference |
| SAE Serverless App Engine | `sae` | `GET /api/pricing/sae` | cpu, memory_gb, instances | Pay-as-you-go reference |

> **ECS Pricing Data Disk Parameters**: `data_disk_category` (default `cloud_essd`), `data_disk_size` (GB), `data_disk_pl` (PL0/PL1/PL2/PL3). System disk and data disk must be passed together, otherwise price will be lower than actual.

---

## 2. Storage

| Product | product_code | API Path | Required Parameters | Pricing Method |
|------|--------------|---------|---------|---------|
| OSS Object Storage | `oss` | `GET /api/pricing/oss` | storage_class, capacity_gb | BSS real-time + proportional estimation |
| Block Storage (Cloud Disk) | `disk` | `GET /api/pricing/disk` | disk_category, disk_size, performance_level | ECS DescribePrice real-time |
| NAS File Storage | `nas` | `GET /api/pricing/nas` | storage_type, capacity_gb | Official pricing |
| HBR Hybrid Backup Recovery | `hbr` | `GET /api/pricing/hbr` | storage_gb | Reference price (¥0.1/GB/month) |

---

## 3. Database

| Product | product_code | API Path | Required Parameters | Pricing Method |
|------|--------------|---------|---------|---------|
| RDS Database | `rds` | `GET /api/pricing/rds` | db_instance_class, engine, engine_version, storage | RDS DescribePrice real-time |
| PolarDB | `polardb` | Batch endpoint | db_node_class, engine | PolarDB DescribeClassList real-time |
| Redis Cache | `redis` | `GET /api/pricing/redis` | instance_class, capacity | Redis DescribePrice real-time |
| MongoDB | `mongodb` | Batch endpoint | db_instance_class, disk_size | BSS GetSubscriptionPrice real-time |
| Elasticsearch | `elasticsearch` | Batch endpoint | instance_spec, disk_size | BSS GetSubscriptionPrice real-time |
| AnalyticDB PG (GPDB) | `gpdb` | Batch endpoint | instance_spec, storage_size | BSS GetSubscriptionPrice real-time |
| Lindorm Multi-Model DB | `lindorm` | `GET /api/pricing/lindorm` | spec, node_count, storage_gb | Reference price |
| Graph Database GDB | `gdb` | `GET /api/pricing/gdb` | spec, storage_gb | Reference price |
| Tablestore | `tablestore` | `GET /api/pricing/tablestore` | storage_gb, read_cu, write_cu | Pay-as-you-go reference |

> **PolarDB Pricing**: BSS `GetSubscriptionPrice` does not support PolarDB. Must use PolarDB `DescribeClassList` (CommodityCode=polardb_sub) to get `ReferencePrice` (unit: cents, single-node monthly price). Cluster price = ReferencePrice/100 × node count.

---

## 4. Network & CDN

| Product | product_code | API Path | Required Parameters | Pricing Method |
|------|--------------|---------|---------|---------|
| SLB Load Balancer (CLB) | `slb` | `GET /api/pricing/slb` | spec | BSS GetSubscriptionPrice real-time |
| NAT Gateway | `nat` | Batch endpoint | spec (Small/Medium/Large) | BSS GetSubscriptionPrice real-time |
| EIP Elastic IP | `eip` | Batch endpoint | bandwidth (default 5 Mbps) | BSS GetSubscriptionPrice real-time |
| VPN Gateway | `vpn` | `GET /api/pricing/vpn` | spec (5M/10M/20M/50M/100M) | Reference price |
| CDN Content Delivery | `cdn` | `GET /api/pricing/cdn` | bandwidth_mbps | Reference price (tiered pricing) |
| NLB Network Load Balancer | - | API pricing not supported | - | Pay-as-you-go ¥0.147/h ≈ ¥107.31/month |
| ALB Application Load Balancer | - | API pricing not supported | - | Pay-as-you-go ¥0.147/h ≈ ¥107.31/month |

---

## 5. Messaging & Middleware

| Product | product_code | API Path | Required Parameters | Pricing Method |
|------|--------------|---------|---------|---------|
| Message Queue Kafka | `kafka` | `GET /api/pricing/kafka` | spec_type, io_max, disk_size, topic_quota | BSS GetSubscriptionPrice real-time |
| Message Queue RocketMQ | `rocketmq` | `GET /api/pricing/rocketmq` | spec (2000tps / 5000tps / 10000tps / 20000tps) | Reference price |
| Message Queue RabbitMQ | `rabbitmq` | `GET /api/pricing/rabbitmq` | spec (professional-1000 / 5000) | Reference price |

---

## 6. Big Data & Analytics

| Product | product_code | API Path | Required Parameters | Pricing Method |
|------|--------------|---------|---------|---------|
| E-MapReduce EMR | `emr` | `GET /api/pricing/emr` | spec, node_count | Management fee reference |
| Realtime Compute Flink | `flink` | `GET /api/pricing/flink` | cu_count | Reference price (per CU) |
| Log Service SLS | `sls` | `GET /api/pricing/sls` | ingest_gb_day, retention_days | Pay-as-you-go reference |
| MaxCompute | `maxcompute` | `GET /api/pricing/maxcompute` | cu_count, storage_tb | Reference price |

---

## 7. Security

| Product | product_code | API Path | Required Parameters | Pricing Method |
|------|--------------|---------|---------|---------|
| WAF Web Application Firewall | `waf` | `GET /api/pricing/waf` | edition (pro_asia / business_asia / ultimate_asia) | BSS GetSubscriptionPrice real-time |
| DDoS Protection | `ddos` | `GET /api/pricing/ddos` | edition (bgp/coo), base_bandwidth, ip_count | BSS GetSubscriptionPrice real-time |
| Bastion Host | `bastionhost` | `GET /api/pricing/bastionhost` | edition (basic/standard/advanced) | Reference price |

---

## 8. Batch Pricing (Recommended)

Package multiple products into the `items` array for one-time pricing, significantly reducing API call overhead and latency.

```http
POST /api/pricing/batch
Content-Type: application/json

{
  "region_id": "ap-southeast-1",     // Must be confirmed by user, do not default to cn-beijing
  "period": 1,
  "items": [
    { "product_code": "ecs",      "instance_spec": "ecs.g8y.xlarge", "count": 3, "disk_size": 40, "data_disk_size": 100, "data_disk_pl": "PL1" },
    { "product_code": "rds",      "instance_spec": "rds.mysql.s3.large", "engine": "MySQL", "engine_version": "8.0", "disk_size": 200 },
    { "product_code": "redis",    "instance_spec": "redis.amber.master.2xlarge.multithread", "capacity": 16384 },
    { "product_code": "polardb",  "instance_spec": "polar.mysql.g2.xlarge", "engine": "MySQL" },
    { "product_code": "mongodb",  "instance_spec": "mdb.shard.2x.xlarge.d", "disk_size": 40 },
    { "product_code": "nat",      "instance_spec": "Small" },
    { "product_code": "eip",      "bandwidth": 5 },
    { "product_code": "kafka",    "spec_type": "professional", "io_max": 20, "disk_size": 500 },
    { "product_code": "waf",      "edition": "pro_asia" },
    { "product_code": "ddos",     "edition": "bgp", "base_bandwidth": 20, "ip_count": 100 },
    { "product_code": "vpn",      "spec": "10M" },
    { "product_code": "cdn",      "bandwidth_mbps": 100 },
    { "product_code": "emr",      "spec": "emr.c6.2xlarge", "node_count": 3 },
    { "product_code": "sls",      "ingest_gb_day": 10, "retention_days": 30 },
    { "product_code": "ack",      "edition": "pro" },
    { "product_code": "bastionhost", "edition": "standard" }
  ]
}
```

---

## 9. Pricing Coverage Statistics

| Vendor | Total Mapped Products | Pricing Supported | Free/No Pricing Needed | Pricing Coverage | Effective Coverage (incl. free) |
|------|--------------|------------|---------------|------------|----------------------|
| AWS | 78 | 41 | 13 | 52.6% | 69.2% |
| Azure | 78 | 37 | 14 | 47.4% | 65.4% |
| Tencent Cloud | 85 | 39 | 14 | 45.9% | 62.4% |
| Huawei Cloud | 83 | 38 | 13 | 45.8% | 61.4% |

- **BSS / API Real-Time Pricing (16 products)**: ECS, RDS, Redis, SLB, PolarDB, MongoDB, NAT, EIP, Elasticsearch, GPDB, OSS, Disk, Kafka, WAF, DDoS
- **Official Reference Pricing (17 products)**: NAS, HBR, RocketMQ, RabbitMQ, VPN, CDN, EMR, Flink, SLS, MaxCompute, ACK, ECI, FC, SAE, Lindorm, GDB, Tablestore, BastionHost
- **API Pricing Not Supported (manual estimation)**: NLB, ALB (pay-as-you-go only, BSS does not support)

---

## 10. Response Handling and Error Processing

All pricing service responses are unified JSON. Callers should identify and handle according to the table below.

| HTTP Status | Business Field | Meaning | Recommended Action |
|-----------|---------|------|---------|
| 200 | `{"price": ..., "currency": "CNY", ...}` | Pricing success | Write to report |
| 200 | `{"price": null, "warning": "..."}` | Spec exists but no quote (e.g., new spec, region unavailable) | Annotate "Reference price missing, please verify manually", fall back to mapping table reference price |
| 400 | `{"error": "invalid_param", "detail": "..."}` | Parameter error (e.g., PL1 with <20GB data disk) | Validate input then retry, auto-downgrade (PL1 → PL0) |
| 404 | `{"error": "spec_not_found"}` | Spec does not exist or deprecated | Fall back by CPU:memory ratio (1:2→ecs.c7, 1:4→ecs.g7, 1:8→ecs.r7) |
| 429 | `{"error": "rate_limited"}` | API rate limiting (BSS / ECS DescribePrice both have QPS limits) | Exponential backoff retry (recommended 1s / 2s / 4s, max 3 retries) |
| 5xx / timeout | `{"error": "upstream_timeout"}` | Upstream timeout or service exception | Retry once per item; if still fails, skip and annotate "Pricing failed" |

**Three things callers MUST do:**

1. **Timeout**: Set HTTP client timeout to 30 seconds (PolarDB DescribeClassList can be slow in large regions).
2. **Retry**: Use exponential backoff for 429 / 5xx / timeout, max 3 retries.
3. **Fallback**: All failed pricing items must be annotated "Pricing failed / Reference price missing, please verify manually" in report; **silent discard is prohibited**.
