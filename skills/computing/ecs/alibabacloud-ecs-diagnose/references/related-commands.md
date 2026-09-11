# Related CLI Commands

This document provides a comprehensive reference of all Aliyun CLI commands used in the ECS diagnostics skill.

---

## CLI Command Standards

> **CRITICAL: All CLI commands MUST follow these standards to avoid parameter errors.**

### General Rules

| Rule | Correct | Incorrect |
|------|---------|-----------|
| **Command name** | `run-command` (kebab-case) | `RunCommand` (PascalCase) |
| **User agent** | Always include `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` | Missing user-agent |

### Region Parameter — use `--biz-region-id` for ALL products

> **[MUST]** Current Aliyun CLI (>= 3.4, and any CLI where the product plugin is
> installed — which this skill's pre-check enforces via `--auto-plugin-install`)
> exposes the API's `RegionId` parameter as **`--biz-region-id`** for **every**
> product (`ecs`, `ebs`, `vpc`, `cms`). `--region-id` is **not** a valid flag and
> fails immediately with `Error: unknown flag: --region-id`.

| Flag | Meaning | Use |
|------|---------|-----|
| `--biz-region-id <region>` | The API's own `RegionId` parameter | **Always** — ECS / EBS / VPC / CMS / Cloud Assistant commands |
| `--region <region>` | Global flag; overrides only the **service endpoint** region | Only as a retry when endpoint resolution fails (see below) |
| `--region-id <region>` | ❌ Does not exist | Never |

**[MUST] Flag self-correction rule:** if a command fails with `unknown flag` or
`Missing/Invalid parameter`, do **not** retry blindly with guessed variants. Run
`aliyun <product> <command> --help` once and use exactly the flags it lists.

**Newer-region endpoint fallback:** if a per-region call fails with
`InvalidOperation.NotSupportedEndpoint` (common for newly launched regions), retry
the same command with the global `--region <region>` flag added to force the
regional endpoint:

```bash
aliyun ecs describe-instances --biz-region-id <region> --region <region> \
  --instance-ids '["i-xxxxx"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

### Instance ID Parameter (Command-Specific)

| Command | Parameter Format | Example |
|---------|------------------|---------|
| `run-command` | `--instance-id.1` (indexed) | `--instance-id.1 i-xxxxx` |
| `describe-instances-full-status` | `--instance-id.1` (indexed) | `--instance-id.1 i-xxxxx` |
| `describe-instances` | `--instance-ids` (JSON array) | `--instance-ids '["i-xxxxx"]'` |
| `describe-instance-attribute` | `--instance-id` (single) | `--instance-id i-xxxxx` |
| `describe-instance-history-events` | `--instance-id` (single) | `--instance-id i-xxxxx` |

---

## Cloud Assistant Commands

### RunCommand Standard Format

```bash
# Linux instance
aliyun ecs run-command \
  --biz-region-id <region-id> \
  --instance-id.1 <instance-id> \
  --type RunShellScript \
  --command-content '<base64-encoded-command>' \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Windows instance
aliyun ecs run-command \
  --biz-region-id <region-id> \
  --instance-id.1 <instance-id> \
  --type RunPowerShellScript \
  --command-content '<base64-encoded-command>' \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

### Query Invocation Results

```bash
aliyun ecs describe-invocation-results \
  --biz-region-id <region-id> \
  --invoke-id <invoke-id> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

> **Note:** The `Output` field in response is Base64 encoded. Decode before analysis.

---

## ECS Commands

### Instance Query Commands

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun ecs describe-instances` | Query instance details by various filters | `aliyun ecs describe-instances --biz-region-id cn-hangzhou --instance-ids '["i-xxxxx"]' --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun ecs describe-instance-attribute` | Query detailed attributes of a single instance | `aliyun ecs describe-instance-attribute --biz-region-id cn-hangzhou --instance-id i-xxxxx --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun ecs describe-instance-status` | Query runtime status of instances | `aliyun ecs describe-instance-status --biz-region-id cn-hangzhou --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun ecs describe-instances-full-status` | Query full status including scheduled events | `aliyun ecs describe-instances-full-status --biz-region-id cn-hangzhou --instance-id.1 i-xxxxx --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |

### System Event Commands

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun ecs describe-instance-history-events` | Query historical and active system events | `aliyun ecs describe-instance-history-events --biz-region-id cn-hangzhou --instance-id i-xxxxx --instance-event-cycle-status.1 Executing --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |

### Security Group Commands

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun ecs describe-security-group-attribute` | Query security group rules | `aliyun ecs describe-security-group-attribute --biz-region-id cn-hangzhou --security-group-id sg-xxxxx --direction ingress --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun ecs describe-security-groups` | List all security groups | `aliyun ecs describe-security-groups --biz-region-id cn-hangzhou --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun ecs authorize-security-group` | Add ingress rule to security group | See detailed example below |
| `aliyun ecs revoke-security-group` | Remove ingress rule from security group | See detailed example below |

#### Security Group Rule Operations

**Add ingress rule (allow SSH from specific IP):**
```bash
aliyun ecs authorize-security-group \
  --biz-region-id cn-hangzhou \
  --security-group-id sg-xxxxx \
  --ip-protocol tcp \
  --port-range 22/22 \
  --source-cidr-ip 1.2.3.4/32 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**Add ingress rule (allow HTTP from anywhere):**
```bash
aliyun ecs authorize-security-group \
  --biz-region-id cn-hangzhou \
  --security-group-id sg-xxxxx \
  --ip-protocol tcp \
  --port-range 80/80 \
  --source-cidr-ip 0.0.0.0/0 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**Remove ingress rule (MUST specify all matching parameters):**
```bash
aliyun ecs revoke-security-group \
  --biz-region-id cn-hangzhou \
  --security-group-id sg-xxxxx \
  --ip-protocol tcp \
  --port-range 22/22 \
  --source-cidr-ip 0.0.0.0/0 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

> **Important:** When revoking a security group rule, you MUST specify `--ip-protocol`, `--port-range`, and `--source-cidr-ip` (or `--source-group-id`). Using `--security-group-rule-id` alone will fail.

### Cloud Assistant Commands

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun ecs run-command` | Execute command on instance via Cloud Assistant | `aliyun ecs run-command --biz-region-id cn-hangzhou --instance-id.1 i-xxxxx --type RunShellScript --command-content "dXB0aW1l" --timeout 60 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun ecs describe-invocation-results` | Query command execution results | `aliyun ecs describe-invocation-results --biz-region-id cn-hangzhou --invoke-id t-xxxxx --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun ecs describe-invocations` | Query command invocation records | `aliyun ecs describe-invocations --biz-region-id cn-hangzhou --instance-id i-xxxxx --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |

## VPC Commands

### VPC Query Commands

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun vpc describe-vpcs` | Query VPC details | `aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --vpc-id vpc-xxxxx --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun vpc describe-vswitch-attributes` | Query VSwitch attributes | `aliyun vpc describe-vswitch-attributes --biz-region-id cn-hangzhou --vswitch-id vsw-xxxxx --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |

### EIP Commands

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun vpc describe-eip-addresses` | Query Elastic IP addresses | `aliyun vpc describe-eip-addresses --biz-region-id cn-hangzhou --associated-instance-id i-xxxxx --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |

## Cloud Monitor (CMS) Commands

### Monitoring Metrics Commands

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun cms describe-metric-last` | Query the latest monitoring data point | `aliyun cms describe-metric-last --biz-region-id cn-hangzhou --namespace acs_ecs_dashboard --metric-name CPUUtilization --dimensions '[{"instanceId":"i-xxxxx"}]' --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun cms describe-metric-list` | Query monitoring data within a time range | `aliyun cms describe-metric-list --biz-region-id cn-hangzhou --namespace acs_ecs_dashboard --metric-name CPUUtilization --dimensions '[{"instanceId":"i-xxxxx"}]' --start-time 1640000000000 --end-time 1640086400000 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |

### Common Monitoring Metrics

| Metric Name | Namespace | Description | Dimensions |
|-------------|-----------|-------------|------------|
| `CPUUtilization` | `acs_ecs_dashboard` | CPU utilization (%) | `{"instanceId":"i-xxxxx"}` |
| `memory_usedutilization` | `acs_ecs_dashboard` | Memory utilization (%) | `{"instanceId":"i-xxxxx"}` |
| `diskusage_utilization` | `acs_ecs_dashboard` | Disk utilization (%) | `{"instanceId":"i-xxxxx","device":"/dev/vda1"}` |
| `disk_readiops` | `acs_ecs_dashboard` | Disk read IOPS | `{"instanceId":"i-xxxxx","device":"/dev/vda"}` |
| `disk_writeiops` | `acs_ecs_dashboard` | Disk write IOPS | `{"instanceId":"i-xxxxx","device":"/dev/vda"}` |
| `InternetInRate` | `acs_ecs_dashboard` | Inbound network bandwidth (bits/s) | `{"instanceId":"i-xxxxx"}` |
| `InternetOutRate` | `acs_ecs_dashboard` | Outbound network bandwidth (bits/s) | `{"instanceId":"i-xxxxx"}` |
| `IntranetInRate` | `acs_ecs_dashboard` | Inbound private network bandwidth (bits/s) | `{"instanceId":"i-xxxxx"}` |
| `IntranetOutRate` | `acs_ecs_dashboard` | Outbound private network bandwidth (bits/s) | `{"instanceId":"i-xxxxx"}` |

## EBS Disk Diagnosis Commands (Disk Performance / IO Bottleneck scenario)

> The EBS diagnosis APIs **are** available through the `aliyun` CLI via the
> `aliyun-cli-ebs` plugin (auto-installed by this skill's pre-check). Use the CLI —
> the Python SDK is only a fallback. First identify or verify the disk, then create
> the report, poll it to completion, and interpret its events and recommendations.

| Command | Description | Example |
|---------|-------------|---------|
| `aliyun ebs describe-lens-monitor-disks` | List disks monitored by CloudLens for EBS | `aliyun ebs describe-lens-monitor-disks --biz-region-id cn-hangzhou --max-results 100 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun ebs create-diagnose-report` | Start a disk performance diagnosis, returns `ReportId` | `aliyun ebs create-diagnose-report --biz-region-id cn-hangzhou --diagnose-type Performance --resource-type Disk --resource-id d-xxxxx --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |
| `aliyun ebs describe-diagnose-report` | Poll diagnosis status / fetch results | `aliyun ebs describe-diagnose-report --biz-region-id cn-hangzhou --diagnose-type Performance --report-ids <report-id> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` |

**Parameter notes:**
- `--resource-type Disk` — capital `D`, exactly this casing.
- `--diagnose-type Performance` — required on `create-diagnose-report`, and also pass
  it to `describe-diagnose-report`.
- `--report-ids` / `--resource-ids` / `--disk-ids` are **list** flags:
  space-separated values (`--report-ids id1 id2`), *not* JSON arrays.
- `--start-time` / `--end-time` are optional ISO 8601 UTC (`yyyy-MM-ddTHH:mm:ssZ`);
  omit both to diagnose the last 12 hours.

## Common Command Patterns

### Query Instance by Different Identifiers

**By Instance ID:**
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxxxx","i-yyyyy"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**By Instance Name:**
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-name "my-instance" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**By Private IP:**
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --private-ip-addresses '["192.168.1.10"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**By Public IP:**
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --public-ip-addresses '["47.100.1.1"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**By VPC ID:**
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --vpc-id vpc-xxxxx \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**By Security Group ID:**
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --security-group-id sg-xxxxx \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

### Execute Cloud Assistant Commands

**Execute Shell script (Linux):**
```bash
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunShellScript \
  --command-content "$(echo 'df -h' | base64)" \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**Execute PowerShell script (Windows):**
```bash
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunPowerShellScript \
  --command-content "$(echo 'Get-Volume' | base64)" \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**Execute with parameters:**
```bash
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunShellScript \
  --command-content "$(echo 'echo {{param1}} {{param2}}' | base64)" \
  --parameters '{"param1":"value1","param2":"value2"}' \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**Execute on multiple instances:**
```bash
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --instance-id.2 i-yyyyy \
  --instance-id.3 i-zzzzz \
  --type RunShellScript \
  --command-content "$(echo 'uptime' | base64)" \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

### Query Monitoring with Time Range

**Last 15 minutes:**
```bash
aliyun cms describe-metric-list \
  --biz-region-id cn-hangzhou \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions '[{"instanceId":"i-xxxxx"}]' \
  --start-time $(date -d '15 minutes ago' +%s)000 \
  --end-time $(date +%s)000 \
  --period 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**Last 1 hour:**
```bash
aliyun cms describe-metric-list \
  --biz-region-id cn-hangzhou \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions '[{"instanceId":"i-xxxxx"}]' \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --end-time $(date +%s)000 \
  --period 300 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

## Advanced Usage

### Pagination

When results exceed page limit, use pagination:

```bash
# First page
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --page-size 50 \
  --page-number 1 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Second page
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --page-size 50 \
  --page-number 2 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

### Output Formatting

**JSON format (default):**
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**Table format:**
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]' \
  --output table \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**Extract specific fields with jq:**
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}" \
  | jq '.Instances.Instance[0].InstanceId'
```

## Troubleshooting Commands

### Check Cloud Assistant Status

```bash
# Check if Cloud Assistant is installed
aliyun ecs describe-cloud-assistant-status \
  --biz-region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# List Cloud Assistant agents
aliyun ecs describe-instance-attribute \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}" \
  | jq '.CloudAssistantStatus'
```

### Check Recent Failed Commands

```bash
aliyun ecs describe-invocations \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --invocation-status Failed \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

### View Command Output in Detail

```bash
aliyun ecs describe-invocation-results \
  --biz-region-id cn-hangzhou \
  --invoke-id t-xxxxx \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}" \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' \
  | base64 -d
```

## Reference Links

- [ECS API Reference](https://www.alibabacloud.com/help/ecs/developer-reference/api-overview)
- [VPC API Reference](https://www.alibabacloud.com/help/vpc/developer-reference/api-overview)
- [Cloud Monitor API Reference](https://www.alibabacloud.com/help/cms/developer-reference/api-overview)
- [Cloud Assistant Documentation](https://www.alibabacloud.com/help/ecs/user-guide/cloud-assistant-overview)
- [Aliyun CLI Documentation](https://www.alibabacloud.com/help/cli/what-is-alibaba-cloud-cli)
