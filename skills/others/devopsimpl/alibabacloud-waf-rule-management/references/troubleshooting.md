# WAF Skill Common Issues Troubleshooting

> This file contains solutions for common issues with CLI tool installation, SLS queries, authentication, etc.
>
> Read on demand by the Agent when encountering issues.

---

## 1. Command Not Found: `aliyun: command not found`

**Solution**:
```bash
brew install aliyun-cli
```

---

## 2. Command Not Found: `aliyunlog: command not found`

**Solution**:
```bash
pip3 install aliyun-log-cli
```

---

## 3. SLS Query Returns Empty Results

**Troubleshooting Steps**:

1. Confirm the traceid / query condition is correct
2. Confirm the time range covers the request time (recommend querying the last 7 days)
3. Confirm the Region is correct (domestic `cn-hangzhou`, overseas `ap-southeast-1`)
4. Confirm the AK/SK has permission to access SLS
5. Confirm the Project/Logstore name is spelled correctly

---

## 4. Authentication Failure

**Troubleshooting Steps**:

1. Run `aliyun sts get-caller-identity` to verify AK/SK validity
2. Confirm the account has permission to access the corresponding Project/Logstore
3. Check whether the RAM permission policy is correctly configured (see [ram-policies.md](ram-policies.md))

---

## 5. SLS Query Error: `ParameterInvalid: Column 'xxx' cannot be resolved`

**Cause**: The select statement uses a non-existent field (e.g., `waf_hit`).

**Solution**: Remove the non-existent field and retry. See SKILL.md Section 1.4 for key field descriptions.

---

## 6. WAF API Error: `Defense.Control.DefenseWhitelistBypassTagInvalid`

**Cause**: The whitelist rule is missing the `tags` field.

**Solution**: Add a valid tag such as `"tags":["regular_rule"]`. See [api_reference.md](api_reference.md).

---

## 7. WAF API Error: `Defense.Control.DefenseRuleConditionValueInvalid`

**Cause**: The conditions field is incorrect, e.g., using `"value"` instead of `"values"`.

**Solution**: Check the field names of each object in the conditions array, ensure the plural form `"values"` is used.

---

## 8. WAF API Error: `InvalidBindResources`

**Cause**: Array parameter format error, using JSON array or missing index.

**Solution**: Use flat format: `--BindResources.1 'xxx'`. See [cli_traps.md](cli_traps.md).

---

## 9. Rule Not Taking Effect After Deployment

**Troubleshooting Steps**:

1. Confirm the rule status `status=1` (enabled)
2. Wait 10-30 seconds for effective delay
3. Use the rule not effective diagnosis process (SKILL.md Section 3)
4. Check whether the protection object is correctly bound to the template
5. Check for whitelist conflicts

---

## 10. Rule's Template Not Bound to Protection Object

**Problem Manifestation**: The rule has been created and status is normal (status=1), but traffic is not being blocked or allowed.

**Cause Analysis**:
- In WAF 3.0, rules are organized in templates (Template)
- Templates must be bound to a protection object (Resource) to take effect
- If the rule's template is not bound to the target protection object, the rule will not take effect

**Diagnosis Steps**:

1. **Query the rule's template**:
   ```bash
   aliyun waf-openapi describe-defense-rules \
     --version 2021-10-01 --force --region cn-hangzhou \
     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}" \
     --InstanceId '<instance_id>' \
     --RuleType 'custom_acl'
   ```
   Find the target rule in the returned results and record its `TemplateId`

2. **Query templates bound to the protection object**:
   ```bash
   aliyun waf-openapi describe-defense-resource-templates \
     --version 2021-10-01 --force --region cn-hangzhou \
     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}" \
     --InstanceId '<instance_id>' --Resource '<resource>'
   ```
   View the returned `Templates` array

3. **Compare and determine**:
   - If the rule's `TemplateId` is not in the bound template list, this confirms the issue

**Solution**:

**Method 1: Bind the rule's template to the protection object**
- Console operation:
  1. Go to `Protection Configuration` → `Protection Objects`
  2. Find the target protection object (e.g., `i-bp1ivk5aoljy431axxa8-80-ecs`)
  3. Click "Bind Template" or "Manage Templates"
  4. Select the template containing the target rule
  5. Save the binding

**Method 2: Recreate the rule in an already bound template**
- Console operation:
  1. Go to `Protection Configuration` → `Custom Protection` → `Custom Rules`
  2. Ensure the rule is created in the context of an already bound template
  3. Or edit the existing rule and move it to a bound template

**Notes**:
- Template binding takes effect in about 30 seconds
- A protection object can be bound to multiple templates
- Whitelist templates have higher priority than custom rule templates

---

## 11. Rule Match Conditions Do Not Match Actual Request

**Problem Manifestation**: The rule is configured with specific URI, IP, or other conditions, but the actual request does not meet these conditions, causing the rule to not take effect.

**Common Scenarios**:

**Scenario 1: URI Path Mismatch**
- Rule configuration: URI **contains** `/chenhang`
- Actual request: `request_path: "/"`
- Result: Path does not match, rule does not take effect

**Scenario 2: IP Address Mismatch**
- Rule configuration: Source IP **contains** `192.168.1.0/24`
- Actual request: `real_client_ip: 10.0.0.1`
- Result: IP not in the specified network segment, rule does not take effect

**Diagnosis Steps**:

1. **Query rule configuration**:
   ```bash
   aliyun waf-openapi describe-defense-rules \
     --version 2021-10-01 --force --region cn-hangzhou \
     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}" \
     --InstanceId '<instance_id>' \
     --Query '{"ruleId":<rule_id>}'
   ```
   View the `conditions` array in the `Config` field

2. **Query actual traffic logs**:
   ```bash
   aliyun sls get-logs-v2 \
     --project "wafnew-project-<account_id>-cn-hangzhou" \
     --logstore "wafnew-logstore" \
     --from "$(( $(date +%s) - 604800 ))" --to "$(date +%s)" \
     --query "request_traceid:<traceid>" \
     --line 10 \
     --read-timeout 30 --connect-timeout 10 \
     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
   ```
   View `request_path`, `real_client_ip`, `host` and other fields

3. **Compare and analyze**:
   - Check the key in the rule conditions (e.g., URL, IP)
   - Check the opValue in the rule conditions (e.g., contain, eq, ne)
   - Check the values in the rule conditions (e.g., `/chenhang`, `192.168.1.0/24`)
   - Compare with the corresponding fields of the actual request

**Solution**:

Adjust the rule match conditions according to actual needs:
- To block all requests to the root path: URI **equals** `/`
- To block requests containing a specific path: URI **contains** `/specific_path`
- To block a specific IP: Source IP **contains** `IP_address`
- To block non-specific IPs: Source IP **not equal** `IP_address`

---

## 12. WAF Console Path Errors (WAF 2.0 vs 3.0)

**Problem Description**: The user or AI provided incorrect console configuration paths.

**Wrong Example**:
- ❌ `Protection Configuration` → `Access Control` → `Whitelist` (this is the WAF 2.0 path)

**Correct Paths (WAF 3.0)**:
- ✅ `Protection Configuration` → `Custom Protection` → `Whitelist`
- ✅ `Protection Configuration` → `Custom Protection` → `Custom Rules`
- ✅ `Protection Configuration` → `Custom Protection` → `IP Blacklist`

**How to Identify WAF Version**:
- WAF 3.0 API version: `2021-10-01`
- WAF 3.0 product name: `waf-openapi`
- If the user does not specify, default to WAF 3.0

**Solution**: Ensure the correct WAF 3.0 console paths are used for configuration guidance.

---

## 13. IP Access Control Configuration Incomplete

**Problem Description**: The user wants to implement "only allow specific IPs to access", but only configured the whitelist without a block rule.

**Wrong Approach**:
- Only configure the whitelist to allow a specific IP to access, but without configuring a block rule for other IPs
- This way other IPs can still access (unless basic protection blocks by default)

**Correct Approach (Two Options)**:

**Option 1: Custom Rule (Recommended)**
- Create a custom rule: IP **not belonging to** the specified network segment → **Block**
- One rule can implement "only allow specific IPs to access"
- Use `custom_acl` DefenseScene, `ne` operator

**Option 2: Whitelist + Basic Protection**
- Configure the whitelist to allow specific IPs
- Ensure basic protection (`waf_group` or `waf_base`) is enabled
- Basic protection will block unmatched requests by default

**Solution**: Explicitly state the complete rule set that needs to be configured in the configuration guidance, ensuring the logic is complete.
