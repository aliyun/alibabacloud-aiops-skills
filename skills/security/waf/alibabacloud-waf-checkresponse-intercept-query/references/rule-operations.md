# WAF Rule Operation Policy

## Warning: Rule Disabling Policy (Important!)

**When the user requests to disable a rule, the following constraints must be followed:**

### 1. Only Perform Disable Operations

Only call `ModifyDefenseRule` or `ModifyDefenseTemplate` to set the rule status to `Status=0`

### 2. Never Delete Rules

Even if the disable operation fails, you **must not** call `DeleteDefenseRule` to delete the rule

### 3. Never Modify Rule Content

Do not modify rule matching conditions, actions, or other configurations

### 4. Failure Handling

- If the disable operation fails, inform the user of the failure reason
- **Do not** attempt to delete the rule or use other workarounds
- **Wait for the user's new instructions** before performing any other operations

### 5. Idempotent Check-Then-Act (Required)

Before executing any write operation, **always query the current state first** and skip the operation if the resource is already in the target state:

```bash
# Step 1: Check current rule status
aliyun waf-openapi DescribeDefenseRule \
  --region <region-id> \
  --InstanceId '<instance-id>' \
  --TemplateId <template-id> \
  --RuleId <rule-id> \
  --DefenseScene '<defense-scene>' \
  --RegionId '<region-id>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query

# Step 2: Only proceed if the rule is NOT already in the target state
# If the rule is already disabled (Status=0), skip the disable call
# If the rule is already enabled (Status=1), skip the enable call
```

> **Rationale**: This check-then-act pattern ensures idempotent behavior — repeated execution produces no additional side effects. It prevents unnecessary API calls and provides clear feedback to the user about the current state.

### 6. Pre-Operation Confirmation

```
Confirm operation: Disable rule {rule_name} (ID: {rule_id})
- Operation type: Disable (Status=0)
- Will not delete the rule
- Will not modify rule content
- Can be re-enabled at any time

Continue? Reply "yes" to confirm
```

---

## Example Commands

### Recommended: Use ModifyDefenseRuleStatus (Simple and Direct)

**Disable a rule**:
```bash
aliyun waf-openapi ModifyDefenseRuleStatus \
  --region ap-southeast-1 \
  --InstanceId 'waf_v2_public_cn-xxx' \
  --RuleId 20400384 \
  --RuleStatus 0 \
  --RegionId ap-southeast-1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query
```

**Enable a rule**:
```bash
aliyun waf-openapi ModifyDefenseRuleStatus \
  --region ap-southeast-1 \
  --InstanceId 'waf_v2_public_cn-xxx' \
  --RuleId 20400384 \
  --RuleStatus 1 \
  --RegionId ap-southeast-1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query
```

### Alternative: Use ModifyDefenseRule (Requires Full Configuration)

```bash
aliyun waf-openapi ModifyDefenseRule \
  --region ap-southeast-1 \
  --InstanceId waf_v2_public_cn-xxx \
  --Rules '{"id": 20400384, "Status": 0, "Config": "..."}' \
  --RegionId ap-southeast-1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query
```

> **Note**: `ModifyDefenseRule` requires passing the complete rule configuration with complex parameters. It is recommended to use `ModifyDefenseRuleStatus` first.

### Wrong: Never Delete (Even on Failure)

```bash
aliyun waf-openapi DeleteDefenseRule ...  # Forbidden
```

### Wrong: Never Modify Configuration

```bash
aliyun waf-openapi ModifyDefenseRule \
  --Rules '{"id": 20400384, "Config": {"action": "monitor"}}'  # Forbidden
```

---

## Operation Flowchart

```
User requests to disable/enable a rule
       |
Confirm rule information (RuleId, InstanceId, Region)
       |
Check current rule status via DescribeDefenseRule    <-- Idempotent check
       |
  +---------------------+
  | Already in target   |
  | state?              |
  +------+--------------+
     Yes | No
         |        |
   Inform user    Confirm operation with user
   (no action     (disable only, no deletion)
    needed)              |
                  Execute ModifyDefenseRuleStatus
                         |
                    +-------------+
                    |   Success?  |
                    +------+------+
                       Yes | No
                           |        |
                           |   Report failure reason
                           |   Wait for user's new instructions
                           |   (Do not attempt to delete)
                           v
                      Operation complete
```
