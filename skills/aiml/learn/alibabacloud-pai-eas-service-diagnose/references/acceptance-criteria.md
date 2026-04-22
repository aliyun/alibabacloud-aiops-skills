# Acceptance Criteria: alibabacloud-pai-eas-service-diagnose

**Scenario**: PAI-EAS Service Diagnosis
**Purpose**: Skill test acceptance criteria

---

# Correct CLI Command Patterns

## 1. EAS Service Diagnostic Operations

### Correct: Query service status

```bash
aliyun eas describe-service --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills
```

### Incorrect: Missing --user-agent

```bash
aliyun eas describe-service --cluster-id cn-hangzhou --service-name my-service
```

### Incorrect: Using API format instead of plugin mode

```bash
aliyun eas DescribeService --region cn-hangzhou --ServiceName my-service
```

## 2. Log Query

### Correct: Keyword filtering

```bash
aliyun eas describe-service-log --cluster-id cn-hangzhou --service-name my-service --keyword "error" --limit 20 --user-agent AlibabaCloud-Agent-Skills
```

### Incorrect: Missing --service-name

```bash
aliyun eas describe-service-log --cluster-id cn-hangzhou --keyword "error" --user-agent AlibabaCloud-Agent-Skills
```

## 3. Event Query

### Correct: Query service events

```bash
aliyun eas describe-service-event --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills
```

### Correct: Filter Warning events

```bash
aliyun eas describe-service-event --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills | jq '.Events[] | select(.Type == "Warning")'
```

## 4. Instance Query

### Correct: List instances

```bash
aliyun eas list-service-instances --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills
```

### Correct: List containers (requires --instance-name)

```bash
# First get instance name
aliyun eas list-service-instances --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills | jq -r '.Instances[0].InstanceName'

# Then list containers with instance-name
aliyun eas list-service-containers --cluster-id cn-hangzhou --service-name my-service --instance-name my-service-xxxxx-yyyyy --user-agent AlibabaCloud-Agent-Skills
```

## 5. Gateway Query

### Correct: Query gateway details

```bash
aliyun eas describe-gateway --cluster-id cn-hangzhou --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills
```

### Incorrect: Missing cluster-id

```bash
aliyun eas describe-gateway --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills
```

---

# Diagnosis Flow Verification

## 1. Service Startup Failure Diagnosis

### Correct flow

```bash
# 1. Check service status
aliyun eas describe-service --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills | jq '{Status, Message}'

# 2. Check failure events
aliyun eas describe-service-event --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills | jq '.Events[] | select(.Type == "Warning")'

# 3. Check error logs
aliyun eas describe-service-log --cluster-id cn-hangzhou --service-name my-service --keyword "error" --limit 20 --user-agent AlibabaCloud-Agent-Skills
```

### Incorrect: Skipping status check and jumping to logs

```bash
# Wrong: Not confirming service status first
aliyun eas describe-service-log --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills
```

## 2. jq Filter Verification

### Correct: Extract status information

```bash
aliyun eas describe-service --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills | jq '{Status, RunningInstance, TotalInstance, Message}'
```

### Correct: Filter restart events

```bash
aliyun eas describe-service-event --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills | jq '.Events[] | select(.Reason == "Restarted")'
```

### Incorrect: Wrong jq path

```bash
# Wrong: Field name case error
aliyun eas describe-service --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills | jq '{status, runningInstance}'
```

---

# Security Rule Verification

## Correct: Credential check

```bash
aliyun configure list
```

## Incorrect: Reading AK/SK

```bash
# Forbidden: Reading or outputting AK/SK
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET
```

## Incorrect: Asking user to input AK/SK

```bash
# Forbidden: Interactive credential input
read -p "Enter AccessKey ID: " AK
read -p "Enter AccessKey Secret: " SK
```

---

# Parameter Confirmation Requirements

## Correct: All user parameters must be confirmed

The following parameters must be confirmed before diagnosis:
- Region
- ServiceName
- InstanceId (if querying a specific instance)

## Incorrect: Using default values without confirmation

```bash
# Wrong: Using default region without asking the user
aliyun eas describe-service --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills
```

---

# Error Keyword Identification

## Correct: Identify common errors

| Keyword | Correct Diagnosis Direction |
|---------|-----------------------------|
| `OOMKilled` | Out of memory, suggest increasing memory specification |
| `ImagePullBackOff` | Image pull failure, check image address and permissions |
| `CrashLoopBackOff` | Container startup failure, check startup command and configuration |
| `OutOfGPU` | Insufficient GPU resources, check tp parameter or change specification |
| `liveness probe failed` | Health check failure, adjust health check parameters |

## Incorrect: Wrong diagnosis direction

```markdown
# Wrong: Diagnosing OOMKilled as a network issue
OOMKilled → Check network configuration
```

---

# Diagnosis Suggestion Verification

## Correct: Provide actionable suggestions

```markdown
OOMKilled issue suggestions:
1. Increase memory specification (e.g., upgrade from 16Gi to 32Gi)
2. Check for memory leaks
3. For large models, consider model quantization
```

## Incorrect: Provide vague suggestions

```markdown
# Wrong: Suggestions not specific
OOMKilled issue suggestions:
- Optimize memory usage
- Check configuration
```

---

# Boundary Verification

## Correct: Identify Skill boundaries

Diagnostic scenarios:
- Service status check ✅
- Log viewing and analysis ✅
- Event analysis ✅
- Instance status diagnosis ✅

Non-diagnostic scenarios (should use other Skills):
- Create/update/delete services → `alibabacloud-pai-eas-service-manage`
- Start/stop/restart services → `alibabacloud-pai-eas-service-manage`
- Auto-scaling configuration → `alibabacloud-pai-eas-service-manage`
- Deploy new services → `alibabacloud-pai-eas-service-deploy`
