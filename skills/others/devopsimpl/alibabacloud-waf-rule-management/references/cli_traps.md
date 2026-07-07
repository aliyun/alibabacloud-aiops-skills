# WAF CLI Traps Checklist

> This file documents common traps and error patterns in Alibaba Cloud WAF CLI calls. MUST be consulted before execution.

---

## 1. DescribeDefenseRules Whitelist Scenario MUST Specify RuleType

**API**: `DescribeDefenseRules`

### Error Pattern

```bash
# ❌ WRONG: Query whitelist rules without specifying RuleType
aliyun waf-openapi describe-defense-rules \
  --InstanceId '<instance_id>' \
  --Query '{"templateId":<template_id>}'
# Result: Returns 0 records
```

### Correct Usage

```bash
# ✅ CORRECT: MUST add --RuleType whitelist for whitelist scenarios
aliyun waf-openapi describe-defense-rules \
  --InstanceId '<instance_id>' \
  --Query '{"templateId":<template_id>}' \
  --RuleType 'whitelist'
```

### Root Cause

WAF API has special handling for whitelist DefenseScene. If `--RuleType whitelist` is not explicitly specified, the API filters out whitelist rules.

### Checklist

Before querying rules, confirm:
- [ ] If querying whitelist rules, MUST add `--RuleType whitelist`
- [ ] Other DefenseScenes also need corresponding RuleType specified

---

## 2. SLS Query Field Truncation Issue

**API**: `aliyun sls get-logs-v2`

### Error Pattern

```bash
# ❌ WRONG: Without specifying select, log fields may be truncated
aliyun sls get-logs-v2 \
  --project "<project>" --logstore "wafnew-logstore" \
  --from "<timestamp>" --to "<timestamp>" \
  --query "request_traceid: <traceid>"
# Result: Key fields like matched_host, real_client_ip may be missing
```

### Correct Usage

```bash
# ✅ CORRECT: Use select to explicitly specify required fields
aliyun sls get-logs-v2 \
  --project "<project>" --logstore "wafnew-logstore" \
  --from "<timestamp>" --to "<timestamp>" \
  --query "* | select request_traceid, matched_host, host, real_client_ip, request_path, request_method, status, final_plugin, final_rule_id, waf_rule_type, waf_action" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
```

---

## 3. WAF 3.0 Console Path Errors

**CRITICAL**: WAF 3.0 and WAF 2.0 console paths are COMPLETELY different.

### Error Pattern

```
❌ WRONG (WAF 2.0 path):
- Security Operations → Website Configuration
- Protection Configuration → CC Security Protection
```

### Correct Usage

```
✅ CORRECT (WAF 3.0 path):
- CC Protection: Protection Configuration → Web Core Protection → CC Protection
- Whitelist: Protection Configuration → Custom Protection → Whitelist
- Custom Rules: Protection Configuration → Custom Protection → Custom Rules
- IP Blacklist: Protection Configuration → Custom Protection → IP Blacklist
```

### Important Notes

- WAF 3.0 uses "Web Core Protection" submenu (not top-level menu)
- CC Protection requires creating protection templates first
- CC Protection strict mode is NOT suitable for API interfaces
- If user does not specify version, ALWAYS default to WAF 3.0

---

## 4. CC Protection Mode Selection

**Common Mistake**: Using strict mode for API interfaces

### Error Pattern

Using CC Protection strict mode for API rate limiting:
- Causes high false positive rate
- Intercepts legitimate API requests
- Only suitable for web pages (including H5)

### Correct Usage

**For API rate limiting**:
- Use Custom Rules instead: `Protection Configuration` → `Custom Protection` → `Custom Rules`
- Configure frequency-based rules with IP dimension
- Set appropriate thresholds (1.5-2x normal peak)

**CC Protection mode selection**:
- **Normal Mode**: Daily use, low false positive rate
- **Strict Mode**: Only for web pages under CC attack, NEVER for APIs

---

## 5. Rule Naming Convention Violations

### Error Pattern

```
❌ WRONG (contains spaces):
- "rate limit api login"
- "whitelist scan test"
```

### Correct Usage

```
✅ CORRECT (use underscores or hyphens):
- rate_limit_api_login
- whitelist-scan-test
- cc_protection_api
```

### Rule

All rule names and protection template names MUST NOT contain spaces.

---

## 6. SLS CLI Missing User-Agent

### Error Pattern

```bash
# ❌ WRONG: Missing User-Agent parameter
aliyun sls get-logs-v2 \
  --project "<project>" --logstore "wafnew-logstore" \
  --from "<timestamp>" --to "<timestamp>" \
  --query "*"
```

### Correct Usage

```bash
# ✅ CORRECT: ALL Alibaba Cloud CLI commands MUST include User-Agent
aliyun waf-openapi describe-instance \
  --version 2021-10-01 --force --region cn-hangzhou \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
```

---

## 7. SLS CLI Command Format Traps (aliyun sls get-logs-v2)

**Important**: The `aliyun sls get-logs-v2` command has several common traps; the correct format must be strictly followed.

### 7.1 Credential Parameter Errors

```bash
# ❌ WRONG: Using --profile parameter (not supported, forbidden)
aliyun sls get-logs-v2 ... --profile default

# ✅ CORRECT: Rely on default credential chain, NO --profile
aliyun sls get-logs-v2 \
  --project "<project>" --logstore "<logstore>" \
  --from "<timestamp>" --to "<timestamp>" \
  --query "<query>" \
  --line 10 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
```

**Important Notes**:
- `aliyun sls get-logs-v2` does NOT support `--profile` parameter
- Credentials rely on the default credential chain (`~/.aliyun/config.json`)
- If user has not configured, guide user to run: `aliyun configure`

### 7.2 Query Syntax Format

```bash
# ❌ WRONG: Using pure SQL format
--query="* | select field1, field2 where request_traceid = 'xxx'"

# ✅ CORRECT: Use SLS query syntax (filter first, then process)
--query="request_traceid:xxx | select field1, field2 limit 1"
```

### 7.3 Complete Correct Example

```bash
# ✅ Complete correct command format
aliyun sls get-logs-v2 \
  --project "wafnew-project-1882089769163987-cn-hangzhou" \
  --logstore "wafnew-logstore" \
  --from "$(( $(date +%s) - 604800 ))" \
  --to "$(date +%s)" \
  --query "request_traceid:2f6f0cbc17759652456034145eef13 | select matched_host, host, real_client_ip, request_path, request_method, status, final_plugin, final_rule_id, waf_rule_type, waf_action limit 1" \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
```

### 7.4 Common Error Troubleshooting

| Error Message | Cause | Solution |
|---------|------|---------|
| `Invalid parameters` | Used `--profile` or unsupported parameters | Remove `--profile`, rely on default credential chain |
| `Column 'xxx' cannot be resolved` | Query uses non-existent field | Remove the field or use `select` to specify valid fields |
| Query returns empty | Time range mismatch or wrong Region | Confirm time range and Region (domestic `cn-hangzhou`, overseas `ap-southeast-1`) |
| `AccessDenied` | AK/SK lacks SLS permission | Check RAM permissions (see [ram-policies.md](ram-policies.md)) |

---

## 8. SLS Region & PayType Naming Trap (CRITICAL)

**API**: `aliyun sls get-logs-v2`

### Error Pattern 1: Missing --region Parameter

```bash
# ❌ WRONG: Without --region, CLI uses default region (cn-hangzhou)
# If SLS project is in cn-shenzhen, returns ProjectNotExist (404)
aliyun sls get-logs-v2 \
  --project "wafnew-project-1882089769163987-cn-shenzhen" \
  --logstore "wafnew-logstore" \
  --from "<timestamp>" --to "<timestamp>" \
  --query "request_traceid:xxx"
# Result: ProjectNotExist error
```

### Correct Usage

```bash
# ✅ CORRECT: MUST add --region matching the SLS project's region
aliyun sls get-logs-v2 \
  --project "wafnew-project-1882089769163987-cn-shenzhen" \
  --logstore "wafnew-logstore" \
  --from "<timestamp>" --to "<timestamp>" \
  --query "request_traceid:xxx" \
  --region cn-shenzhen \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
```

### Error Pattern 2: Wrong PayType Naming

```bash
# WRONG: Using wafnew-* for a Subscription (Annual/Monthly) instance
# Subscription instances use wafng-* naming
--project "wafnew-project-<AccountId>-<region>"  # Wrong for Subscription
--logstore "wafnew-logstore"                     # Wrong for Subscription
```

### PayType-Based Naming Rules

| PayType | SLS Project | Logstore |
|---------|-------------|----------|
| POSTPAY (Pay-As-You-Go) | `wafnew-project-<AccountId>-<SLSRegion>` | `wafnew-logstore` |
| Subscription (Annual/Monthly) | `wafng-project-<AccountId>-<SLSRegion>` | `wafng-logstore` |

### How to Determine Correct Parameters

1. **Get AccountId**: `aliyun sts get-caller-identity`
2. **Get PayType**: Query `describe-instance` → check `PayType` field (POSTPAY or Subscription)
3. **Determine SLSRegion**: ⚠️ SLS project region may DIFFER from WAF instance RegionId
   - Try WAF instance region first
   - If `ProjectNotExist`, try other regions: cn-hangzhou, cn-shenzhen, cn-beijing, etc.
   - Use `aliyun sls list-log-stores --project "<project>" --region <region>` to verify project existence
4. **Construct query**: Use correct Project + Logstore + `--region`

### Root Cause

- `aliyun sls get-logs-v2` defaults to the CLI's configured region (usually cn-hangzhou)
- SLS projects are region-specific resources; querying from wrong region returns 404
- WAF instance RegionId (e.g., cn-hangzhou) does NOT guarantee the SLS project is in the same region (e.g., may be cn-shenzhen)
- PayType determines the project name prefix: `wafnew-` (POSTPAY) vs `wafng-` (Subscription)

### Checklist

Before executing SLS queries:
- [ ] Checked PayType from `describe-instance` response
- [ ] Used correct project prefix (`wafnew-` for POSTPAY, `wafng-` for Subscription)
- [ ] Used correct logstore name (`wafnew-logstore` for POSTPAY, `wafng-logstore` for Subscription)
- [ ] Added `--region <SLSRegion>` to the SLS query command
- [ ] If `ProjectNotExist`, tried other regions before concluding logstore doesn't exist

---

## Quick Reference Checklist

Before executing any WAF CLI command:

- [ ] Using WAF 3.0 API version (`2021-10-01`)
- [ ] Using correct WAF 3.0 console paths (not WAF 2.0)
- [ ] Added `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"` parameter
- [ ] **NOT using `--profile` parameter** (rely on default configuration)
- [ ] **NOT running `aliyun configure get`** (exposes AK/SK)
- [ ] SLS query uses `aliyun sls get-logs-v2` (SLS plugin required)
- [ ] **Checked PayType to determine correct SLS Project/Logstore name** (wafnew-* vs wafng-*)
- [ ] **Added `--region <SLSRegion>` to SLS query commands** (SLS region may differ from WAF region)
- [ ] Rule names do not contain spaces
- [ ] Whitelist query includes `--RuleType whitelist`
- [ ] SLS query uses explicit `select` to specify key fields
- [ ] CC protection strict mode not used for API interfaces
- [ ] Output is concise (keep within 20 lines where possible)
