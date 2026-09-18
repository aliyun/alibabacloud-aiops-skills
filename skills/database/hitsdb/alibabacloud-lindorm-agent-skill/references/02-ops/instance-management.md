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

- Pass the region with `--lindorm-region`, never `--region`. The parent `aliyun` CLI consumes `--region` silently. See SKILL.md → "Region Policy".
- **Default behavior**: If the user does not specify a region, query `--lindorm-region cn-shanghai` and explicitly state that the query covers the China East 2, Shanghai region.
- **Expanded query**: If the user asks for all regions, is unsure, or says the instance may be elsewhere, first run `aliyun lindorm summary` for navigation. It may under-report, so then query each region with `--lindorm-region`.
- Before responding, verify `region_id` in the output instead of assuming the parameter took effect.

**Execution commands**:

```bash
# List V1 and V2 instances in the specified region.
aliyun lindorm instance list --lindorm-region cn-shanghai --output json

# Search by a partial name or ID.
aliyun lindorm instance list --lindorm-region cn-shanghai --query <keyword>

# Query the all-region overview. This command is region-agnostic.
aliyun lindorm summary

# List all supported regions.
aliyun lindorm regions list
```

**Key fields**, returned in snake_case with `--output json`:

| Field | Meaning | Common Values |
|------|------|--------|
| instance_id | Instance ID | `ld-xxx` |
| instance_name | Instance alias | User-defined name, which may be empty |
| status | Instance status | `ACTIVATION`, running<br>`CREATING`, being created<br>`STOPPED`, stopped |
| arch | Architecture | `v1` / `v2`, suitable for direct command routing |
| service_type | Instance type | `lindorm` / `lindorm_v2` / ... |
| region_id | Region ID | `cn-shanghai` |
| zone_id | Zone ID | `cn-shanghai-e` |
| network_type | Network type | `vpc` |
| create_time | Creation time | `2026-07-22 10:29:57` |

> This command does not return billing type or engine enablement flags. Use Flow 2 or Flow 3 when those details are required.

---

### Flow 2: Query Instance Details

**Applicable scenario**: The user wants to understand the complete configuration information of an instance.

**Execution command**:

```bash
aliyun lindorm v1 instance describe <instance-id> --lindorm-region <region>
```

**Parameters**:
- The instance ID is a required positional argument. Do not use `--instance-id`.
- Specify the region with `--lindorm-region`; otherwise, the active profile region is used. The endpoint is resolved from the region, not automatically from the instance ID.
- For V2, run `aliyun lindorm v2 instance describe <instance-id> --lindorm-region <region>` to obtain node-group topology and `connect_address_list`.

**Key fields**, in snake_case:

| Category | Field | Meaning |
|------|------|------|
| **Basic** | instance_id / status / service_type / arch_version / create_time / expire_time | ID, status, type, architecture version, and creation/expiration times |
| **Network** | vpc_id / vswitch_id / network_type | VPC, VSwitch, and network type |
| **Storage** | instance_storage / disk_category / disk_threshold | Capacity in GB, disk type, and watermark threshold in percent |
| **Engines** | engines[]: engine / core_count / cpu_count / memory_size / specification / latest_version | Engine list and specifications |

---

### Flow 3: Query Instance Engine List

**Applicable scenario**: The user wants to know which engines are enabled for the instance, and the specification and version of each engine.

**Execution command**:

```bash
aliyun lindorm v1 instance engine-list <instance-id> --lindorm-region <region>
```

**Key fields**: The top level is an array flattened by engine and endpoint.

| Field | Meaning |
|------|------|
| engine_type | Engine type. See SKILL.md → "Engine Types". |
| connection_string | Connection domain name |
| port | Port |
| net_type | `VPC`, private / `PUBLIC`, public |
| net_type_code | `"2"` for VPC, `"0"` for public |
| access_type | Access type, distinguishing multiple protocol ports of the same engine |

> Engine specifications, node counts, and versions are not returned by this command. Use `instance describe` from Flow 2 and inspect `engines[]`. Engines without reachable endpoints, such as bds or compute, are still listed with empty endpoint fields.

---

### Flow 4: Query Storage Details

**Applicable scenario**: The user wants to understand storage usage and hot/cold tiering.

**Execution commands, selected by version**:

```bash
# V1 instance
aliyun lindorm v1 instance storage <instance-id> --lindorm-region <region>

# V2 instance
aliyun lindorm v2 instance storage <instance-id> --lindorm-region <region>
```

**Key field descriptions**:

**V1 instance**, `v1 instance storage`:

| Field | Meaning |
|------|------|
| fs_capacity | Total capacity, bytes encoded as a string |
| fs_capacity_hot / fs_capacity_cold | Hot/cold storage capacity in bytes |
| fs_used_hot / fs_used_cold | Used hot/cold storage in bytes |
| used_on_lindorm_table | Capacity used by the wide table engine |
| used_on_lindorm_table_data | Wide table data size |
| used_on_lindorm_table_wal | WAL size |
| disks[] | Details by disk type: disk_type / capacity / used / used_lindorm_* |

> V1 storage fields are byte values encoded as strings. Convert them to numbers before calculation.

**V2 instance**, `v2 instance storage`; `--output json` is required:

| Field | Meaning |
|------|------|
| usage_by_disk_category[] | Usage details grouped by disk type |
| └ diskType | `StandardCloudStorage` / `PerformanceCloudStorage` / `CapacityCloudStorage` |
| └ capacity | Capacity in bytes |
| └ used | Used capacity in bytes |
| └ usedLindormTable | Capacity used by the wide table engine |
| └ usedLindormTsdb | Capacity used by the time series engine |
| capacity_by_disk_category[] | Capacity information grouped by disk category |
| └ category | `STD_CLOUD_ESSD_PL0` / `PERF_CLOUD_ESSD_PL1` / `REMOTE_CAP_OSS`, and others |
| └ capacity | Capacity in GB |

> ⚠️ The top-level keys are snake_case, but keys inside the arrays remain camelCase because they are passed through from the API. Table output cannot flatten these arrays; use `--output json`.

---

## Scaling

> This section provides knowledge and solution selection only. For the complete workflow for issuing a configuration change, including dry-run preview, parameter constraints, UpgradeType inference, storage coupling, scale-in risk warnings, and known pitfalls, see **`instance-lifecycle.md`**.
>
> Configuration changes affect billing. Run `--dry-run` first and obtain explicit user confirmation before execution. The user may also perform the operation in the console.

### Scaling Method Comparison

| Bottleneck Type | Solution | Effective Time | Business Impact |
|---------|------|---------|---------|
| Insufficient storage | Storage scale-out, online | 5 to 10 minutes | No impact |
| Insufficient QPS | Increase node count, horizontal scaling | 10 to 20 minutes | No impact |
| High single-query latency | Upgrade node specification, vertical scaling | About 30 minutes, rolling restart | Recommended during off-peak hours |

Operation paths: use `aliyun lindorm v1|v2 instance modify` in the CLI, as described in `instance-lifecycle.md`, or go to Lindorm console → Instance Details → Change Configuration.

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
| Missing region | Default to `--lindorm-region cn-shanghai` and state the queried region. If the user asks for all regions, start with `aliyun lindorm summary`. |
| Missing instance ID | Run `aliyun lindorm instance list --lindorm-region <region>` and let the user select an instance. |

---

## Error Handling

| Error | Cause | Guidance |
|------|------|------|
| Instance does not exist | Incorrect ID or released instance | Confirm the ID with `aliyun lindorm instance list --lindorm-region <region>` |
| Region mismatch | The instance is in another region | Pass the correct `--lindorm-region`. Misusing `--region` silently queries the wrong region instead of failing. |
| Insufficient permissions | The AccessKey lacks Lindorm permissions | `AliyunLindormReadOnlyAccess` is required |

---

## Related Scenarios

- **Instance write operations**, including create, modify, release, and billing conversion → `instance-lifecycle.md`
- Whitelist / security group → `network-access-control.md`
- CLI quick reference, region rules, and return structures → `../03-ref/related-commands.md`
- Performance analysis before scaling → `monitoring-guide.md`
- Storage usage details → `storage-analysis.md`
- Monitoring after scaling → `monitoring-guide.md`
