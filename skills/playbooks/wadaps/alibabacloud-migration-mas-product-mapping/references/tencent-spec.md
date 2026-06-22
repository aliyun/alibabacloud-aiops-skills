# Tencent Cloud → Alibaba Cloud Spec Mapping

> This document is the Tencent Cloud detailed index for [SKILL.md](../SKILL.md) Section 4 "Instance Spec Mapping", including CVM instance families, CDB MySQL, TDSQL-C, Redis, MongoDB spec mapping and pricing examples.

## CVM → ECS Instance Family Mapping

### Standard (General 1:4, Most Common)

| Tencent Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| S3(Standard 3rd gen) | Intel General 1:4 | ecs.g6 / ecs.g7 | Legacy, map to g7 |
| S4(Standard 4th gen) | Intel General 1:4 | ecs.g7 | |
| S5(Standard 5th gen) | Intel Ice Lake 1:4 | ecs.g7 / ecs.g8i | Mainstream |
| S6(Standard 6th gen) | Intel General 1:4 | ecs.g7 / ecs.g8i | Mainstream |
| S7(Standard 7th gen) | Intel Sapphire Rapids 1:4 | ecs.g8i | New gen |
| S8(Standard 8th gen) | Intel Latest 1:4 | ecs.g8i | Latest |
| SA2/SA3(AMD Standard) | AMD EPYC 1:4 | ecs.g8a | |
| SA5(AMD Standard 5th gen) | AMD Genoa 1:4 | ecs.g8a | New gen |
| SR1(ARM Standard) | Ampere ARM 1:4 | ecs.g8y (Yitian ARM) | ARM |

### Compute Optimized (1:2)

| Tencent Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| C4(Compute 4th gen) | Intel Compute 1:2 | ecs.c7 | Legacy |
| C6(Compute 6th gen) | Intel Compute 1:2 | ecs.c7 / ecs.c8i | Mainstream |
| C7(Compute 7th gen) | Intel Compute 1:2 | ecs.c7 / ecs.c8i | Mainstream |
| C8(Compute 8th gen) | Intel Latest 1:2 | ecs.c8i | Latest |
| CA3/CA5(AMD Compute) | AMD EPYC 1:2 | ecs.c8a | |

### Memory Optimized (1:8)

| Tencent Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| M4(Memory 4th gen) | Intel Memory 1:8 | ecs.r7 | Legacy |
| M5(Memory 5th gen) | Intel Memory 1:8 | ecs.r7 / ecs.r8i | |
| M6(Memory 6th gen) | Intel Memory 1:8 | ecs.r7 / ecs.r8i | Mainstream |
| M7(Memory 7th gen) | Intel Memory 1:8 | ecs.r7 / ecs.r8i | Mainstream |
| M8(Memory 8th gen) | Intel Latest 1:8 | ecs.r8i | Latest |
| MA2/MA3(AMD Memory) | AMD EPYC 1:8 | ecs.r8a | |

### High IO / Local Storage

| Tencent Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| I6/I9(High IO) | Local NVMe SSD | ecs.i3 / ecs.i4 | Local disk released with instance |
| IT5/IT7(Big Data) | Local HDD large capacity | ecs.d3s | Big data scenarios |
| D3(Dense Storage) | Local HDD ultra-large | ecs.d3s / ecs.d2s | Massive storage |

### GPU / Heterogeneous Computing

| Tencent Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| GN7(GPU Compute) | Tesla T4 inference | ecs.gn7i (T4) | Inference/light training |
| GN10X/GN10Xp(GPU Compute) | Tesla V100 training | ecs.gn6v (V100) | Training |
| GN14(GPU Compute) | A100/A800 training | ecs.gn7e (A100) | Large-scale training |
| GI3X/GI5X(GPU Inference) | T4 dedicated inference | ecs.gn7i (T4) | Inference optimized |
| PNV4ne(GPU Rendering) | GPU rendering | ecs.vgn7i (vGPU) | Rendering/remote desktop |

### Burstable / Other

| Tencent Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| T6(Burstable) | Burstable with credits | ecs.t6 | Only large (xlarge+ falls back to ecs.c7) |
| S5se(Storage Enhanced) | High-throughput 1:4 | ecs.g7se | Storage enhanced |
| BC1/BS1(Batch Compute) | Spot instance | ecs.c7 / ecs.g7 (preemptible) | Map to preemptible |

### Bare Metal Server

| Tencent Cloud Instance Family | Characteristics | Alibaba Cloud Recommended Spec | Notes |
|------------|------|----------------|------|
| BMS5/BMS6(Bare Metal Standard) | Physical 1:4 | Bare Metal ebmg7 | |
| BMC5(Bare Metal Compute) | Physical 1:2 | Bare Metal ebmc7 | |
| BMM5(Bare Metal Memory) | Physical 1:8 | Bare Metal ebmr7 | |
| BMGN7s/BMGNV4(Bare Metal GPU) | Physical GPU | Bare Metal ebmgn7e | GPU training |

> **Coverage Note**: The above covers ~40+ Tencent Cloud CVM instance families with ~85%+ coverage. The few uncovered families (e.g., deprecated S1/S2/C2/C3, FPGA FX4) are auto-mapped by CPU:memory ratio.

## CVM Spec Size Conversion

| Tencent Cloud Size | vCPU | Memory(GB) | Alibaba Cloud Size |
|------------|------|---------|------------|
| SMALL1/SMALL2/SMALL4 | 1 | 1/2/4 | large(minimum purchasable) |
| MEDIUM4/MEDIUM8 | 2 | 4/8 | large |
| LARGE8/LARGE16 | 4 | 8/16 | xlarge |
| 2XLARGE16/2XLARGE32 | 8 | 16/32 | 2xlarge |
| 4XLARGE32/4XLARGE64 | 16 | 32/64 | 4xlarge |
| 8XLARGE64/8XLARGE128 | 32 | 64/128 | 8xlarge |
| 16XLARGE128/16XLARGE256 | 64 | 128/256 | 16xlarge |
| 32XLARGE256/32XLARGE512 | 128 | 256/512 | 32xlarge |
| 64XLARGE512/64XLARGE1024 | 256 | 512/1024 | 52xlarge(bare metal level) |

> **Auto-Fallback Rule**: When mapped spec family is unavailable in target region, fall back in priority: same-generation substitute (e.g., g8i→g7) → same-ratio substitute (e.g., g7→c7 when 1:2 fits) → general-purpose fallback (ecs.g7).

## CVM Spec Name Parsing and Pricing Derivation

CVM spec naming format: `{Family}{Gen}.{Size}`, e.g., `S5.LARGE8` = Standard 5th gen, 4vCPU 8GiB.

Derivation process:
1. **Parse spec name**: `S5.LARGE8` → Family=S5, Size=LARGE, memory_suffix=8
2. **Family → Alibaba Cloud spec family**: S5 → `ecs.g7` or `ecs.g8i`
3. **Size → Alibaba Cloud size**: LARGE → `xlarge` (4vCPU)
4. **Combine**: `ecs.g7.xlarge` or `ecs.g8i.xlarge`
5. **Call pricing**: `POST /api/pricing/batch`, `product_code=ecs`, `instance_spec=ecs.g7.xlarge`

```
# CVM spec name Size meaning
# SMALL = 1vCPU, MEDIUM = 2vCPU, LARGE = 4vCPU, {N}XLARGE = N*4 vCPU
# Suffix number = Memory GiB (e.g., LARGE8 = 4C8G, 2XLARGE16 = 8C16G)
```

> **CVM Pricing Note**: CVM memory suffix may not match the default ratio of Alibaba Cloud spec family (e.g., S5.LARGE8 = 4C8G is 1:2 not standard 1:4). Prioritize matching by CPU:memory ratio: 1:1→ecs.s6, 1:2→ecs.c7, 1:4→ecs.g7, 1:8→ecs.r7.

## CDB MySQL → Alibaba Cloud RDS Spec

| CDB MySQL Spec | vCPU | Memory(GB) | Alibaba Cloud RDS MySQL Spec | Alibaba Cloud RDS PG Spec |
|---------------|------|---------|--------------------------|------------------------|
| 1C1G | 1 | 1 | rds.mysql.t1.small | pg.n1.micro.1 |
| 1C2G | 1 | 2 | rds.mysql.s1.small | pg.n2.small.1 |
| 2C4G | 2 | 4 | rds.mysql.s2.large | pg.n2.small.2c |
| 2C8G | 2 | 8 | rds.mysql.s2.xlarge | pg.n2.medium.2c |
| 4C8G | 4 | 8 | rds.mysql.s3.small | pg.n4.medium.1 |
| 4C16G | 4 | 16 | rds.mysql.s3.large | pg.n2.medium.2c |
| 8C16G | 8 | 16 | rds.mysql.c1.medium | pg.n4.large.1 |
| 8C32G | 8 | 32 | rds.mysql.m1.medium | pg.n2.large.2c |
| 16C32G | 16 | 32 | rds.mysql.c1.xlarge | pg.n4.xlarge.1 |
| 16C64G | 16 | 64 | rds.mysql.m1.xlarge | pg.n2.xlarge.2c |
| 16C128G | 16 | 128 | rds.mysql.r1.xlarge | pg.n8.xlarge.2c |
| 32C128G | 32 | 128 | rds.mysql.m1.2xlarge | pg.n4.2xlarge.1 |
| 32C256G | 32 | 256 | rds.mysql.r1.2xlarge | pg.n8.2xlarge.2c |
| 64C256G | 64 | 256 | rds.mysql.m1.4xlarge | pg.n4.4xlarge.1 |
| 64C512G | 64 | 512 | rds.mysql.r1.4xlarge | pg.n8.4xlarge.2c |

> **RDS Spec Naming Convention**: `rds.mysql.{CPU:memory_ratio}.{size}`, where s=1:2, m=1:4, c=1:2(compute), r=1:8(memory).
> **CDB MariaDB / SQL Server**: Same logic, replace `rds.mysql` with `rds.mariadb` / `rds.mssql`.

## TDSQL-C → Alibaba Cloud PolarDB Spec

| TDSQL-C Spec | vCPU | Memory(GB) | PolarDB MySQL Spec | PolarDB PG Spec |
|--------------|------|---------|-------------------------------|------------------------------|
| 1C1G | 1 | 1 | polar.mysql.g2.medium | polar.pg.g2.medium |
| 1C2G | 1 | 2 | polar.mysql.g2.medium | polar.pg.g2.medium |
| 2C4G | 2 | 4 | polar.mysql.g2.large | polar.pg.g2.large |
| 2C8G | 2 | 8 | polar.mysql.g2.xlarge | polar.pg.g2.xlarge |
| 4C16G | 4 | 16 | polar.mysql.g4.xlarge | polar.pg.g4.xlarge |
| 8C32G | 8 | 32 | polar.mysql.g8.xlarge | polar.pg.g8.xlarge |
| 8核64GB | 8 | 64 | polar.mysql.g8.2xlarge | polar.pg.g8.2xlarge |
| 16C64G | 16 | 64 | polar.mysql.g8.2xlarge | polar.pg.g8.2xlarge |
| 16C128G | 16 | 128 | polar.mysql.g8.4xlarge | polar.pg.g8.4xlarge |
| 32C128G | 32 | 128 | polar.mysql.g8.4xlarge | polar.pg.g8.4xlarge |
| 32C256G | 32 | 256 | polar.mysql.g8.8xlarge | polar.pg.g8.8xlarge |
| 64C256G | 64 | 256 | polar.mysql.g8.8xlarge | polar.pg.g8.8xlarge |
| 64C512G | 64 | 512 | polar.mysql.g8.16xlarge | polar.pg.g8.16xlarge |

> **PolarDB Spec Naming Convention**: `polar.{engine}.g{Mem/vCPU_multiplier}.{size}`, e.g., g2=1:2, g4=1:4, g8=1:8.
> **PolarDB Pricing Note**: The above pricing returns **single-node monthly price**. TDSQL-C minimum deployment = 1 primary + 1 read-only = 2 nodes; actual monthly cost = single-node price × node count.

## Redis → Alibaba Cloud Redis Spec

| Tencent Cloud Redis Spec | Memory | Alibaba Cloud Redis Spec | capacity(MB) |
|-------------------|------|-------------------------------|-------------|
| 256MB Standard | 256MB | redis.amber.master.small.multithread | 256 |
| 1GB Standard | 1GB | redis.amber.master.small.multithread | 1024 |
| 2GB Standard | 2GB | redis.amber.master.mid.multithread | 2048 |
| 4GB Standard | 4GB | redis.amber.master.stand.multithread | 4096 |
| 8GB Standard | 8GB | redis.amber.master.large.multithread | 8192 |
| 16GB Standard | 16GB | redis.amber.master.2xlarge.multithread | 16384 |
| 32GB Standard | 32GB | redis.amber.master.4xlarge.multithread | 32768 |
| 64GB Standard | 64GB | redis.amber.master.8xlarge.multithread | 65536 |

> For cluster Redis pricing, capacity should pass total memory (e.g., 4 shards × 8GB = 32GB total).

## MongoDB → Alibaba Cloud MongoDB Spec

| Tencent Cloud MongoDB Spec | vCPU | Memory | Alibaba Cloud MongoDB Spec | Notes |
|---------------------|------|------|-------------------------------|------|
| 2C4G | 2 | 4GB | mdb.shard.2x.large.d | Dedicated 2C4G |
| 4C8G | 4 | 8GB | mdb.shard.2x.xlarge.d | Dedicated 4C8G |
| 8C16G | 8 | 16GB | mdb.shard.2x.2xlarge.d | Dedicated 8C16G |
| 16C32G | 16 | 32GB | mdb.shard.2x.4xlarge.d | Dedicated 16C32G |
| 32核64GB | 32 | 64GB | mdb.shard.2x.8xlarge.d | Dedicated 32C64G |

> MongoDB pricing via BSS `GetSubscriptionPrice` (ProductCode=dds), default storage 40GB.

## Batch Pricing Call Example

```json
{
  "region_id": "cn-beijing",
  "period": 1,
  "items": [
    { "product_code": "ecs", "instance_spec": "ecs.g7.xlarge", "disk_size": 50, "data_disk_size": 100, "data_disk_pl": "PL1" },
    { "product_code": "rds", "instance_spec": "rds.mysql.s3.large", "engine": "MySQL", "engine_version": "8.0", "disk_size": 200 },
    { "product_code": "polardb", "instance_spec": "polar.mysql.g2.xlarge", "engine": "MySQL" },
    { "product_code": "redis", "instance_spec": "redis.amber.master.2xlarge.multithread", "capacity": 16384 },
    { "product_code": "mongodb", "instance_spec": "mdb.shard.2x.xlarge.d", "disk_size": 40 }
  ]
}
```
