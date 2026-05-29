---
name: alibabacloud-pai-dlc-job-diagnostics
description: |
  PAI-DLC job diagnostics and health inspection. Queuing-stuck root cause
  analysis, failed-job localization, cluster health checks.
  Companion to the `alibabacloud-pai-dlc-job` skill (read-only — no writes).
  Triggers: "diagnose", "diagnose job", "job stuck", "why queuing",
  "queue stuck", "stuck in queue", "job failed", "failure reason",
  "healthcheck", "health check", "inspect job", "inspection".
---

# PAI-DLC Job Diagnostics and Health Inspection

Read-only diagnostic analysis for PAI-DLC distributed training jobs, covering
three scenarios:

- **Queuing-stuck root cause analysis** — quota check, node scheduling
  diagnosis, hyper-node availability
- **Failed-job localization** — failure classification, logs/events evidence
  chain, root cause identification
- **Cluster health inspection** — training throughput, hang detection,
  SanityCheck, restart stability

**Architecture**: PAI-DLC Job (read-only queries) + PAI Studio Resource
Diagnosis API (queuing scenario).

## 0. Dependencies

This skill performs **read-only diagnostics** only. All write operations
(create / update / stop jobs, resource discovery, etc.) live in the companion
skill `alibabacloud-pai-dlc-job`. The two skills are complementary in
responsibility and share a common field contract.

| Prerequisite Skill | Role | When to switch to it |
|--------------------|------|----------------------|
| `alibabacloud-pai-dlc-job` | Write ops (create/update/stop) + AIWorkSpace resource discovery | Creating / modifying / stopping jobs, or discovering Image / Dataset / CodeSource |
| This skill | Read-only diagnostics (logs / events / sanity-check / queuing root cause) | Job already exists — troubleshooting or health inspection |

**Discover and install the prerequisite skill:**

```bash
# Discover available skills
npx skills add aliyun/alibabacloud-aiops-skills --skill alibabacloud-find-skills
# Install the alibabacloud-pai-dlc-job skill itself
npx skills add aliyun/alibabacloud-aiops-skills --skill alibabacloud-pai-dlc-job
```

**Cross-skill field contract:** The `--job-id` / `--pod-id` values this skill
consumes are produced verbatim by `alibabacloud-pai-dlc-job` via
`list-jobs` / `get-job --cli-query "Pods[0].PodId"` — no transformation needed.
`--region` / `--workspace-id` follow the same resolution rules in both skills.

## Installation Requirements

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md).
> Then [MUST] run `aliyun configure set --auto-plugin-install true`.

> **Note on `--user-agent`:** Every API-invoking `aliyun` command in this skill MUST
> include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics`. Client-side helpers
> (`aliyun version`, `aliyun configure ...`, `aliyun plugin ...`,
> `aliyun <product> --help`) do not invoke remote APIs and therefore do not require
> the flag.

```bash
aliyun version
aliyun configure set --auto-plugin-install true
aliyun plugin update
aliyun pai-dlc --help
aliyun paistudio --help >/dev/null 2>&1 || aliyun plugin install --names aliyun-cli-paistudio

aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics"
# After session: aliyun configure ai-mode disable
```

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session**
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Permissions

> **[MUST] Permission Failure Handling:** When any command fails due to permission errors:
> 1. Read `references/ram-policies.md` for the full permission list
> 2. Use `ram-permission-diagnose` skill to guide the user
> 3. Pause and wait until the user confirms permissions have been granted

| Product | Permissions | Purpose |
|---------|-------------|---------|
| pai-dlc | `pai:GetJob`, `pai:GetPodLogs`, `pai:GetJobEvents`, `pai:GetPodEvents`, `pai:ListJobSanityCheckResults` | Job information collection |
| paistudio | `paistudio:GetQuotaWorkloadDiagnosis` | Queuing resource diagnosis |

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command,
> ALL user-customizable parameters (RegionId, JobId, etc.) MUST be confirmed with the user.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `region` | Yes | Region where the job runs |
| `job_id` | Yes | DLC job ID (e.g., `dlcXXX`) |

---

## Entry Routing

When a diagnostic request arrives, first call `get-job` to fetch job status,
then route by status:

| Job status | Route to scenario |
|------------|-------------------|
| `Queuing` / `Creating` | → Queuing-stuck root cause analysis |
| `Failed` | → Failed-job localization |
| `Running` | → Health inspection |
| `Stopped` | Inform the user "job was actively stopped", no diagnosis |
| `Succeeded` | → Historical review (follow Scenario 3 Execution steps) |

**Edge case — job was queuing but is now Stopped/Succeeded**: If the user
describes the job as "stuck in queue" but `get-job` shows `Stopped` or
`Succeeded`, still route to Scenario 1 (queuing analysis) but expect the
resource diagnosis API to return HTTP 400. Follow the "Fallback on API Failure"
procedure in Scenario 1.

Users may also directly request a specific scenario (e.g., "run a health
inspection" even when status is not Running).

---

## Diagnostic Toolbox

### PAI-DLC Read-Only Commands

```bash
aliyun pai-dlc get-job --region <r> --job-id <id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
aliyun pai-dlc get-job-events --region <r> --job-id <id> --max-events-num 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
aliyun pai-dlc get-pod-events --region <r> --job-id <id> --pod-id <pod> --max-events-num 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
aliyun pai-dlc get-pod-logs --region <r> --job-id <id> --pod-id <pod> --max-lines 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
aliyun pai-dlc list-job-sanity-check-results --region <r> --job-id <id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
aliyun pai-dlc get-job-sanity-check-result --region <r> --job-id <id> --sanity-check-number 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
```

### PAI Studio Resource Diagnosis (queuing scenario only)

```bash
aliyun paistudio GET /api/v1/quotas/{quota_id}/workloads/{job_id}/diagnosis \
  --region <r> --header "Content-Type=application/json" --force \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
```

**Hard constraint**: `quota_id` MUST come from `get-job`'s `ResourceId` field.
If `ResourceId` is empty (public pay-as-you-go), this API is unavailable.

Full API structure: see [references/resource-diagnosis-api.md](references/resource-diagnosis-api.md).

---

## Scenario 1: Queuing-Stuck Root Cause Analysis

**Trigger**: job status = `Queuing` / `Creating` and user reports it cannot be scheduled.

**Tools**: `get-job` → `paistudio resource diagnosis` → (optional) `get-job-events`.

**Hard constraints**:
- `ResourceId` empty → resource diagnosis unavailable; mine events for clues
- `ResourceId` non-empty → resource diagnosis API is the primary instrument

> **CRITICAL: pai-dlc vs paistudio — two different products**
>
> | Product | Scope | Commands |
> |---------|-------|----------|
> | **pai-dlc** | Job/Pod lifecycle (GetJob, GetJobEvents, ListJobs, GetPodLogs) | `aliyun pai-dlc get-job ...` |
> | **paistudio** | Platform-level services including resource diagnosis | `aliyun paistudio GET /api/v1/quotas/...` |
>
> The resource diagnosis API belongs to **paistudio**, NOT pai-dlc.
> Do **NOT** call `pai-dlc GetResourceQuota`, `pai-dlc ListResourceQuotas`,
> or any `pai-dlc GET /api/v1/resourcequotas/...` — these are wrong APIs
> and will fail. The correct command is:
> ```bash
> aliyun paistudio GET /api/v1/quotas/{quota_id}/workloads/{job_id}/diagnosis ...
> ```

**Pattern knowledge**: resource diagnosis returns 4 checks
(`self_quota` / `ancestor_quota` / `user_limit` / `queue_strategy`), plus node
scheduling and hyper-node analysis. Common patterns:
[references/diagnostic-patterns.md](references/diagnostic-patterns.md) §1.

**Agent latitude**: decide whether to compute the quota gap, whether to pull
events for corroboration, and how verbose the report should be.

### Fallback on API Failure

The PAI Studio resource diagnosis API may fail with HTTP 400/404 when the
job is no longer in an active queuing state (e.g., already `Stopped` by user).
In this case:

1. **Explicitly declare** the API failure in the report:
   `"Resource diagnosis API unavailable: HTTP {code} — {error message}"`
2. **Perform qualitative analysis** using only these data sources:
   - `get-job` → `ResourceRequest` (GPU/CPU/Memory demand per pod)
   - `get-job` → `PodCount` × per-pod resources = **total demand**
   - `get-job` → `EcsSpec` (instance type and its per-node capacity)
   - `get-job-events` → scheduling event timeline and queuing duration
3. **Prohibited language**: NEVER use hedging words such as "possibly",
   "might", "perhaps", "may not be sufficient". State only confirmed facts:
   - Total GPU demand = PodCount × RequestGPU = {computed value}
   - Instance type = {EcsSpec}
   - Queuing duration = {computed hours/minutes}
   - Job final status = {Stopped/Succeeded/etc.}
4. **Mandatory output structure** when API is unavailable:

```markdown
## Resource Diagnosis (API Unavailable — Configuration-Based Analysis)

- Diagnosis API: unavailable (HTTP {code}: {message})
- Resource demand: {PodCount} pods × {GPU/pod} GPU = {total} GPU cards
- Instance type: {EcsSpec}
- Queuing duration: {hours}h {minutes}m
- Quota ID: {ResourceId}
- Job final status: {status} ({ReasonCode})
- Conclusion: The job requested {total} GPU cards which could not be
  fulfilled within the queuing window before the job was {stopped/completed}.
```

---

## Scenario 2: Failed-Job Localization

**Trigger**: job status = `Failed`.

**Tools**: `get-job` → (as needed) `get-job-events` / `get-pod-events` / `get-pod-logs`.

**Hard constraints**:
- `Stopped` is not a failure — do not diagnose
- **[OUTPUT GUARD — RECOMMENDATIONS STRICTLY FORBIDDEN]** When the failure
  falls into any of the categories below, the diagnostic report **MUST strictly
  omit** any "Recommendations" / "Suggested fixes" / "Next steps" / "Solution"
  section, and output only the root cause and objective facts:
  - `ResourceAllocateFailed` (insufficient resources)
  - Job preempted / evicted (`ReasonMessage` contains `preempted` or `evicted`)
  - Spot instance reclamation
  - **Report MUST end on the diagnostic conclusion.** No sentence anywhere in
    the output may instruct the user to change configuration, request more
    quota, switch instance types, add retry logic, or modify any job parameter.
  - **Negative examples (ALL forbidden)**:
    - "Recommend using pay-as-you-go instances"
    - "Consider requesting more quota"
    - "Try switching to another zone"
    - "Disable preemptible jobs by setting EnablePreemptibleJob: false"
    - "Implement checkpointing and retry logic"
    - "Solution: Use guaranteed quota instead of oversold quota"
  - **Positive examples (allowed)**:
    - "Root cause: spot instance reclaimed by the cloud platform, triggering pod eviction and job failure."
    - "The job failed due to preemption/eviction of pods. ReasonCode: JobFailed."
  - **Only permitted user-facing suggestion**: "For quota policy adjustments, please contact your platform administrator."

**Mandatory output template for preemption/eviction/resource-shortage failures**:
```markdown
## Diagnosis Conclusion

- Failure reason: {classification} ({ReasonCode}: {ReasonMessage})
- Affected pods: {pod list with SubStatus}
- Timeline: {key timestamps from events}
- Evidence: {quoted ReasonMessage or event details}

For quota policy or resource allocation adjustments, please contact your
platform administrator.
```

**Pattern knowledge**: failure-classification priority
(network > image > runtime > resource > config > system), exit-code meanings,
keyword-matching rules. See
[references/diagnostic-patterns.md](references/diagnostic-patterns.md) §2.

**Agent latitude**: when `ReasonCode` is clear, logs may be unnecessary; when
logs already explain the issue, events may be unnecessary. Decide investigation
depth based on information sufficiency.

---

## Scenario 3: Health Inspection

**Trigger**: job status = `Running` and user requests inspection / health check.

**Tools**: `get-job` + `get-job-events` + `get-pod-logs`
+ `list-job-sanity-check-results`.

**Execution steps**:
1. `get-job` → obtain status, WorkspaceId, Pod list, whether `EnableSanityCheck` is set
2. `get-job-events` → event-chain analysis (scheduling, restarts, etc.)
3. `get-pod-logs` → target the **master pod** (rank=0) first; extract structured training metrics if present
4. `list-job-sanity-check-results` → execute only if `EnableSanityCheck=true` in job settings
5. **Generate console links (MANDATORY — must always output both links)**:
   - Job overview: `https://pai.console.aliyun.com/?regionId={region}&workspaceId={workspace_id}#/dlc/jobs/{job_id}/overview`
   - Monitoring dashboard: `https://pai.console.aliyun.com/?regionId={region}&workspaceId={workspace_id}#/dlc/jobs/{job_id}/monitor`
   - **Mandatory closing notice** (append verbatim to every inspection report):
     ```
     > GPU/memory real-time resource utilization metrics require the monitoring
     > dashboard above. This skill's CLI commands do not support fetching
     > runtime utilization data directly.
     ```
   This step is **mandatory** regardless of job status (Running, Succeeded, or
   any other state). Even if the job has already completed, the user needs
   the monitoring link to review historical resource utilization.

**Dimension matrix** (mandatory vs optional):

| Dimension | Mandatory/Optional | Notes |
|-----------|-------------------|-------|
| Training throughput | Optional | Extract from master pod logs |
| Hang detection | Running only | Skip for Succeeded jobs |
| Hardware health | Optional | Requires `EnableSanityCheck=true` |
| Restart stability | **Mandatory** | Read `RestartCount` directly from `get-job` |

**Note on resource utilization**: GPU/memory metrics are NOT available via this
skill's CLI commands. The monitoring dashboard link (step 5) and its closing
notice are **mandatory** in every inspection report — do not omit them.

Interpretation rules per dimension: see
[references/healthcheck-dimensions.md](references/healthcheck-dimensions.md).

**Agent latitude**: kilo-card jobs focus on Hang + SanityCheck; small jobs
look at training throughput from logs. Decide depth and report verbosity
from scale and user intent.

---

## Best Practices

1. **`get-job` first, route second** — never assume status; query and then route
2. **Cap response size** — `--max-lines 100` / `--max-events-num 50` to avoid context blow-up
3. **Find the problem pod** — among `get-job` Pods, focus on `Status=Failed/Unknown` or those with `ReasonMessage`
4. **Read log tail** — errors usually live in the last few dozen lines; no need to pull the whole log
5. **Exit codes are clues, not conclusions** — `exit 137` may be OOM or external kill; combine with context
6. **Don't over-diagnose** — when `ReasonCode` already states the cause, skip the full log dump
7. **Console links** — generate both overview and monitoring links so the user can jump into the console for details and resource utilization metrics
8. **Read-only** — this skill MUST NEVER execute `stop` / `update` / `create`
9. **Report summary** — present a per-dimension rating table at the end of the report:

| Dimension | Rating | Key Finding |
|-----------|--------|-------------|
| Training throughput | ✅/⚠️/❌/N/A | ... |
| Hang detection | ✅/⚠️/❌/N/A | ... |
| Hardware health | ✅/⚠️/❌/N/A | ... |
| Restart stability | ✅/⚠️/❌ | ... |

## Reference Links

| Document | Contents |
|----------|----------|
| [references/resource-diagnosis-api.md](references/resource-diagnosis-api.md) | PAI Studio resource diagnosis API full reference |
| [references/diagnostic-patterns.md](references/diagnostic-patterns.md) | Failure pattern knowledge base (queuing / failure / hang / restart) |
| [references/healthcheck-dimensions.md](references/healthcheck-dimensions.md) | Health inspection dimensions and interpretation rules |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/related-commands.md](references/related-commands.md) | CLI command quick reference |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
| [references/verification-method.md](references/verification-method.md) | Verification method |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
