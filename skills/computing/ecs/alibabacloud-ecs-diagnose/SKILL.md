---
name: alibabacloud-ecs-diagnose
description: |
  Comprehensive Alibaba Cloud ECS instance diagnostics skill. Performs systematic troubleshooting
  including cloud platform status checks and GuestOS internal diagnostics via Cloud Assistant.
  Use when users report server connectivity issues, SSH timeout, instance lag, website unavailability,
  disk full, CPU/memory alerts, system event notifications, or abnormal instance status.
  Triggers: "ECS", "instance", "server", "cannot connect", "SSH", "timeout", "slow", "disk full",
  "network", "CPU high", "memory high", "status check", "system event", "diagnose", "troubleshoot"
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

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

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

---

## CLI Command Standards

> **[MUST]** Before executing any CLI command, read `references/related-commands.md` for command format standards.
>
> **Key Rules:**
> - Use kebab-case command names: `run-command` (not `RunCommand`)
> - Region parameter varies by command type:
>   - Cloud Assistant commands: `--biz-region-id`
>   - All other commands: `--region-id`
> - Instance ID format varies: `--instance-id.1`, `--instance-ids '["..."]'`, or `--instance-id`
> - Always include `--user-agent AlibabaCloud-Agent-Skills`

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

## Scenario-Based Routing

> **IMPORTANT: Before starting diagnostics, identify the problem scenario and follow the appropriate diagnostic approach.**
>
> **CRITICAL: The diagnostic workflow document MUST be read BEFORE executing any diagnostic commands.**
> This is not optional — skip this step will result in incorrect diagnosis.

Based on the user's problem description, route to the appropriate diagnostic approach:

| Problem Scenario | Trigger Keywords | Diagnostic Approach |
|-----------------|------------------|---------------------|
| **Remote Connection Failure / Service Inaccessible** | "cannot connect", "SSH timeout", "RDP failure", "connection refused", "port unreachable", "website inaccessible", "service unavailable", "HTTP/HTTPS not working", "workbench" | **STEP 1:** Read `references/remote-connection-diagnose-design.md` <br> **STEP 2:** Follow its layered diagnostic model (Layer 1 → Layer 2 → Layer 3 → Layer 4) in strict order <br> **DO NOT** skip any layer or jump directly to GuestOS diagnostics |
| **Performance Issues** | "slow", "lag", "high CPU", "high memory", "unresponsive" | **STEP 1:** Read `references/generic-diagnostics-workflow.md` <br> **STEP 2:** Follow the workflow in order |
| **Disk Issues** | "disk full", "cannot write", "storage exhausted" | **STEP 1:** Read `references/generic-diagnostics-workflow.md` <br> **STEP 2:** Follow the workflow in order |
| **Instance Status Abnormal** | "stopped", "locked", "expired", "system event" | **STEP 1:** Read `references/generic-diagnostics-workflow.md` <br> **STEP 2:** Follow the workflow in order |


---

## Diagnostic Report Output Format

After completing diagnostics, output a report with these sections:

```
================== ECS Diagnostic Report ==================
【Basic Information】Instance ID, Name, Status, OS, IPs, Time
【Basic Diagnostics】Instance Status, System Events, Security Group, Network, Metrics
【Deep Diagnostics】System Load, Disk, Network, Logs, Processes
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
| [Generic Diagnostics Workflow](references/generic-diagnostics-workflow.md) | Standard two-level diagnostic workflow for general ECS issues |

## Notes

1. Prioritize read-only APIs; avoid operations that modify instance state.
2. On API failure, log error and continue with subsequent diagnostics.
3. Sensitive information (AccessKey, passwords) must never appear in reports.
