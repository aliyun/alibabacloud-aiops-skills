---
name: alibabacloud-sas-openclaw-security
description: Perform security operations on OpenClaw environments by calling Alibaba Cloud Security Center (SAS) and ECS APIs via the aliyun CLI. Supports asset queries, vulnerability detection, baseline checks, alert analysis, daily security report generation, and Cloud Assistant command execution. Use this skill when users need to query OpenClaw security status, handle security alerts, check vulnerability risks, execute emergency commands, or generate security reports.
---

# OpenClaw Security Operations

Perform comprehensive security operations on the OpenClaw environment by calling Alibaba Cloud Security Center (SAS) and ECS APIs via the aliyun CLI.

## Workflow

Execute security operations in the following order:

1. **Query Instances**: Understand the OpenClaw deployment (SCA component query)
2. **Check Security**: Three-dimensional check — vulnerabilities, baselines, alerts
3. **Deep Dive**: Correlation analysis for identified risks
4. **Remediate**: Handle risks with reference to the remediation guide (guidance only)
5. **Recommend**: Recommend Alibaba Cloud security products based on risks
6. **Daily Report**: Generate a security daily report summary

For the detailed workflow, see [references/security_workflow.md](references/security_workflow.md).

## Prerequisites

All API calls are made through the **aliyun CLI**. Complete the following steps before use:

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-openclaw-security`

### 1. Confirm aliyun CLI Is Installed

Run the aliyun command to check installation status:

```bash
aliyun version
```

### 2. Check Credential Configuration

```bash
aliyun sts get-caller-identity
```

If not yet configured, run `aliyun configure` and follow the prompts. Credentials are stored in `~/.aliyun/config.json`.

> Do not hard-code AK/SK in scripts or environment variables. Manage credentials uniformly via `aliyun configure`.
> Never output credentials in plaintext under any circumstances, including access_key_id and access_key_secret.

### 3. Note on region-id Handling

When using Security Center (SAS) and Security Guardrail (AISC) features, only two regions are supported: `cn-shanghai` (Mainland China) and `ap-southeast-1` (outside Mainland China).

When using Cloud Assistant (ECS) features, the region-id is directly tied to the ECS instance region. Use `query_asset_detail` to look up the instance region-id by Security Center UUID.

### 4. Confirm RAM Permissions

All CLI calls in this Skill require the corresponding RAM Action authorizations for each cloud service. The minimum permission policy is documented in [references/ram-policies.md](references/ram-policies.md).

### About User-Agent

All aliyun CLI calls made through `base_client.py` automatically append `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-openclaw-security`. No manual configuration is needed.


## Quick Start

### Query OpenClaw Instances

List all deployed OpenClaw components, showing hostname, IP, and version.

```bash
python -m scripts.query_openclaw_instances \
    --name-pattern openclaw --biz sca_ai
```

### Query Asset Details

Query detailed information (OS, IP, disk, client status, etc.) for a single machine by UUID.

```bash
python -m scripts.query_asset_detail --uuid <UUID>
# Multiple UUIDs separated by commas
python -m scripts.query_asset_detail --uuid <UUID1>,<UUID2>
```

### Check Vulnerabilities

Query unresolved emergency vulnerabilities related to OpenClaw, and output a vulnerability list with remediation recommendations.

```bash
python -m scripts.check_openclaw_vulns \
    --name "emg:SCA:AVD-2026-1860246" --type emg --dealed n
# View only critical vulnerabilities
python -m scripts.check_openclaw_vulns --necessity asap
```

### Check Baseline Risks

Query a baseline check result summary by UUID. Specify `--risk-id` to drill into the check details for a specific risk item.

```bash
# Summary only
python -m scripts.check_openclaw_baseline --uuid <UUID>
# Drill into a specific risk item
python -m scripts.check_openclaw_baseline --uuid <UUID> --risk-id 320
```

### Check Alerts

Query unhandled security alerts, filterable by severity or host.

```bash
python -m scripts.check_openclaw_alerts --dealed N
# View only critical alerts
python -m scripts.check_openclaw_alerts --dealed N --levels serious
# Filter by specific hosts
python -m scripts.check_openclaw_alerts --uuids <UUID1>,<UUID2>
```

### Push Check Tasks

Trigger vulnerability scans and baseline checks for specified machines. Confirm the UUID before execution.

```bash
python -m scripts.push_openclaw_check_tasks --uuid <UUID>
```

### Install Security Guardrail

Deploy the security guardrail to a specified ECS instance via Cloud Assistant. Automatically waits for installation to complete and outputs the result.

```bash
python -m scripts.install_security_guardrail \
    --instance-ids i-abc123 --region cn-hangzhou
# Multiple machines
python -m scripts.install_security_guardrail \
    --instance-ids i-abc123,i-def456
```

### Query Guardrail Status

Detect the running status of the security guardrail on target machines via Cloud Assistant, used for post-installation verification.

```bash
python -m scripts.query_guardrail_status \
    --instance-ids i-abc123 --region cn-hangzhou
```

### Run Cloud Assistant Command

Remotely execute any Shell command on ECS instances, waiting for results in real time and returning the output.

```bash
python -m scripts.run_cloud_assistant_command \
    --instance-ids i-abc123 \
    --command "uname -a" \
    --region cn-hangzhou
```

> Notes:
> 1. The Cloud Assistant region must match the ECS instance region. SAS defaults to `cn-shanghai`; ECS defaults to `cn-hangzhou`.
> 2. Escape `$()` in commands as `\$()`.
> 3. Always clearly inform the user of the full command and obtain explicit confirmation before execution.

### Generate Security Daily Report

One-click aggregation of four dimensions — instances, vulnerabilities, baselines, and alerts — outputting a Markdown report to the `output/` directory.

```bash
python -m scripts.generate_security_report
```

## Script Reference

| Script | Purpose | Required Args | Optional Args (Common) |
|--------|---------|---------------|------------------------|
| `query_openclaw_instances.py` | Query OpenClaw SCA instance list | — | `--name-pattern`, `--biz`, `--max-pages` |
| `query_asset_detail.py` | Query asset details by UUID (host/OS/disk/client status) | `--uuid` | `--region` |
| `check_openclaw_vulns.py` | Query unresolved vulnerabilities | — | `--name`, `--type`, `--dealed`, `--necessity`, `--uuids` |
| `check_openclaw_baseline.py` | Query baseline check results by UUID | `--uuid` | `--risk-id` (drill into a specific risk item) |
| `check_openclaw_alerts.py` | Query security alert events | — | `--dealed`, `--levels`, `--uuids`, `--name` |
| `push_openclaw_check_tasks.py` | Push vulnerability and baseline check tasks (trigger scan) | `--uuid` | `--tasks` |
| `get_ai_agent_plugin_command.py` | Get AI Security Assistant installation command | — | `--output-dir` |
| `install_security_guardrail.py` | Install security guardrail via Cloud Assistant | `--instance-ids` | `--region`, `--timeout`, `--username` |
| `query_guardrail_status.py` | Query guardrail installation/running status via Cloud Assistant | `--instance-ids` | `--region`, `--timeout` |
| `run_cloud_assistant_command.py` | Remotely execute commands on ECS via Cloud Assistant | `--instance-ids`, `--command` | `--region`, `--type`, `--timeout`, `--username` |
| `generate_security_report.py` | Aggregate four-dimension security daily report (instances/vulns/baseline/alerts) | — | `--vuln-name`, `--name-pattern`, `--region` |

All scripts support `--region` and `--output-dir` parameters (`run_cloud_assistant_command.py` does not support `--output-dir`).

## Cloud Assistant Security Rules

Before executing any command via Cloud Assistant, the following rules must be followed:

1. Clearly inform the user of the full command content to be executed.
2. Require the user to explicitly confirm (reply with agreement) before executing the command.
3. If the user has not confirmed or the command is high-risk, execution is prohibited.

## Output Strategy

All query results and reports are saved to the `output/` directory:

- JSON format: Raw API response data, for programmatic consumption
- Markdown format: Human-readable reports, for display and archiving

## References

- [API Parameter Reference](references/api_reference.md)
- [Security Operations Workflow](references/security_workflow.md)
- [Remediation and Product Recommendations](references/remediation_guide.md)
- [RAM Permission Policies](references/ram-policies.md)
