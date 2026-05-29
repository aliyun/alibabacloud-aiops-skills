# Verification Method

Steps to verify the correctness of CLI commands used in this skill.

> **`--user-agent` rule:** Only business API commands (`list-jobs`, `get-job`,
> `get-pod-logs`, ...) carry the `--user-agent` flag. Client-side helpers
> (`--help`, `plugin install`, `configure ...`) MUST NOT include it.

---

## 1. Verify PAI-DLC Commands

For every `aliyun pai-dlc` command used in the skill, run `--help` to confirm:

```bash
# Verify subcommands exist
aliyun pai-dlc get-job --help
aliyun pai-dlc get-job-events --help
aliyun pai-dlc get-pod-events --help
aliyun pai-dlc get-pod-logs --help
aliyun pai-dlc list-job-sanity-check-results --help
aliyun pai-dlc get-job-sanity-check-result --help
```

**Checkpoints**:
- Subcommand exists (no `unknown command` error)
- Every parameter name used in the skill appears in the help output

---

## 2. Verify PAI Studio Commands

```bash
# Verify the paistudio plugin is installed
aliyun paistudio --help

# Verify ROA path-call format (dry-run, no real execution)
aliyun paistudio GET /api/v1/quotas/test/workloads/test/diagnosis \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --force \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
# Expected: 404 or parameter error (path format accepted), NOT `unknown command`.
```

---

## 3. End-to-End Verification (requires a real job)

### Queuing diagnosis verification

```bash
# 1. Pick a job in Queuing state
aliyun pai-dlc list-jobs --region <r> --status Queuing \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics

# 2. Fetch its ResourceId
aliyun pai-dlc get-job --region <r> --job-id <id> --cli-query "ResourceId" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics

# 3. Call resource diagnosis
aliyun paistudio GET /api/v1/quotas/<ResourceId>/workloads/<job_id>/diagnosis \
  --region <r> --header "Content-Type=application/json" --force \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
# Expected: response contains Diagnosis.ResourceDiagnosis and Diagnosis.SchedulingDiagnosis
```

### Failure diagnosis verification

```bash
# 1. Pick a Failed job
aliyun pai-dlc list-jobs --region <r> --status Failed \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics

# 2. Fetch details (includes Pods, ReasonCode)
aliyun pai-dlc get-job --region <r> --job-id <id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics

# 3. Fetch pod logs
aliyun pai-dlc get-pod-logs --region <r> --job-id <id> --pod-id <pod> --max-lines 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
# Expected: log content returned
```

### Health-inspection verification

```bash
# 1. Pick a Running job
aliyun pai-dlc list-jobs --region <r> --status Running \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics

# 2. Fetch pod logs (master pod)
aliyun pai-dlc get-pod-logs --region <r> --job-id <id> --pod-id <master-pod> --max-lines 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
# Expected: log content returned

# 3. Fetch SanityCheck results
aliyun pai-dlc list-job-sanity-check-results --region <r> --job-id <id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
# Expected: result list, or empty when SanityCheck is disabled
```
