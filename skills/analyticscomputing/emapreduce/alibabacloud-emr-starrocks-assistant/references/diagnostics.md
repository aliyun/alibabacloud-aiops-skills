# StarRocks Cluster Health Diagnostics

Quickly determine cluster health and pinpoint issues using a series of read-only SQL queries. All commands run through `srsql` (see [connect.md](connect.md)).

## Prerequisites

Depends on the `srsql` command. If not yet configured, run `sr-login` as described in [connect.md](connect.md).

## Step 0: Identify the architecture

**Required.** The diagnostic path differs between shared-nothing and shared-data. `SHOW WAREHOUSES` exists in v3.1+; in v2.5 only BE / local-compaction paths apply.

```bash
srsql --format table -e "SHOW WAREHOUSES"
```

- **Has results & `default_warehouse` exists** -> **shared-data architecture** (EMR Serverless default)
  - Focus on **CN (Compute Nodes) + Warehouse + Cloud Native Compaction (`be_cloud_native_compactions`, v3.1+)**
  - `information_schema.be_tablets` is still populated (BE-local tablet metadata + cache info), but data files live in object storage
- **No warehouse table or error** -> **shared-nothing architecture**
  - Focus on **BE + local tablets + local compaction (`be_compactions`)**

## Step 1: FE (Frontend) nodes

**Applies to both architectures:**

```bash
srsql --format table -e "SHOW FRONTENDS"
```

**How to read it:**

- Every FE has `Alive=true`
- Exactly 1 FE has `Role=LEADER` (the rest are `FOLLOWER` or `OBSERVER`)
- `ErrMsg` non-empty -> investigate based on the message
- `ReplayedJournalId` differs by > 10000 across FEs -> a Follower can't keep up with the Leader; possibly a slow disk or network jitter

## Step 2a: BE (shared-nothing only)

```bash
srsql --format table -e "SHOW BACKENDS"
```

**How to read it:**

- All `Alive=true`
- `TabletNum` differs > 20% between nodes -> tablet distribution skew; consider a manual rebalance
- `MaxDiskUsedPct > 85%` -> disk warning (any single disk hitting the threshold)
- `UsedPct > 90%` (overall) -> disk critical
- `MemUsedPct > 90%` -> memory pressure
- `CpuUsedPct` sustained > 80% -> CPU saturation

## Step 2b: CN (v3.1+; column set varies by RunMode)

```bash
srsql --format table -e "SHOW COMPUTE NODES"
```

**How to read it:**

- All `Alive=true`
- `WarehouseName` column is present **only in shared-data mode** (not in shared-nothing)
- `MemUsedPct`, `CpuUsedPct` sustained high -> consider scaling up CUs or adding CN count
- `NumRunningQueries` abnormally high -> possibly slow queries blocking the system

## Step 3: Warehouse status (shared-data only; output columns vary by version)

```bash
srsql --format table -e "SHOW WAREHOUSES"
```

**Output column set by version (verified against `ShowWarehousesStmt`):**

- **v3.2:** `Id, Warehouse, State, ClusterCount` (4 columns) — no queue/cluster-cap info; fall back to `SHOW PROC '/current_queries'` for queue inspection.
- **v3.3+:** `Id, Name, State, NodeCount, CurrentClusterCount, MaxClusterCount, StartedClusters, RunningSql, QueuedSql, CreatedOn, ResumedOn, UpdatedOn, Comment`

**How to read it (v3.3+):**

- `State=AVAILABLE`
- `QueuedSql > 0` sustained -> insufficient concurrency; consider scaling up CUs
- `CurrentClusterCount < MaxClusterCount` and `QueuedSql > 0` -> auto-scale not triggered, or already at the cap

## Step 4: Database and tablet health overview

**Applies to both architectures.** This is the most important step.

```bash
srsql --format table -e "SHOW PROC '/statistic'"
```

Returns per-DB: `TableNum / PartitionNum / IndexNum / TabletNum / ReplicaNum / UnhealthyTabletNum / InconsistentTabletNum / CloningTabletNum / ErrorStateTabletNum`.

**How to read it** (all = 0 is best):

- `UnhealthyTabletNum > 0` -> unhealthy replicas; immediately check the FE scheduling queue
- `InconsistentTabletNum > 0` -> replica data inconsistency
- `ErrorStateTabletNum > 0` -> tablet corruption; open a ticket

## Step 5: Tablet scheduling queue

**Applies to both architectures:**

```bash
srsql --format table -e "
SELECT STATE, PRIORITY, COUNT(*) AS cnt
FROM information_schema.fe_tablet_schedules
GROUP BY STATE, PRIORITY
ORDER BY cnt DESC;
"
```

**How to read it:**

- Empty result, or only a small number of `FINISHED`, is best
- `PENDING` piling up > 100 sustained -> scheduling issue or insufficient BE/CN resources
- `RUNNING` high for a long time -> replicas are being cloned
- Many `CANCELLED` -> tablet replicas may be corrupted

## Step 6: Compaction health

**Shared-nothing:**

```bash
srsql --format table -e "
SELECT BE_ID, CANDIDATES_NUM, LATEST_COMPACTION_SCORE, CANDIDATE_MAX_SCORE,
       BASE_COMPACTION_CONCURRENCY, CUMULATIVE_COMPACTION_CONCURRENCY
FROM information_schema.be_compactions
ORDER BY CANDIDATE_MAX_SCORE DESC;
"
```

- `CANDIDATE_MAX_SCORE > 100` -> compaction can't keep up with writes; severe version backlog
- `CANDIDATES_NUM` sustained high -> increase compaction concurrency

**Shared-data (v3.1+):**

```bash
# Columns: BE_ID, TXN_ID, TABLET_ID, VERSION, SKIPPED, RUNS, START_TIME, FINISH_TIME, PROGRESS, STATUS, PROFILE
srsql --format table -e "
SELECT BE_ID, STATUS, COUNT(*) AS cnt
FROM information_schema.be_cloud_native_compactions
GROUP BY BE_ID, STATUS
ORDER BY cnt DESC;
"
```

- Any `STATUS='FAILED'` records -> drill in with `SELECT TABLET_ID, RUNS, PROFILE FROM ... WHERE STATUS='FAILED'`
- `PROGRESS` stuck low + `RUNS` increasing -> compaction repeatedly retrying

## Step 7: Resource group status

**Applies to both architectures:**

```bash
srsql --format table -e "SHOW RESOURCE GROUPS ALL"
```

**How to read it:**

- Default `default_wg` and `default_mv_wg` exist
- Check classifiers to see business resource groups (user-defined)

## Step 8: Recent ingestion job status

**Applies to both architectures** (ingestion is a common source of issues):

```bash
srsql --format table -e "
SELECT STATE, COUNT(*) AS cnt
FROM information_schema.loads
WHERE CREATE_TIME > DATE_SUB(NOW(), INTERVAL 1 DAY)
GROUP BY STATE
ORDER BY cnt DESC;
"
```

Details of failed jobs in the last 24 hours:

```bash
srsql --format table -e "
SELECT ID, LABEL, DB_NAME, TABLE_NAME, TYPE, STATE,
       CREATE_TIME, LOAD_FINISH_TIME, ERROR_MSG
FROM information_schema.loads
WHERE STATE IN ('CANCELLED', 'FAILED')
  AND CREATE_TIME > DATE_SUB(NOW(), INTERVAL 1 DAY)
ORDER BY CREATE_TIME DESC
LIMIT 20;
"
```

## Synthesis template

After diagnostics are complete, summarize for the user using this template:

```
StarRocks Cluster Diagnostic Report
===================================

Architecture: [shared-nothing | shared-data]
Overall status: [healthy | warning | critical]

Nodes:
  FE: {alive}/{total} healthy, Leader={ip}
  BE: {alive}/{total} healthy (shared-nothing)
  CN: {alive}/{total} healthy, warehouse={default_warehouse} state=AVAILABLE (shared-data)

Data:
  DB count={db_count}, table count={table_count}, tablet count={tablet_count}
  Unhealthy tablets: {unhealthy}
  Scheduling queue: PENDING={pending}, RUNNING={running}

Resources:
  Max disk usage: {max_disk}%
  Max memory usage: {max_mem}%
  Max CPU usage: {max_cpu}%

Last 24 hours:
  Ingestion jobs: {finished} succeeded / {failed} failed
  Highest compaction score: {max_score}

Key issues:
  - ... (list anomalies)

Recommendations:
  - ... (actionable suggestions)
```

## Severity quick reference

| Condition | Severity |
|---|---|
| Any FE/BE/CN with `Alive=false` | critical |
| No FE with Role=LEADER | critical |
| `UnhealthyTabletNum > 0` or `ErrorStateTabletNum > 0` | critical |
| Warehouse `State != AVAILABLE` | critical |
| BE `MaxDiskUsedPct > 95%` | critical |
| Tablet scheduling `PENDING > 1000` | warning |
| BE disk 85-95% | warning |
| BE `TabletNum` severely skewed | warning |
| Failed loads in last 24h > 5% | warning |
| `CANDIDATE_MAX_SCORE > 100` | warning |
| `QueuedSql > 0` sustained | warning |
| Other | healthy |

## Follow-up diagnostic commands

Once you've identified a class of issue, you can drill deeper:

| Symptom | Next command |
|---|---|
| A specific tablet has issues | `SHOW TABLET {tablet_id}` |
| Details of a specific DB | `SHOW PROC '/dbs/{db_id}'` |
| Currently running queries | `SHOW PROC '/current_queries'` |
| Ingestion failure details | Read `information_schema.load_tracking_logs` |

## Out of scope

- Don't modify any configuration (this topic is read-only)
- Don't restart nodes (this is a control-plane operation; handle it via the EMR Serverless console or the corresponding OpenAPI)
- Don't kill queries (requires write privilege; outside this skill's scope)
- Don't export log files (no filesystem access)
