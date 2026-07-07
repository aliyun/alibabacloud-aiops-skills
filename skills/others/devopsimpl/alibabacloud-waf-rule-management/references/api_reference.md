# WAF 3.0 OpenAPI Parameter Specification

> This document is the **authoritative parameter reference** for WAF read-only diagnosis. When constructing any API request, you must strictly follow the field definitions and example formats in this document.
>
> **Note**: This Skill is read-only. All API calls rely on the default credential chain (NO `--profile` parameter, NO explicit AK/SK).

---

## 1. General Constraints

- **Credential Usage**: All CLI commands rely on the default credential chain (NO `--profile` parameter) and set `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"`
- **Name Constraint**: All rule names and protection template names MUST NOT contain spaces
- **status Field**: All `status` field values are **integers** `0` or `1`

---

## 2. DescribeInstance

Get the WAF instance information under the current account.

### Request Parameters

No required parameters.

### CLI Example

```bash
aliyun waf-openapi describe-instance \
  --version 2021-10-01 --force --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
```

Extract the `InstanceId` field from the returned JSON.

### Key Return Fields

| Field | Type | Description |
| --- | --- | --- |
| InstanceId | string | WAF instance ID |

---

## 3. DescribeDefenseResourceTemplates

Query the protection templates bound to a protection object.

### Request Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| InstanceId | string | Yes | WAF instance ID |
| Resource | string | Yes | Protection object name |

### Key Return Fields

| Field | Type | Description |
| --- | --- | --- |
| Templates[].TemplateId | integer | Template ID |
| Templates[].TemplateName | string | Template name |
| Templates[].DefenseScene | string | Defense scene |
| Templates[].TemplateType | string | user_default / user_custom |
| Templates[].TemplateStatus | integer | 0=disabled, 1=enabled |

### CLI Example

```bash
aliyun waf-openapi describe-defense-resource-templates \
  --version 2021-10-01 --force --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}" \
  --InstanceId '<instance_id>' --Resource '<resource>'
```

---

## 4. DescribeDefenseRules

Query protection rule configuration.

### Request Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| InstanceId | string | Yes | WAF instance ID |
| Query | string | Yes | JSON-format query condition, e.g., `{"templateId":<id>}` or `{"ruleId":<id>}` |
| RuleType | string | No | Defense scene type; whitelist scenarios MUST specify `whitelist` |

### Key Return Fields

| Field | Type | Description |
| --- | --- | --- |
| Rules[].RuleId | integer | Rule ID |
| Rules[].RuleName | string | Rule name |
| Rules[].Status | integer | 0=disabled, 1=enabled |
| Rules[].Config | object | Rule configuration details |

### CLI Example

#### 4.1 Query rules under a template

```bash
aliyun waf-openapi describe-defense-rules \
  --version 2021-10-01 --force --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}" \
  --InstanceId '<instance_id>' \
  --Query '{"templateId":<template_id>}' \
  --RuleType '<defense_scene>'
```

> **API Trap**: Whitelist (whitelist) scenarios MUST add `--RuleType whitelist`, otherwise the query returns 0 results.

#### 4.2 Query rule by ruleId

```bash
aliyun waf-openapi describe-defense-rules \
  --version 2021-10-01 --force --region <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}" \
  --InstanceId '<instance_id>' \
  --Query '{"ruleId":<rule_id>}'
```

---

## 5. DefenseScene Values

| Value | Meaning |
| --- | --- |
| waf_group | Basic protection |
| waf_base | New Web Core Protection |
| antiscan | Scan protection |
| ip_blacklist | IP blacklist |
| custom_acl | Custom rules |
| whitelist | Whitelist |
| region_block | Region blocking |
| custom_response | Legacy custom response |
| cc | CC protection |
| tamperproof | Web tamper protection |
| dlp | Information leak protection |
| spike_throttle | Spike throttling |

---

## 6. Rule Configuration Config Structure

### 6.1 General Structure

```json
{
  "name": "rule_name",
  "status": 1,
  "conditions": [...],
  "action": {...}
}
```

### 6.2 Condition Structure

```json
{
  "key": "field_name",
  "op": "operator",
  "opValue": "match_value"
}
```

**Common keys**:
- `ip`: Client IP
- `uri`: Request URI
- `host`: Request domain
- `user_agent`: User-Agent

**Common ops**:
- `contain`: Contains
- `not-contain`: Does not contain
- `eq`: Equals
- `ne`: Not equal

### 6.3 Action Structure

```json
{
  "type": "action_type",
  "value": "action_value"
}
```

**type values**:
- `block`: Block
- `pass`: Allow
- `captcha`: Slider verification
- `js`: JS verification

---

## 7. SLS Log Field Reference

Key fields when querying WAF logs:

| Field | Meaning |
|------|------|
| `matched_host` | **Protection object** (WAF matched protection object name) |
| `host` | Request domain |
| `real_client_ip` | Client real IP |
| `request_path` | Request path |
| `request_method` | Request method |
| `status` | WAF returned status code |
| `final_plugin` | Triggered module (waf/cc/customrule, etc.) |
| `final_rule_id` | Triggered rule ID |
| `waf_rule_type` | Triggered rule type |
| `waf_action` | WAF action (block/pass) |
| `request_traceid` | Request trace ID |

> **Note**: The `waf_hit` field may not exist in some logs; do not include it in queries.

---

## 8. key and opValue Compatibility Quick Reference

| key | Supported op | opValue Example |
|-----|-----------|--------------|
| ip | contain, not-contain | `1.2.3.4`, `1.2.3.0/24` |
| uri | contain, not-contain, eq, ne | `/api/login` |
| host | contain, eq | `example.com` |
| user_agent | contain, not-contain | `Mozilla/5.0` |

**Important**:
- In whitelist (whitelist) scenarios, IP only allows `contain` and `not-contain`; **`eq` is prohibited**
- **Do NOT use the `inl` operator**
