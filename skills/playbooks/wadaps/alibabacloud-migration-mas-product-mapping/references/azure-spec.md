# Azure → Alibaba Cloud Spec Mapping

> This document is the Azure detailed index for [SKILL.md](../SKILL.md) Section 4 "Instance Spec Mapping", including VM instance series, Database for MySQL/PG, Cache for Redis, and Cosmos DB spec mapping.

## VM → Alibaba Cloud ECS Instance Series Mapping

### Burstable

| Azure VM Series | Characteristics | Alibaba Cloud ECS Spec Family |
|-------------|------|----------------|
| Bsv2 / Basv2 | Burstable Intel/AMD | ecs.t6 |
| B1ls / B1s / B2s | Burstable legacy | ecs.t6 |

### General Purpose (1:4)

| Azure VM Series | Characteristics | Alibaba Cloud ECS Spec Family |
|-------------|------|----------------|
| Dv4 / Dsv4 | Intel Ice Lake | ecs.g7 |
| Dv5 / Dsv5 | Intel Sapphire Rapids | ecs.g8i |
| Dasv5 / Dadsv5 | AMD EPYC | ecs.g8a |
| Ddsv5 | Intel + local NVMe | ecs.g8i |
| Dpdsv6 / Dpldsv6 | ARM Cobalt 100 | ecs.g8y |
| Dpsv5 / Dplsv5 | ARM Ampere Altra | ecs.g8y |

### Compute Optimized (1:2)

| Azure VM Series | Characteristics | Alibaba Cloud ECS Spec Family |
|-------------|------|----------------|
| Fsv2 | Intel Xeon | ecs.c7 |
| Fv6 / Falsv6 | Intel Granite Rapids | ecs.c8i |
| Fasv6 | AMD EPYC | ecs.c8a |

### Memory Optimized (1:8)

| Azure VM Series | Characteristics | Alibaba Cloud ECS Spec Family |
|-------------|------|----------------|
| Ev4 / Esv4 | Intel Ice Lake | ecs.r7 |
| Ev5 / Esv5 | Intel Sapphire Rapids | ecs.r8i |
| Easv5 / Eadsv5 | AMD EPYC | ecs.r8a |
| Edsv5 / Ebdsv5 | Intel + local NVMe | ecs.r8i |
| Ebsv5 | Intel + high storage bandwidth | ecs.r8i |
| Epsv5 / Epdsv5 | ARM Ampere | ecs.r8y |

### Ultra-High Memory

| Azure VM Series | Characteristics | Alibaba Cloud ECS Spec Family |
|-------------|------|----------------|
| Mv2 / Msv2 / Mdsv2 | SAP HANA / ultra-high memory | ecs.re7 |

### Storage Optimized

| Azure VM Series | Characteristics | Alibaba Cloud ECS Spec Family |
|-------------|------|----------------|
| Lsv3 / Lasv3 | Local NVMe SSD | ecs.i3 / ecs.i4 |

### GPU

| Azure VM Series | Characteristics | Alibaba Cloud ECS Spec Family |
|-------------|------|----------------|
| NCasT4_v3 | NVIDIA T4 inference | ecs.gn7i |
| NCads_A100_v4 | NVIDIA A100 training | ecs.gn7e |
| NCv3 / NC_A100_v4 | NVIDIA V100/A100 | ecs.gn7e |
| NDv2 / NDs_H100_v5 | NVIDIA high-end training | ecs.gn7e / ecs.gn8 |
| NVv4 / NVadsA10_v5 | AMD GPU / A10 rendering | ecs.vgn7i |

### HPC

| Azure VM Series | Characteristics | Alibaba Cloud ECS Spec Family |
|-------------|------|----------------|
| HBv3 / HBv4 | AMD EPYC HPC | ecs.hfc7 |
| HXv3 / HXv4 | Intel Xeon HPC | ecs.hfc7 |

### ARM

| Azure VM Series | Characteristics | Alibaba Cloud ECS Spec Family |
|-------------|------|----------------|
| Dpsv5 / Dplsv5 (1:4) | ARM General | ecs.g8y |
| Epsv5 / Epdsv5 (1:8) | ARM Memory | ecs.r8y |
| Dpdsv6 / Dpldsv6 (1:2) | ARM Compute | ecs.c8y |

## Azure Spec Size Conversion

| Azure Size | vCPU | Alibaba Cloud Size |
|-----------|------|------------|
| Standard_D2s_v5 | 2 | large |
| Standard_D4s_v5 | 4 | xlarge |
| Standard_D8s_v5 | 8 | 2xlarge |
| Standard_D16s_v5 | 16 | 4xlarge |
| Standard_D32s_v5 | 32 | 8xlarge |
| Standard_D48s_v5 | 48 | 13xlarge |
| Standard_D64s_v5 | 64 | 16xlarge |
| Standard_D96s_v5 | 96 | 32xlarge |

> Azure naming convention: `Standard_{Series}{vCPU}{options}_v{version}`, map directly to Alibaba Cloud size by vCPU count.

## Database for MySQL/PostgreSQL → Alibaba Cloud RDS

| Azure Spec Series | vCPU | Memory(GB) | Alibaba Cloud RDS MySQL Spec | Alibaba Cloud RDS PG Spec |
|--------------|------|---------|---------------------|-------------------|
| B_Standard_B1s | 1 | 2 | rds.mysql.s1.small | pg.n2.small.1 |
| B_Standard_B2s | 2 | 4 | rds.mysql.s2.large | pg.n2.small.2c |
| B_Standard_B4ms | 4 | 8 | rds.mysql.s3.small | pg.n4.medium.1 |
| B_Standard_B8ms | 8 | 16 | rds.mysql.c1.medium | pg.n4.large.1 |
| B_Standard_B12ms | 12 | 24 | rds.mysql.c1.xlarge | pg.n4.xlarge.1 |
| B_Standard_B16ms | 16 | 32 | rds.mysql.c1.xlarge | pg.n4.xlarge.1 |
| B_Standard_B20ms | 20 | 80 | rds.mysql.m1.xlarge | pg.n2.xlarge.2c |
| D_Standard_D2ds | 2 | 8 | rds.mysql.s2.xlarge | pg.n2.medium.1 |
| D_Standard_D4ds | 4 | 16 | rds.mysql.s3.large | pg.n4.medium.1 |
| D_Standard_D8ds | 8 | 32 | rds.mysql.m1.medium | pg.n2.large.2c |
| D_Standard_D16ds | 16 | 64 | rds.mysql.m1.xlarge | pg.n2.xlarge.2c |
| D_Standard_D32ds | 32 | 128 | rds.mysql.m1.2xlarge | pg.n4.2xlarge.1 |
| D_Standard_D48ds | 48 | 192 | rds.mysql.m1.4xlarge | pg.n4.4xlarge.1 |
| D_Standard_D64ds | 64 | 256 | rds.mysql.m1.4xlarge | pg.n4.4xlarge.1 |
| MO_Standard_E2ds | 2 | 16 | rds.mysql.s2.xlarge | pg.n2.medium.1 |
| MO_Standard_E4ds | 4 | 32 | rds.mysql.s3.large | pg.n4.medium.1 |
| MO_Standard_E8ds | 8 | 64 | rds.mysql.m1.medium | pg.n2.large.2c |
| MO_Standard_E16ds | 16 | 128 | rds.mysql.m1.xlarge | pg.n2.xlarge.2c |
| MO_Standard_E32ds | 32 | 256 | rds.mysql.m1.2xlarge | pg.n4.2xlarge.1 |
| MO_Standard_E48ds | 48 | 384 | rds.mysql.m1.4xlarge | pg.n4.4xlarge.1 |
| MO_Standard_E64ds | 64 | 512 | rds.mysql.m1.4xlarge | pg.n4.4xlarge.1 |
| MO_Standard_E96ds | 96 | 672 | rds.mysql.m1.8xlarge | pg.n8.8xlarge.1 |

> Azure database spec naming: `{SKU_type}_Standard_{Series}{vCPU}`, where B=Burstable, D=General Purpose, MO=Memory Optimized.

## Cache for Redis → Alibaba Cloud Redis

| Azure Spec | Memory(MB) | Alibaba Cloud Redis Spec | Description |
|-----------|---------|---------------------|------|
| Basic C0 | 250 | redis.amber.master.small.multithread | Cloud-native 256MB |
| Basic C1 | 1024 | redis.amber.master.small.multithread | Cloud-native 1GB |
| Basic C2 | 2560 | redis.amber.master.mid.multithread | Cloud-native 2GB |
| Basic C3 | 6144 | redis.amber.master.large.multithread | Cloud-native 8GB |
| Standard C0 | 250 | redis.amber.master.small.multithread | Cloud-native 256MB dual-replica |
| Standard C1 | 1024 | redis.amber.master.small.multithread | Cloud-native 1GB dual-replica |
| Standard C2 | 2560 | redis.amber.master.mid.multithread | Cloud-native 2GB dual-replica |
| Standard C3 | 6144 | redis.amber.master.large.multithread | Cloud-native 8GB dual-replica |
| Standard C4 | 13312 | redis.amber.master.2xlarge.multithread | Cloud-native 16GB dual-replica |
| Standard C5 | 26624 | redis.amber.master.4xlarge.multithread | Cloud-native 32GB dual-replica |
| Standard C6 | 53248 | redis.amber.master.8xlarge.multithread | Cloud-native 64GB dual-replica |
| Premium P1 | 6144 | redis.amber.master.large.multithread | Cloud-native 8GB |
| Premium P2 | 13312 | redis.amber.master.2xlarge.multithread | Cloud-native 16GB |
| Premium P3 | 26624 | redis.amber.master.4xlarge.multithread | Cloud-native 32GB |
| Premium P4 | 53248 | redis.amber.master.8xlarge.multithread | Cloud-native 64GB |
| Premium P5 | 122880 | redis.shard.amber.ce13.5.default | Cloud-native 128GB cluster |

## Cosmos DB (MongoDB API) → Alibaba Cloud MongoDB

| Azure Cosmos DB Config | Mapping Logic | Alibaba Cloud MongoDB Spec |
|--------------------|---------|--------------------|
| 400-1000 RU/s | Small workload | mdb.shard.2x.large.d (2C4G) |
| 1000-4000 RU/s | Medium workload | mdb.shard.2x.xlarge.d (4C8G) |
| 4000-10000 RU/s | Large workload | mdb.shard.2x.2xlarge.d (8C16G) |
| 10000-50000 RU/s | Extra-large workload | mdb.shard.2x.4xlarge.d (16C32G) |
| >50000 RU/s | Sharded cluster | mdb.shard.2x.8xlarge.d (32C64G) |

> Cosmos DB is billed by RU/s with no direct spec correspondence. Mapping logic: every 1000 RU/s ≈ 2vCPU equivalent compute power.
