# AWS EC2 → Alibaba Cloud ECS Spec Mapping

> This document is the AWS detailed index for [SKILL.md](../SKILL.md) Section 4 "Instance Spec Mapping", including instance family mapping, ARM/Intel/AMD series breakdown, and spec size conversion.

## Instance Family Overview

| AWS Instance Family | Characteristics | Alibaba Cloud ECS Series | Recommended Spec Family |
|-----------|------|---------------|----------|
| t2/t3/t3a/t4g (burstable) | Burstable performance, credits | Burstable Performance | ecs.t5 / ecs.t6 |
| m5/m5a/m5d/m5n/m6i/m6a/m7i/m7a/m8i (general) | Balanced 1:4 ratio | General Purpose | ecs.g7 / ecs.g8i / ecs.g8a |
| c5/c5a/c5d/c5n/c6i/c6a/c7i/c7a (compute) | Compute optimized 1:2 | Compute Optimized | ecs.c7 / ecs.c8i / ecs.c8a |
| r5/r5a/r5d/r5n/r6i/r6a/r7i/r7a (memory) | Memory optimized 1:8 | Memory Optimized | ecs.r7 / ecs.r8i / ecs.r8a |
| x1/x1e/x2idn/x2gd/u-*tb1 (high-memory) | Ultra-high memory/SAP | Memory Optimized | ecs.re7 |
| i3/i3en/i4i/i4g/im4gn/is4gen (storage optimized) | Local NVMe SSD | Local SSD | ecs.i3 / ecs.i4 |
| d2/d3/d3en/h1 (dense storage) | Large capacity HDD | Big Data | ecs.d2s / ecs.d3s |
| hpc6a/hpc6id/hpc7a/hpc7g (HPC) | High-performance computing | High-Frequency/Compute | ecs.hfc7 |
| m5zn/z1d (high-frequency) | High clock speed | High-Frequency | ecs.hfg7 / ecs.hfr7 |
| p3/p4d/p5 (GPU training) | GPU V100/A100/H100 | GPU Compute | ecs.gn6v / ecs.gn7e / ecs.gn8 |
| g4dn/g4ad/g5/g6 (GPU inference) | GPU T4/A10/L4 | GPU Inference | ecs.gn7i / ecs.gn7 / ecs.gn8i |
| inf1/inf2 (inference) | AWS Inferentia | GPU Inference | ecs.gn7i / ecs.gn8i |
| dl1/dl2q/trn1/trn2 (training) | Gaudi/Trainium | GPU Training | ecs.gn7e / ecs.gn8 |
| mac1/mac2 (Mac) | macOS development | General Purpose | ecs.g7 |

## ARM Graviton → Alibaba Cloud Yitian ARM

| AWS Instance Family | Type | Alibaba Cloud Spec Family | Notes |
|-----------|------|------------|------|
| c6g/c6gd/c6gn/c7g/c7gd/c7gn/c8g | ARM Compute | ecs.c8y | Yitian ARM Compute |
| m6g/m6gd/m7g/m7gd/m8g | ARM General | ecs.g8y | Yitian ARM General |
| r6g/r6gd/r7g/r7gd/r8g | ARM Memory | ecs.r8y | Yitian ARM Memory |
| t4g | ARM Burstable | ecs.t6-c1m2 | Burstable (only large available) |
| x2gd | ARM High-Memory | ecs.re7 | Ultra-high memory |
| im4gn/is4gen/i4g | ARM Storage | ecs.i4 | Local SSD |
| a1 | ARM General | ecs.g8y | Yitian ARM General |
| hpc7g | ARM HPC | ecs.hfc7 | High-performance computing |

## Intel Series

| AWS Instance Family | Alibaba Cloud Spec Family |
|-----------|------------|
| c5/c5d/c5n | ecs.c7 |
| c6i/c6id/c6in | ecs.c8i |
| c7i/c7i-flex | ecs.c8i |
| m5/m5d/m5n/m5dn | ecs.g7 |
| m6i/m6id/m6idn/m6in | ecs.g8i |
| m7i/m7i-flex/m8i | ecs.g8i |
| r5/r5d/r5n/r5dn/r5b | ecs.r7 |
| r6i/r6id/r6idn/r6in | ecs.r8i |
| r7i/r7iz | ecs.r8i |

## AMD Series

| AWS Instance Family | Alibaba Cloud Spec Family |
|-----------|------------|
| c5a/c5ad | ecs.c7a |
| c6a/c7a | ecs.c8a |
| m5a/m5ad | ecs.g7a |
| m6a/m7a | ecs.g8a |
| r5a/r5ad | ecs.r7a |
| r6a/r7a | ecs.r8a |

> **t6 Burstable Size Limitation (Verified)**: Alibaba Cloud `ecs.t6-c1m2` series in cn-beijing only has `large` (2vCPU 4GiB) available for purchase; `xlarge` and `2xlarge` do not exist. When AWS burstable instances require xlarge or above, fall back to standard compute `ecs.c8y.xlarge`.

## Spec Size Conversion (size suffix)

| AWS Size | vCPU | Memory(GB) | Alibaba Cloud Size | Notes |
|----------|------|---------|------------|------|
| nano | 2 | 0.5 | large | t6 minimum available is large |
| micro | 2 | 1 | large | t6 minimum available is large |
| small | 2 | 2 | large | t6 minimum available is large |
| medium | 2 | 4 | large | |
| large | 2 | 8 | large | |
| xlarge | 4 | 16 | xlarge | t6 unavailable, fall back to ecs.c8y.xlarge |
| 2xlarge | 8 | 32 | 2xlarge | t6 unavailable, fall back to ecs.c8y.2xlarge |
| 4xlarge | 16 | 64 | 4xlarge | |
| 8xlarge | 32 | 128 | 8xlarge | |
| 12xlarge | 48 | 192 | 13xlarge (nearest match) | |
| 16xlarge | 64 | 256 | 16xlarge | |
| 24xlarge | 96 | 384 | 32xlarge (nearest match) | |
