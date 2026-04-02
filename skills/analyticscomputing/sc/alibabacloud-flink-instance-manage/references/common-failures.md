# Common Failure Patterns

Patterns to avoid. Each pattern shows the wrong approach and the correct fix.

## Pattern 1: Missing Confirmation Flag

**Scenario**: Create command without `--confirm`

❌ **Wrong**:
```bash
python scripts/instance_ops.py create \
  --region_id cn-beijing \
  --name my-instance \
  --instance_type PayAsYouGo \
  --vswitch_id vsw-xxx \
  --vpc_id vpc-xxx \
  --cu_count 4
```

**Error**: `SafetyCheckRequired`

✓ **Correct**:
```bash
python scripts/instance_ops.py create \
  --region_id cn-beijing \
  --name my-instance \
  --instance_type PayAsYouGo \
  --vswitch_id vsw-xxx \
  --vpc_id vpc-xxx \
  --cu_count 4 \
  --confirm
```

**Why**: `--confirm` is a safety gate for all create operations.

---

## Pattern 2: Incomplete Resource Specification

**Scenario**: Providing only `--cpu` or only `--memory_gb`

❌ **Wrong**:
```bash
--cpu 4
```
→ Error: MissingParameter (memory_gb required)

❌ **Wrong**:
```bash
--memory_gb 16
```
→ Error: MissingParameter (cpu required)

✓ **Correct Option A**:
```bash
--cpu 4 --memory_gb 16
```

✓ **Correct Option B**:
```bash
--cu_count 4
```
(automatically calculates as 4 cores + 16 GB)

**Why**: Resource specification must be complete. Use either `--cu_count` OR both `--cpu` and `--memory_gb`.

---

## Pattern 3: Invalid instance_type

**Scenario**: Wrong case or format for `--instance_type`

❌ **Wrong**:
```bash
--instance_type pay-as-you-go
--instance_type PAYASYOUGO
--instance_type payasyougo
```

✓ **Correct**:
```bash
--instance_type PayAsYouGo
--instance_type Subscription
```

**Why**: Value must match exactly (case-sensitive).

---

## Pattern 4: Missing Required Parameters

**Scenario**: Omitting required flags for create

❌ **Wrong**:
```bash
python scripts/instance_ops.py create \
  --region_id cn-beijing \
  --name my-instance \
  --confirm
```

→ Error: MissingParameter (instance_type, vswitch_id, vpc_id required)

✓ **Correct**:
```bash
python scripts/instance_ops.py create \
  --region_id cn-beijing \
  --name my-instance \
  --instance_type PayAsYouGo \
  --vswitch_id vsw-xxx \
  --vpc_id vpc-xxx \
  --cu_count 4 \
  --confirm
```

**Why**: All required flags must be present. See `parameter-validation.md` for complete list.

---

## Pattern 5: Blind Retries Without Fixing Root Cause

**Scenario**: Repeating the same failed command

❌ **Wrong**:
```bash
# First attempt fails with SafetyCheckRequired
python scripts/instance_ops.py create ... --region_id cn-beijing

# Retry with same command (still fails)
python scripts/instance_ops.py create ... --region_id cn-beijing
```

✓ **Correct**:
```bash
# First attempt fails
python scripts/instance_ops.py create ... --region_id cn-beijing

# Fix the root cause (add --confirm)
python scripts/instance_ops.py create ... --region_id cn-beijing --confirm
```

**Why**: Maximum 2 attempts total. Second attempt must correct the error.

---

## Pattern 6: Claiming Success Without Verification

**Scenario**: Reporting success after create response only

❌ **Wrong**:
```
Create command returned success: true
→ Reporting: "Instance created successfully"
```

✓ **Correct**:
```bash
# Step 1: Create command
python scripts/instance_ops.py create ... --confirm

# Step 2: Verify with query
python scripts/instance_ops.py describe --region_id cn-beijing

# Step 3: Confirm instance exists with correct spec
→ Reporting: "Instance created and verified: found my-instance with 4 cores, 16 GB"
```

**Why**: Success requires create response + read-back verification.

---

## Pattern 7: Auto-switching Operations on Failure

**Scenario**: Create fails, agent switches to different operation

❌ **Wrong**:
```bash
# Create instance fails
python scripts/instance_ops.py create ... --confirm
# Error: InstanceNameConflict

# Agent tries different operation without user approval
python scripts/instance_ops.py create_namespace ...
```

✓ **Correct**:
```bash
# Create instance fails
python scripts/instance_ops.py create ... --confirm
# Error: InstanceNameConflict

# Report error and ask user
"Instance creation failed: name 'my-instance' already exists with different configuration.
Options:
1. Use a different name
2. Verify existing instance spec
3. Delete existing instance (requires update/delete scope - outside skill)"
```

**Why**: Never switch operations without explicit user approval.

---

## Pattern 8: Creating Duplicate Resources

**Scenario**: Creating resource that already exists

❌ **Wrong**:
```bash
# Create instance without checking if it exists
python scripts/instance_ops.py create \
  --name my-instance \
  ...
```

✓ **Correct**:
```bash
# Step 1: Query existing instances
python scripts/instance_ops.py describe --region_id cn-beijing

# Step 2: Check if my-instance exists
# If exists with same config: skip creation (idempotent success)
# If exists with different config: report conflict
# If not exists: proceed with creation
```

**Why**: Check existing state before create to avoid conflicts and enable idempotent behavior.

---

## Pattern 9: Operating on Not-Ready Instance

**Scenario**: Creating namespace immediately after instance creation

❌ **Wrong**:
```bash
# Create instance
python scripts/instance_ops.py create ... --confirm
# Immediately create namespace (fails)
python scripts/instance_ops.py create_namespace --instance_id f-cn-xxx --name ns --confirm
```

**Error**: "Resource adjustment in progress" or "Instance is not ready"

✓ **Correct**:
```bash
# Create instance
python scripts/instance_ops.py create ... --confirm

# Wait for instance to be RUNNING (not just AVAILABLE)
sleep 60
python scripts/instance_ops.py describe --region_id cn-beijing
# Check status is RUNNING before proceeding

# Then create namespace
python scripts/instance_ops.py create_namespace --instance_id f-cn-xxx --name ns --confirm
```

**Why**: Instances need time to fully initialize. AVAILABLE status is not sufficient; wait for RUNNING.

---

## Pattern 10: Insufficient Resources for Namespace

**Scenario**: Creating namespace with resources that exceed instance capacity

❌ **Wrong**:
```bash
# Instance has 1 CPU, 4 GB total
# Existing namespace uses 1 CPU, 4 GB
python scripts/instance_ops.py create_namespace \
  --instance_id f-cn-xxx \
  --name new-ns \
  --cpu 2 \
  --memory_gb 8 \
  --confirm
```

**Error**: "Insufficient resources" or similar

✓ **Correct**:
```bash
# Step 1: Check instance resources
python scripts/instance_ops.py describe --region_id cn-beijing
# Note: Total = 1 CPU, 4 GB

# Step 2: Check existing namespaces
python scripts/instance_ops.py describe_namespaces --instance_id f-cn-xxx --region_id cn-beijing
# Note: Allocated = 1 CPU, 4 GB

# Step 3: Calculate available
# Available = Total - Allocated = 0 CPU, 0 GB

# Report clearly and request manual capacity action
# (this skill does not support scaling operations)
# "Insufficient resources for new namespace.
#  Please manually expand or reallocate the instance resources, then retry."
```

**Why**: Resources are pre-allocated to namespaces. Check availability before creating.

---

## Pattern 11: Using Decimal CPU Values

**Scenario**: Specifying fractional CPU for namespace

❌ **Wrong**:
```bash
python scripts/instance_ops.py create_namespace \
  --instance_id f-cn-xxx \
  --name ns \
  --cpu 0.5 \
  --memory_gb 2 \
  --confirm
```

**Error**: "CPU must be an integer"

✓ **Correct**:
```bash
python scripts/instance_ops.py create_namespace \
  --instance_id f-cn-xxx \
  --name ns \
  --cpu 1 \
  --memory_gb 2 \
  --confirm
```

**Why**: CPU allocation must be integer values only.

---

## Pattern 12: Parsing Output with Grep

**Scenario**: Using grep to extract instance details from JSON

❌ **Wrong**:
```bash
python scripts/instance_ops.py describe --region_id cn-beijing | grep "InstanceId"
```

This is fragile and may miss context.

✓ **Correct Option A** (Parse JSON):
```bash
python scripts/instance_ops.py describe --region_id cn-beijing | \
  python -c "import json,sys; data=json.load(sys.stdin); print(json.dumps([x for x in data['data']['Instances'] if x['InstanceId']=='f-cn-xxx'], indent=2))"
```

✓ **Correct Option B** (Save and parse):
```bash
python scripts/instance_ops.py describe --region_id cn-beijing > /tmp/instances.json
python -c "import json; data=json.load(open('/tmp/instances.json')); inst=[x for x in data['data']['Instances'] if x['InstanceId']=='f-cn-xxx']; print(f\"Status: {inst[0]['Status']}\") if inst else print('Not found')"
```

**Why**: JSON parsing is reliable. Grep is fragile for structured data.

---

## Pattern 13: Fake Closed Loop by Switching Instance

**Scenario**: Created instance is still `CREATING`, then namespace is created on another pre-existing instance

❌ **Wrong**:
```bash
# create returns new instance: f-cn-new
python scripts/instance_ops.py create ... --confirm

# f-cn-new still CREATING
python scripts/instance_ops.py describe --region_id cn-beijing

# agent switches target without user approval
python scripts/instance_ops.py create_namespace --instance_id f-cn-old --name ns --confirm
```

✓ **Correct**:
```bash
# keep target locked to f-cn-new
python scripts/instance_ops.py describe --region_id cn-beijing
# poll until f-cn-new status is RUNNING (up to timeout window)

# then create namespace on f-cn-new
python scripts/instance_ops.py create_namespace --instance_id f-cn-new --name ns --confirm
```

**Why**: Minimal lifecycle loop requires same-target chain integrity.

---

## Pattern 14: Declaring Completion While Namespace Step Is Pending

**Scenario**: Instance is created, but namespace step has not been executed or verified yet.

❌ **Wrong**:
```
Instance created successfully.
Namespace will be created later when instance becomes RUNNING.
Final: completed
```

✓ **Correct**:
```
operation: create + create_namespace
create_result: success
verify_result: instance still CREATING after wait window; namespace not executed
status: not_ready
next_action: wait until RUNNING, then create namespace on the same instance
```

**Why**: Lifecycle completion requires both steps to be executed and verified on the same target instance.

---

## Pattern 15: Declaring Completion After Namespace Create Failure

**Scenario**: `create_namespace` was attempted but returned `success: false`, yet final report says workflow completed.

❌ **Wrong**:
```
Instance create succeeded.
Namespace create failed due to capacity.
Final: completed
```

✓ **Correct**:
```
operation: create + create_namespace
create_result: instance created
verify_result: namespace create failed (InsufficientResources)
status: failed
next_action: manually expand/reallocate instance resources, then retry create_namespace
```

**Why**: For lifecycle create/create_namespace flow, completion requires BOTH create commands to succeed.

---

## Quick Reference: Error Code → Fix

| Error Code | Root Cause | Fix Action |
|-----------|-----------|-----------|
| SafetyCheckRequired | Missing `--confirm` | Add `--confirm` flag, retry once |
| MissingParameter | Missing required flag | Add missing flag, retry once |
| ValueError | Invalid param combo | Fix resource spec, retry once |
| InstanceNameConflict | Instance exists with different config | Use different name or verify existing |
| NamespaceNotFound | Parent instance not found | Verify instance_id exists |
| AccessDenied | Insufficient permissions | Stop, report required RAM policy |
| Throttling | Rate limit | Wait and retry once (query only) |
| ResourceAdjustmentInProgress | Instance not fully initialized | Wait 2-5 min, check status is RUNNING |
| InsufficientResources | Namespace resources exceed available | Inform user to manually expand/reallocate resources, then retry |
| InvalidCpuValue | CPU is not integer | Use integer value (e.g., 1, 2, 4) |

**Maximum retries**: 2 total (initial + one corrected retry)
