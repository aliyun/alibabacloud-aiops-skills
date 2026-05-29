# Related CLI Commands

Quick reference for every CLI command this skill uses. All are read-only.

> Every command MUST be invoked with `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics` (omitted from the tables below for brevity).

---

## PAI-DLC commands (`pai-dlc` plugin)

| CLI command | API action | Purpose | Key parameters |
|-------------|-----------|---------|----------------|
| `get-job` | GetJob | Job details (status, Pods, Settings) | `--region` `--job-id` |
| `get-job-events` | GetJobEvents | Job-level system events | `--region` `--job-id` `--max-events-num` |
| `get-pod-events` | GetPodEvents | Pod-level Kubernetes events | `--region` `--job-id` `--pod-id` `--max-events-num` |
| `get-pod-logs` | GetPodLogs | Container logs | `--region` `--job-id` `--pod-id` `--max-lines` |
| `list-job-sanity-check-results` | ListJobSanityCheckResults | Hardware-check result list | `--region` `--job-id` |
| `get-job-sanity-check-result` | GetJobSanityCheckResult | Single sanity-check detail | `--region` `--job-id` `--sanity-check-number` |

---

## PAI Studio commands (`paistudio` plugin)

| CLI command | Purpose | Key parameters |
|-------------|---------|----------------|
| `GET /api/v1/quotas/{quota_id}/workloads/{workload_id}/diagnosis` | Resource diagnosis (queuing root cause) | `--region` `--header "Content-Type=application/json"` `--force` |

**Full invocation**:
```bash
aliyun paistudio GET /api/v1/quotas/{quota_id}/workloads/{workload_id}/diagnosis \
  --region <region> \
  --header "Content-Type=application/json" \
  --force \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
```

---

## Console Link Composition

Static console link (no token required, user logs in with their own account):

```
https://pai.console.aliyun.com/?regionId={region}&workspaceId={workspace_id}#/dlc/jobs/{job_id}/overview
```

- `region`: from the `--region` parameter (e.g. `cn-hangzhou`)
- `workspace_id`: from `get-job` response field `WorkspaceId`
- `job_id`: the DLC job ID (e.g. `dlcXXX`)
