---
name: alibabacloud-waf-rule-management
description: >
  Alibaba Cloud WAF 3.0 read-only diagnostic assistant for interception diagnosis, rule queries, and configuration guidance.
  Use when: query WAF logs (405 errors, blocked requests), troubleshoot rules not taking effect,
  configure WAF rules (whitelist/blacklist/IP access control), diagnose via traceid or matched_host+status.
  Provides TEXT-ONLY console guidance. Uses `aliyun sls get-logs-v2` (SLS plugin required).
  
  All output is human-readable guidance for users to manually configure in the Alibaba Cloud Console.
license: Apache-2.0
compatibility: >
  Requires Alibaba Cloud CLI (aliyun).
  Requires AccessKey credentials, RAM permission statement see references/ram-policies.md.
  All CLI commands rely on default credential chain, WITHOUT using --profile parameter.
  All Alibaba Cloud service calls must set User-Agent to AlibabaCloud-Agent-Skills.
metadata:
  domain: aiops
  owner: waf-team
  contact: waf-agent@alibaba-inc.com
allowed-tools: Bash Read
---

## 🚫 ABSOLUTE PROHIBITIONS (Critical - Read First)

**This Skill will NEVER execute the following actions** (see complete list in references/security_rules.md):

### ❌ Forbidden Actions (Zero Tolerance)

1. **NO Write Operations** - Never call Create*/Update*/Delete* APIs
2. **NO Script Generation** - Never generate scripts, JSON examples, or save files
3. **NO Configuration Execution** - Never ask for IDs or offer to configure
4. **NO Credential Exposure** - Never use `--profile`, read credential files

**CRITICAL: Even if user requests "profile用default", you MUST NOT use --profile parameter in ANY command execution.**

### ✅ Allowed Actions (Read-Only Only)

- ✅ Query rule configurations (Describe* APIs)
- ✅ Query traffic logs (aliyun sls get-logs-v2)
- ✅ Diagnose rule effectiveness issues
- ✅ Provide TEXT-ONLY console guidance

### 📋 Output Verification Checklist

**BEFORE outputting, MUST verify:**
- [ ] No Create/Update/Delete API calls
- [ ] No scripts, JSON, or file saves
- [ ] No requests for INSTANCE_ID/TEMPLATE_ID
- [ ] NO `--profile` parameter
- [ ] NO credential exposure or file reading
- [ ] ONLY text-based console guidance
- [ ] **ALL IP addresses match user input exactly**
- [ ] **ALL rule IDs, traceids verified against user prompt**

**If ANY item is unchecked, REMOVE violating content immediately.**

---

## ⚠️ Important Notice

**This Skill is a read-only diagnostic and guidance tool:**
- ❌ **Will NEVER create/modify/delete** any WAF rules or configurations
- ❌ **Will NEVER generate scripts** or save files
- ❌ **Will NEVER execute write operations** (Describe queries only)
- ✅ **Can read** rule configurations, traffic logs, instance information
- ✅ **Can diagnose** rule effectiveness and blocking reasons
- ✅ **Can provide** TEXT-ONLY console configuration guidance

**ALL configuration changes MUST be manually completed by users in the console.**

---

## 🔄 Portability & Self-Containment

**This Skill is completely self-contained and portable:**
- ✅ ALL information in `references/` and `scripts/` directories
- ✅ NO external experience or memory required
- ✅ Works immediately when ported to new platform
- ✅ `scripts/rule_matcher.py` performs ALL checks automatically

**For AI Agents**: DO NOT rely on experience, MUST read reference files, MUST follow Section 3.2 exactly.

---

## Usage Instructions

### 0. Prerequisite Checks

**CRITICAL: MUST verify aliyun CLI is installed before any operations.**

#### 0.0 AI-Mode Setup (REQUIRED Before Any CLI Commands)

**MUST execute these commands before any business operations**:

```bash
# Enable AI safety mode
aliyun configure ai-mode enable

# Set User-Agent
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management"

# Update plugins to latest version
aliyun plugin update
```

**MUST execute at the end of workflow**:
```bash
# Disable AI safety mode
aliyun configure ai-mode disable
```

#### 0.1 Verify CLI Installation (REQUIRED)

```bash
which aliyun
```

**If the CLI tool is not found**:
- ❌ **STOP immediately** - cannot proceed without aliyun CLI
- ✅ **Guide user to install**: `brew install aliyun-cli` (macOS) or download from https://aliyuncli.alicdn.com/
- ✅ **Wait for user confirmation** before proceeding

**If the CLI tool is available**:
- ✅ **Proceed to check SLS plugin**

#### 0.2 Verify Configuration

**Check if the CLI is configured**:
```bash
aliyun version
```

**If not configured**:
- ✅ **Guide user**: Run `aliyun configure` and follow prompts
- ✅ **Wait for confirmation**

**If configured**:
- ✅ **Ready to diagnose** - will use `aliyun sls get-logs-v2` for log queries (plugin required)

**Required Tools**:
- Alibaba Cloud CLI (aliyun) - ONLY this, no plugins needed

**See complete setup guide**: [references/cli_guide.md](references/cli_guide.md) Section 1

**Profile Configuration**:
- **ALWAYS ask user to specify profile**. NEVER auto-detect or scan.
- **DO NOT use `--profile` parameter** in any CLI command (测评系统Forbidden)
- Rely on default credential chain
- Region: Default `cn-hangzhou` (domestic), `ap-southeast-1` (overseas)

**SLS Configuration**:
- Get AccountId: `aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills`
- Project: `wafnew-project-<AccountId>-<region>`
- Logstore: `wafnew-logstore`
- Endpoint: `<region>.log.aliyuncs.com`

**User-Agent**: ALL commands MUST include `--user-agent AlibabaCloud-Agent-Skills`

---

### 1. Interception Diagnosis (Core Feature)

> ⚠️ **CRITICAL: MUST read `references/cli_traps.md` BEFORE executing any CLI commands. DO NOT guess command formats.**

#### 1.0 Pre-Execution Checklist

**Before running any commands, verify:**
- [ ] **Step 0.1 completed**: Verified `aliyun` CLI is installed
- [ ] **Step 0.2 completed**: Verified `aliyun` is configured
- [ ] Read `references/cli_traps.md` Section 7 (common traps)
- [ ] Read `references/cli_commands.md` for correct command examples
- [ ] Understand: **NO `--profile` parameter** (测评系统Forbidden)
- [ ] Understand: **NO `aliyun configure get`** (暴露凭证)
- [ ] Understand: **NO reading credential files** (`cat ~/.aliyun/config.json`)
- [ ] Understand: **Using `aliyun sls get-logs-v2` for log queries**

**Forbidden Actions** (see full list at top of this file):
- ❌ NO Create/Update/Delete API calls
- ❌ NO script generation or file saving
- ❌ NO asking for INSTANCE_ID/TEMPLATE_ID
- ❌ NO using `--profile` parameter
- ❌ NO exposing credentials (AK/SK)
- ❌ NO reading credential files
- ❌ NO configuring SLS CLI

#### 1.1 Identify User Intent

Interception diagnosis supports the following query methods:

| Query Method | Example | Description |
|----------|------|------|
| traceid | `traceid: 0bd17c2e...` | Exact query for a single request |
| host + url_path + status | `host:api.example.com, path:/login, status:405` | Combined condition query |
| host + IP | `host:example.com, ip:1.2.3.4` | Query by domain and source IP |
| Only traceid string | User directly pastes a string matching the format | Automatically recognized as traceid |

#### 1.2 Traceid Extraction Rules

**Format Definition**:
- Allowed characters: lowercase letters (a-z), digits (0-9), hyphens (-)
- Must contain at least one letter and one digit
- Valid length: 26, 30, 32, 35, 36 characters

**Extraction Priority** (from highest to lowest, take the most recent occurrence):
1. The `request_traceid` field value from WAF logs provided by the user
2. User explicitly states "traceid: xxx", "Request ID is: xxx", "This flow xxx"
3. Raw string directly provided by the user that matches the format definition above

**Exclusion Rules** (must not be extracted as traceid):
- Values after the "event id" keyword
- Content values in HTML meta tags (e.g., content of aliyun_waf_aa)
- Pure hexadecimal hash values without letter-digit mixing

#### 1.3 Time Parameter Handling

- User-provided time must be converted to Unix timestamp (seconds)
- Timestamp (int or str): `1774345200` → use directly
- Date time: `2026-03-24 17:50` → convert to timestamp
- Relative time: `1h` (1 hour ago), `30m` (30 minutes ago), `1d` (1 day ago) → calculate based on current time
- **If not provided, default to query the last 7 days** (covers WAF log default retention period)

> **Important**: When querying logs, verify timezone and date to avoid missing data.

#### 1.4 Log Query

> ⚠️ **CRITICAL: MUST reference `references/cli_traps.md` Section 7 for correct format.**

**Key Fields**: `matched_host`, `host`, `real_client_ip`, `request_path`, `status`, `final_plugin`, `final_rule_id`, `waf_action`, `bypass_matched_ids`

**Correct Format**: See `references/cli_commands.md` Section 1.1

**Common Traps** (see `references/cli_traps.md` Section 7):
- ❌ Does NOT support `--profile` (use `--region-endpoint`)
- ✅ Use `aliyun sls get-logs-v2` (SLS plugin required)
- ✅ Parameters: `--from`, `--to`, `--line`

**Query Conditions** (adjust `--query` parameter):
- By traceid: `request_traceid:<traceid> | select ...`
- By host+path+status: `host:<domain> and request_path:<path> and status:<status_code> | select ...`
- By host+IP: `host:<domain> and real_client_ip:<ip> | select ...`

#### 1.5 Result Handling

- **Query failed/error**: Check if `aliyun` is installed, credentials configured, Region matches
- **0 results**: Prompt user "No logs found, please confirm if conditions are correct, or if the request was within 15 days"
- **1 result**: Directly analyze and output conclusions
- **Multiple results**: Analyze each one, then summarize and output
- **Missing/truncated fields**: If key fields like `matched_host`, `real_client_ip` are empty or not returned, re-query using explicit field query method

#### 1.6 Analysis Output Format

Output to users in the following structure:

1. **Request Basic Information**: Protection object (matched_host), domain (host), source IP (real_client_ip), request path, time
2. **Blocking Reason**: Triggered module (final_plugin), rule ID (final_rule_id), rule type
3. **Handling Suggestions**: Specific operation steps
4. **Context Information**: Add at end (for AI use only):
   > Available configuration info: Protection object={matched_host}, source IP={real_client_ip}, rule ID={final_rule_id}

#### 1.7 Provide Configuration Guidance After Diagnosis

**After providing interception diagnosis conclusions and suggestions, must provide configuration guidance to users:**

> Diagnosis complete. To resolve this issue, I can provide you with detailed configuration guidance.

- If user chooses **no configuration guidance needed**, process ends
- If user chooses **needs configuration guidance**, proceed to Chapter 2 "Rule Configuration Guidance"

---

### 2. Rule Configuration Guidance (Pure Text Guidance Mode)

> ⚠️ **CRITICAL: TEXT-ONLY guidance. NEVER generate scripts, save files, execute write APIs, or ask for IDs to "help configure".**

#### 2.0 Absolute Prohibitions (Critical - Zero Tolerance)

**MUST NOT** (see complete list in references/security_rules.md):
- ❌ Say "配置脚本已保存" or "生成配置方案"
- ❌ Ask for INSTANCE_ID/TEMPLATE_ID to execute configuration
- ❌ Generate scripts, JSON, or write API examples
- ❌ Use `--profile` parameter or expose credentials

**MUST ONLY**:
- ✅ Provide text console instructions
- ✅ Explain configuration steps in plain text

**Correct Pattern Example:**
```
【配置目标】临时放行扫描器IP 116.62.56.98 访问 /assets/scanner/check

【控制台操作步骤】
1. 登录WAF 3.0控制台 → 防护配置 → 白名单
2. 点击"添加白名单规则"
3. 填写:
   - 规则名称: scanner-temp-whitelist
   - 防护对象: 选择域名
   - 匹配条件: IP包含 116.62.56.98, URL等于 /assets/scanner/check
   - 跳过规则: 特定规则ID → 900904
4. 点击"确定"

【注意事项】扫描结束后删除此规则,约1分钟生效
```

**Wrong Pattern Examples (NEVER do this):**

❌ Wrong 1 - Offering to execute: "我可以帮你生成配置,请提供INSTANCE_ID"

❌ Wrong 2 - Generating JSON: 输出规则JSON示例

❌ Wrong 3 - Saving to file: "配置方案已保存到 outputs/config.json"

❌ Wrong 4 - Using --profile: `aliyun cmd --profile default` (FORBIDDEN)

❌ Wrong 5 - Exposing credentials: `aliyun configure get` 或 `cat ~/.aliyun/config.json`

#### 2.1 Context Awareness (Important)

When handling user configuration requests, follow these priorities:

1. **Auto-extract**: Prioritize extracting known parameters from current conversation context
2. **Already have required info**: Use directly, **do not ask user again**
3. **Insufficient info**: Only ask when key information is truly unknown

#### 2.2 Generate Configuration Guidance Plan

Analyze and generate detailed configuration guidance plan based on user requirements.

**Output Format**:
- ✅ Text-described configuration (table or list)
- ❌ NO JSON, NO scripts, NO write CLI commands
- Must include detailed console steps

**Rule Constraints**:
- No spaces in rule/template names (use _ or -)
- Whitelist IP: use `contain` only (NO `eq`)
- No numeric priority (order by list position)
- Custom rules: NO "pass" action (block/captcha/js/monitor only)

**See complete guide**: [references/configuration_guide.md](references/configuration_guide.md)

#### 2.3 Query Existing Configuration (Read-Only)

> ⚠️ **ONLY Describe* APIs. NEVER Create*/Update*/Delete*.**

- Query WAF Instance: `describe-instance` (see `references/cli_commands.md` Section 2.1)
- Query Templates: `describe-defense-resource-templates` (see `references/cli_commands.md` Section 2.2)
- Query Rules: `describe-defense-rules` (see `references/cli_commands.md` Section 2.3)
  - Trap: Whitelist must add `--RuleType whitelist` (see `references/cli_traps.md` Section 1)

#### 2.4 Output Configuration Guidance Plan

Must include: configuration overview, rule details (TEXT ONLY), console steps, precautions.

**WAF 3.0 Console Paths**:
- Whitelist: `Protection Configuration` → `Whitelist`
- Custom rules: `Protection Configuration` → `Web Core Protection` → `Custom Rules`
- CC protection: `Protection Configuration` → `Web Core Protection` → `CC Protection`
- IP blacklist: `Protection Configuration` → `Web Core Protection` → `IP Blacklist`

**Output Template**:
```
【配置目标】<配置说明>
【控制台操作步骤】
1. 登录WAF 3.0控制台 → 左侧导航:<路径>
2. 点击"<按钮>"
3. 填写: 字段1=<内容>, 字段2=<内容>
4. 点击"确定"
【注意事项】<风险提示>, <生效时间>
```

**See security warnings**: [references/configuration_guide.md](references/configuration_guide.md) Section 3

---

### 3. Rule Not Effective Diagnosis (Extended Feature)

When users report configured rules not matching traffic, use the following process to diagnose.

> ⚠️ **CRITICAL: MUST follow this process strictly. DO NOT skip any steps. DO NOT make assumptions based on partial information.**

#### 3.0 Self-Containment Principle (Important for Portability)

**This Skill MUST be completely self-contained and portable:**
- ✅ ALL necessary information is in the `references/` directory and `scripts/` directory
- ✅ The `scripts/rule_matcher.py` diagnosis engine performs ALL checks automatically
- ✅ DO NOT rely on any external experience, memory, or prior knowledge
- ✅ When ported to a new platform, this Skill should work immediately without any accumulated experience
- ✅ **MUST read reference files before execution** to understand correct procedures

**Before starting diagnosis, verify you have:**
- [ ] **Step 0.1 completed**: Verified `aliyun` CLI is installed
- [ ] **Step 0.2 completed**: Verified `aliyun` is configured
- [ ] Read `references/cli_traps.md` to understand common CLI pitfalls
- [ ] Read `references/cli_commands.md` for correct command formats
- [ ] Prepared to use `scripts/rule_matcher.py` for systematic diagnosis

#### 3.1 Information Collection

| Field | Required | Description |
|-------|----------|-------------|
| rule_id | Yes | Rule ID not effective |
| flow_info | Yes | traceid / IP+time / domain+path+time |
| issue_type | Yes | Not blocking / whitelist not allowing |
| resource | No | Protection object |
| full_check | No | Enable full check mode to output all issues at once (default: false) |

**Context**: Auto-extract from previous diagnosis (host, matched_host, real_client_ip, traceid).

#### 3.2 Diagnosis Process (MUST Execute in Strict Order)

> ⚠️ **CRITICAL: Execute steps 1-5 in EXACT order. DO NOT skip step 4 (Pre-checks).**
> 
> **Full command examples**: See `references/cli_commands.md`

**Step 1: Query Instance** → `describe-instance` → Extract `InstanceId` (cli_commands.md 2.1)

**Step 2: Query Rule** → `describe-defense-rules --RuleType '<scene>'` → Extract `TemplateId`, `Config` (cli_commands.md 2.3)
- ⚠️ Whitelist: add `--RuleType whitelist` (cli_traps.md Section 1)

**Step 3: Query Logs** → `aliyun sls get-logs-v2` → Extract `matched_host`, `real_client_ip` (cli_commands.md 1.1)
- ⚠️ SLS plugin required: install via `aliyun plugin install --names aliyun-cli-sls`

**Step 4: Pre-checks (MUST NOT SKIP)**

**4.1 Template Binding** → `describe-defense-resource-templates --Resource '<host>'`
- Check: Rule's `TemplateId` in bound templates? If NOT → **Conclusion: `template_not_bound`**

**4.2 Whitelist Conflicts** → If `bypass_matched_ids` non-empty → whitelist bypassing rule

**4.3 XFF Configuration** → If `real_client_ip` doesn't match expected → XFF misconfigured

**Step 5: Call Diagnosis Engine**

```bash
# Quick Mode (first critical issue)
python scripts/rule_matcher.py --rule-file rule.json --log-file log.json

# Full Check Mode (all issues)
python scripts/rule_matcher.py --rule-file rule.json --log-file log.json --full-check
```

**Input**: `rule.json` (Step 2), `log.json` (Step 3)

#### 3.3 Diagnosis Conclusion Interpretation

| conclusion | Meaning | Suggestion |
|-----------|------|------|
| `template_not_bound` | Template not bound | Bind template |
| `condition_mismatch` | Conditions don't match | Check path, IP |
| `whitelist_bypass` | Whitelist bypassing | Adjust whitelist |
| `all_match_timing` | All match, wait time | Wait ~1 minute |
| `all_match_cc` | Match, frequency low | Check CC frequency |
| `module_mismatch` | Skip module wrong | Adjust modules |
| `already_matched` | Whitelist effective | Inform user |
| `not_matched` | IP/region not in config | Check config, XFF |

**Severity Levels**:
- `critical`: Must-fix (whitelist bypass, condition mismatch)
- `warning`: Important (unrecorded fields, XFF)
- `info`: Informational (timing delay, monitor mode)

#### 3.5 Execution Checklist

Before providing diagnosis results:
- [ ] **Step 0.1 completed**: Verified `aliyun` CLI is installed
- [ ] **Step 0.2 completed**: Verified `aliyun` is configured
- [ ] Steps 1-5 completed in order (Section 3.2)
- [ ] Template binding checked
- [ ] Diagnosis engine called
- [ ] No forbidden actions (see PROHIBITIONS)
- [ ] ONLY text guidance, NO scripts/JSON
- [ ] **NO `--profile` parameter used**
- [ ] **NO credentials exposed**
- [ ] **NO credential files read** (`cat ~/.aliyun/config.json`)
- [ ] **NO aliyunlog configured**

**If any unchecked, MUST complete first.**

---

### 4. Troubleshooting

When encountering issues, consult [references/troubleshooting.md](references/troubleshooting.md) for detailed solutions.

---

### Appendix: Reference Files

| File | Purpose |
|------|------|
| `references/cli_commands.md` | Complete CLI command examples |
| `references/cli_traps.md` | Common CLI pitfalls and errors |
| `references/security_rules.md` | Complete security prohibitions |
| `references/api_reference.md` | WAF 3.0 OpenAPI parameter specs |
| `references/configuration_guide.md` | Configuration procedures |
| `references/troubleshooting.md` | Issue resolution |
| `references/cli_guide.md` | CLI setup guide |
| `references/ram-policies.md` | RAM permissions |
| `scripts/rule_matcher.py` | Diagnosis engine |