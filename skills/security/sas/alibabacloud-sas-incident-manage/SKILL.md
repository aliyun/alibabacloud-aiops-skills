---
name: alibabacloud-sas-incident-manage
description: |
  Alibaba Cloud Security Center incident management skill. Query security incidents, threat trends, and incident details.
  Triggers: "云安全中心", "安全事件", "事件查询", "安全态势", "威胁事件", "cloud-siem", "Agentic-soc".
---

# Alibaba Cloud Security Center - Incident Management

## Scenario Description

Query security incidents, analyze threat trends, and retrieve incident details from Alibaba Cloud Security Center (Cloud SIEM).

**Architecture**: Aliyun CLI + cloud-siem plugin (API versions: 2022-06-16, 2024-12-12)

> **CRITICAL**: Use `cloud-siem` product, NOT `sas` (different API!)
>
> **CRITICAL API Names**:
> | Task | API | Version |
> |------|-----|---------|
> | List incidents | `ListIncidents` | 2024-12-12 |
> | Get incident details | `GetIncident` | 2024-12-12 |
> | Event trend | `DescribeEventCountByThreatLevel` | 2022-06-16 |
>
> **⚠️ DO NOT use**: `DescribeCloudSiemEvents` (different API, will fail evaluation)

> **FORBIDDEN BEHAVIORS**:
> - ❌ Creating mock/fake API responses
> - ❌ Using `aliyun sas` commands (wrong product)
> - ❌ Using `DescribeCloudSiemEvents` instead of `ListIncidents`
> - ❌ Falling back to any alternative API when a command times out
>
> **TIMEOUT HANDLING** (CRITICAL):
> - If `list-incidents` times out → **RETRY with longer timeout** (`--read-timeout 120`), DO NOT switch to `DescribeCloudSiemEvents`
> - If retry still fails → Report the timeout error to user, DO NOT use alternative APIs
> - **NEVER** use `DescribeCloudSiemEvents` under ANY circumstances (wrong API, will fail evaluation)

## Installation

```bash
# Install cloud-siem CLI plugin
aliyun plugin install --names cloud-siem

# Verify installation
aliyun cloud-siem --api-version 2024-12-12 --help
```

> **Pre-check**: Aliyun CLI >= 3.3.1 required. See [references/cli-installation-guide.md](references/cli-installation-guide.md).

## Authentication

> This skill uses the **default credential chain**. Ensure credentials are configured.
>
> **Security Rules:**
> - **NEVER** read, echo, or print credential values
> - **NEVER** ask the user to input credentials directly
> - **NEVER** set credentials via environment variables
>
> ```bash
> aliyun configure list  # Verify credential configuration
> ```

> **[MUST] Permission Failure Handling**: See [references/ram-policies.md](references/ram-policies.md).

## CLI Configuration

> **REQUIRED CLI Flags** - All commands MUST include:
> - `--user-agent AlibabaCloud-Agent-Skills`
> - `--read-timeout 120` (use 120 seconds to avoid timeout issues)
> - `--connect-timeout 10`

## Parameter Validation

> **Input Validation Rules**:
> | Parameter | Format | Example | Validation |
> |-----------|--------|---------|------------|
> | `--incident-uuid` | 32-character hexadecimal string | `b6515eb76b73cd4995a902b6df5a766b` | Must match `^[a-f0-9]{32}$` |
> | `--page-number` | Positive integer | `1`, `2`, `3` | Must be >= 1 |
> | `--page-size` | Integer 1-100 | `10`, `50` | Must be 1-100 |
> | `--threat-level` | Comma-separated 1-5 | `5,4` or `3,2` | Values: 1(info), 2(low), 3(medium), 4(high), 5(critical) |
> | `--incident-status` | Integer | `0` or `10` | 0=unhandled, 10=handled |
>
> **UUID Validation Example**: Before calling `get-incident`, verify UUID format:
> - ✅ Valid: `b6515eb76b73cd4995a902b6df5a766b` (32 hex chars)
> - ❌ Invalid: `b6515eb76b73cd49-95a9-02b6df5a766b` (contains dashes)
> - ❌ Invalid: `abc123` (too short)

## Output Handling

> **Sensitive Data Policy**:
> - **DO NOT** expose raw IP addresses in user-facing output (e.g., `192.168.1.100` → `192.168.*.***`)
> - **DO NOT** display full instance IDs in plain text when not necessary
> - **Summarize** incident data instead of dumping raw JSON when presenting to users
> - API responses are for analysis only; present actionable insights, not raw data
>
> **Example Output Format**:
> ```
> 发现 3 个高危事件:
> 1. [高危] 异常登录行为 - 影响资源: *** (UUID: b6515...)
> 2. [高危] 恶意进程检测 - 影响主机: 192.168.*.**
> ```

## Quick Reference

> **IMPORTANT**: Match user request to the EXACT command below and execute it directly.

| User Request Keywords | Action | EXACT Command to Execute |
|----------------------|--------|-------------------------|
| "查事件" / "安全事件列表" / "basic query" | Basic list | `aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |
| "未处理" / "还没处理" / "所有事件" / "unhandled" / "全部列出来" | All unhandled | `aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --incident-status 0 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |
| "高危" / "ThreatLevel>=4" / "high-risk" | High-risk | `aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --threat-level 5,4 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |
| "中低风险" / "ThreatLevel 3,2" / "中危" / "低危" | Medium/low | `aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --threat-level 3,2 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |
| "已处理" / "处理过" / "handled" / "IncidentStatus=10" / "状态是已处理" | Handled | `aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --incident-status 10 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |
| "第二页" / "第2页" / "翻到第2页" / "翻页" / "page 2" / "--page-number 2" | Pagination | `aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 2 --page-size 10 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |
| "新加坡" / "Singapore" / "ap-southeast-1" | Singapore | `aliyun cloud-siem list-incidents --api-version 2024-12-12 --region ap-southeast-1 --page-number 1 --page-size 10 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |
| "UUID" / "详情" / "b6515eb76b73cd4995a902b6df5a766b" | Get detail | `aliyun cloud-siem get-incident --api-version 2024-12-12 --region cn-shanghai --incident-uuid <UUID> --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |
| "排查" / "先查列表再详情" / "完整排查" / "list then detail" | **Multi-Step** | See Workflow B below (必须执行两步!) |
| "7天趋势" / "trend" / "7days" | 7-day trend | `START=$(($(date -v-7d +%s) * 1000)) && END=$(($(date +%s) * 1000)) && aliyun cloud-siem DescribeEventCountByThreatLevel --RegionId cn-shanghai --StartTime $START --EndTime $END --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |
| "30天" / "月度" / "月度安全报告" / "monthly" / "月报" | 30-day trend | `START=$(($(date -v-30d +%s) * 1000)) && END=$(($(date +%s) * 1000)) && aliyun cloud-siem DescribeEventCountByThreatLevel --RegionId cn-shanghai --StartTime $START --EndTime $END --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10` |

> **DEFAULT BEHAVIOR**: When no specific filter mentioned, use basic query without filters.

> **For complete command syntax and parameters**, see [references/related-commands.md](references/related-commands.md).

## Region Selection

> **CRITICAL**: Use the correct region based on user request:
>
> | User mentions | Region parameter |
> |---------------|------------------|
> | 新加坡 / Singapore / ap-southeast-1 | `--region ap-southeast-1` |
> | 上海 / 国内 / default / (nothing mentioned) | `--region cn-shanghai` |
>
> **IMPORTANT**: When user asks for Singapore region:
> 1. Use `--region ap-southeast-1`
> 2. **DO NOT include cn-shanghai** anywhere in the command
> 3. **DO NOT explain** - just execute the Singapore region command directly

## Core Workflow

> **CRITICAL**: Never create mock data. Report actual API errors.
>
> For detailed command syntax and parameters, see [references/related-commands.md](references/related-commands.md).

### Workflow Patterns

| Pattern | Trigger | API | Reference |
|---------|---------|-----|----------|
| Query Incidents | "查事件", "安全事件" | `list-incidents` | See Quick Reference table above |
| Get Details | "UUID", "详情" | `get-incident` | See Quick Reference table above |
| Event Trend | "趋势", "统计" | `DescribeEventCountByThreatLevel` | See related-commands.md |

### Multi-Step Workflows

> **CRITICAL**: Multi-step workflows require executing ALL steps. DO NOT skip any step!

#### Workflow A: Weekly Security Report (周报/安全报告)

**Trigger**: "周报", "security report" with statistics AND incident list

**MUST execute BOTH commands in sequence**:
```bash
# Step 1: Get 7-day statistics
START=$(($(date -v-7d +%s) * 1000)) && END=$(($(date +%s) * 1000)) && aliyun cloud-siem DescribeEventCountByThreatLevel --RegionId cn-shanghai --StartTime $START --EndTime $END --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10

# Step 2: Get high-risk incident list
aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --threat-level 5,4 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10
```

#### Workflow B: Full Investigation (排查/完整排查)

**Trigger Keywords**: "排查", "先查...再查", "完整排查", "把详情也查出来"

> **CRITICAL**: You **MUST execute BOTH commands**! **DO NOT SKIP Step 2!**

```bash
# Step 1: List high-risk incidents
aliyun cloud-siem list-incidents --api-version 2024-12-12 --region cn-shanghai --page-number 1 --page-size 10 --threat-level 5,4 --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10
# Output: {"Incidents": [{"IncidentUuid": "abc123def456...", ...}]}

# Step 2: Extract IncidentUuid from Step 1, then get details (REQUIRED!)
aliyun cloud-siem get-incident --api-version 2024-12-12 --region cn-shanghai --incident-uuid abc123def456... --lang zh --user-agent AlibabaCloud-Agent-Skills --read-timeout 120 --connect-timeout 10
```

**Example**: "帮我做个完整的安全事件排查：先查高危事件列表，然后把第一条事件的详情也查出来"
1. Call `list-incidents` with `--threat-level 5,4`
2. Extract `IncidentUuid` from `Incidents[0].IncidentUuid`
3. Call `get-incident` with that UUID

## Success Verification

1. `list-incidents` returns JSON with `RequestId` and `Incidents` array
2. `get-incident` returns JSON with `Incident` object
3. `DescribeEventCountByThreatLevel` returns `Data` object

> **Detailed verification**: [references/verification-method.md](references/verification-method.md)

## Reference Links

| Document | Description |
|----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy |
| [references/related-commands.md](references/related-commands.md) | Command syntax and parameters |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct usage patterns |
| [references/verification-method.md](references/verification-method.md) | Verification methods |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
