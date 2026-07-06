# Safety Guidelines

This skill performs **READ-ONLY** assessment only:
- ❌ Never executes SQL statements against your database
- ❌ Never creates/modifies indexes or tables
- ❌ Never performs DML operations
- ✅ Only analyzes SQL statements and provides recommendations
- ✅ All changes must be manually reviewed and executed by users

## Usage Disclaimer

**All optimization suggestions are for reference only.** Before deploying, always evaluate applicability based on your business scenario and data characteristics.

## Critical Safety Rules

### 1. Never Execute COUNT(*) on Unknown Tables

**Problem**: Running `COUNT(*)` on large tables (millions/billions of rows) causes:
- Full table scan consuming significant CPU and I/O
- Query execution time from seconds to minutes
- Resource contention affecting production workloads
- Potential locking issues

**Safe Alternative**:
- Use DAS diagnosis API (`create-request-diagnosis`) which provides row estimates via execution plan analysis without direct database connection.
- This skill does NOT connect to the database — all analysis is done through static linting and DAS API.

### 2. No Table Structure Access

**Critical Limitation**: DAS API does NOT provide any interface to fetch table structure

**What You CANNOT Do**:
- ❌ Fetch table schema (columns, types, keys)
- ❌ Get table statistics (row count, data size)
- ❌ Check index information
- ❌ Analyze column types (TEXT, BLOB, etc.)

**What You CAN Do**:
- ✅ Run static SQL linting (28+ rules)
- ✅ Use DAS `create-request-diagnosis` for execution plan
- ✅ Get index recommendations from DAS
- ✅ Provide generic best practice suggestions

**Risk Assessment Limitations**:
Since table structure cannot be accessed, risk assessments can ONLY include:
1. Static rule violations (from sql_lint.py)
2. Generic SQL pattern warnings (e.g., DELETE without WHERE)
3. DAS execution plan analysis (if SQL is executable)

**DO NOT** report:
- Table size or row count
- Column types or structure
- Specific undo log impact
- Table-specific performance metrics

**Prohibited Operations**:
- ❌ `COUNT(*)` on unknown/large tables
- ❌ `SELECT *` without LIMIT on large tables
- ❌ Complex JOINs without EXPLAIN analysis
- ❌ Full table scans (missing indexes)
- ❌ LOCK TABLES or explicit locking
- ❌ ALTER TABLE without online DDL flags

### 3. Always Use Non-Destructive Analysis

**Analysis Workflow** (Safe & API-Only):
1. ✅ Run static linting: `python3 scripts/sql_lint.py --sql "..."`
2. ✅ Create DAS diagnosis: `aliyun das create-request-diagnosis`
3. ✅ Get DAS result: `aliyun das get-request-diagnosis-result`
4. ✅ Provide recommendations (no execution)
5. ⏸️ Wait for user to manually apply changes

**Remember**: 
- ❌ NO direct database connection
- ❌ NO table structure access (API doesn't exist)
- ❌ NO metadata queries
- ✅ ONLY static linting + DAS diagnosis
