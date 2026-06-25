# WAF CLI Command Reference

> This file contains complete examples of all WAF-related CLI commands.
> 
> Agent should read this file before executing commands to get correct command formats.

---

## Credential Usage

### Profile Handling Rules (Critical)

**IMPORTANT: To ensure Skill portability, MUST follow these rules:**

- ❌ **DO NOT use `--profile` parameter** (Evaluation system Forbidden rule)
- ❌ **DO NOT auto-detect user's profile** (Do NOT run `aliyun configure list`)
- ❌ **DO NOT run `aliyun configure get`** (Exposes AK/SK, serious security violation)
- ❌ **DO NOT assume or hardcode profile names**
- ✅ **Rely on default profile** (Do NOT explicitly specify any profile parameter)
- ✅ **Rely on environment variables or ~/.aliyun/config.json default configuration**

**Correct Approach**:
```bash
# ✅ Correct: No --profile specified, relies on default configuration
aliyun waf-openapi describe-instance --version 2021-10-01 --region cn-hangzhou

# ❌ Wrong: Using --profile (Forbidden)
aliyun waf-openapi describe-instance --profile default --version 2021-10-01

# ❌ Wrong: Running configure get (Exposes AK/SK)
aliyun configure get --profile default
```

**Alibaba Cloud CLI (aliyun)**:
- **Do NOT use `--profile` parameter**, rely on default credential chain
- **Do NOT explicitly pass credentials**
- All commands MUST include `--user-agent AlibabaCloud-Agent-Skills`

---

## 1. SLS Log Query Commands

> **IMPORTANT**: Use `aliyun sls get-logs-v2` (SLS plugin required).
> 
> Credentials must be configured in advance via `aliyun configure`, stored in `~/.aliyun/config.json`.

### 1.1 Query by traceid (Recommended, explicit field selection)

```bash
aliyun sls get-logs-v2 \
  --project "<ProjectName>" \
  --logstore "<LogStoreName>" \
  --from "$FROM" \
  --to "$TO" \
  --query "request_traceid: <traceid>" \
  --line 10 \
  --accept_encoding lz4 \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example**:
```bash
aliyun sls get-logs-v2 \
  --project "wafnew-project-1882089769163987-cn-hangzhou" \
  --logstore "wafnew-logstore" \
  --from "$(( $(date +%s) - 604800 ))" \
  --to "$(date +%s)" \
  --query "request_traceid:2f6f0cbc17759652456034145eef13" \
  --line 10 \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### 1.2 Query by traceid (Simplified, may truncate fields)

```bash
aliyun sls get-logs-v2 \
  --project "<ProjectName>" \
  --logstore "<LogStoreName>" \
  --from "$FROM" \
  --to "$TO" \
  --query "request_traceid: <traceid>" \
  --line 10 \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### 1.3 Query by host + url_path + status combination

```bash
aliyun sls get-logs-v2 \
  --project "<ProjectName>" \
  --logstore "<LogStoreName>" \
  --from "$FROM" \
  --to "$TO" \
  --query "host:<domain> and request_path:<path> and status:<status_code>" \
  --line 10 \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```
```

### 1.4 Query by host + IP

```bash
aliyun sls get-logs-v2 \
  --project "<ProjectName>" \
  --logstore "<LogStoreName>" \
  --from "$FROM" \
  --to "$TO" \
  --query "host:<domain> and real_client_ip:<ip>" \
  --line 10 \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### 1.5 Query blocked requests

```bash
aliyun sls get-logs-v2 \
  --project "<ProjectName>" \
  --logstore "<LogStoreName>" \
  --from "$FROM" \
  --to "$TO" \
  --query "request_traceid:<traceid> and final_action:block" \
  --line 10 \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### ⚠️ Common Errors

| Error | Cause | Solution |
|------|------|---------|  
| `Invalid parameters` | Used `--profile` | Remove `--profile`, rely on default credential chain |

**Note**: Using `aliyun sls get-logs-v2` (SLS plugin required)

---

## 2. WAF Instance and Template Query Commands

### 2.1 Get WAF Instance ID

```bash
aliyun waf-openapi describe-instance \
  --version 2021-10-01 --force --region <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 2.2 Query protection templates bound to protected resources

```bash
aliyun waf-openapi describe-defense-resource-templates \
  --version 2021-10-01 --force --region <region> \
  --user-agent AlibabaCloud-Agent-Skills \
  --InstanceId '<instance_id>' --Resource '<resource>'
```

### 2.3 Query template details and binding count

```bash
aliyun waf-openapi describe-defense-template \
  --version 2021-10-01 --force --region <region> \
  --user-agent AlibabaCloud-Agent-Skills \
  --InstanceId '<instance_id>' --TemplateId <template_id>
```

---

## 3. Rule Query Commands

### 3.1 Query rules under a template

```bash
aliyun waf-openapi describe-defense-rules \
  --version 2021-10-01 --force --region <region> \
  --user-agent AlibabaCloud-Agent-Skills \
  --InstanceId '<instance_id>' \
  --Query '{"templateId":<template_id>}' \
  --RuleType '<defense_scene>'
```

> **API Trap**: For whitelist scenarios, MUST add `--RuleType whitelist`, otherwise query returns 0 results.

### 3.2 Query rule by ruleId

```bash
aliyun waf-openapi describe-defense-rules \
  --version 2021-10-01 --force --region <region> \
  --user-agent AlibabaCloud-Agent-Skills \
  --InstanceId '<instance_id>' \
  --Query '{"ruleId":<rule_id>}'
```

---

## 4. Diagnosis Engine Invocation

```bash
# Save rule Config JSON to /tmp/waf_rule.json
# Save log entry to /tmp/waf_log.json

python scripts/rule_matcher.py \
  --rule-file /tmp/waf_rule.json \
  --log-file /tmp/waf_log.json \
  --xff-status <0|1|2>
```
