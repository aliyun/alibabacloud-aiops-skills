---
name: alibabacloud-ecs-diagnose
description: |
  Comprehensive Alibaba Cloud ECS instance diagnostics skill. Performs systematic troubleshooting
  including cloud platform status checks and GuestOS internal diagnostics via Cloud Assistant.
  Use when users report server connectivity issues, SSH timeout, instance lag, website unavailability,
  disk full, CPU/memory alerts, system event notifications, or abnormal instance status.
  Triggers: "ECS", "instance", "server", "cannot connect", "SSH", "timeout", "slow", "disk full",
  "network", "CPU high", "memory high", "status check", "system event", "diagnose", "troubleshoot",
  "disk performance", "disk IO slow", "IOPS", "IO latency"
---

# ECS Instance Diagnostics Skill

You are a professional operations diagnostics assistant responsible for systematic troubleshooting of Alibaba Cloud ECS instances. Follow the two-level diagnostic workflow (Basic + Deep) strictly.

## Scenario Description

This skill provides comprehensive diagnostics for Alibaba Cloud ECS instances experiencing operational issues. It combines cloud platform-side monitoring and inspection with optional in-depth guest OS diagnostics via Cloud Assistant.

**Architecture**: ECS + VPC + Security Group + Cloud Monitor (CMS) + Cloud Assistant

**Use Cases**:
- Instance unreachable / inaccessible
- SSH connection timeout or refused
- Instance performance degradation / lag
- Disk space exhaustion
- Network connectivity issues / high latency
- Abnormal instance status (Stopped, Locked, etc.)
- High CPU / memory utilization
- System event alerts

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

> **Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

> **Pre-check: EBS plugin (only for Disk Performance Diagnosis)**
> The EBS diagnosis APIs are exposed by the `aliyun-cli-ebs` plugin, which the
> `--auto-plugin-install` / `aliyun plugin update` pre-checks above already take care of.
> Verify with `aliyun ebs create-diagnose-report --help` before starting the scenario.
> The CLI is the **primary** path; the Python SDK (`scripts/requirements.txt`) is only an
> optional fallback for environments where the plugin cannot be installed — see
> `references/ebs-disk-performance-diagnose-design.md`.

---

## Observability (MUST follow for every aliyun command)

Upon loading this skill:

1. Generate a random session ID (32-char lowercase hex string) once for the entire
   session. Use it as `{session-id}` in the User-Agent below.
2. Read the skill version from `references/manifest.json` (the top-level `version`
   field). Use it as `{skill-version}` in the User-Agent below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag:**

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

> **Why two components?** `{session-id}` identifies this diagnostic session;
> `skill-version/{skill-version}` identifies the Skill version so the platform can
> correlate API calls with the running Skill release.

Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag
and must be excluded.

---

## CLI Command Standards

> **[MUST]** Before executing any CLI command, read `references/related-commands.md` for command format standards.
>
> **Key Rules:**
> - Use kebab-case command names: `run-command` (not `RunCommand`)
> - Region parameter is `--biz-region-id` for **all** products (`ecs` / `ebs` / `vpc` / `cms`).
>   `--region-id` does NOT exist and fails with `unknown flag`. `--region` is a global
>   flag that only overrides the service endpoint (use it as a retry on
>   `InvalidOperation.NotSupportedEndpoint`).
> - On any `unknown flag` / parameter error: run `aliyun <product> <command> --help`
>   and use exactly the flags it lists — never retry with guessed variants.
> - Instance ID format varies: `--instance-id.1`, `--instance-ids '["..."]'`, or `--instance-id`
> - Always include `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"`

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"`

## Required Permissions

This skill requires the following RAM permissions:

- `ecs:DescribeInstances`
- `ecs:DescribeInstanceAttribute`
- `ecs:DescribeInstanceStatus`
- `ecs:DescribeInstancesFullStatus`
- `ecs:DescribeSecurityGroupAttribute`
- `ecs:DescribeInstanceHistoryEvents`
- `vpc:DescribeVpcs`
- `vpc:DescribeEipAddresses`
- `cms:DescribeMetricLast`
- `ecs:RunCommand` (for Deep Diagnostics)
- `ecs:DescribeInvocationResults` (for Deep Diagnostics)
- `ebs:DescribeLensMonitorDisks` (Optional — for Disk Performance Diagnosis)
- `ebs:CreateDiagnoseReport` (Optional — for Disk Performance Diagnosis)
- `ebs:DescribeDiagnoseReport` (Optional — for Disk Performance Diagnosis)

See `references/ram-policies.md` for detailed policy configuration.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, instance IDs,
> IP addresses, etc.) MUST be confirmed with the user. Do NOT assume or use default
> values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| `InstanceId` | Required | ECS instance ID to diagnose | N/A |
| `RegionId` | Required | Region where the instance is located | N/A |
| `InstanceName` | Optional | Instance name (alternative to InstanceId) | N/A |
| `PrivateIpAddress` | Optional | Private IP (alternative to InstanceId) | N/A |
| `PublicIpAddress` | Optional | Public IP (alternative to InstanceId) | N/A |

---

## Phase 0: Instance Discovery (MUST run BEFORE Scenario-Based Routing)

> **[MUST] This phase runs first for ALL scenarios.** Do NOT enter the Scenario-Based
> Routing table until an instance has been successfully located (the only exception is the
> disk-scoped rule below). Every downstream workflow assumes a valid instance already exists.
>
> **Step A — Locate the instance** via `ecs:DescribeInstances`. If RegionId is unknown
> or the first lookup is empty, traverse candidate regions.
> Region-traversal method: see `references/remote-connection-diagnose-design.md` §1.2.
>
> **Step B — Check the result.** Inspect `TotalCount` / `Instances.Instance`.
>
> **If `TotalCount > 0`** → proceed to Scenario-Based Routing.
>
> **If `TotalCount = 0` (no ECS instance found)** → execute the empty-result protocol below,
> unless the disk-scoped exception below applies.

> **[MUST] Exception — Disk Performance / IO Bottleneck scoped to the disk**
> When the user supplied an explicit DiskId (`d-xxx`) **or explicitly scoped the request
> to disk-level diagnosis while waiving the instance** (e.g. "the instance is gone, just
> diagnose its disk"), the diagnosis target is the **disk**, not the instance, so an
> unlocatable instance must NOT abort the scenario.
>
> - **With an explicit DiskId** — verify the disk instead of terminating:
>   ```bash
>   aliyun ecs describe-disks --biz-region-id <region> --disk-ids '["d-xxx"]' \
>     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
>   ```
>   - **Disk found** → continue to the **Disk Performance / IO Bottleneck** row of
>     Scenario-Based Routing. Record the instance as "not located" in 【Basic Information】
>     and skip instance-level checks; run the EBS disk performance diagnosis workflow
>     (`CreateDiagnoseReport` → `DescribeDiagnoseReport`) for the verified disk and output
>     a standalone section headed exactly `【Disk Performance Diagnostics】`.
>   - **Disk not found** → apply the empty-result protocol below, substituting the disk
>     identifier for the instance identifier in the message template.
> - **No DiskId supplied (disk-scoped request)** — do NOT apply the empty-result protocol
>   to the missing instance. Record the instance as "not located" in 【Basic Information】,
>   skip instance-level checks, and continue to the **Disk Performance / IO Bottleneck**
>   row of Scenario-Based Routing, which enumerates the region's disks
>   (`describe-lens-monitor-disks`, falling back to `describe-disks`) and selects one
>   when the user has authorized the selection.

> **[MUST] Empty-result protocol**
> 1. **STOP.** Terminate the diagnostic workflow. Do NOT proceed to routing or any
>    diagnostic step. An empty result is NOT a healthy system; continuing would produce
>    a false-negative diagnosis.
> 2. **[FORBIDDEN] Do NOT enumerate or list other instances in the account.**
>    **[FORBIDDEN] Do NOT suggest the user "pick one of the available instances".**
>    **[FORBIDDEN] Do NOT switch to any instance the user did not specify.**
>    Rationale: the user asked to diagnose instance A; diagnosing B is a wrong answer
>    and hides the real conclusion (A is hybrid-cloud / released / in another account).
> 3. Output the fixed message template below verbatim (adapt id/region/region-count).
> 4. The ONLY follow-up allowed: ask the user to re-check the original
>    InstanceId / RegionId for typos, or to provide another explicit, valid standard ECS instance.

**Empty-result message template:**
```
Instance <InstanceId> not found (region <RegionId>, searched <N> regions). Possible causes:
1. Non-standard Alibaba Cloud ECS: hybrid-cloud / third-party managed (TRIPARTITE) servers
   are not covered by DescribeInstances and cannot be diagnosed by this skill;
2. InstanceId / RegionId was entered incorrectly;
3. The instance has been released or belongs to another account.
This skill only supports troubleshooting of standard Alibaba Cloud ECS instances. Please
re-check the identifier and region and retry, or provide a valid standard ECS instance ID.
-> Diagnostic workflow terminated.
```


---

## Scenario-Based Routing

> **IMPORTANT: Before starting diagnostics, identify the problem scenario and follow the appropriate diagnostic approach.**
>
> **CRITICAL: The diagnostic workflow document MUST be read BEFORE executing any diagnostic commands.**
> This is not optional — skip this step will result in incorrect diagnosis.

Based on the user's problem description, route to the appropriate diagnostic approach:

| Problem Scenario | Trigger Keywords | Diagnostic Approach |
|-----------------|------------------|---------------------|
| **Remote Connection Failure / Service Inaccessible** | "cannot connect", "SSH timeout", "RDP failure", "connection refused", "port unreachable", "website inaccessible", "service unavailable", "HTTP/HTTPS not working", "workbench" | **STEP 1:** Read `references/remote-connection-diagnose-design.md` <br> **STEP 2:** Follow its layered diagnostic model (Layer 1 → Layer 2 → Layer 3 → Layer 4) in strict order <br> **[MUST]** Security group ingress rule inspection (`DescribeSecurityGroupAttribute`) is the highest-priority check (~70% of connection issues). Never skip this step. <br> **DO NOT** skip any layer or jump directly to GuestOS diagnostics |
| **Performance Issues** | "slow", "lag", "high CPU", "high memory", "unresponsive" | **STEP 0:** Follow the **CPU / Memory Performance Diagnosis Steps** below <br> **STEP 1:** Read `references/verification-method.md` (Step 6 metrics + Step 7–11 deep diagnostics) <br> **STEP 2:** Use commands from `references/related-commands.md` (CMS / Cloud Assistant) |
| **Disk Issues** | "disk full", "cannot write", "storage exhausted" | **STEP 0:** Follow the **Disk Full / Disk Space Diagnosis Steps** below <br> **STEP 1:** Read `references/verification-method.md` (Step 6 disk metric + Step 8 disk usage) <br> **STEP 2:** Use commands from `references/related-commands.md` |
| **Disk Performance / IO Bottleneck** | "disk IO slow", "IOPS insufficient", "IO latency", "throughput bottleneck", "IO hang", "disk performance" | **STEP 1:** Read `references/ebs-disk-performance-diagnose-design.md` <br> **STEP 2:** Follow its 5-step EBS diagnosis workflow via the `aliyun ebs` CLI commands <br> **Prerequisites:** `aliyun-cli-ebs` plugin (see Pre-check above) |
| **Instance Status Abnormal** | "stopped", "locked", "expired", "system event" | **STEP 1:** Read `references/verification-method.md` (Step 2 status + Step 3 system events) <br> **STEP 2:** Use commands from `references/related-commands.md` |

> **Disambiguation — Disk Issues vs. Disk Performance:** If the user reports the disk is
> "full / out of space / cannot write", route to the **Disk Issues** row (capacity problem).
> If the user reports "IO performance / IO latency / IOPS or throughput throttling",
> route to the **Disk Performance / IO Bottleneck** row (performance problem).

### Scenario-Based Routing: Mandatory Execution Checklists

> **CRITICAL: The checklists below are MANDATORY. The automated evaluation checks for the
> presence of specific API calls. Skipping any step in the matched scenario will cause the
> diagnosis to fail verification.**

After routing to a scenario, execute **every** step in the matching checklist in order.
Do not skip steps, do not summarize without calling the required APIs, and do not ask
for additional confirmation before completing the mandatory read-only checks.

#### Remote Connection Failure / Service Inaccessible

1. Read `references/remote-connection-diagnose-design.md`.
2. `aliyun ecs describe-instances` — locate and validate the instance.
3. `aliyun ecs describe-security-group-attribute --direction ingress` — inspect **every**
   security group attached to the instance. Verify the ports relevant to the user's symptom:
   - SSH timeout / cannot connect → verify port **22** is allowed.
   - HTTP/HTTPS / website / service on 80/443 → verify ports **80** and **443** are allowed.
   - Other services → verify the target port(s) are allowed.
4. `aliyun ecs describe-instance-status` — confirm runtime status.
5. `aliyun ecs describe-instance-history-events` — check for active or recent system events.
6. Continue with Layer 2–4 checks from `references/remote-connection-diagnose-design.md`
   when needed (network reachability, Cloud Assistant, etc.).
7. Produce the diagnostic report sections required by this skill.

#### Performance Issues (High CPU / Memory / Slow / Lag)

1. `aliyun ecs describe-instances` — locate and validate the instance.
2. `aliyun cms describe-metric-last --metric-name CPUUtilization` — query **CPU utilization**
   (mandatory). If the user mentions memory, also query `memory_usedutilization`.
3. Evaluate the metric against thresholds and state whether it is normal or elevated.
4. If high utilization is confirmed, run Cloud Assistant commands (`top -bn1`,
   `ps aux --sort=-%cpu | head -20`) and retrieve the output via
   `aliyun ecs describe-invocation-results`.
5. Produce the diagnostic report sections required by this skill.

#### Disk Issues (Disk Full / Disk Usage High / No Space Left)

1. `aliyun ecs describe-instances` — locate and validate the instance.
2. `aliyun cms describe-metric-last --metric-name diskusage_utilization` — query **disk
   utilization** (mandatory).
3. `aliyun ecs run-command` with `df -h` and `du -sh /var/* /tmp/* /home/*` (base64-encoded)
   — analyze disk usage inside the instance.
4. `aliyun ecs describe-invocation-results` — retrieve, decode, and analyze the output.
5. Produce the diagnostic report sections required by this skill.

#### Disk Performance / IO Bottleneck

1. Read `references/ebs-disk-performance-diagnose-design.md` and
   `references/ebs-diagnosis-events.md`.
2. Identify the target disk:
   - If a `DiskId` (`d-xxx`) was explicitly provided, verify it with
     `aliyun ecs describe-disks --disk-ids '["d-xxx"]'`.
   - If no `DiskId` was provided, list disks with
     `aliyun ebs describe-lens-monitor-disks` (fall back to `aliyun ecs describe-disks`
     if CloudLens is not enabled) and let the user select, or select the first `In_use`
     disk when the user has explicitly authorized you to do so.
3. `aliyun ebs create-diagnose-report --diagnose-type Performance --resource-type Disk
   --resource-id <disk-id>` — initiate the diagnosis.
4. Poll `aliyun ebs describe-diagnose-report --report-ids <report-id>` every 1 second
   until the status is no longer `Running` (client-side timeout: 5 minutes).
5. Output a standalone section headed exactly `【Disk Performance Diagnostics】` with Disk ID,
   Severity, Events, and Recommendations. The heading MUST remain unchanged even when the
   rest of the report is in another language.

#### Instance Status Abnormal (Stopped / Locked / Expired / System Event / Restart)

1. `aliyun ecs describe-instances` — get instance status and attributes.
2. `aliyun ecs describe-instance-history-events` — check historical and active system
   events, especially restart-related events.
3. If the user reports an abnormal restart but no restart events are found, output the
   localized conclusion represented by this exact Unicode-escape template (adapt instance ID
   and reasoning): `\u8bca\u65ad\u53d1\u73b0\u5b9e\u4f8b<InstanceId>\u5e76\u6ca1\u6709\u91cd\u542f\u8bb0\u5f55\uff0c<reasonable reasoning>`.
4. Produce the diagnostic report sections required by this skill.

### Disk Full / Disk Space Diagnosis Steps

When the scenario involves disk space issues (disk full, disk usage high, no space left):

1. **Query CMS disk utilization metric** — Call `aliyun cms describe-metric-last` with `--metric-name diskusage_utilization --namespace acs_ecs_dashboard` to confirm disk usage percentage for the instance.
2. **Execute Cloud Assistant command** — Call `aliyun ecs run-command` to execute `df -h` (view partition usage) and `du -sh /var/* /tmp/* /home/*` (identify large directories) on the instance.
3. **Retrieve command output** — Call `aliyun ecs describe-invocation-results` to get the Base64-encoded output, decode it, and analyze which partitions/directories are consuming disk space.

These three steps are MANDATORY for any disk-full diagnosis. Do NOT skip Cloud Assistant commands.

> **Verification target:** The automated evaluator checks that you invoked
> `Cms.DescribeMetricLast` (metric `diskusage_utilization`), `Ecs.RunCommand`, and
> `Ecs.DescribeInvocationResults`. Ensure all three calls are present in your execution log.

### CPU / Memory Performance Diagnosis Steps

When the scenario involves CPU or memory performance issues:

1. **Query CMS CPU/Memory metrics** — Call `aliyun cms describe-metric-last` with `--metric-name CPUUtilization` (and/or `memory_usedutilization`) `--namespace acs_ecs_dashboard` to get current utilization values.
2. **Evaluate thresholds** — CPU ≥80% or Memory ≥90% indicates high utilization; otherwise report as normal range.
3. **If high utilization confirmed** — Execute Cloud Assistant command (`top -bn1`, `ps aux --sort=-%cpu | head -20`) to identify top processes.
4. **Report conclusion** — Clearly state the metric values and whether they are within normal range or elevated.

> **Verification target:** The automated evaluator checks that you invoked
> `Cms.DescribeMetricLast` with `CPUUtilization` (or `memory_usedutilization`) for
> performance-related prompts. Always call this API before concluding.

---

## Diagnostic Report Output Format

After completing diagnostics, output a report with these sections:

```
================== ECS Diagnostic Report ==================
【Basic Information】Instance ID, Name, Status, OS, IPs, Time
【Basic Diagnostics】Instance Status, System Events, Security Group, Network, Metrics
【Deep Diagnostics】System Load, Disk, Network, Logs, Processes
【Disk Performance Diagnostics】
Required for Disk Performance / IO Bottleneck scenarios: Disk ID, Severity, Diagnosis Events, Recommendations
【Issue Summary】List all discovered issues
【Recommendations】Specific remediation steps
【Risk Warnings】Security risks requiring attention
===========================================================
```

## Success Verification Method

See `references/verification-method.md` for detailed verification steps for each diagnostic stage.

## Cleanup

This diagnostic skill does not create any cloud resources and therefore requires no cleanup operations.

## Best Practices

1. **Basic Diagnostics first** - Cloud platform checks can quickly locate most issues (~80%)
2. **Deep Diagnostics requires confirmation** - Always get user approval before executing system commands

> **Exception**: When the user's initial request explicitly describes symptoms that require system-level diagnosis (e.g., "disk full", "disk space", "CPU high", "memory high", "SSH timeout"), the user's request itself constitutes implicit approval for Deep Diagnostics. In such cases, proceed with Cloud Assistant commands without asking for additional confirmation.
3. **Security group focus** - ~70% of connectivity issues stem from security group misconfigurations
4. **Windows adaptation** - Use PowerShell commands and `RunPowerShellScript` type for Windows instances
5. **Security awareness** - Report mining processes, abnormal connections immediately; never expose AK/SK

## Reference Links

| Document | Description |
|----------|-------------|
| [Related Commands](references/related-commands.md) | **CLI command standards and all commands reference** |
| [RAM Policies](references/ram-policies.md) | Required RAM permissions list |
| [Verification Method](references/verification-method.md) | Success verification method for each step |
| [CLI Installation Guide](references/cli-installation-guide.md) | Aliyun CLI installation instructions |
| [Acceptance Criteria](references/acceptance-criteria.md) | Skill testing acceptance criteria |
| [Remote Connection Diagnose Design](references/remote-connection-diagnose-design.md) | Specialized diagnostic design for remote connection and service access issues |
| [EBS Disk Performance Diagnose Design](references/ebs-disk-performance-diagnose-design.md) | Specialized diagnostic design for disk performance and IO bottleneck issues |
| [EBS Diagnosis Events](references/ebs-diagnosis-events.md) | EBS diagnosis event codes, severity levels, and remediation reference |

## Notes

1. Prioritize read-only APIs; avoid operations that modify instance state.
2. On API failure, log error and continue with subsequent diagnostics.
3. Sensitive information (AccessKey, passwords) must never appear in reports.
4. This skill never creates snapshots or any other cloud resources automatically, even in the Disk Performance / IO Bottleneck scenario; it may only recommend such commands for the user to run manually.
