# Transaction Lifecycle Judgment Rules

This document details the MySQL transaction lifecycle judgment rules, used to accurately identify blocking sources during lock wait diagnosis.

## Transaction Lifecycle Overview

A complete transaction lifecycle includes:
1. **Transaction Start** - Explicitly or implicitly begin a transaction
2. **Transaction Execution** - Execute SQL statements (may acquire locks)
3. **Transaction End** - Explicitly or implicitly commit/rollback, releasing locks

**Core Judgment Logic:**
```
If a transaction has started but has not yet ended -> The transaction may hold locks -> It may be the blocking source
```

---

## Transaction Start Indicators

If **any** of the following conditions are met, the transaction has started:

| SQL Statement | Description |
|----------|------|
| `SET autocommit=0;` | Disable auto-commit mode |
| `BEGIN;` | Begin transaction (recommended) |
| `START TRANSACTION;` | Begin transaction (standard SQL) |

**Examples:**
```sql
-- Method 1: Using BEGIN
BEGIN;
UPDATE accounts SET balance=balance-100 WHERE id=1;
-- Transaction in progress...

-- Method 2: Using START TRANSACTION
START TRANSACTION;
DELETE FROM orders WHERE status='expired';
-- Transaction in progress...

-- Method 3: Disabling auto-commit
SET autocommit=0;
INSERT INTO logs VALUES ('test');
-- All subsequent SQL statements are in the same transaction until COMMIT/ROLLBACK
```

---

## Transaction End Indicators

Transaction endings are divided into two major categories: **explicit endings** and **implicit endings**.

### (A) Explicit Ending

| SQL Statement | Description | Lock Release |
|----------|------|--------|
| `COMMIT;` | Commit transaction, save changes | Releases all locks |
| `ROLLBACK;` | Rollback transaction, undo changes | Releases all locks |

**Example:**
```sql
BEGIN;
UPDATE accounts SET balance=1000 WHERE id=1;
COMMIT;  -- Transaction ends, locks released
```

---

### (B) Implicit Commit

The following statements will **automatically commit the current transaction** (even without an explicit COMMIT):

#### 1. DDL Statements (Data Definition Language)

| Category | SQL Statements |
|------|----------|
| **ALTER** | ALTER EVENT, ALTER FUNCTION, ALTER PROCEDURE, ALTER SERVER, ALTER TABLE, ALTER TABLESPACE, ALTER VIEW |
| **CREATE** | CREATE DATABASE, CREATE EVENT, CREATE FUNCTION, CREATE INDEX, CREATE PROCEDURE, CREATE ROLE, CREATE SERVER, CREATE SPATIAL REFERENCE SYSTEM, CREATE TABLE, CREATE TABLESPACE, CREATE TRIGGER, CREATE VIEW |
| **DROP** | DROP DATABASE, DROP EVENT, DROP FUNCTION, DROP INDEX, DROP PROCEDURE, DROP ROLE, DROP SERVER, DROP SPATIAL REFERENCE SYSTEM, DROP TABLE, DROP TABLESPACE, DROP TRIGGER, DROP VIEW |
| **Other** | INSTALL PLUGIN, RENAME TABLE, TRUNCATE TABLE, UNINSTALL PLUGIN |

**Example:**
```sql
BEGIN;
UPDATE accounts SET balance=1000 WHERE id=1;
-- Transaction in progress, holding locks...

ALTER TABLE accounts ADD COLUMN status VARCHAR(10);
-- Implicit commit! The preceding UPDATE is automatically committed, locks released
```

#### 2. Account/Privilege Management Statements

| SQL Statement | Description |
|----------|------|
| `CREATE USER ...` | Create user |
| `DROP USER ...` | Drop user |
| `GRANT ...` | Grant privileges |
| `REVOKE ...` | Revoke privileges |
| `SET PASSWORD ...` | Set password |
| `RENAME USER ...` | Rename user |

**Example:**
```sql
BEGIN;
DELETE FROM accounts WHERE id=1;
-- Transaction in progress...

GRANT SELECT ON db.* TO 'user'@'%';
-- Implicit commit! The DELETE is automatically committed
```

#### 3. Replication-Related Statements

| SQL Statement | Description |
|----------|------|
| `START REPLICA` | Start replication |
| `STOP REPLICA` | Stop replication |
| `RESET REPLICA` | Reset replication |
| `CHANGE REPLICATION SOURCE TO` | Change replication source |
| `CHANGE MASTER TO` | Change master (legacy syntax) |

#### 4. Data Loading Statements

| SQL Statement | Description |
|----------|------|
| `LOAD DATA INFILE '...' INTO TABLE ...` | Load data from file |

#### 5. Table Maintenance and Cache Statements

| SQL Statement | Description |
|----------|------|
| `ANALYZE TABLE` | Analyze table statistics |
| `CACHE INDEX` | Cache index |
| `CHECK TABLE` | Check table |
| `FLUSH` | Flush |
| `LOAD INDEX INTO CACHE` | Load index into cache |
| `OPTIMIZE TABLE` | Optimize table |
| `REPAIR TABLE` | Repair table |
| `RESET` | Reset (**excluding** RESET PERSIST) |

#### 6. Lock and autocommit-Related Statements

| SQL Statement | Description |
|----------|------|
| `BEGIN` | Begin new transaction (commits the previous transaction) |
| `START TRANSACTION` | Begin new transaction (commits the previous transaction) |
| `LOCK TABLES` | Lock tables |
| `UNLOCK TABLES` | Unlock tables |
| `SET autocommit = 1` | Enable auto-commit (if currently not 1) |

**Example:**
```sql
SET autocommit=0;
BEGIN;
UPDATE accounts SET balance=1000 WHERE id=1;
-- Transaction in progress...

BEGIN;  -- A new BEGIN implicitly commits the previous transaction
SELECT * FROM orders;
-- The preceding UPDATE has been automatically committed
```

---

### (C) Implicit Rollback

The following operations will **automatically rollback the current transaction** (equivalent to executing ROLLBACK):

| Operation | Description | Trigger Scenario |
|------|------|----------|
| `LOGOUT;` | Session exit | Client disconnects |
| `COM_RESET_CONNECTION` | Reset connection | Connection pool resets connection |
| `COM_CHANGE_USER` | Switch user | Connection pool switches user |

**Example:**
```sql
BEGIN;
UPDATE accounts SET balance=1000 WHERE id=1;
-- Transaction in progress, holding locks...

-- Client suddenly disconnects (LOGOUT)
-- Transaction is implicitly rolled back, locks released, UPDATE undone
```

**Important:**
- Implicit rollback will **undo** all uncommitted changes
- Implicit commit will **save** all uncommitted changes
- Both will **release locks**

---

## Transaction Judgment Flowchart

```
SQL Execution
  |
  +-- Is it BEGIN/START TRANSACTION/SET autocommit=0?
  |   +-- YES -> Transaction started, record time point T1
  |
  +-- Is it UPDATE/DELETE/INSERT/SELECT...FOR UPDATE?
  |   +-- YES -> May acquire locks, record SQL and locked resources
  |
  +-- Is it COMMIT/ROLLBACK?
  |   +-- YES -> Transaction explicitly ended, locks released
  |
  +-- Is it DDL/GRANT/LOAD DATA or other implicit commit statement?
  |   +-- YES -> Transaction implicitly committed, locks released
  |
  +-- Is it LOGOUT/connection disconnect?
  |   +-- YES -> Transaction implicitly rolled back, locks released
  |
  +-- Other SQL
      +-- Continue execution, transaction state unchanged
```

---

## Practical Case Analysis

### Case 1: Lock Wait Caused by Uncommitted Transaction

**Timeline:**
```
09:37:08.489  Thread 1993: BEGIN                           <- Transaction started
09:37:08.887  Thread 1993: DELETE FROM accounts WHERE id=1  <- Row lock acquired
09:38:04.442  Thread 1999: UPDATE accounts SET balance=1001 WHERE id=1  <- Blocked
```

**Analysis:**
```
Thread 1993:
  OK 09:37:08 BEGIN -> Transaction started
  OK 09:37:08 DELETE -> Acquired row lock on id=1
  X  No COMMIT/ROLLBACK between 09:37:08 and 09:38:04
  X  No DDL statement (implicit commit)
  X  No LOGOUT (implicit rollback)
  -> Transaction is still active, holding locks!

Thread 1999:
  X  No BEGIN -> Running in autocommit=1 mode
  OK 09:38:04 UPDATE -> Needs to acquire row lock on id=1
  Timer: Timed out after waiting 50.003 seconds (Error 1205)

Conclusion: Thread 1993 is the lock source
```

---

### Case 2: DDL Implicit Commit Releases Locks

**Timeline:**
```
10:00:00  Thread 2001: BEGIN
10:00:05  Thread 2001: UPDATE accounts SET balance=2000 WHERE id=1  <- Lock acquired
10:00:10  Thread 2001: ALTER TABLE accounts ADD COLUMN status VARCHAR(10)  <- Implicit commit
10:00:15  Thread 2002: UPDATE accounts SET balance=3000 WHERE id=1  <- Not blocked
```

**Analysis:**
```
Thread 2001:
  OK 10:00:00 BEGIN -> Transaction started
  OK 10:00:05 UPDATE -> Acquired row lock on id=1
  OK 10:00:10 ALTER TABLE -> Implicit commit! Transaction ended, locks released
  -> After 10:00:10, Thread 2001 no longer holds locks

Thread 2002:
  OK 10:00:15 UPDATE -> Can acquire lock normally
  -> Not blocked

Conclusion: DDL statement triggered implicit commit, locks released
```

---

### Case 3: LOGOUT Implicit Rollback

**Timeline:**
```
11:00:00  Thread 3001: BEGIN
11:00:05  Thread 3001: DELETE FROM accounts WHERE id=1  <- Lock acquired
11:00:30  Thread 3001: LOGOUT  <- Implicit rollback
11:00:35  Thread 3002: UPDATE accounts SET balance=4000 WHERE id=1  <- Not blocked
```

**Analysis:**
```
Thread 3001:
  OK 11:00:00 BEGIN -> Transaction started
  OK 11:00:05 DELETE -> Acquired row lock on id=1
  OK 11:00:30 LOGOUT -> Implicit rollback! Transaction undone, locks released
  -> After 11:00:30, Thread 3001 no longer holds locks, DELETE undone

Thread 3002:
  OK 11:00:35 UPDATE -> Can acquire lock normally
  -> Not blocked

Conclusion: LOGOUT triggered implicit rollback, locks released
```

---

## Diagnostic Recommendations

### 1. Quick Lock Source Identification

```python
def is_transaction_active(sql_logs, thread_id, target_time):
    """
    Determine whether the specified thread still has an active transaction at the target time point

    Args:
        sql_logs: List of SQL log entries
        thread_id: Thread ID
        target_time: Target time point

    Returns:
        bool: True=transaction active (may hold locks), False=transaction ended
    """
    # Get all SQL for this thread before the target time
    thread_sqls = [
        log for log in sql_logs 
        if log['ThreadID'] == thread_id and log['OriginTime'] < target_time
    ]
    
    # Sort by time
    thread_sqls.sort(key=lambda x: x['OriginTime'])
    
    transaction_started = False
    
    for sql in thread_sqls:
        sql_text = sql['SQLText'].upper()
        
        # Check transaction start
        if any(cmd in sql_text for cmd in ['BEGIN', 'START TRANSACTION']):
            transaction_started = True
        
        # Check explicit ending
        if any(cmd in sql_text for cmd in ['COMMIT', 'ROLLBACK']):
            transaction_started = False
        
        # Check implicit commit (DDL)
        if any(cmd in sql_text for cmd in [
            'ALTER', 'CREATE', 'DROP', 'TRUNCATE', 'RENAME',
            'GRANT', 'REVOKE', 'LOAD DATA'
        ]):
            transaction_started = False
        
        # Check implicit rollback
        if 'LOGOUT' in sql_text:
            transaction_started = False
    
    return transaction_started
```

### 2. Find Lock Source

```python
def find_lock_source(sql_logs, blocked_sql):
    """
    Find the source of the lock

    Args:
        sql_logs: List of SQL log entries
        blocked_sql: The blocked SQL record

    Returns:
        dict: Lock source information, or None
    """
    blocked_time = blocked_sql['OriginTime']
    blocked_thread = blocked_sql['ThreadID']
    
    # Find all SQL executed before the blocked SQL
    prior_sqls = [log for log in sql_logs if log['OriginTime'] < blocked_time]
    
    # Group by thread
    threads = {}
    for sql in prior_sqls:
        tid = sql['ThreadID']
        if tid != blocked_thread:  # Exclude the blocked thread
            if tid not in threads:
                threads[tid] = []
            threads[tid].append(sql)
    
    # Check each thread for an active transaction
    for thread_id, sqls in threads.items():
        if is_transaction_active(sqls, thread_id, blocked_time):
            # Check for lock-acquiring operations
            for sql in sqls:
                sql_text = sql['SQLText'].upper()
                if any(cmd in sql_text for cmd in [
                    'UPDATE', 'DELETE', 'INSERT', 'SELECT', 'FOR UPDATE'
                ]):
                    return {
                        'thread_id': thread_id,
                        'lock_sql': sql['SQLText'],
                        'lock_time': sql['OriginTime'],
                        'reason': 'Transaction uncommitted, holding locks'
                    }
    
    return None
```

---

## Common Misconceptions

### Misconception 1: Only COMMIT/ROLLBACK Can End a Transaction

**Incorrect understanding:** "The transaction has no COMMIT, so it must still be in progress"

**Correct understanding:** DDL, GRANT, LOGOUT, etc. can also end a transaction (implicit commit or rollback)

---

### Misconception 2: No Locks in autocommit=1 Mode

**Incorrect understanding:** "autocommit=1, every SQL auto-commits, so there won't be lock waits"

**Correct understanding:** Even a single UPDATE/DELETE acquires locks during execution, they are just released quickly

---

### Misconception 3: Ignoring Implicit Rollback

**Incorrect understanding:** "The client disconnected, so the transaction should still be active"

**Correct understanding:** LOGOUT, connection disconnect, and COM_RESET_CONNECTION will implicitly rollback the transaction

---

## References

- [MySQL Transaction Documentation](https://dev.mysql.com/doc/refman/8.0/en/commit.html)
- [MySQL Implicit Commit Documentation](https://dev.mysql.com/doc/refman/8.0/en/implicit-commit.html)
- [Alibaba Cloud DAS Lock Analysis](https://help.aliyun.com/zh/das/user-guide/lock-analysis/)

---

**Document Version:** v1.0  
**Last Updated:** 2026-04-13  
**Maintainer:** alibabacloud-history-lock-diagnose skill
