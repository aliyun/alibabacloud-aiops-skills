# Error Code Reference

**Table of Contents**

- [Container Startup Errors](#container-startup-errors)
- [Service State Errors](#service-state-errors)
- [Network Access Errors](#network-access-errors)
- [Resource Group Errors](#resource-group-errors)
- [Health Check Errors](#health-check-errors)

## Container Startup Errors

### ImagePullBackOff (Image Pull Failure)

**Error message**:
```
Failed to pull image "xxx": rpc error: code = Unknown desc = Error response from daemon: pull access denied
```

**Possible causes**:
1. Incorrect image address
2. Insufficient image registry permissions
3. Image does not exist
4. Network unreachable (public image)

**Solutions**:

| Cause | Solution |
|-------|----------|
| Incorrect image address | Check image address format, use VPC internal address |
| Insufficient permissions | Configure image registry access credentials |
| Image does not exist | Confirm image has been pushed to registry |
| Network unreachable | Use VPC internal image address |

**VPC image address format**:
```
eas-registry-vpc.{region}.cr.aliyuncs.com/pai-eas/{image}:{tag}
```

### CrashLoopBackOff (Container Startup Failure)

**Error message**:
```
Back-off restarting failed container
```

**Possible causes**:
1. Incorrect startup command
2. Dependency service not ready
3. Missing configuration file
4. Port conflict

**Diagnostic commands**:
```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# View container logs
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE --keyword "error" --limit 50 --user-agent AlibabaCloud-Agent-Skills

# View startup events
aliyun eas describe-service-event --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Events[] | select(.Reason == "Started" or .Reason == "Failed")'
```

### OOMKilled (Out of Memory)

**Error message**:
```
Container xxx was OOMKilled
```

**Possible causes**:
1. Memory specification too small
2. Memory leak
3. Model loading consumes too much memory

**Solutions**:

| Scenario | Solution |
|----------|----------|
| Specification too small | Upgrade memory specification |
| Memory leak | Investigate code, fix leak |
| Model too large | Use model quantization, reduce batch size |

**Common memory specifications**:

| Specification | Memory | Use Case |
|--------------|--------|----------|
| ecs.r7.large | 16Gi | Lightweight services |
| ecs.r7.xlarge | 32Gi | Medium services |
| ecs.gn6i-c8g1.2xlarge | 31Gi | GPU inference |
| ecs.gn6e-c12g1.3xlarge | 92Gi | Large model inference |

### OutOfGPU (Insufficient GPU Resources)

**Error message**:
```
Insufficient nvidia.com/gpu
```

**Possible causes**:
1. Incorrect GPU specification selected
2. Insufficient GPU inventory in public resource group
3. GPU node failure in dedicated resource group

**Solutions**:

| Cause | Solution |
|-------|----------|
| Incorrect specification | Check `--tp` parameter in command, ensure it matches GPU count |
| Insufficient inventory | Switch region or specification, or use dedicated resource group |
| Node failure | Check resource group node status |

---

## Service State Errors

### Creating (Creation Timeout)

**Symptom**: Service stuck in Creating state for a long time

**Possible causes**:
1. Waiting for resource allocation
2. Slow image pull
3. Startup command stuck

**Diagnostic flow**:
```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# 1. Check events
aliyun eas describe-service-event --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills

# 2. Check logs
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE --limit 100 --user-agent AlibabaCloud-Agent-Skills

# 3. Check instance status
aliyun eas list-service-instances --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills
```

### Failed (Service Failure)

**Symptom**: Service status is Failed

**Diagnostic flow**:
```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# 1. Get failure reason
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{Status, Message, Reason}'

# 2. View failure events
aliyun eas describe-service-event --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Events[] | select(.Type == "Warning" or .Type == "Normal") | select(.Reason | test("Fail|Error"; "i"))'
```

---

## Network Access Errors

### Service Inaccessible

**Possible causes**:
1. Gateway status anomaly
2. Security group misconfiguration
3. Token configuration error
4. VPC network misconfiguration

**Diagnostic flow**:
```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# 1. Check gateway status
aliyun eas describe-gateway --cluster-id $REGION --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills | \
  jq '{Status: .LoadBalancerList[0].Status}'

# 2. Check service endpoints
aliyun eas describe-service-endpoints --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills

# 3. Test connectivity (execute within VPC)
curl --connect-timeout 10 --max-time 30 -H "Authorization: xxx" http://xxx.vpc.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/my-service
```

### Token Authentication Failure

**Error message**:
```json
{"code": "Unauthorized", "message": "Invalid token"}
```

**Solutions**:
1. Verify Token is correct
2. Check if Token has expired
3. Regenerate Token

```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# Get Token
aliyun eas describe-service-endpoints --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.Token'
```

---

## Resource Group Errors

### Dedicated Resource Group Node Anomaly

**Diagnostic commands**:
```bash
REGION="cn-hangzhou"

# Check resource group status
aliyun eas describe-resource --cluster-id $REGION --resource-id eas-r-xxx --user-agent AlibabaCloud-Agent-Skills | \
  jq '{Name, Status, TotalNodes, HealthyNodes}'

# Check node details
aliyun eas describe-resource --cluster-id $REGION --resource-id eas-r-xxx --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Nodes[] | select(.Status != "Running")'
```

**Node status descriptions**:

| Status | Description |
|--------|-------------|
| Running | Running normally |
| NotReady | Node anomaly |
| Offline | Node offline |

---

## Health Check Errors

### Health Check Failure

**Error message**:
```
Liveness probe failed: HTTP probe failed with statuscode: 500
```

**Possible causes**:
1. Service startup not complete
2. Incorrect health check path
3. Incorrect health check port
4. Internal service error

**Solutions**:

| Cause | Solution |
|-------|----------|
| Startup not complete | Increase `initial_delay_seconds` |
| Incorrect path | Check `http_get.path` configuration |
| Incorrect port | Check `http_get.port` configuration |
| Service error | Check service logs for investigation |

**Health check configuration reference**:
```json
{
  "startup_check": {
    "http_get": { "path": "/health", "port": 8000 },
    "initial_delay_seconds": 30,
    "period_seconds": 10,
    "timeout_seconds": 5,
    "failure_threshold": 3
  }
}
```
