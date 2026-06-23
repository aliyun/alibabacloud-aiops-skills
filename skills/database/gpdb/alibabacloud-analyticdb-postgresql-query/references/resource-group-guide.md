# Resource Group Isolation Configuration Guide

Through ADBPG's Resource Group feature, DBAs can set independent concurrency and resource limits for Agent accounts, preventing AI queries from impacting business operations at the database level.

---

## Why Resource Groups Are Needed

| Risk | How Resource Groups Mitigate |
|------|------------------------------|
| Agent initiates many concurrent queries in a short time | Concurrency limit; excess queries are rejected |
| A single complex query consumes excessive CPU/memory | Memory quota limit; over-limit queries are automatically terminated |
| Agent abnormal loop causes connection count surge | Connection limit; prevents connection pool exhaustion |

Even if Skill-level frequency controls fail, Resource Groups serve as a database-level "hard circuit breaker."

---

## Configuration Steps

### 1. Create a Resource Group

```sql
-- Create an Agent-dedicated resource group, limiting concurrency to 5
CREATE RESOURCE GROUP rg_agent WITH (
  concurrency = 5,
  cpu_rate_limit = 10,
  memory_limit = 10
);
```

| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| `concurrency` | Maximum concurrent queries | 3~5 (Agent maximum 5 queries per turn) |
| `cpu_rate_limit` | CPU percentage limit (%) | 10~20 |
| `memory_limit` | Memory percentage limit (%) | 10~15 |

### 2. Bind Agent Account to Resource Group

```sql
-- Assuming the Agent uses read-only account agent_reader
ALTER ROLE agent_reader RESOURCE GROUP rg_agent;
```

### 3. Verify Configuration

```sql
-- View resource group list
SELECT * FROM gp_toolkit.gp_resgroup_config;

-- View current user's resource group
SELECT rolname, rsgname
FROM pg_roles, pg_resgroup
WHERE pg_roles.rolresgroup = pg_resgroup.oid
AND rolname = 'agent_reader';
```

### 4. Runtime Monitoring

```sql
-- View resource group real-time usage
SELECT * FROM gp_toolkit.gp_resgroup_status;

-- View queued queries
SELECT * FROM gp_toolkit.gp_resgroup_status_per_host;
```

---

## Over-Limit Behavior

When Agent queries exceed resource group limits:

- **Concurrency exceeded**: New queries enter a wait queue; after exceeding `queuing_timeout` (default: unlimited wait; recommended: 30s), an error is returned
- **Memory exceeded**: Query is terminated with `ERROR: out of resource group memory`

### Recommended Queue Timeout Setting

```sql
-- Set maximum queue wait time to 30 seconds
ALTER RESOURCE GROUP rg_agent SET queuing_timeout = 30000;
```

This ensures Agent queries do not wait indefinitely; after timeout, the error is returned directly and the Agent can report to the user.

---

## Complete Configuration Example (DBA Initialization Checklist)

The following script completes all database-side configurations required by the Agent in sequence:

```sql
-- 1. Create resource group
CREATE RESOURCE GROUP rg_agent WITH (
  concurrency = 5,
  cpu_rate_limit = 10,
  memory_limit = 10
);
ALTER RESOURCE GROUP rg_agent SET queuing_timeout = 30000;

-- 2. Create read-only account
CREATE ROLE agent_reader WITH LOGIN PASSWORD 'xxx' NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- 3. Bind resource group
ALTER ROLE agent_reader RESOURCE GROUP rg_agent;

-- 4. Grant access only to business-required tables (minimum permissions; replace table names as needed)
GRANT SELECT ON public.orders, public.customers, public.products TO agent_reader;

-- 5. Create semantic model (see semantic-model-guide.md for details)
--    After creating _agent_meta schema and populating table/column/relationship metadata:
GRANT USAGE ON SCHEMA _agent_meta TO agent_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA _agent_meta TO agent_reader;
```

> **Complete semantic model creation script and population examples** are in [semantic-model-guide.md](semantic-model-guide.md).

---

## Relationship with Other Skill Security Layers

```
Agent Side                      Database Side
┌───────────────────┐       ┌───────────────────────┐
│ Semantic Model     │       │ _agent_meta Semantic   │
│ Constraints        │       │ Model                  │
│ Frequency Control  │       │ Resource Group         │
│ (5 calls/turn)     │       │  ├ concurrency = 5    │
│ SQL Whitelist      │──────→│  ├ cpu_rate_limit = 10 │
│ Statement Timeout  │       │  ├ memory_limit = 10   │
│ User Confirmation  │       │  └ queuing_timeout=30s │
└───────────────────┘       │ read_only = on         │
                            │ Read-Only Account      │
                            │ (SELECT only)          │
                            └───────────────────────┘
```

**Defense in Depth**: Semantic model limits query scope → Skill-level frequency control → Database-level Resource Group limits concurrency → Read-only mode rejects writes → Minimum-privilege account as fallback.
