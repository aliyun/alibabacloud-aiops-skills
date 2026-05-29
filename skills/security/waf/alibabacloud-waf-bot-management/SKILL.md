---
name: alibabacloud-waf-bot-management
description: >
  Alibaba Cloud WAF Bot Management automated configuration assistant. Automatically completes bot protection
  policy evaluation, configuration, verification, and tuning via OpenAPI/CLI.
  Supports scenarios such as LLM API protection, retail promotion anti-scalper, general anti-crawling,
  and academic research platforms.
  Triggers when the user mentions Bot management, crawler protection, anti-crawling, WAF Bot, BOT2.0,
  LLM API abuse prevention, retail anti-scalper, promotion protection,
  SMS bombing, script attacks, or automated traffic protection.
---

# WAF Bot Management Automated Configuration Assistant

## Prerequisites

### Alibaba Cloud CLI

Alibaba Cloud CLI (aliyun) must be installed and configured. Credentials must be obtained through the default credential chain; hardcoding AK/SK in scripts is prohibited.

```bash
# Verify CLI is available
aliyun version
# Verify credentials are valid
aliyun waf-openapi describe-instance --region cn-hangzhou \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

If the CLI is not installed or credentials are invalid, direct the user to: https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference/cli-integration-example-v3

### WAF Instance

The user must have purchased a WAF 3.0 instance (Enterprise edition or above), and the Bot Management module must be enabled (Bot Management is a WAF add-on module and must be purchased separately).

### AI-Mode Configuration

This skill uses the aliyun CLI for all operations. AI-Mode lifecycle management commands:

```bash
# Enable AI-Mode
aliyun configure ai-mode enable

# Set User-Agent
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# Disable AI-Mode
aliyun configure ai-mode disable

# Update plugin
aliyun plugin update
```

Current state: AI-Mode must be enabled before executing any `aliyun waf-openapi` commands. All business CLI commands below include the `--user-agent` flag for traceability. System commands (e.g., `--help`, `configure`) do not set user-agent.

---

## Input Collection

Use AskUserQuestion to collect the following information. Any missing items must be followed up on:

### Required Items

1. **Industry Scenario**: LLM/API Service | Retail E-commerce/Promotion | General Anti-Crawling | Academic Research Platform
2. **Protected Domains**: At least one domain that needs protection
3. **Access Method**: CNAME | ALB Cloud Product Access | Hybrid Cloud | Not sure (can be queried via API)

### Scenario-Specific Follow-Up Questions

- **LLM Scenario**: API endpoint path prefix (e.g., /api/v1/), whether there is a mobile app, daily average API call volume
- **Retail Scenario**: Whether there are promotion time windows (date + time period), whether there is an app/mini-program, whether there are flash-sale/seckill scenarios
- **Academic Research Scenario**: Whether users access from cloud provider VMs, whether Python/script-based API calls are allowed
- **General Scenario**: Current attack symptoms (bandwidth saturation / data scraping / SMS bombing / other)

### Optional Items

- WAF instance region (default: cn-hangzhou)
- Whether there are compliance restrictions (e.g., cannot show CAPTCHA, cannot block by region)
- Whether specific legitimate crawlers need to be protected (e.g., search engine spiders)

---

## Execution Workflow

### Step 1: Current State Assessment (CLI Automation)

Query the current WAF instance and Bot Management configuration status via API, and output an assessment report.

```bash
# 1.1 Query WAF instance information
aliyun waf-openapi describe-instance --region {region} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 1.2 Query existing protection template list
aliyun waf-openapi describe-defense-templates --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 1.3 Query Bot Management rule label information
aliyun waf-openapi describe-bot-rule-labels --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 1.4 Query log service status
aliyun waf-openapi describe-user-waf-log-status --region {region} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 1.5 Query protected object list
aliyun waf-openapi describe-defense-resources --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 1.6 Query CNAME access domain list (confirm protected domains are onboarded)
aliyun waf-openapi describe-domains --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

**Assessment Checklist Output** (verify each item):
- [ ] WAF instance status is normal, Bot Management module is enabled
- [ ] Protected domains are onboarded to WAF (CNAME or cloud product access)
- [ ] Protected objects are created and associated
- [ ] Log service is enabled (required for subsequent verification)
- [ ] Bot collection fields are added to logs and indexing is enabled

If the Bot module is not enabled or domains are not onboarded, output operational guidance and pause. Wait for the user to confirm completion before continuing.

**Runtime Error Handling** (applies to all CLI calls):

When executing CLI commands in Step 1/3/4, handle errors as follows:

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| command not found | CLI not installed | Pause the workflow. Direct the user to https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference/cli-integration-example-v3 to install the CLI, or run `brew install aliyun-cli` (macOS) |
| InvalidAccessKeyId / Forbidden.RAM | Insufficient permissions | Pause the workflow. Ask the user to verify the RAM policy includes `AliyunWAFReadWriteAccess` |
| InvalidSecurityToken.Expired | STS Token expired | Ask the user to run `aliyun configure` to refresh credentials and retry |
| Throttling / Throttling.User | API rate limited | Wait 5 seconds and retry, up to 3 retries with increasing intervals (5s/10s/15s) |
| InternalError | Server-side error | Wait 10 seconds and retry once. If still failing, pause and report completed steps |
| InvalidParameter | Parameter error | Verify InstanceId and region are correct. Do not auto-retry |

**Rollback Strategy**: If some rules fail to create during Step 3, successfully created rules will not be automatically rolled back. Output the list of created rule IDs and advise the user to manually run `delete-defense-rule` to clean up, or wait until all rules are confirmed before enabling the template (Step 3.4 executes last).

**SDK Integration Checklist** (three critical pitfalls to proactively remind about):
1. Web clients must integrate the Web SDK; otherwise, all four soft-block actions (JS challenge, dynamic token, slider, strict slider) will fail
2. Static files (js/css/images) cannot have the Web SDK injected; only built-in Bot detection rules + slider can be used
3. When APP and Web share the same domain, the APP must integrate the SDK; otherwise, JS challenges will fail due to the lack of a JS environment, impacting business

For detailed SDK integration steps, see `references/sdk-integration-guide.md`.

---

### Step 2: Scenario-Based Rule Recommendation

Based on the user's selected scenario, load the corresponding configuration plan:

| Scenario | Reference Document | Core Protection Targets |
|----------|-------------------|------------------------|
| LLM/API Service | `references/scene-llm-api.md` | LLM API endpoints |
| Retail E-commerce/Promotion | `references/scene-retail-promotion.md` | Login page / Order page / Product page / Pricing API |
| General Anti-Crawling | `references/scene-anti-crawl.md` | All web pages |
| Academic Research Platform | `references/scene-academic.md` | API endpoints + Web pages |

Each scenario document includes: recommended rule labels to enable, rules not recommended for enabling with reasons, action selection, rate-limit threshold references, and special considerations.

**Universal Rules**: All scenarios must reference `references/rules-blacklist.md` (list of rules not recommended for enabling) and `references/attack-level-matrix.md` (attack level matching matrix).

---

### Step 3: CLI Automated Configuration

Based on the scenario recommendations from Step 2, automatically create protection templates and rules via CLI.

#### 3.0 Configure Whitelist (Execute First)

Before creating protection rules, add trusted IPs to the whitelist to avoid false positives on internal monitoring and legitimate services:

```bash
# Query existing address books
aliyun waf-openapi describe-addresses --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# Add trusted IPs to whitelist (can be executed multiple times)
aliyun waf-openapi add-address \
  --region {region} \
  --InstanceId {instance_id} \
  --AddressList '["{trusted_ip_1}","{trusted_ip_2}"]' \
  --AddressType "ipv4" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

Whitelist IP sources: internal monitoring IPs provided by the user, CI/CD egress IPs, partner fixed IPs, customer-owned cloud resource IP ranges.

#### 3.1 Create Protection Template

```bash
aliyun waf-openapi create-defense-template \
  --region {region} \
  --InstanceId {instance_id} \
  --TemplateName "{scenario_name}_Bot_Protection" \
  --DefenseScene "antibot" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

#### 3.2 Create Protection Rules

Based on the scenario-recommended rule labels, create rules one by one. Each rule requires:
- **DefenseScene**: Protection scenario (antibot)
- **RuleName**: Rule name
- **RuleContent**: Match conditions (labels, rate-limit thresholds, etc.)
- **Action**: Disposition action (block/captcha/captcha_strict/js/sigchl/monitor/bypass)

```bash
# Example: Create crawler client detection rule (action = block)
aliyun waf-openapi create-defense-rule \
  --region {region} \
  --InstanceId {instance_id} \
  --TemplateId {template_id} \
  --DefenseScene "antibot" \
  --RuleName "Crawler_Client_Block" \
  --RuleContent '{"bot_labels":["malicious_crawler_python","malicious_crawler_java"],"action":"block"}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# Example: Create IP rate-limit rule (requests > 30 in 60 seconds -> JS challenge)
aliyun waf-openapi create-defense-rule \
  --region {region} \
  --InstanceId {instance_id} \
  --TemplateId {template_id} \
  --DefenseScene "antibot" \
  --RuleName "IP_High_Frequency_Rate_Limit" \
  --RuleContent '{"stat_object":"ip","interval":60,"threshold":30,"action":"js","rule_type":"frequency"}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

#### 3.3 Bind Protected Objects

```bash
aliyun waf-openapi modify-template-resources \
  --region {region} \
  --InstanceId {instance_id} \
  --TemplateId {template_id} \
  --ResourceMode "bind" \
  --ResourceList '["{resource_id_1}","{resource_id_2}"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

To obtain `resource_id`: Extract the `ResourceId` field from the `describe-defense-resources` response in Step 1.5. If no protected objects were found in Step 1, create one first via `create-defense-resource`.

#### 3.4 Enable Protection Template

```bash
aliyun waf-openapi modify-defense-template-status \
  --region {region} \
  --InstanceId {instance_id} \
  --TemplateId {template_id} \
  --Status "enabled" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

**Canary Deployment Recommendation**: For initial configuration, set all disposition actions to `monitor` (observe only, no blocking). Run for a period and review hit data. After confirming no false positives, switch to the formal disposition actions. Recommended canary periods by scenario: LLM/Retail scenarios 24-48 hours, general anti-crawling 24-48 hours, academic research scenarios 7-14 days (diverse user patterns require a longer observation period).

**Canary Switch SOP** (monitor -> formal action):
1. Review canary period hit data via `describe-rule-hits-top-rule-id` and `describe-rule-hits-top-client-ip`
2. Check whether any flagged Top IPs/UAs are legitimate users (cross-validate with SLS logs)
3. After confirming no false positives, modify rule actions one by one:
```bash
# Switch a single rule from monitor to formal action (e.g., captcha)
aliyun waf-openapi modify-defense-rule \
  --region {region} \
  --InstanceId {instance_id} \
  --RuleId {rule_id} \
  --Action "captcha" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```
4. After switching each rule, run for 4 hours of observation. Confirm no anomalies before switching the next rule
5. If the target action is block, it is recommended to first switch to captcha and observe for 4 hours before upgrading to block:
```bash
# captcha -> block upgrade (execute only after confirming captcha has no false positives)
aliyun waf-openapi modify-defense-rule \
  --region {region} \
  --InstanceId {instance_id} \
  --RuleId {rule_id} \
  --Action "block" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```
6. After all switches are complete, confirm all rule statuses via `describe-defense-rules`

#### 3.5 Configuration Verification

After each rule is created, query to verify:
```bash
aliyun waf-openapi describe-defense-rules \
  --region {region} \
  --InstanceId {instance_id} \
  --TemplateId {template_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

---

### Step 4: CLI Automated Verification

After configuration is complete and has run for a period (recommended at least 1 hour), query protection effectiveness via API.

```bash
# 4.1 Query Top 10 rule hits
aliyun waf-openapi describe-rule-hits-top-rule-id \
  --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 4.2 Query Top 10 attack source IPs
aliyun waf-openapi describe-rule-hits-top-client-ip \
  --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 4.3 Query attack traffic time series
aliyun waf-openapi describe-security-event-time-series-metric \
  --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 4.4 Query Top traffic URLs
aliyun waf-openapi describe-flow-top-url \
  --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 4.5 Query Top UAs hitting rules
aliyun waf-openapi describe-rule-hits-top-ua \
  --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

For more granular log analysis (e.g., single-device multi-account switching detection), use SLS queries. Templates are available in `references/sls-query-templates.md`.

---

### Step 5: Effectiveness Assessment and Tuning

Based on the data from Step 4, output an assessment report:

**Block Rate Assessment**:
- Target block rate > 85% (practical reference range: 85%-95%)
- If the block rate is too low, check whether rules cover the main attack signatures
- If the block rate is too high (>98%), check for false positives

**False Positive Risk Assessment**:
- Check whether any blocked Top IPs/UAs are legitimate users
- Refer to `references/rules-blacklist.md` to confirm no rules are enabled that should not be

**Tuning Operations** (CLI commands):

```bash
# 5.1 Adjust rule disposition action (e.g., if a rule has a high false positive rate, switch to observe mode)
aliyun waf-openapi modify-defense-rule \
  --region {region} \
  --InstanceId {instance_id} \
  --RuleId {rule_id} \
  --Action "monitor" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 5.2 Disable false-positive rule
aliyun waf-openapi modify-defense-rule-status \
  --region {region} \
  --InstanceId {instance_id} \
  --RuleId {rule_id} \
  --Status "disabled" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 5.3 Add targeted rule (based on newly discovered attack signatures)
aliyun waf-openapi create-defense-rule \
  --region {region} \
  --InstanceId {instance_id} \
  --TemplateId {template_id} \
  --DefenseScene "antibot" \
  --RuleName "{new_rule_name}" \
  --RuleContent '{...}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"

# 5.4 Adjust rate-limit threshold (modify existing frequency control rule)
aliyun waf-openapi modify-defense-rule \
  --region {region} \
  --InstanceId {instance_id} \
  --RuleId {rule_id} \
  --RuleContent '{"stat_object":"ip","interval":60,"threshold":50,"action":"captcha","rule_type":"frequency"}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

**Tuning Recommendations**:
- Threshold adjustment: Adjust rate-limit thresholds based on normal business baselines
- Action adjustment: Switch rules confirmed as false positives during observation to monitor or disable them
- New rules: Add targeted policies based on newly discovered attack signatures
- SDK deployment: If the SDK is not yet deployed, it is strongly recommended to deploy it for optimal protection

---

## Action Selection Principles (Universal)

| Rule Type | Recommended Action | Reason |
|-----------|-------------------|--------|
| IDC Intelligence / Request Sequence / Threat Intelligence | captcha (slider) | Legitimate users can pass verification |
| AI Crawlers / Forged Spiders / Known Malicious Tools | block | Clearly malicious; no need to offer verification |
| Script Clients (Python/Java/Go, etc.) | block or captcha | Depends on scenario; academic platforms may have legitimate scripts |
| IP/Device/Account High-Frequency Rate Limiting | js (JS challenge) or captcha | Normal browsers can pass automatically |
| Device Spoofing Detection | captcha | Prevents false positives on legitimate users |
| Browser Probe | captcha | Detects developer tools/emulators |

**Slider Type Distinction**:
- Standard slider (captcha): After passing verification, no further verification for 30 minutes (Cookie-based). Suitable for login pages
- Strict slider (captcha_strict): Verifies every time. Suitable for critical operations such as order pages/payment pages

---

## Output Format

After each execution, output a Markdown report containing:

1. **Current State Assessment Summary**: Instance status, number of configured rules, SDK deployment status
2. **Configuration Change Log**: List of rules created/modified in this session (rule name, disposition action, effective scope)
3. **Protection Effectiveness Data**: Block rate, top hit rules, top attack IPs
4. **Tuning Recommendations**: Next optimization suggestions
5. **Important Notes**: SDK deployment reminders, rules not recommended for enabling

---

## Reference Document Index

| File | Content | Usage Scenario |
|------|---------|---------------|
| `references/bot2-rules-reference.md` | BOT2.0 full rule label reference | Look up label names and default states when configuring rules |
| `references/sdk-integration-guide.md` | Web/App SDK integration guide | Step 1 SDK deployment check |
| `references/scene-llm-api.md` | LLM API scenario configuration manual | Step 2 scenario recommendation |
| `references/scene-retail-promotion.md` | Retail promotion scenario configuration manual | Step 2 scenario recommendation |
| `references/scene-anti-crawl.md` | General anti-crawling scenario configuration manual | Step 2 scenario recommendation |
| `references/scene-academic.md` | Academic research scenario configuration manual | Step 2 scenario recommendation |
| `references/sls-query-templates.md` | SLS query template library | Step 4 deep log analysis |
| `references/attack-level-matrix.md` | Attack level x protection strategy matrix | Step 2 attack level assessment |
| `references/rules-blacklist.md` | Rules not recommended for enabling | Step 2/3 rule filtering |
| `references/openapi-reference.md` | WAF Bot Management OpenAPI quick reference | Step 3 CLI configuration |
