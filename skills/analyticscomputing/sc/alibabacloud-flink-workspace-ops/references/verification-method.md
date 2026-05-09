# Verification Methods

Use this guide after a mutating command to verify actual resource state.

## ⚠️ Global Verification Rules

- **MANDATORY**: Verify after EVERY mutating operation
- Prefer `-o json` for deterministic parsing
- Verify immediately after each mutation (don't delay)
- For async operations, verify only after polling returns terminal result
- **NEVER claim success without read-back verification**

## Verification Protocol (MANDATORY)

### Step 1: Identify Verification Command

Match operation to verification command:

| Operation | Verification Command | Expected Result |
|-----------|---------------------|-----------------|
| create_deployment | get_deployment | status: CREATED |
| start_job | get_job | state: RUNNING |
| stop_job | get_job | state: STOPPED/CANCELED |
| create_session_cluster | get_session_cluster | state: CREATED/RUNNING |
| delete_deployment | get_deployment | ResourceNotFound error |
| create_savepoint | get_savepoint | state: COMPLETED |

### Step 2: Execute Verification Command

```bash
python scripts/flink_ververica_ops.py get_<resource> -w <workspace> -n <namespace> -r <region> --<resource>_id <id> -o json
```

### Step 3: Parse and Confirm Response

**Successful creation/update:**
```json
{
  "success": true,
  "data": {
    "resource_id": "xxx",
    "name": "expected-name",
    "status": "EXPECTED_STATE"
  }
}
```

**Successful deletion:**
```json
{
  "success": false,
  "error": {
    "code": "ResourceNotFound"
  }
}
```

### Step 4: Report Verification Results

```
✓ Verification successful

**Operation:** create_deployment
**Resource ID:** d-123456
**Current State:**
- Name: etl-job
- Status: CREATED
- Engine Version: vvr-8.0.1-flink-1.17
- Namespace: default
- Workspace: w-xxx
```

## Verification Examples by Workflow

### create_folder / update_folder
```bash
# After creation
python scripts/flink_ververica_ops.py get_folder -w <workspace> -n <namespace> -r <region> --folder_id <folder_id> -o json

# Verify:
# - success: true
# - data.name matches expected name
# - data.folder_id exists
```

### delete_folder
```bash
# After deletion, verify it's gone
python scripts/flink_ververica_ops.py get_folder -w <workspace> -n <namespace> -r <region> --folder_id <folder_id> -o json

# Verify:
# - success: false
# - error.code: "ResourceNotFound"
```

### create_draft / update_draft
```bash
# After creation
python scripts/flink_ververica_ops.py get_draft -w <workspace> -n <namespace> -r <region> --draft_id <draft_id> -o json

# Verify:
# - success: true
# - data.name matches expected name
# - data.sql_content matches expected SQL
```

### validate_draft (async)
```bash
# Step 1: Start validation
python scripts/flink_ververica_ops.py validate_draft -w <workspace> -n <namespace> -r <region> --draft_id <draft_id> -o json

# Returns: {"success": true, "data": {"ticket_id": "xxx-xxx-xxx"}}

# Step 2: Poll for result (repeat until terminal state)
python scripts/flink_ververica_ops.py get_validate_result -w <workspace> -n <namespace> -r <region> --ticket_id <ticket_id> -o json

# Verify:
# - success: true
# - data.status: "SUCCEEDED" or "FAILED"
# - If FAILED: data.errors contains error details
```

### deploy_draft (async)
```bash
# Step 1: Start deployment
python scripts/flink_ververica_ops.py deploy_draft -w <workspace> -n <namespace> -r <region> --draft_id <draft_id> --deployment_name <name> --confirm -o json

# Returns: {"success": true, "data": {"ticket_id": "xxx-xxx-xxx"}}

# Step 2: Poll for result
python scripts/flink_ververica_ops.py get_deploy_result -w <workspace> -n <namespace> -r <region> --ticket_id <ticket_id> -o json

# Verify:
# - success: true
# - data.status: "SUCCEEDED"
# - data.deployment_id exists
```

## W2 Job Operations

### create_deployment / update_deployment
```bash
# After operation
python scripts/flink_ververica_ops.py get_deployment -w <workspace> -n <namespace> -r <region> --deployment_id <deployment_id> -o json

# Verify:
# - success: true
# - data.name matches expected
# - data.status in ["CREATED", "RUNNING", "STOPPED"]
# - data.engine_version matches expected
```

### start_job
```bash
# After start
python scripts/flink_ververica_ops.py get_job -w <workspace> -n <namespace> -r <region> --job_id <job_id> -o json

# Verify:
# - success: true
# - data.state: "RUNNING"
# - data.start_time exists
```

### stop_job
```bash
# After stop
python scripts/flink_ververica_ops.py get_job -w <workspace> -n <namespace> -r <region> --job_id <job_id> -o json

# Verify:
# - success: true
# - data.state: "STOPPED" or "CANCELED"
# - data.stop_time exists
```

### create_savepoint
```bash
# After creation
python scripts/flink_ververica_ops.py get_savepoint -w <workspace> -n <namespace> -r <region> --savepoint_id <savepoint_id> -o json

# Verify:
# - success: true
# - data.state: "COMPLETED"
# - data.location contains savepoint path
```

### delete_deployment
```bash
# After deletion
python scripts/flink_ververica_ops.py get_deployment -w <workspace> -n <namespace> -r <region> --deployment_id <deployment_id> -o json

# Verify:
# - success: false
# - error.code: "ResourceNotFound"
```

## W3 Session Clusters

### create_session_cluster / update_session_cluster
```bash
# After operation
python scripts/flink_ververica_ops.py get_session_cluster -w <workspace> -n <namespace> -r <region> --cluster_id <cluster_id> -o json

# Verify:
# - success: true
# - data.name matches expected
# - data.state in ["CREATED", "STARTING", "RUNNING", "STOPPING", "STOPPED"]
```

### start_session_cluster
```bash
# After start
python scripts/flink_ververica_ops.py get_session_cluster -w <workspace> -n <namespace> -r <region> --cluster_id <cluster_id> -o json

# Verify:
# - success: true
# - data.state: "RUNNING"
```

### stop_session_cluster
```bash
# After stop
python scripts/flink_ververica_ops.py get_session_cluster -w <workspace> -n <namespace> -r <region> --cluster_id <cluster_id> -o json

# Verify:
# - success: true
# - data.state: "STOPPED"
```

### delete_session_cluster
```bash
# After deletion, verify removal
python scripts/flink_ververica_ops.py list_session_clusters -w <workspace> -n <namespace> -r <region> -o json

# Verify:
# - success: true
# - data.session_clusters does NOT contain the deleted cluster
```

## W4 Dev Resources

### execute_sql
```bash
# For DDL (CREATE TABLE/DATABASE), verify via metadata query
# For DML (INSERT), verify via SELECT query

# Example: after CREATE TABLE
python scripts/flink_ververica_ops.py get_tables -w <workspace> -n <namespace> -r <region> --catalog <catalog> --database <database> -o json

# Verify:
# - success: true
# - data.tables contains the newly created table
```

### get_catalogs / get_databases / get_tables
```bash
# These are read operations, verify by:
# - success: true
# - data contains expected catalogs/databases/tables
```

## W5 Workspace Administration

### create_member / update_member
```bash
# After operation
python scripts/flink_ververica_ops.py get_member -w <workspace> -n <namespace> -r <region> --member_id <member_id> -o json

# Verify:
# - success: true
# - data.user_id matches expected
# - data.role matches expected
```

### delete_member
```bash
# After deletion
python scripts/flink_ververica_ops.py list_members -w <workspace> -n <namespace> -r <region> -o json

# Verify:
# - success: true
# - data.members does NOT contain the deleted member
```

### create_variable / update_variable
```bash
# After operation
python scripts/flink_ververica_ops.py list_variables -w <workspace> -n <namespace> -r <region> -o json

# Verify:
# - success: true
# - data.variables contains the created/updated variable
# - Variable value matches expected
```

### create_deploy_target / update_deploy_target
```bash
# After operation
python scripts/flink_ververica_ops.py list_deploy_targets -w <workspace> -n <namespace> -r <region> -o json

# Verify:
# - success: true
# - data.deploy_targets contains the created/updated target
```

## Verification Response Template

When reporting verification to user:

```
✓ Verification successful

**Operation:** create_deployment
**Resource ID:** d-123456
**Current State:**
- Name: etl-job
- Status: CREATED
- Engine Version: vvr-8.0.1-flink-1.17
- Namespace: default
- Workspace: w-xxx

**Next Actions:**
- To start the job: start_job --deployment_id d-123456
- To update configuration: update_deployment --deployment_id d-123456 --body_json '{...}'
```

## Common Verification Failures

### Failure 1: Resource not found
```
❌ Verification failed: Resource not found
Expected: Deployment d-123456 should exist
Actual: get_deployment returned ResourceNotFound

Possible causes:
- Creation failed silently
- Wrong deployment_id
- Wrong workspace/namespace/region
```

### Failure 2: Wrong state
```
❌ Verification failed: Unexpected state
Expected: Job j-xxx should be RUNNING
Actual: Job state is FAILED

Error from job:
- Failure Reason: Checkpoint timeout
- Error Message: Checkpoint could not be completed within timeout
```

### Failure 3: Partial update
```
❌ Verification failed: Update incomplete
Expected: deployment_target_name = "target-prod"
Actual: deployment_target_name = "target-dev" (unchanged)

Possible causes:
- Update operation failed
- Body JSON not properly formatted
```

## Best Practices

1. **Always verify** - never assume success from write response alone
2. **Verify immediately** - don't delay between operation and verification
3. **Check all fields** - not just success flag, but actual resource state
4. **Report clearly** - show what was expected vs what was found
5. **Investigate failures** - don't just report failure, investigate root cause
