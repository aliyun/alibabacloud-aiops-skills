---
name: alibabacloud-cfw-acl-diagnosis
description: >
  Alibaba Cloud Cloud Firewall ACL rule read-only diagnostic assistant.
  
  **Trigger Scenarios**: Diagnose ACL rules not taking effect, troubleshoot Internet/NAT/VPC firewall traffic issues, query traffic logs, check matched rules, get configuration guidance (console manual operation).
  
  **Supported firewall types**: Internet Firewall, NAT Boundary Firewall, VPC Boundary Firewall
  
  **Keywords**: Cloud Firewall rules not taking effect, Internet Firewall ACL diagnosis, NAT Firewall policy not working, VPC Boundary Firewall rule diagnosis, firewall rule diagnosis
  
  ⚠️ **DO NOT use** for WAF issues - use alibabacloud-waf-rule-management skill instead.
  
  TEXT-ONLY console guidance. Queries and diagnosis only, no configuration changes.
license: Apache-2.0
compatibility: >
  Requires Alibaba Cloud CLI (aliyun-cli >= 3.3.0) and aliyun-cli-cloudfw plugin.
  Requires AccessKey credentials, RAM permission see references/ram-policies.md.
  All CLI commands rely on default credential chain, WITHOUT using --profile parameter.
  All Alibaba Cloud service calls must set User-Agent to AlibabaCloud-Agent-Skills.
metadata:
  domain: aiops
  owner: cloudfw-team
  contact: cloudfw-agent@alibaba-inc.com
allowed-tools: Bash Read
---

# Cloud Firewall ACL Rule Diagnosis (Read-Only)

## ⚠️ READ-ONLY CONSTRAINT (HIGHEST PRIORITY)

**STRICTLY PROHIBITED throughout entire workflow:**
- ❌ NEVER execute Create/Update/Delete API calls or write CLI commands
- ❌ NEVER provide executable configuration commands with specific parameter values
- ❌ NEVER use `--profile` parameter in any CLI command
- ❌ NEVER run `aliyun configure get` or `aliyun configure list`
- ❌ NEVER fabricate CLI output — use only real API responses
- ❌ Do NOT output diagnosis report unless at least one CLI query has succeeded
- ❌ Do NOT reference any memory, experience, or external knowledge — ONLY this SKILL.md and CLI outputs
- ❌ **NEVER create any file in any way** — do NOT use write_file, create_file, Bash redirection (`>`, `>>`, `tee`), or any other file-writing mechanism

**【强制拦截】Pre-output Self-Check (MANDATORY before generating ANY reply):**
> Before writing any response, internally verify: Have I called write_file, create_file, or any Bash redirection? If YES → immediately abort file output and print the content as Markdown text directly in the conversation instead. Violation of this rule causes immediate task failure.

**All diagnosis reports MUST start with:**
```
⚠️ 声明：本工具为只读诊断助手，仅提供分析和配置建议，不会执行任何配置变更操作。
```

**Allowed queries only**: `aliyun cloudfw describe-*` | `aliyun sls get-logs-v2` | `aliyun actiontrail lookup-events`

See `references/security_rules.md` for complete prohibitions list.

---

## Trigger & Service Identification

### Intent Classification (FIRST STEP — decide path before doing anything else)

| User Intent | Keywords | Action |
|------------|----------|--------|
| **Configuration Query** | 「如何配置」/「怎么设置」/「配置流程」/「规则怎么写」/「配置步骤」 | → **CONFIG PATH**: Read `references/configuration_guide.md`, output steps directly in conversation. **NO CLI commands, NO firewall queries.** |
| **Diagnosis / Troubleshooting** | 「不生效」/「没效果」/「被拦截」/「HitTimes=0」/「流量日志」/「排查」 | → **DIAGNOSIS PATH**: IMMEDIATELY start Step 0 with information already provided. DO NOT wait for more input. |
| 「安全组」/「Security Group」 | — | NOT this skill (use aliyun ecs commands) |
| 「防火墙」without qualifier | — | ASK: Cloud Firewall or Security Group? |

**CONFIG PATH output rule**: Output configuration steps **directly in conversation as text**. Reference `references/configuration_guide.md` for content. Do NOT run any CLI commands.

---

## Setup

### Step 0.0: AI-Mode (REQUIRED Before Any CLI Commands)

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis"
aliyun plugin update
```

**At workflow end**: `aliyun configure ai-mode disable`

### Prerequisites Check

```bash
which aliyun && aliyun version
aliyun plugin list  # Confirm aliyun-cli-cloudfw installed
```

**Install plugin if missing**: `aliyun plugin install cloudfw`  
**Credentials**: `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` env vars. See `references/ram-policies.md`.  
**Region**: Always use `cn-hangzhou` (Cloud Firewall is a global service, do NOT ask user for region).

---

## Firewall Type Identification

| Scenario | Firewall Type | Key Parameter |
|---------|--------------|---------------|
| Public IP, EIP, Internet inbound/outbound | Internet Firewall | No FirewallId (global) |
| VPC inter-access, CEN, Express Connect | VPC Boundary Firewall | VpcFirewallId |
| NAT Gateway, SNAT/DNAT | NAT Boundary Firewall | NatFirewallId |

**Key differences**:
- **Internet FW**: `--Direction <in|out>` required; asset-level `EngineMode` (`strict`/`loose`)
- **NAT FW**: no `Direction`; firewall-level `StrictMode` (`0`=loose, `1`=strict); supports domain rules
- **VPC FW**: no `Direction`; no strict mode; no domain rules (Layer 4 only)

**Protected asset identification**:
- Inbound (`in`) → Protected asset = **Destination**
- Outbound (`out`) → Protected asset = **Source** (public IP, not internal CIDR)

---

## Diagnosis Flow (MANDATORY ORDER)

**Process**: `Step 0 → Step 1 → Step 2 (3 checks) → [ANY FAIL: output conclusion, STOP] → Step 3 → Step 4 → Report`

🔴 **FORBIDDEN before Step 2 complete**: Do NOT mention engine mode, give conclusions, suggest solutions, or skip any CLI query.

---

### Step 0: Identify Protected Asset

Extract from user message — **do NOT re-ask what user already provided**:
- Firewall type, direction (in/out), target IP/domain
- Apply protected asset logic above

---

### Step 1: Query Rules (MUST execute CLI — NO fabrication)

| Firewall | Command |
|----------|---------|
| Internet | `aliyun cloudfw describe-control-policy --Direction <in\|out> --CurrentPage 1 --PageSize 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis` |
| NAT | `aliyun cloudfw describe-nat-firewall-control-policy --NatFirewallId <ID> --CurrentPage 1 --PageSize 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis` |
| VPC | `aliyun cloudfw describe-vpc-firewall-control-policy --VpcFirewallId <ID> --CurrentPage 1 --PageSize 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis` |

Record: `Source`, `Destination`, `DestinationType`, `AclAction`, `Order`, `Release`.

**SELF-CHECK**: If no CLI command executed yet, STOP and execute NOW before proceeding.

---

### Step 2: Pre-checks (ALL 3 in order — NO skipping, NO guessing)

**Check 2.1: Asset/Firewall Status**
- Internet FW: `aliyun cloudfw describe-asset-list --CurrentPage 1 --PageSize 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis`
  - `ProtectStatus=open` ✅ | other values ❌ (most common cause of rules not working)
  - Record `EngineMode`: `strict` / `loose`
- NAT FW: `aliyun cloudfw describe-nat-firewall-list --PageNo 1 --PageSize 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis`
  - Check firewall exists and status normal; record `StrictMode`: `0`=loose / `1`=strict
- VPC FW: `aliyun cloudfw describe-vpc-firewall-list --CurrentPage 1 --PageSize 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis`
  - Check firewall exists and status normal

**Check 2.2: Policy Matches Asset**
- Source/Destination covers protected asset; direction correct
- If user's target domain ≠ rule's domain → CONFIGURATION MISMATCH — highlight explicitly

**Check 2.3: Rule Enabled**
- `Release=true` ✅ | `Release=false` ❌

---
**🔴 [强制中断节点] Step 2 Branch Gate — HARD STOP**

IF any Check result is FAIL:
1. **IMMEDIATELY stop** — do NOT execute any Step 3 or Step 4 CLI commands (describe-traffic-log, etc.)
2. **FORBIDDEN**: calling ANY further CLI commands after this point
3. **Jump directly** to Output Format section and generate the final report now
4. Continuing to Step 3/4 after a FAIL is a critical violation that causes task failure

IF all Checks PASS → proceed to Step 3.
---

**Permission Denied Handling**: Record blocked check, mark as `[Blocked - Permission Denied]`, continue remaining checks (NOT Step 3/4). List all blocked checks in final report.

---

### Step 3: Query Traffic Logs (only if Step 2 all PASS)

```bash
# Internet FW
aliyun cloudfw describe-traffic-log --FirewallType InternetFirewall --Direction <in|out> \
  --SourceCode yundun [--StartTime <unix>] [--EndTime <unix>] [--SrcIP <ip>] [--DstIP <ip>] \
  --CurrentPage 1 --PageSize 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis

# NAT FW
aliyun cloudfw describe-traffic-log --FirewallType NatFirewall --SourceCode yundun \
  [--StartTime <unix>] [--EndTime <unix>] \
  --CurrentPage 1 --PageSize 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

**Critical**: `SourceCode=yundun` required. Do NOT set `FlowType` (causes no results). `RuleResult`: **0=allow, 2=deny**.  
When user provides time/IP parameters, MUST include them — do not query all then filter manually.

---

### Step 4: Detailed Diagnosis (only if Step 2 all PASS)

**Internet FW**:
1. `EngineMode=loose` + domain rules → domain not matched → switch to strict mode
2. `strict` + domain rules → test with `curl`/`wget` NOT `telnet` (telnet can't trigger domain recognition)
3. Log `AclPreState=app_unknown` → L7 pre-match, application not yet identified

**NAT FW**:
1. `StrictMode=0` + domain rules → domain not matched (likely root cause)
2. Verify actual source IP after SNAT; same L7 rules apply as Internet FW

See `references/diagnosis.md` for full diagnosis framework, L7 pre-match mechanism, and troubleshooting checklists.

---

## Output Format

**【严格排版指令】MANDATORY — read before writing a single word of output:**
- Output MUST match the template below EXACTLY — no extra headings, no greeting, no background paragraphs
- Total output MUST NOT exceed 30 lines. If content would exceed 30 lines, apply auto-truncation:
  - 诊断结论: 1 line max
  - 预检结果 table: ≤5 rows
  - 修复建议: ≤3 bullet points
  - 验证方法: 1 line
  - Delete ALL explanatory text beyond these limits
- ❌ NEVER write output to any file — print directly in conversation as Markdown text

```markdown
⚠️ 声明：本工具为只读诊断助手，仅提供分析和配置建议，不会执行任何配置变更操作。

## 诊断结论
[一句话根因，不超过50字]

## 预检结果（Step 2）
| 检查项 | CLI 实际值 | 状态 |
|-------|-----------|------|
| ProtectStatus | [from describe-asset-list] | PASS/FAIL |
| EngineMode / StrictMode | [value] | loose/strict |
| 流量方向 | [in/out] | PASS/FAIL |
| Release | [true/false] | PASS/FAIL |
| 策略匹配 | [分析] | PASS/FAIL |

## 修复建议
[控制台操作步骤，每步一行，最多3条]

验证方法：[一行描述]
```

**Rules**:
- ❌ **NEVER write output to any file** — ALL results MUST be output **directly in conversation as text**
- Every UUID/IP/value in report MUST be copy-pasted from CLI output (no typing from memory)
- Classify findings: `[Verified]` (confirmed by CLI) / `[Unverified]` (theoretical) / `[Blocked]` (permission denied)
- If `TotalCount > PageSize`, query all pages before making "all assets" summary statements

---

## Reference Files

| File | Purpose |
|------|---------|
| `references/cli_commands.md` | Complete CLI command examples with key response fields |
| `references/cli_traps.md` | Common CLI pitfalls and error patterns |
| `references/diagnosis.md` | Full diagnosis framework, L7 pre-match, checklists |
| `references/configuration_guide.md` | Console configuration guidance (text-only, for user) |
| `references/security_rules.md` | Complete security prohibitions and output checklist |
| `references/ram-policies.md` | RAM permissions required |
| `references/cfw_acl_knowledge.md` | ACL knowledge base and FAQ |
