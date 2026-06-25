# KVStore Health Inspection Manual Workflow

This document describes how to perform Redis instance health inspections manually using the Aliyun CLI, when the automated script `health-inspect.py` is unavailable or cannot be used.

## Prerequisites

- Aliyun CLI installed and configured (version >= 3.0.0)
- Valid AccessKey ID and Secret configured
- Appropriate RAM permissions (see [RAM Policies](ram-policies.md))
- All `aliyun` CLI commands MUST use the **plugin (kebab-case) form**, e.g. `describe-instance-attribute`, **NEVER** the deprecated PascalCase form `DescribeInstanceAttribute`.

## Observability (SA-2.11) — required for every command below

Generate a session ID once, then pass `--user-agent` on **every** `aliyun` invocation. Do NOT use the deprecated `aliyun configure ai-mode` mechanism or the `ALIBABA_CLOUD_USER_AGENT` environment variable.

```bash
# Step 1 — generate a session ID (32-char lowercase hex, no dashes)
export ALICLOUD_SKILL_SESSION_ID="$(uuidgen | tr -d '-' | tr 'A-F' 'a-f')"

# Step 2 — build the full UA (must include the /{session-id} segment)
export UA="AlibabaCloud-Agent-Skills/alibabacloud-kvstore-health-inspection/${ALICLOUD_SKILL_SESSION_ID}"
```

Every command in the sections below assumes `${UA}` is exported and is passed via `--user-agent "${UA}"`.

## Inspection Workflow

### 1. Instance Basic Information

Get basic information about the Redis instance:

```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id <instance-id> \
  --user-agent "${UA}"
```

**Key fields to extract:**
- `InstanceId` - Instance identifier
- `InstanceName` - Instance name
- `InstanceClass` - Instance specification (e.g., redis.master.small.default)
- `InstanceType` - Instance type (Tair/Redis)
- `EngineVersion` - Redis engine version
- `ArchitectureType` - Architecture type (standard/cluster/readwrite)
- `Connections` - Maximum connections
- `Bandwidth` - Maximum bandwidth (MB/s)
- `Capacity` - Storage capacity (MB)
- `InstanceStatus` - Instance status
- `CreateTime` - Creation time

### 2. Resource Usage Metrics

Query historical monitoring data for resource usage:

```bash
aliyun r-kvstore describe-monitor-items \
  --instance-id <instance-id> \
  --user-agent "${UA}"
```

Then query specific metrics:

```bash
aliyun r-kvstore describe-history-monitor-values \
  --instance-id <instance-id> \
  --monitor-keys <metric-key> \
  --start-time <start-time> \
  --end-time <end-time> \
  --interval-for-history 01m \
  --user-agent "${UA}"
```

**Supported metrics:**
- `CpuUsage` - CPU usage (%)
- `MemoryUsage` - Memory usage (%)
- `ConnectionUsage` - Connection usage (%)
- `IntranetInRatio` - Input bandwidth usage (%)
- `IntranetOutRatio` - Output bandwidth usage (%)
- `proxy_CpuUsage` - Proxy CPU usage (%) (cluster/readwrite only)
- `proxy_ConnectionUsage` - Proxy connection usage (%) (cluster/readwrite only)
- `proxy_MemoryUsage` - Proxy memory usage (%) (cluster/readwrite only)
- `proxy_IntranetIn` - Proxy input traffic (KB/s) (cluster/readwrite only)
- `proxy_IntranetOut` - Proxy output traffic (KB/s) (cluster/readwrite only)
- `pmem_usage` - Persistent memory usage (%) (tair_pena only)
- `disk_usage` - Disk usage (%) (tair_essd only)

**Time range:** Default is last 7 days. Use ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`

### 3. Session Information

#### 3.1 Connection Usage

From the resource metrics above, extract `ConnectionUsage` data.

#### 3.2 Real-time Sessions (DAS API)

```bash
aliyun das get-redis-all-session \
  --instance-id <instance-id> \
  --region cn-shanghai \
  --user-agent "${UA}"
```

**Key information:**
- Total active sessions
- Source IP statistics (client IP distribution)
- Session details (top 50 by idle time)

### 4. Big Key and Hot Key Analysis

```bash
aliyun das describe-hot-big-keys \
  --instance-id <instance-id> \
  --region cn-shanghai \
  --user-agent "${UA}"
```

**Output categories:**
- **Large Keys** (by memory size) - Top 10
- **Big Keys** (by element count) - Top 10
- **Hot Keys** (by QPS) - Top 10
- **High Traffic Keys** (by bandwidth) - Top 10

### 5. Slow Log Analysis

Query slow log records:

```bash
aliyun r-kvstore describe-slow-log-records \
  --instance-id <instance-id> \
  --start-time <start-time> \
  --end-time <end-time> \
  --user-agent "${UA}"
```

**Key information:**
- Command name
- Execution count
- Total elapsed time (ms)
- Average elapsed time (ms)
- Maximum elapsed time (ms)
- Sample key

### 6. Alert History and Rules

#### 6.1 Alert Rules

```bash
aliyun cms describe-metric-rule-list \
  --namespace acs_kvstore \
  --page-size 100 \
  --page-number 1 \
  --user-agent "${UA}"
```

#### 6.2 Alert History

```bash
aliyun cms describe-alert-log-list \
  --product "kvstore" \
  --start-time <start-timestamp> \
  --end-time <end-timestamp> \
  --page-size 100 \
  --page-number 1 \
  --user-agent "${UA}"
```

**Note:** Start and end times are Unix timestamps in milliseconds.

### 7. Architecture-Specific Checks

#### 7.1 Cluster Architecture

For cluster instances, query topology:

```bash
aliyun r-kvstore describe-logic-instance-topology \
  --instance-id <instance-id> \
  --user-agent "${UA}"
```

Then query metrics for each node individually using the node IDs from the topology.

#### 7.2 Read-Write Splitting Architecture

Similar to cluster, query topology to identify read-only nodes and proxy nodes, then query their respective metrics.

#### 7.3 Tair Instance Types

- **Tair PENA** (persistent memory): Check `pmem_usage` metric
- **Tair ESSD** (disk): Check `disk_usage` metric

## Data Analysis and Suggestions

### Resource Thresholds

| Metric | Warning | Danger |
|--------|---------|--------|
| CPU Usage (peak) | > 60% | > 80% |
| Memory Usage (peak) | > 80% | > 95% |
| Connection Usage (peak) | > 60% | > 80% |
| Bandwidth Usage (peak) | > 60% | > 80% |

### Cross-Dimensional Correlation

When analyzing the data, look for these patterns:

1. **High CPU + Hot Keys**: CPU peaks often correlate with hot key access patterns
2. **High Memory + Large Keys**: Memory pressure with large keys indicates need for key optimization
3. **High Connections + Slow Logs**: Connection accumulation may be caused by slow commands
4. **High Bandwidth + Big Keys**: Bandwidth spikes often correlate with large key transfers

### Example Analysis

```
Instance: r-bp1xxxxxxxxxxxxx
Region: cn-hangzhou
Architecture: cluster

Findings:
1. CPU peak 85% (danger) - correlated with 5 hot keys (QPS > 1000)
   Suggestion: Optimize hot key access patterns, consider read replicas
   
2. Memory peak 92% (warning) - 3 large keys (> 10MB each)
   Suggestion: Review large key usage, consider key splitting or expiration
   
3. Connection peak 75% (warning)
   Suggestion: Monitor trend, review connection pooling strategy
```

## Output Format

The manual inspection should produce a report similar to the automated script output, including:
- Instance basic information
- Resource usage summary table
- Session information
- Big/Hot key analysis
- Slow log analysis
- Alert history
- Suggestions based on the analysis

For detailed output format specifications, see [report-format.md](report-format.md).
