# Semantic Model Configuration Guide

The Agent uses an in-database semantic model to understand queryable tables, columns, business meanings, and inter-table relationships. DBAs need to create the `_agent_meta` schema in the database and populate it with metadata. The Agent reads from it at runtime and **no longer uses `\dt` or `information_schema` to discover table structure**.

---

## Why a Semantic Model Is Needed

| Problem | How the Semantic Model Solves It |
|---------|----------------------------------|
| Agent sees all tables in the database and cannot distinguish which are business-relevant | The semantic model only registers business-needed tables; the Agent queries only within this scope |
| Agent doesn't understand the business meaning of columns and may use wrong fields in generated SQL | Each column includes a business description, role (dimension/measure), and synonyms |
| Agent doesn't know how to JOIN tables and may produce Cartesian products | The semantic model explicitly declares JOIN relationships and paths |
| Every query requires `\dt` + `\d` to discover structure, wasting query calls | One query to `_agent_meta` retrieves all context |
| Agent doesn't know how to calculate business KPIs | `metric_meta` defines metric expressions, dimensions, and filters |

> **Industry Reference**: dbt Semantic Layer, Snowflake Cortex Analyst, ADB MySQL Semantic View, Databricks Unity Catalog, and others all adopt a similar approach — adding a structured metadata layer between data and AI, improving text-to-SQL accuracy from ~40% to 85-95%.

---

## What Information the Agent Needs

The simplest way to build a semantic model is to provide the table DDL directly; the Agent will automatically parse and infer semantics.

### Input Methods (by Priority)

| Method | Operation | What the Agent Can Automatically Extract |
|--------|-----------|------------------------------------------|
| `\d+ table_name` output (Recommended) | Execute `\d+ orders` in psql, paste the output | Column names, types, constraints, COMMENTs, foreign key relationships |
| DDL with COMMENTs | Paste CREATE TABLE + COMMENT ON statements | Column names, types, constraints, business descriptions, foreign key relationships |
| Free-text description | Describe table names and column purposes in text | Only what the user explicitly provides |

The Agent will automatically infer roles from types and constraints in the DDL (primary/foreign key → identifier, numeric → measure, text/date → dimension), then display the inference results for your confirmation and supplementation.

### Information You May Need to Supplement

Content that cannot be automatically inferred from DDL; the Agent will ask you to confirm or supplement:

| Field | Description | Example |
|-------|-------------|---------|
| Business description | When DDL has no COMMENT, the Agent guesses from column names; you need to confirm | `order_date` → "Order date" ✅ |
| Business domain | Which business area the table belongs to | "Sales", "Finance", "Operations" |
| Synonyms | Alternative names users might use | amount → "revenue, income" |
| Aggregation method adjustment | Agent defaults to sum for numeric types; may need adjustment | price should be avg not sum |
| Sample values | Help understand the value range of dimension columns | "East, South, North" |
| Additional JOIN relationships | Associations that exist in practice but are not declared as foreign keys in DDL | orders.region_code → regions.code |
| Business metrics and filters | Derived/ratio/cumulative metrics and reusable filter definitions | profit, completion_rate, completed_only |

> **Tip**: All of the above are optional supplements. Even with only DDL, the Agent can generate a usable semantic model; adjustments can be made at any time.

---

## Creation Steps

### Step 1: Create the `_agent_meta` Schema

```sql
CREATE SCHEMA IF NOT EXISTS _agent_meta;
```

### Step 2: Create Metadata Tables

Five tables in total: `tables` (table-level), `columns` (column-level), `joins` (relationships), `metric_meta` (metrics-level), and `filters` (reusable filter definitions).

```sql
-- 1. Table-level metadata: which tables the Agent can query and their business meanings
CREATE TABLE _agent_meta.tables (
    table_schema    TEXT NOT NULL DEFAULT 'public',
    table_name      TEXT NOT NULL,
    display_name    TEXT,                -- Chinese display name, e.g., '订单主表'
    description     TEXT NOT NULL,       -- Business description
    business_domain TEXT,                -- Business domain label, e.g., 'Sales', 'Finance'
    PRIMARY KEY (table_schema, table_name)
);

COMMENT ON TABLE  _agent_meta.tables IS 'Registry of tables the Agent can query; unregistered tables are invisible';
COMMENT ON COLUMN _agent_meta.tables.display_name IS 'Chinese display name, e.g., 订单主表';
COMMENT ON COLUMN _agent_meta.tables.description IS 'Business description, e.g., "Stores all customer orders"';
COMMENT ON COLUMN _agent_meta.tables.business_domain IS 'Business domain label, e.g., "Sales", "Finance", "Operations"';

-- 2. Column-level metadata: business meaning, role, and synonyms for each column
CREATE TABLE _agent_meta.columns (
    table_schema       TEXT NOT NULL DEFAULT 'public',
    table_name         TEXT NOT NULL,
    column_name        TEXT NOT NULL,
    display_name       TEXT,                -- Chinese display name, e.g., '实付金额'
    column_role        TEXT NOT NULL CHECK (column_role IN ('dimension', 'measure', 'identifier')),
    data_type          TEXT,                -- Data type, e.g., NUMERIC, DATE, TEXT
    column_description TEXT,                -- Business description
    synonyms           TEXT[],              -- Synonym array, e.g., {revenue,income,GMV}
    agg_default        TEXT,                -- Default aggregation (measure only): sum / count / avg / min / max / count_distinct
    example_values     TEXT,                -- Sample values, e.g., 'East, South, North'
    PRIMARY KEY (table_schema, table_name, column_name)
    -- Note: ADBPG does not support triggers, therefore FOREIGN KEY constraints cannot be used
    -- Referential integrity between columns and tables is ensured at the application level (when DBA populates data)
);

COMMENT ON TABLE  _agent_meta.columns IS 'Column definitions and business semantics available to the Agent';
COMMENT ON COLUMN _agent_meta.columns.display_name IS 'Chinese display name, e.g., 实付金额';
COMMENT ON COLUMN _agent_meta.columns.column_role IS 'dimension=groupable/filterable, measure=aggregatable, identifier=primary/foreign key';
COMMENT ON COLUMN _agent_meta.columns.data_type IS 'Data type, e.g., NUMERIC, DATE, TEXT';
COMMENT ON COLUMN _agent_meta.columns.synonyms IS 'Synonym array, e.g., {revenue,income,GMV}';
COMMENT ON COLUMN _agent_meta.columns.agg_default IS 'Required for measure only: sum / count / avg / min / max / count_distinct';
COMMENT ON COLUMN _agent_meta.columns.example_values IS 'Optional sample values, e.g., East, South, North';

-- 3. Inter-table relationships: basis for Agent-generated JOINs
CREATE TABLE _agent_meta.joins (
    id                SERIAL PRIMARY KEY,
    left_schema       TEXT NOT NULL DEFAULT 'public',
    left_table        TEXT NOT NULL,
    left_column       TEXT NOT NULL,
    right_schema      TEXT NOT NULL DEFAULT 'public',
    right_table       TEXT NOT NULL,
    right_column      TEXT NOT NULL,
    join_type         TEXT NOT NULL DEFAULT 'LEFT',  -- LEFT / INNER
    relationship_type TEXT DEFAULT 'many_to_one',     -- many_to_one / one_to_many / one_to_one
    description       TEXT
);

COMMENT ON TABLE  _agent_meta.joins IS 'Inter-table JOIN relationship declarations; Agent can only use paths defined here';
COMMENT ON COLUMN _agent_meta.joins.join_type IS 'LEFT or INNER';
COMMENT ON COLUMN _agent_meta.joins.relationship_type IS 'Cardinality: many_to_one (fact→dimension), one_to_many, one_to_one';

-- 4. Business metrics definitions: derived/ratio/cumulative metrics beyond single-column aggregation
CREATE TABLE _agent_meta.metric_meta (
    metric_name    TEXT PRIMARY KEY,          -- e.g., 'profit', 'avg_order_value', 'completion_rate'
    business_desc  TEXT NOT NULL,             -- Business definition, e.g., 'Net profit = revenue - cost'
    metric_type    TEXT NOT NULL DEFAULT 'derived',  -- simple / ratio / derived / cumulative
    sql_expression TEXT NOT NULL,             -- SQL aggregate expression, referencing registered columns
    numerator      TEXT,                      -- For ratio type: numerator expression
    denominator    TEXT,                      -- For ratio type: denominator expression
    dimensions     TEXT[],                    -- Allowed dimensions, format: {schema.table.column, ...}
    filters        TEXT[],                    -- References to _agent_meta.filters.filter_name, e.g., {completed_only, high_value}
    owner          TEXT,                      -- Metric definition owner
    ai_hints       TEXT                       -- Extra instructions for Agent, e.g., 'Must aggregate by month'
);

COMMENT ON TABLE  _agent_meta.metric_meta IS 'Business metric definitions; Agent uses these for consistent KPI calculation';
COMMENT ON COLUMN _agent_meta.metric_meta.metric_type IS 'simple=single agg, ratio=numerator/denominator, derived=cross-metric, cumulative=windowed';
COMMENT ON COLUMN _agent_meta.metric_meta.sql_expression IS 'SQL aggregate expression referencing _agent_meta.columns, e.g., SUM(amount) - SUM(cost)';
COMMENT ON COLUMN _agent_meta.metric_meta.numerator IS 'Required for ratio type only; e.g., SUM(CASE WHEN status=''Completed'' THEN amount END)';
COMMENT ON COLUMN _agent_meta.metric_meta.denominator IS 'Required for ratio type only; e.g., SUM(amount)';
COMMENT ON COLUMN _agent_meta.metric_meta.dimensions IS 'Allowed dimension references, e.g., {public.orders.region, public.customers.level}';
COMMENT ON COLUMN _agent_meta.metric_meta.filters IS 'References to _agent_meta.filters.filter_name, e.g., {completed_only, high_value}';
COMMENT ON COLUMN _agent_meta.metric_meta.ai_hints IS 'Extra instructions for Agent, e.g., Must aggregate by month';

-- 5. Reusable filter definitions: pre-defined WHERE or FILTER(WHERE) conditions
CREATE TABLE _agent_meta.filters (
    filter_name    TEXT PRIMARY KEY,          -- e.g., 'completed_only', 'high_value'
    description    TEXT NOT NULL,             -- Business description, e.g., 'Completed orders only'
    sql_fragment   TEXT NOT NULL,             -- SQL boolean expression, e.g., status = 'Completed'
    filter_scope   TEXT NOT NULL DEFAULT 'where',  -- 'where' = global WHERE clause, 'measure' = per-aggregate FILTER clause
    owner          TEXT                       -- Filter owner
);

COMMENT ON TABLE  _agent_meta.filters IS 'Reusable filter definitions; referenced by metric_meta.filters';
COMMENT ON COLUMN _agent_meta.filters.sql_fragment IS 'SQL boolean expression, e.g., status = ''Completed'', amount > 10000';
COMMENT ON COLUMN _agent_meta.filters.filter_scope IS 'where=inject into WHERE clause (global), measure=inject into FILTER(WHERE) clause (per aggregate, DuckDB-style)';
```

### Step 3: Populate the Semantic Model

Example using an "orders + customers + products" scenario:

```sql
-- === Register Tables ===
INSERT INTO _agent_meta.tables (table_schema, table_name, display_name, description, business_domain) VALUES
('public', 'orders',    '订单主表', 'Customer orders table, one row per order', 'Sales'),
('public', 'customers', '客户主表', 'Customer master data table',              'Sales'),
('public', 'products',  '商品目录', 'Product catalog table with price and category info', 'Products');

-- === Register Columns ===
-- orders table
INSERT INTO _agent_meta.columns (table_schema, table_name, column_name, display_name, column_role, data_type, column_description, synonyms, agg_default, example_values) VALUES
('public','orders','order_id',     '订单ID',    'identifier', 'BIGINT',  'Unique order identifier',               NULL,                NULL,    NULL),
('public','orders','customer_id',  '客户ID',    'identifier', 'BIGINT',  'Customer ID (references customers)',    NULL,                NULL,    NULL),
('public','orders','product_id',   '商品ID',    'identifier', 'BIGINT',  'Product ID (references products)',      NULL,                NULL,    NULL),
('public','orders','order_date',   '下单日期',  'dimension',  'DATE',    'Order date',                            '{order time}',      NULL,    NULL),
('public','orders','amount',       '订单金额',  'measure',    'NUMERIC', 'Order amount (currency unit)',          '{revenue,income}',  'sum',   NULL),
('public','orders','quantity',     '购买数量',  'measure',    'INTEGER', 'Purchase quantity',                     '{count,items}',     'sum',   NULL),
('public','orders','status',       '订单状态',  'dimension',  'TEXT',    'Order status',                          NULL,                NULL,    'Completed, Pending, Cancelled'),
('public','orders','region',       '订单区域',  'dimension',  'TEXT',    'Order region',                          '{area,territory}',  NULL,    'East, South, North, Southwest');

-- customers table
INSERT INTO _agent_meta.columns (table_schema, table_name, column_name, display_name, column_role, data_type, column_description, synonyms, agg_default, example_values) VALUES
('public','customers','id',         '客户ID',      'identifier', 'BIGINT',  'Unique customer identifier',            NULL,                NULL,    NULL),
('public','customers','name',       '客户名称',    'dimension',  'TEXT',    'Customer name',                         '{customer name}',   NULL,    NULL),
('public','customers','level',      '客户等级',    'dimension',  'TEXT',    'Customer tier',                         '{membership level,VIP tier}', NULL, 'Regular, Silver, Gold, Diamond'),
('public','customers','city',       '客户城市',    'dimension',  'TEXT',    'Customer city',                         '{city}',            NULL,    NULL),
('public','customers','created_at', '注册日期',    'dimension',  'TIMESTAMP','Customer registration date',           '{registration date}',NULL,   NULL);

-- products table
INSERT INTO _agent_meta.columns (table_schema, table_name, column_name, display_name, column_role, data_type, column_description, synonyms, agg_default, example_values) VALUES
('public','products','id',         '商品ID',      'identifier', 'BIGINT',  'Unique product identifier',             NULL,                NULL,    NULL),
('public','products','name',       '商品名称',    'dimension',  'TEXT',    'Product name',                          '{product name}',    NULL,    NULL),
('public','products','category',   '商品类别',    'dimension',  'TEXT',    'Product category',                      '{type,class}',      NULL,    'Electronics, Home, Apparel'),
('public','products','price',      '单价',        'measure',    'NUMERIC', 'Unit price (currency unit)',            '{unit price,pricing}','avg', NULL);

-- === Register JOIN Relationships ===
INSERT INTO _agent_meta.joins (left_table, left_column, right_table, right_column, join_type, relationship_type, description) VALUES
('orders', 'customer_id', 'customers', 'id', 'LEFT', 'many_to_one', 'Order references customer'),
('orders', 'product_id',  'products',  'id', 'LEFT', 'many_to_one', 'Order references product');

-- === Register Filters ===
INSERT INTO _agent_meta.filters VALUES
('completed_only',    'Completed orders only',                    'status = ''Completed''',       'where',   'ops_team'),
('high_value',        'High-value orders (amount > 10000)',       'amount > 10000',              'where',   'finance_team'),
('completed_measure', 'Filter for completed orders per measure',  'status = ''Completed''',       'measure', 'ops_team');

-- === Register Business Metrics ===
-- Derived metric: profit = revenue - cost
INSERT INTO _agent_meta.metric_meta VALUES
('profit', 'Net profit = revenue - cost', 'derived',
 'SUM(amount) - SUM(CASE WHEN discount > 0 THEN amount * discount ELSE 0 END)',
 NULL, NULL,
 '{public.orders.region, public.orders.status, public.customers.level}',
 '{completed_only}',
 'finance_team',
 'Must aggregate by region or status; avoid grouping by order_id'),

-- Ratio metric: order completion rate
('completion_rate', 'Order completion rate = completed orders / all orders', 'ratio',
 'SUM(CASE WHEN status = ''Completed'' THEN 1 ELSE 0 END)::numeric / COUNT(*)',
 'SUM(CASE WHEN status = ''Completed'' THEN 1 ELSE 0 END)',
 'COUNT(*)',
 '{public.orders.region, public.customers.level}',
 '{completed_measure}',
 'ops_team',
 NULL),

-- Cumulative metric: running total of order amount
('cumulative_revenue', 'Cumulative (running) revenue by order date', 'cumulative',
 'SUM(SUM(amount)) OVER (ORDER BY order_date ROWS UNBOUNDED PRECEDING)',
 NULL, NULL,
 '{public.orders.order_date, public.orders.region}',
 NULL,
 'finance_team',
 'Requires ORDER BY order_date in the query');
```

### Step 4: Grant Permissions

```sql
-- Grant the Agent account read access to the semantic model (all five tables)
GRANT USAGE ON SCHEMA _agent_meta TO agent_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA _agent_meta TO agent_reader;
```

---

## Maintenance Operations

### Adding a New Table

```sql
-- 1. Register table
INSERT INTO _agent_meta.tables (table_schema, table_name, display_name, description, business_domain) VALUES
('public', 'new_table', '新表', 'Business description of the table', 'Business domain');

-- 2. Register columns (one row per column)
INSERT INTO _agent_meta.columns (table_schema, table_name, column_name, display_name, column_role, data_type, column_description, synonyms, agg_default, example_values) VALUES
('public', 'new_table', 'col1', '列1', 'dimension', 'TEXT', 'Column description', '{synonym}', NULL, NULL);

-- 3. Register JOIN relationships if applicable
INSERT INTO _agent_meta.joins (left_table, left_column, right_table, right_column, join_type, relationship_type, description)
VALUES ('new_table', 'fk_col', 'other_table', 'pk_col', 'LEFT', 'many_to_one', 'Relationship description');

-- 4. Don't forget to grant access to the actual data table
GRANT SELECT ON public.new_table TO agent_reader;
```

### Removing a Table

```sql
DELETE FROM _agent_meta.joins   WHERE left_table = 'old_table' OR right_table = 'old_table';
DELETE FROM _agent_meta.columns WHERE table_name = 'old_table';
DELETE FROM _agent_meta.tables  WHERE table_name = 'old_table';
-- Also remove any metrics that reference the removed table
DELETE FROM _agent_meta.metric_meta WHERE sql_expression LIKE '%old_table%';
-- Remove any filters that reference columns from the removed table
DELETE FROM _agent_meta.filters WHERE sql_fragment LIKE '%old_table%';

REVOKE SELECT ON public.old_table FROM agent_reader;
```

### Adding / Modifying Column Definitions

```sql
-- Add column
INSERT INTO _agent_meta.columns (table_schema, table_name, column_name, display_name, column_role, data_type, column_description, synonyms, agg_default, example_values) VALUES
('public', 'orders', 'discount', '折扣金额', 'measure', 'NUMERIC', 'Discount amount', '{discount,coupon}', 'sum', NULL);

-- Modify column description
UPDATE _agent_meta.columns
SET column_description = 'New business description', synonyms = '{new_synonym}'
WHERE table_name = 'orders' AND column_name = 'amount';
```

### Managing Business Metrics

```sql
-- Add a new metric
INSERT INTO _agent_meta.metric_meta VALUES
('avg_order_value', 'Average order value per customer', 'simple',
 'AVG(amount)', NULL, NULL,
 '{public.orders.region, public.customers.level}',
 NULL, 'ops_team', NULL);

-- Modify a metric definition
UPDATE _agent_meta.metric_meta
SET business_desc = 'Updated business definition',
    sql_expression = 'SUM(CASE WHEN status = ''Completed'' THEN amount END)'
WHERE metric_name = 'profit';

-- Remove a metric
DELETE FROM _agent_meta.metric_meta WHERE metric_name = 'old_metric';
```

**metric_type selection guide**:

| When to use | metric_type | Example |
|-------------|-------------|---------|
| Single column + single aggregation | simple | `AVG(price)`, `COUNT(*)` |
| Two metrics as numerator/denominator | ratio | Completion rate = completed / total |
| Arithmetic across other metrics | derived | Profit = revenue - cost |
| Running total or time-windowed | cumulative | MTD revenue |

### Managing Filters

```sql
-- Add a new filter (scope=where: injected into WHERE clause)
INSERT INTO _agent_meta.filters VALUES
('recent_orders', 'Orders from the last 30 days',
 "order_date >= CURRENT_DATE - INTERVAL '30 days'",
 'where', 'ops_team');

-- Add a measure-scope filter (scope=measure: injected into FILTER(WHERE) clause)
INSERT INTO _agent_meta.filters VALUES
('pending_measure', 'Pending orders per measure',
 'status = ''Pending''',
 'measure', 'ops_team');

-- Link a filter to a metric
UPDATE _agent_meta.metric_meta
SET filters = array_append(filters, 'recent_orders')
WHERE metric_name = 'profit';

-- Remove a filter from a metric
UPDATE _agent_meta.metric_meta
SET filters = array_remove(filters, 'completed_only')
WHERE metric_name = 'profit';

-- Delete a filter entirely (must remove from all metrics first)
UPDATE _agent_meta.metric_meta SET filters = array_remove(filters, 'old_filter');
DELETE FROM _agent_meta.filters WHERE filter_name = 'old_filter';
```

**filter_scope selection guide**:

| When to use | filter_scope | SQL generated by Agent | Example |
|-------------|-------------|----------------------|---------|
| Filter applies to entire query | where | `WHERE filter_expr AND ...` | "Only completed orders" |
| Filter applies to specific aggregate | measure | `SUM(x) FILTER (WHERE filter_expr)` | "Completed revenue vs total revenue in one query" |

---

## Verification

After populating, run the following queries to confirm the semantic model content is correct:

```sql
-- View registered tables
SELECT table_name, display_name, description, business_domain FROM _agent_meta.tables ORDER BY table_name;

-- View column definitions for a specific table
SELECT column_name, display_name, column_role, data_type, column_description, agg_default, synonyms
FROM _agent_meta.columns
WHERE table_name = 'orders'
ORDER BY column_name;

-- View JOIN relationships
SELECT left_table, left_column, right_table, right_column, join_type, relationship_type, description
FROM _agent_meta.joins;

-- View business metrics
SELECT metric_name, business_desc, metric_type, sql_expression, dimensions, filters, owner
FROM _agent_meta.metric_meta
ORDER BY metric_name;

-- View filter definitions
SELECT filter_name, description, sql_fragment, filter_scope, owner
FROM _agent_meta.filters
ORDER BY filter_name;

-- View metrics with their resolved filters
SELECT m.metric_name, m.business_desc, m.filters,
       f.filter_name, f.description, f.sql_fragment, f.filter_scope
FROM _agent_meta.metric_meta m
LEFT JOIN LATERAL unnest(m.filters) AS f_name(filter_name)
LEFT JOIN _agent_meta.filters f ON f.filter_name = f_name.filter_name
ORDER BY m.metric_name, f.filter_name;
```

---

## Relationship with Other Security Layers

```
DBA Configuration                        Agent Runtime
┌──────────────────────────────┐     ┌──────────────────────────────┐
│ 1. Create read-only account  │     │ Query _agent_meta for        │
│    + Resource Group          │     │ semantic model               │
│ 2. GRANT SELECT only on      │────→│ Generate SQL only within     │
│    business tables           │     │ semantic model scope         │
│ 3. Create _agent_meta and    │     │ Out of scope → reject and    │
│    populate semantic model   │     │ prompt DBA to extend         │
│ 4. GRANT _agent_meta         │     │ SQL review + LIMIT + timeout │
│    read access               │     └──────────────────────────────┘
└──────────────────────────────┘
```

**Defense in Depth**: Semantic model limits scope → Filters ensure consistent WHERE/FILTER injection → Metric meta ensures consistent KPI calculation → Resource Group limits resources → Read-only mode rejects writes → Minimum-privilege account as fallback.
