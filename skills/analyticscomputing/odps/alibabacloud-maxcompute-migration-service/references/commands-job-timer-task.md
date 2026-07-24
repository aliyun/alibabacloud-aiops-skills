# MMS Commands — Job, Timer, Task & Async

MMS provides API capabilities through the MaxCompute OpenAPI (product code `MaxCompute`, version `2022-01-04`).  
CLI invocation format: `aliyun maxcompute <command> [params] --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}`

## Migration Job Management

### CreateMmsJob — Create a migration job

> **CLI form**: `create-mms-job` / `create-mms-timer` do **not** use `--body` to pass JSON; fields are **flat subcommand parameters** (consistent with `aliyun maxcompute create-mms-job -h` and `create-mms-timer -h`). OpenAPI camelCase names generally map to CLI **kebab-case** (e.g. `srcDbName` → `--src-db-name`). Parameters such as `--column-mapping`, `--partition-filters`, and `--table-mapping` can be repeated when they are **key=value** mappings; refer to `-h` for the exact usage.
>
> **[Required] `--name`**: Every time you create a migration job or timer, the command line **must include** `**--name <job or timer display name>`** (matching the summary shown to the user). Agents/scripts are **forbidden** from omitting `--name`; if no name is provided, ask the user first before issuing the command.
>
> **Execution starts automatically after creation**; there is no need to manually call StartMmsJob.

#### Async tasks and the real `job_id`

The response body of `create-mms-job` is usually an **async task ID** (such as `asyncTaskId`, etc., **based on the actual JSON field**), **not** the final migration job's `job_id`.

1. Retrieve `async_task_id` (and `source_id`) from the response.
2. Poll: `get-mms-async-task --source-id <sourceId> --async-task-id <asyncTaskId>`, with a recommended interval of **2–10 seconds**; such async tasks generally finish quickly.
3. When the status reaches a **successful terminal state** (commonly `DONE`, based on the API enumeration), retrieve the **object ID** from the response body (commonly the field `objectId` or the equivalent field in the documentation), which is the `**job_id`**. If the terminal state is failure, parse the error message, and do **not** mistake the async task ID for the `job_id`.
4. **The job execution phase** may last a long time: after obtaining the `job_id`, **by default do not** keep polling until migration completes within an automated flow; hand the `job_id` and the query commands available to the user (`list-mms-jobs`, `get-mms-job`, etc.) over to the user. Only when the user explicitly asks you to check progress on their behalf should you query at a **low frequency and for a small number of times**.

> **Note**: `create-mms-timer` differs from `create-mms-job` in that it **returns synchronously** — it returns `timerId` (or an equivalent field, based on the actual JSON) directly in the response body, **will not** return `asyncTaskId`, and does not require polling `get-mms-async-task`.

#### Three creation modes (choose parameters based on requirements)

```bash
# Mode 1: Full-database migration (migrate all tables in the database)
aliyun maxcompute create-mms-job \
  --source-id <sourceId> \
  --name <job_name> \
  --src-db-name <src_db_name> \
  --enable-schema-migration true \
  --enable-data-migration true \
  --enable-verification true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}

# Mode 2: Specified-table migration (migrate only the given tables)
aliyun maxcompute create-mms-job \
  --source-id <sourceId> \
  --name <job_name> \
  --src-db-name <src_db_name> \
  --tables table_a table_b \
  --enable-schema-migration true \
  --enable-data-migration true \
  --enable-verification true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}

# Mode 3: Partition-level migration (table name → partition filter expression; quote the value as needed by the shell when it contains special characters)
aliyun maxcompute create-mms-job \
  --source-id <sourceId> \
  --name <job_name> \
  --src-db-name <src_db_name> \
  --tables table_a table_b \
  --partition-filters table_a=ds=20260101 table_b=pt=hangzhou \
  --enable-schema-migration true \
  --enable-data-migration true \
  --enable-verification true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

Parameter selection rules:

- When the user says "entire database / full database / all tables": do not pass `--tables` or `--partition-filters`
- When the user explicitly provides table names: pass `--tables`, do not pass `--partition-filters`
- When the user explicitly provides partition conditions: you must pass both `--tables` and `--partition-filters` (each table corresponds to one `table_name=partition_filter_expression`)

### ListMmsJobs — List migration jobs

```bash
aliyun maxcompute list-mms-jobs \
  --source-id <sourceId> \
  --name <name> \
  --src-db-name <srcDbName> \
  --src-table-name <srcTableName> \
  --status <status> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```


| Parameter    | Type    | Description          |
| ------------ | ------- | -------------------- |
| name         | string  | Filter by job name   |
| srcDbName    | string  | Filter by source database name |
| srcTableName | string  | Filter by source table name    |
| status       | string  | Filter by status     |
| stopped      | integer | Whether stopped      |
| timerId      | integer | Filter by timer ID   |


### GetMmsJob — Get migration job details

```bash
aliyun maxcompute get-mms-job \
  --source-id <sourceId> \
  --job-id <jobId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### StartMmsJob — Start/resume a migration job

```bash
aliyun maxcompute start-mms-job \
  --source-id <sourceId> \
  --job-id <jobId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

> Used only to resume a job that was stopped by StopMmsJob.

### StopMmsJob — Stop a migration job

```bash
aliyun maxcompute stop-mms-job \
  --source-id <sourceId> \
  --job-id <jobId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### RetryMmsJob — Retry a migration job

```bash
aliyun maxcompute retry-mms-job \
  --source-id <sourceId> \
  --job-id <jobId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

## Migration Task Management

### ListMmsTasks — List migration tasks

```bash
aliyun maxcompute list-mms-tasks \
  --source-id <sourceId> \
  --job-id <jobId> \
  --status <status> \
  --src-table-name <srcTableName> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```


| Parameter    | Type    | Description         |
| ------------ | ------- | ------------------- |
| jobId        | integer | Filter by job ID    |
| jobName      | string  | Filter by job name  |
| srcDbName    | string  | Filter by source database name |
| srcTableName | string  | Filter by source table name    |
| status       | string  | Filter by status    |
| partition    | string  | Filter by partition |


### GetMmsTask — Get migration task details

```bash
aliyun maxcompute get-mms-task \
  --source-id <sourceId> \
  --task-id <taskId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### ListMmsTaskLogs — View migration task logs

```bash
aliyun maxcompute list-mms-task-logs \
  --source-id <sourceId> \
  --task-id <taskId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### Global execution status observation (every N minutes)

Used for the fixed workflow of "checking the overall migration status once every N minutes" (default `N=5`, user-configurable):

1. `list-mms-jobs`: filter for jobs currently executing (the status filter field is based on `-h`).
2. `list-mms-tasks`: filter for tasks currently executing (can be narrowed by job/db/table; the status filter is based on `-h`).
3. Output this round's results using the fixed template (consistent with `SKILL` Step 6): `Snapshot` → `Executing jobs` → `Executing tasks` → `Changes since last round` → `Risk notes` → `Next action`.
4. If this round has **running job=0 and running task=0**: output the final "observation complete" report and then stop polling.

## Timer Task Management (Timer)

### CreateMmsTimer — Create a timer task

Same as `create-mms-job`: **flat parameters**, no `--body`. See `aliyun maxcompute create-mms-timer -h` for the full list.

```bash
aliyun maxcompute create-mms-timer \
  --source-id <sourceId> \
  --name <timer_name> \
  --src-db-name <src_db_name> \
  --schedule-type Daily \
  --value 02:30 \
  --enable-schema-migration true \
  --enable-data-migration true \
  --enable-verification true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```


| CLI Parameter                               | Required | Description                              |
| ------------------------------------------- | -------- | ---------------------------------------- |
| `--name`                                    | Yes      | Timer task name                          |
| `--src-db-name`                             | Yes      | Source database name                     |
| `--schedule-type`                           | Yes      | Schedule type (e.g. `Daily` / `Hourly`, based on the `-h` enumeration) |
| `--value`                                   | Yes      | `HH:MM` for `Daily`; minute `MM` for `Hourly` |
| `--tables`                                  | No       | Multiple table names: `--tables t1 t2`   |
| `--partition-filters`                       | No       | `table_name=partition_filter_expression`, see `-h` for multiple groups |
| `--table-black-list` / `--table-white-list` | No       | Blacklist/whitelist tables for database-level timers |
| `--enable-schema-migration` etc.            | No       | Same meaning as for jobs                 |


### ListMmsTimers — List timer tasks

```bash
aliyun maxcompute list-mms-timers \
  --source-id <sourceId> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### GetMmsTimer — Get timer task details

```bash
aliyun maxcompute get-mms-timer \
  --source-id <sourceId> \
  --timer-id <timerId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### UpdateMmsTimer — Update a timer task

Supports only flat fields such as schedule-related ones, with **no** `--body`. See `aliyun maxcompute update-mms-timer -h`.

```bash
aliyun maxcompute update-mms-timer \
  --source-id <sourceId> \
  --timer-id <timerId> \
  --schedule-type Daily \
  --value 03:00 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### ListMmsTimerLogs — View timer task execution logs

```bash
aliyun maxcompute list-mms-timer-logs \
  --source-id <sourceId> \
  --timer-id <timerId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

## Async Tasks

### GetMmsAsyncTask — Check async task status

Used for the short polling after `**create-mms-job`** and similar commands return an `asyncTaskId`: until the status reaches a successful terminal state (such as `DONE`), then read `**objectId`** (or the object ID field agreed upon in the documentation) from the Body as the real `**job_id`**. Do not confuse this with a migration **Task** (table-level task).

> **Note**: `create-mms-timer` returns `timerId` synchronously and does not require the use of `get-mms-async-task`.

```bash
aliyun maxcompute get-mms-async-task \
  --source-id <sourceId> \
  --async-task-id <asyncTaskId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```
