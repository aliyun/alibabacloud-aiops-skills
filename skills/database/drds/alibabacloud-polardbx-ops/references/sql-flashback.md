# SQL Flashback APIs

PolarDB-X SQL flashback (row-level recovery) APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--polardbx-instance-id` (the PolarDB-X instance/cluster ID).

---

## DescribeSqlFlashbackTaskList

Query the list of SQL flashback tasks.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `polardbx-instance-id` | String | PolarDB-X instance ID |

### CLI example

```bash
aliyun polardbx describe-sql-flashback-task-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --polardbx-instance-id pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeSqlFlashbackTaskList`

---

## PreCheckSqlFlashbackTask

Pre-check feasibility before executing a SQL flashback recovery.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `polardbx-instance-id` | String | Cluster ID |
| `db-name` | String | Database name |
| `start-time` | String | Flashback start time |
| `end-time` | String | Flashback end time |

### CLI example

```bash
aliyun polardbx pre-check-sql-flashback-task \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --polardbx-instance-id pxc-******** \
  --db-name <database> \
  --start-time 2024-10-01T00:00:00Z \
  --end-time 2024-10-01T01:00:00Z \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:PreCheckSqlFlashbackTask`

---

## SubmitSqlFlashbackTask

Submit a SQL flashback task to recover data.

> **[MUST] Secondary confirmation required.** Flashback recovery generates and applies recovery SQL that alters data. Confirm the scope (database, table, time range, SQL type) with the user before submitting.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `polardbx-instance-id` | String | PolarDB-X instance ID |
| `db-name` | String | Database name |
| `start-time` | String | Flashback SQL start time |
| `end-time` | String | Flashback SQL end time |
| `recall-restore-type` | String | Recovery type |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `recall-type` | String | Exact or fuzzy match |
| `sql-type` | String | `INSERT` / `UPDATE` / `DELETE` |
| `table-name` | String | Target table name |
| `sql-pk` | String | Primary key of the flashback SQL |
| `trace-id` | String | Trace ID of the flashback SQL |

### CLI example

```bash
aliyun polardbx submit-sql-flashback-task \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --polardbx-instance-id pxc-******** \
  --db-name <database> \
  --start-time 2024-10-01T00:00:00Z \
  --end-time 2024-10-01T01:00:00Z \
  --recall-restore-type <type> \
  --sql-type DELETE \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:SubmitSqlFlashbackTask`
