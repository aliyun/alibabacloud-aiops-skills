# Implementation Notes & Known Issues

This document contains development notes, bug fixes, and technical details for the SQL Lint skill.

---

## Critical Implementation Details

### 1. RULE-001 (Require InnoDB) - Multi-line Regex Fix

**Issue**: Multi-line CREATE TABLE statements failed to detect ENGINE clause

**Root Cause**: Regex `.*` doesn't match newlines by default

**Fix Applied**: Added `re.DOTALL` flag to regex patterns
```python
re.search(r'CREATE\s+TABLE.*ENGINE\s*=\s*(\w+)', sql, re.IGNORECASE | re.DOTALL)
```

**Impact**: All multi-line CREATE TABLE statements now correctly detect non-InnoDB engines

---

### 2. RULE-061 (Merge ALTER TABLE) - Multi-Statement Detection

**Issue**: Detecting consecutive ALTER TABLE statements that target the same table

**Root Cause**: 
- Rule requires seeing multiple statements simultaneously

**Fix Applied**: 
1. Added `_check_merge_alter_table()` method to group consecutive ALTER statements by table name
2. `lint_sql()` now splits multi-statement input by `;` and calls `_check_merge_alter_table()` across all statements
3. `lint_sql_file()` also supports RULE-061 detection

**Usage**:
```python
# ✅ Works: Multi-statement via --sql
engine.lint_sql('ALTER TABLE users ADD COLUMN age INT; ALTER TABLE users ADD COLUMN name VARCHAR(50);')

# ✅ Works: File-level detection
engine.lint_sql_file('migration.sql')
```

---

### 3. DAS Endpoint is Fixed

**Critical**: DAS endpoint is always `das.cn-shanghai.aliyuncs.com` regardless of instance region

```python
self.endpoint = 'das.cn-shanghai.aliyuncs.com'  # Fixed, not configurable
```

**Reason**: DAS is a centralized service, all regions use the same endpoint

**Migration Note**: Do NOT parameterize this endpoint based on `--region` argument

---

### 4. DAS Diagnosis Uses `--message-id` NOT `--task-id`

**Critical**: Common mistake is using wrong parameter name

```bash
# ✅ CORRECT
aliyun das get-request-diagnosis-result --message-id <task-id>

# ❌ WRONG (will fail)
aliyun das get-request-diagnosis-result --task-id <task-id>
```

**API Response**:
```json
{
  "Code": 200,
  "Data": "<message-id>",  // This is the MessageId, not TaskId
  "Message": "Successful"
}
```

---

### 5. SQL Lint Engine Returns List[Dict], Not Dict

**Important**: `lint_sql()` returns a list, not a single dict

```python
# ✅ CORRECT
issues = engine.lint_sql(sql)  # Returns List[Dict]
for issue in issues:
    print(issue['rule_id'])

# ❌ WRONG (will cause AttributeError)
issue = engine.lint_sql(sql)
print(issue['rule_id'])  # Error: 'list' object has no attribute 'rule_id'
```

---

### 6. Test Framework Auto-Detects Multi-Statement Cases

**Implementation**: Test framework (`run-tests.py`) automatically detects multi-statement test cases and uses file-level linting

```python
# test-suite/scripts/run-tests.py line 67-96
def run_test_case(test_case, engine):
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    
    if len(statements) > 1:
        # Multi-statement: use lint_sql_file
        issues = engine.lint_sql_file(temp_file)
    else:
        # Single statement: use lint_sql
        issues = engine.lint_sql(sql)
```

**Migration Note**: When porting test framework, preserve this auto-detection logic

---

## Test Coverage Summary

**Test Results**: 94/94 (100% pass rate)
- DDL Tests: 28/28 passed
- DML Tests: 66/66 passed

**Test Files**:
- `test-suite/test-cases/ddl-tests.sql` - 28 DDL test cases
- `test-suite/test-cases/dml-tests.sql` - 66 DML test cases
- Missing: `naming-tests.sql`, `performance-tests.sql` (not yet created)

---

## Performance Characteristics

### Static Linting
- **Speed**: Instant (< 0.1s per SQL statement)
- **Resource Usage**: Minimal (pure Python regex matching)
- **Database Connection**: NOT required

### DAS Dynamic Diagnosis
- **Speed**: ~15-20 seconds per SQL (includes API calls)
- **Resource Usage**: Network API calls to DAS
- **Database Connection**: NOT required (uses DAS API)
- **Wait Time**: 15 seconds hard-coded (could be optimized with polling)

**Optimization Opportunity**: Replace fixed 15s wait with polling mechanism:
```python
# Current: Fixed wait
time.sleep(15)

# Better: Poll until complete
for _ in range(30):  # Max 30 seconds
    result = get_diagnosis_result(message_id)
    if result['status'] == 'completed':
        break
    time.sleep(1)
```

---

## Rule Categories & Count

| Category | Rule Count | Rule IDs |
|----------|-----------|----------|
| Engine | 1 | RULE-001 |
| Naming | 4 | RULE-010, 011, 012, 073 |
| Statement | 6 | RULE-020, 021, 022, 023, 024, 072 |
| Table | 4 | RULE-030, 031, 032, 071 |
| Column | 6 | RULE-040, 041, 042, 043, 044, 045 |
| Index | 4 | RULE-050, 051, 052, 053 |
| Schema | 2 | RULE-060, 061 |
| System | 1 | RULE-070 |
| **Total** | **28** | |

---

## Known Limitations

1. **RULE-061**: Works in both `lint_sql()` (multi-statement) and `lint_sql_file()` modes
2. **DAS Wait Time**: Fixed 15s wait, not adaptive
3. **Index DDL Extraction**: DAS returns index recommendations but DDL sometimes shows as N/A
4. **Test Files Missing**: `naming-tests.sql` and `performance-tests.sql` not yet created
5. **No Interactive Mode**: Cannot prompt user for confirmation before suggesting changes

---

## Migration Checklist

When porting this skill to another platform, ensure:

- [ ] Preserve `re.DOTALL` flag in RULE-001 regex patterns
- [x] RULE-061 works in both `lint_sql()` and `lint_sql_file()` modes
- [ ] Keep DAS endpoint fixed to `das.cn-shanghai.aliyuncs.com`
- [ ] Use `--message-id` (not `--task-id`) for DAS API calls
- [ ] Maintain `lint_sql()` return type as `List[Dict]`
- [ ] Preserve multi-statement auto-detection in test framework
- [ ] Test all 28 rules with provided test suite (94 test cases)
- [ ] Verify DAS API permissions in RAM policy
- [ ] Do NOT connect to database for metadata queries (safety rule)
