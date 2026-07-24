# MMS: `source_id` resolution & name → ID rules

This reference expands the **bounded `source_id` discovery** and **metadata lookup** rules summarized in `SKILL.md`. Keep `SKILL.md` short; use this file for the full checklist.

## Name → ID resolution (MMS uses IDs)

| Resource | ID field | Typical resolution |
| --- | --- | --- |
| Data source | `source_id` | `list-mms-data-sources` (optionally `--name`) |
| Job | `job_id` | `list-mms-jobs --source-id <id>` (optionally `--name`) |
| Task | `task_id` | `list-mms-tasks --source-id <id>` (filters vary) |

### Name filter first (must)

When the user already provides a resource **name** and asks to resolve an ID, **do not start with unfiltered list-all**.  
Use the corresponding `list-* --name <token>` first, then apply strict-equality checks (LIKE warning below).

### LIKE matching warning

Many `list-* --name ...` filters are **SQL LIKE** on the backend. Treat results as **candidates** and re-check **strict equality** on the intended field before proceeding.

### Disambiguation rules

1. Exactly one strict match → use it.
2. Zero matches → tell the user and suggest corrections.
3. Otherwise → show candidates and ask the user to pick.

## Table lookup when `source_id` is known

When the user already has **`source_id`** (in message or session) and wants to **find or confirm a table** in MMS metadata:

1. **[MUST NOT]** call `list-mms-dbs` first just to “discover which db holds the table” when the user did **not** give `srcDbName` / `db_name` — the same table name can exist in **multiple** databases; guessing a db from a db list is unsafe.
2. Prefer **`list-mms-tables`** with `--source-id` plus the tightest **`--name`** filter for the user’s table (remember LIKE → **strict** equality on the returned name field). **Omit `db-name` / `dbId`** until you must narrow **duplicate** hits.
3. If several rows still match after strict checks (same table name, different db/schema), show `(db/schema, table)` candidates and ask which `srcDbName` (or equivalent) they mean, then scope further reads to that db.

## Missing `source_id` when creating jobs/timers

If the user wants `create-mms-job` / `create-mms-timer` but only provides `srcDbName` / `tables` / `partitionFilters` (or only `table_name`) and **both** the session context and the planned create **CLI flags** lack `source_id`, use this section **instead of** improvising extra discovery.

### Hard limits (must obey)

1. **Single inventory pass (for unknown source name)**: if the user did **not** provide a usable data-source name, call `list-mms-data-sources` **once** without `--name`. Let **N** = total data sources returned (if the API paginates, finish pagination **once**, then count). **Do not** re-list all sources to “double-check” unless the call failed technically.

2. **If N ≥ 3 — no metadata guessing**:
   - **[MUST NOT]** call `list-mms-dbs`, `list-mms-tables`, partition listing, or `list-mms-tasks` **to infer** `source_id` from db/table/partition/task names.
   - **[MUST]** when the user already supplied a data-source name and you are resolving name → ID, start with `list-mms-data-sources --name <narrow token>` (do not list all first). Treat LIKE hits as **candidates** and require **strict** equality on the intended field before accepting.
   - **Otherwise**: print a **short** candidate table (`source_id` + safe display name) and ask the user to reply with **one** `source_id` (or an unambiguous name). **Stop** until they answer.

3. **If N < 3 — bounded auto-resolve**:
   - **[MUST NOT]** repeat broad listing across sources after you already have enough evidence to decide or to know it is ambiguous.
   - For each remaining candidate `source_id`: `list-mms-dbs` **at most once** (prefer filters that match the user’s `srcDbName` when they gave a DB name).
   - `list-mms-tables` / partition reads **only** for `(source_id, db)` pairs still in play, and **only** to break ties — not to browse catalogs.
   - Set `source_id` **only** if **exactly one** candidate remains after **strict** db/table equality (see disambiguation rules above). If zero or >1 remain → **ask the user**; do not chain more list calls “just in case”.

4. **Table-only input** (no `source_id`, no `srcDbName`): same **N ≥ 3** ban on cross-source metadata guessing. For **N < 3**, you may spend **at most** one tight metadata pass per candidate (e.g. one `list-mms-dbs` then one `list-mms-tables` scoped to the smallest plausible db set) — then decide or ask; **no open-ended search**.

5. **Task-oriented exception**: `list-mms-tasks --src-table-name ...` is allowed for **progress/troubleshooting** when the user is clearly asking for task status, not for choosing `source_id` for a **new** `create-mms-job` / `create-mms-timer`. For **new** job/timer creation without `source_id`, still follow items 1–4.
