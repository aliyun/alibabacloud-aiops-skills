# SQL Lint Examples

Additional examples for SQL linting scenarios.

---

## Example 1: DDL Assessment

**Input SQL:**
```sql
CREATE TABLE user_sessions (
  id INT AUTO_INCREMENT,
  user_id INT,
  session_token VARCHAR(255),
  created_at TIMESTAMP,
  PRIMARY KEY (id)
);
```

**Assessment Result:**
```
[WARNING]

  1. Auto-increment column uses INT (max: 2.1B) (RULE-040)
     Suggestion: Use BIGINT UNSIGNED (max: 18.4Q) to prevent overflow

  2. Columns missing comments: id, user_id, session_token, created_at (RULE-041)
     Suggestion: Add column comments for documentation

  3. Table missing comment (RULE-032)
     Suggestion: Add table comment for documentation: COMMENT='User session management'
```

**Optimized SQL:**
```sql
CREATE TABLE user_sessions (
  id BIGINT UNSIGNED AUTO_INCREMENT COMMENT 'Primary key',
  user_id BIGINT UNSIGNED NOT NULL COMMENT 'User ID reference',
  session_token VARCHAR(255) NOT NULL COMMENT 'Session token',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation time',
  PRIMARY KEY (id),
  INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='User session management';
```

---

## Example 2: DML Assessment

**Input SQL:**
```sql
SELECT * FROM orders WHERE user_id = 100;
```

**Assessment Result:**
```
[WARNING]

  1. SELECT * detected (RULE-020)
     Suggestion: Specify required columns explicitly to improve performance and maintainability
```

**DAS Recommendation:**
```
[DAS DIAGNOSIS]

  Cost Estimate: Large table scan
    Estimated rows: 2500000
    Estimated CPU: 15234.50
    Estimated I/O: 8120.00

  Index Recommendations:
    - CREATE INDEX idx_user_id ON orders(user_id);

  Tuning Advice:
    - Full table scan detected, no index matched. Add appropriate index.
```

---

## Example 3: Schema Change Assessment

**Input SQL:**
```sql
ALTER TABLE products ADD COLUMN description BLOB;
```

**Assessment Result:**
```
[WARNING]

  1. Disallowed column types: BLOB (Consider using VARCHAR or TEXT with proper indexing) (RULE-045)
     Suggestion: Replace with recommended alternatives for better performance and maintainability
```

---

## Example 4: Dangerous UPDATE

**Input SQL:**
```sql
UPDATE users SET status = 'inactive';
```

**Assessment Result:**
```
[CRITICAL]

  1. UPDATE without WHERE clause (RULE-021)
     SQL: UPDATE users SET status = 'inactive'
     Suggestion: Add WHERE clause to limit affected rows
```

**Corrected SQL:**
```sql
UPDATE users 
SET status = 'inactive' 
WHERE last_login < '2025-01-01' 
  AND status = 'active';
```

---

## Example 5: Large Batch INSERT

**Input SQL:**
```sql
INSERT INTO users (username, email) VALUES
  ('user1', 'user1@example.com'),
  ('user2', 'user2@example.com'),
  -- ... 5000 rows total
  ('user5000', 'user5000@example.com');
```

**Assessment Result:**
```
[WARNING]

  1. Large batch INSERT (RULE-072)
     Suggestion: INSERT exceeds 1000 rows, split into smaller batches
```

**Corrected SQL:**
```sql
-- Batch 1 (1000 rows)
INSERT INTO users (username, email) VALUES
  ('user1', 'user1@example.com'),
  -- ... 999 more rows
  ('user1000', 'user1000@example.com');

-- Batch 2 (1000 rows)
INSERT INTO users (username, email) VALUES
  ('user1001', 'user1001@example.com'),
  -- ... 999 more rows
  ('user2000', 'user2000@example.com');

-- ... continue for remaining batches
```

---

## Example 6: Full-Text Search Alternative

**Input SQL:**
```sql
SELECT * FROM products WHERE name LIKE '%phone%';
```

**Assessment Result:**
```
[WARNING]

  1. SELECT * detected (RULE-020)
     Suggestion: Specify required columns explicitly to improve performance and maintainability

  2. Leading wildcard in LIKE pattern (RULE-022)
     Suggestion: Avoid LIKE '%xxx' as it prevents index usage. Consider full-text search
```

**Alternative Solutions:**

**Option 1: FULLTEXT Index**
```sql
-- Add FULLTEXT index
ALTER TABLE products ADD FULLTEXT INDEX ft_name (name);

-- Use MATCH...AGAINST
SELECT id, name, price 
FROM products 
WHERE MATCH(name) AGAINST('phone' IN BOOLEAN MODE);
```

**Option 2: External Search Engine**
```python
# Use Elasticsearch
results = es.search(index='products', body={
    "query": {"match": {"name": "phone"}}
})
```

---

## Example 7: Index Optimization

**Input SQL:**
```sql
CREATE TABLE orders (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  user_id BIGINT UNSIGNED,
  status VARCHAR(20),
  created_at TIMESTAMP,
  amount DECIMAL(10,2),
  PRIMARY KEY (id),
  INDEX idx_user (user_id),
  INDEX idx_status (status),
  INDEX idx_created (created_at),
  INDEX idx_user_status (user_id, status),
  INDEX idx_user_created (user_id, created_at),
  INDEX idx_amount (amount),
  INDEX idx_status_created (status, created_at),
  INDEX idx_user_amount (user_id, amount),
  INDEX idx_status_amount (status, amount),
  INDEX idx_all (user_id, status, created_at, amount)
);
```

**Assessment Result:**
```
[WARNING]

  1. Table has 11 indexes (max: 10) (RULE-052)
     Suggestion: Reduce index count. Too many indexes slow down INSERT/UPDATE/DELETE operations
```

**Optimization Suggestions:**
```sql
-- Keep only necessary indexes
CREATE TABLE orders (
  id BIGINT UNSIGNED AUTO_INCREMENT,
  user_id BIGINT UNSIGNED,
  status VARCHAR(20),
  created_at TIMESTAMP,
  amount DECIMAL(10,2),
  PRIMARY KEY (id),
  INDEX idx_user_status_created (user_id, status, created_at)  -- Composite index
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Order table';
```
