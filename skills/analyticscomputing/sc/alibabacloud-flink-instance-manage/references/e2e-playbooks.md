# End-to-end playbooks

Complete execution sequences for common scenarios. Each playbook includes discovery, execution, and verification.

**Core principle**: Never claim success without read-back verification.

## Playbook 1: Create Instance (PayAsYouGo)

### Step 1: Discover
```bash
python scripts/instance_ops.py describe_regions
python scripts/instance_ops.py describe --region_id <REGION>
```

**Decision**: Check if target instance name already exists

### Step 2: Execute
```bash
python scripts/instance_ops.py create \
  --region_id <REGION> \
  --name <NAME> \
  --instance_type PayAsYouGo \
  --vswitch_id <VSWITCH_ID> \
  --vpc_id <VPC_ID> \
  --cu_count <N> \
  --confirm
```

### Step 3: Verify
```bash
python scripts/instance_ops.py describe --region_id <REGION>
```

**Verify**: InstanceId, InstanceName, CPU/memory all match

**CRITICAL**: Check instance status is `RUNNING` (not just `AVAILABLE`)
- If status is `CREATING` or not `RUNNING`, wait 60 seconds and re-check
- Instance must be `RUNNING` before creating namespaces
- See `instance-state-management.md` for detailed state handling

### Step 4: Report
```json
{
  "operation": "create",
  "create_result": "success",
  "instance_id": "f-cn-xxx",
  "verify_result": "Instance found with matching spec",
  "final_status": "completed"
}
```

**Done when**: Create success + read-back verification confirms presence and spec

## 2) Create namespace

### Target lock for lifecycle chain

If this namespace step is part of a `create instance -> create namespace` closed loop:
- use the `InstanceId` returned by that same create operation
- do not switch to another existing RUNNING instance without explicit user approval
- if not ready, wait/poll on the same target instead of pivoting

### Pre-requisite Checks

1. **Verify instance exists and is READY**:
   ```bash
   python scripts/instance_ops.py describe --region_id <region>
   ```
   - Confirm instance status is `RUNNING` (not `CREATING` or `AVAILABLE`)
   - If not `RUNNING`, wait before proceeding (see `instance-state-management.md`)

2. **Check available resources**:
   ```bash
   python scripts/instance_ops.py describe_namespaces --region_id <region> --instance_id <id>
   ```
   - Note total instance CPU/memory
   - Calculate used resources from existing namespaces
   - Ensure sufficient resources available

### Execution Steps

1. Run `describe --region_id <region>` and verify target instance exists AND status is `RUNNING`.
2. Run `describe_namespaces` and check whether target namespace already exists.
3. **If namespace does not exist**:
   - Calculate required resources (must be integer CPU, GB memory)
   - Verify resources are available (total - used >= required)
   - Run `create_namespace --cpu <N> --memory_gb <M> --confirm`
   - If resources insufficient: do not blind retry; explicitly tell user to manually
     expand or reallocate instance resources (this skill does not support scaling)
     and retry later.
4. **If namespace already exists**: treat as idempotent success only when existing
   spec matches expected; otherwise report mismatch and remediation.
5. Run `describe_namespaces` for the same instance.
6. Verify namespace exists; if CPU/memory was requested, verify spec matches.

### If target instance is not ready

- Poll every 30 seconds (same `InstanceId`) until status becomes `RUNNING`
- Maximum wait time: 10 minutes
- If still not `RUNNING`, stop and provide a clear next action
- Do not claim closed-loop completion before namespace is actually created and verified

### Common Errors

- **Resource adjustment in progress**: Instance not fully ready → Wait 2-5 minutes
- **Insufficient resources**: Namespace resources exceed available → Ask user to
  manually expand/reallocate resources, then retry
- **CPU must be integer**: Decimal CPU value → Use integer (1, 2, 4, etc.)

Done when:

- namespace exists in `describe_namespaces`
- expected namespace spec is verified (or explicitly confirmed unchanged)

Not done when:

- `create_namespace` returns `success: false` for all allowed attempts
- namespace step was skipped due to capacity issues
- chain switched to another instance without explicit user approval

## 3) Query-only inspection

When user requests inspection without create:

1. Instance scope:
   - run `describe --region_id <region>`
2. Namespace scope:
   - run `describe_namespaces --region_id <region> --instance_id <id>`
3. Region/zone scope:
   - run `describe_regions`
   - run `describe_zones --region_id <region>`
4. Tag scope:
   - run `list_tags --region_id <region> --resource_type vvpinstance --resource_ids <ids>`

Done when:

- returned data clearly answers user query
- response includes the exact filters used (region, instance_id, resource_ids)

## 4) Batch operation checklist

When request includes multiple targets (IDs/names):

1. Parse all items in input order.
2. For each item: execute create/query -> run read-back verification -> record status.
3. Continue remaining items after single-item failure unless all-or-nothing is required.
4. Return per-item final table (`item`, `result`, `verify`, `status`, `reason`).
