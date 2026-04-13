# Verification Method - MongoDB Instance Management Verification

This document provides verification methods after successful MongoDB instance creation and management operations.

## Creation Success Verification

### 1. Query Instance Status

After instance creation, confirm success by querying instance attributes:

```bash
aliyun dds describe-db-instance-attribute \
  --db-instance-id <your-instance-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 2. Verify Instance Status is Running

After successful instance creation, `DBInstanceStatus` should be `Running`:

```bash
aliyun dds describe-db-instance-attribute \
  --db-instance-id <your-instance-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | grep -E '"DBInstanceStatus"'
```

Expected output:
```
"DBInstanceStatus": "Running",
```

### 3. Verify Replica Set Node Count

Confirm that the primary/secondary node count matches the configuration:

```bash
aliyun dds describe-db-instance-attribute \
  --db-instance-id <your-instance-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | grep -E '"ReplicationFactor"'
```

Expected output (3-node example):
```
"ReplicationFactor": "3",
```

## Instance Status Reference

| Status | Description |
|--------|-------------|
| Creating | Instance is being created |
| Running | Running (normal state) |
| Deleting | Instance is being deleted |
| Rebooting | Instance is restarting |
| DBInstanceClassChanging | Spec modification in progress |
| NetAddressCreating | Network address is being created |
| NetAddressDeleting | Network address is being released |

## Complete Verification Script

```bash
#!/bin/bash
# MongoDB Replica Set Instance Creation Verification Script

INSTANCE_ID=$1

if [ -z "$INSTANCE_ID" ]; then
    echo "Usage: $0 <instance-id>"
    exit 1
fi

echo "=== Verifying MongoDB Instance: $INSTANCE_ID ==="

# Get instance attributes
RESULT=$(aliyun dds describe-db-instance-attribute \
  --db-instance-id "$INSTANCE_ID" \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

# Check if command succeeded
if [ $? -ne 0 ]; then
    echo "ERROR: Unable to retrieve instance information"
    echo "$RESULT"
    exit 1
fi

# Extract key information
STATUS=$(echo "$RESULT" | grep -o '"DBInstanceStatus": "[^"]*"' | cut -d'"' -f4)
REPLICATION=$(echo "$RESULT" | grep -o '"ReplicationFactor": "[^"]*"' | cut -d'"' -f4)
ENGINE_VERSION=$(echo "$RESULT" | grep -o '"EngineVersion": "[^"]*"' | cut -d'"' -f4)
REGION=$(echo "$RESULT" | grep -o '"RegionId": "[^"]*"' | cut -d'"' -f4)
STORAGE=$(echo "$RESULT" | grep -o '"DBInstanceStorage": [0-9]*' | cut -d':' -f2 | tr -d ' ')

echo "Instance Status: $STATUS"
echo "Node Count: $REPLICATION"
echo "Database Version: $ENGINE_VERSION"
echo "Region: $REGION"
echo "Storage: ${STORAGE}GB"

# Validate status
if [ "$STATUS" == "Running" ]; then
    echo ""
    echo "✅ Verification passed: Instance created successfully and running normally"
    exit 0
else
    echo ""
    echo "⚠️  Instance status is: $STATUS (waiting for Running)"
    exit 1
fi
```

## Wait for Instance Ready

After instance creation, it may take several minutes to reach Running status. Use the following command to poll:

```bash
# Poll and wait for instance ready (max 10 minutes)
INSTANCE_ID="<your-instance-id>"
MAX_WAIT=600  # seconds
INTERVAL=30   # seconds
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$(aliyun dds describe-db-instance-attribute \
      --db-instance-id "$INSTANCE_ID" \
      --user-agent AlibabaCloud-Agent-Skills \
      2>/dev/null | grep -o '"DBInstanceStatus": "[^"]*"' | cut -d'"' -f4)
    
    echo "Current status: $STATUS (elapsed: ${ELAPSED}s)"
    
    if [ "$STATUS" == "Running" ]; then
        echo "✅ Instance is ready"
        break
    fi
    
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "❌ Timeout: Instance did not become ready within ${MAX_WAIT} seconds"
    exit 1
fi
```

## Network Connection Verification

After successful instance creation, verify network connectivity:

### 1. Get Connection Address

```bash
aliyun dds describe-db-instance-attribute \
  --db-instance-id <your-instance-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | grep -A5 '"ReplicaSetList"'
```

### 2. Test Connection Using mongosh (must be executed on an ECS in the same VPC)

```bash
# Connect using Primary node
mongosh "mongodb://root:<password>@<connection-string>:3717/admin?replicaSet=mgset-xxxxx"
```

## Common Troubleshooting

### Instance Stuck in Creating Status for a Long Time

Possible causes:
1. Insufficient resources in the region
2. Quota limitations

How to check:
```bash
# Check available resources
aliyun dds describe-available-resource \
  --region-id cn-hangzhou \
  --zone-id cn-hangzhou-g \
  --db-type replicate \
  --user-agent AlibabaCloud-Agent-Skills
```

### Unable to Connect to Instance

Checklist:
1. ✅ Is the instance status Running?
2. ✅ Does the IP whitelist include the client IP?
3. ✅ Are the ECS and MongoDB in the same VPC?
4. ✅ Do security group rules allow port 3717?

### Check IP Whitelist

```bash
aliyun dds describe-security-ips \
  --db-instance-id <your-instance-id> \
  --user-agent AlibabaCloud-Agent-Skills
```
