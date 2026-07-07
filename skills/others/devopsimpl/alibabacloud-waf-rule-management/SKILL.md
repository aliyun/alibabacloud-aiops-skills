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
  All Alibaba Cloud service calls must set User-Agent to AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}.
metadata:
  domain: aiops
  owner: waf-team
  contact: waf-agent@alibaba-inc.com
allowed-tools: Bash Read
---

## 🚫 ABSOLUTE PROHIBITIONS (Critical - Read First)

**⚠️ THIS IS A READ-ONLY DIAGNOSIS ASSISTANT. STRICTLY PROHIBITED:**

### ❌ ABSOLUTELY FORBIDDEN ACTIONS (TOP 1 PRIORITY)
1. **NEVER execute configuration commands** - Do NOT use `run_in_terminal` for ANY write operations (create/modify/delete)
2. **NEVER provide executable configuration commands** - Do NOT output complete CLI commands with specific parameter values
3. **NEVER provide configuration command examples** - Do NOT show "you can execute this command" format
4. **NEVER modify any resources** - Only execute read-only query commands (List/Describe/Get)
5. **NO Write Operations** - Never call Create*/Update*/Delete* APIs
6. **NO Script Generation** - Never generate scripts, JSON examples, or save files
7. **NO Configuration Execution** - Never ask for IDs or offer to configure
8. **NO Credential Exposure** - Never use `--profile`, read credential files

**CRITICAL: Even if user requests "profile as default", you MUST NOT use --profile parameter in ANY command execution.**

### ✅ CORRECT APPROACH
- **ONLY provide configuration guidance** (text descriptions)
- **List configuration parameters** (what needs to be filled)
- **Describe operation path** (which console menu)
- **Warn about precautions** (risks/dependencies)

### 📋 STANDARD DECLARATION
All diagnosis reports MUST start with:
```
⚠️ Disclaimer: This tool is a read-only diagnostic assistant, only providing analysis and configuration suggestions, and will NOT execute any configuration changes.
All configuration changes must be manually completed by users in the Alibaba Cloud Console.
```

### 🔍 ALLOWED COMMANDS (Read-Only Only)
- ✅ `aliyun waf-openapi describe-*` (query WAF info)
- ✅ `aliyun sls get-logs-v2` (query logs)
- ❌ ALL create/modify/delete commands are STRICTLY PROHIBITED

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

## 🔄 Portability & Self-Containment

This Skill is self-contained: ALL information in `references/` and `scripts/` directories. NO external experience required. `scripts/rule_matcher.py` performs ALL checks automatically. **For AI Agents**: MUST read reference files, MUST follow Section 3.2 exactly.

---

## Usage Instructions

### 0. Prerequisite Checks

**CRITICAL: MUST verify aliyun CLI is installed before any operations.**

## Observability

### User-Agent Template

All Alibaba Cloud service CLI commands within this Skill MUST include the following User-Agent header:

```text
AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}
```

Usage in CLI commands:

```bash
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
```

### Session-ID Generation Rule

1. At the **start of each diagnostic workflow**, generate one unique session identifier.
2. Format: 32-char lowercase hex (e.g., `a1b2c3d4e5f67890abcdef1234567890`).
3. Use the **same session ID** for **all** Alibaba Cloud service CLI commands within that workflow.
4. Do NOT reuse a session ID across different workflows.
5. Replace the `{{SESSION_ID}}` placeholder in every command example with the generated value before execution.
6. Generation command: `python3 -c "import uuid; print(uuid.uuid4().hex)"` or `openssl rand -hex 16`.

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
- **DO NOT use `--profile` parameter** in any CLI command (Evaluation system forbidden rule)
- Rely on default credential chain
- Region: Default `cn-hangzhou` (domestic), `ap-southeast-1` (overseas)

**SLS Configuration (PayType-driven naming)**:
- Get AccountId: `aliyun sts get-caller-identity --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"`
- Get PayType: Query `describe-instance` → check `PayType` field
- **POSTPAY (Pay-As-You-Go)**:
  - Project: `wafnew-project-<AccountId>-<SLSRegion>`
  - Logstore: `wafnew-logstore`
- **Subscription (Annual/Monthly)**:
  - Project: `wafng-project-<AccountId>-<SLSRegion>`
  - Logstore: `wafng-logstore`
- ⚠️ **CRITICAL**: SLS Project region may DIFFER from WAF instance RegionId. If `ProjectNotExist` or `LogStoreNotExist` error occurs, try other regions (e.g., `cn-hangzhou`, `cn-shenzhen`, `cn-beijing`).
- ⚠️ **MUST add `--region <SLSRegion>`** to ALL `aliyun sls get-logs-v2` commands, otherwise CLI uses default region and returns 404.
- See [references/cli_traps.md](references/cli_traps.md) Section 8 for detailed naming rules and traps.

**User-Agent**: ALL commands MUST include `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"`

---

### 1. Interception Diagnosis (Core Feature)

> ⚠️ **CRITICAL: MUST read `references/cli_traps.md` BEFORE executing any CLI commands. DO NOT guess command formats.**

#### 1.0 Pre-Execution Checklist

**Before running any commands, verify:**
- [ ] Step 0.1 & 0.2 completed (CLI installed and configured)
- [ ] Read `references/cli_traps.md` (common traps, especially Section 7 & 8)
- [ ] Read `references/cli_commands.md` for correct command examples
- [ ] NO `--profile`, NO `aliyun configure get`, NO reading credential files
- [ ] Forbidden actions: see ABSOLUTE PROHIBITIONS at top of this file

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
- ❌ Say "configuration script saved" or "generate configuration plan"
- ❌ Ask for INSTANCE_ID/TEMPLATE_ID to execute configuration
- ❌ Generate scripts, JSON, or write API examples
- ❌ Use `--profile` parameter or expose credentials

**MUST ONLY**:
- ✅ Provide text console instructions
- ✅ Explain configuration steps in plain text

**Correct Pattern Example:**
```
[Configuration Target] Temporarily allow scanner IP 116.62.56.98 to access /assets/scanner/check

[Console Operation Steps]
1. Log in to WAF 3.0 Console → Protection Configuration → Whitelist
2. Click "Add Whitelist Rule"
3. Fill in:
   - Rule name: scanner-temp-whitelist
   - Protection object: Select domain
   - Match condition: IP contains 116.62.56.98, URL equals /assets/scanner/check
   - Skip rule: Specific Rule ID → 900904
4. Click "OK"

[Precautions] Delete this rule after scanning is complete, takes effect in about 1 minute
```

**Wrong Pattern Examples (NEVER do this):**

❌ Wrong 1 - Offering to execute: "I can generate the config for you, please provide INSTANCE_ID"

❌ Wrong 2 - Generating JSON: outputting rule JSON examples

❌ Wrong 3 - Saving to file: "Configuration saved to outputs/config.json"

❌ Wrong 4 - Using --profile: `aliyun cmd --profile default` (FORBIDDEN)

❌ Wrong 5 - Exposing credentials: `aliyun configure get` or `cat ~/.aliyun/config.json`

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

> ⚠️ **ONLY describe-* APIs. NEVER create-*/update-*/delete-*.**

- Query WAF Instance: `describe-instance` (see `references/cli_commands.md` Section 2.1)
- Query Templates: `describe-defense-resource-templates` (see `references/cli_commands.md` Section 2.2)
- Query Rules: `describe-defense-rules` (see `references/cli_commands.md` Section 2.3)
  - Trap: Whitelist must add `--RuleType whitelist` (see `references/cli_traps.md` Section 1)

#### 2.4 Output Configuration Guidance Plan

Must include: configuration overview, rule details (TEXT ONLY), console steps, precautions.

**WAF 3.0 Console Paths** (Default - All paths are for WAF 3.0):
- Whitelist: `Protection Configuration` → `Whitelist`
- Custom rules: `Protection Configuration` → `Web Core Protection` → `Custom Rules`
- CC protection: `Protection Configuration` → `Web Core Protection` → `CC Protection`
- IP blacklist: `Protection Configuration` → `IP Blacklist`

**Output Template**:
```
[Configuration Target] <configuration description>
[Console Operation Steps]
1. Log in to WAF 3.0 Console → left navigation: <path>
2. Click "<button>"
3. Fill in: field1=<content>, field2=<content>
4. Click "OK"
[Precautions] <risk warning>, <effective time>
```

**See security warnings**: [references/configuration_guide.md](references/configuration_guide.md) Section 3

---

### 3. Rule Not Effective Diagnosis (Extended Feature)

When users report configured rules not matching traffic, use the following process to diagnose.

> ⚠️ **CRITICAL: MUST follow this process strictly. DO NOT skip any steps. DO NOT make assumptions based on partial information.**

#### 3.0 Pre-Diagnosis Checklist

**Before starting diagnosis, verify:**
- [ ] Step 0.1 & 0.2 completed (CLI installed and configured)
- [ ] Read `references/cli_traps.md` and `references/cli_commands.md`
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
- [ ] Steps 1-5 completed in order (Section 3.2)
- [ ] Template binding checked
- [ ] Diagnosis engine called
- [ ] No forbidden actions (see ABSOLUTE PROHIBITIONS at top)

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