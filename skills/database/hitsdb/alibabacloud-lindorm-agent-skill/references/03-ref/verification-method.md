# Verification Methods

How to verify success after executing operations.

## Instance Query Verification

### Verify Successful Instance List Query

**Purpose**: Query the instance list, including IDs, status, engine switches, and support for filtering by region/type.

```bash
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai
```

**Key returned fields**:
- `InstanceList[]`: InstanceId, InstanceAlias, InstanceStatus, ServiceType
- `Enable*` engine switches: EnableLts, EnableStream, EnableCompute, EnableVector, and others
- Does not include connection addresses or engine node counts/specifications

**Success indicators**:
- The `InstanceList` array is not empty.

**Failure indicators**:
- `Forbidden.RAM`: Insufficient permissions
- `InvalidParameter`: Parameter error

### Verify Successful Instance Detail Query

**Purpose**: Query configuration/version/status, including ServiceType, engine node count, and specifications. **Connection addresses are not included**.

```bash
aliyun hitsdb get-lindorm-instance --instance-id ld-xxx
```

**Key returned fields**:
- Instance information: InstanceId, InstanceStatus, ServiceType, VpcId, DiskUsage
- `EngineList[]`: Engine, CoreCount, node count, CpuCount, MemorySize, Specification, Version
- Does not include connection addresses. Use `get-lindorm-instance-engine-list` when connection addresses are required.

**Success indicators**:
- `InstanceStatus` is `ACTIVATION`, indicating the instance is running.

**Verification steps**:
1. Check that `InstanceId` is consistent with the request parameter.
2. Check `ServiceType` to determine V1, `lindorm`, or V2, `lindorm_v2`.
3. Check the node count and specification in the `EngineList` engine list.

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
# V1 instance.
aliyun hitsdb get-lindorm-fs-used-detail --instance-id ld-xxx

# V2 instance.
aliyun hitsdb get-lindorm-v2-storage-usage --instance-id ld-xxx
```

**Success indicators**:
- The returned JSON contains storage-capacity-related fields.
- Numeric values are in bytes.

## IP Whitelist Verification

### Verify Successful Whitelist Query

```bash
aliyun hitsdb get-instance-ip-white-list --instance-id ld-xxx
```

**Success indicators**:
- The returned JSON contains the `GroupList` array.
- The array contains IP addresses or whitelist rules in CIDR format.

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
| Query instance list | `aliyun hitsdb get-lindorm-instance-list` | `InstanceList` array is not empty and contains InstanceId/Status/Enable* |
| Query configuration/status | `aliyun hitsdb get-lindorm-instance` | `EngineList` contains CoreCount/Specification/Version, excluding connection addresses |
| Query connection addresses | `aliyun hitsdb get-lindorm-instance-engine-list` | `NetInfoList` contains ConnectionString/Port/NetType |
| Query storage details | `aliyun hitsdb get-lindorm-fs-used-detail` | Contains storage capacity data |
| Query IP whitelist | `aliyun hitsdb get-instance-ip-white-list` | Contains whitelist rules |
| Query monitoring metrics | `aliyun cms describe-metric-meta-list` | `Resources` array is not empty |
| Query monitoring data | `aliyun cms describe-metric-last` | `Datapoints` field is not empty |