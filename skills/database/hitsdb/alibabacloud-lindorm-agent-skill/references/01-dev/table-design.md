# Lindorm SQL Table Creation Statement Guide

This document provides a complete guide to Lindorm wide table creation statements, including syntax, best practices, and advanced features.

## Data Types

### Data Type Lookup Rules

When creating tables with the Lindorm wide table engine, you need to understand the supported data types. The Lindorm wide table engine supports basic data types, JSON data types, and spatial data types.

1. If the data type mentioned by the user is not within the supported data types of the Lindorm wide table engine, tell the user which data types are supported and provide relevant documentation links.
2. Prefer selecting data types from the table below.
3. If the data type is not in the table below, look up the official documentation:
   - **Basic data types**: https://help.aliyun.com/zh/lindorm/developer-reference/basic-data-types
   - **JSON data type**: https://help.aliyun.com/zh/lindorm/developer-reference/json-data-type
   - **Spatial data type**: https://help.aliyun.com/zh/lindorm/developer-reference/spatial-data-type-1
4. If the data type is still not supported, tell the user that the data type is not supported or ask them to contact technical support.

### Basic Data Types

| Type | Byte Length | Description | Java Mapping | Value Range / Precision |
|------|----------|------|-----------|----------------|
| BOOLEAN | 1 byte | Boolean type | java.lang.Boolean | true / false |
| TINYINT | 1 byte | 8-bit exact numeric value | java.lang.Byte | -128 ~ 127 (signed) |
| SMALLINT | 2 bytes | 16-bit exact numeric value | java.lang.Short | -32768 ~ 32767 |
| INTEGER | 4 bytes | 32-bit exact numeric value | java.lang.Integer | -2^31 ~ 2^31-1 |
| BIGINT | 8 bytes | 64-bit exact numeric value | java.lang.Long | -2^63 ~ 2^63-1 |
| FLOAT | 4 bytes | Single-precision floating-point number | java.lang.Float | About 7 significant digits |
| DOUBLE | 8 bytes | Double-precision floating-point number | java.lang.Double | About 15 to 17 significant digits, represented in scientific notation |
| DECIMAL(precision, scale) | Variable | High-precision decimal | java.math.BigDecimal | precision: [1,38], scale: [0,precision] |
| VARCHAR | Variable | Variable-length string | java.lang.String | Up to 2 MB, supports Chinese characters |
| CHAR(n) | n bytes | Fixed-length string | java.lang.String | Fixed length n. Missing characters are automatically padded with spaces. |
| BINARY(n) | n bytes | Fixed-length binary | byte[] | Fixed n bytes. Missing bytes are padded with 0, and extra bytes are truncated. |
| VARBINARY | Variable | Variable-length binary | byte[] | Can only be the last column when used as a primary key |
| DATE | 4 bytes | Date only, without time | java.sql.Date | YYYY-MM-DD, **not recommended** because time zone conversion is error-prone |
| TIME | 4 bytes | Time | java.sql.Time | HH:mm:ss, affected by time zone |
| TIMESTAMP | 8 bytes | Timestamp | java.sql.Timestamp | 0001-01-01 00:00:00 ~ 9999-12-31 23:59:59 |

**Important notes**:
- **TIMESTAMP**: The maximum value supported by Lindorm is `9999-12-31 23:59:59`, while MySQL supports only up to `2038-01-19 03:14:07`.
- **DECIMAL**: Suitable for high-precision scenarios such as amounts. For monitoring scenarios where precision requirements are not high, FLOAT or DOUBLE is recommended.
- **DATE/TIME**: Date errors can easily occur during time zone conversion. Avoid using them.

### JSON Data Type

**Applicable engine**: Supported only by the wide table engine. Version 2.6.2 or later is required.

**Limit**: Primary key columns do not support the JSON type.

**Table creation syntax**:
```sql
-- Specify a JSON column when creating a table.
CREATE TABLE tb (
    p1 INT,
    c1 VARCHAR,
    c2 JSON,
    PRIMARY KEY(p1)
);

-- Add a JSON column to an existing table.
ALTER TABLE tb ADD c3 JSON;
```

### Type Usage Recommendations

- **Primary key columns**: VARCHAR or BIGINT is recommended. VARBINARY can only be the last primary key column.
- **Timestamp**: Prefer TIMESTAMP, which has a larger range, or use BIGINT in milliseconds.
- **Large text**: Use VARCHAR, up to 2 MB.
- **Binary data**: Use BINARY(n) or VARBINARY.
- **High-precision numeric values**: Use DECIMAL, such as for amounts.
- **General numeric values**: Use INTEGER, BIGINT, FLOAT, or DOUBLE.
- **Avoid**: DATE and TIME because of time zone issues.

## Basic Syntax

**Notes**:
- Answer user questions only based on content explicitly documented in this Skill. Do not infer, associate, or generate SQL syntax, parameters, features, or configurations that are not present in the documentation.
- If the documentation does not contain relevant information, clearly tell the user "This content is not included in the current documentation" and guide the user to official documentation.
- Generated code examples must be based on templates in the documentation. Parameters and syntax must be consistent with the documentation.

### CREATE TABLE Syntax

```sql
CREATE TABLE [ IF NOT EXISTS ] table_identifier
'('
  column_definition
  ( ',' column_definition )*
  ',' PRIMARY KEY '(' primary_key ')'
  ( ',' {KEY|INDEX} [index_identifier]
    [ USING index_method_definition ]
    [ INCLUDE column_identifier ( ',' column_identifier )* ]
    [ WITH index_options ]
  )*
')'
[ WITH table_options ]
```

**Syntax element descriptions:**

| Syntax Element | Description                                                                    |
|---------|-----------------------------------------------------------------------|
| column_definition | `column_identifier data_type [ NOT NULL ] [ DEFAULT default_value ] ` |
| primary_key | `column_identifier [ ',' column_identifier (ASC\|DESC)]`              |
| index_method_definition | `{ KV \| SEARCH }`                                                    |
| index_options | `'(' option_definition (',' option_definition )*')'`                  |
| table_options | `'(' option_definition (',' option_definition )* ')'`                 |
| option_definition | `option_identifier '=' string_literal`                                |

### DEFAULT Clause

Column definitions support setting default values through the DEFAULT clause.

**Limits:**
- The default value can only be a constant expression of the column type or the no-argument function `NOW()`.
- It cannot be set to NULL.

**Example:**
```sql
CREATE TABLE orders (
  id VARCHAR NOT NULL,
  status INTEGER DEFAULT -1,
  create_time TIMESTAMP DEFAULT NOW(),
  remark VARCHAR DEFAULT 'pending',
  PRIMARY KEY(id)
);
```

### Naming Rules

**Table name (table_identifier):**
- Can contain digits, uppercase and lowercase English letters, half-width periods (.), hyphens (-), and underscores (_).
- Cannot start with a half-width period (.) or hyphen (-).
- Length is 1 to 255 characters.

**Column name (column_identifier):**
- Can contain digits, uppercase and lowercase English letters, half-width periods (.), hyphens (-), and underscores (_).
- System reserved keywords are not allowed.
- Length cannot exceed 255 bytes.

### Basic Table Creation Examples

```sql
-- Basic table.
CREATE TABLE orders (
  channel VARCHAR NOT NULL,
  id VARCHAR NOT NULL,
  ts TIMESTAMP NOT NULL,
  status VARCHAR,
  location VARCHAR,
  PRIMARY KEY(channel, id, ts)
);

-- Table with table properties.
CREATE TABLE orders (
  channel VARCHAR NOT NULL,
  id VARCHAR NOT NULL,
  ts TIMESTAMP NOT NULL,
  status VARCHAR,
  PRIMARY KEY(channel, id, ts)
) WITH (
  COMPRESSION = 'ZSTD',
  TTL = '86400'
);
```

## Primary Key Design

### Primary Key Characteristics

- **Immutable**: The primary key is determined when the table is created. After table creation, primary key columns cannot be added, deleted, reordered, or changed to another data type.
- **Uniqueness**: All primary key columns together form the RowKey, which is unique within a table.
- **Clustered index**: Data is stored in primary key order and follows the leftmost prefix principle.

### Primary Key Limits

- The maximum length of a single primary key column is 2 KB.
- The total length of all primary key columns cannot exceed 30 KB.
- The maximum length of a single non-primary-key column cannot exceed 2 MB.

### Primary Key Design Best Practices

#### Avoid Hotspot Issues

```sql
-- Incorrect example: an incremental primary key causes write hotspots.
CREATE TABLE logs (
  timestamp BIGINT NOT NULL,
  message VARCHAR,
  PRIMARY KEY(timestamp)
);

-- Correct example: use HASH sharding.
CREATE TABLE logs (
  timestamp BIGINT NOT NULL,
  hostname VARCHAR NOT NULL,
  message VARCHAR,
  PRIMARY KEY(hash32(timestamp), timestamp, hostname)
);
```

#### Primary Key Design Principles

1. **Make the first primary key column as scattered as possible**: Using the same prefix is not recommended.
2. **Avoid auto-increment data**: For example, do not use a timestamp column as the first column.
3. **Avoid enum values**: For example, do not use order_type as the first column.
4. **Number of primary key columns**: It is recommended to use 1 to 3 columns.
5. **Primary key value length**: Keep values short whenever possible and use fixed-length types.

#### Common Scenario Designs

**Log and time series data:**
```sql
-- Query data of a specific metric on a specific machine within a time range.
CREATE TABLE logs (
  hostname VARCHAR NOT NULL,
  log_event VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  content VARCHAR,
  PRIMARY KEY(hostname, log_event, timestamp)
);

-- Query latest data in descending order.
CREATE TABLE logs (
  hostname VARCHAR NOT NULL,
  log_event VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  content VARCHAR,
  PRIMARY KEY(hostname, log_event, timestamp DESC)
);

-- When the time dimension has a large data volume, use buckets for sharding.
CREATE TABLE logs (
  bucket BIGINT NOT NULL,
  timestamp BIGINT NOT NULL,
  hostname VARCHAR NOT NULL,
  log_event VARCHAR NOT NULL,
  content VARCHAR,
  PRIMARY KEY(bucket, timestamp, hostname, log_event)
);
-- During writes: bucket = timestamp % numBuckets
```

**Transaction data:**
```sql
-- Query by seller.
CREATE TABLE seller_orders (
  seller_id VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  order_number VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(seller_id, timestamp, order_number)
);

-- Query by buyer.
CREATE TABLE buyer_orders (
  buyer_id VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  order_number VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(buyer_id, timestamp, order_number)
);

-- Query by order number.
CREATE TABLE order_index (
  order_number VARCHAR NOT NULL,
  seller_id VARCHAR,
  buyer_id VARCHAR,
  PRIMARY KEY(order_number)
);
```

## HASH Primary Key Sharding

Use HASH functions to distribute data across different shards, avoiding data skew and hotspot issues.

### Supported HASH Algorithms

| Algorithm | Description |
|------|------|
| hash8 | 8-bit HASH with the lowest storage overhead |
| hash32 | 32-bit HASH, consuming an additional 4 bytes for each keyValue pair |
| hash64 | 64-bit HASH with the highest storage overhead |

### Usage Examples

```sql
-- Use HASH on a single primary key column.
CREATE TABLE t1 (
  p1 BIGINT,
  p2 INTEGER,
  c1 INTEGER,
  c2 VARCHAR,
  PRIMARY KEY(hash32(p1), p1, p2)
);

-- Use HASH on multiple primary key columns.
CREATE TABLE t2 (
  p1 BIGINT,
  p2 INTEGER,
  c1 INTEGER,
  c2 VARCHAR,
  PRIMARY KEY(hash8(p1, p2), p1, p2)
);
```

### Notes

- The HASH function expression must be placed at the beginning of the primary key.
- Primary key columns that already use a HASH algorithm cannot be modified.
- Values of all primary key columns that use the HASH algorithm must be specified during queries.
- HASH columns support only equality queries and do not support range queries.
- After primary key HASH sharding is used, data import through bulkload is not supported.

## Table Properties (WITH Clause)

### Common Table Properties

| Property | Type | Description |
|------|------|------|
| COMPRESSION | STRING | Compression algorithm: SNAPPY, ZSTD, or LZ4. The default value is ZSTD. |
| TTL | INT | Data validity period in seconds. The default value is empty, which means no expiration. |
| NUMREGIONS | INT | Number of pre-split regions |
| STARTKEY / ENDKEY | Same as the first primary key column type | Start and end keys for pre-splitting |
| SPLITKEYS | Same as the first primary key column type | Split points for pre-splitting |
| DYNAMIC_COLUMNS | STRING | Whether to enable dynamic columns: 'true' or 'false' |
| MUTABILITY | STRING | Index write mode, such as IMMUTABLE or MUTABLE_LATEST |
| CONSISTENCY | STRING | Consistency level: eventual (default) or strong |

### Examples

```sql
-- Set compression and TTL.
CREATE TABLE logs (
  id VARCHAR NOT NULL,
  content VARCHAR,
  PRIMARY KEY(id)
) WITH (
  COMPRESSION = 'ZSTD',
  TTL = '2592000'  -- 30 days
);

-- Set pre-splitting.
CREATE TABLE orders (
  id VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(id)
) WITH (
  NUMREGIONS = '16',
  STARTKEY = 'a',
  ENDKEY = 'z'
);
```

## Dynamic Columns

Dynamic columns allow columns that are not explicitly defined during table creation to be dynamically written at runtime.

### Enable Dynamic Columns

```sql
-- Enable during table creation.
CREATE TABLE t_dynamic (
  p1 INT,
  c1 INT,
  c2 VARCHAR,
  PRIMARY KEY(p1)
) WITH (DYNAMIC_COLUMNS = 'true');

-- Enable for an existing table.
ALTER TABLE t_dynamic SET 'DYNAMIC_COLUMNS' = 'true';
```

### Write Dynamic Columns

The data type of dynamic columns is VARBINARY, which is a byte array.

```sql
-- SQL text write. The value is a HexString.
UPSERT INTO t_dynamic (p1, c2, c3) VALUES (1, '1', '41');

-- Use x'' syntax to specify a HexString. Requires SQL engine 2.6.8 or later.
UPSERT INTO t_dynamic (p1, c4) VALUES (3, x'ef0011');
```

### Query Dynamic Columns

```sql
-- Explicitly specify dynamic columns.
SELECT p1, c2, c3, c4 FROM t_dynamic WHERE p1 = 1;

-- Use SELECT *. LIMIT must be added.
SELECT * FROM t_dynamic LIMIT 10;
```

## Wildcard Columns

Wildcard columns implement dynamic column writes for multiple data types and resolve the limitation that dynamic columns support only VARBINARY.

### Supported Wildcards

| Wildcard | Description |
|--------|------|
| * | Matches any character sequence, including an empty sequence |
| ? | Matches any single character |

### Usage Example

```sql
-- Create a table with wildcard columns.
CREATE TABLE tb (
  pk INTEGER,
  c1 VARCHAR,
  `c2*` BIGINT,
  `c3*` VARCHAR,
  PRIMARY KEY(pk)
) WITH (wildcard_column = 'c2*,c3*');

-- Write data.
UPSERT INTO tb(pk, c1, c2, c21, c22, c31) VALUES (1, 'a1', 2, 21, 22, 'c3');
```

### Limits

- Wildcard columns cannot be used as primary keys.
- SELECT * queries must add LIMIT.
- Only search indexes can be created for wildcard columns. Secondary indexes are not supported.
- Querying data by wildcard column names is not supported. Actual column names must be used.

## Indexes Created During Table Creation

Create indexes in CREATE TABLE statements by using KEY or INDEX clauses.

### Syntax

```sql
CREATE TABLE table_name (
  column_definitions,
  PRIMARY KEY(pk_columns),
  {KEY|INDEX} [index_name]
    [ USING { KV | SEARCH } ]
    [ INCLUDE (columns) ]
    [ WITH (index_options) ]
);
```

### Index Types

| Type | Keyword | Description |
|------|--------|------|
| Secondary index | KV (default) | Suitable for non-primary-key matching scenarios |
| Search index | SEARCH | Suitable for multidimensional queries, analyzer queries, and fuzzy queries |

### Redundant Column Settings

When creating indexes during table creation, you can set redundant columns through INCLUDE or WITH (INDEX_COVERED_TYPE):

```sql
-- Explicitly specify redundant columns.
CREATE TABLE sensor (
    device_id VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    time TIMESTAMP NOT NULL,
    temperature DOUBLE,
    humidity BIGINT,
    PRIMARY KEY(device_id, region, time),
    KEY (temperature, time) INCLUDE (humidity)
);

-- Redundantly store all defined columns.
CREATE TABLE sensor (
    device_id VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    time TIMESTAMP NOT NULL,
    temperature DOUBLE,
    humidity BIGINT,
    PRIMARY KEY(device_id, region, time),
    KEY (temperature, time) WITH (INDEX_COVERED_TYPE = 'COVERED_ALL_COLUMNS_IN_SCHEMA')
);
```

### Examples

```sql
-- Create a table and a secondary index at the same time.
CREATE TABLE orders (
  order_id VARCHAR NOT NULL,
  user_id VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(order_id),
  INDEX idx_user USING KV (user_id) INCLUDE (amount)
);

-- Create a table and a search index at the same time.
CREATE TABLE products (
  id VARCHAR NOT NULL,
  name VARCHAR,
  description VARCHAR,
  PRIMARY KEY(id),
  INDEX idx_search USING SEARCH (name, description)
);
```

## CREATE INDEX Syntax

Syntax for creating an index separately.

```sql
CREATE INDEX [IF NOT EXISTS] [index_name]
  [ USING { KV | SEARCH | COLUMNAR } ]
  ON table_name (index_key_expression)
  [ INCLUDE (columns) ]
  [ { ASYNC | SYNC } ]
  [ WITH (index_options) ];
```

### Index Types

| Parameter | Index Type | Description |
|------|----------|------|
| KV | Secondary index | Default type. Each table supports up to 3 secondary indexes. |
| SEARCH | Search index | Full-text search. Each table supports up to 1 search index. |
| COLUMNAR | Columnar index | Analytical computing. Each table supports up to 1 columnar index. |

### Columnar Index Enablement Conditions

**Legacy columnar index** (default, officially released):

| Engine | Purpose |
|------|------|
| Wide table engine | Source data storage |
| LindormDFS | File storage, version >= 4.0.0 |
| Compute engine | Executes analytical queries |

**Enablement instructions**:

1. **Enable the Lindorm compute engine**.
2. **Purchase compute resources** for data synchronization from the wide table engine to the compute engine.

**Console enablement path**:

1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/).
2. On the instance list page, click the **target instance ID**.
3. In the left-side navigation pane, choose **Wide Table Engine**.
4. Click the **Columnar Index** tab and click **Enable Now**.
5. In the dialog box, click **OK**.

**Columnar index creation example** (legacy version, officially released):

```sql
-- Create a columnar index. Legacy version, with synchronization latency of about 15 minutes.
CREATE INDEX idx_columnar USING COLUMNAR ON my_table(
  pk0, pk1, pt_d, col0, col1
)
PARTITION BY ENUMERABLE (pt_d, bucket(16, pk0))
WITH (
  `lindorm_columnar.user.index.database` = 'my_index_db',  -- Database name of the columnar index.
  `lindorm_columnar.user.index.table` = 'my_index_tbl'     -- Table name of the columnar index.
);
```

**Query a columnar index**:

```sql
-- Use HINT to specify that the query uses the columnar index.
SELECT /*+ _use_ldps_(cg_name), _columnar_index_ */
  pk1, SUM(col0)
FROM my_db.my_table
WHERE pt_d = '2024-01-01'
GROUP BY pk1;
```

> **Note**: `cg_name` is the name of the compute engine OLAP resource group.

---

### New Columnar Index Version (Real-time Synchronization)

> ⚠️ **If second-level synchronization latency is required**, you can use the new columnar index version, which is currently in **invited preview**.

**Comparison between the legacy and new versions**:

| Feature | Legacy Columnar Index | New Columnar Index |
|------|-------------|-------------|
| **Synchronization latency** | 15 minutes | **Real-time, second-level** |
| **Data freshness** | High latency | Near real-time |
| **Scenario** | Offline analytics | Real-time analytics |
| **Version status** | Officially released | Invited preview |

**Application method**:
- Contact Lindorm technical support to apply for use. You can submit a ticket on the Alibaba Cloud official website or contact your account manager.

**Engine version requirements for the new version**:

| Engine | Version Requirement | Purpose |
|------|---------|------|
| Wide table engine | >= 2.8.6 | Source data storage |
| LTS | >= 3.9.1 | Real-time log subscription |
| Columnar engine | >= 3.10.15 | Index data storage |
| Compute engine | - | Executes analytical queries |

> **Key difference**: The new columnar index version depends on the **columnar engine** to store index data and supports second-level synchronization. The legacy version does not depend on the columnar engine and has synchronization latency of about 15 minutes.

**New version creation syntax**:

Add the `lindorm_columnar.user.index.type = 'LCE'` property:

```sql
-- Create a columnar index. New version with second-level synchronization.
CREATE INDEX idx_columnar USING COLUMNAR ON my_table(
  pk0, pk1, pt_d, col0, col1
)
PARTITION BY ENUMERABLE (pt_d, bucket(16, pk0))
WITH (
  `lindorm_columnar.user.index.database` = 'my_index_db',  -- Database name of the columnar index.
  `lindorm_columnar.user.index.table` = 'my_index_tbl',     -- Table name of the columnar index.
  `lindorm_columnar.user.index.type` = 'LCE'               -- Required for the new version. Specifies the new link.
);
```

> **Important**: `lindorm_columnar.user.index.type = 'LCE'` is required for the new version. If it is missing, the legacy link is used, with 15-minute latency.

**Official documentation**: [New columnar index version](https://help.aliyun.com/zh/lindorm/user-guide/column-store-index-new-version)

### Search Index — Depends on the LindormSearch Engine at the Underlying Layer

> **Engine description**: The underlying engine of search indexes is LindormSearch. API code V1 is `solr`, and V2 is `lsearch`. It is externally compatible with Elasticsearch 7.10 APIs on port 30070 and does not provide Solr APIs. Search indexes in wide table SQL automatically synchronize data to LindormSearch through LTS. Users do not need to operate the search engine directly.
>

> ⚠️ **Important**: Search indexes must be enabled in the console before use. Otherwise, index creation reports `SERVER INTERNAL ERROR`.

**Enablement steps**:

1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/).
2. On the instance list page, click the **target instance ID**.
3. In the left-side navigation pane, click **Wide Table Engine** → **Search Index**.
4. Click **Enable Now**.
5. Configure the following parameters:

| Parameter | Description | Recommendation |
|------|------|------|
| Search node specification | Processing capability of the search engine | 16 cores and 64 GB, for QPS 500+ and write TPS 50000+ |
| Number of search nodes | Number of search nodes | At least 2, to avoid a single point of failure |
| LTS data synchronization specification | Data synchronization service | 4 cores and 16 GB |
| Number of LTS nodes | Number of synchronization nodes | 2 nodes are recommended |
| Storage space | Search engine storage size | Estimate based on data volume |

> **Dependency description**: Search indexes depend on the LTS data synchronization service. LTS is enabled at the same time when this feature is enabled. If backup and restore or data subscription has already been enabled, LTS does not need to be enabled again.

**Official documentation**: https://help.aliyun.com/zh/lindorm/user-guide/enable-the-search-index-feature

#### Search Index Applicable Scenarios

| Scenario | Description | Example |
|------|------|------|
| Multidimensional combined query | Random combinations of any index columns | `WHERE c1=? AND c2=?` or `WHERE c3=?` |
| Analyzer query | Text tokenization matching | `MATCH(content) AGAINST('keyword')` |
| Fuzzy query | LIKE suffix or contains query | `WHERE name LIKE '%keyword%'` |
| Aggregate analysis | COUNT/SUM/MIN/MAX/AVG | `SELECT COUNT(*) GROUP BY` |
| Sorting and pagination | Sort by any index column | `ORDER BY create_time DESC LIMIT 10` |

#### Analyzer Query Syntax (MATCH AGAINST)

Search indexes support analyzer queries by using the `MATCH ... AGAINST` syntax:

```sql
-- Create a search index with analyzers.
CREATE INDEX idx_text USING SEARCH ON articles (
  title(type=text, analyzer=ik),
  content(type=text, analyzer=ik)
);

-- Analyzer query: query records whose content column contains "feature introduction".
SELECT * FROM articles WHERE MATCH(content) AGAINST('feature introduction');

-- Matches records that contain "feature", "introduction", or "feature introduction".
```

**Supported analyzers**:

| Analyzer | Description |
|--------|------|
| standard | Standard analyzer, used by default |
| ik | Chinese intelligent analyzer, recommended for Chinese text |
| english | English analyzer |
| whitespace | Tokenizes by spaces |
| comma | Tokenizes by commas |

#### Data Type Limits

> ⚠️ Search indexes **do not support the following data types**: DECIMAL, DATE, and TIME. If needed, use DOUBLE instead of DECIMAL, and use TIMESTAMP instead of DATE or TIME.

**Incorrect example**: Using DECIMAL in a search index column reports `Incompatible data type casting`.

#### Index Build Time

| Index Type | Build Time, Based on Actual Test Reference |
|---------|-------------------|
| Secondary index (KV) | About 10 seconds |
| Search index (SEARCH) | **About 30 seconds** |

> Queries executed before index construction is complete still report a "low-efficiency query interception" error. Actual build time varies by data volume. It is recommended to wait long enough after creating an index before querying.

#### Notes for Hot and Cold Data Separation Scenarios

> ⚠️ If hot and cold data separation is enabled for an instance, the search index construction process reads back data. Cold storage throttling of capacity-based cloud storage directly affects index construction efficiency and may cause backpressure on write operations.

**Prerequisites for enabling cold storage**:
- Capacity-based cloud storage must be enabled in the console as the cold storage medium first.
- Enablement path: log on to the Lindorm console → select a region → instance list → target instance ID → **Cold Storage** in the left-side navigation pane → click **Enable**.
- ⚠️ **Warning**: The enablement process requires a **rolling restart of the instance**, which may cause **latency fluctuation or connection interruption** for read and write requests. It is recommended to perform this operation during off-peak hours.
- Instances that use **local HDD disks** as the storage type do not support capacity-based cloud storage.

**Recommendations**:
- Complete index construction while data is written to hot storage.
- Or temporarily increase the cold storage read throttling limit.

### Secondary Index Redundant Columns (INCLUDE)

Redundant columns are used to copy data from other columns to the index table, avoiding lookups against the primary table during queries and improving query performance.

**Default behavior**:
- Lindorm SQL 2.9.3.10 and later: If INCLUDE is not specified, **no columns are redundantly stored** by default.
- Versions earlier than Lindorm SQL 2.9.3.10: If INCLUDE is not specified, **all columns are redundantly stored** by default.

**Redundantly store all columns (INDEX_COVERED_TYPE)**:

If all columns need to be redundantly stored, you can set the index property `INDEX_COVERED_TYPE`:

| Value | Description |
|------|------|
| COVERED_ALL_COLUMNS_IN_SCHEMA | Redundantly stores all defined columns in the primary table |
| COVERED_DYNAMIC_COLUMNS | Redundantly stores all columns, including dynamic columns. Applicable to dynamic tables. |

```sql
-- Redundantly store all defined columns.
CREATE INDEX idx_user ON orders (user_id) 
  WITH (INDEX_COVERED_TYPE = 'COVERED_ALL_COLUMNS_IN_SCHEMA');

-- Redundantly store all columns for a dynamic table, including dynamic columns.
CREATE INDEX idx_user ON orders (user_id) 
  WITH (INDEX_COVERED_TYPE = 'COVERED_DYNAMIC_COLUMNS');
```

**Usage recommendations**:
- Explicitly specify the columns that need to be redundantly stored. Avoid relying on default behavior.
- Redundant columns increase storage space usage. It is recommended to redundantly store only columns commonly used in queries.
- Only secondary indexes support redundant columns. Search indexes and columnar indexes do not support them.

**Notes**:
- Explicitly specified redundant columns cannot include primary key columns or index columns.

**Example of explicitly specifying redundant columns**:
```sql
-- Explicitly specify redundant columns.
CREATE INDEX idx_user ON orders (user_id) INCLUDE (amount, status);

-- During queries, amount and status can be obtained directly from the index without looking up the primary table.
SELECT user_id, amount, status FROM orders WHERE user_id = 'u001';
```

### Examples

```sql
-- Create a secondary index.
CREATE INDEX idx_user ON orders (user_id);

-- Create a secondary index with redundant columns.
CREATE INDEX idx_user ON orders (user_id) INCLUDE (amount, status);

-- Create a search index.
CREATE INDEX idx_search USING SEARCH ON products (name, description);

-- Create a search index by using a wildcard.
CREATE INDEX idx_all USING SEARCH ON products (*);

-- Create an index by using a function expression.
CREATE INDEX idx_hash ON orders (hash64(user_id, order_date), user_id, order_date);
```

### Search Index Key Properties

```sql
-- Use analyzers.
CREATE INDEX idx_text USING SEARCH ON articles (
  title(type=text, analyzer=ik),
  content(type=text, analyzer=ik)
);
```

| Property | Description |
|------|------|
| indexed | Whether to create an index. The default value is true. |
| rowStored | Whether to store raw data. The default value is false. |
| columnStored | Whether to use columnar storage. The default value is true. |
| type | Sets the analyzed field to text |
| analyzer | Analyzer: standard, english, ik, whitespace, or comma |

## Hot and Cold Data Separation

### Timestamp-based Hot and Cold Data Separation

```sql
-- Set during table creation.
CREATE TABLE dt (
  p1 INTEGER,
  p2 INTEGER,
  c1 VARCHAR,
  c2 BIGINT,
  PRIMARY KEY(p1 DESC)
) WITH (
  COMPRESSION = 'ZSTD',
  CHS = '86400',           -- Hot and cold boundary, in seconds.
  CHS_L2 = 'storagetype=COLD'
);

-- Enable for an existing table.
ALTER TABLE dt SET 'CHS' = '86400', 'CHS_L2' = 'storagetype=COLD';
```

### Custom Time Column-based Hot and Cold Data Separation

```sql
-- Set during table creation.
CREATE TABLE dt (
  p1 INTEGER,
  p2 BIGINT,
  p3 BIGINT,
  c1 VARCHAR,
  PRIMARY KEY(p1, p2, p3)
) WITH (
  COMPRESSION = 'ZSTD',
  CHS = '86400',
  CHS_L2 = 'storagetype=COLD',
  CHS_COLUMN = 'COLUMN=p2'  -- Specify the time column.
);

-- Specify the time unit.
CREATE TABLE dt (
  p1 INTEGER,
  p2 BIGINT,
  p3 BIGINT,
  c1 VARCHAR,
  PRIMARY KEY(p1, p2, p3)
) WITH (
  COMPRESSION = 'ZSTD',
  CHS = '86400',
  CHS_L2 = 'storagetype=COLD',
  CHS_COLUMN = 'COLUMN=p2|TIMEUNIT=SECONDS'
);
```

**CHS_COLUMN notes:**
- The custom time column must be a primary key column.
- The custom time column cannot be the first primary key column.
- Only BIGINT and TIMESTAMP types are supported.

### Modify and Disable Hot and Cold Data Separation

```sql
-- Modify the hot and cold boundary.
ALTER TABLE dt SET 'CHS' = '1000';

-- Disable hot and cold data separation.
ALTER TABLE dt SET 'CHS' = '', 'CHS_L2' = '', 'CHS_COLUMN' = '';
```

## Erasure Coding (EC)

Erasure coding is a data redundancy storage mechanism that saves storage space while maintaining the same reliability.

### Prerequisites

- Wide table engine 2.5.4 or later, and underlying storage 4.3.4 or later.
- At least 7 nodes.
- Local HDD disks.

### Usage

```sql
-- Enable during table creation.
CREATE TABLE dt (
  p1 INTEGER,
  p2 INTEGER,
  PRIMARY KEY(p1)
) WITH (EC_POLICY = 'RS-4-2');

-- Modify the erasure coding algorithm.
ALTER TABLE dt SET 'EC_POLICY' = 'RS-4-2';

-- Delete the erasure coding algorithm.
ALTER TABLE dt SET 'EC_POLICY' = '';
```

**Description:** The RS-4-2 algorithm is equivalent to 1.5 replicas in storage efficiency.

## Pre-splitting

It is recommended to configure pre-splitting when the data volume is large or when using Bulkload to import data.

### Recommended Number of Pre-split Regions

| Scenario | Recommended Number of Regions |
|------|-----------|
| SQL/HBase API writes | Number of nodes × 4 |
| Bulkload batch import | Data volume (GB) ÷ 8 |

### Examples

```sql
-- Specify the number of regions and the start and end keys.
CREATE TABLE orders (
  id VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(id)
) WITH (
  NUMREGIONS = '16',
  STARTKEY = 'a',
  ENDKEY = 'z'
);

-- Specify split points.
CREATE TABLE orders (
  id INTEGER NOT NULL,
  amount BIGINT,
  PRIMARY KEY(id)
) WITH (
  SPLITKEYS = '100,200,300,400,500'
);
```

## Complete Table Creation Examples

### IoT Device Data Table

```sql
CREATE TABLE iot_device_data (
  device_id VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  metric_name VARCHAR NOT NULL,
  metric_value DOUBLE,
  `extra_*` VARCHAR,
  PRIMARY KEY(hash32(device_id), device_id, timestamp DESC, metric_name)
) WITH (
  COMPRESSION = 'ZSTD',
  TTL = '7776000',              -- 90 days
  DYNAMIC_COLUMNS = 'true',
  wildcard_column = 'extra_*',
  CHS = '2592000',              -- Archive to cold storage after 30 days.
  CHS_L2 = 'storagetype=COLD',
  CHS_COLUMN = 'COLUMN=timestamp|TIMEUNIT=SECONDS'
);

-- Create a secondary index for queries by device type.
CREATE INDEX idx_metric ON iot_device_data (metric_name) INCLUDE (metric_value);
```

### E-commerce Order Table

```sql
CREATE TABLE orders (
  order_id VARCHAR NOT NULL,
  user_id VARCHAR NOT NULL,
  create_time BIGINT NOT NULL,
  status VARCHAR,
  amount BIGINT,
  items VARCHAR,
  PRIMARY KEY(hash32(order_id), order_id),
  INDEX idx_user USING KV (user_id, create_time DESC) INCLUDE (status, amount)
) WITH (
  COMPRESSION = 'ZSTD',
  CONSISTENCY = 'strong',
  MUTABILITY = 'MUTABLE_LATEST',
  NUMREGIONS = '32'
);

-- Create a search index to support product search.
CREATE INDEX idx_search USING SEARCH ON orders (items(type=text, analyzer=ik));
```

### Log Analysis Table

```sql
CREATE TABLE app_logs (
  bucket INTEGER NOT NULL,
  timestamp BIGINT NOT NULL,
  app_id VARCHAR NOT NULL,
  level VARCHAR NOT NULL,
  message VARCHAR,
  stack_trace VARCHAR,
  PRIMARY KEY(bucket, timestamp, app_id, level)
) WITH (
  COMPRESSION = 'ZSTD',
  TTL = '604800',                -- 7 days
  EC_POLICY = 'RS-4-2',
  CHS = '86400',                 -- Archive after 1 day.
  CHS_L2 = 'storagetype=COLD'
);
-- During writes: bucket = timestamp % 16
```
