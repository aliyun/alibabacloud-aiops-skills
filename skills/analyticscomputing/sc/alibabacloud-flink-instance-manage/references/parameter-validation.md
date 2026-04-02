# Parameter Validation Rules

Pre-execution validation checklist. If any check fails, do not execute.

## Create Command Validation

### 1. Confirmation flag (MANDATORY)
- ✓ `--confirm` flag MUST be present
- ❌ Missing flag → SafetyCheckRequired error
- Action: Add `--confirm` and retry ONCE

### 2. Resource specification (EXACTLY ONE option)

**Option A**: `--cu_count N`
- Valid: `--cu_count 4`
- Auto-calculates: 4 cores + 16 GB

**Option B**: `--cpu N --memory_gb M`
- Valid: `--cpu 4 --memory_gb 16`
- **Both flags required together**

**Invalid patterns**:
- ❌ `--cpu 4` alone (missing memory_gb)
- ❌ `--memory_gb 16` alone (missing cpu)
- ❌ `--cu_count 4 --cpu 2` (conflicting specs)
- ❌ No resource spec at all

Action: Fix parameter combination and retry ONCE

### 3. Required flags for create

All of these MUST be present:
- `--region_id` (never assume default)
- `--name` (instance name)
- `--instance_type` (exact: "PayAsYouGo" or "Subscription", case-sensitive)
- `--vswitch_id`
- `--vpc_id`

**Invalid patterns**:
- ❌ `--instance_type pay-as-you-go` (wrong case)
- ❌ `--instance_type PAYASYOUGO` (wrong format)
- ✓ `--instance_type PayAsYouGo` (correct)

### 4. Subscription-specific requirements

If `--instance_type Subscription`:
- Optional: `--period` (1, 2, 3, 6, or 12 months)
- Optional: `--auto_renew` (flag)

## Create Namespace Validation

### 1. Confirmation flag (MANDATORY)
- ✓ `--confirm` flag MUST be present
- ❌ Missing → SafetyCheckRequired error

### 2. Required flags
- `--region_id`
- `--instance_id` (must reference existing instance)
- `--name` (namespace name)

### 3. Resource specification (optional)

For creating a NEW namespace:
- Both `--cpu` AND `--memory_gb` are required together
- ❌ Invalid: only `--cpu` or only `--memory_gb`
- ❌ Invalid: omit both for a new namespace

Idempotent exception:
- If namespace already exists with the same `--name`, create operation can return
  idempotent success without requiring new resource values.

## Query Command Validation

Query commands have minimal validation:
- `describe_regions`: no parameters required
- `describe_zones`: requires `--region_id`
- `describe`: requires `--region_id`
- `describe_namespaces`: requires `--region_id` and `--instance_id`
- `list_tags`: requires `--region_id` and `--resource_type`

## Error Code to Validation Mapping

| Error Code | Cause | Fix |
|-----------|-------|-----|
| SafetyCheckRequired | Missing `--confirm` | Add `--confirm` flag |
| MissingParameter | Missing required flag | Add the required flag |
| ValueError | Invalid parameter combination | Check resource spec rules |
| InstanceNameConflict | Instance exists with different config | Use different name or verify existing instance |
| NamespaceNotFound | Parent instance not found | Verify instance_id exists |
| InsufficientResources | Requested namespace resources exceed available capacity | Inform user and request manual instance resource expansion/reallocation, then retry |

## Validation Checklist Template

Before executing `create`:
```
□ --confirm flag present
□ --region_id present
□ --name present
□ --instance_type valid (PayAsYouGo or Subscription)
□ --vswitch_id present
□ --vpc_id present
□ Resource spec: either --cu_count OR (--cpu AND --memory_gb)
□ No conflicting parameters
```

Before executing `create_namespace`:
```
□ --confirm flag present
□ --region_id present
□ --instance_id present
□ --name present
□ For new namespace: both --cpu AND --memory_gb present
□ Resource request does not exceed available instance capacity
```
