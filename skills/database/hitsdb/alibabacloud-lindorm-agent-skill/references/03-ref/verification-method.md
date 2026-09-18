# Verification Methods

How to verify success after executing operations.

## Instance Query Verification

### Verify Successful Instance List Query

**Purpose**: Query the mixed V1/V2 instance list in a region specified by `--lindorm-region`.

```bash
aliyun lindorm instance list --lindorm-region cn-shanghai --output json
```

**Key returned fields**, in snake_case:
- The top level is an array, without an `InstanceList` or `Total` wrapper.
- Each item contains `instance_id`, `instance_name`, `status`, `arch`, `service_type`, `region_id`, `zone_id`, `network_type`, and `create_time`.
- It does not contain connection endpoints, engine node counts/specifications, or engine enablement flags.

**Success indicators**:
- The returned array is not empty and its `region_id` matches the requested region.

**Failure indicators**:
- `Forbidden.RAM`: insufficient permissions.
- `InvalidParameter`: invalid parameter.
- Instances from another region: `--region` was probably used and silently consumed by the parent aliyun CLI. Use `--lindorm-region`.

### Verify Successful Instance Detail Query

**Purpose**: Query configuration/version/status, including `service_type`, engine node count, and specifications. **Connection addresses are not included**.

```bash
aliyun lindorm v1 instance describe ld-xxx --lindorm-region cn-shanghai
```

**Key returned fields**, in snake_case:
- Instance information: `instance_id`, `status`, `service_type`, `arch_version`, `vpc_id`, `instance_storage`, and `disk_category`.
- `engines[]`: `engine`, `core_count` as the node count, `cpu_count`, `memory_size`, `specification`, and `latest_version`.
- Connection endpoints are not included. Run `aliyun lindorm v1 instance engine-list ld-xxx --lindorm-region cn-shanghai` when they are required.

**Success indicators**:
- `status=ACTIVATION` means the instance is running.

**Verification steps**:
1. Confirm that `instance_id` matches the request parameter.
2. Use `service_type` to identify V1, `lindorm`, or V2, `lindorm_v2`.
3. Check node counts and specifications in `engines`.

## Monitoring Query Verification

### Verify Successful Metric List Query

```bash
aliyun cms describe-metric-meta-list --namespace acs_lindorm
```

**Success indicators**:
- The returned JSON contains the `Resources` array.
- The array contains metric objects with fields such as `MetricName`, `Namespace`, and `Description`.

### Verify Successful Monitoring Data Query

```bash
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-xxx"}]'
```

**Success indicators**:
- The returned JSON contains the `Datapoints` field.
- `Datapoints` contains data points with fields such as `instanceId`, `timestamp`, and `Average`.
- `Code` is `200`, indicating success.

**Verification steps**:
1. Check that the `Datapoints` field is not empty.
2. Check that the `instanceId` in the data point is consistent with the request parameter.
3. Check that the value range of the `Average` field is reasonable, such as 0 to 100 for CPU idle rate.

## Storage Query Verification

### Verify Successful Storage Detail Query

```bash
# V1 instance
aliyun lindorm v1 instance storage ld-xxx --lindorm-region cn-shanghai

# V2 instance
aliyun lindorm v2 instance storage ld-xxx --lindorm-region cn-shanghai
```

**Success indicators**:
- V1 returns `fs_capacity`, `fs_used_hot`, and `disks[]`; byte values are encoded as strings.
- V2 returns `capacity_by_disk_category[]` in GB and `usage_by_disk_category[]` in bytes. Use `--output json`; table output cannot flatten these arrays.
- An architecture mismatch is not symmetric: `v1 instance storage` against V2 returns HTTP 200 with an empty body, while the reverse returns 451.

## IP Whitelist Verification

### Verify Successful Whitelist Query

```bash
aliyun lindorm v1 instance whitelist get ld-xxx --lindorm-region cn-shanghai
```

**Success indicators**:
- The JSON contains a `groups` array with `group_name` and `security_ip_list`.
- Whitelist entries are IP addresses or CIDR blocks.

## Connection Verification

### Verify Network Connectivity

Use telnet or nc to test port connectivity:

```bash
# Test MySQL protocol port, 33060.
telnet <lindorm-host> 33060

# Test HBase API port, 30020.
telnet <lindorm-host> 30020

# Test time series engine HTTP port, 8242.
curl --connect-timeout 10 -m 60 http://<lindorm-host>:8242/api/v2/status
```

**Success indicators**:
- telnet displays "Connected to xxx".
- curl returns a normal status response.

## Verification Checklist

After executing any operation, verify it according to the following checklist:

| Operation | Verification Command | Success Indicator |
|------|---------|---------|
| Query instance list | `aliyun lindorm instance list --lindorm-region <region>` | Non-empty array containing `instance_id`, `status`, `arch`, and `region_id` |
| Query configuration/status | `aliyun lindorm v1 instance describe <id>` | `engines[]` contains `core_count`, `specification`, and `latest_version`; connection endpoints are absent |
| Query connection endpoints | `aliyun lindorm v1 instance engine-list <id>` | Array contains `connection_string`, `port`, and `net_type` |
| Query storage details | `aliyun lindorm v1 instance storage <id>` | Storage capacity data is present |
| Query IP whitelist | `aliyun lindorm v1 instance whitelist get <id>` | `groups[]` contains whitelist rules |
| Query monitoring metrics | `aliyun cms describe-metric-meta-list` | `Resources` is not empty |
| Query monitoring data | `aliyun cms describe-metric-last` | `Datapoints` is not empty |
