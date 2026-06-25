# Manual Workflow: Step-by-Step Execution

> Only reference this document when `health-inspect.py` is unavailable. The recommended approach is the one-command script.

## Step 0: Auto-Discover Instance Region

> **Important**: If the user has not provided a Region, auto-discover the instance Region first.

```bash
python3 scripts/find-instance-region.py {DBClusterId}
```

## Step 1: Get Instance Basic Information

```bash
aliyun polardb describe-db-cluster-attribute \
  --region {RegionId} \
  --db-cluster-id {DBClusterId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection
```

**Key fields to extract:**
- `DBType` — Database type
- `DBVersion` — Database version
- `DBNodeClass` — Node specification
- `DBClusterStatus` — Cluster status
- `StorageType` — Storage type
- `StorageUsed` — Used storage space (in bytes)
- `StorageMax` — Maximum storage space
- `DBNodes` — Node list

Get node information to determine max connections (determined by node spec):
```bash
aliyun polardb describe-db-nodes \
  --region {RegionId} \
  --db-cluster-id {DBClusterId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection
```

## Step 1.5: Get Version Information

```bash
aliyun polardb describe-db-cluster-version \
  --region {RegionId} \
  --db-cluster-id {DBClusterId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection
```

**Return fields:**
- `DBVersion` — Major version (e.g., 8.0)
- `DBMinorVersion` — Minor version (e.g., 8.0.1)
- `DBRevisionVersion` — Kernel revision version (e.g., 8.0.1.1.54)
- `DBLatestVersion` — Latest available version (e.g., 8.0.1.1.54.1)
- `IsLatestVersion` — Whether it is the latest
- `ProxyRevisionVersion` — Proxy version
- `IsProxyLatestVersion` — Whether Proxy is the latest

## Step 2: Query Resource Usage (Last 24 Hours)

> **Time format note**: `describe-db-cluster-performance` / `describe-db-node-performance` use ISO 8601 format: `yyyy-MM-ddTHH:mmZ`

**Cluster-level monitoring metric keys (verified):**
- `PolarDBCPU` — CPU usage, returns `cpu_ratio` (%)
- `PolarDBMemory` — Memory usage, returns `mem_ratio` (%)
- `PolarDBDiskUsage` — Space usage, returns `mean_data_size` (MB, divide by StorageMax to calculate percentage)
- `PolarDBConnections` — Connection count, returns `mean_total_session`, `mean_active_session` (absolute values)
- `PolarDBInnoDBDataReadWrite` — IO throughput, returns `mean_innodb_data_read`, `mean_innodb_data_written` (KB/s)
- `PolarDBQPS` — QPS, returns `mean_qps`

**Node-level monitoring (must include `--region` parameter):**
- Use `describe-db-node-performance --db-node-id {NodeId} --region {RegionId}`
- Supported keys are the same as cluster-level: `PolarDBCPU`, `PolarDBMemory`, `PolarDBConnections`

```bash
# Cluster-level CPU
aliyun polardb describe-db-cluster-performance \
  --region {RegionId} \
  --db-cluster-id {DBClusterId} \
  --key "PolarDBCPU" \
  --start-time "{StartTime}" \
  --end-time "{EndTime}" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection

# Node-level CPU (query each node separately)
aliyun polardb describe-db-node-performance \
  --region {RegionId} \
  --db-node-id {NodeId} \
  --key "PolarDBCPU" \
  --start-time "{StartTime}" \
  --end-time "{EndTime}" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection
```

**Performance data parsing:**

The API returns `PerformanceKeys.PerformanceItem[]`, each Item contains:
- `MetricName` — Metric name (e.g., `cpu_ratio`, `mem_ratio`, `mean_total_session`)
- `Points.PerformanceItemValue[]` — Data point array
  - `Timestamp` — Timestamp
  - `Value` — Metric value (number in string format)

**Calculating average and peak:**
- Average = sum of all data point Values / number of data points
- Peak = maximum Value among all data points
- Connection usage = mean_total_session / MaxConnections x 100%
- Space usage = mean_data_size (MB) / StorageMax (converted to MB) x 100%

## Step 3: Space Usage Details TOP20 (DAS API)

### 3.1 Create Storage Analysis Task

```bash
aliyun das create-storage-analysis-task \
  --instance-id {DBClusterId} \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection
```

**Example response:**
```json
{
  "Code": 200,
  "Data": {
    "CreateTaskSuccess": true,
    "TaskId": "de28ea38-e992-4b1d-90b7-e9c2919df5f7"
  }
}
```

### 3.2 Wait for Task Completion and Get Results

```bash
aliyun das get-storage-analysis-result \
  --instance-id {DBClusterId} \
  --task-id {TaskId} \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection
```

**Extract TOP20 table space information:**
From `StorageAnalysisResult.TableStats`, sort by space size and take the top 20 entries, including:
- Database name
- Table name
- Total space (data + index)
- Data size
- Index size
- Fragmentation size
- Row count

## Step 4: Slow Log Statistics

```bash
aliyun polardb describe-slow-logs \
  --region {RegionId} \
  --db-cluster-id {DBClusterId} \
  --biz-region-id {RegionId} \
  --start-time "{StartDate}" \
  --end-time "{EndDate}" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardb-mysql-inspection
```

> **Time format**: `describe-slow-logs` uses date format `yyyy-MM-ddZ` (e.g., `2026-05-14Z`)
> **Required parameter**: `--biz-region-id` is mandatory, same value as `--region`

**Slow log statistics return fields:**
- `DBName` — Database name
- `SQLText` — Slow SQL text (summary)
- `TotalExecutionCounts` — Total execution count
- `TotalExecutionTimes` — Total execution time (seconds)
- `MaxExecutionTime` — Maximum execution time (seconds)
- `TotalLockTimes` — Total lock wait time (seconds)
- `MaxLockTime` — Maximum lock wait time
- `ParseTotalRowCounts` — Total rows scanned
- `ReturnTotalRowCounts` — Total rows returned
