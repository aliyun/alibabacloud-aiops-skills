# Instance State Management

This document provides guidance on handling instance states and waiting for readiness.

## Instance States

### Common States
- `CREATING` - Instance is being created
- `RUNNING` - Instance is operational and ready
- `AVAILABLE` - Instance is available but may not be fully ready
- `RELEASING` - Instance is being deleted
- `EXCEPTION` - Instance has errors

### State Transitions
```
CREATING → RUNNING (normal flow)
CREATING → EXCEPTION (creation failed)
RUNNING → RELEASING (deletion initiated)
```

## Waiting for Instance Readiness

After creating an instance, you MUST wait for it to become fully ready before creating namespaces.

### Step 1: Check Initial State
```bash
python scripts/instance_ops.py describe --region_id <REGION>
```

Look for:
- `ClusterStatus` or `Status` field
- Instance should be `RUNNING` (not just `AVAILABLE`)

### Step 2: Poll for Readiness (if needed)

If instance is in `CREATING` or `AVAILABLE` but not `RUNNING`:

```bash
# Wait loop (check every 30 seconds)
for i in {1..10}; do
  python scripts/instance_ops.py describe --region_id <REGION> > /tmp/instance_status.json
  status=$(python -c "import json; data=json.load(open('/tmp/instance_status.json')); inst=[x for x in data['data']['Instances'] if x['InstanceId']=='<INSTANCE_ID>']; print(inst[0].get('Status', 'UNKNOWN') if inst else 'NOT_FOUND')")
  
  if [ "$status" == "RUNNING" ]; then
    echo "Instance is ready"
    break
  fi
  
  echo "Instance status: $status, waiting..."
  sleep 30
done
```

### Step 3: Verify Readiness for Namespace Operations

Before creating namespaces, verify:
1. Instance status is `RUNNING`
2. No "resource adjustment in progress" errors
3. Instance has available resources (CPU/Memory not fully allocated)

```bash
# Check available resources
python scripts/instance_ops.py describe --region_id <REGION> | \
  python -c "import json,sys; data=json.load(sys.stdin); inst=[x for x in data['data']['Instances'] if x['InstanceId']=='<INSTANCE_ID>']; print(f\"Total: {inst[0]['Cpu']} CPU, {inst[0]['MemoryGB']} GB\" if inst else 'Not found')"

# Check existing namespaces to see resource usage
python scripts/instance_ops.py describe_namespaces --region_id <REGION> --instance_id <INSTANCE_ID>
```

## Common Errors and Solutions

### Error: "Resource adjustment in progress"

**Cause**: Instance is still initializing or undergoing resource changes

**Solution**: 
1. Wait 2-5 minutes for initialization to complete
2. Check instance status until it shows `RUNNING`
3. Retry namespace creation

**Do NOT**: 
- Blindly retry without waiting
- Switch to a different instance without user approval
- Report failure immediately

### Error: "Insufficient resources"

**Cause**: Instance doesn't have enough free CPU/memory for namespace

**Solution**:
1. Query existing namespaces to see resource allocation
2. Check total instance resources vs allocated resources
3. Either:
   - Create namespace with smaller resources
   - Use a different instance with more available resources (with user approval)
   - Create namespace without resource specification (shares instance pool)

### Error: "Instance not found"

**Cause**: Instance ID is incorrect or instance was deleted

**Solution**:
1. Verify instance exists with `describe` command
2. Check correct region_id was used
3. If instance was deleted, report to user

## Resource Calculation for Namespaces

### Minimum Resources
- CPU: 1 (minimum integer value)
- Memory: 1 GB (minimum)

### Resource Allocation Rules
- CPU must be integer (no decimals)
- Memory must be in GB (integer)
- Both CPU and memory must be specified together
- Resources cannot exceed instance total capacity

### Example Calculations

**Instance**: 4 CPU, 16 GB
**Existing namespace**: 1 CPU, 4 GB (already allocated)
**Available for new namespace**: 3 CPU, 12 GB maximum

**Valid namespace creation**:
```bash
# Within available resources
python scripts/instance_ops.py create_namespace \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx \
  --name new-ns \
  --cpu 2 \
  --memory_gb 8 \
  --confirm
```

**Invalid namespace creation** (would fail):
```bash
# Exceeds available resources
--cpu 5 --memory_gb 20  # Too much

# Decimal CPU (invalid)
--cpu 0.5 --memory_gb 2  # CPU must be integer
```

## Timeout Guidelines

### Creation Timeouts
- Instance creation: 5-10 minutes
- Namespace creation: 30-60 seconds
- Status transitions: 2-5 minutes

### Polling Intervals
- Check instance status: Every 30 seconds
- Maximum wait time: 10 minutes
- Polling checks are separate from command retry policy in `output-handling.md`

## Best Practices

1. **Always verify state before proceeding** to next operation
2. **Use JSON parsing** instead of grep for reliability
3. **Check resource availability** before creating namespaces
4. **Wait for RUNNING state** not just AVAILABLE
5. **Report temporary states** to user with expected timeline
