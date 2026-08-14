# Data Evaluate & Engine Migration APIs

PolarDB-X SQL evaluation, evaluate-and-import task management, replication inspection, and engine migration APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; tasks are identified by `--slink-task-id`.

> **Security:** Source/target passwords are sensitive. NEVER echo or hardcode them; use placeholders.

---

## CreateSQLEvaluateTask

Create a SQL evaluation task (static analysis and risk assessment against a target).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance ID |
| `src-res-id` | String | Source RDS instance ID |
| `src-db` | String | Source database info |
| `src-user-name` | String | Source username |
| `src-password` | String | Source password (never echo) |
| `dst-res-id` | String | Target SQL ID |
| `dst-db` | String | Target instance ID |
| `dst-user-name` | String | Target username |
| `dst-password` | String | Target password (never echo) |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `slink-task-id` | String | Task ID |
| `slink-task-desc` | String | Task description |
| `src-res-type` | String | Source type: `RDS_MYSQL` / `POLARX1` / `POLARX2_STANDARD` etc. |

### CLI example

```bash
aliyun polardbx create-sql-evaluate-task \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --src-res-id rm-******** --src-db <db> --src-user-name <user> --src-password '<pwd>' \
  --dst-res-id <dst-id> --dst-db <db> --dst-user-name <user> --dst-password '<pwd>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateSQLEvaluateTask`

---

## DescribeEvaluateAndImportTask

Query a single evaluate-and-import task.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `slink-task-id` | String | Task ID |

### CLI example

```bash
aliyun polardbx describe-evaluate-and-import-task \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --slink-task-id etx-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeEvaluateAndImportTask`

---

## DescribeEvaluateAndImportTasks

Query the list of evaluate-and-import tasks.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page-number` / `page-size` | Integer | Pagination |

### CLI example

```bash
aliyun polardbx describe-evaluate-and-import-tasks \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --page-number 1 --page-size 30 \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeEvaluateAndImportTasks`

---

## DeleteEvaluateAndImportTask

Delete an evaluate-and-import task.

> **[MUST] Secondary confirmation required.** Confirm the task ID with the user before deleting.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `slink-task-id` | String | Task ID |

### CLI example

```bash
aliyun polardbx delete-evaluate-and-import-task \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --slink-task-id etx-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DeleteEvaluateAndImportTask`

---

## CreateRplInspectionTask

Create a replication-link health inspection task (during data migration).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `slink-task-id` | String | Migration task ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `src-user-name` / `src-password` | String | Source credentials (never echo) |
| `dst-res-id` / `dst-db` | String | Target instance / database |
| `dst-user-name` / `dst-password` | String | Target credentials (never echo) |

### CLI example

```bash
aliyun polardbx create-rpl-inspection-task \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --slink-task-id etx-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateRplInspectionTask`

---

## DescribeRplInspectionTask

Query the details of a replication inspection task.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `slink-task-id` | String | Task ID |
| `success-page-number` / `success-page-size` | Integer | Pagination of success records |
| `fail-page-number` / `fail-page-size` | Integer | Pagination of failure records |

### CLI example

```bash
aliyun polardbx describe-rpl-inspection-task \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --slink-task-id etx-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeRplInspectionTask`

---

## CloseEngineMigration

Close the database engine migration process of an instance.

> **[MUST] Secondary confirmation required.** Closing migration finalizes the engine switch. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance name |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `continue-enable-binlog` | String | Whether to keep binlog enabled |

### CLI example

```bash
aliyun polardbx close-engine-migration \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CloseEngineMigration`

---

## ModifyEngineMigration

Modify the configuration/parameters of an engine migration task.

> **[MUST] Secondary confirmation required.** Migration config changes affect the switch. Confirm with the user.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `source-db-instance-name` | String | Source instance name |
| `new-master-db-instance-name` | String | New master instance name after migration |
| `connection-strings` | String | Connection address pairs to swap (JSON) |
| `swap-connection-string` | String | Whether to auto-swap connection strings |

### CLI example

```bash
aliyun polardbx modify-engine-migration \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --source-db-instance-name pxc-source \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyEngineMigration`
