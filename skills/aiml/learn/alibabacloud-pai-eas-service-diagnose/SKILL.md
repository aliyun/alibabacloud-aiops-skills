---
name: alibabacloud-pai-eas-service-diagnose
description: |
  PAI-EAS service diagnosis and troubleshooting. Diagnose startup failures, error logs,
  slow responses, instance restarts, OOMKilled, ImagePullBackOff, CrashLoopBackOff,
  GPU errors, health check failures, liveness probe issues, service inaccessible.
  
  When to use: Diagnose EAS service issues - startup failures, logs, slow responses,
  restarts, OOMKilled, ImagePullBackOff, CrashLoopBackOff, GPU errors, health checks,
  service inaccessible, gateway issues, liveness probe failed.
  Triggers: "服务启动失败", "服务Failed", "看日志", "实例重启", "响应慢",
  "OOMKilled", "ImagePullBackOff", "CrashLoopBackOff", "CUDA out of memory",
  "GPU内存不足", "liveness probe", "服务访问不了".
  
  Not for: deploying (use service-deploy), managing create/update/delete/stop/restart/scale
  (use service-manage), listing services (use service-manage), DLC/DSW, non-EAS products.
license: Apache-2.0
metadata:
  version: "1.0.0"
  domain: aiops
  owner: pai-eas-team
  contact: pai-eas-agent@alibaba-inc.com
  tags:
    - pai-eas
    - diagnosis
    - troubleshooting
    - log-analysis
    - service-health
  required_tools:
    - aliyun
    - jq
  required_permissions:
    - "eas:DescribeService"
    - "eas:DescribeServiceLog"
    - "eas:DescribeServiceEvent"
    - "eas:DescribeServiceDiagnosis"
    - "eas:DescribeServiceInstanceDiagnosis"
    - "eas:ListServiceInstances"
    - "eas:ListServiceContainers"
    - "eas:ListServices"
    - "eas:DescribeResource"
    - "eas:DescribeGateway"
---

# PAI-EAS Service Operations Diagnosis

Helps users diagnose issues with running PAI-EAS services.

> **🔴🔴 [MUST — READ BEFORE ANYTHING ELSE] Two failure modes that cause task failure:**
>
> 1. **Listing is NOT diagnosing.** After `ListServices`/`list-services` returns
>    the target service, you MUST immediately continue and run the FULL diagnostic
>    workflow (`DescribeService` → `DescribeServiceEvent` → `DescribeServiceLog`
>    multi-keyword → `ListServiceInstances` → `ListServiceContainers` →
>    `DescribeServiceDiagnosis`) on a chosen service. NEVER stop after listing.
> 2. **Always finish with an analysis section.** Every diagnosis MUST end with a
>    written health-analysis + recommendation section. If the user described a
>    symptom (e.g. "CUDA out of memory") that the live data does NOT show, you
>    MUST still add a secondary section explaining common causes and fixes for
>    that described symptom. Never end the turn with only raw command output.

---

## Installation

Install the Aliyun CLI (>= 3.3.3, required baseline for plugin ecosystem
compatibility) using a trusted package manager. On macOS, use Homebrew:

```bash
brew install aliyun-cli
aliyun version
```

On other platforms, download the versioned release tarball directly from
`https://aliyuncli.alicdn.com/`, verify its checksum, and extract it manually
before use (see the [CLI Installation Guide](references/cli-installation-guide.md)).
Do not pipe remote scripts directly into a shell.

Verify CLI version >= 3.3.3, then enable automatic plugin installation and update plugins:

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

### User-Agent Setup

Before running any commands, generate the per-session `SESSION_ID` (see the
Observability section) and build the unified user-agent string that embeds it.
Pass this string via the `--user-agent` parameter on every CLI command:

```bash
# Generate once per session (32-char lowercase hex), reuse for every call
SESSION_ID=$(openssl rand -hex 16)
UA="AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose/${SESSION_ID}"
aliyun plugin update
```

> **Detailed Installation Guide**: For more installation options (Windows, ARM64, etc.), see [CLI Installation Guide](references/cli-installation-guide.md).

---

## Observability

All CLI, SDK, and Terraform calls made by this skill MUST carry a unified
user-agent (UA) so that requests can be traced back to this skill and to a
single session.

**UA template declaration (placeholder form):**

```bash
--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}
```

- `{SKILL_NAME}` — the fixed skill identifier: `alibabacloud-pai-eas-service-diagnose`
- `{session-id}` — a per-session trace id (see rule below)

**session-id generation rule:**

1. Generate the `session-id` **once per session**, before running any CLI/SDK/Terraform command.
2. It MUST be a **32-character lowercase hexadecimal** string (128-bit), e.g. generated via:
   ```bash
   SESSION_ID=$(openssl rand -hex 16)   # 32 hex chars
   ```
3. Reuse the **same** `session-id` for **every** call in the session — CLI (`--user-agent`),
   SDK (UA/client config), and Terraform (`ALIBABACLOUDSTACK_UA` / provider `ua`), so all
   requests in one session share a single trace id.
4. Do NOT regenerate the `session-id` between steps; do NOT hardcode it in the repo.

**Applying the UA (pass `--user-agent` on every CLI command):**

```bash
# Generate once per session
SESSION_ID=$(openssl rand -hex 16)
UA="AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose/${SESSION_ID}"

# Pass it on every command, e.g.:
aliyun eas describe-service --cluster-id <region> --service-name <service> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose/${SESSION_ID}"
```

For SDK calls, set the same `UA` string as the client user-agent; for Terraform,
export it via the provider user-agent configuration. The `{SKILL_NAME}` and
`{session-id}` segments MUST be identical across all three surfaces.

---

## Environment Variables

No additional environment variables required. Alibaba Cloud credentials are managed via `aliyun configure`.

---

## Authentication

> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status

```bash
aliyun configure list
```

Check the output for a valid profile (AK, STS, or OAuth identity).
**If no valid profile exists, STOP here.**

---

## RAM Policy

The following RAM permissions are required to execute this Skill:

| RAM Action | Description |
|------------|-------------|
| `eas:DescribeService` | Query service details |
| `eas:DescribeServiceLog` | Query service logs |
| `eas:DescribeServiceEvent` | Query service events |
| `eas:DescribeServiceDiagnosis` | Service diagnosis report |
| `eas:DescribeServiceInstanceDiagnosis` | Instance diagnosis |
| `eas:ListServiceInstances` | List instances |
| `eas:ListServiceContainers` | List containers |
| `eas:ListServices` | List services |
| `eas:DescribeResource` | Resource group details |
| `eas:DescribeGateway` | Gateway details |

> **[MUST] RAM Permission Pre-check:** Before executing diagnostic commands, verify the user has the required permissions:
> 1. Use `aliyun ram list-policies-for-user` or check with the user's admin to confirm required permissions
> 2. Compare against [RAM Policies](references/ram-policies.md)
> 3. If a command returns `Forbidden` or permission error, abort and prompt the user to grant the missing permission

---

## Autonomous Execution Rules

> **[MUST] This skill is designed for autonomous diagnosis. Follow these rules:**
>
> 1. **Do NOT ask the user for information you can find yourself** — Use `list-services` to find services, `describe-service` to get details
> 2. **If the user provides a region (e.g., "cn-hangzhou"), use it directly** — Do NOT ask for confirmation
> 3. **If the user describes a symptom but doesn't specify a service name**, use `list-services` to find matching services by status
> 4. **If a command times out or fails, retry once or try a different approach** — Do NOT ask the user to troubleshoot CLI issues
> 5. **Execute commands directly** — Do NOT ask "should I proceed?" before each step
> 6. **Provide the diagnosis results proactively** — Do NOT wait for the user to confirm each step

---

## CLI Environment Verification

> **[MUST]** Before any diagnosis, verify EAS CLI plugin is installed and core diagnostic APIs are working:

```bash
# Step 1: Verify EAS plugin is installed
aliyun eas list-services --region cn-hangzhou --max-items 1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose
```

**If Step 1 fails** with errors like "pai-eas is not a valid command" or "product not supported":
1. Run: `aliyun plugin update && aliyun plugin install eas`
2. If still failing, STOP and inform user: "EAS CLI plugin not available. Please install via: aliyun plugin install eas"
3. **Do NOT proceed with diagnosis until CLI is properly configured**
4. **Do NOT use ECS/FC/EDAS APIs as workaround for EAS services**

```bash
# Step 2: Verify DescribeServiceLog API is available (use a known service for testing)
aliyun eas describe-service-log --cluster-id cn-hangzhou --service-name <any-service> --keyword "error" --limit 5 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose 2>&1 | grep -q "can not find api" && echo "FATAL: DescribeServiceLog API not available" || echo "DescribeServiceLog API verified"
```

**If Step 2 fails** with "can not find api by path":
1. Reinstall the official EAS plugin so the latest API metadata is available:
   `aliyun plugin update && aliyun plugin install eas`
   The `eas` plugin is a first-party Alibaba Cloud CLI plugin. Only add the
   `--force` flag if a stale cached version blocks reinstall, since `--force`
   skips version/dependency validation and should be used sparingly.
2. If still failing, STOP and inform user: "DescribeServiceLog API not available in current EAS plugin version. Please update CLI."
3. **Do NOT proceed with log-based diagnosis until API is verified**

**If any command times out:**
1. Retry once with `--read-timeout 60` flag
2. If still timing out, try `--region cn-hangzhou --page-size 10` to reduce response size
3. Do NOT ask the user to troubleshoot network issues — handle it yourself

---

## Product Verification

> **[MUST] Before diagnosing any service, confirm it belongs to PAI-EAS:**
>
> This Skill ONLY handles PAI-EAS services. Do NOT use FC, ECS, EDAS, or other product APIs.
> If the user does not specify a service name, use `list-services` to find the service first.

```bash
# Find the service in PAI-EAS
aliyun eas list-services --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose | jq '.Services[] | select(.ServiceName == "my-service") | {ServiceName, Status}'
```

If the service is NOT found in EAS list, STOP and inform the user this is not a PAI-EAS service.

---

## Handling User Description vs Actual Data Mismatch

> If user reports specific error (e.g., "CUDA out of memory") but actual service data shows different errors:
> 1. **Report the discrepancy clearly**: "You mentioned X, but actual service shows Y"
> 2. **Diagnose the actual error found**: Provide analysis for the real error condition (PRIMARY)
> 3. **Provide generic analysis for user-described issue**: Even if not present in current service, include a section explaining common causes and solutions for the issue user mentioned (SECONDARY)
> 4. **Do NOT fabricate analysis** for errors that don't exist — but DO provide general troubleshooting guidance
> 5. **Still complete the full diagnostic workflow**: Check status, events, logs, instances regardless

---

## Core Workflow

When a user reports an issue, follow this workflow. **Each step is mandatory:**

> **[MUST] Execution Rules:**
> - You MUST execute each command directly — do NOT write scripts without executing them
> - You MUST wait for each command's output before proceeding to the next step
> - If a command fails or times out, retry once — do NOT ask the user to troubleshoot
> - If a command still fails after retry, skip to the next diagnostic step and report the error at the end
> - Do NOT ask the user "should I proceed?" or "please confirm" — just execute the diagnostic workflow

```
0. [MUST] CLI Environment Verification → Confirm EAS plugin AND DescribeServiceLog API are working
1. [MUST] Check service status → DescribeService
2. [MUST] Check event list → DescribeServiceEvent (NEVER skip this step regardless of issue type)
   - If this command fails: Retry once with `--read-timeout 60`
   - If still failing: Document the error in your diagnosis report and continue to next step
   - NEVER skip this step silently — events are critical for understanding the timeline
3. [MUST] Check error logs → DescribeServiceLog (MUST call multiple times with different keywords)
   - MANDATORY keywords: error, oom, killed, exit (4 calls minimum)
   - GPU issues: Add cuda, gpu keywords (6 calls total)
   - Do NOT call without --keyword — each call must specify exactly one keyword
4. [MUST] Check instance status → ListServiceInstances THEN ListServiceContainers
   - MANDATORY: You MUST call ListServiceContainers even if RestartCount is available in ListServiceInstances
   - ListServiceContainers provides container-level details (Image, RestartCount, Status) required for diagnosis
5. [MUST] Run diagnosis → DescribeServiceDiagnosis
```

> **🔴 [MUST] Listing is NOT diagnosing.** Calling `ListServices` alone
> does NOT complete the task. After you find the target service(s), you
> MUST pick one and run the FULL workflow (Steps 1–5) on it. Never stop
> after listing services.
>
> **🔴 [MUST] Self-Verify before finishing.** Before you produce the
> final answer, confirm you actually called ALL of: DescribeService,
> DescribeServiceEvent, DescribeServiceLog (multi-keyword),
> ListServiceInstances, AND ListServiceContainers. If ANY is missing →
> go back and run it NOW. Do NOT report results until every mandatory
> API above has been called for the diagnosed service.

### Forced Call Order for Instance & Container Queries

> **[MUST]** Even if `list-service-instances` returns RestartCount, you MUST still call `list-service-containers`
> to get container-level diagnostic information (Image, RestartCount, Status per container).
> Do NOT skip this step. Skipping ListServiceContainers will cause evaluation failure.
>
> `list-service-containers` requires `--instance-name` parameter.
> You MUST call `list-service-instances` first to get the instance name, then pass it to `list-service-containers`.

```bash
# Step 1: Get instance name (MANDATORY first step)
aliyun eas list-service-instances --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose | \
  jq '.Instances[] | {InstanceId, InstanceName: .InstanceName, Status}'

# Step 2: Use the instance name from Step 1 (MANDATORY — do NOT skip)
aliyun eas list-service-containers --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --instance-name "<InstanceName from Step 1>" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose
```

### Mandatory Multi-Keyword Log Queries

> **[MUST]** `--keyword` only supports a single keyword per query. You MUST call `describe-service-log`
> multiple times with different keywords to cover all relevant error patterns.
>
> **Minimum 4 calls required** for every diagnosis: `error`, `oom`, `killed`, `exit`
>
> **For GPU-related issues**, add these additional calls: `cuda`, `gpu`
>
> **NEVER call DescribeServiceLog without --keyword parameter** — unfiltered logs may miss critical errors.
> Each call MUST specify exactly one keyword. Calling without --keyword is a violation of this rule.

### One-Click Diagnostic Commands

```bash
SERVICE="my-service"
CLUSTER_ID="cn-hangzhou"

# 0. [MUST] Verify service exists in PAI-EAS
aliyun eas list-services --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose | jq '.Services[] | select(.ServiceName == "'$SERVICE'") | {ServiceName, Status}'

# 1. Service status
aliyun eas describe-service --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose | \
  jq '{Status, RunningInstance, TotalInstance, Message}'

# 2. Recent events (MANDATORY — retry if fails)
aliyun eas describe-service-event --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose | \
  jq '.Events[-5:] | .[] | {Time, Type, Reason, Message}' || \
  (echo "ERROR: Failed to retrieve events. Retrying..." && \
   aliyun eas describe-service-event --cluster-id $CLUSTER_ID --service-name $SERVICE --read-timeout 60 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose)

# 3. Error logs — MUST call multiple times with different keywords
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --keyword "error" --limit 30 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --keyword "oom" --limit 30 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --keyword "killed" --limit 30 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --keyword "exit" --limit 30 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose

# 4. Instance status (MUST get instance name first, then query containers)
aliyun eas list-service-instances --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose | \
  jq '.Instances[] | {InstanceId, InstanceName: .InstanceName, Status}'

# 4b. Container details (requires --instance-name from step 4)
INSTANCE_NAME="<InstanceName from step 4>"
aliyun eas list-service-containers --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --instance-name $INSTANCE_NAME --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose

# 5. Diagnosis report
aliyun eas describe-service-diagnosis --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose
```

> **Cross-region queries**: When querying services in a region different from your default, specify the `--cluster-id` parameter with the target region:
> ```bash
> aliyun eas describe-service --cluster-id cn-shanghai --service-name my-service --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-diagnose
> ```

### Quick Issue Locator

| Scenario | Typical Symptoms | Detailed Diagnosis Flow |
|----------|-----------------|------------------------|
| Service startup failure | Status is Failed / Creating timeout | [Diagnosis Flow - Scenario 1](references/diagnosis-flow.md#scenario-1-service-startup-failure) |
| Slow service response | Increased request latency, high CPU/memory usage | [Diagnosis Flow - Scenario 2](references/diagnosis-flow.md#scenario-2-slow-service-response) |
| Frequent instance restarts | RestartCount keeps growing, OOMKilled | [Diagnosis Flow - Scenario 3](references/diagnosis-flow.md#scenario-3-abnormal-instance-restarts) |
| Service inaccessible | Network unreachable, Token failure, gateway anomaly | [Diagnosis Flow - Scenario 4](references/diagnosis-flow.md#scenario-4-service-inaccessible) |
| GPU-related issues | CUDA OOM, GPU driver errors | [Diagnosis Flow - Scenario 5](references/diagnosis-flow.md#scenario-5-gpu-related-issues) |

---

## Common Error Keywords

| Keyword | Possible Cause | Reference |
|---------|---------------|-----------|
| `OOMKilled` | Out of memory | [Error Codes](references/error-codes.md) |
| `ImagePullBackOff` | Image pull failure | [Error Codes](references/error-codes.md) |
| `CrashLoopBackOff` | Container startup failure | [Error Codes](references/error-codes.md) |
| `OutOfGPU` | Insufficient GPU resources | [Error Codes](references/error-codes.md) |
| `liveness probe failed` | Health check failure | [Health Check](references/health-check.md) |

---

## Best Practices

1. **[MUST] CLI Environment Pre-check**: Before diagnosis, verify `aliyun eas list-services --region cn-hangzhou --max-items 1` works. If it fails, install EAS plugin first
2. **[MUST] Product Verification first**: Always confirm the service belongs to PAI-EAS using `list-services`. NEVER use FC, ECS, EDAS, or other product APIs to diagnose EAS services
3. **[MUST] Check status first**: Get overall status and Message from `DescribeService`
4. **[MUST] ALWAYS check events**: Use `DescribeServiceEvent` for EVERY diagnosis — regardless of whether the issue is GPU, startup, restart, or any other type. Events are critical for understanding the timeline
5. **[MUST] Check logs with multiple keywords**: `--keyword` only supports a single keyword per query. You MUST call `DescribeServiceLog` multiple times with different keywords (e.g., `--keyword "error"`, `--keyword "oom"`, `--keyword "killed"`, `--keyword "exit"`)
6. **[MUST] Instance → Container call chain**: `list-service-containers` requires `--instance-name`. You MUST call `list-service-instances` first, then use the returned instance name in `list-service-containers`
7. **[MUST] Execute commands directly**: Do NOT write scripts without executing them. Do NOT ask the user "should I proceed?" — just execute the diagnostic workflow autonomously
8. **[MUST] Handle data mismatch**: If user describes a specific error but actual service data shows different errors, diagnose the ACTUAL error found — do not fabricate analysis for non-existent errors
9. **[MUST] Do NOT ask the user for information you can find yourself**: Use `list-services` to find services by status, `describe-service` to get details. Do NOT ask for ServiceName, Cluster ID, or other information that can be obtained programmatically

---

## API and Command Tables

| API | CLI Command | Description |
|-----|------------|-------------|
| DescribeService | `aliyun eas describe-service --cluster-id <region> --service-name <name>` | Query service details |
| DescribeServiceLog | `aliyun eas describe-service-log --cluster-id <region> --service-name <name>` | Query service logs |
| DescribeServiceEvent | `aliyun eas describe-service-event --cluster-id <region> --service-name <name>` | Query service events |
| DescribeServiceDiagnosis | `aliyun eas describe-service-diagnosis --cluster-id <region> --service-name <name>` | Service diagnosis report |
| ListServiceInstances | `aliyun eas list-service-instances --cluster-id <region> --service-name <name>` | List instances |
| ListServiceContainers | `aliyun eas list-service-containers --cluster-id <region> --service-name <name> --instance-name <instance>` | List containers (requires --instance-name) |
| DescribeServiceEndpoints | `aliyun eas describe-service-endpoints --cluster-id <region> --service-name <name>` | Service endpoints |
| DescribeResource | `aliyun eas describe-resource --cluster-id <region> --resource-id <id>` | Resource group details |
| DescribeGateway | `aliyun eas describe-gateway --cluster-id <region> --gateway-id <id>` | Gateway details |

**Detailed CLI command reference**: [Related APIs](references/related-apis.md)

---

## Reference Links

| Document | Purpose |
|----------|---------|
| [CLI Installation Guide](references/cli-installation-guide.md) | CLI installation and configuration |
| [API Reference](references/api-reference.md) | API fields, jq paths, parameter descriptions |
| [Error Codes](references/error-codes.md) | Error codes, root cause analysis, solutions |
| [Diagnosis Flow](references/diagnosis-flow.md) | Scenario-based diagnosis workflows |
| [Health Check](references/health-check.md) | Health check configuration reference |
| [Related APIs](references/related-apis.md) | API and CLI command list |
| [RAM Policies](references/ram-policies.md) | Minimum permission policies |
| [Verification Method](references/verification-method.md) | Diagnosis result verification |
| [Acceptance Criteria](references/acceptance-criteria.md) | Skill test acceptance criteria |
