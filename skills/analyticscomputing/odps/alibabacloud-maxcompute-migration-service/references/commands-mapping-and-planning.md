# MMS Commands — Mapping & Planning

MMS provides API capabilities through the MaxCompute OpenAPI (product code `MaxCompute`, version `2022-01-04`).  
CLI invocation format: `aliyun maxcompute <command> [params] --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}`

## Target Mapping (CLI)

When mapping an MMS **source database / source table** to a **MaxCompute target project, schema, and table name**, use the following commands (**you do not have to rely on the console alone**). The `db-id` / `table-id` must first be obtained from `list-mms-dbs`, `list-mms-tables`, or `get-mms-db`, `get-mms-table`.

### UpdateMmsDb — Update database-level mapping

```bash
aliyun maxcompute update-mms-db \
  --source-id <sourceId> \
  --db-id <dbId> \
  --dst-project-name <maxcomputeProject> \
  --dst-name <maxcomputeSchemaOrDstName> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

Parameter meanings are as defined by `aliyun maxcompute update-mms-db -h` (including optional fields such as `--status`).

### UpdateMmsTable — Update table-level mapping

```bash
aliyun maxcompute update-mms-table \
  --source-id <sourceId> \
  --table-id <tableId> \
  --dst-project-name <maxcomputeProject> \
  --dst-schema-name <maxcomputeSchema> \
  --dst-name <maxcomputeTableName> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

Optional fields are as defined by `aliyun maxcompute update-mms-table -h`.

> **Report back after execution (mandatory)**: After completing `update-mms-db` / `update-mms-table`, you must print to the user the "before / after" values of the **db schema name** (from the actual MMS read results before and after the update — do not guess). At the database level this usually corresponds to `dst_name`; at the table level, display the schema-related fields in the response. Print the before and after values even if they are unchanged or `null`.

## Migration Planning (Aligned with SKILL Step 4)

- **The planning output retains only two items**: `(1) the job partitioning plan` and `(2) whether incremental migration is needed`.
- **Mapping decisions belong to the planning phase**: read the current mapping first, then decide. When the user has not specified target mapping fields, keep the current/default values and do not call the update API to rewrite identical values; when the user has specified target mapping fields, first perform a consistency comparison and only execute `update-mms-db` / `update-mms-table` when there is a mismatch. If already consistent, explicitly report back "mapping is already consistent; no update was performed this time".
- **Check status during planning**: when deciding on a plan and determining "how far the migration has progressed", rely on the **migration status of tables / partitions on the metadata side**: use **`list-mms-tables` / `get-mms-table`** and **`list-mms-partitions` / `get-mms-partition`**, reading the returned fields (such as `status`, as defined by `-h`) in the order **database → table → partition**. **Do not** use only the job-level status from **`get-mms-job` / `list-mms-jobs`** as the sole basis. **`list-mms-tasks` / `get-mms-task`** are oriented toward **execution tasks** and are used for execution/troubleshooting drill-down; they are **not** the primary signal for the planning phase.
- **Status enumeration (planning perspective)**: **tables** commonly have `INIT`, `DOING`, `FAILED`, `DONE`, `PART_DONE`; **partitions** commonly have `INIT`, `DOING`, `FAILED`, `DONE` (the actual JSON is authoritative; casing/aliases may vary by version, as defined by `-h` and the samples).
- **Use counts for large-scale planning**: when the number of tables/partitions is extremely large, **do not enumerate everything by default**; prefer to output the **count for each status** (a histogram-style summary) to support planning and high-level progress — for example, for `list-mms-tables`, when supported, query with paging by status via **`--status`** and accumulate the counts (or read a total/count-type field in the response, if any); otherwise, bucket the unfiltered paged results by `status`. Apply the same approach to partitions within a single table or a narrowed scope using **`list-mms-partitions`**. When drill-down is needed, list the narrowed sets such as **FAILED / DOING**, or filter by the table names specified by the user.
- **Whole-database first**: MMS skips tables/partitions that have already been migrated and are **unchanged**; during the planning phase, the default recommendation is **`create-mms-job` for the whole database** (`--src-db-name`, without passing `--tables`), unless the user explicitly wants only a table/partition scope.
- **Daily increment**: ask the user whether **daily incremental** migration is needed after the initial migration. When needed, explain the main flow: **(1)** configure **scheduled metadata pulling** (e.g., daily) in the **data source console**, and **(2)** then configure **`create-mms-timer`** to trigger the **migration job** after the metadata refresh completes (commonly within the same database scope); identifying newly added/changed partitions depends on **metadata that has been refreshed on schedule**. CLI inventory-type tasks can be used for the initial migration/supplementary pulls, but **continuous increments** rely on "scheduled data source + migration timer" — do not just say "inventory first, then timer" while omitting the console scheduling configuration.
- **Check the data source scheduling configuration before creating a timer**: when planning determines that increments are needed, first call `get-mms-data-source --with-config true` to read the metadata scheduled-refresh time/frequency (fields are as defined by `-h` / the actual response). If it is not configured or the time window cannot be confirmed, first remind the user to complete the configuration in the console, then proceed with timer creation.
- **Metadata scheduling**: configure **scheduled metadata pulling** in the **MaxCompute console → Data Source** (this is not a subcommand of this CLI). If not configured, guide the user to open the web page to configure it, and have the user tell you the **planned time**.
- **Scheduled task timing**: the `--value` (and `--schedule-type`) of `create-mms-timer` should be scheduled to run **after the data source metadata scheduled refresh completes** (leave a buffer), using the real schedule provided by the user.
- **Execution order after confirmation**: after the user confirms adopting incremental migration, first create `create-mms-timer`, then ask whether `trigger-mms-timer` should be executed immediately. `create-mms-timer` likewise must not be executed until it has passed Step 4 planning confirmation.

Incremental-related CLI: for `create-mms-job`, see **`--increment`** (`aliyun maxcompute create-mms-job -h`); use `create-mms-timer` for daily scheduling (`create-mms-timer -h`), commonly within the same scope as the whole-database baseline.
