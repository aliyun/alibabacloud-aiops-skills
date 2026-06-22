# Acceptance Criteria: alibabacloud-history-lock-diagnose

**Scenario**: PolarDB/RDS MySQL Historical Lock Wait Root Cause Analysis
**Purpose**: Skill testing acceptance criteria — validate CLI commands, diagnosis output, and lock type coverage

---

## 1. Correct CLI Command Patterns

### 1.1 Credential Verification
#### CORRECT
```bash
aliyun configure list
```

#### INCORRECT
```bash
# NEVER print AK values
echo $ALIBABA_CLOUD_ACCESS_KEY_ID

# NEVER configure with literal AK/SK
aliyun configure set --mode AK --access-key-id LTAI5t... --access-key-secret abc123...
```

### 1.2 SQL Insight Config Check
#### CORRECT
```bash
aliyun das describe-sql-log-config \
  --instance-id pc-bp1xxxxx \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

#### INCORRECT
```bash
# Wrong: PascalCase action name (must use plugin mode)
aliyun das DescribeSqlLogConfig --InstanceId pc-bp1xxxxx

# Wrong: missing --endpoint (DAS endpoint is always das.cn-shanghai.aliyuncs.com)
aliyun das describe-sql-log-config --instance-id pc-bp1xxxxx
```

### 1.3 SQL Audit Hot Data Query (Primary Data Source)
#### CORRECT
```bash
aliyun das get-das-sql-log-hot-data \
  --instance-id pc-bp1xxxxx \
  --start 1749370000000 \
  --end 1749380000000 \
  --max-records-per-page 500 \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

#### INCORRECT
```bash
# Wrong: --page-size instead of --max-records-per-page
aliyun das get-das-sql-log-hot-data --instance-id pc-bp1xxxxx --page-size 500

# Wrong: second-level timestamps (must be milliseconds)
aliyun das get-das-sql-log-hot-data --instance-id pc-bp1xxxxx --start 1749370000 --end 1749380000

# Wrong: missing --user-agent
aliyun das get-das-sql-log-hot-data --instance-id pc-bp1xxxxx --start 1749370000000 --end 1749380000000
```

### 1.4 Deadlock History Query
#### CORRECT
```bash
aliyun das get-dead-lock-history \
  --instance-id pc-bp1xxxxx \
  --start-time 1749370000000 \
  --end-time 1749380000000 \
  --source AUTO \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

#### INCORRECT
```bash
# Wrong: --start/--end instead of --start-time/--end-time (different from GetDasSQLLogHotData)
aliyun das get-dead-lock-history --instance-id pc-bp1xxxxx --start 1749370000000 --end 1749380000000
```

### 1.5 Deadlock Detail Query
#### CORRECT
```bash
aliyun das get-dead-lock-detail \
  --instance-id pc-bp1xxxxx \
  --text-id {TextId} \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

### 1.6 Current Session Query (Fallback)
#### CORRECT
```bash
aliyun das get-mysql-all-session-async \
  --instance-id pc-bp1xxxxx \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

### 1.7 Local Commands (No --user-agent)
#### CORRECT
```bash
# Local commands do NOT support --user-agent
aliyun version
aliyun configure list
aliyun plugin list
```

#### INCORRECT
```bash
# Wrong: --user-agent on local commands causes "invalid flag" error
aliyun version --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
aliyun configure list --user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

---

## 2. Diagnosis Script Behavior

### 2.1 Pre-check: SQL Insight Config
The script must call `DescribeSqlLogConfig` before querying audit data and verify:
- `SqlLogEnable` is true (SQL Insight enabled)
- `HotEnable` is true (hot data available)
- `HotRetention` > 0 (retention period configured)
- Problem time is within hot data retention window

#### CORRECT behavior
```
✅ SQL Insight enabled (hot: 1d, cold: 29d)
```

#### CORRECT behavior (expired data)
```
⚠️  Problem time (2026-05-01 10:00:00) is 39 days ago, exceeds hot data retention (1d).
❌ No blocked SQL or diagnosed thread records found, cannot continue diagnosis
   Likely cause: problem time exceeds hot data retention (1d). Audit data has expired.
```

#### INCORRECT behavior
- Skip `DescribeSqlLogConfig` and directly query `GetDasSQLLogHotData`
- Not checking `HotEnable` (may fail silently when hot data is disabled)

### 2.2 Lock Type Detection
The script must correctly identify and output fine-grained lock types:

| Lock Category | Script Output Label | Trigger Condition |
|--------------|--------------------|--------------------|
| InnoDB Record Lock | `Record Lock` | LockTime > 10ms, same-row DML conflict |
| Exclusive Lock | `Exclusive Lock (X Lock)` | Blocker uses `SELECT ... FOR UPDATE` |
| Shared Lock | `Shared Lock (S Lock)` | Blocker uses `LOCK IN SHARE MODE` |
| Gap Lock | `Gap Lock` | RR isolation, range DELETE/UPDATE blocks INSERT |
| INSERT Intention Lock | `INSERT Intention Lock` | INSERT holds Next-Key Lock blocking DELETE |
| SERIALIZABLE Next-Key | `SERIALIZABLE Shared Next-Key Lock (S Lock)` | SERIALIZABLE isolation, plain SELECT auto-locks |
| MDL Lock | `MDL (Metadata Lock)` | LockTime <= 10ms, uncommitted DML blocks DDL |
| Flush Lock | `Flush Lock` | FLUSH TABLES cascading blockage |
| Flush + Global Read | `Flush Lock + Global Read Lock` | FLUSH TABLES WITH READ LOCK |
| Deadlock | `Deadlock` | State=1213, InnoDB deadlock detection |

### 2.3 Diagnosis Output Format
The script must output structured steps:

```
Step 1: Extract table and WHERE conditions from user SQL
Step 2: Query blocked SQL (+/-5 minutes)
Step 3: [Lock-type specific analysis]
Step 4: Time overlap analysis results
Step 5: Full SQL timeline
Step 6: Diagnosis conclusion
   1. Lock type: {fine-grained label}
   2. Table: {table_name}
   3. WHERE conditions: {id=1,2}
```

### 2.4 Blocking Chain Rendering
Must show lock holder thread timeline with annotations:

```
🔗 Blocking chain:
① Thread {holder_id} (lock holder)
  YYYY-MM-DD HH:MM:SS.mmm  BEGIN; Begin transaction
  YYYY-MM-DD HH:MM:SS.mmm  DELETE FROM accounts WHERE id=1; Transaction uncommitted, holds lock 50s
② Thread {blocked_id} (diagnosed thread)
  YYYY-MM-DD HH:MM:SS.mmm  UPDATE accounts SET balance=1001 WHERE id=1; lock wait timeout
```

### 2.5 Deadlock Diagnosis (CLI Path)
For State=1213, the script must:
1. Call `CreateLatestDeadLockAnalysis` to trigger analysis
2. Call `GetDeadLockHistory` with time window [-1h, +24h] (DAS filters by gmtCreate, not lockTime)
3. Validate DAS deadlock matches user time (lockTime diff < 60s) and thread ID
4. Call `GetDeadLockDetail` for full deadlock graph
5. Output winner/victim threads with hold/wait lock info

#### INCORRECT behavior
- Using narrow time window (±5min) for `GetDeadLockHistory` — DAS gmtCreate can lag hours behind lockTime
- Not validating the returned deadlock is the same event the user reported

---

## 3. Key Parameter Validation

### GetDasSQLLogHotData Parameters

| Parameter | CLI Flag | Type | Notes |
|-----------|----------|------|-------|
| InstanceId | `--instance-id` | string | rm-xxx (RDS) or pc-xxx (PolarDB) |
| Start | `--start` | long | Millisecond Unix timestamp |
| End | `--end` | long | Millisecond Unix timestamp |
| MaxRecordsPerPage | `--max-records-per-page` | int | NOT `--page-size` |
| QueryKeyword | `--query-keyword` | string | Server-side pre-filter |
| LogicalOperator | `--logical-operator` | string | `or` / `and` for QueryKeyword |

### GetDeadLockHistory Parameters

| Parameter | CLI Flag | Type | Notes |
|-----------|----------|------|-------|
| InstanceId | `--instance-id` | string | rm-xxx or pc-xxx |
| StartTime | `--start-time` | long | NOT `--start` (differs from GetDasSQLLogHotData) |
| EndTime | `--end-time` | long | NOT `--end` |
| Source | `--source` | string | `AUTO` |

---

## 4. Lock Scenario Coverage (19 Scenarios)

The skill must correctly diagnose all 19 lock scenarios:

| # | Scenario | Lock Type | Key Diagnostic Logic |
|---|----------|-----------|---------------------|
| 1 | Same-column row lock | Record Lock | WHERE condition precise matching |
| 2 | Chained lock wait (A→B→C) | Record Lock | Trace blocking chain to root cause |
| 3 | Different-column row lock | Record Lock | Full-table DML fallback when WHERE mismatch |
| 4 | Full-table DELETE | Record Lock | No WHERE condition, same-table DML analysis |
| 5 | Uncommitted transaction MDL | MDL Lock | LockTime ≤ 10ms → MDL path, find uncommitted DML |
| 6 | Long SELECT MDL | MDL Lock | Find long-running SELECT holding shared MDL |
| 7 | INSERT intention lock | INSERT Intention Lock | INSERT holds Next-Key Lock |
| 8 | Gap Lock (RR isolation) | Gap Lock | Detect SET transaction_isolation = RR |
| 9 | FLUSH TABLES cascade | Flush Lock | Long SELECT → FLUSH blocked → DML blocked |
| 10 | FLUSH WITH READ LOCK | Flush Lock + Global Read Lock | FTWRL global lock detection |
| 11 | Row lock blocks FLUSH | Flush Lock | Row lock holder → FLUSH → subsequent DML |
| 12 | SELECT FOR UPDATE | Exclusive Lock (X Lock) | Detect FOR UPDATE in blocker SQL |
| 13 | LOCK IN SHARE MODE | Shared Lock (S Lock) | Detect LOCK IN SHARE MODE in blocker SQL |
| 14 | SERIALIZABLE SELECT | SERIALIZABLE Shared Next-Key Lock | Detect SET SERIALIZABLE + plain SELECT |
| 15 | Deadlock | Deadlock | State=1213 → CLI deadlock detail → winner/victim |
| 16 | MDL queue cascade | MDL Lock | DML → DDL queues X lock → blocks subsequent SELECT |
| 17 | INSERT ON DUPLICATE KEY | Record Lock | Same-row UPDATE holds lock blocking IODKU |
| 18 | LOCK TABLES WRITE | MDL Lock | Detect LOCK TABLES WRITE holding table-level lock |
| 19 | Cross-table transaction | Record Lock | Transaction spans multiple tables, lock on target table |

---

## 5. Anti-Pattern Checklist

| Anti-Pattern | Why It's Wrong | Correct Approach |
|-------------|----------------|------------------|
| Hardcoded AK/SK | Security risk | Use `aliyun configure list` to check |
| Missing `--user-agent` on API commands | Cannot trace call origin | Add full UA with session-id |
| Adding `--user-agent` to local commands | Causes "invalid flag" error | Only on API commands (das, rds, polardb) |
| Using `--page-size` for DAS | Wrong parameter name | Use `--max-records-per-page` |
| Second-level timestamps | DAS requires milliseconds | Multiply by 1000 |
| Narrow time window for deadlock history | DAS gmtCreate lags behind lockTime | Use [-1h, +24h] window |
| Treating LockTime=0 as "no lock wait" | MDL lock wait not recorded in LockTime | Check for concurrent DDL/FLUSH |
| Assuming timed-out SQL holds locks | State=1205/1317 means lock NOT acquired | Only State=0 SQL can be lock holder |
| PascalCase CLI commands | Must use plugin mode | `get-das-sql-log-hot-data` not `GetDasSQLLogHotData` |
| Using `aliyun configure ai-mode` | Deprecated | Use per-command `--user-agent` |
| Skipping `DescribeSqlLogConfig` check | May fail silently on disabled instances | Always check before querying |
