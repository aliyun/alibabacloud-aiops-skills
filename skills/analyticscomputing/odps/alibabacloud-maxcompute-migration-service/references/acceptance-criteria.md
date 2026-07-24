# Acceptance Criteria: MaxCompute Migration Service (MMS)

**Scenario**: MaxCompute Migration Service (MMS) - Migrate various data sources to MaxCompute
**Purpose**: Skill testing acceptance criteria

---

# Correct Usage Patterns

## 1. CLI Commands

### ✅ CORRECT

```bash
# List projects
aliyun maxcompute list-projects --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}

# Get project details
aliyun maxcompute get-project --project my_project --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}

# List tables
aliyun maxcompute list-tables --project my_project --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### ❌ INCORRECT

```bash
# Missing --user-agent
aliyun maxcompute list-projects --region cn-hangzhou

# Using the wrong API format (not plugin mode)
aliyun maxcompute ListProjects --RegionId cn-hangzhou

# Missing required parameters
aliyun maxcompute get-project --region cn-hangzhou
```

## 2. Console Operations

### ✅ CORRECT

1. Log in to the MaxCompute console
2. Navigate to **Data Transfer > Migration Service**
3. Create data sources and migration jobs step by step

### ❌ INCORRECT

1. Creating an MMS data source directly via the CLI (currently not supported)
2. Skipping the preparation work and creating a migration job directly

## 3. Parameter Handling

### ✅ CORRECT

- Confirm all user parameters before performing operations
- Use the specific values provided by the user; do not assume default values
- List a parameter confirmation table for the user to confirm

### ❌ INCORRECT

```markdown
# Wrong: assuming default values
aliyun maxcompute list-projects --region cn-hangzhou  # Assumes the user wants to query the Hangzhou region

# Wrong: executing directly with placeholders
aliyun maxcompute get-project --project <project-name>
```

## 4. Credential Handling

### ✅ CORRECT

```bash
# Only check credential status
aliyun configure list
```

The output shows a valid profile (AK, STS, or OAuth identity).

### ❌ INCORRECT

```bash
# Read or print AK/SK values
echo $ALIBABA_CLOUD_ACCESS_KEY_ID

# Have the user enter credentials on the command line
aliyun configure set --access-key-id <user-input>
```

## 5. Error Handling

### ✅ CORRECT

1. Capture the error message
2. Analyze the cause of the error
3. Provide a solution
4. Guide the user to use the `ram-permission-diagnose` skill to handle permission issues

### ❌ INCORRECT

- Ignoring errors and continuing execution
- Not providing resolution suggestions
- Repeatedly executing the same failed operation

---

# Feature Verification Checklist

## MMS Core Features

- [ ] Identification of supported data source types (Hive, BigQuery, Databricks, MaxCompute)
- [ ] Explanation of migration job types (whole database, multiple tables, multiple partitions)
- [ ] Complete preparation work steps
- [ ] Clear data source creation flow
- [ ] Clear migration job creation flow
- [ ] Well-defined monitoring and verification methods

## CLI Commands

- [ ] All `aliyun` commands include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}`
- [ ] Use plugin mode format (e.g., `list-projects` instead of `ListProjects`)
- [ ] Required parameters are complete

## Documentation

- [ ] RAM Policy documentation is complete
- [ ] Related Commands documentation is complete
- [ ] Verification Method documentation is complete
- [ ] CLI Installation Guide copied to the references directory

## Security

- [ ] Do not expose AK/SK values
- [ ] Use `aliyun configure list` to verify credentials
- [ ] RAM permission list is complete
