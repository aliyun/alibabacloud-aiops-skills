# EIP Batch Associate Cloud Resources - Success Verification Method

This document details how to verify the successful execution of the EIP batch association scenario.

## Scenario Goal Verification

**Expected Outcome**: 3 independent EIPs successfully bindngd to ECS instance, ALB instance, and NAT Gateway respectively.

## Verification Steps

### 1. Verify EIP bindng to ECS Instance

```bash
# Query ECS EIP status
aliyun vpc describe-eip-addresses \
  --region cn-hangzhou \
  --allocation-id <EcsEipAllocationId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- `Status` = `InUse`
- `InstanceId` = `<EcsInstanceId>`
- `InstanceType` = `EcsInstance`

**Example Success Output**:
```json
{
  "EipAddresses": {
    "EipAddress": [{
      "AllocationId": "eip-bp1xxxxx",
      "Status": "InUse",
      "InstanceId": "i-bp1xxxxx",
      "InstanceType": "EcsInstance",
      "IpAddress": "47.xxx.xxx.xxx"
    }]
  }
}
```

### 2. Verify EIP bindng to ALB Instance

```bash
# Query ALB attributes to verify EIP bindng
aliyun alb get-load-balancer-attribute \
  --load-balancer-id <LoadBalancerId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- `AddressType` = `Internet`
- `AddressAllocatedMode` = `Fixed`
- Zone mappings contain `AllocationId`

### 3. Verify EIP bindng to NAT Gateway

```bash
# Query NAT EIP status
aliyun vpc describe-eip-addresses \
  --region cn-hangzhou \
  --allocation-id <NatEipAllocationId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- `Status` = `InUse`
- `InstanceId` = `<NatGatewayId>`
- `InstanceType` = `Nat`

### 4. Batch Verify All EIP Status

```bash
# Query all EIPs (filter by status)
aliyun vpc describe-eip-addresses \
  --region cn-hangzhou \
  --status InUse \
  --user-agent AlibabaCloud-Agent-Skills
```

### 5. Verify ECS Instance Public Network Connectivity

```bash
# Get EIP address bindngd to ECS
EIP_ADDRESS=$(aliyun vpc describe-eip-addresses \
  --region cn-hangzhou \
  --allocation-id <EcsEipAllocationId> \
  --user-agent AlibabaCloud-Agent-Skills \
  | grep -o '"IpAddress":"[^"]*"' | cut -d'"' -f4)

# Test ping connectivity (requires security group to allow ICMP)
ping -c 3 $EIP_ADDRESS
```

### 6. Verify NAT Gateway Associated EIP

```bash
# Query NAT Gateway details to confirm EIP association
aliyun vpc describe-nat-gateways \
  --region cn-hangzhou \
  --nat-gateway-id <NatGatewayId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators**:
- `IpLists` contains the bindngd EIP address

## Resource Status Reference Table

### EIP Status

| Status | Description |
|--------|-------------|
| Associating | bindng in progress |
| Unassociating | Unbinding in progress |
| InUse | Allocated (bindngd) |
| Available | Available (not bindngd) |

### ECS Status

| Status | Description |
|--------|-------------|
| Pending | Creating |
| Running | Running |
| Starting | Starting |
| Stopping | Stopping |
| Stopped | Stopped |

### ALB Status

| Status | Description |
|--------|-------------|
| Provisioning | Creating |
| Active | Running normally |
| Configuring | Configuring |

### NAT Gateway Status

| Status | Description |
|--------|-------------|
| Creating | Creating |
| Available | Available |
| Modifying | Modifying |
| Deleting | Deleting |

## Common Error Troubleshooting

### EIP bindng Failed

**Error**: `InvalidInstanceId.NotFound`
- **Cause**: Target resource ID does not exist
- **Solution**: Confirm resource ID is correct and resource status is normal

**Error**: `InvalidStatus.NotSatisfied`
- **Cause**: EIP or target resource status does not meet bindng conditions
- **Solution**: Wait for resource status to become available and retry

**Error**: `IncorrectInstanceStatus`
- **Cause**: ECS instance status is not Running
- **Solution**: Start ECS instance and retry

### EIP Already Occupied

**Error**: `InvalidAllocationId.AlreadyAssociated`
- **Cause**: EIP is already bindngd to another resource
- **Solution**: Unbind existing bindng first, or use a new EIP

## Verification Script Example

```bash
#!/bin/bash
# EIP Batch bindng Verification Script

REGION="cn-hangzhou"
ECS_EIP_ID="eip-xxxxx"
ALB_LB_ID="alb-yyyyy"
NAT_EIP_ID="eip-zzzzz"

echo "=== Verify ECS EIP bindng ==="
aliyun vpc describe-eip-addresses --region $REGION --allocation-id $ECS_EIP_ID --user-agent AlibabaCloud-Agent-Skills | grep -E '"Status"|"InstanceId"|"InstanceType"'

echo "=== Verify ALB Address Type ==="
aliyun alb get-load-balancer-attribute --load-balancer-id $ALB_LB_ID --user-agent AlibabaCloud-Agent-Skills | grep -E '"AddressType"'

echo "=== Verify NAT EIP bindng ==="
aliyun vpc describe-eip-addresses --region $REGION --allocation-id $NAT_EIP_ID --user-agent AlibabaCloud-Agent-Skills | grep -E '"Status"|"InstanceId"|"InstanceType"'

echo "=== Verification Complete ==="
```
