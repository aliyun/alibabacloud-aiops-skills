# Acceptance Criteria

## Scenario: alibabacloud-pai-dlc-job-diagnostics

**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. PAI-DLC Product — verify product subcommand exists

```bash
# CORRECT: use pai-dlc plugin
aliyun pai-dlc get-job --region cn-hangzhou --job-id dlcXXX
aliyun pai-dlc get-pod-logs --region cn-hangzhou --job-id dlcXXX --pod-id podXXX --max-lines 100

# INCORRECT: wrong product name
aliyun dlc get-job ...        # `dlc` does not exist
aliyun pai get-job ...        # `pai` is not the correct plugin name
```

### 2. PAI Studio Product — verify ROA path invocation

```bash
# CORRECT: paistudio + RESTful path
aliyun paistudio GET /api/v1/quotas/quotaXXX/workloads/dlcXXX/diagnosis \
  --region cn-hangzhou --header "Content-Type=application/json" --force

# INCORRECT: wrong patterns
aliyun paistudio get-quota-workload-diagnosis ...   # this subcommand does not exist
aliyun pai-dlc GET /api/v1/quotas/...              # must use paistudio, not pai-dlc
```

### 3. Parameters — verify each parameter name exists

```bash
# CORRECT parameters
aliyun pai-dlc get-pod-logs --region cn-hangzhou --job-id dlcXXX --pod-id podXXX --max-lines 100

# INCORRECT parameters
aliyun pai-dlc get-pod-logs --lines 100                    # should be --max-lines
```

### 4. User-Agent — every API command must include it

```bash
# CORRECT
aliyun pai-dlc get-job --region cn-hangzhou --job-id dlcXXX \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics

# INCORRECT: missing user-agent on API-invoking command
aliyun pai-dlc get-job --region cn-hangzhou --job-id dlcXXX

# CORRECT: helper commands don't need user-agent
aliyun pai-dlc --help
aliyun pai-dlc get-job --help
```

---

## Behavioral Acceptance Criteria

### Scene 1: Queue Stuck Diagnosis

| Check | Expected |
|-------|----------|
| Job status is not `Queuing` / `Creating` | Do not run queuing diagnosis; inform the user of the current status |
| `ResourceId` empty (EcsSpec) | Do not call the resource-diagnosis API; explain that public resources have no such interface |
| `ResourceId` non-empty | First call `get-job` to obtain `ResourceId`, then invoke the resource-diagnosis API |
| Resource-diagnosis API returns all Succeeded | Inform the user that quota is sufficient; queuing may be due to queue strategy or transient scheduling |
| Any item Failed + `ExceedResources` | State explicitly which item exceeded the limit and by how much |

### Scene 2: Failure Diagnosis

| Check | Expected |
|-------|----------|
| `status = Stopped` | Do not perform failure diagnosis; explain it was a user-initiated stop |
| `ReasonCode = ResourceAllocateFailed` | Diagnose directly as resource shortage; do not provide remediation advice |
| `ReasonCode` empty | Drill deeper into pod logs / events to localize the cause |
| Logs contain `ReadTimeoutError` | Classify as a network issue |
| Logs contain `ImportError` | Classify as a runtime error |

### Scene 3: Health Check

| Check | Expected |
|-------|----------|
| User asks about GPU utilization | Direct to PAI console monitoring dashboard (provide console link) |
| Logs silent > 30 min | Flag as suspected hang |
| SanityCheck deviation > 5% | Annotate the outlier node |
