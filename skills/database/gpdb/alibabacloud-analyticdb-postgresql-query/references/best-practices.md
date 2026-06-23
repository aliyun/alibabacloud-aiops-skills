# ADBPG Query Skill Best Practices

This document summarizes best practices for using the ADBPG Query Skill in production environments, continuously refined based on issues encountered during real deployments.

---

## 1. DBA-Side Initialization Checklist

Before the Agent is put into use, the DBA should complete the following configurations; otherwise, the Agent will trigger warnings at every session startup:

### 1.1 Create a Dedicated Read-Only Account

```sql
-- Create account without granting any excessive privileges
CREATE ROLE agent_readonly WITH LOGIN PASSWORD 'xxx' NOSUPERUSER NOCREATEROLE NOCREATEDB;

-- Grant access only to business-required tables (GRANT SELECT ON ALL TABLES IN SCHEMA is prohibited)
GRANT SELECT ON public.orders, public.customers, public.products TO agent_readonly;

-- Grant read access to the semantic model
GRANT USAGE ON SCHEMA _agent_meta TO agent_readonly;
GRANT SELECT ON _agent_meta.tables, _agent_meta.columns, _agent_meta.joins TO agent_readonly;
```

**Common Mistake**: Connecting with a DBA or superadmin account, causing `rolsuper=true` warnings at every session and risking accidental write operations.

### 1.2 Create a Dedicated Resource Group

```sql
-- Create Agent-dedicated resource group
CREATE RESOURCE GROUP agent_rg WITH (
  concurrency = 3,          -- Match the Agent's max 5 psql calls per turn
  cpu_rate_limit = 10,      -- CPU limit 10%
  memory_limit = 15,        -- Memory limit 15%
  memory_shared_quota = 80
);

-- Set queue timeout to prevent indefinite query waiting
ALTER RESOURCE GROUP agent_rg SET memory_spill_ratio 0;

-- Bind read-only account
ALTER ROLE agent_readonly RESOURCE GROUP agent_rg;
```

**Common Mistake**: Not configuring a dedicated resource group (or using `default_group`), causing Agent high-frequency queries to compete with business resources and trigger performance alerts.

### 1.3 Create the Semantic Model

See `semantic-model-guide.md` for table creation scripts. Population rules:

| Field Type | Recommended column_role | Example |
|-----------|------------------------|---------|
| Primary / Foreign Key | `identifier` | order_id, customer_id |
| Numeric (amounts, quantities, metrics) | `measure` | amount, quantity, score |
| Text, enum, date | `dimension` | status, region, created_at |

**Common Mistake**: Not filling in `synonyms`, causing the Agent to be unable to map "order count" to the `order_count` field when a user uses business terminology.

---

## 2. Agent-Side Connection Configuration

### 2.1 Recommended Configuration Methods (by Priority)

**macOS / Linux**:

```ini
# ~/.pg_service.conf (Recommended: read-only options built-in, Agent doesn't need to be aware)
[adbpg]
host=xxx.gpdb.rds.aliyuncs.com
port=5432
dbname=mydb
user=agent_readonly
options=-c default_transaction_read_only=on -c statement_timeout=60000
```

```
# ~/.pgpass (permissions must be 0600)
xxx.gpdb.rds.aliyuncs.com:5432:mydb:agent_readonly:your_password
```

**Windows**:

```powershell
# System-level environment variables (PowerShell, persistent)
[Environment]::SetEnvironmentVariable("PGSERVICE", "adbpg", "User")
[Environment]::SetEnvironmentVariable("PGOPTIONS", "-c default_transaction_read_only=on -c statement_timeout=60000", "User")
```

### 2.2 Prohibited Configuration Methods

```bash
# ❌ Prohibited: embedding options in conninfo (ADBPG does not support)
psql "host=xxx options='-c default_transaction_read_only=on'"

# ❌ Prohibited: plaintext password in command line
psql "host=xxx password=mypassword"

# ❌ Prohibited: providing password to Agent in conversation
# Agent seeing password → may be captured by logs, context, or other tools
```

---

## 3. Semantic Model Maintenance

### 3.1 Coverage Scope Principles

- **Only register tables that need to be queried**; tables that don't need to be exposed to the Agent should not be added to `_agent_meta`
- Tables in `_agent_meta` must be consistent with those authorized by the DBA; inconsistencies will cause Gate 4 to block queries

### 3.2 Synonyms Are Key

```sql
-- Good example: when business terminology differs significantly from field names, synonyms must be configured
UPDATE _agent_meta.columns
SET synonyms = ARRAY['order count', 'order volume', 'number of orders']
WHERE table_name = 'orders' AND column_name = 'order_count';
```

Without synonyms, when a user says "check recent order volume", the Agent cannot map to the correct field and is prone to hallucinations or generating incorrect SQL.

### 3.3 Version Update Process

```
New business table → DBA updates _agent_meta → New table automatically visible to Agent
Deprecated business table → DBA deletes from _agent_meta → Agent automatically rejects queries on that table
Field meaning change → DBA updates column_description and synonyms
```

No action needed on the Agent side; semantic model changes take effect immediately.

---

## 4. Known Risks and Remediation

### 4.1 Account Privilege Escalation Risk (Frequently Triggered)

**Symptom**: Session startup warns `rolcreaterole=true` or `rolcreatedb=true`

**Root Cause**: Account was created with `CREATEROLE` or `CREATEDB` options

**Remediation**:
```sql
-- Revoke excessive privileges
ALTER ROLE agent_readonly NOCREATEROLE NOCREATEDB;
```

**Temporary Workaround**: Type "continue" to skip the warning, but must fix during the next maintenance window.

### 4.2 Resource Group Not Configured (Frequently Triggered)

**Symptom**: Session startup warns current binding is `default_group`

**Root Cause**: `ALTER ROLE ... RESOURCE GROUP agent_rg` was not executed after account creation

**Remediation**:
```sql
ALTER ROLE agent_readonly RESOURCE GROUP agent_rg;
-- Verify
SELECT r.rolname, g.rsgname FROM pg_roles r
LEFT JOIN pg_resgroup g ON r.rolresgroup = g.oid
WHERE r.rolname = 'agent_readonly';
```

### 4.3 Semantic Model Does Not Exist (Hard Stop)

**Symptom**: `ERROR: schema "_agent_meta" does not exist` or `COUNT = 0`

**Remediation**: Enter semantic model initialization guide; provide DDL (`\d+` output); the Agent auto-infers and generates table creation scripts.

**Note**: When the semantic model doesn't exist, the Agent will not bypass it. Do not attempt to use "just check \dt for a quick look" to bypass; it will be blocked by Gate 3.

### 4.4 ADBPG Does Not Support FOREIGN KEY

**Symptom**: Running `_agent_meta.columns` table creation script produces `ERROR: Trigger is not supported on beam yet`

**Root Cause**: ADBPG beam engine does not support triggers; FOREIGN KEY constraints rely on triggers internally

**Remediation**: The table creation script has already removed FOREIGN KEY; referential integrity is ensured by the DBA during data population (`table_schema/table_name` in `_agent_meta.columns` must match existing records in `_agent_meta.tables`).

### 4.5 Agent Skips Session Startup Checks

**Symptom**: Agent sees `~/.pg_service.conf` already exists and jumps directly to the query step, skipping permission and resource group checks

**Root Cause**: "Config file exists" is mistakenly treated as "environment has been audited"

**Remediation**: Explicitly tell the Agent "please re-run the session startup checks", or start a new conversation to let the Skill reinitialize.

**Prevention**: SKILL.md explicitly states "config file exists ≠ permissions have been audited"; the Agent must not skip steps 3-6.

---

## 5. Defense-in-Depth Security Architecture

```
User Request
    │
    ▼
[Session Startup Check]
    ├── Account permission check (rolsuper/rolcreaterole/rolcreatedb)
    │     └── Risk detected → pause, wait for user confirmation
    ├── Resource Group check (not default_group)
    │     └── Not configured → pause, wait for user confirmation
    └── Semantic model check
          └── Does not exist → hard stop, enter initialization guide
    │
    ▼
[Pre-Query 6 Gates]
    ├── Gate 1: Read-only mode (absolute prerequisite; no psql execution if not passed)
    ├── Gate 2: Statement timeout (auto-appended)
    ├── Gate 3: Semantic model ready (hard stop)
    ├── Gate 4: Target table authorized (hard stop)
    ├── Gate 5: SQL contains only SELECT (hard stop)
    └── Gate 6: Includes LIMIT (auto-append 50000)
    │
    ▼
[Execution Layer]
    ├── DB level: Read-only account (no write permissions as fallback)
    ├── DB level: Resource Group (concurrency/CPU/memory limits)
    └── Skill level: ≤5 psql calls per turn, SQL displayed for user audit
```

Each layer has independent protection; single-layer failure does not lead to overall loss of control.

---

## 6. Performance Optimization Recommendations

### 6.1 Merge Semantic Model Queries

```bash
# Recommended: fetch all semantics in 1 psql call, reducing network round trips
psql "service=adbpg" \
  -c "SELECT * FROM _agent_meta.tables;" \
  -c "SELECT * FROM _agent_meta.columns;" \
  -c "SELECT * FROM _agent_meta.joins;"
```

### 6.2 Use pg_service.conf Built-in Timeout

Write `statement_timeout` into `~/.pg_service.conf` instead of passing it on the command line each time:

```ini
options=-c default_transaction_read_only=on -c statement_timeout=60000
```

This way, Gate 2 passes directly without appending parameters each time.

### 6.3 Specify Timestamp Filenames for CSV Exports

```bash
psql "service=adbpg" \
  -c "\COPY (SELECT ...) TO '/tmp/export_$(date +%Y%m%d_%H%M%S).csv' CSV HEADER"
```

Facilitates auditing and version traceability; filename conflicts are also automatically avoided.
