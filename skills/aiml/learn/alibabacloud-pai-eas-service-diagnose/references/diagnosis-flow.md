# Diagnosis Flow Guide

**Table of Contents**

- [Quick Diagnosis Entry](#quick-diagnosis-entry)
- [Scenario 1: Service Startup Failure](#scenario-1-service-startup-failure)
- [Scenario 2: Slow Service Response](#scenario-2-slow-service-response)
- [Scenario 3: Abnormal Instance Restarts](#scenario-3-abnormal-instance-restarts)
- [Scenario 4: Service Inaccessible](#scenario-4-service-inaccessible)
- [Scenario 5: GPU Related Issues](#scenario-5-gpu-related-issues)
- [Diagnosis Report Generation](#diagnosis-report-generation)

## Quick Diagnosis Entry

When a user reports an issue, first confirm the service name and region, then follow this workflow:

```
1. Check service status → Confirm current state
2. Check event list → Understand recent changes
3. Check error logs → Locate specific errors
4. Check instance status → Verify instance health
5. Run diagnosis → Get diagnosis report
```

---

## Scenario 1: Service Startup Failure

### Diagnosis Flow

```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# Step 1: Check service status
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{Status, Message, RunningInstance, TotalInstance}'

# Step 2: View recent events
aliyun eas describe-service-event --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Events[-5:] | .[] | {Time, Type, Reason, Message}'

# Step 3: View error logs
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE \
  --keyword "error" --limit 30 --user-agent AlibabaCloud-Agent-Skills

# Step 4: Check instance status
aliyun eas list-service-instances --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Instances[] | {InstanceId, Status, IpAddress}'

# Step 5: Run diagnosis
aliyun eas describe-service-diagnosis --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills
```

### Common Causes and Solutions

| Error Symptom | Possible Cause | Solution |
|--------------|---------------|----------|
| ImagePullBackOff | Image pull failure | Check image address and permissions |
| CrashLoopBackOff | Container startup failure | Check startup command and logs |
| OOMKilled | Out of memory | Increase memory specification |
| OutOfGPU | Insufficient GPU resources | Check tp parameter or change specification |
| Pending | Waiting for resources | Check resource group inventory |

---

## Scenario 2: Slow Service Response

### Diagnosis Flow

```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# Step 1: Check instance running status
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{RunningInstance, TotalInstance, Cpu, Memory}'

# Step 2: Check instance resource usage
aliyun eas list-service-instances --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Instances[] | {InstanceId, Status, CpuUtilization, MemoryUtilization}'

# Step 3: View slow query logs
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE \
  --keyword "slow" --limit 20 --user-agent AlibabaCloud-Agent-Skills

# Step 4: Check for error logs
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE \
  --keyword "error" --limit 20 --user-agent AlibabaCloud-Agent-Skills
```

### Performance Issue Analysis

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| High CPU usage | Compute-intensive tasks | Increase CPU cores or scale out |
| High memory usage | Model loading, data caching | Increase memory specification |
| Low GPU utilization | Inference batch too small | Increase batch size |
| Request queuing | Insufficient instances | Enable auto-scaling |

### Auto-Scaling Configuration Check

```bash
# Check if auto-scaling is enabled
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.AutoScale'

# Check current instance count
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{RunningInstance, DesiredInstance, MinInstance, MaxInstance}'
```

---

## Scenario 3: Abnormal Instance Restarts

### Diagnosis Flow

```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# Step 1: Check restart events
aliyun eas describe-service-event --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Events[] | select(.Reason == "Restarted") | {Time, Message}'

# Step 2: Check container restart count (requires --instance-name, get it from list-service-instances first)
INSTANCE_NAME=$(aliyun eas list-service-instances --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | jq -r '.Instances[0].InstanceName')
aliyun eas list-service-containers --cluster-id $REGION --service-name $SERVICE --instance-name "$INSTANCE_NAME" --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Containers[] | {ContainerId, RestartCount, Status}'

# Step 3: View pre-restart logs
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE \
  --keyword "killed" --limit 30 --user-agent AlibabaCloud-Agent-Skills

# Step 4: Check health check configuration
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{LivenessCheck, ReadinessCheck}'
```

### Restart Cause Analysis

| Restart Cause | Symptom | Solution |
|--------------|---------|----------|
| OOMKilled | Memory usage exceeds limit | Increase memory specification |
| Liveness failure | Health check keeps failing | Adjust health check parameters |
| Application crash | Program exits abnormally | Investigate application logs |
| Resource pressure | Insufficient node resources | Migrate to another node |

---

## Scenario 4: Service Inaccessible

### Diagnosis Flow

```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# Step 1: Check service status
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{Status, RunningInstance}'

# Step 2: Get service endpoints
aliyun eas describe-service-endpoints --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills

# Step 3: Check gateway status (if using dedicated gateway)
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.ExtraData.GatewayName' | xargs -I {} \
  aliyun eas describe-gateway --cluster-id $REGION --gateway-name {} --user-agent AlibabaCloud-Agent-Skills | \
  jq '{Name, Status: .LoadBalancerList[0].Status}'

# Step 4: Check security group configuration (VPC direct connect scenario)
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.ExtraData.SecurityGroupId'
```

### Network Issue Troubleshooting

| Access Method | Checkpoints |
|--------------|-------------|
| Public gateway | Gateway status, Token, security group |
| VPC direct connect | Security group, VPC configuration, service endpoints |
| Dedicated gateway | Gateway status, NLB status, security group |

### Connectivity Test

```bash
# Get endpoint and Token
ENDPOINT=$(aliyun eas describe-service-endpoints --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | jq -r '.InternetEndpoint')
TOKEN=$(aliyun eas describe-service-endpoints --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | jq -r '.Token')

# Test connectivity
curl --connect-timeout 10 --max-time 30 -H "Authorization: $TOKEN" "$ENDPOINT/health"
```

---

## Scenario 5: GPU Related Issues

### Diagnosis Flow

```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# Step 1: Check GPU specification
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{Cpu, Memory, GPU, GPUType}'

# Step 2: Check instance GPU status
aliyun eas list-service-instances --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Instances[] | {InstanceId, Status, GPUUtilization, GPUMemoryUtilization}'

# Step 3: View GPU-related errors
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE \
  --keyword "cuda" --limit 30 --user-agent AlibabaCloud-Agent-Skills
```

### GPU Issue Analysis

| Issue | Symptom | Solution |
|-------|---------|----------|
| Insufficient GPU memory | CUDA out of memory | Reduce batch size or upgrade GPU |
| Low GPU utilization | Poor inference efficiency | Increase batch size or use multi-stream |
| GPU driver error | Driver error | Check driver version compatibility |
| Multi-GPU communication failure | NCCL error | Check network configuration, tp parameter |

### Tensor Parallel Check

```bash
# Check tp parameter in command
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.Image.Command' | grep -oP '(?<=--tp\s)\d+'

# Verify GPU count matches
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{GPU, Command}'
```

---

## Diagnosis Report Generation

### One-Click Diagnosis Script

```bash
#!/bin/bash
SERVICE="my-service"
REGION="cn-hangzhou"

echo "=== PAI-EAS Service Diagnosis Report ==="
echo "Service: $SERVICE"
echo "Region: $REGION"
echo ""

echo "## Service Status"
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{Status, RunningInstance, TotalInstance, Message}'
echo ""

echo "## Recent Events (Last 5)"
aliyun eas describe-service-event --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Events[-5:] | .[] | {Time, Type, Reason, Message}'
echo ""

echo "## Instance Status"
aliyun eas list-service-instances --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Instances[] | {InstanceId, Status}'
echo ""

echo "## Error Logs (Last 10)"
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE \
  --keyword "error" --limit 10 --user-agent AlibabaCloud-Agent-Skills | jq '.'
echo ""

echo "## Diagnosis Suggestions"
aliyun eas describe-service-diagnosis --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.DiagnosisItems[] | {Name, Status, Suggestion}'
```
