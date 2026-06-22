# Common Spec Mapping (Database / Cache / NoSQL / FC / Disk / Others)

Applicable to cross-vendor common mapping rules. Vendor-specific spec codes are split into `aws-spec.md`, `tencent-spec.md`, `huawei-spec.md`, `azure-spec.md`.

---

## 1. RDS Common Spec Mapping (Normalized by vCPU/Memory)

Source RDS (AWS RDS / Tencent CDB / Huawei RDS / Azure DB for MySQL/PG) normalized by vCPU and memory to map to Alibaba Cloud RDS / PolarDB.

| Source Spec (vCPU / Memory GB) | Alibaba Cloud RDS MySQL Spec | Alibaba Cloud RDS PG Spec | Alibaba Cloud PolarDB MySQL Spec |
|---------------------------|--------------------------|------------------------|-------------------------------|
| 1 / 1 | rds.mysql.t1.small | pg.n1.micro.1 | polar.mysql.g2.medium |
| 1 / 2 | rds.mysql.s1.small | pg.n2.small.1 | polar.mysql.g2.medium |
| 2 / 4 | rds.mysql.s2.large | pg.n2.small.2c | polar.mysql.g2.large |
| 2 / 8 | rds.mysql.s2.xlarge | pg.n2.medium.2c | polar.mysql.g2.xlarge |
| 4 / 8 | rds.mysql.s3.small | pg.n4.medium.1 | polar.mysql.g4.large |
| 4 / 16 | rds.mysql.s3.large | pg.n2.medium.2c | polar.mysql.g4.xlarge |
| 8 / 16 | rds.mysql.c1.medium | pg.n4.large.1 | polar.mysql.g8.xlarge |
| 8 / 32 | rds.mysql.m1.medium | pg.n2.large.2c | polar.mysql.g8.xlarge |
| 8 / 64 | rds.mysql.r1.medium | pg.n2.large.2c | polar.mysql.g8.2xlarge |
| 16 / 32 | rds.mysql.c1.xlarge | pg.n4.xlarge.1 | polar.mysql.g8.2xlarge |
| 16 / 64 | rds.mysql.m1.xlarge | pg.n2.xlarge.2c | polar.mysql.g8.2xlarge |
| 16 / 128 | rds.mysql.r1.xlarge | pg.n8.xlarge.2c | polar.mysql.g8.4xlarge |
| 32 / 128 | rds.mysql.m1.2xlarge | pg.n4.2xlarge.1 | polar.mysql.g8.4xlarge |
| 32 / 256 | rds.mysql.r1.2xlarge | pg.n8.2xlarge.2c | polar.mysql.g8.8xlarge |
| 64 / 256 | rds.mysql.m1.4xlarge | pg.n4.4xlarge.1 | polar.mysql.g8.8xlarge |
| 64 / 512 | rds.mysql.r1.4xlarge | pg.n8.4xlarge.2c | polar.mysql.g8.16xlarge |

**RDS Spec Naming Convention**: `rds.mysql.{CPU:memory_ratio}.{size}`, where `s`=1:2, `m`=1:4, `c`=1:2(compute), `r`=1:8(memory).

**MariaDB / SQL Server**: Replace `rds.mysql` with `rds.mariadb` / `rds.mssql`.

**PolarDB Spec Naming Convention**: `polar.{engine}.g{multiplier}.{size}`, e.g., `g2`=2vCPU base, `g4`=4vCPU base, `g8`=8vCPU base.

> **Key Reminder**: Aurora / TDSQL-C / GaussDB users should preferably map to PolarDB (consistent disaggregated storage-compute architecture). Aurora engine identified by port (3306=MySQL, 5432=PostgreSQL).

> **PolarDB Pricing**: BSS `GetSubscriptionPrice` does not support PolarDB. Must use PolarDB `DescribeClassList` (CommodityCode=polardb_sub) to get `ReferencePrice` (unit: cents, single-node monthly price). Minimum cluster = 1 primary + 1 read-only = 2 nodes; actual monthly cost = single-node price × node count.

### RDS Batch Pricing Example

```json
{
  "region_id": "cn-beijing",
  "period": 1,
  "items": [
    { "product_code": "rds", "instance_spec": "rds.mysql.s3.large", "engine": "MySQL", "engine_version": "8.0", "disk_size": 200 },
    { "product_code": "rds", "instance_spec": "rds.mysql.m1.medium", "engine": "MySQL", "engine_version": "8.0", "disk_size": 500 },
    { "product_code": "rds", "instance_spec": "pg.n2.medium.2c", "engine": "PostgreSQL", "engine_version": "15.0", "disk_size": 100 }
  ]
}
```

---

## 2. Redis Cloud-Native Spec Mapping (Unified Rules)

Source Redis (AWS ElastiCache / Tencent Redis / Huawei DCS / Azure Cache for Redis) normalized by memory capacity to Alibaba Cloud Redis Cloud-Native edition.

| Memory (GB) | Alibaba Cloud Redis Spec | capacity (MB) |
|-----------|----------------------|----------------|
| 0.25 / 1 | redis.amber.master.small.multithread | 256 / 1024 |
| 2 | redis.amber.master.mid.multithread | 2048 |
| 4 | redis.amber.master.stand.multithread | 4096 |
| 8 | redis.amber.master.large.multithread | 8192 |
| 16 | redis.amber.master.2xlarge.multithread | 16384 |
| 32 | redis.amber.master.4xlarge.multithread | 32768 |
| 64 | redis.amber.master.8xlarge.multithread | 65536 |
| 128 (cluster) | redis.shard.amber.ce13.5.default | - |

**Cloud-Native Spec Naming**: `redis.amber.master.{size}.multithread` (standard dual-replica), `redis.amber.logic.sharding.{mem}g.{n}db.*` (cluster).

> **Cluster Pricing**: capacity should pass **total memory** (e.g., 4 shards × 8GB = 32GB total).
> **Pricing API**: r-kvstore `DescribePrice` (real-time).

---

## 3. MongoDB Spec Mapping (Unified Rules)

Source MongoDB / DocumentDB / Cosmos DB (MongoDB API) / DDS uniformly mapped to Alibaba Cloud MongoDB (dedicated, new cloud disk version).

| Source Spec (vCPU / Memory GB) | Alibaba Cloud MongoDB Spec | Notes |
|---------------------------|--------------------------|------|
| 2 / 4 | mdb.shard.2x.large.d | Dedicated 2C4G (suitable for dev/test) |
| 4 / 8 | mdb.shard.2x.xlarge.d | Dedicated 4C8G (suitable for prod default) |
| 8 / 16 | mdb.shard.2x.2xlarge.d | Dedicated 8C16G (medium workload) |
| 16 / 32 | mdb.shard.2x.4xlarge.d | Dedicated 16C32G (heavy workload) |
| 32 / 64 | mdb.shard.2x.8xlarge.d | Dedicated 32C64G (sharded cluster base) |

**Spec Naming**: `mdb.shard.{memory_multiplier}x.{size}.d` (dedicated) / `.c` (general). Default to dedicated (`.d`) consistent with console.

> **Environment Inference**: When source does not provide exact specs, infer by cluster name prefix — `prod-*` → `mdb.shard.2x.xlarge.d` (4C8G), `dev/test-*` → `mdb.shard.2x.large.d` (2C4G).
> **Pricing API**: BSS `GetSubscriptionPrice` (ProductCode=dds), default storage 40GB.
> **Cosmos DB RU/s Conversion**: Every 1000 RU/s ≈ 2vCPU equivalent compute power (400-1000→2C4G, 1000-4000→4C8G, 4000-10000→8C16G, >10000→16C32G+).

---

## 4. Additional Database Product Pricing Guide

The following products have no direct subscription pricing API on Alibaba Cloud; reference price estimation is used:

| Source Product | Alibaba Cloud Product | Pricing Method | Estimation Logic |
|---------|------------|---------|---------|
| TDSQL MySQL (distributed) | PolarDB-X | Official reference | ~¥200/vCPU/month (including compute+storage nodes) |
| TDSQL-H (HTAP) | PolarDB MySQL (HTAP) | Same as PolarDB | Use PolarDB MySQL spec for pricing |
| TencentDB ClickHouse | ClickHouse Cloud DB | Official reference | ~¥150/vCPU/month + storage ¥0.35/GB/month |
| CTSDB Time-Series DB | TSDB / Lindorm | Official reference | Lindorm time-series engine: ~¥100/vCPU/month + storage ¥0.15/GB/month |
| Graph DB KonisGraph | Graph Database GDB | Official reference | 2C16G ≈ ¥2,000/month, 4C32G ≈ ¥4,000/month |
| TcaplusDB | Tablestore | Pay-as-you-go | CU read/write + storage capacity |
| Elasticsearch Service | Elasticsearch | BSS pricing | `ProductCode=elasticsearch`, by node spec + storage |
| CDWPG Cloud Data Warehouse | AnalyticDB PostgreSQL | BSS pricing | `ProductCode=gpdb`, by compute nodes + storage |

> The above reference prices are based on cn-beijing public pricing, excluding business discounts. Reports should annotate "Reference price, subject to official website."

---

## 5. Lambda / Function Compute Mapping

| Source Memory Config | Alibaba Cloud FC Spec | vCPU |
|------------|----------------|------|
| 128 MB | FC 128MB | 0.05 |
| 256 MB | FC 256MB | 0.1 |
| 512 MB | FC 512MB | 0.25 |
| 1024 MB | FC 1GB | 0.5 |
| 2048 MB | FC 2GB | 1.0 |
| 3008 MB | FC 3GB | 2.0 |

> Applicable to AWS Lambda, Tencent Cloud SCF, Huawei Cloud FunctionGraph, Azure Functions. Maps to Alibaba Cloud Function Compute FC by memory configuration.

---

## 6. EBS / Cloud Disk Mapping

| Source Disk Type | Alibaba Cloud Disk Type | IOPS | Throughput |
|--------------|----------------|------|--------|
| AWS gp2 / Tencent SSD / Huawei SSD / Azure Premium SSD | ESSD PL0 | Baseline 3000 | 125 MB/s |
| AWS gp3 / High-Performance SSD | ESSD PL1 | Baseline 3000, adjustable to 16000 | 125-1000 MB/s |
| AWS io1/io2 / Ultra SSD | ESSD PL2/PL3 | Up to 256000 | Up to 4000 MB/s |
| AWS st1 / Tencent Efficient Disk / Huawei SATA | Efficient Cloud Disk | - | 500 MB/s |

### Disk Mapping Practical Rules

1. **System disk**: Uniformly use ESSD PL0, minimum 20GB (Alibaba Cloud ESSD minimum supported is 20GB)
2. **Data disk >= 20GB**: Use ESSD PL1 (GP3 equivalent)
3. **Data disk < 20GB**: **Must downgrade to ESSD PL0** (ESSD PL1 minimum requires 20GB, otherwise API error)
4. **ECS pricing must include both system disk and data disk**, otherwise results will be lower than actual

---

## 7. Other Service Mapping

| Source Service | Alibaba Cloud Product | Billing Method |
|---------|------------|---------|
| AWS Athena / Azure Synapse | MaxCompute | By data scanned |
| AWS EventBridge / Azure Event Grid | EventBridge | By event count |
| AWS SNS / Azure Service Bus (notifications) | Message Service MNS | By API calls |
| CloudWatch Logs / Azure Monitor Logs | Log Service SLS | Ingest + Index + Storage |
| NAT Gateway (all vendors) | NAT Gateway | BSS pricing |
| Elastic IP | Elastic IP (EIP) | BSS pricing |

---

## 8. Usage Conversion

| Dimension | Source Metering | Alibaba Cloud Metering | Conversion Notes |
|------|---------|------------|---------|
| Compute | Instance hours | ECS instance hours | 1:1 direct mapping |
| Storage capacity | GB·month | GB·month | 1:1 direct mapping |
| Data transfer | Data Transfer Out (GB) | Public network traffic (GB) | 1:1, note tiered pricing |
| Database storage | Storage GB | RDS / PolarDB storage GB | 1:1 |
| Object storage requests | PUT/GET requests | PUT/GET requests | 1:1 |
