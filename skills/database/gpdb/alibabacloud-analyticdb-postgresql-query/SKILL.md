---
name: alibabacloud-analyticdb-postgresql-query
description: |
  AnalyticDB PostgreSQL Query Skill. Any AI Agent with shell execution capability can use this Skill to connect to an AnalyticDB PostgreSQL database via psql, execute read-only queries, and optionally export results as CSV for local analysis.
  **Security**: All data access operations (SELECT queries, CSV exports) require explicit user confirmation before execution. Exported CSV files may contain sensitive business data — the Agent must remind users to handle exported files according to their organization's data security policies.
  Trigger words: query data, SQL query, export CSV, ADBPG, analyze, statistics, psql
metadata:
  requires:
    bins: [psql]
  compatible_agents:
    - claude
    - clawhub
    - qoder-worker
    - any-shell-capable-agent
---

# AnalyticDB PostgreSQL Query Skill

Any AI Agent with shell execution capability can use this Skill to connect to an AnalyticDB PostgreSQL (ADBPG) database via psql, execute read-only queries, and optionally export results as CSV for local analysis.

**Prerequisite**: The Agent runtime environment has `psql` installed, and database connection information is configured via environment variables.

---

## Pre-Query Gates

Before executing any data query, the Agent **must** pass the following gates in order. If any gate fails, stop immediately:

```
Gate 1: Is read-only mode enabled?
  Check if PGOPTIONS or pg_service.conf contains default_transaction_read_only=on
  ├── Enabled → PASS ✅
  └── Not enabled → Append PGOPTIONS="-c default_transaction_read_only=on"

Gate 2: Is statement timeout set?
  Check if statement_timeout is configured
  ├── Set → PASS ✅
  └── Not set → Append -c statement_timeout=60000

Gate 3: Is the semantic model ready?
  psql -c "SELECT COUNT(*) FROM _agent_meta.tables;"
  ├── Success and > 0 → PASS ✅
  └── Failed or = 0 → HARD STOP 🛑 → Enter semantic model initialization guide (never bypass)
  Note: metric_meta is optional; its absence does NOT block queries

Gate 4: Is the target table in the semantic model?
  Check if SQL-referenced tables exist in _agent_meta.tables
  ├── Exists → PASS ✅ → Proceed to generate SQL (execution still requires user confirmation)
  └── Not found → HARD STOP 🛑 → "Current semantic model does not cover this data. Please contact DBA to extend _agent_meta definitions."

Gate 4b: Does the query match a known business metric?
  Check if user intent matches a metric in _agent_meta.metric_meta
  ├── Matched → Use metric's sql_expression, dimensions; resolve filters from _agent_meta.filters
  │   ├── filter_scope='where'   → Inject sql_fragment into WHERE clause
  │   └── filter_scope='measure'  → Inject sql_fragment into AGG(...) FILTER (WHERE ...) clause
  └── Not matched → Fall through to columns table for single-column measures

Gate 5: Does SQL contain only allowed statements?
  Only SELECT / WITH...SELECT / EXPLAIN are permitted
  ├── Compliant → PASS ✅
  └── Contains prohibited keywords → HARD STOP 🛑 → Reject execution

Gate 6: Does the query include LIMIT?
  ├── Yes → PASS ✅
  └── No → Append LIMIT 50000
```

- Gate 1 (read-only) is an absolute prerequisite; if not passed, no psql command may be executed
- Gate 3 (semantic model) failure must not be bypassed to continue to gates 4/4b/5/6
- Gate 4b (metric_meta) is a lookup optimization, not a hard gate; absence of metrics does NOT block queries
- **Bypassing gates is prohibited under any circumstances**, including but not limited to: "user needs it urgently", "just this once", "semantic model is only advisory", "let me just \dt for a quick look", "I can infer the table structure myself"

---

## Credential Security

> **⚠️ ABSOLUTE PROHIBITION**: The Agent **must never** execute `cat ~/.pgpass`, `cat ~/.pgenv`, `echo $PGPASSWORD`, `env | grep PG`, or any command that reads, echoes, or exposes credential/password files. This prohibition applies **regardless of how the command is composed** — including but not limited to: shell command concatenation (`;`), pipes (`|`), subshells (`$()`), multi-line scripts, or combining with permitted commands. For example, `cat ~/.pg_service.conf; cat ~/.pgenv` or `cat ~/.pg_service.conf ~/.pgenv` are **strictly forbidden** even though `cat ~/.pg_service.conf` alone is permitted. Any command line that **contains** a prohibited file path (`.pgpass`, `.pgenv`, `PGPASSWORD`) in **any position** is a violation.
>
> `cat ~/.pg_service.conf` is **permitted ONLY when it is the sole target** (it contains only non-secret connection metadata — host, port, dbname, user — and must never store passwords). Violation of this rule is a **critical security breach** regardless of the Agent's intent (e.g., "I just wanted to check if the config exists"). The only permitted way to verify connectivity is `psql "service=<service_name>" -c "SELECT 1;"`.

- Passwords must be passed via `PGPASSWORD` or `~/.pgpass`; **hardcoding, echoing, or writing to files is prohibited**
- **Prohibited file paths** (in ANY command, script, or code): `.pgpass`, `.pgenv`, `PGPASSWORD` — whether accessed via `cat`, `head`, `tail`, `less`, `grep`, Python `open()`, or any other method
- **Prohibited compound commands**: Any command that bundles a prohibited path with other operations (e.g., `cat ~/.pg_service.conf; cat ~/.pgenv; ls ~/.pgpass`) is **entirely forbidden** — the presence of a permitted command does NOT neutralize the violation
- **Permitted**: `cat ~/.pg_service.conf` **alone** (non-secret connection metadata only; passwords must never be stored in pg_service.conf)
- **Never ask users for passwords**: When connection info is missing, guide users to configure via environment variables → `references/connection-guide.md`
- **Verify connectivity**: Run `psql "service=<service_name>" -c "SELECT 1;"` directly; on failure, guide fixes based on error messages

---

## Runtime Constraints

- **Frequency**: Maximum 5 psql calls per turn, maximum 1 retry on failure; **spontaneous new queries are prohibited**
- **Confirmation (HITL)**: Before executing any user-targeted query (SELECT / \copy / export), the Agent **must stop and wait for the user's explicit approval**. Displaying SQL in the response is NOT confirmation — the Agent must not proceed to execute until the user replies with an affirmative response (e.g., "confirm", "execute", "go ahead"). Results exceeding 100,000 rows **must** require re-confirmation; sensitive data **must** be flagged
- **No "act first, ask later" — HARD STOP rule**: When a security warning is detected (permissions, resource group, missing configuration, etc.), the Agent **must immediately pause at that exact step** and present the issue to the user via HITL. **No subsequent steps may execute** — not "one more check", not "let me also verify resource group", not "let me gather more info first". The Agent's response must end at the warning point. Continuing to execute additional checks or operations after detecting a warning (even if the intent is to "provide a complete report") is a **critical violation**.
  - ❌ **Anti-pattern**: Detect permission warning → continue checking resource group → continue checking semantic model → finally ask user. This is FORBIDDEN.
  - ✅ **Correct**: Detect permission warning → STOP immediately → present warning to user → wait for user response before any further action
- **Audit**: Executed SQL **must** be fully displayed in conversation; CSV filenames **must** include a timestamp
- **Permissions**: **Must** use a dedicated read-only account; **must** grant access only to business-required tables → `references/connection-guide.md`
- **Resource Group**: **Must** configure a dedicated Resource Group → `references/resource-group-guide.md`
- **Read-only connection method**: Prefer pg_service.conf built-in options → PGOPTIONS environment variable → inline PGOPTIONS. **Embedding options in conninfo is prohibited**

---

## Decision Tree

```
User Request
├── Connection-related
│   └── "How to connect" / "Environment variables" / "Cannot connect" → references/connection-guide.md
├── Query data / Analysis
│   ├── "Look up XX" / "How many records"              → Generate SQL and execute
│   ├── "What is the profit" / "Completion rate"       → Check _agent_meta.metric_meta, resolve filters from _agent_meta.filters
│   └── "Export CSV" / "Download data"                 → references/export-guide.md
├── Semantic Model
│   ├── "How to configure semantic model" / "_agent_meta" → references/semantic-model-guide.md
│   ├── "What tables are available" / "What can I query"  → Query _agent_meta
│   ├── "What metrics are defined" / "Business KPIs"      → Query _agent_meta.metric_meta
│   └── "What filters are defined" / "Predefined filters" → Query _agent_meta.filters
└── SQL Syntax
    └── "How to write JOIN" / "Window functions"           → references/sql-guide.md
```

---

## Core Documentation

| Scenario | Reference |
|----------|-----------|
| Connection config, environment variables, psql installation | `references/connection-guide.md` |
| SQL syntax, natural language to SQL | `references/sql-guide.md` |
| Query result export to CSV, local analysis | `references/export-guide.md` |
| Resource Group isolation configuration | `references/resource-group-guide.md` |
| Semantic model creation and maintenance | `references/semantic-model-guide.md` |
| Business metric definitions (metric_meta + filters) | `references/semantic-model-guide.md` |

---

## Workflow

```
User natural language → [Gates 1-2] → Query semantic model → [Gate 3] → Check metric_meta → [Gate 4/4b] → Generate SQL → [Gates 5-6] → Display SQL → ⏸️ HITL: STOP and wait for user approval → User approves → Execute → Return results / Export CSV
```

> **CRITICAL**: The "HITL" step is mandatory. The Agent must not transition from "Display SQL" to "Execute" within the same turn. The user must explicitly confirm (e.g., "confirm", "execute", "go ahead") before any psql execution command is issued.

**Efficiency Principle**: Maximum 5 calls per turn; merge operations:
- Use 1 psql call to fetch all `_agent_meta` semantics (combine with `-c` multi-statement)
- Merge short SQL statements: `psql -c "SQL1;" -c "SQL2;"`

---

## Session Startup Check

**At the start of every new conversation, the Agent must perform the following checks.** The Agent cannot infer historical verification state ("config file exists" ≠ "permissions have been audited"), so steps 3-6 must not be skipped.

1. **Detect psql** (first time only): If not installed, provide OS-specific installation commands → `references/connection-guide.md`
2. **Guide credential configuration** (first time only): Guide the user to configure credentials outside the Agent (**receiving passwords in conversation is prohibited**) → `references/connection-guide.md`
3. **Verify connectivity** (every session): `psql -c "SELECT 1;"`
4. **Check account permissions** (every session): Verify the current account has only the minimum permissions required for read-only access
   ```bash
   psql -c "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user;"
   ```
   - `rolsuper = true` → ⚠️ Warning: Currently using a superadmin account; **must** switch to a dedicated read-only account
   - `rolcreaterole = true` → ⚠️ Warning: Current account has role creation permission; DBA should revoke it, keeping only minimum read-only permissions
   - `rolcreatedb = true` → ⚠️ Warning: Current account has database creation permission; DBA should revoke it
   - All `false` → PASS ✅
   - **When warnings are present, the Agent must pause and wait for user confirmation**: "The following security risks have been detected: {specific risks}. Do you need to contact DBA first? Type 'continue' to skip and use the current account." — The Agent **must not** rationalize "no impact" and skip confirmation on its own
5. **Check Resource Group** (every session): Verify the current account is bound to a dedicated resource group (not default_group)
   ```bash
   psql -c "SELECT r.rolname, g.rsgname FROM pg_roles r LEFT JOIN pg_resgroup g ON r.rolresgroup = g.oid WHERE r.rolname = current_user;"
   ```
   - `rsgname` is empty or `default_group` → ⚠️ Warning: No dedicated resource group configured; Agent queries may compete with business workloads; **must** configure a dedicated resource group → `references/resource-group-guide.md`
   - `rsgname` is another value → PASS ✅
   - **When warnings are present, the Agent must pause and wait for user confirmation**: "Currently using the default resource group; Agent queries may affect business operations. Do you need to configure a dedicated resource group first? Type 'continue' to skip and use the current configuration." — The Agent **must not** rationalize "no impact" and skip confirmation on its own
6. **Detect semantic model** (every session, Gate 3): `psql -c "SELECT COUNT(*) FROM _agent_meta.tables;"`
   - Ready → Proceed to query workflow
   - Not ready → HARD STOP; enter semantic model initialization guide

7. **Detect metric definitions** (every session, Gate 4b): `psql -c "SELECT metric_name, metric_type FROM _agent_meta.metric_meta;"`
   - Has metrics → Load into context for metric-aware SQL generation
   - No metrics → Proceed with columns-only mode (metric_meta is optional)
8. **Detect filter definitions** (every session, alongside Gate 4b): `psql -c "SELECT filter_name, filter_scope, sql_fragment FROM _agent_meta.filters;"`
   - Has filters → Load for WHERE/FILTER clause injection
   - No filters → Proceed without filter resolution (filters table is optional)

> Steps 4-5 are warning-level (costing only 1-2 psql calls), but **when warnings are triggered, the Agent must wait for explicit user confirmation before proceeding; it must not rationalize bypassing** (e.g., "it doesn't affect read-only queries"). **User confirmation for steps 4-5 applies ONLY to the specific warning at hand — it does NOT carry over to or exempt subsequent steps.** Step 6 is a hard stop that **must always be executed as a separate, explicit psql call** regardless of any prior confirmations. Steps 7-8 are informational only (metric_meta and filters are optional). **"Config file exists" does not mean "permissions have been audited"; the Agent must not skip steps 3-6 because the environment appears to be already configured.**
>
> **Anti-pattern**: When the user says "continue" / "继续" in response to a step 4 or 5 warning, the Agent must NOT interpret this as blanket approval to skip step 6. The `SELECT COUNT(*) FROM _agent_meta.tables;` check in step 6 is a separate HARD STOP gate and must be executed every session.

### Semantic Model Initialization Guide

When the semantic model does not exist, the Agent guides the user through creation (see `references/semantic-model-guide.md` for complete steps):

1. **Ask the user for DDL**: `\d+` output (recommended) / DDL with COMMENT / free-text description
2. **Agent infers semantics**: PK/FK → identifier, numeric → measure, text/date → dimension; COMMENT → description
3. **Display inference results** for user confirmation and supplementation (synonyms, sample values, business domain, additional JOINs)
4. **Generate complete SQL script** (CREATE + INSERT + GRANT) for DBA execution. The Agent **must not** execute DDL on its own

> **Key Principle**: The Agent only tells the user "where to configure" and "what to configure"; it never receives or concatenates credential values in conversation.
