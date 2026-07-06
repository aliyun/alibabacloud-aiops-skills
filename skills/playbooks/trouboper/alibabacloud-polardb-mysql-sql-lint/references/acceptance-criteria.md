# Acceptance Criteria: alibabacloud-polardb-mysql-sql-lint

**Scenario**: PolarDB MySQL SQL pre-release assessment
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — `das` exists as a valid product

```bash
# ✅ CORRECT
aliyun das --help
```

### 2. Commands — verify actions exist under `das`

```bash
# ✅ CORRECT (plugin mode)
aliyun das create-request-diagnosis --help
aliyun das get-request-diagnosis-result --help

# ❌ INCORRECT (PascalCase / non-plugin mode)
aliyun das CreateRequestDiagnosis
aliyun das GetRequestDiagnosisResult
```

### 3. Parameters — verify each parameter name exists

```bash
# ✅ CORRECT (plugin mode parameters)
aliyun das create-request-diagnosis \
  --instance-id pc-xxxxx \
  --database test_db \
  --sql "SELECT * FROM t" \
  --endpoint das.cn-shanghai.aliyuncs.com

# ❌ INCORRECT (PascalCase parameters)
aliyun das create-request-diagnosis \
  --InstanceId pc-xxxxx \
  --Database test_db \
  --Sql "SELECT * FROM t"
```

### 4. Result retrieval uses `--message-id` not `--task-id`

```bash
# ✅ CORRECT
aliyun das get-request-diagnosis-result \
  --instance-id pc-xxxxx \
  --message-id <task-id>

# ❌ INCORRECT
aliyun das get-request-diagnosis-result \
  --instance-id pc-xxxxx \
  --task-id <task-id>
```

### 5. DAS endpoint is always fixed

```bash
# ✅ CORRECT — always use cn-shanghai endpoint
--endpoint das.cn-shanghai.aliyuncs.com

# ❌ INCORRECT — do not parameterize endpoint by region
--endpoint das.cn-hangzhou.aliyuncs.com
```

### 6. Instance validation uses `describe-instance-das-pro`

```bash
# ✅ CORRECT: Validate instance before DAS diagnosis
aliyun das describe-instance-das-pro \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --instance-id pc-xxxxx

# ❌ INCORRECT: Skip validation, directly run diagnosis with unverified ID
aliyun das create-request-diagnosis \
  --instance-id pc-uf6xxxxxxxxx \  # Fake ID, will fail later
  --database db --sql "..."

# ❌ INCORRECT: Use non-existent API for validation
aliyun das get-instance --instance-id pc-xxxxx  # This command doesn't exist!
```

---

## Correct Workflow Patterns

### 1. Always validate instance, then run static linting AND DAS diagnosis

```bash
# ✅ CORRECT: Full workflow with validation
aliyun das describe-instance-das-pro --endpoint das.cn-shanghai.aliyuncs.com --instance-id pc-xxx
python3 scripts/sql_lint.py --instance-id pc-xxx --sql "..." --region cn-shanghai
aliyun das create-request-diagnosis --instance-id pc-xxx --database db --sql "..."
sleep 5
aliyun das get-request-diagnosis-result --instance-id pc-xxx --message-id <id>

# ❌ INCORRECT: Skip validation and only static linting
python3 scripts/sql_lint.py --instance-id pc-xxx --sql "..."
# (missing instance validation AND DAS diagnosis)
```

### 2. Never connect to database directly

```bash
# ❌ INCORRECT: Direct database connection
mysql -h<host> -u<user> -p -e "SHOW CREATE TABLE users"
mysql -h<host> -u<user> -p -e "SELECT COUNT(*) FROM large_table"

# ✅ CORRECT: API-only approach
aliyun das create-request-diagnosis --instance-id pc-xxx --database db --sql "..."
```

### 3. Always collect required parameters from user

```
# ✅ CORRECT: Ask user for all required info
Required: Instance ID, Database Name, SQL Statement

# ❌ INCORRECT: Assume or hardcode values
--instance-id pc-default  # Never assume
--database mysql          # Default is 'mysql' but should confirm with user
```

---

## Safety Criteria

| Criterion | Expected |
|-----------|----------|
| Direct DB connection | NEVER |
| COUNT(*) on unknown tables | NEVER |
| Table structure fetch | NEVER (API doesn't exist) |
| Instance validation | ALWAYS run before DAS diagnosis |
| Static linting | ALWAYS run |
| DAS diagnosis | ALWAYS run after static linting |
| User parameter confirmation | ALWAYS before execution |
| Output disclaimer | ALWAYS include [NOTICE] section |
