# Instance Management Scenarios

Covers instance queries, including lists, details, engines, and storage, and provides scaling knowledge guidance.

## Trigger Conditions

- "Which Lindorm instances do I have?"
- "List all instances in cn-shanghai."
- "What configuration does instance ld-xxx use?"
- "Which engines are enabled for this instance?"
- "How much disk space is left?"
- "Instance storage is almost full. How do I scale it out?"
- "I need more configuration. How do I operate it?"

---

## Query Flows

### Flow 1: List All Instances

**Applicable scenario**: The user wants to view all instances in a region, or does not know the specific instance ID.

**Region strategy**:

- **Default behavior**: If the user does not specify a region, query `cn-shanghai`, East China 2 Shanghai, by default, and **must explicitly state** that "this query is for the Shanghai region".
- **Extended query**: If the user says "all regions", "not sure", or "maybe in another region", first run `get-instance-summary` to obtain a cross-region overview, and then query regions as needed.

**Execution commands**:

```bash
# Query the instance list in a specified region. --region is required.
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai

# Query a cross-region instance overview. --region is not required.
aliyun hitsdb get-instance-summary

# Query all regions.
aliyun hitsdb describe-regions
```

**Key field descriptions**:

| Field | Meaning | Common Values |
|------|------|--------|
| InstanceId | Instance ID | `ld-xxx` |
| InstanceAlias | Instance alias | User-defined name |
| InstanceStatus | Instance status | `ACTIVATION`, running<br>`CREATING`, creating<br>`STOPPED`, stopped |
| PayType | Billing type | `POSTPAY`, pay-as-you-go<br>`PREPAY`, subscription |
| RegionId | Region ID | `cn-shanghai` |
| ZoneId | Zone ID | `cn-shanghai-e` |
| NetworkType | Network type | `vpc` |

---

### Flow 2: Query Instance Details

**Applicable scenario**: The user wants to understand the complete configuration information of an instance.

**Execution command**:

```bash
aliyun hitsdb get-lindorm-instance --instance-id <instance-id>
```

**Parameter descriptions**:
- `--instance-id`: Instance ID, required.
- `--region`: Region ID, optional. It is automatically located based on instance-id.

**Key field descriptions**:

| Category | Field | Meaning |
|------|------|------|
| **Basic** | InstanceId / InstanceAlias / InstanceStatus / CreateTime / ExpireTime | Instance ID, alias, status, creation time, expiration time |
| **Network** | VpcId / VswitchId / NetworkType | VPC, vSwitch, network type |
| **Storage** | InstanceStorage / DiskCategory / DiskUsage / ColdStorage | Storage capacity in GB, disk type, usage percentage, cold storage capacity |
| **Engines** | EngineList / EnableLTS / EnableSearch | Engine list, time series and search switches |

---

### Flow 3: Query Instance Engine List

**Applicable scenario**: The user wants to know which engines are enabled for the instance, and the specification and version of each engine.

**Execution command**:

```bash
aliyun hitsdb get-lindorm-instance-engine-list --instance-id <instance-id>
```

**Key field descriptions**:

| Field | Meaning |
|------|------|
| EngineType | Engine type. For details, see SKILL.md → "Engine types". |
| Version | Current version |
| LatestVersion | Latest upgradable version |
| CpuCount | Number of CPU cores |
| MemorySize | Memory size in GB |
| CoreCount | Number of nodes |

---

### Flow 4: Query Storage Details

**Applicable scenario**: The user wants to understand storage usage and hot/cold tiering.

**Execution commands, selected by version**:

```bash
# V1 instance.
aliyun hitsdb get-lindorm-fs-used-detail --instance-id <instance-id>

# V2 instance.
aliyun hitsdb get-lindorm-v2-storage-usage --instance-id <instance-id>
```

**Key field descriptions**:

**V1 instance** (`get-lindorm-fs-used-detail`):

| Field | Meaning |
|------|------|
| FsCapacity | Total file engine capacity, in bytes |
| FsCapacityHot / FsCapacityCold | Hot/cold storage capacity, in bytes |
| FsUsedHot / FsUsedCold | Used hot/cold storage, in bytes |
| FsUsedOnLindormTable | Used by Lindorm wide table |
| FsUsedOnLindormTableData | Wide table data size |
| FsUsedOnLindormTableWAL | WAL log size |

**V2 instance** (`get-lindorm-v2-storage-usage`):

| Field | Meaning |
|------|------|
| UsageByDiskCategory[] | Usage detail array by disk type |
| └ diskType | Disk type, such as `PerformanceCloudStorage` or `CapacityCloudStorage` |
| └ capacity | Capacity, in bytes |
| └ used | Used capacity, in bytes |
| └ usedLindormTable | Used by wide table |
| └ usedLindormTsdb | Used by time series |
| CapacityByDiskCategory[] | Capacity information array by disk category |
| └ category | Category, such as `PERF_CLOUD_ESSD_PL1` or `REMOTE_CAP_OSS` |
| └ capacity | Capacity, in GB |

---

## Scaling Knowledge

**⚠️ This read-only Skill does not execute scaling change commands.** The following is knowledge guidance and directs users to operate in the console.

### Scaling Method Comparison

| Bottleneck Type | Solution | Effective Time | Business Impact |
|---------|------|---------|---------|
| Insufficient storage | Storage scale-out, online | 5 to 10 minutes | No impact |
| Insufficient QPS | Increase node count, horizontal scaling | 10 to 20 minutes | No impact |
| High single-query latency | Upgrade node specification, vertical scaling | About 30 minutes, rolling restart | Recommended during off-peak hours |

Operation path: Lindorm console → Instance details → Change Configuration

### Scaling Constraints

- Scale-in requires used space to be less than the target capacity.
- Configuration can be changed at most 3 times within 24 hours, with at least 1 hour between two changes.
- If scale-out fails because of insufficient inventory, change the zone or specification.

### Official Documentation

- Manage storage space: https://help.aliyun.com/zh/lindorm/user-guide/manage-storage-space/
- Change capacity cloud storage capacity: https://help.aliyun.com/zh/lindorm/user-guide/expand-cold-storage
- Billing mode description: https://help.aliyun.com/zh/lindorm/product-overview/billing

---

## Missing Parameter Handling

| Missing Parameter | Strategy |
|------|------|
| Missing region | Query `cn-shanghai` by default and proactively state the query region. If the user says "all regions", first use `get-instance-summary`. |
| Missing instance-id | List instances first and let the user select one. |

---

## Error Handling

| Error | Cause | Guidance |
|------|------|------|
| Instance does not exist | Instance ID is incorrect or the instance has been released | Use `get-lindorm-instance-list` to confirm the instance ID |
| Region mismatch | Instance is in another region | Prompt the user to specify the correct region |
| Insufficient permissions | AK has no Lindorm permission | `AliyunLindormReadOnlyAccess` permission is required |

---

## Related Scenarios

- Performance analysis before scale-out → `monitoring-guide.md`
- Storage usage details → `storage-analysis.md`
- Monitoring settings after scale-out → `monitoring-guide.md`