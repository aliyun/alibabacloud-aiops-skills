# Diagnostic API Quick Reference

**Table of Contents**

- [Service Status API](#service-status-api)
- [Log API](#log-api)
- [Event API](#event-api)
- [Instance API](#instance-api)
- [Diagnosis API](#diagnosis-api)
- [Resource Group API](#resource-group-api)
- [Gateway API](#gateway-api)
- [Quick Diagnostic Command Summary](#quick-diagnostic-command-summary)

## Service Status API

### describe-service (Service Details)

```bash
aliyun eas describe-service --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills
```

**Key fields**:

| Field | Description | jq Path |
|-------|-------------|---------|
| Service name | Unique service identifier | `.ServiceName` |
| Status | Current status | `.Status` |
| Running instances | Normally running instances | `.RunningInstance` |
| Total instances | Total instance count | `.TotalInstance` |
| CPU | CPU cores | `.Cpu` |
| Memory | Memory size | `.Memory` |
| GPU | GPU count | `.GPU` |
| Image | Container image | `.Image` |
| Error message | Failure reason | `.Message` |

**Status descriptions**:

| Status | Description |
|--------|-------------|
| Creating | Being created |
| Starting | Starting up |
| Running | Running |
| Updating | Being updated |
| Stopping | Stopping |
| Stopped | Stopped |
| Failed | Failed |

---

### list-services (Service List)

```bash
aliyun eas list-services --cluster-id $CLUSTER_ID --user-agent AlibabaCloud-Agent-Skills
```

**Common filters**:

```bash
# Filter failed services
aliyun eas list-services --cluster-id $CLUSTER_ID --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Services[] | select(.Status == "Failed")'

# Filter services by resource group
aliyun eas list-services --cluster-id $CLUSTER_ID --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Services[] | select(.ResourceId == "eas-r-xxx")'
```

---

### describe-service-endpoints (Service Endpoints)

```bash
aliyun eas describe-service-endpoints --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills
```

**Response fields**:

| Field | Description |
|-------|-------------|
| `.InternetEndpoint` | Public endpoint |
| `.IntranetEndpoint` | Internal endpoint |
| `.Token` | Access Token |

---

## Log API

### describe-service-log (Service Logs)

```bash
# Basic query
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE --limit 100 --user-agent AlibabaCloud-Agent-Skills

# Keyword filtering
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --keyword "error" --limit 50 --user-agent AlibabaCloud-Agent-Skills

# Time range
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --start-time "2026-03-19T00:00:00Z" --end-time "2026-03-19T23:59:59Z" --user-agent AlibabaCloud-Agent-Skills

# Specific instance
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --instance-id i-xxx --limit 50 --user-agent AlibabaCloud-Agent-Skills
```

**Parameter descriptions**:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--limit` | Number of entries to return | 100 |
| `--keyword` | Single keyword filter (does not support pipe-separated multiple keywords; run multiple queries for different keywords) | - |
| `--start-time` | Start time | - |
| `--end-time` | End time | - |
| `--instance-id` | Specific instance | - |

---

## Event API

### describe-service-event (Service Events)

```bash
aliyun eas describe-service-event --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills
```

**Key fields**:

| Field | Description |
|-------|-------------|
| `.Time` | Event time |
| `.Type` | Event type |
| `.Reason` | Event reason |
| `.Message` | Event details |

**Event types**:

| Type | Description |
|------|-------------|
| Normal | Normal event |
| Warning | Warning event |

**Common Reasons**:

| Reason | Description |
|--------|-------------|
| Started | Started successfully |
| Failed | Failed |
| Scaled | Scaled up/down |
| Restarted | Restarted |
| Updated | Updated |
| Unhealthy | Unhealthy |

---

## Instance API

### list-service-instances (Instance List)

```bash
aliyun eas list-service-instances --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills
```

**Response fields**:

| Field | Description |
|-------|-------------|
| `.InstanceId` | Instance ID |
| `.Status` | Instance status |
| `.IpAddress` | Instance IP |
| `.CreateTime` | Creation time |
| `.CpuUtilization` | CPU utilization |
| `.MemoryUtilization` | Memory utilization |

**Instance statuses**:

| Status | Description |
|--------|-------------|
| Pending | Pending |
| Creating | Being created |
| Running | Running |
| Failed | Failed |
| Stopping | Stopping |
| Stopped | Stopped |

---

### list-service-containers (Container List)

> **Note**: `--instance-name` is a required parameter. Get it from `list-service-instances` first.

```bash
# Step 1: Get instance name
INSTANCE_NAME=$(aliyun eas list-service-instances --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | jq -r '.Instances[0].InstanceName')

# Step 2: List containers
aliyun eas list-service-containers --cluster-id $CLUSTER_ID --service-name $SERVICE --instance-name "$INSTANCE_NAME" --user-agent AlibabaCloud-Agent-Skills
```

**Key fields**:

| Field | Description |
|-------|-------------|
| `.ContainerId` | Container ID |
| `.InstanceId` | Parent instance |
| `.Status` | Container status |
| `.RestartCount` | Restart count |

---

## Diagnosis API

### describe-service-diagnosis (Service Diagnosis)

```bash
aliyun eas describe-service-diagnosis --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills
```

**Diagnosis items**:

| Diagnosis Item | Description |
|---------------|-------------|
| Resource usage | CPU/memory utilization |
| Network status | Network connectivity |
| Health status | Health check status |
| Storage status | Storage mount status |

---

### describe-service-instance-diagnosis (Instance Diagnosis)

```bash
aliyun eas describe-service-instance-diagnosis --cluster-id $CLUSTER_ID \
  --service-name $SERVICE --instance-id i-xxx --user-agent AlibabaCloud-Agent-Skills
```

---

## Resource Group API

### describe-resource (Resource Group Details)

```bash
aliyun eas describe-resource --cluster-id $CLUSTER_ID --resource-id eas-r-xxx --user-agent AlibabaCloud-Agent-Skills
```

**Key fields**:

| Field | Description |
|-------|-------------|
| `.Name` | Resource group name |
| `.Status` | Resource group status |
| `.TotalNodes` | Total node count |
| `.HealthyNodes` | Healthy node count |
| `.Nodes[]` | Node list |

---

### list-resources (Resource Group List)

```bash
aliyun eas list-resources --cluster-id $CLUSTER_ID --user-agent AlibabaCloud-Agent-Skills
```

---

## Gateway API

### describe-gateway (Gateway Details)

```bash
aliyun eas describe-gateway --cluster-id $CLUSTER_ID --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills
# or
aliyun eas describe-gateway --cluster-id $CLUSTER_ID --gateway-name my-gateway --user-agent AlibabaCloud-Agent-Skills
```

**Key fields**:

| Field | Description |
|-------|-------------|
| `.Name` | Gateway name |
| `.LoadBalancerList[0].Status` | Load balancer status |
| `.LoadBalancerList[0].Address` | Load balancer address |

---

### list-gateways (Gateway List)

```bash
aliyun eas list-gateways --cluster-id $CLUSTER_ID --user-agent AlibabaCloud-Agent-Skills
```

---

## Quick Diagnostic Command Summary

```bash
CLUSTER_ID="cn-hangzhou"
SERVICE="my-service"

# Quick view service status
alias ds='aliyun eas describe-service --cluster-id $CLUSTER_ID --service-name'

# Quick view logs
alias dl='aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name'

# Quick view events
alias de='aliyun eas describe-service-event --cluster-id $CLUSTER_ID --service-name'

# Quick view instances
alias di='aliyun eas list-service-instances --cluster-id $CLUSTER_ID --service-name'

# Quick diagnose
alias dd='aliyun eas describe-service-diagnosis --cluster-id $CLUSTER_ID --service-name'

# Usage examples
ds $SERVICE --user-agent AlibabaCloud-Agent-Skills | jq '{Status, RunningInstance, TotalInstance}'
dl $SERVICE --keyword "error" --limit 20 --user-agent AlibabaCloud-Agent-Skills
de $SERVICE --user-agent AlibabaCloud-Agent-Skills | jq '.Events[-5:]'
di $SERVICE --user-agent AlibabaCloud-Agent-Skills | jq '.Instances[].Status'
dd $SERVICE --user-agent AlibabaCloud-Agent-Skills | jq '.DiagnosisItems[]'
```
