# Troubleshooting Guide

> Related: [SKILL.md](../SKILL.md), [ram-policies.md](ram-policies.md), [mcp-tools-reference.md](mcp-tools-reference.md)

Detailed error identification and recovery procedures for ODPS Information Schema queries.

## T1: "Table not found" on IS Views

**Error signal:**
```
SemanticAnalysException: Table not found: SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES
```

**Root cause:** Missing `odps.namespace.schema=true` flag. Without it, MaxCompute cannot resolve the cross-project `SYSTEM_CATALOG` reference.

**Fix — MCP:**
```python
execute_sql(
  sql="SELECT ... FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES ...",
  hints={"odps.namespace.schema": "true"}
)
```

**Fix — odpscmd:**
```sql
SET odps.namespace.schema=true;
SELECT ... FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES ...;
```

**Verification:** Run [Q30 smoke test](verified-queries.md#q30-namespace-flag-verification):
```sql
SET odps.namespace.schema=true;
SELECT COUNT(*) AS table_count FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES LIMIT 1;
```
If this returns a count, the flag is working.

---

## T2: "Access denied" / "Permission denied" on IS Views

**Error signal:**
```
ODPS-0130131: Authorization failed -- user XXX does not have SELECT privilege on table SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES
```

**Root cause:** Current user lacks tenant-level IS access role. Only Alibaba Cloud primary account has access by default; RAM sub-accounts need explicit role assignment.

**Fix:** See [ram-policies.md](ram-policies.md) for the complete Policy template and authorization steps. Summary:

1. Log in to MaxCompute Console → **管理配置 > 租户管理**
2. Create role with `odps:Describe` + `odps:Select` on `information_schema/tables/*` and `odps:List` on `information_schema`
3. Assign user to the role

---

## T3: TASKS_HISTORY Query Slow or Expensive

**Error signal:** Query takes >60s, or `cost_sql` returns high CU estimate.

**Root cause:** Missing `ds` partition filter. TASKS_HISTORY is partitioned by `ds` (date string `YYYYMMDD`). Without it, the engine scans all 14 days of data.

**Fix:** Always add a `ds` filter:
```sql
WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -14, 'dd'), 'yyyymmdd')
```

**Pre-check:** Use `cost_sql` before executing (supports IS views, verified 2026-04):
```python
cost_sql(
  sql="SELECT ... FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY WHERE ds >= '20260401' ...",
  hints={"odps.namespace.schema": "true"}
)
```

---

## T4: MCP Returns Exactly 1000 Rows

**Error signal:** `execute_sql` returns `rowCount: 1000` — this indicates sync mode truncation.

**Root cause:** MCP sync mode (`async=false`) has a 1000-row limit. The actual result may be larger.

**Fix — Option A (recommended):** Re-run with async mode:
```python
instance_id = execute_sql(sql=..., hints={"odps.namespace.schema": "true"}, async=True)
# Poll until complete
get_instance_status(instance_id)
# Retrieve full results
get_instance(instance_id)
```

**Fix — Option B:** Add tighter WHERE/LIMIT:
```sql
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
LIMIT 500
```

---

## T5: "Column not found" Error

**Error signal:**
```
SemanticAnalysException: Column not found: size_bytes
```

**Root cause:** Used a non-existent column name. Common mistakes documented in [SKILL.md Critical Column Reference](../SKILL.md#column-reference).

**Most common wrong columns and their correct replacements:**

| Wrong Column | Correct Column | Context |
|---|---|---|
| `size_bytes` | `data_length` | TABLES table size |
| `task_status` | `status` | TASKS_HISTORY |
| `task_owner` | `owner_name` | TASKS_HISTORY submitter |
| `task_id` | `inst_id` | TASKS_HISTORY instance |
| `error_message` | `result` | TASKS_HISTORY error info |
| `duration_ms` | `DATEDIFF(end_time, start_time, 'ss')` | Computed duration |
| `scan_bytes` / `processed_bytes` | `input_bytes` | TASKS_HISTORY input size |
| `grantee` | `user_name` / `user_id` | TABLE_PRIVILEGES |
| `comment` | `table_comment` / `column_comment` | TABLES/COLUMNS |
| `project_name` | `task_catalog` / `table_catalog` | TASKS_HISTORY/TABLES |

**Fix:** Replace the wrong column with the correct one from the table above.

---

## T6: Async Query Timeout (>30s)

**Error signal:** Sync mode returns `instanceId` instead of results (timeout exceeded).

**Root cause:** Query involves large scan (e.g., TASKS_HISTORY with wide `ds` range, multi-table JOIN).

**Fix:**
1. **Pre-check with `cost_sql`:** Estimate CU before running
2. **Add `ds` filter:** Narrow the date range
3. **Use async mode explicitly:**
```python
instance_id = execute_sql(sql=..., async=True, hints={"odps.namespace.schema": "true"})
# Poll with get_instance_status
# Retrieve with get_instance (no row limit in async)
```
4. **Split the query:** Break a 14-day scan into two 7-day queries

---

## T7: IS View Shows No Recent Data

**Error signal:** Query returns 0 rows for today's data.

**Root cause:** IS views have inherent delays:
- **History views** (TASKS_HISTORY, TUNNELS_HISTORY): ~5 min delay
- **Realtime views** (TABLES, COLUMNS, etc.): ~3 hours delay
- **TASKS (live snapshot):** Seconds delay (Preview feature)

**Fix:**
- For yesterday's data: query after 06:00 to ensure completeness
- For today's data: expect ~5 min latency for history, ~3 hours for realtime
- Use `TASKS` (not TASKS_HISTORY) for live monitoring of running jobs
