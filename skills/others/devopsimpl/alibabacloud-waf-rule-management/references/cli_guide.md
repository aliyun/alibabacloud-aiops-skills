# Alibaba Cloud CLI Operation Reference

> This document is the public CLI reference for WAF Rule Management Skill.

---

## 1. Credentials and Region Conventions

### SLS Log Query (SLS Plugin Required)

**Using `aliyun sls get-logs-v2` API, SLS plugin required**:

```bash
# Direct log query (SLS plugin required)
aliyun sls get-logs-v2 \
  --project "<ProjectName>" \
  --logstore "<LogStoreName>" \
  --from "<timestamp>" \
  --to "<timestamp>" \
  --query "<query>" \
  --line 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Profile Handling Rules (Critical)

**IMPORTANT: To ensure Skill portability, MUST follow these rules:**

- ❌ **DO NOT auto-detect user's profile** (Do NOT run `aliyun configure list`)
- ❌ **DO NOT assume or hardcode profile names** (e.g., `waf-diag`, `cfw-diag`)
- ❌ **DO NOT use `--profile` parameter** (Evaluation system Forbidden rule)
- ✅ **Ask user for profile name** (For understanding only, DO NOT use in commands)
- ✅ **Rely on default credential chain** (Do NOT explicitly pass any profile parameter)

**Standard Interaction Flow**:
```
Assistant: Which Alibaba Cloud CLI profile do you use? (e.g., default, waf-diag)
User: I use my-waf-profile  
Assistant: OK, I will use the default credential chain for queries (no --profile parameter)
```

### Credential Passing

**Alibaba Cloud CLI (aliyun)**:
- **Do NOT use `--profile` parameter** (Evaluation system Forbidden)
- Rely on default credential chain
- **Do NOT explicitly pass AK/SK**
- All commands MUST include `--user-agent AlibabaCloud-Agent-Skills`

### Region Defaults

| Scenario | Region | Description |
|------|--------|------|
| Domestic WAF instance | `cn-hangzhou` | Default value |
| Overseas WAF instance | `ap-southeast-1` | Singapore |

If user does not specify Region, default to `cn-hangzhou`. If query returns no results, try `ap-southeast-1`.

---

## 2. WAF CLI General Format

```bash
aliyun waf-openapi <Action> \
  --version 2021-10-01 --force \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills \
  --<ParamName> '<value>'
```

**MUST include**:
- `--version 2021-10-01` — WAF 3.0 API version
- `--force` — Skip API metadata validation (REQUIRED for WAF 3.0)
- `--user-agent AlibabaCloud-Agent-Skills` — User-Agent identifier
- **Do NOT use `--profile` parameter** — Rely on default credential chain

**Parameter Naming**: PascalCase (e.g., `--InstanceId`, `--Domain`, `--RegionId`)

**JSON Parameters**: Some parameters accept JSON values, wrap with single quotes:
```bash
--Query '{"templateId":12345}'
```

---

## 3. SLS Log Query (Using aliyun CLI)

```bash
aliyun sls get-logs-v2 \
  --project "<project_name>" \
  --logstore "<logstore_name>" \
  --from "$FROM" \
  --to "$TO" \
  --query "<query_string>" \
  --line 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Time Parameters**:
- Absolute time: Unix timestamp (seconds), e.g., `1774345200`
- Relative time: `$(( $(date +%s) - 604800 ))` (7 days ago)

**Query Syntax**: SLS query syntax, supports `and`, `or` operators

---

## 4. STS CLI Format

```bash
aliyun sts get-caller-identity \
  --user-agent AlibabaCloud-Agent-Skills
```

Used to get AccountId and derive SLS Project name.

---

## 5. WAF Log Field Reference

Key fields when querying WAF logs:

| Field | Meaning |
|------|------|  
| `matched_host` | **Protected resource** (WAF matched protection object name) |
| `host` | Request domain |
| `real_client_ip` | Client real IP |
| `request_path` | Request path |
| `request_method` | Request method |
| `status` | WAF returned status code |
| `final_plugin` | Triggered module (waf/cc/customrule etc.) |
| `final_rule_id` | Triggered rule ID |
| `waf_rule_type` | Triggered rule type |
| `waf_action` | WAF action (block/pass) |
| `request_traceid` | Request trace ID |

> **Note**: `waf_hit` field may not exist in some logs, DO NOT include in query, otherwise will cause errors.

---

## 6. Common Query Examples

### 6.1 Query by traceid

```bash
aliyun sls get-logs-v2 \
  --project "wafnew-project-<AccountId>-cn-hangzhou" \
  --logstore "wafnew-logstore" \
  --from "$(( $(date +%s) - 604800 ))" \
  --to "$(date +%s)" \
  --query "request_traceid: <traceid>" \
  --line 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### 6.2 Query by host + path + status

```bash
aliyun sls get-logs-v2 \
  --project "<ProjectName>" \
  --logstore "<LogStoreName>" \
  --from "$FROM" \
  --to "$TO" \
  --query "host:example.com and request_path:/api/login and status:403" \
  --line 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### 6.3 Query blocked requests

```bash
aliyun sls get-logs-v2 \
  --project "<ProjectName>" \
  --logstore "<LogStoreName>" \
  --from "$FROM" \
  --to "$TO" \
  --query "host:example.com and final_action:block" \
  --line 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## 7. Notes

1. **SLS Project Naming**: `wafnew-project-<AccountId>-<region>`
2. **SLS Logstore**: Fixed as `wafnew-logstore`
3. **Time Range**: WAF logs retained for 7-15 days by default
4. **Field Truncation**: Default query may return truncated fields, recommend using `select` to explicitly specify key fields
5. **Error Handling**: When query fails, check if aliyun is installed, credentials are correct, Region matches
