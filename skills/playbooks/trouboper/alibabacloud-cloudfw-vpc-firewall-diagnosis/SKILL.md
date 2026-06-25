---
name: alibabacloud-cloudfw-vpc-firewall-diagnosis
description: >
  Diagnose Alibaba Cloud Cloud Firewall VPC firewall provisioning failures, route policy configuration failures,
  and closure pre-check risks using read-only CloudFirewall, CBN, VPC, STS, and ActionTrail APIs. Use this skill when
  troubleshooting VPC firewall creation failures, route policy/drainage configuration failures, firewall status stuck
  in configuring, or assessing route and ACL impact before closing VPC firewall drainage.
license: Apache-2.0
compatibility: >
  Requires Alibaba Cloud CLI (aliyun-cli >= 3.3.0) and Python 3.6+.
  All CLI commands use --profile and never pass AccessKey ID or AccessKey Secret explicitly.
  All Alibaba Cloud service calls must set User-Agent to AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis.
metadata:
  domain: aiops
  owner: cloudfw-team
  contact: cloudfw-agent@alibaba-inc.com
allowed-tools: Bash
hooks:
  PreToolUse:
    - matcher: Bash
      command: bash ${SKILL_DIR}/scripts/check-write-operation.sh
      description: >
        Bash command whitelist and confirmation gate. This read-only diagnostic skill only allows clearly matched
        read-only Alibaba Cloud CLI APIs, environment checks, local inspection commands, and bundled diagnostic scripts.
        Write operations, destructive local commands, or unmatched Bash commands return permissionDecision=ask.
---

# VPC Firewall Provisioning Failure Diagnosis

## Prerequisites

### CLI Tool
- **aliyun-cli version**: >= 3.3.0.
- **Validation**: `aliyun version`.

### Python Runtime
- **Python version**: Python 3.6+ for `scripts/analyze_routes.py` and `scripts/closure_precheck.py`.
- **Dependencies**: Standard library only (`json`, `subprocess`, `sys`).

### Alibaba Cloud Credentials
Configure a CLI profile with `aliyun configure`, then pass credentials through `--profile <profile>` in every command.

```bash
aliyun configure --profile <profile-name>
# Enter AccessKey ID, AccessKey Secret, Region, and output format as prompted.
```

Never hardcode AccessKey values in commands, scripts, or documentation. See [references/profile_setup_guide.md](references/profile_setup_guide.md).

### Required RAM Permissions
This skill is a read-only diagnostic tool. Grant only the minimum read-only actions below.

| Action | Purpose |
|---|---|
| `cloudfw:DescribeTrFirewallsV2List` | Query VPC firewall list and key status fields. |
| `cloudfw:DescribeVpcFirewallList` | Query VPC boundary firewall information. |
| `cloudfw:DescribeVpcFirewallPrecheckDetail` | Query precheck details. This API uses `--Region`, not `--RegionId`. |
| `cloudfw:DescribeFirewallTask` | Query drainage task status and `ErrorDetail`. |
| `cloudfw:DescribeTrFirewallPolicyBackUpAssociationList` | Query the rollback target route table. |
| `cloudfw:DescribeVpcFirewallControlPolicy` | Query VPC firewall ACL policies. |
| `actiontrail:LookupEvents` | Query recent operation history. |
| `cbn:ListTransitRouters` | Query transit routers under a CEN instance. |
| `cbn:ListTransitRouterRouteTables` | Query transit router route tables. |
| `cbn:ListTransitRouterRouteEntries` | Query route entries for route comparison. |
| `cbn:ListTransitRouterVpcAttachments` | Query VPC attachments. |
| `vpc:DescribeVpcs` / `vpc:DescribeVpcAttribute` | Query VPC basic attributes. |
| `sts:GetCallerIdentity` | Validate profile identity. |

Full permission details are documented in [references/ram-policies.md](references/ram-policies.md).

### User-Agent Requirement
All Alibaba Cloud service calls must include:

```bash
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Alibaba Cloud CLI AI-Mode and Plugin Update
Before running any Alibaba Cloud service CLI command in this skill, initialize CLI AI-Mode and refresh plugins:

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
aliyun plugin update
```

After the diagnostic workflow ends, disable AI-Mode:

```bash
aliyun configure ai-mode disable
```

Rules:
- AI-Mode is enabled only for the diagnostic workflow and must be disabled after completion.
- `set-user-agent` must use the full skill identifier: `AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis`.
- `plugin update` is a local/system CLI command and must be run before service API calls to ensure lowercase-hyphenated plugin actions are current; do not add `--user-agent` to this system command.
- Local-only environment commands such as `aliyun version`, `aliyun configure list`, and `python3 --version` do not call Alibaba Cloud service APIs and do not require the User-Agent flag.

### Environment Validation
Run these read-only checks before diagnosis:

```bash
aliyun version
aliyun configure list
aliyun sts get-caller-identity --profile <profile> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
python3 --version
```

## Mandatory Execution Rules

Before every execution:
1. Read this complete `SKILL.md`.
2. Read [references/execution_standards.md](references/execution_standards.md).
3. Identify the applicable scenario.
4. Follow the scenario flow exactly; do not skip mandatory steps.

## Core Principle: Read-Only Diagnosis

This skill is a read-only diagnostic assistant.

### Absolutely Forbidden
1. Never execute create, modify, delete, attach, detach, enable, disable, or any configuration-changing operation.
2. Never provide complete executable write commands with concrete parameter values.
3. Never modify Alibaba Cloud resources.
4. Never hardcode credentials or profile names.

### Correct Remediation Style
- Provide text-only configuration guidance.
- List required configuration fields and console navigation paths.
- Explain risks, dependencies, and verification points.
- Let the user perform all configuration changes manually in the console or their own approved workflow.

### Standard Report Declaration
Every diagnostic report must start with:

```text
Notice: This tool is a read-only diagnostic assistant. It only provides analysis and configuration guidance and will not perform any configuration changes.
Please apply all configuration changes manually in the Alibaba Cloud Console or through your own approved process.
```

### Allowed Command Categories
- AI-Mode setup commands: `aliyun configure ai-mode enable`, `aliyun configure ai-mode set-user-agent`, `aliyun plugin update`, and final `aliyun configure ai-mode disable`.
- `aliyun cloudfw describe-*` read-only queries.
- `aliyun cbn list-*` and `aliyun cbn describe-*` read-only queries.
- `aliyun actiontrail lookup-events` read-only operation history queries.
- `aliyun sts get-caller-identity` identity validation.
- Environment checks: `aliyun version`, `aliyun configure list`, `python3 --version`.
- Local read-only inspection commands such as `cat`, `ls`, `grep`, `find`, `pwd`, `which`, `date`, `stat`, and `file`.
- Bundled read-only scripts: `scripts/analyze_routes.py` and `scripts/closure_precheck.py`.

Any Bash command that does not match the whitelist must return `permissionDecision=ask`.

## Required User Inputs

Collect all information at once before diagnosis:
1. CLI profile name, for example `default`.
2. Whether the case is cross-region.
3. CEN instance ID.
4. Region ID when cross-region is involved, for example `cn-hangzhou`.
5. Problem type: creation failure, route policy configuration failure, or closure pre-check.

Do not proceed until the required inputs are confirmed.

## Closure Pre-check Iron Rules

- Never compare routes manually.
- Always save route table JSON outputs and run `scripts/analyze_routes.py`.
- Never infer route safety from `TotalCount` alone.
- Generate the final route risk conclusion from script output.

Detailed flow: [references/closure_precheck_guide.md](references/closure_precheck_guide.md).

## Scenario Quick Reference

### Scenario 1: VPC Firewall Creation Failed
First query `describe-tr-firewalls-v2-list`, then check `PrecheckStatus`, `ResultCode`, and firewall status fields. See [references/diagnosis_steps.md](references/diagnosis_steps.md#scenario-1-vpc-firewall-creation-failed).

### Scenario 2: Route Policy Configuration Failed
First query `describe-firewall-task` with `--TaskType VPC` and `--ChildInstanceId <vpc-id>`. See [references/diagnosis_steps.md](references/diagnosis_steps.md#scenario-2-route-policy-configuration-failed).

### Scenario 3: Closure Pre-check, Auto-Drainage Mode
Identify the mode, get `OriginalRouteTableId`, run `scripts/analyze_routes.py`, check ACL policies, and assess risk.

### Scenario 4: Closure Pre-check, Manual-Drainage Mode
Collect current and target route table IDs, run `scripts/analyze_routes.py`, check ACL policies, and assess risk.

## Strict Prohibitions

- Never skip the scenario's first mandatory API.
- Never query logs older than 24 hours unless the user explicitly requests a wider range.
- Never use `DescribeFirewallV2List`; this API is invalid for this skill.
- Never rely on precheck results alone. Use `ErrorDetail` and ActionTrail as final evidence.
- Never rely on memory or external historical knowledge for diagnostic logic. This skill must be self-contained.

## Key APIs and CLI Actions

| API | CLI action | Service | Required parameters | Purpose |
|---|---|---|---|---|
| `DescribeTrFirewallsV2List` | `describe-tr-firewalls-v2-list` | cloudfw | `--RegionId` | Query VPC firewall list. |
| `DescribeFirewallTask` | `describe-firewall-task` | cloudfw | `--TaskType VPC`, `--ChildInstanceId <vpc-id>` | Query route policy task status. |
| `DescribeTrFirewallPolicyBackUpAssociationList` | `describe-tr-firewall-policy-back-up-association-list` | cloudfw | `--FirewallId`, `--TrFirewallRoutePolicyId` | Query rollback target route table. |
| `DescribeVpcFirewallControlPolicy` | `describe-vpc-firewall-control-policy` | cloudfw | `--VpcFirewallId`, `--PageSize`, `--CurrentPage` | Query ACL policies. |
| `LookupEvents` | `lookup-events` | actiontrail | `--StartTime`, `--EndTime`, `--LookupAttribute.1.Key`, `--LookupAttribute.1.Value` | Query operation history. |
| `ListTransitRouterRouteTables` | `list-transit-router-route-tables` | cbn | `--RegionId`, `--TransitRouterId` | Query route tables. |
| `ListTransitRouterRouteEntries` | `list-transit-router-route-entries` | cbn | `--TransitRouterRouteTableId` | Query route entries. |

Critical notes:
- `DescribeVpcFirewallPrecheckDetail` uses `--Region`, not `--RegionId`.
- `ListTransitRouterRouteEntries` does not require `--TransitRouterId`.
- `LookupEvents` uses dot notation: `--LookupAttribute.1.Key`.
- All Alibaba Cloud service CLI commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis`.
- Local/system commands such as `aliyun version`, `aliyun configure list`, `aliyun configure ai-mode enable/disable`, and `aliyun plugin update` must not add the User-Agent flag.
- AI-Mode must be enabled before diagnosis, configured with the skill User-Agent, and disabled after the workflow.
- CLI profile option is lowercase: `--profile`.

## Output Format

For failure scenarios, report: root cause, evidence, and recommended remediation.
For closure pre-check scenarios, report: route rollback risk, ACL policy risk, recommended manual actions, and verification points.
Keep evidence concise and avoid exposing full resource inventories or sensitive identifiers unless needed for diagnosis.

## References

- [Closure Pre-check Guide](references/closure_precheck_guide.md)
- [Complete Diagnosis Steps](references/diagnosis_steps.md)
- [Diagnosis Rules](references/diagnosis_rules.md)
- [Full API Reference](references/api_reference.md)
- [Firewall Lifecycle](references/firewall_lifecycle.md)
- [Execution Standards](references/execution_standards.md)
