# Workflow Examples: Correct vs Incorrect Approaches

## ❌ WRONG Approaches (Don't Do This)

### Mistake 1: Connecting to Database for Metadata

```bash
# WRONG: Don't connect to database to check table structure
mysql -h<host> -u<user> -p -e "SHOW CREATE TABLE ..."
mysql -h<host> -u<user> -p -e "SELECT COUNT(*) FROM ..."
```

**Why it's wrong:**
- `COUNT(*)` on large tables causes full table scan
- Consumes significant CPU, I/O, and memory
- May block production workloads
- Violates safety guidelines
- **NO API exists** for fetching table structure

### Mistake 2: Attempting to Fetch Table Structure

```bash
# WRONG: Don't try to get table structure - NO SUCH API EXISTS
aliyun das describe-dbinstance-table-structure ...  # This API doesn't exist!
mysql -h<host> -u<user> -p -e "DESCRIBE table ..."  # Direct connection forbidden
```

**Why it's wrong:**
- DAS API does NOT provide table structure interface
- aliyun CLI has NO command for this
- Direct database connection is strictly forbidden

### Mistake 3: Skipping DAS Diagnosis When Instance ID Is Available

```bash
# WRONG: Have instance ID but only run static linting
python3 scripts/sql_lint.py --sql "..."  # Missing --instance-id even though user provided one!
```

**Why it's wrong:**
- When user provides instance ID, you MUST use it for DAS diagnosis
- Missing execution plan analysis, index recommendations, and cost estimation
- Note: If user does NOT provide instance ID, static-only mode is perfectly valid

### Mistake 4: Skipping Instance Validation

```bash
# WRONG: Directly run DAS diagnosis with unverified instance ID
aliyun das create-request-diagnosis \
  --instance-id pc-uf6xxxxxxxxx \  # Could be fake/wrong!
  --database order_system --sql "..."
```

**Why it's wrong:**
- Wastes time waiting for DAS task that will eventually fail
- Error messages from `create-request-diagnosis` can be cryptic
- A simple pre-check (`describe-instance-das-pro`) catches bad IDs immediately
- Always validate before running the full workflow

## ✅ CORRECT Approach (Always Do This)

**Step 0: Validate Instance** (catches bad IDs immediately)
```bash
aliyun das describe-instance-das-pro \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --instance-id pc-bp167736gfqyn483x
```
Only stop if the API call itself fails (non-200 Code, network error, permission denied).
`Code: 200` means the instance is valid and reachable — **always proceed to Step 1 and Step 2** regardless of `Data` value. DAS may not return optimization suggestions for small datasets, and that is normal.

**Step 1: Static Linting** (instant, no database connection)
```bash
python3 scripts/sql_lint.py \
  --instance-id pc-bp167736gfqyn483x \
  --sql "SELECT count(*) FROM test_big_records WHERE create_time > '2026-05-06 14:33:47'"
```

**Step 2: DAS Diagnosis** (uses DAS API, no direct DB connection)
```bash
# Create task
TASK_ID=$(aliyun das create-request-diagnosis \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --instance-id pc-bp167736gfqyn483x \
  --database test_db \
  --sql "SELECT count(*) FROM test_big_records WHERE create_time > '2026-05-06 14:33:47'" \
  --output cols=Data | tail -1)

# Get result (after 5s wait)
sleep 5
aliyun das get-request-diagnosis-result \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --instance-id pc-bp167736gfqyn483x \
  --message-id $TASK_ID
```

**Step 3: Combine Results**
- Static rules: 28/28 passed ✅
- DAS diagnosis: Found 1 critical issue 🔴
- Recommendation: Add index on `create_time`
- Expected improvement: 3,964,954x 
