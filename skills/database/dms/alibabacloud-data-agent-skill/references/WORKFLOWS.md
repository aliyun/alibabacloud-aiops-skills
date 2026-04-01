# Typical Workflows

This document contains complete operational workflow examples.

---

## Method 1: Start from Existing Database in Data Center (Recommended)

> **Prerequisite**: The database must already exist in Data Agent Data Center.
>
> **Built-in Demo Database**: `internal_data_employees` is DataAgent's built-in test database, containing employee, department, and salary data, suitable for first-time experience.

```
Step 1  ls          -- List available databases
Step 2  ls --db-id  -- List tables for a specific database, and print db command ready to copy
Step 3  db -q       -- Initiate query/analysis session, output progress and conclusions in real-time
Step 4  attach      -- Connect to existing session (confirm plan / follow-up / view latest results)
```

### Complete Example

```bash
# Step 1: Discover databases
python3 scripts/data_agent_cli.py ls

# Step 2: View tables in built-in test database internal_data_employees and get command template
python3 scripts/data_agent_cli.py ls --db-id <AgentDbId>

# Step 3: Query (copy command from previous step, replace question)
python3 scripts/data_agent_cli.py db \
    --dms-instance-id <DMS_INSTANCE_ID> --dms-db-id <DMS_DB_ID> \
    --instance-name <INSTANCE_NAME> --db-name internal_data_employees \
    --tables "employees,departments,salaries" \
    --session-mode ASK_DATA \
    -q "Which position has the highest salary"

# Step 4: Connect to existing session for follow-up questions
python3 scripts/data_agent_cli.py attach --session-id <SESSION_ID> -q "Calculate average salary by department"
```

---

## Method 2: Discover and Import from DMS Instance to Data Center

> **Use Case**: When Data Agent Data Center doesn't have the database you need.

```
Step 1  dms list-instances    -- Query database instances in DMS
Step 2  dms search-database   -- Search databases in instance
Step 3  dms list-tables       -- List tables in database
Step 4  ls                    -- Check if Data Center already has this database
Step 5  import                -- Import DMS database tables to Data Center
Step 6  db                    -- Initiate query/analysis session
Step 7  attach                -- Connect to existing session
```

### Complete Example

```bash
# 1. Query DMS instance list
python3 scripts/data_agent_cli.py dms list-instances

# 2. Search for target database (get Database ID)
python3 scripts/data_agent_cli.py dms search-database --search-key employees

# 3. View tables in database
python3 scripts/data_agent_cli.py dms list-tables --database-id <DATABASE_ID>

# 4. Check if Data Center already has this database
python3 scripts/data_agent_cli.py ls --search employees

# 5. Import to Data Center (required step)
python3 scripts/data_agent_cli.py import \
    --dms-instance-id <DMS_INSTANCE_ID> \
    --dms-db-id <DMS_DB_ID> \
    --instance-name <INSTANCE_NAME> \
    --db-name employees \
    --tables "departments,employees,salaries"

# 6. Initiate analysis
python3 scripts/data_agent_cli.py db \
    --dms-instance-id <DMS_INSTANCE_ID> --dms-db-id <DMS_DB_ID> \
    --instance-name <INSTANCE_NAME> --db-name employees \
    --tables "departments,employees,salaries" \
    -q "Query the department with highest average salary"
```

---

## Background Execution Best Practices

For long-running `ls` and `db` commands, running in background is recommended:

```bash
# Start ANALYSIS task in background
nohup python3 scripts/data_agent_cli.py db \
    --dms-instance-id <DMS_INSTANCE_ID> --dms-db-id <DMS_DB_ID> \
    --instance-name <INSTANCE_NAME> --db-name internal_data_employees \
    --tables "employees,departments,salaries" \
    --session-mode ANALYSIS \
    -q "Analyze salary distribution and generate report" > analysis.log 2>&1 &

# Get session ID from log
grep "Session ready" analysis.log

# Attach anytime to check progress
python3 scripts/data_agent_cli.py attach --session-id <SESSION_ID>

# If network is interrupted or you want to resume from a specific state, specify checkpoint
python3 scripts/data_agent_cli.py attach --session-id <SESSION_ID> --checkpoint <CHECKPOINT_NUM>
```

**Benefits**:
- Avoid task failure due to network interruption (seamless resume with `--checkpoint` parameter)
- Check progress anytime via `attach`
- Output logs for later review

---

## Session Reuse Workflow

For multiple analyses on the same database, reusing sessions is recommended for efficiency:

```bash
# Analysis 1: Create new session
python3 scripts/data_agent_cli.py db \
    --dms-instance-id <DMS_INSTANCE_ID> --dms-db-id <DMS_DB_ID> \
    --instance-name <INSTANCE_NAME> --db-name internal_data_employees \
    --tables "employees,departments" \
    --session-mode ANALYSIS \
    -q "Analyze 2024 salary growth trends"
# Output: ✅ Async task started. Session ID: abc123xyz

# Analysis 2: Reuse same session, follow-up with details
python3 scripts/data_agent_cli.py attach --session-id abc123xyz -q "Break down salary structure by job level"

# Analysis 3: Modify plan
python3 scripts/data_agent_cli.py attach --session-id abc123xyz -q "Simplify to 3 steps"

# Analysis 4: Confirm execution
python3 scripts/data_agent_cli.py attach --session-id abc123xyz -q "Confirm execution"

# Step 5: Read final results
cat sessions/abc123xyz/progress.log

# Step 6: Download generated reports
python3 scripts/data_agent_cli.py reports --session-id abc123xyz
```

**Benefits of Reuse**:
- Avoid repeated data understanding phase
- Preserve context history
- Reduce API calls

> See [ANALYSIS_MODE.md](ANALYSIS_MODE.md) for detailed sub-agent implementation specifications
