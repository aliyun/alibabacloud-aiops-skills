# Cluster Information Query

> **🚨🚨🚨 MUST | P0 | NON-NEGOTIABLE — Execution Checklist 🚨🚨🚨**
>
> When the user asks about cluster information, **the following checks must be executed**:
>
> - [ ] **MUST**: Execute the corresponding `aliyun adb describe-db-clusters` or `describe-db-cluster-attribute` command based on user needs
> - [ ] **MUST**: Output the command string on the **first line** of the response, format: `Command executed: aliyun adb <command-name> --biz-region-id <region-id>`
> - [ ] **NON-NEGOTIABLE**: Do not skip API call and directly give advice
>
> **Violating any checklist item = task failure**

When the user wants to know "what instances exist", "what is the instance configuration", "cluster status", etc., follow the steps below.

## 1. Query Cluster List

**Response Format Template** (must be followed):
```
Command executed: `aliyun adb describe-db-clusters --biz-region-id <region-id> --region <region-id>`

[Query results, tables, etc.]
```

List all ADB MySQL clusters under the specified region:

```bash
aliyun adb describe-db-clusters --api-version 2021-12-01 --biz-region-id <region-id> --region <region-id>
```

## 2. Query Cluster Detailed Attributes

Get complete configuration information for a single cluster (specification, VPC, storage, version, etc.):

```bash
aliyun adb describe-db-cluster-attribute --api-version 2021-12-01 --biz-region-id <region-id> --region <region-id> --db-cluster-id <cluster-id>
```

**Key Fields in Response**:

| Field | Meaning |
|------|------|
| `DBClusterId` | Cluster ID |
| `DBClusterDescription` | Cluster description / alias |
| `DBClusterStatus` | Cluster status (Running, Stopped, etc.) |
| `DBClusterType` | Cluster type |
| `CommodityCode` | Billing method |
| `ComputeResource` | Compute resource specification |
| `StorageResource` | Storage resource specification |
| `DBVersion` | Kernel version |
| `VPCId` / `VSwitchId` | Network information |
| `ConnectionString` | Connection address |
| `Port` | Port |
| `CreationTime` | Creation time |
| `ExpireTime` | Expiration time (valid for subscription billing) |

## 3. Query Storage Space Overview

Understand the cluster's disk usage:

```bash
aliyun adb describe-db-cluster-space-summary --api-version 2021-12-01 --biz-region-id <region-id> --region <region-id> --db-cluster-id <cluster-id>
```

**Key Fields in Response**:

| Field | Meaning |
|------|------|
| `TotalSize` | Total data size (unit: bytes) |
| **HotData** | **Hot data information** |
| `HotData.TotalSize` | Hot data total size (bytes) |
| `HotData.DataSize` | Table record data size (bytes) |
| `HotData.IndexSize` | Regular index data size (bytes) |
| `HotData.PrimaryKeyIndexSize` | Primary key index data size (bytes) |
| `HotData.OtherSize` | Other data size (bytes) |
| **ColdData** | **Cold data information** |
| `ColdData.TotalSize` | Cold data total size (bytes) |
| `ColdData.DataSize` | Table record data size (bytes) |
| `ColdData.IndexSize` | Regular index data size (bytes) |
| `ColdData.PrimaryKeyIndexSize` | Primary key index data size (bytes) |
| `ColdData.OtherSize` | Other data size (bytes) |
| **DataGrowth** | **Data growth information** |
| `DataGrowth.DayGrowth` | Last day data growth amount (bytes) |
| `DataGrowth.WeekGrowth` | Last 7 days average daily data growth amount (bytes) |

> **Calculation Formula**:
> - Total data size = Hot data size + Cold data size
> - Hot data size = Table record data + Regular index + Primary key index + Other data
> - Last 7 days average daily growth = (Current data size - 7 days ago data size) / 7

## 4. Common Use Cases

- **User says "help me see what ADB instances exist"** → Execute step 1
- **User says "what is the configuration of instance amv-xxx"** → Execute step 2
- **User says "is this cluster about to expire"** → Execute step 2, check `ExpireTime`
- **User says "how much disk space is left"** → Execute step 3
- **User doesn't know cluster-id** → First execute step 1 to get the list, then select the target cluster for subsequent operations