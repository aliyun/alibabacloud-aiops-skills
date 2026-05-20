# Detailed Sort Key and Index Design Guide

## Table of Contents

1. [Sort Key and Prefix Index](#sort-key-and-prefix-index)
2. [ORDER BY Syntax](#order-by-syntax)
3. [Bitmap Index](#bitmap-index)
4. [Bloom Filter Index](#bloom-filter-index)
5. [N-Gram Bloom Filter Index](#n-gram-bloom-filter-index)
6. [Full-Text Inverted Index](#full-text-inverted-index)
7. [Built-in Indexes](#built-in-indexes)
8. [Index Selection Decision](#index-selection-decision)

---

## Sort Key and Prefix Index

### How the Prefix Index Works

StarRocks builds the prefix index automatically during data ingestion:
- One index entry is generated every 1,024 rows
- Index content = the prefix of the sort key values from the first row
- **Maximum length 36 bytes**; anything beyond is truncated

At query time, the prefix index quickly locates the row ranges that contain the target data and skips irrelevant data blocks.

### Sort Key Design Principles

| Principle | Description |
|------|------|
| **At most 3 columns** | More than 3 columns increases write-time sorting overhead and may exceed the 36-byte prefix-index limit |
| **High-frequency filter columns first** | The first column of the sort key should be the most frequently used equality/range filter in query WHERE |
| **High-cardinality columns first** | High-cardinality columns filter better (low-cardinality columns like gender/status filter poorly) |
| **VARCHAR/STRING last** | String columns have variable length; the prefix index truncates at the first VARCHAR |
| **Follow leftmost-prefix matching** | Query conditions must match the sort key from the first column contiguously to use the prefix index |

### Leftmost-Prefix Matching Example

Sort key `ORDER BY (dt, user_id, action)`:

| Query Condition | Prefix Index | Reason |
|---------|---------|------|
| `WHERE dt = '2024-01-01'` | Hits | Matches the first column |
| `WHERE dt = '2024-01-01' AND user_id = 123` | Hits | Matches the first two columns |
| `WHERE user_id = 123` | Misses | Skips the first column dt |
| `WHERE action = 'click'` | Misses | Skips the first two columns |
| `WHERE dt > '2024-01-01' AND user_id = 123` | Partial hit | dt is a range condition; subsequent columns cannot benefit |

### Verifying Prefix Index Effectiveness

Check `ShortKeyFilterRows` in the query Profile:
- Larger values → more rows filtered by the prefix index → better effect
- A value of 0 → prefix index did not take effect; check whether the query conditions match the sort key

---

## ORDER BY Syntax

### Version Support

| Version | Scope of Support |
|------|---------|
| v3.0+ | Primary Key tables support independent ORDER BY |
| v3.3+ | All table types support independent ORDER BY |
| Before v3.3 | The sort key is determined by the KEY columns (DUPLICATE KEY / AGGREGATE KEY / UNIQUE KEY) |

### Relationship with KEY Columns

**v3.3+ (recommended):** ORDER BY is independent of KEY columns; physical sorting is determined by ORDER BY.

```sql
-- Aggregate table: ORDER BY can differ in order from AGGREGATE KEY columns
CREATE TABLE agg_stats (
    user_id INT,
    dt DATE,
    region VARCHAR(20),
    pv BIGINT SUM
)
AGGREGATE KEY(user_id, dt, region)
ORDER BY (dt, region, user_id)  -- Optimize queries by time range
PARTITION BY date_trunc('day', dt)
DISTRIBUTED BY HASH(user_id) BUCKETS 16;
```

**Before v3.3 (compatibility):** The sort key is implicitly determined by the KEY definition.

```sql
-- For a Duplicate Key table, the KEY columns = the sort key
CREATE TABLE log (
    dt DATE,
    user_id BIGINT,
    action VARCHAR(32),
    detail VARCHAR(256)
)
DUPLICATE KEY(dt, user_id, action);  -- Sort key = (dt, user_id, action)
```

### Sort Key Examples

```sql
-- E-commerce orders: queried by user and time
CREATE TABLE orders (
    order_id BIGINT NOT NULL,
    user_id INT NOT NULL,
    order_date DATE NOT NULL,
    status TINYINT,
    amount DECIMAL(12,2)
)
PRIMARY KEY(order_id, order_date, user_id)
PARTITION BY date_trunc('day', order_date)
DISTRIBUTED BY HASH(user_id) BUCKETS 32
ORDER BY (user_id, order_date);  -- Optimize equality on user_id + range on order_date

-- Log table: queried by time range
CREATE TABLE access_log (
    log_time DATETIME NOT NULL,
    service VARCHAR(64),
    level VARCHAR(8),
    message VARCHAR(1024)
)
DUPLICATE KEY(log_time, service)
ORDER BY (log_time, service)  -- Optimize time range + service filter
PARTITION BY date_trunc('hour', log_time)
DISTRIBUTED BY RANDOM;
```

---

## Bitmap Index

**Applicable scenarios:** Equality/IN queries on non-prefix columns; works for both high-cardinality and low-cardinality columns.

**Syntax:**

```sql
-- Create at table creation time
CREATE TABLE user_profile (
    user_id BIGINT,
    age INT,
    gender VARCHAR(8),
    city VARCHAR(32),
    INDEX idx_city (city) USING BITMAP
)
DUPLICATE KEY(user_id)
DISTRIBUTED BY HASH(user_id) BUCKETS 16;

-- Add to an existing table
CREATE INDEX idx_gender ON user_profile (gender) USING BITMAP;

-- Drop the index
DROP INDEX idx_gender ON user_profile;
```

**Supported query patterns:**
- `WHERE city = 'Shanghai'`
- `WHERE city IN ('Shanghai', 'Beijing')`
- AND/OR combinations across multiple Bitmap-indexed columns

**Limitations:**
- Not supported on value columns of Aggregate / Unique Key tables
- Not supported for FLOAT, DOUBLE, DECIMAL types
- Extra overhead at write time for index construction

**When to use:**
- Queries frequently filter on non-sort-key columns
- Combined conditions on several low-cardinality columns (e.g., `city = X AND status = Y`)
- Equality queries on high-cardinality columns (e.g., user_id)

---

## Bloom Filter Index

**Applicable scenarios:** Equality queries on high-cardinality columns (ID-like) to quickly decide whether a data block contains the target value.

**Syntax:**

```sql
-- Specify at table creation
CREATE TABLE orders (
    order_id VARCHAR(64),
    user_id BIGINT,
    product_name VARCHAR(128),
    amount DECIMAL(12,2)
)
DUPLICATE KEY(order_id)
DISTRIBUTED BY HASH(order_id) BUCKETS 32
PROPERTIES (
    "bloom_filter_columns" = "order_id, user_id"
);

-- Add to an existing table
ALTER TABLE orders SET ("bloom_filter_columns" = "order_id, user_id, product_name");
```

**How it works:**
- Each data Page maintains a Bloom Filter
- At query time the Bloom Filter is checked first; if it says the value is absent, the page is skipped
- False positives are possible, but false negatives are not

**When to use:**
- High-cardinality columns (ID-like fields such as order_id, transaction_id)
- Queries dominated by equality conditions
- The prefix index doesn't cover (column is not in the sort key or fails leftmost-prefix matching)

**Limitations:**
- Not supported for TINYINT, FLOAT, DOUBLE types
- Effective only for `=` and `IN`; not for range queries
- About 1-2% additional storage per column

---

## N-Gram Bloom Filter Index

**Applicable scenarios:** Accelerates LIKE fuzzy queries and the `ngram_search` function.

**Syntax:**

```sql
CREATE TABLE articles (
    id BIGINT,
    title VARCHAR(256),
    content STRING,
    INDEX idx_content (content) USING NGRAMBF ("gram_num" = "4", "bloom_filter_fpp" = "0.05")
)
DUPLICATE KEY(id)
DISTRIBUTED BY HASH(id) BUCKETS 16;
```

**Parameters:**
- `gram_num`: The N value of the N-gram, typically 4
- `bloom_filter_fpp`: False positive rate, default 0.05

**When to use:**
- Need to accelerate `WHERE content LIKE '%keyword%'`
- `ngram_search()` function queries

---

## Full-Text Inverted Index

**Applicable scenarios:** Keyword full-text search.

**Syntax:**

```sql
CREATE TABLE docs (
    doc_id BIGINT,
    title VARCHAR(256),
    body STRING,
    INDEX idx_body (body) USING GIN
         ("parser" = "chinese")  -- Supports standard/english/chinese
)
DUPLICATE KEY(doc_id)
DISTRIBUTED BY HASH(doc_id) BUCKETS 16;
```

**Supported tokenizers:**
- `standard`: Tokenize by whitespace/punctuation
- `english`: English tokenization with stemming
- `chinese`: Chinese tokenization

**When to use:**
- Keyword search in logs
- Document content retrieval
- Replace inefficient full table scans caused by LIKE '%keyword%'

---

## Built-in Indexes

The following indexes are maintained automatically by StarRocks; no manual creation is needed:

### ZoneMap Index
- **Level:** Segment level + Page level
- **Content:** Min, Max, HasNull, HasNotNull for each column
- **Purpose:** At query time, automatically skip data blocks that do not satisfy WHERE range conditions
- **Influencing factors:** Sort key order affects ZoneMap effectiveness — ZoneMap filtering is most effective on the first sort key column

### Ordinal Index
- **Level:** Page level
- **Content:** Row number → physical page address mapping
- **Purpose:** Locate data pages in the columnar storage format

---

## Index Selection Decision

```
Is the column in the sort key?
├── Yes → The prefix index applies automatically (when leftmost-prefix matching is satisfied)
│   └── If leftmost-prefix matching is not satisfied → consider reordering sort key columns
│       or add a Bitmap / Bloom Filter index
└── No → What is the query pattern?
    ├── Equality query (= / IN)
    │   ├── High-cardinality column (ID-like) → Bloom Filter index
    │   ├── Low-cardinality column or multi-column combination → Bitmap index
    │   └── When both apply → Bloom Filter (lower write overhead)
    ├── Fuzzy query (LIKE '%X%') → N-Gram Bloom Filter
    ├── Full-text search → Inverted index (GIN)
    └── Range query (> / < / BETWEEN)
        → Rely on ZoneMap (automatic); if not effective, consider reordering the sort key
```

**Multi-index combination example:**

```sql
CREATE TABLE ecommerce_events (
    event_time DATETIME NOT NULL,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(32),
    product_id BIGINT,
    category VARCHAR(64),
    search_query VARCHAR(256),
    -- Bitmap index: filter on event type and category combinations
    INDEX idx_event_type (event_type) USING BITMAP,
    INDEX idx_category (category) USING BITMAP,
    -- N-Gram index: fuzzy match on search terms
    INDEX idx_search (search_query) USING NGRAMBF ("gram_num" = "4", "bloom_filter_fpp" = "0.05")
)
DUPLICATE KEY(event_time, user_id)
ORDER BY (event_time, user_id)
PARTITION BY date_trunc('day', event_time)
DISTRIBUTED BY HASH(user_id) BUCKETS 32
PROPERTIES (
    -- Bloom Filter index: equality queries on high-cardinality product_id
    "bloom_filter_columns" = "product_id"
);
```
