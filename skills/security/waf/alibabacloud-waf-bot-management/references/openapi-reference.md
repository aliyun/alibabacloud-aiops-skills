# WAF Bot Management OpenAPI Quick Reference

## Overview

WAF 3.0 OpenAPI is based on RPC signature style and supports multi-language SDKs. All Bot management operations can be performed via API.

Base parameters:
- All API calls must specify `--region` (e.g., cn-hangzhou)
- Most API calls require `--InstanceId` (WAF instance ID)
- API version: 2021-10-01

---

## Bot Management Direct APIs

| API Name | Description | Use Case |
|----------|-------------|----------|
| describe-bot-rule-labels | Query BOT management rule label information | Step 1: Query available label list |
| describe-bot-app-key | Query Bot management AppKey | Get AppKey during SDK integration |

---

## Protection Template Management APIs

A protection template is the top-level container for Bot management. A template contains multiple rules and takes effect when bound to a protection object.

| API Name | Description | Use Case |
|----------|-------------|----------|
| create-defense-template | Create a protection template | Step 3: Create Bot protection template |
| modify-defense-template | Modify a protection template | Update template configuration |
| delete-defense-template | Delete a protection template | Clean up unneeded templates |
| copy-defense-template | Copy a protection template | Quickly create a new template based on an existing one |
| modify-defense-template-status | Modify protection template status | Enable/disable template |
| describe-defense-templates | Query protection template list | Step 1: View existing templates |

---

## Protection Rule Management APIs

Protection rules are the specific policies within a template. Each rule corresponds to one or more Bot labels + an action.

| API Name | Description | Use Case |
|----------|-------------|----------|
| create-defense-rule | Create a protection rule | Step 3: Create Bot rules one by one |
| modify-defense-rule | Modify a protection rule | Step 5: Adjust rule parameters |
| delete-defense-rule | Delete a protection rule | Clean up unneeded rules |
| describe-defense-rules | Query protection rule list | Step 1/3: View/confirm rules |
| describe-defense-rule | Query a single protection rule's details | View detailed rule configuration |
| modify-defense-rule-status | Modify protection rule status | Enable/disable a single rule |

### CreateDefenseRule Parameter Description

```json
{
  "DefenseScene": "antibot",
  "RuleName": "Rule name",
  "RuleContent": {
    "bot_labels": ["malicious_crawler_python", "malicious_crawler_java"],
    "action": "block"
  }
}
```

Rate limiting rule RuleContent:

```json
{
  "stat_object": "ip",
  "interval": 60,
  "threshold": 30,
  "action": "js",
  "rule_type": "frequency"
}
```

Action codes: block (block), captcha (slider CAPTCHA), captcha_strict (strict slider CAPTCHA), js (JS verification), sigchl (dynamic token), monitor (observe), bypass (origin tag).

---

## Protection Object and Resource Management APIs

A protection object is a web application protected by WAF. Protection templates must be bound to a protection object to take effect.

| API Name | Description | Use Case |
|----------|-------------|----------|
| create-defense-resource | Create a protection object | Create a new protection object |
| delete-defense-resource | Delete a protection object | Clean up unneeded objects |
| modify-defense-resource | Modify a protection object | Update object configuration |
| describe-defense-resources | Query protection object list | Step 1: View existing objects |
| create-defense-resource-group | Create a protection object group | Manage protection objects in bulk |
| modify-template-resources | Bind/unbind protection resources to/from template | Step 3: Bind template to objects |
| describe-template-resources | Query protection resources bound to template | View which objects a template is bound to |
| describe-template-resource-count | Query count of resources bound to template | Quickly view binding count |

---

## Defense Scene Configuration APIs

| API Name | Description | Use Case |
|----------|-------------|----------|
| describe-defense-scene-config | Query defense scene configuration | View current scene configuration |
| modify-defense-scene-config | Modify defense scene configuration | Update scene parameters |

---

## WAF Instance and Domain Management APIs

| API Name | Description | Use Case |
|----------|-------------|----------|
| describe-instance | Query WAF instance information | Step 1: Confirm instance status and version |
| describe-domains | Query CNAME access domain list | Step 1: Confirm domain is onboarded |

---

## Log Service APIs

| API Name | Description | Use Case |
|----------|-------------|----------|
| describe-user-waf-log-status | Query log service status | Step 1: Confirm logging is enabled |

The log service has 20+ APIs covering log service status queries, field configuration, LogStore management, delivery configuration, and more.

---

## Report Information APIs

Used for Step 4 protection effectiveness verification.

| API Name | Description | Use Case |
|----------|-------------|----------|
| describe-rule-hits-top-rule-id | Query top rules by hit count | Step 4: View which rules are taking effect |
| describe-rule-hits-top-client-ip | Query top attack source IPs | Step 4: Identify major attack IPs |
| describe-rule-hits-top-ua | Query top UAs hitting rules | Step 4: Identify attack tools |
| describe-security-event-time-series-metric | Query security event time series | Step 4: View attack trends |
| describe-flow-top-url | Query top URLs by traffic | Step 4: Identify attack targets |

The report information section has 20+ APIs covering traffic time series, attack TopN, rule hit Top, security events, and more.

---

## Address Book APIs

Used for managing IP whitelists and blacklists.

| API Name | Description | Use Case |
|----------|-------------|----------|
| add-address | Add an address | Add trusted IP to whitelist |
| delete-address | Delete an address | Remove IP from whitelist |
| describe-addresses | Query address list | View current whitelist/blacklist |
| clear-address | Clear all addresses | Bulk reset address book |

---

## API Security APIs (LLM Scenario Integration)

The API security module has 30+ APIs covering risk detection, event alerts, asset management, compliance auditing, trace auditing, policy configuration, log subscription, and more. In the Bot management scenario, the key areas are:

- Risk detection: Discover API assets and identify security risks
- Event alerts: Events such as abnormally high-frequency access, traversal crawling, malicious consumption, etc.
- Policy configuration: Integrate Bot management or CC protection to configure interception rules

---

## Typical API Call Workflow

### Step 1: Current State Assessment

```
DescribeInstance -> DescribeDefenseTemplates -> DescribeBotRuleLabels
-> DescribeUserWafLogStatus -> DescribeDefenseResources -> DescribeDomains
```

### Step 3: Automated Configuration

```
CreateDefenseTemplate -> CreateDefenseRule (one by one)
-> ModifyTemplateResources (bind objects) -> ModifyDefenseTemplateStatus (enable)
```

### Step 4: Effectiveness Verification

```
DescribeRuleHitsTopRuleId -> DescribeRuleHitsTopClientIp
-> DescribeSecurityEventTimeSeriesMetric -> DescribeFlowTopUrl
-> DescribeRuleHitsTopUa
```

### Step 5: Tuning

```
ModifyDefenseRule (adjust parameters) -> ModifyDefenseRuleStatus (disable false positive rules)
-> CreateDefenseRule (add new rules)
```
