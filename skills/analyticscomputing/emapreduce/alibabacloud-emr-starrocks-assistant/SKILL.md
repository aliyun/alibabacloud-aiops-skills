---
name: alibabacloud-emr-starrocks-assistant
description: >
  Alibaba Cloud EMR Serverless StarRocks development & operations assistant.
  Covers five scenarios: cluster connection, schema design, data ingestion,
  SQL development & tuning, and cluster health diagnostics.
  Use this Skill when users ask about StarRocks table design, writing SQL,
  choosing an ingestion method, query execution plans, materialized views,
  cluster health checks, FE/BE/CN node status, tablet health, or compaction.
  Typical scenarios: table design, Stream Load / Routine Load / Broker Load
  selection, SQL optimization, window functions, CTEs, JOIN tuning,
  materialized view design, cluster health inspection, node-down diagnosis.
  Not applicable for: StarRocks instance lifecycle management
  (create / scale / restart / config change / version upgrade — these are
  control-plane operations, please use the EMR Serverless console or the
  corresponding OpenAPI), or other Alibaba Cloud products (EMR Cluster,
  Spark, Milvus, ClickHouse, Doris, RDS, ECS).
license: MIT
allowed-tools: Bash Read
compatibility: >
  Python 3.10+ with uv; reachable StarRocks FE endpoint (default port 9030).
  On first use, run `sr-login` to register a cluster credential locally.
  Privileges follow the user's own account — capabilities (which databases /
  diagnostic commands are accessible) are introspected at login via
  SHOW GRANTS FOR CURRENT_USER().
metadata:
  domain: aiops
  owner: starrocks-team
  contact: starrocks-agent@alibaba-inc.com
  required_starrocks_privileges:
    - "Whatever the user's account already has. The skill does not create or elevate accounts."
    - "For full feature coverage: SELECT on the databases of interest + OPERATE ON SYSTEM for cluster diagnostics. Missing privileges degrade gracefully (specific suggestions are skipped)."
---

# Alibaba Cloud EMR Serverless StarRocks Development & Operations Assistant

Help users perform day-to-day table design, data ingestion, SQL writing & tuning, and health diagnostics on Alibaba Cloud EMR Serverless StarRocks. All cluster access goes through the bundled `srsql` CLI (pymysql-based, uses the user's own account); no MySQL client required. Non-READ SQL is classified by sqlglot and requires `--yes` confirmation before execution.

> **Scope statement**: This Skill focuses on *using* StarRocks — development, diagnostics, and day-to-day data operations. Cluster-internal data and schema operations (DDL, DML, materialized view refresh, GRANT, etc.) are supported and execute under the user's own account, gated by sqlglot classification + `--yes` confirmation. Instance-lifecycle operations (create, scale, restart, configuration change, version upgrade) are control-plane operations and are **not** in this Skill's scope; please use the EMR Serverless console or the corresponding OpenAPI.

## When to use / When not to use

**When to use**:

- Schema design (table model, partitioning, bucketing, sort key, indexes, storage parameters)
- Data ingestion selection (Stream/Broker/Routine Load, INSERT, Pipe, Flink/Kafka Connector, CDC)
- SQL writing, rewriting, and tuning (JOIN strategy, window functions, CTE, aggregation optimization, statistics)
- Materialized view design and operations
- Cluster health diagnostics (FE/BE/CN nodes, tablet health, compaction, warehouse, recent failed loads)

**When NOT to use**:

- Instance lifecycle control: create / scale / restart / config change / upgrade StarRocks instances — these are control-plane operations; use the EMR Serverless console or the corresponding OpenAPI instead
- Operating non-StarRocks products: EMR Cluster, Spark, Milvus, ClickHouse, Doris, RDS, ECS, etc.

## First-time setup: install & log in

This Skill ships with the `sr-connect` Python CLI. See [references/connect.md](references/connect.md) for details.

### Assistant bootstrap protocol (instructions for Claude)

When this Skill is invoked and you anticipate running any cluster query, ensure `srsql` is available *before* asking the user for anything:

1. Run `which srsql`. If it returns a path, skip to step 4.
2. If missing, install it yourself: `uv tool install <skill-project-root>` where `<skill-project-root>` is the directory containing this `SKILL.md` and `pyproject.toml` (the Skill's base directory shown at invocation time; commonly `~/.claude/skills/alibabacloud-emr-starrocks-assistant/`, which may be a symlink). **Do not ask the user to run this** — the bundled CLI is part of the Skill's capability surface, not user infrastructure.
3. If `uv` itself is missing (`which uv` fails), surface that to the user — `uv` is a system tool and not auto-installed.
4. Check `~/.starrocks/{profile}.cnf` (default profile name: `default`; respect `SR_PROFILE` env var if set). If it exists, skip to step 5. If missing:
   - **First try `sr-login --from-env`.** Safe to call unconditionally — it exits 2 with a clear "missing" message when the environment doesn't have the credentials it needs, and does nothing else. You do not need to inspect environment variables yourself.
   - **If `sr-login --from-env` exits non-zero**, the user hasn't logged in yet. Give them the `sr-login --host ... --user ...` command and ask them to run it themselves. **Do not run interactive `sr-login` yourself** — it would block on a password prompt you cannot answer.
5. After both `srsql` is on PATH and the profile file exists, run queries via `srsql -e "..."` yourself.

If `srsql` was just installed in this session and PATH hasn't been refreshed in the user's shell, fall back to the absolute path printed by `uv tool install` (typically `~/.local/bin/srsql`).

**Chat-style rule after bootstrap succeeds**: Do **not** echo `sr-whoami` / `srsql -e "..."` invocation syntax to the user as a "you can now run …" hint. You are the one calling these CLIs on the user's behalf — the user drives the Skill, not the binaries. Skip the post-success "next step" narration entirely and just ask what they want to do, or proceed if their intent is already clear.

### Login command (give this to the user when their profile is missing)

```bash
# EMR Serverless StarRocks — both internal and public endpoints use the MySQL
# wire protocol over plain TCP; no SSL/TLS. Use the same form for either.
sr-login --host <fe-endpoint> --port 9030 --user <account>

# Verify
sr-whoami
srsql -e "SELECT CURRENT_VERSION()"
```

Re-running `sr-login` with the same `--profile` silently overwrites the stored credential (same semantics as `docker login`). Use `--profile` for multi-cluster:

```bash
sr-login --profile prod --host fe-prod.xxx --user app_user
SR_PROFILE=prod srsql -e "..."
```

## Security model

This Skill has **two layers**:

1. **FE is the authoritative permission boundary.** The user supplies their own StarRocks account; whatever they're allowed to do, they're allowed to do. The Skill does not create, elevate, or rotate any accounts.
2. **`srsql` is a UX gate, not a security boundary.** Every statement is parsed by sqlglot (dialect `starrocks`):
   - `READ` (SELECT / SHOW / DESC / EXPLAIN / WITH / …) executes directly.
   - **Any non-READ** (INSERT / UPDATE / DELETE / DDL / GRANT / SET / USE / …) **is refused unless `--yes` is passed**.
   - SQL sqlglot cannot parse falls back to a leading-keyword check; if still ambiguous → `UNKNOWN`, treated as non-READ, executable with `--yes` plus a soft warning.

When the user asks for a write operation:

1. Show them the SQL you intend to run.
2. Optionally preview classification via `srsql --dry-run -e "..."`.
3. Get explicit confirmation in chat.
4. Then run with `srsql --yes -e "..."`.

For DDL on production tables, or operations that change global cluster state (CREATE/DROP USER, ADMIN SET CONFIG, etc.), prefer to print the SQL and let the user run it themselves — even though the gate would let them run it via `--yes`. The gate is a safety net, not a license.

## Input validation & command-injection protection

SQL passed into `srsql -e "..."` is assembled by the LLM and must follow these rules:

1. Identifiers (table / column / database names) are validated before interpolation: only `[A-Za-z0-9_]` plus backtick-quoted forms.
2. User-provided string values (search terms, label names, etc.) are **not** spliced into SQL directly; use parameter binding or pre-escape.
3. Never execute raw user-provided strings as SQL fragments.

## Sensitive data masking

| Scenario | Handling |
|----------|----------|
| Profile file content (incl. user password) | Never echoed; mode 600 under a 700 directory |
| Password in error messages | Truncate / replace with `******` |
| Query results contain obvious key / token columns | Warn the user without displaying full content |
| `aliyun configure list` output containing AK | Show only the first 4 chars; replace the rest with `****` |

## Intent routing

> **Disambiguation rule**: When the user input is ambiguous (e.g. "ingestion is slow", "queries are slow") and context is unclear, ask one clarifying question before acting.

| User intent | Route | Reference |
|-------------|-------|-----------|
| First-time cluster connection / register or switch credentials / multi-cluster setup | sr-login / sr-whoami / sr-logout | [references/connect.md](references/connect.md) |
| New table / change schema / table model selection / partition+bucket design | Schema design | [references/schema.md](references/schema.md) |
| Choose ingestion method / configure Stream/Broker/Routine Load / Flink/Kafka Connector | Import selection | [references/data-import.md](references/data-import.md) |
| Write SQL / optimize SQL / materialized views / function selection / read execution plans | SQL development & tuning | [references/sql.md](references/sql.md) |
| Cluster health check / FE/BE/CN status / unhealthy tablets / compaction lag | Cluster diagnostics | [references/diagnostics.md](references/diagnostics.md) |
| "Ingestion used to be fine, suddenly slow" | Cluster diagnostics (distinct from import selection) | [references/diagnostics.md](references/diagnostics.md) |
| "How should I design a new ingestion pipeline" | Import selection | [references/data-import.md](references/data-import.md) |

## Five scenarios at a glance

### 1. Schema design

Four table models and their typical use cases:

| Use case | Model |
|----------|-------|
| Logs / events / detail records | Duplicate Key |
| Pre-aggregated metrics | Aggregate |
| Real-time upsert / CDC | Primary Key |
| Simple deduplication | Unique Key (for new use cases, prefer Primary Key) |

**⚠ Anti-patterns — do not produce these in DDL:**
- **Shared-data PK table without `persistent_index_type=CLOUD_NATIVE` + `datacache.partition_duration`** — LOCAL index doesn't survive CN rebalance; no hot-data caching window. See [schema/storage-properties.md](references/schema/storage-properties.md).
- **Setting `datacache.partition_duration` to an arbitrary "hot window" (e.g. `30 DAY`) instead of the user's stated query window** — the value MUST be **≥ the query window**. If the user says "查询近 N 天" / "queries the last N days", set `datacache.partition_duration = "N DAY"` (or larger). A value smaller than the query window guarantees cache misses on in-window queries. Do not default to 7/30/60 days when the user has given you a number.
- **`storage_cooldown_time`/`storage_cooldown_ttl`/`storage_medium`/`replicated_storage` on shared-data** — silently stripped or rejected by `PropertyAnalyzer`; use `datacache.partition_duration` for the cooldown effect.
- **FLOAT / DOUBLE columns inside `PRIMARY KEY`** — not supported; use BIGINT or DECIMAL.
- **Treating "CN" as a shared-nothing signal** — CN = Compute Node, which is the shared-data terminology. BE = Backend = shared-nothing.

See [references/schema.md](references/schema.md).

### 2. Data ingestion

| Data source | Recommended method |
|-------------|--------------------|
| Local files < 10 GB | Stream Load |
| Object storage / HDFS bulk | Broker Load or `INSERT INTO ... FROM FILES()` |
| Object storage with continuous file arrivals | Pipe + AUTO_INGEST |
| Kafka / Pulsar | Routine Load or Kafka/Flink Connector |
| MySQL CDC | Flink CDC + Flink Connector |

**⚠ Anti-patterns — do not produce these in load configs:**
- **PK-table DELETE without `__op` integer column (`0`=UPSERT, `1`=DELETE) in COLUMNS list + `$.__op` in `jsonpaths`** — all events are silently treated as UPSERT. **The `__op` contract is a pair and must be taught as a pair**: the literal column name is `__op`, and the integer values are `__op=0` for UPSERT **and** `__op=1` for DELETE. Even when the user only asks about DELETE, your response MUST state **both** mappings (`__op=0` → UPSERT, `__op=1` → DELETE) — never one without the other. This applies on every ingestion path including Flink Connector and Kafka Connector, where the connector populates `__op` for the user but they still need both values to debug "DELETE not applied" / "UPSERT not applied" symptoms.
- **Treating `partial_update=true` as a DELETE enabler** — it controls partial-column UPSERT and has **nothing to do** with DELETE. If a user enables it while asking why DELETE doesn't work, **flag it as misconfigured-for-intent** and tell them to remove it unless they actually have a partial-column UPSERT use case. Do not validate the existing setting just because it parses.
- **`COLUMNS FROM PATH AS (...)` in Routine Load** — that's Broker Load's Hive-partition path syntax; not valid in Routine Load.
- **`__op` values as strings (`"upsert"`/`"delete"`)** — must be the integers `0` / `1`.
- **High-throughput CDC (≥ ~10K events/sec) without flagging TOO_MANY_VERSION risk** — applies to Routine Load, Flink Connector, Kafka Connector, not just `INSERT INTO VALUES`. Whenever the user's scenario implies high event rate, the recommendation MUST cover: (a) the method-appropriate concurrency cap (`desired_concurrent_number` ≤ Kafka partitions for Routine Load; `sink.parallelism` ≤ Kafka partitions for Flink/Kafka Connector), AND (b) an explicit TOO_MANY_VERSION / compaction-pressure warning with the relevant flush-interval guidance.

See [references/data-import.md](references/data-import.md).

### 3. SQL development

| Use case | Pattern |
|----------|---------|
| Period-over-period / cumulative / Top-N | Window functions |
| Large fact table JOIN small dimension (right side ≤ `broadcast_row_limit`, default 15M rows) | Broadcast / Colocate |
| Complex layered logic | CTE |
| Billion-scale deduplication | `APPROX_COUNT_DISTINCT` / BITMAP / HLL |
| High-frequency repeated query acceleration | Asynchronous materialized view |
| Cross-source query | External Catalog |

**⚠ Anti-patterns — do not produce these in query rewrites or tuning advice:**
- **Wrapping the partition column with `date_format()` / `date_trunc()` / `cast()` in WHERE** — breaks partition pruning; rewrite as a range predicate (`col >= '...' AND col < '...'`).
- **Tuning advice without `EXPLAIN VERBOSE` + checking `partitions=N/M` and `tabletRatio=N/M`** — pruning failures (numerator == denominator) go undetected; never use plain `EXPLAIN` for this.
- **Reading `cardinality` in EXPLAIN as the result row count** — it's the **CBO's row estimate**. Always quantify the staleness gap using the **direct comparison `cardinality` vs the user-stated total table size** (e.g. "estimate 5M vs total 500M ≈ 100×"); a ratio > 10× means stats are stale → run `ANALYZE TABLE`.
- **Estimating "real filtered rows" by guessing predicate selectivity, then comparing cardinality to that guess** — you don't have runtime row counts, and guessing selectivity from a predicate like `WHERE create_time > '...'` introduces large errors (you don't know the data distribution). When the user gives you a total row count, compare `cardinality` to that **directly**; do not divide the total by an assumed time window or selectivity factor.
- **Conflating `partitions`/`tabletRatio` pruning failures with `cardinality` deviation** — these are **two independent diagnostic signals**. When both look bad in the same OlapScanNode (e.g. `partitions=N/N` AND `cardinality` off from total table size by 10×–100×), report them as **separate findings with separate fixes** (predicate/type fix vs `ANALYZE TABLE`). Do not use cardinality deviation to "explain" pruning failure, and do not let pruning failure absorb the stale-stats finding.
- **Recommending BE/CN scale-out before plan/stats analysis** — SQL/stats fixes precede capacity changes.

See [references/sql.md](references/sql.md).

### 4. Cluster diagnostics

Diagnostic order:

1. Identify architecture (shared-nothing / shared-data) → `SHOW WAREHOUSES`
2. FE → `SHOW FRONTENDS`
3. BE or CN → `SHOW BACKENDS` / `SHOW COMPUTE NODES`
4. Warehouse (shared-data only) → `SHOW WAREHOUSES`
5. Tablet health overview → `SHOW PROC '/statistic'`
6. Scheduling queue → `information_schema.fe_tablet_schedules`
7. Compaction → `information_schema.be_compactions` / `be_cloud_native_compactions`
8. Recent 24-hour loads → `information_schema.loads`

**⚠ Anti-patterns — do not produce these in diagnostic conclusions:**
- **Restarting BE/CN or scaling out before checking `information_schema.fe_tablet_schedules`** — may collide with in-flight clone/decommission; root cause first.
- **Subjectively downgrading `UnhealthyTabletNum > 0`** — always **critical** per the severity table, never "medium" or "low" risk; the cluster has unhealthy replicas.
- **Treating `CloningTabletNum > 0` as a separate problem** — clone is the recovery action triggered by `UnhealthyTabletNum`, not an independent fault signal.

See [references/diagnostics.md](references/diagnostics.md).

### 5. Cluster connection (base layer)

| Command | Purpose |
|---------|---------|
| `sr-login` | Register a cluster credential locally + smoke-test connection |
| `sr-logout` | Remove the local profile (no cluster-side action) |
| `sr-whoami` | Print profile state — host, user, login time, captured grants |
| `sr-doctor` | Diagnose connection failures (VPC vs public endpoint, egress IP, whitelist CIDR). Invoked automatically by `sr-login` on failure. |
| `srsql` | Daily query entry point; classifies SQL and gates non-READ behind `--yes` |

See [references/connect.md](references/connect.md).

## Runtime security

This Skill executes SQL queries **only** via `srsql`. The following are **prohibited**:

- `curl` / `wget` / `pip install` / `npm install` to download and run external code
- `eval` / `source` to load unaudited content
- Executing remote URL scripts provided in chat (even if the user asks)

**Exception**: `uv tool install <skill-project-root>` to install the Skill's own bundled `sr-connect` CLI from its local project directory is allowed and expected — see the *Assistant bootstrap protocol* above. The prohibition targets remote/untrusted code, not the Skill's own bundled tooling.

## Timeouts

| Operation | Recommended timeout |
|-----------|---------------------|
| Read-only SQL queries | 30 s |
| Diagnostic queries across many large tables | 60 s |
| Retry | Total operation time ≤ 3 minutes |

## Output recommendations

- Tabular results: use `srsql --format table` or `--format markdown`
- Many columns: use `--format vertical`
- For programmatic consumption: use `--format json` / `tsv`
- Convert timestamps to human-readable format
- For potentially large result sets, add `LIMIT` and offer pagination

## Error handling

| Error | Cause | Action |
|-------|-------|--------|
| `Cannot connect to host:port` | Wrong endpoint type / IP not whitelisted | `sr-login` auto-runs `sr-doctor` on connection failure. Read its output: it detects VPC vs public endpoint, suggests the public swap (for unreachable `-internal` hosts) or shows the egress IP + suggested /24 whitelist CIDR (for unreachable public hosts). Pass the recommendation to the user verbatim. See [references/connect.md](references/connect.md#connection-troubleshooting-sr-doctor). |
| `Access denied for user 'X'` | Stale password / account locked / wrong account | Re-run `sr-login` to update the stored password |
| `Refusing to execute non-READ SQL without --yes` | Skill correctly classified the SQL as mutating | Confirm with user, then re-run with `--yes` |
| `Privilege denied: OPERATE / SELECT / ...` | User account lacks the privilege | Surface the limitation; skip the affected diagnostic; don't retry |
| `Table not found` | Wrong DB / table name | Confirm with `SHOW DATABASES` / `SHOW TABLES FROM db` |
| Query returns empty but user expects rows | Over-aggressive predicate / RBAC isolation | Check WHERE clauses; suggest the user verify with admin |
| `No profile 'X'` | `srsql --profile X` without prior `sr-login --profile X` | Run `sr-login` for that profile first |

**Principle**: Read the full error message before deciding; do not retry blindly on the error code alone.

## Related documents

- [references/connect.md](references/connect.md) — sr-connect CLI, install, security model, troubleshooting
- [references/ram-policies.md](references/ram-policies.md) — RAM permission declaration (none required; StarRocks-internal auth only)
- [references/schema.md](references/schema.md) — schema design flow: table models, partitioning, bucketing, sort key, indexes, storage parameters
- [references/data-import.md](references/data-import.md) — ingestion method selection, parameters, performance tuning, Primary Key updates
- [references/sql.md](references/sql.md) — query writing, window functions, materialized views, functions, SQL tuning, advanced features
- [references/diagnostics.md](references/diagnostics.md) — cluster health inspection flow, severity classification, synthesis template
