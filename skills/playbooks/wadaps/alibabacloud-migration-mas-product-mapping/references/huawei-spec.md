# Huawei Cloud → Alibaba Cloud Spec Mapping

> This document is the Huawei Cloud detailed index for [SKILL.md](../SKILL.md) Section 4 "Instance Spec Mapping", including ECS instance families, RDS, GaussDB, DCS Redis, DDS MongoDB spec mapping and pricing examples.

## ECS → Alibaba Cloud ECS Instance Family Mapping

### General Purpose (1:4)

| Huawei Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| s3(General 3rd gen) | Intel 1:4 | ecs.g6 / ecs.g7 | Legacy |
| s6/s6e(General 6th gen) | Intel 1:4 | ecs.g7 | Mainstream |
| s7/s7n(General 7th gen) | Intel 1:4 | ecs.g7 / ecs.g8i | Mainstream |
| g6/g7(General Compute) | Intel 1:4 | ecs.g7 / ecs.g8i | |
| g7ne(Network Enhanced) | Intel 1:4 high-bandwidth | ecs.g7ne / ecs.g7 | Network-enhanced |
| sn3(General Early) | Intel 1:4 | ecs.g6 | Deprecated legacy |

### Compute Optimized (1:2)

| Huawei Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| c3/c3ne(Compute 3rd gen) | Intel 1:2 | ecs.c7 | Legacy |
| c6/c6s(Compute 6th gen) | Intel 1:2 | ecs.c7 | Mainstream |
| c7/c7n(Compute 7th gen) | Intel 1:2 | ecs.c7 / ecs.c8i | Mainstream |
| c7t(Compute 7th gen features) | Intel 1:2 | ecs.c7 | |
| c9(Kunpeng Compute 9th gen) | ARM 1:2 | ecs.c8y (Yitian ARM) | ARM |
| ac7(ARM Compute) | Kunpeng ARM 1:2 | ecs.c8y | ARM |
| hc2(HPC) | High-frequency 1:2 | ecs.hfc7 | High-frequency |

### Memory Optimized (1:8)

| Huawei Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| m3/m3ne(Memory 3rd gen) | Intel 1:8 | ecs.r7 | Legacy |
| m6/m6e(Memory 6th gen) | Intel 1:8 | ecs.r7 | Mainstream |
| m7/m7n(Memory 7th gen) | Intel 1:8 | ecs.r7 / ecs.r8i | Mainstream |
| m7ne(Network Enhanced Memory) | Intel 1:8 | ecs.r7 | Network-enhanced |
| e3/e3ne(Ultra-High Memory) | Intel 1:12~1:28 | ecs.r7 / ecs.re7 | Ultra-high memory |
| x1/x1e(Ultra-High Memory) | Intel 1:16+ | ecs.re7 | SAP/In-memory DB |

### ARM Kunpeng/Yitian

| Huawei Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| kc1(Kunpeng Compute) | ARM 1:2 | ecs.c8y (Yitian ARM) | |
| km1(Kunpeng General) | ARM 1:4 | ecs.g8y (Yitian ARM) | |
| kr1(Kunpeng Memory) | ARM 1:8 | ecs.r8y (Yitian ARM) | |
| ka1(Kunpeng General Early) | ARM 1:4 | ecs.g8y | Legacy |

### Local Disk / Storage Optimized

| Huawei Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| d6/d7(Dense Storage) | Local HDD | ecs.d3s | Big Data |
| i3/i3l(Ultra-High IO) | Local NVMe SSD | ecs.i3 / ecs.i4 | IO-intensive |
| ir3(Ultra-High IO Memory) | Local NVMe 1:8 | ecs.i3 | |

### GPU / Heterogeneous Computing

| Huawei Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| p2s/p2vs(GPU Compute) | V100 training | ecs.gn6v (V100) | Training |
| p3(GPU Compute 3rd gen) | A100/A800 | ecs.gn7e (A100) | Large-scale training |
| pi2(GPU Inference) | T4 inference | ecs.gn7i (T4) | Inference |
| g6v(GPU Graphics) | GPU rendering | ecs.vgn7i (vGPU) | Rendering |

### Burstable / Shared

| Huawei Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| t6/t6e(Burstable) | Burstable with credits | ecs.t6 | Only large; xlarge+ falls back to ecs.c7 |
| s6 Shared | Shared | ecs.s6 | Upgrade to g7/r7 when mem ratio>2 |

### Bare Metal Server

| Huawei Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| physical(Bare Metal General) | Physical 1:4 | ebmg7 | |
| physical.c(Bare Metal Compute) | Physical 1:2 | ebmc7 | |
| physical.m(Bare Metal Memory) | Physical 1:8 | ebmr7 | |
| physical.gpu(Bare Metal GPU) | Physical GPU | ebmgn7e | GPU training |

> **Coverage Note**: The above covers ~40+ Huawei Cloud ECS instance families with ~85%+ coverage. The few uncovered families (e.g., deprecated s1/s2/c1) are auto-mapped by CPU:memory ratio.

## Huawei Cloud ECS Spec Name Parsing

Huawei Cloud ECS spec naming format: `{vCPU}vCPUs | {Mem}GB | {family}.{size}.{ratio}`, e.g., `4vCPUs | 8GB | c7.xlarge.2`.

Derivation process:
1. **Parse spec name**: `4vCPUs | 8GB | c7.xlarge.2` → vCPU=4, Mem=8, family=c7
2. **Family → Alibaba Cloud spec family**: c7 → `ecs.c7`
3. **vCPU → Alibaba Cloud size**: 4vCPU → `xlarge`
4. **Combine**: `ecs.c7.xlarge`

```
# Huawei Cloud vCPU → Alibaba Cloud size mapping (same as AWS/Tencent Cloud)
# 1vCPU → large, 2vCPU → large, 4vCPU → xlarge
# 8vCPU → 2xlarge, 16vCPU → 4xlarge, 32vCPU → 8xlarge
# 64vCPU → 16xlarge, 128vCPU → 32xlarge
```

> **Huawei Cloud spec suffix meaning**: `.{ratio}` indicates memory-to-vCPU ratio (`.2`=1:2, `.4`=1:4, `.8`=1:8). When suffix doesn't match mapping table, adjust by actual memory ratio: 1:2→ecs.c7, 1:4→ecs.g7, 1:8→ecs.r7.

## RDS → Alibaba Cloud RDS Spec

| Huawei Cloud RDS Spec | vCPU | Memory(GB) | Alibaba Cloud RDS MySQL Spec | Alibaba Cloud RDS PG Spec |
|-----------------|------|---------|--------------------------|------------------------|
| 1C2G | 1 | 2 | rds.mysql.s1.small | pg.n2.small.1 |
| 2C4G | 2 | 4 | rds.mysql.s2.large | pg.n2.small.2c |
| 2C8G | 2 | 8 | rds.mysql.s2.xlarge | pg.n2.medium.2c |
| 4C8G | 4 | 8 | rds.mysql.s3.small | pg.n4.medium.1 |
| 4C16G | 4 | 16 | rds.mysql.s3.large | pg.n2.medium.2c |
| 8C16G | 8 | 16 | rds.mysql.c1.medium | pg.n4.large.1 |
| 8C32G | 8 | 32 | rds.mysql.m1.medium | pg.n2.large.2c |
| 16C32G | 16 | 32 | rds.mysql.c1.xlarge | pg.n4.xlarge.1 |
| 16C64G | 16 | 64 | rds.mysql.m1.xlarge | pg.n2.xlarge.2c |
| 32C128G | 32 | 128 | rds.mysql.m1.2xlarge | pg.n4.2xlarge.1 |
| 64C256G | 64 | 256 | rds.mysql.m1.4xlarge | pg.n4.4xlarge.1 |

> When exact spec is unavailable, infer by environment: prod→rds.mysql.m1.medium(8C32G), dev/test→rds.mysql.s2.large(2C4G).

## GaussDB → Alibaba Cloud PolarDB Spec

| Huawei Cloud GaussDB Spec | vCPU | Memory(GB) | PolarDB MySQL Spec | PolarDB PG Spec |
|----------------------|------|---------|-------------------------------|------------------------------|
| 2C8G | 2 | 8 | polar.mysql.g2.xlarge | polar.pg.g2.xlarge |
| 4C16G | 4 | 16 | polar.mysql.g4.xlarge | polar.pg.g4.xlarge |
| 8C32G | 8 | 32 | polar.mysql.g8.xlarge | polar.pg.g8.xlarge |
| 8C64G | 8 | 64 | polar.mysql.g8.2xlarge | polar.pg.g8.2xlarge |
| 16C64G | 16 | 64 | polar.mysql.g8.2xlarge | polar.pg.g8.2xlarge |
| 16C128G | 16 | 128 | polar.mysql.g8.4xlarge | polar.pg.g8.4xlarge |
| 32C256G | 32 | 256 | polar.mysql.g8.8xlarge | polar.pg.g8.8xlarge |
| 64C512G | 64 | 512 | polar.mysql.g8.16xlarge | polar.pg.g8.16xlarge |

> GaussDB uses disaggregated storage-compute architecture, consistent with PolarDB. Preferably map to PolarDB. For pricing, product_code=polardb returns single-node monthly price; actual cost = single-node price × node count.

## DCS Redis → Alibaba Cloud Redis Spec

| Huawei Cloud DCS Redis Spec | Memory | Alibaba Cloud Redis Spec | capacity(MB) |
|------------------------|------|-------------------------------|-------------|
| Primary-Standby 256MB | 256MB | redis.amber.master.small.multithread | 256 |
| Primary-Standby 1GB | 1GB | redis.amber.master.small.multithread | 1024 |
| Primary-Standby 2GB | 2GB | redis.amber.master.mid.multithread | 2048 |
| Primary-Standby 4GB | 4GB | redis.amber.master.stand.multithread | 4096 |
| Primary-Standby 8GB | 8GB | redis.amber.master.large.multithread | 8192 |
| Primary-Standby 16GB | 16GB | redis.amber.master.2xlarge.multithread | 16384 |
| Primary-Standby 32GB | 32GB | redis.amber.master.4xlarge.multithread | 32768 |
| Primary-Standby 64GB | 64GB | redis.amber.master.8xlarge.multithread | 65536 |

> For Huawei Cloud DCS Proxy cluster pricing, capacity should pass total memory. When exact spec unavailable, infer by environment: prod→16GB, dev/test→4GB.

## DDS MongoDB → Alibaba Cloud MongoDB Spec

| Huawei Cloud DDS Spec | vCPU | Memory | Alibaba Cloud MongoDB Spec | Notes |
|------------------|------|------|-------------------------------|------|
| 2C4G | 2 | 4GB | mdb.shard.2x.large.d | Dedicated 2C4G |
| 4C8G | 4 | 8GB | mdb.shard.2x.xlarge.d | Dedicated 4C8G |
| 8C16G | 8 | 16GB | mdb.shard.2x.2xlarge.d | Dedicated 8C16G |
| 16C32G | 16 | 32GB | mdb.shard.2x.4xlarge.d | Dedicated 16C32G |
| 32C64G | 32 | 64GB | mdb.shard.2x.8xlarge.d | Dedicated 32C64G |

> When exact spec unavailable, infer by environment: prod→mdb.shard.2x.xlarge.d(4C8G), dev/test→mdb.shard.2x.large.d(2C4G).

## Batch Pricing Call Example

```json
{
  "region_id": "cn-shenzhen",
  "period": 1,
  "items": [
    { "product_code": "ecs", "instance_spec": "ecs.g7.xlarge", "disk_size": 80, "data_disk_size": 200, "data_disk_pl": "PL1" },
    { "product_code": "rds", "instance_spec": "rds.mysql.m1.medium", "engine": "MySQL", "engine_version": "8.0", "disk_size": 200 },
    { "product_code": "polardb", "instance_spec": "polar.mysql.g8.xlarge", "engine": "MySQL" },
    { "product_code": "redis", "instance_spec": "redis.amber.master.2xlarge.multithread", "capacity": 16384 },
    { "product_code": "mongodb", "instance_spec": "mdb.shard.2x.xlarge.d", "disk_size": 40 }
  ]
}
```
