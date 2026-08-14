# Monitoring & Logs APIs

PolarDB-X performance monitoring and log query APIs.

---

## DescribeDBNodePerformance

Query performance data of instance nodes.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `key` | String | Metric names, comma-separated, up to 6. CN uses `Cpu_Usage,Mem_Usage`; DN uses `MySQL_MemCpuUsage` (one key returns both cpuusage and memusage) |
| `start-time` | String | Query start time, format `YYYY-MM-ddTHH:mmZ` (UTC). **Must not be a future time** |
| `end-time` | String | Query end time, format `YYYY-MM-ddTHH:mmZ` (UTC). Must be later than start-time and cannot exceed current UTC time |
| `db-node-ids` | String | Node names. CN supports multiple comma-separated values; DN only supports one node ID per call, query multiple DNs in batches |
| `character-type` | String | Node type: `polarx_cn` / `polarx_dn` / `polarx_cdc` / `polarx_gms` |
| `db-node-role` | String | Node role: `master` / `slave` (only valid for DN and GMS) |

### CLI example

```bash
aliyun polardbx describe-db-node-performance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --key Cpu_Usage,Mem_Usage \
  --start-time 2024-01-01T00:00Z \
  --end-time 2024-01-01T01:00Z \
  --db-node-ids pxc-i-******,pxc-i-****** \
  --character-type polarx_cn \
  --db-node-role master \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBNodePerformance`

### Common pitfalls

| Error | Cause | Fix |
|---|---|---|
| `InvalidStartTime.Malformed` | start-time/end-time used a future time, or the time format is not UTC | Use a time range before current UTC time, format `YYYY-MM-ddTHH:mmZ` |
| `InvalidDBNodeIds.Malformed` | Multiple comma-separated db-node-ids were passed for a DN node | Query one DN node ID per call; batch multiple DNs |
| `InvalidKey.Malformed` | DN node used CN metric names `Cpu_Usage`/`Mem_Usage` | DN nodes use `MySQL_MemCpuUsage` |

> In short: use UTC time for performance queries, CN can be batched while DN must be single-node, and CN/DN metric keys differ.

---

## DescribeSlowLogRecords

Query slow SQL details for PolarDB-X compute and storage nodes.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `start-time` | String | Query start time, format `YYYY-MM-ddTHH:mmZ` (UTC) |
| `end-time` | String | Query end time |
| `character-type` | String | Node type, e.g. `polarx_cn` (CN) / `polarx_dn` (DN) |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-node-ids` | String | Node IDs, comma-separated; required when querying DN |
| `page-size` | Integer | Page size, max 100, default 100 |
| `page` | Integer | Page number, default 1 |
| `db-name` | String | Database name |

### CLI example

```bash
aliyun polardbx describe-slow-log-records \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --start-time 2024-01-01T00:00Z \
  --end-time 2024-01-02T00:00Z \
  --character-type polarx_cn \
  --page-size 30 \
  --page 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeSlowLogRecords`

---

## DescribeBinaryLogList

Query the binlog log list. Download links are valid for 2 days.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Current instance name/ID |
| `start-time` | String | Query start time |
| `end-time` | String | Query end time |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page-number` | Integer | Page number, default 1 |
| `page-size` | Integer | Items per page, default 30 |
| `instance-name` | String | CDC instance name, default queries single-stream binlog |

### CLI example

```bash
aliyun polardbx describe-binary-log-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --start-time "2024-01-01 00:00:00" \
  --end-time "2024-01-02 00:00:00" \
  --page-number 1 \
  --page-size 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeBinaryLogList`
