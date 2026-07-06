# SQL Linting Rules Reference

Complete reference for all SQL linting rules in the `alibabacloud-polardb-mysql-sql-lint` skill.

## Rule Categories

1. **Engine Rules** - Storage engine validation
2. **Naming Rules** - Object naming conventions
3. **Statement Rules** - SQL statement best practices
4. **Table Rules** - Table design guidelines
5. **Column Rules** - Column design guidelines
6. **Index Rules** - Index optimization rules
7. **Schema Rules** - Schema change safety rules
8. **System Rules** - Database system configuration

---

## Engine Rules

### RULE-001: Require InnoDB

**Severity:** 🔴 Critical  
**Category:** Engine  
**Description:** Ensure tables use InnoDB storage engine

**Why:** InnoDB is the default and recommended storage engine for MySQL 5.5+. It provides:
- ACID transaction support
- Row-level locking
- Foreign key constraints
- Crash recovery
- MVCC (Multi-Version Concurrency Control)

**Violation Examples:**
```sql
-- ❌ Using MyISAM
CREATE TABLE users (id INT) ENGINE = MyISAM;

-- ❌ Using CSV
CREATE TABLE logs (id INT) ENGINE = CSV;

-- ❌ Changing to non-InnoDB
ALTER TABLE users ENGINE = MyISAM;
```

**Correct Examples:**
```sql
-- ✅ Explicitly use InnoDB
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='User table';

-- ✅ Default (InnoDB is default in MySQL 5.5+)
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  PRIMARY KEY (id)
);
```

**Fix:** Always specify `ENGINE=InnoDB` in CREATE TABLE statements.

---

## Naming Rules

### RULE-010: Table Naming Convention

**Severity:** 🟡 Warning  
**Category:** Naming  
**Description:** Validate table names follow snake_case convention

**Pattern:** `^[a-z]+(_[a-z]+)*$`

**Why:** Consistent naming improves readability and maintainability across teams.

**Violation Examples:**
```sql
-- ❌ CamelCase
CREATE TABLE UserSessions (...);

-- ❌ UPPERCASE
CREATE TABLE USER_LOGS (...);

-- ❌ Hyphens
CREATE TABLE user-logs (...);
```

**Correct Examples:**
```sql
-- ✅ snake_case
CREATE TABLE user_sessions (...);
CREATE TABLE user_logs (...);
CREATE TABLE order_items (...);
```

**Configuration:**
```json
{
  "naming_conventions": {
    "table_pattern": "^[a-z]+(_[a-z]+)*$",
    "max_length": 64
  }
}
```

---

### RULE-011: Column Naming Convention

**Severity:** 🟡 Warning  
**Category:** Naming  
**Description:** Validate column names follow snake_case convention

**Pattern:** `^[a-z]+(_[a-z]+)*$`

**Violation Examples:**
```sql
CREATE TABLE users (
  userId INT,        -- ❌ camelCase
  UserName VARCHAR,  -- ❌ PascalCase
  EMAIL VARCHAR      -- ❌ UPPERCASE
);
```

**Correct Examples:**
```sql
CREATE TABLE users (
  user_id INT,           -- ✅ snake_case
  user_name VARCHAR(50), -- ✅ snake_case
  email VARCHAR(100)     -- ✅ snake_case
);
```

---

### RULE-012: Index Naming Convention

**Severity:** 🟡 Warning  
**Category:** Naming  
**Description:** Validate index names follow naming pattern

**Pattern:** 
- Regular indexes: `idx_{table}_{columns}`
- Unique indexes: `uniq_{table}_{columns}`

**Violation Examples:**
```sql
-- ❌ Generic name
CREATE INDEX idx1 ON users(user_id);

-- ❌ No prefix
CREATE INDEX user_id_index ON users(user_id);
```

**Correct Examples:**
```sql
-- ✅ Clear naming
CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_orders_user_status ON orders(user_id, status);
CREATE UNIQUE INDEX uniq_users_email ON users(email);
```

**Why:** Descriptive index names make it easier to:
- Identify index purpose
- Debug performance issues
- Manage indexes in large schemas

---

## Statement Rules

### RULE-020: Disallow SELECT *

**Severity:** 🟡 Warning  
**Category:** Statement  
**Description:** Require explicit column list in SELECT statements

**Violation Examples:**
```sql
-- ❌ Select all columns
SELECT * FROM users WHERE id = 1;

-- ❌ In JOIN
SELECT * FROM users u JOIN orders o ON u.id = o.user_id;
```

**Correct Examples:**
```sql
-- ✅ Specify columns
SELECT id, username, email FROM users WHERE id = 1;

-- ✅ Use table aliases
SELECT u.id, u.username, o.order_id, o.amount 
FROM users u 
JOIN orders o ON u.id = o.user_id;
```

**Why:**
- **Performance**: Reduces network I/O and memory usage
- **Maintainability**: Makes code self-documenting
- **Stability**: Prevents breaking changes when schema evolves
- **Index Coverage**: Enables covering index optimization

**Exception:** Allow in:
- Ad-hoc queries for debugging
- COUNT(*) queries
- EXISTS subqueries

---

### RULE-021: Require WHERE Clause

**Severity:** 🔴 Critical  
**Category:** Statement  
**Description:** UPDATE and DELETE must have WHERE clause

**Violation Examples:**
```sql
-- ❌ Update all rows
UPDATE users SET status = 'inactive';

-- ❌ Delete all rows
DELETE FROM logs;
```

**Correct Examples:**
```sql
-- ✅ With WHERE clause
UPDATE users SET status = 'inactive' WHERE last_login < '2025-01-01';

-- ✅ With WHERE clause
DELETE FROM logs WHERE created_at < '2025-01-01' LIMIT 1000;
```

**Why:**
- **Data Safety**: Prevents accidental data loss
- **Audit Trail**: Makes intent clear in binlog
- **Replication Safety**: Reduces replication lag

**Best Practice:**
- Always use LIMIT with DELETE for large operations
- Test with SELECT first: `SELECT COUNT(*) FROM table WHERE ...`
- Use transactions for multi-step updates

---

### RULE-022: Disallow Leading % in LIKE

**Severity:** 🟡 Warning  
**Category:** Statement  
**Description:** LIKE '%xxx' causes full table scan

**Violation Examples:**
```sql
-- ❌ Leading wildcard
SELECT * FROM users WHERE username LIKE '%john%';

-- ❌ Only wildcard
SELECT * FROM products WHERE name LIKE '%phone%';
```

**Correct Examples:**
```sql
-- ✅ Trailing wildcard (can use index)
SELECT * FROM users WHERE username LIKE 'john%';

-- ✅ Full-text search (for complex patterns)
SELECT * FROM products WHERE MATCH(name) AGAINST('phone');

-- ✅ Generated column with reversed string
ALTER TABLE users ADD username_rev VARCHAR(50) GENERATED ALWAYS AS (REVERSE(username));
CREATE INDEX idx_username_rev ON users(username_rev);
SELECT * FROM users WHERE username_rev LIKE REVERSE('%john%');
```

**Why:**
- **Performance**: Leading wildcard prevents B-tree index usage
- **Scalability**: Full table scan degrades with data growth
- **CPU Impact**: Multiple concurrent LIKE '%xxx%' queries can cause CPU spike

**Alternative Solutions:**

#### **Option 0: Avoid/Disable Such Queries (Strongly Recommended)**

**When to block**:
- ❌ **Do not use in production**: tables with > 100K rows
- ❌ **Do not use in hot paths**: API endpoints, user-facing search
- ❌ **Do not use under concurrency**: multiple concurrent LIKE '%x%' queries cause CPU spikes

**Alternative strategies**:
```
1. Product level: switch to trailing wildcard search (e.g., "Test%")
2. Technical level: introduce Elasticsearch / Alibaba Cloud OpenSearch
3. Business level: provide tag/category filters instead of fuzzy text search
```

#### **Option 1: Fulltext Index (Recommended for Text Search)**

```sql
-- Add fulltext index
ALTER TABLE test_db.test_like_wildcard 
ADD FULLTEXT INDEX ft_title (title);

-- Use fulltext search instead of LIKE
SELECT id, title 
FROM test_like_wildcard 
WHERE MATCH(title) AGAINST('Test' IN BOOLEAN MODE);
```

**When to use**:
- ✅ Fuzzy search is a hard product requirement
- ✅ Large tables (> 100K rows)
- ✅ Need tokenization / relevance ranking

#### **Option 2: Application-Layer Cache + Search Engine**

```sql
-- Keep original SQL (only for low-frequency back-office queries)
SELECT id, title FROM test_like_wildcard WHERE title LIKE '%Test%';
```

**Optimization strategy**:
- Sync data to Elasticsearch / Redis
- Route frontend search through search engine, not database
- Database used only for persistence

#### **Option 3: Suffix Index + REVERSE Function**

```sql
-- Add reversed column and suffix index
ALTER TABLE test_like_wildcard 
ADD COLUMN title_rev VARCHAR(255) GENERATED ALWAYS AS (REVERSE(title)) STORED,
ADD INDEX idx_title_rev (title_rev);

-- Use reversed query (only optimizes trailing wildcard)
SELECT id, title 
FROM test_like_wildcard 
WHERE title_rev LIKE REVERSE('%Test');
```

**Limitation**: Only optimizes `LIKE '%Test'` (suffix match), not `LIKE '%Test%'` (infix match).

#### **Option 4: Columnar Storage (Analytics Only)**

```sql
ALTER TABLE test_db.test_like_wildcard 
COMMENT 'COLUMNAR=1';
```

**When to use**: Data analytics and reporting queries (**not suitable for OLTP workloads**).

---

**Code Review Guidance**:

The following patterns should be blocked during code review:

```python
# ❌ Forbidden: user search API using LIKE '%xxx%'
@app.route('/search')
def search():
    keyword = request.args.get('q')
    sql = f"SELECT * FROM products WHERE name LIKE '%{keyword}%'"  # Forbidden!
    
# ✅ Recommended: use fulltext search
@app.route('/search')
def search():
    keyword = request.args.get('q')
    # Use Elasticsearch or fulltext index
    results = es.search(index='products', body={
        "query": {"match": {"name": keyword}}
    })
```

**SQL Lint Rule Suggestion**:
```json
{
  "forbidden_patterns": [
    "LIKE '%.*%'"
  ],
  "block_in_production": true
}
```

---

### RULE-023: INSERT Must Specify Columns

**Severity:** 🔴 Critical  
**Category:** Statement  
**Description:** INSERT statements must specify column names

**Violation Examples:**
```sql
-- ❌ No column specification
INSERT INTO users VALUES (1, 'john', 'john@example.com');
```

**Correct Examples:**
```sql
-- ✅ Explicit columns
INSERT INTO users (id, username, email) VALUES (1, 'john', 'john@example.com');

-- ✅ With DEFAULT values
INSERT INTO users (username, email) VALUES ('john', 'john@example.com');
```

**Why:**
- **Schema Evolution**: Safe when columns are added/removed
- **Readability**: Clear mapping of values to columns
- **Maintainability**: Self-documenting code
- **Error Prevention**: Catches column order mismatches

---

### RULE-024: Disallow Explicit COMMIT

**Severity:** 🟡 Warning  
**Category:** Statement  
**Description:** Remove explicit COMMIT statements from migration scripts

**Violation Examples:**
```sql
-- ❌ Explicit COMMIT in migration
INSERT INTO users (username) VALUES ('john');
COMMIT;
```

**Correct Examples:**
```sql
-- ✅ Let migration tool manage transactions
INSERT INTO users (username) VALUES ('john');
```

**Why:**
- **Transaction Management**: Migration tools and frameworks manage transactions automatically
- **Rollback Safety**: Explicit COMMIT prevents atomic rollback of failed migrations
- **Consistency**: Framework-managed transactions ensure data consistency

**Note:** Skipped inside stored procedures/triggers where explicit transaction control is expected.

---

## Table Rules

### RULE-030: Require Primary Key

**Severity:** 🔴 Critical  
**Category:** Table  
**Description:** All tables must have primary key

**Violation Examples:**
```sql
-- ❌ No primary key
CREATE TABLE user_logs (
  user_id INT,
  action VARCHAR(50),
  created_at TIMESTAMP
);
```

**Correct Examples:**
```sql
-- ✅ Auto-increment PK
CREATE TABLE user_logs (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  user_id INT NOT NULL,
  action VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_user_id (user_id)
) ENGINE=InnoDB COMMENT='User activity logs';

-- ✅ Composite PK
CREATE TABLE order_items (
  order_id BIGINT UNSIGNED,
  product_id BIGINT UNSIGNED,
  quantity INT,
  PRIMARY KEY (order_id, product_id)
) ENGINE=InnoDB COMMENT='Order line items';
```

**Why:**
- **Performance**: Clustered index organization
- **Replication**: Required for statement-based replication
- **Data Integrity**: Prevents duplicate rows
- **Query Optimization**: Enables efficient lookups

**Best Practice:**
- Use `BIGINT UNSIGNED AUTO_INCREMENT` for single-column PK
- Use natural keys if they're stable and unique
- Avoid wide composite keys (>3 columns)

---

### RULE-031: Disallow Foreign Key

**Severity:** 🟡 Warning  
**Category:** Table  
**Description:** Avoid foreign key constraints in distributed systems

**Violation Examples:**
```sql
CREATE TABLE orders (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  user_id BIGINT UNSIGNED,
  PRIMARY KEY (id),
  FOREIGN KEY (user_id) REFERENCES users(id)  -- ❌
);
```

**Correct Examples:**
```sql
CREATE TABLE orders (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL COMMENT 'User ID reference',
  PRIMARY KEY (id),
  INDEX idx_user_id (user_id)  -- ✅ Index without FK
) ENGINE=InnoDB COMMENT='Order table';

-- Application-level validation
-- if not user_exists(user_id):
--     raise ValueError("User not found")
```

**Why:**
- **Distributed Systems**: FK constraints don't work across shards
- **Performance**: Adds overhead to INSERT/UPDATE/DELETE
- **Flexibility**: Harder to migrate data
- **Lock Contention**: Can cause deadlocks

**Alternative:**
- Use indexes for query performance
- Validate referential integrity in application code
- Use periodic consistency checks

---

### RULE-032: Table Comment Required

**Severity:** 🟡 Warning  
**Category:** Table  
**Description:** Require table comments for documentation

**Violation Examples:**
```sql
-- ❌ No comment
CREATE TABLE user_sessions (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  PRIMARY KEY (id)
);
```

**Correct Examples:**
```sql
-- ✅ With comment
CREATE TABLE user_sessions (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='User session management';
```

**Why:**
- **Documentation**: Self-documenting schema
- **Onboarding**: Helps new team members understand data model
- **Maintenance**: Reduces knowledge silos

---

## Column Rules

### RULE-042: Columns No NULL Value

**Severity:** 🟡 Warning  
**Category:** Column  
**Description:** Avoid nullable columns, use DEFAULT values instead

**Violation Examples:**
```sql
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50),         -- ❌ Nullable
  email VARCHAR(100),           -- ❌ Nullable
  status TINYINT,               -- ❌ Nullable
  PRIMARY KEY (id)
);
```

**Correct Examples:**
```sql
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL DEFAULT '',
  email VARCHAR(100) NOT NULL DEFAULT '',
  status TINYINT NOT NULL DEFAULT 1,
  PRIMARY KEY (id)
) ENGINE=InnoDB COMMENT='User table';
```

**Why:**
- **Data Quality**: Prevents unknown/missing values
- **Query Simplicity**: No need to handle NULL in WHERE clauses
- **Index Efficiency**: NULL values complicate index usage
- **Application Logic**: Reduces null pointer exceptions

---

### RULE-043: Set DEFAULT for NOT NULL Columns

**Severity:** 🔴 Critical  
**Category:** Column  
**Description:** NOT NULL columns must have DEFAULT value

**Violation Examples:**
```sql
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,     -- ❌ No DEFAULT
  email VARCHAR(100) NOT NULL,       -- ❌ No DEFAULT
  PRIMARY KEY (id)
);
```

**Correct Examples:**
```sql
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL DEFAULT '',
  email VARCHAR(100) NOT NULL DEFAULT '',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1=active, 0=disabled',
  PRIMARY KEY (id)
);
```

**Why:**
- **INSERT Safety**: Prevents failures when columns not specified
- **Schema Evolution**: Safe to add new columns to existing tables
- **Data Consistency**: Ensures all rows have valid values

---

### RULE-044: Require Column Default Value

**Severity:** 🟡 Warning  
**Category:** Column  
**Description:** All columns should have DEFAULT values

**Violation Examples:**
```sql
CREATE TABLE products (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  name VARCHAR(100),          -- ❌ No DEFAULT
  price DECIMAL(10,2),        -- ❌ No DEFAULT
  PRIMARY KEY (id)
);
```

**Correct Examples:**
```sql
CREATE TABLE products (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL DEFAULT '',
  price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  description TEXT DEFAULT '',
  PRIMARY KEY (id)
);
```

---

### RULE-045: Column Type Disallow List

**Severity:** 🟡 Warning  
**Category:** Column  
**Description:** Disallow use of deprecated or problematic column types

**Disallowed Types:**
- `FLOAT` - Use DECIMAL for precise numeric values
- `DOUBLE` - Use DECIMAL for precise numeric values
- `BLOB` - Consider using VARCHAR or TEXT with proper indexing
- `SET` - Use separate junction table for better normalization

**Violation Examples:**
```sql
CREATE TABLE products (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  price FLOAT,                -- ❌ Imprecise for currency
  rating DOUBLE,              -- ❌ Imprecise
  tags SET('new','hot','sale'), -- ❌ Poor normalization
  PRIMARY KEY (id)
);
```

**Correct Examples:**
```sql
CREATE TABLE products (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  price DECIMAL(10,2) NOT NULL DEFAULT 0.00,  -- ✅ Precise
  rating DECIMAL(3,2) NOT NULL DEFAULT 0.00,  -- ✅ Precise
  PRIMARY KEY (id)
);

-- For tags, use junction table
CREATE TABLE product_tags (
  product_id BIGINT UNSIGNED,
  tag VARCHAR(50),
  PRIMARY KEY (product_id, tag)
);
```

---

### RULE-040: Auto-increment Column Type

**Severity:** 🟡 Warning  
**Category:** Column  
**Description:** Use BIGINT UNSIGNED for auto-increment columns

**Limits:**
- INT: 2,147,483,647 (2.1B)
- BIGINT UNSIGNED: 18,446,744,073,709,551,615 (18.4Q)

**Violation Examples:**
```sql
CREATE TABLE users (
  id INT AUTO_INCREMENT,  -- ❌ May overflow
  PRIMARY KEY (id)
);
```

**Correct Examples:**
```sql
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,  -- ✅ Safe for large datasets
  PRIMARY KEY (id)
);
```

**Why:**
- **Future-Proof**: Prevents overflow in high-traffic systems
- **Minimal Overhead**: Only 4 bytes additional storage
- **Best Practice**: Industry standard for modern applications

---

### RULE-041: Column Comment Required

**Severity:** 🟡 Warning  
**Category:** Column  
**Description:** Require column comments for documentation

**Violation Examples:**
```sql
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  user_type INT,          -- ❌ No comment
  status TINYINT,         -- ❌ No comment
  PRIMARY KEY (id)
);
```

**Correct Examples:**
```sql
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT COMMENT 'Primary key',
  user_type TINYINT COMMENT 'User type: 1=normal, 2=admin, 3=super_admin',
  status TINYINT DEFAULT 1 COMMENT 'Account status: 0=disabled, 1=active',
  PRIMARY KEY (id)
);
```

**Why:**
- **Clarity**: Explains column purpose and valid values
- **Maintenance**: Reduces tribal knowledge
- **Code Generation**: Enables automatic API documentation

---

## Index Rules

### RULE-052: Index Count Limit

**Severity:** 🟡 Warning  
**Category:** Index  
**Description:** Limit number of indexes per table (default: 10)

**Violation Examples:**
```sql
CREATE TABLE orders (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  user_id BIGINT UNSIGNED,
  status VARCHAR(20),
  created_at TIMESTAMP,
  -- ... 8 more indexes
  PRIMARY KEY (id),
  INDEX idx_user_id (user_id),
  INDEX idx_status (status),
  INDEX idx_created_at (created_at),
  -- ... 7 more indexes (total 11)
);
```

**Correct Examples:**
```sql
CREATE TABLE orders (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  user_id BIGINT UNSIGNED,
  status VARCHAR(20),
  created_at TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_user_status (user_id, status),  -- ✅ Composite index
  INDEX idx_created_at (created_at)
  -- Total: 3 indexes (within limit)
) ENGINE=InnoDB COMMENT='Order table';
```

**Why:**
- **Write Performance**: Each index slows down INSERT/UPDATE/DELETE
- **Storage Overhead**: Indexes consume disk space
- **Maintenance Cost**: More indexes = longer DDL operations
- **Optimizer Confusion**: Too many indexes may confuse query optimizer

**Best Practice:**
- Monitor index usage: `SELECT * FROM sys.schema_unused_indexes`
- Remove unused indexes regularly
- Use composite indexes instead of multiple single-column indexes

---

### RULE-053: Disallow Duplicate Column in Index

**Severity:** 🔴 Critical  
**Category:** Index  
**Description:** Disallow duplicate columns in composite index keys

**Violation Examples:**
```sql
-- ❌ Duplicate column in index
CREATE INDEX idx_user_user ON orders(user_id, user_id);

-- ❌ Duplicate in composite index
CREATE INDEX idx_composite ON orders(user_id, status, user_id);
```

**Correct Examples:**
```sql
-- ✅ No duplicates
CREATE INDEX idx_user ON orders(user_id);

-- ✅ Proper composite index
CREATE INDEX idx_user_status ON orders(user_id, status);
```

**Why:**
- **Useless**: Duplicate columns provide no benefit
- **Waste**: Consumes extra storage and maintenance overhead
- **Bug Indicator**: Likely a copy-paste error

---

### RULE-050: Index Key Limit

**Severity:** 🟡 Warning  
**Category:** Index  
**Description:** Limit columns per composite index (max: 5)

**Violation Examples:**
```sql
-- ❌ Too many columns
CREATE INDEX idx_complex ON orders(
  user_id, 
  status, 
  created_at, 
  updated_at,
  amount,
  region
);
```

**Correct Examples:**
```sql
-- ✅ Focused index
CREATE INDEX idx_user_status ON orders(user_id, status);

-- ✅ Multiple targeted indexes
CREATE INDEX idx_created_at ON orders(created_at);
CREATE INDEX idx_region ON orders(region);
```

**Why:**
- **Selectivity**: First columns should be most selective
- **Storage**: Wide indexes consume more disk space
- **Maintenance**: Slower INSERT/UPDATE/DELETE
- **Optimizer**: May not use all columns efficiently

**Best Practice:**
- Put equality columns first, then range columns
- Use leftmost prefix principle
- Monitor index usage: `SHOW INDEX FROM table`

---

### RULE-051: Disallow BLOB/TEXT Indexes

**Severity:** 🔴 Critical  
**Category:** Index  
**Description:** Disallow indexing BLOB and TEXT columns

**Violation Examples:**
```sql
-- ❌ Direct index on TEXT
CREATE TABLE articles (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  content TEXT,
  PRIMARY KEY (id),
  INDEX idx_content (content)  -- ❌ Error or inefficient
);
```

**Correct Examples:**
```sql
-- ✅ FULLTEXT index for search
CREATE TABLE articles (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  content TEXT,
  PRIMARY KEY (id),
  FULLTEXT INDEX ft_content (content)  -- ✅
);

-- ✅ Prefix index
CREATE INDEX idx_content_prefix ON articles(content(100));
```

**Why:**
- **Performance**: B-tree indexes on large values are inefficient
- **Storage**: Index can be larger than data
- **Limitations**: MySQL restricts index length

**Alternatives:**
1. **FULLTEXT Index**: For text search
2. **Prefix Index**: `INDEX (column(100))`
3. **Generated Column**: Hash or extract key parts
4. **External Search**: Elasticsearch for complex search

---

## Schema Rules

### RULE-073: Primary Key Naming Convention

**Severity:** 🟡 Warning  
**Category:** Naming  
**Description:** Primary key should be named 'id' or 'pk_<table_name>'

**Violation Examples:**
```sql
CREATE TABLE users (
  user_id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50),
  CONSTRAINT pk_users_custom PRIMARY KEY (user_id)  -- ❌ Non-standard name
);
```

**Correct Examples:**
```sql
-- ✅ Simple 'id' column
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50),
  PRIMARY KEY (id)
);

-- ✅ Named constraint with pk_ prefix
CREATE TABLE users (
  user_id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50),
  CONSTRAINT pk_users PRIMARY KEY (user_id)
);
```

**Why:**
- **Consistency**: Standard naming across all tables
- **ORM Compatibility**: Many ORMs expect 'id' as primary key
- **Maintainability**: Easy to identify primary keys in schema

---

### RULE-070: Charset Allow List

**Severity:** 🔴 Critical  
**Category:** System  
**Description:** Only allow utf8mb4 charset for Unicode support

**Violation Examples:**
```sql
-- ❌ Using latin1
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- ❌ Using utf8 (3-byte, incomplete Unicode)
CREATE TABLE products (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  name VARCHAR(100),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
```

**Correct Examples:**
```sql
-- ✅ Using utf8mb4 (full Unicode including emoji)
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  username VARCHAR(50),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='User table';

-- ✅ Explicit utf8mb4 with collation
CREATE TABLE products (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  name VARCHAR(100) COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Product table';
```

**Why:**
- **Full Unicode**: utf8mb4 supports all Unicode characters including emoji
- **MySQL utf8 is Incomplete**: MySQL's 'utf8' is only 3-byte (utf8mb3), missing some characters
- **Future-Proof**: Supports all current and future Unicode standards
- **Compatibility**: Industry standard for modern applications

---

### RULE-071: Limit DDL on Large Tables

**Severity:** 🟡 Warning  
**Category:** Table  
**Description:** Warn about DDL operations on large tables (>1M rows)

**Violation Examples:**
```sql
-- ⚠️ ALTER TABLE on table with 5M rows
ALTER TABLE orders ADD COLUMN region VARCHAR(50);
```

**Correct Approaches:**
```sql
-- ✅ Online DDL (MySQL 5.6+)
ALTER TABLE orders 
  ADD COLUMN region VARCHAR(50) COMMENT 'Region code',
  ALGORITHM=INPLACE, 
  LOCK=NONE;

-- ✅ Using gh-ost (GitHub's online schema migration tool)
gh-ost \
  --user="migrator" \
  --password="..." \
  --host=localhost \
  --database=shop \
  --table=orders \
  --alter="ADD COLUMN region VARCHAR(50) COMMENT 'Region code'" \
  --execute

-- ✅ Using pt-online-schema-change (Percona Toolkit)
pt-online-schema-change \
  --alter "ADD COLUMN region VARCHAR(50) COMMENT 'Region code'" \
  D=shop,t=orders,h=localhost,u=migrator,p=... \
  --execute
```

**Why:**
- **Lock Time**: Large table DDL can lock table for minutes or hours
- **Replication Lag**: DDL causes replication delays
- **Service Impact**: May cause service downtime
- **Disk Space**: Some DDL operations require table copy (2x disk space)

**Best Practice:**
- Use online DDL (ALGORITHM=INPLACE, LOCK=NONE) when possible
- Schedule DDL during maintenance windows for very large tables
- Use tools like gh-ost or pt-online-schema-change for zero-downtime migrations
- Test DDL on staging environment first

---

### RULE-072: Limit Inserted Rows

**Severity:** 🟡 Warning  
**Category:** Statement  
**Description:** Limit rows per INSERT statement (default: 1000)

**Violation Examples:**
```sql
-- ❌ Inserting 5000 rows in one statement
INSERT INTO users (username, email) VALUES
  ('user1', 'user1@example.com'),
  ('user2', 'user2@example.com'),
  -- ... 4998 more rows
  ('user5000', 'user5000@example.com');
```

**Correct Examples:**
```sql
-- ✅ Batch inserts (1000 rows per statement)
INSERT INTO users (username, email) VALUES
  ('user1', 'user1@example.com'),
  -- ... 999 more rows
  ('user1000', 'user1000@example.com');

INSERT INTO users (username, email) VALUES
  ('user1001', 'user1001@example.com'),
  -- ... 999 more rows
  ('user2000', 'user2000@example.com');

-- ✅ Using LOAD DATA INFILE for large imports
LOAD DATA INFILE '/tmp/users.csv'
  INTO TABLE users
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n'
  (username, email);
```

**Why:**
- **Transaction Size**: Large transactions hold locks longer
- **Replication Lag**: Big INSERT causes replication delays
- **Memory Usage**: Large statements consume more memory
- **Rollback Cost**: Rolling back large transactions is expensive
- **Binlog Size**: Increases binary log size significantly

**Best Practice:**
- Batch size: 500-1000 rows per INSERT
- Use `LOAD DATA INFILE` for bulk imports (>10K rows)
- Monitor replication lag during batch operations
- Use transactions to ensure atomicity across batches

---

### RULE-060: Backward Incompatible Schema Change

**Severity:** 🔴 Critical  
**Category:** Schema  
**Description:** Detect breaking schema changes

**Violation Examples:**
```sql
-- ❌ Renaming column (breaks application)
ALTER TABLE users CHANGE COLUMN username user_name VARCHAR(50);

-- ❌ Changing column type (may lose data)
ALTER TABLE users MODIFY COLUMN age VARCHAR(10);

-- ❌ Dropping column
ALTER TABLE users DROP COLUMN email;
```

**Safe Alternatives:**
```sql
-- ✅ Add new column, migrate data, then remove old
ALTER TABLE users ADD COLUMN user_name VARCHAR(50);
-- Application writes to both columns
-- Backfill: UPDATE users SET user_name = username;
-- Then remove old column in next deployment

-- ✅ Online DDL with ALGORITHM=INPLACE
ALTER TABLE users MODIFY COLUMN age VARCHAR(10), ALGORITHM=INPLACE, LOCK=NONE;
```

**Why:**
- **Zero Downtime**: Avoid service interruption
- **Rollback Safety**: Easy to revert changes
- **Application Compatibility**: Prevent runtime errors

---

### RULE-061: ALTER TABLE Merge

**Severity:** 🟡 Warning  
**Category:** Schema  
**Description:** Combine multiple ALTER TABLE statements

**Violation Examples:**
```sql
-- ❌ Multiple ALTER statements
ALTER TABLE users ADD COLUMN age INT;
ALTER TABLE users ADD COLUMN gender TINYINT;
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
```

**Correct Examples:**
```sql
-- ✅ Single ALTER statement
ALTER TABLE users 
  ADD COLUMN age INT COMMENT 'User age',
  ADD COLUMN gender TINYINT COMMENT 'Gender: 0=unknown, 1=male, 2=female',
  ADD COLUMN phone VARCHAR(20) COMMENT 'Phone number';
```

**Why:**
- **Performance**: Single table rebuild vs multiple
- **Lock Time**: Reduces metadata lock duration
- **Atomicity**: All changes succeed or fail together

---

## DAS Diagnostics Integration

In addition to static lint rules, the skill integrates with Alibaba Cloud DAS for dynamic SQL analysis:

### DAS Diagnostic Checks

1. **Execution Plan Analysis**
   - 🔴 Full table scan (TABLE_SCAN)
   - 🟡 Range scan efficiency
   - 🟢 Index usage validation

2. **Index Recommendations**
   - Missing index suggestions
   - Redundant index detection
   - Covering index opportunities

3. **SQL Rewrite Suggestions**
   - Subquery to JOIN conversion
   - UNION to UNION ALL optimization
   - Implicit type conversion fixes

### DAS Output Interpretation

**Node Colors in Execution Plan:**
- 🟢 Green: Efficient (system, const, eq_ref, ref)
- 🟡 Yellow: Medium (fulltext, range, index_subquery)
- 🔴 Red: Inefficient (all, index) - Prioritize optimization

**Cost Metrics:**
- Cost is relative (CPU + I/O + Memory)
- Compare before/after optimization
- Focus on highest cost nodes first

### Safety Note: Table Analysis

This skill does NOT connect to the database. All analysis is performed through:

- **Static linting**: 28+ rules run instantly with no network calls
- **DAS diagnosis API** (`create-request-diagnosis`): Provides execution plan analysis, cost estimation, and index recommendations without direct database connection

**❌ NEVER** execute SQL directly against the database (no `COUNT(*)`, `EXPLAIN`, `SHOW INDEX`, `INFORMATION_SCHEMA` queries).
**✅ ALWAYS** use static linting + DAS API for analysis.
