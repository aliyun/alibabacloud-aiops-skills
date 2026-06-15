# Slow Query Analysis Scenarios

Follow this guide when users ask "Are there any slow queries?", "Why is the query slow?", "How do I optimize queries?", or "How do I enable slow logs?".

## Trigger Conditions

Typical user expressions:
- "Are there any slow query logs?"
- "How do I enable slow logs or slow query records?"
- "Queries are slow. Help me analyze the cause."
- "Top 10 slowest queries"
- "How do I optimize query performance?"

## Core Principles

**Evidence-driven diagnosis flow**:
1. **Collect the minimum necessary information first**, including engine type, time window, and operation type.
2. **Use monitoring to confirm the symptom**, especially latency metric trends.
3. **Ask the user to provide evidence**, such as slow SQL, execution plans, or slow logs.
4. **Provide targeted suggestions based on evidence**, rather than generic optimization lists.
5. **Provide executable optimization code**, extracted from official best practices.

> ⚠️ **Prohibited behavior**: Do not directly provide "five types of optimization solutions" or probabilistic judgments when specific slow SQL, execution plans, or slow log evidence is missing.

---

## Slow Query Log Management

> **Version requirements**:
> - Real-time slow query locating and termination: wide table engine **2.6.3+**, Lindorm SQL **2.6.6+**
> - Slow query backtracking, slow log records: wide table engine **2.8.2.13+**
>
> The following SQL statements are executed through a Lindorm SQL client, such as MySQL Workbench, DBeaver, Navicat, or ClusterManager. They **take effect immediately and do not require an instance restart**.

### 1. Locate Current Slow Queries in Real Time

```sql
-- View all currently running queries, including query ID / UUID.
SHOW PROCESSLIST;
```

**Description**: The `ID` field in the result is a UUID and is used for subsequent termination operations.

### 2. Terminate a Slow Query

```sql
-- Terminate a specified query. Obtain ID from SHOW PROCESSLIST.
KILL QUERY '581f9ab8-68af-4c93-b73a-eb99679ed192';
```

### 3. Enable Slow Query Backtracking, Slow Log Records

**Step 1: Enable the feature**
```sql
ALTER SYSTEM SET SLOW_QUERY_RECORD_ENABLE = true;
```

**Step 2: Set the slow query threshold, in milliseconds**
```sql
-- Example: record queries longer than 10 seconds. Adjust based on business requirements. Do not set it too low.
ALTER SYSTEM SET SLOW_QUERY_TIME_MS = 10000;
```

**Step 3: Query the slow log view**
```sql
-- View the latest 10 slow queries.
SELECT * FROM lindorm._slow_query_ LIMIT 10;

-- Filter by time. query_start_time is a Unix millisecond timestamp.
SELECT COUNT(sql_query_s) AS num
FROM lindorm._slow_query_
WHERE query_start_time >= 1680152319000;
```

**Slow log view field descriptions**:

| Field Name | Description |
|--------|------|
| `query_start_time` | Query request start time, Unix millisecond timestamp |
| `query_id` | Query request ID |
| `sql_query_id` | SQL statement of the query request. Empty if no SQL exists. |
| `sql_query_s` | SQL statement content. Empty if no SQL exists. |
| `duration_i` | Query execution time |
| `status_s` | Final query status, succeeded or failed |
| `ip_s` | IP address that sent the query request |
| `server_s` | Node that executed the query |
| `query_s` | Internal query request statement that was executed |

> ⚠️ **Notes**:
> - Slow log records are retained for only **1 hour** by default.
> - Frequent slow query recording has some impact on instance performance. In performance-sensitive scenarios, do not set the threshold too low.
> - The view name `lindorm._slow_query_` is fixed and cannot be modified.

**Official documentation**: https://help.aliyun.com/zh/lindorm/developer-reference/slow-query-diagnostics

---

## Execution Flow

### Step 0: Mandatory Minimum Information Collection (Ask Follow-up Questions If Missing, Do Not Conclude)

**Information that must be confirmed**:

| Information Item | Why It Is Required | Follow-up Wording |
|--------|-----------|---------|
| **Engine type** | Optimization strategies are completely different for wide table SQL, HBase API, time series, and search engines | "Which engine are you using? Wide table SQL, HBase API, time series engine, or search engine?" |
| **Time window** | Required to determine query trends and related events | "When did the slow query start approximately? How long has it lasted?" |
| **Slow operation type** | Troubleshooting directions differ for reads, writes, scans, and aggregations | "Is the query slow or the write slow? What is the specific operation type?" |
| **Specific SQL/operation**, if available | Without a specific statement, targeted advice cannot be provided | "Can you provide a specific slow SQL statement or operation code?" |

**Standard reply when parameters are missing**:
```text
I need some information first to diagnose this accurately:

1. Which engine are you using? Wide table SQL / HBase API / Time series / Search
2. When did the slow query start approximately?
3. Is it a slow read operation or slow write operation?
4. Can you provide a specific slow SQL statement or operation example?

With this information, I can help you:
- Query related monitoring metrics to confirm the issue
- Analyze the specific execution plan
- Provide targeted optimization suggestions
```

---

### Step 1: Use Monitoring to Confirm the Symptom (avg vs p99 + Trend)

**The Agent first queries latency metrics**:

```bash
# P99 latency, better for reflecting slow requests.
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name get_rt_p99 \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<start format: YYYY-MM-DD HH:MM:SS>" \
    --end-time "<end format: YYYY-MM-DD HH:MM:SS>" \
    --period 60

# Average latency.
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name read_rt \
    --dimensions '[{"instanceId":"<instance-id>"}]' \
    --start-time "<start format: YYYY-MM-DD HH:MM:SS>" \
    --end-time "<end format: YYYY-MM-DD HH:MM:SS>" \
    --period 60
```

**After analysis, the Agent gives an objective description**, without conclusions or probabilities:

```text
[Latency Metric Observation] Instance ld-xxx, last 1 hour

- Average latency: 35ms
- P99 latency: 180ms
- P99 to average ratio: 5.1x

[Objective Description]
The latency distribution has an obvious long tail, and some requests take significantly longer than the average.

[Next Step]
To determine the specific cause, slow query evidence is required. Choose one of the following methods:

Method 1, recommended: Provide specific slow SQL.
- If you know which SQL statement is slow, provide the SQL text.
- I can help analyze the execution plan.

Method 2: View ClusterManager slow query logs.
- Path: Console → Instance → ClusterManager → Query Analysis → Slow Query Logs
- After finding the top slow queries, tell me the query characteristics.

Method 3: Provide application-side observations.
- Are there specific errors or timeout operations in your application logs?
```

---

### Step 2: Ask the User to Provide Evidence (Any One Is Enough)

**Evidence types**, at least one required:

| Evidence Type | Applicable Scenario | How to Obtain |
|---------|---------|---------|
| **Slow SQL + EXPLAIN** | Wide table SQL slow query | User provides SQL text, and the Agent guides execution of EXPLAIN |
| **ClusterManager slow logs** | All engines | Console → ClusterManager → Query Analysis → Slow Query Logs |
| **HBase Scan/Get parameters** | HBase API slow query | User provides Scan/Get configuration in code |
| **Application error logs** | Scenario with explicit errors | Application-side timeout/error logs |

**Standard reply when evidence is not provided**:
```text
I can currently see that the latency distribution has a long tail, but I cannot determine the specific cause.

Please provide any one of the following pieces of evidence so I can provide targeted optimization suggestions:

Option A: A specific slow SQL statement, if you know which one
Option B: Top slow query screenshot or text from ClusterManager
Option C: Related error information from your application logs

⚠️ Note: Without specific evidence, I do not recommend directly applying generic optimization solutions,
because different causes, such as full table scan, hotspots, and large queries, may require completely different optimization directions.
```

---

### Step 3: Output Based on Evidence Classification (Only Provide 1 to 2 Matched Strategies)

**After receiving evidence, select the corresponding optimization direction based on evidence type**:

| Evidence Feature | Problem Type | Optimization Direction |
|---------|---------|----------|
| EXPLAIN shows TABLE FULL SCAN and a large number of scanned rows, greater than 1 million | Full table scan | Add RowKey range conditions or create a secondary index |
| Single-row query is slow and returns a large amount of data, greater than 1 MB | Querying too many columns | Only SELECT required columns and avoid `SELECT *` |
| A small number of RowKeys have extremely high latency and CPU node distribution is uneven | RowKey hotspot | Add salting or reversal to RowKey for distribution, or create a global index |
| Batch Get/Scan times out or runs out of memory | Large-volume batch query | Query in batches, batchSize 50 to 100, and use LIMIT pagination in SQL |
| Querying non-primary-key columns performs extremely poorly and slows linearly with data volume | Missing index | Create a secondary index by `CREATE INDEX` or a global index by `CREATE GLOBAL INDEX` |

> Based on the evidence provided by the user, **only output the matched 1 to 2 strategies** and provide corresponding executable SQL/code examples.

---

### Step 4: Tell the User How to Obtain Evidence (If the User Cannot Provide It)

**Give an exact path. Do not make the user explore by themselves**:

```text
[View Specific Slow Query Logs]

Although I have provided general optimization solutions, if you want to see **which specific query is the slowest**,
view it through ClusterManager:

Exact path:
1. Log on to the console: https://lindorm.console.aliyun.com/
2. Click instance ID "ld-xxx" to enter instance details.
3. Left-side menu: Database Connection → click "Access through ClusterManager".
4. Enter ClusterManager → Query Analysis → Slow Query Logs.
5. View:
   - Top 10 slowest queries
   - Query duration and scanned rows
   - Query occurrence time

[After Viewing Slow Queries]
Tell me the specific query type, such as Scan/Get/RowKey characteristics, and I will provide a targeted optimization solution.

ClusterManager documentation:
https://help.aliyun.com/zh/lindorm/user-guide/log-in-to-the-cluster-management-system
```

---

### Step 5: Comprehensive Performance Diagnosis (After Evidence Is Available)

**The Agent combines latency metrics + CPU/memory/QPS for comprehensive diagnosis**:

```bash
# Query CPU idle rate.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"<instance-id>"}]'

# Query memory usage percentage.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name mem_used_percent \
    --dimensions '[{"instanceId":"<instance-id>"}]'

# Query QPS.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name read_ops \
    --dimensions '[{"instanceId":"<instance-id>"}]'
```

**Comprehensive analysis example after evidence is available**:

```text
[Comprehensive Diagnosis] Instance ld-xxx, last 1 hour

Performance metrics:
- P99 latency: 180ms
- Average latency: 35ms
- P99/avg ratio: 5.1x
- CPU idle rate: 65%
- Memory usage: 55%

Evidence provided by the user:
- Engine type: Wide table SQL
- Slow SQL: SELECT * FROM orders WHERE status = 'pending'
- EXPLAIN shows: TABLE FULL SCAN

Diagnosis conclusion:
The slow query is caused by a full table scan. The orders table has no index on the status column,
so the query needs to scan the full table.

Targeted optimization solution:
1. Recommended: Create a secondary index:
   CREATE INDEX idx_status ON orders(status) INCLUDE (order_id, amount);

2. Temporary: Limit returned rows:
   SELECT * FROM orders WHERE status = 'pending' LIMIT 100;

3. Long term: If status has low selectivity, consider using a search index to support multi-condition queries.

After you confirm the optimization plan, I can provide the complete execution statements.
```

---

## Optimization Solution Reference

After the user provides specific evidence, the Agent extracts targeted optimization suggestions from the following official documents:

| Evidence Type | Reference Documentation | Extracted Content |
|---------|---------|---------|
| Full table scan | [SQL FAQ](https://help.aliyun.com/zh/lindorm/developer-reference/sql-faq) | Avoid low-efficiency queries, index usage, leftmost prefix matching principle |
| Hotspot issue | [How to design a wide table primary key](https://help.aliyun.com/zh/lindorm/user-guide/how-to-design-the-rowkey-field) | Salting, reversal, partitioning strategy, hotspot avoidance |
| Large query | [Cursor paging](https://help.aliyun.com/zh/lindorm/introduction-to-the-use-of-cursor-paging) | LIMIT pagination, cursor pagination, avoiding memory overflow |
| Index selection | [Secondary indexes](https://help.aliyun.com/zh/lindorm/user-guide/high-performance-native-secondary-indexes) | Secondary index vs search index selection |

> **Principle**: Extract only solutions that match the user's evidence. Do not provide all optimization solutions at once.

---

## Official Documentation Index for Agent Reference

| Scenario | Official Documentation | Expected Extracted Content |
|------|---------|-------------|
| **Slow query diagnosis** | [Slow query diagnostics](https://help.aliyun.com/zh/lindorm/developer-reference/slow-query-diagnostics) | Slow query locating methods, diagnostic tools, optimization suggestions |
| **Secondary index** | [Secondary indexes](https://help.aliyun.com/zh/lindorm/user-guide/high-performance-native-secondary-indexes) | Index types, creation syntax, use cases |
| **Global index** | [CREATE INDEX](https://help.aliyun.com/zh/lindorm/developer-reference/te-create-index) | GLOBAL keyword, index type differences, syntax parameters |
| **Primary key / RowKey design** | [How to design a wide table primary key](https://help.aliyun.com/zh/lindorm/user-guide/how-to-design-the-rowkey-field) | Salting, reversal, partitioning strategy, hotspot avoidance |
| **Index creation overview** | [CREATE INDEX comparison](https://help.aliyun.com/zh/lindorm/developer-reference/te-create-index) | Secondary index vs search index vs columnstore index selection |
| **ClusterManager** | [ClusterManager usage](https://help.aliyun.com/zh/lindorm/user-guide/log-in-to-the-cluster-management-system) | Access path, slow query log viewing |