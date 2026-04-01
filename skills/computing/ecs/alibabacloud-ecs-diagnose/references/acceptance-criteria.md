# Acceptance Criteria: alibabacloud-ecs-diagnose

**Scenario**: ECS Instance Comprehensive Diagnostics
**Purpose**: Skill testing acceptance criteria

---

## 1. CLI Command Patterns

### Product Validation

#### ✅ CORRECT - Valid product names
```bash
aliyun ecs describe-instances --user-agent AlibabaCloud-Agent-Skills
aliyun vpc describe-vpcs --user-agent AlibabaCloud-Agent-Skills
aliyun cms describe-metric-last --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - Invalid product names
```bash
aliyun ec2 describe-instances  # Wrong: "ec2" is AWS, not Aliyun
aliyun elastic-compute describe-instances  # Wrong: Use "ecs" not full name
aliyun cloudmonitor describe-metric-last  # Wrong: Use "cms" not "cloudmonitor"
```

**Explanation**: Aliyun CLI uses abbreviated product codes, not full names or AWS equivalents.

---

### Command/Action Validation

#### ✅ CORRECT - Valid actions in plugin mode
```bash
# ECS actions
aliyun ecs describe-instances --user-agent AlibabaCloud-Agent-Skills
aliyun ecs describe-instance-attribute --user-agent AlibabaCloud-Agent-Skills
aliyun ecs describe-instance-status --user-agent AlibabaCloud-Agent-Skills
aliyun ecs describe-instance-history-events --user-agent AlibabaCloud-Agent-Skills
aliyun ecs describe-security-group-attribute --user-agent AlibabaCloud-Agent-Skills
aliyun ecs run-command --user-agent AlibabaCloud-Agent-Skills
aliyun ecs describe-invocation-results --user-agent AlibabaCloud-Agent-Skills

# VPC actions
aliyun vpc describe-vpcs --user-agent AlibabaCloud-Agent-Skills
aliyun vpc describe-eip-addresses --user-agent AlibabaCloud-Agent-Skills

# CMS actions
aliyun cms describe-metric-last --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - Wrong action format or non-existent actions
```bash
# Wrong: Using API-style PascalCase instead of plugin mode kebab-case
aliyun ecs DescribeInstances  # Should be: describe-instances
aliyun ecs RunCommand  # Should be: run-command

# Wrong: Non-existent actions
aliyun ecs get-instances  # Should be: describe-instances
aliyun ecs list-instances  # Should be: describe-instances
aliyun ecs show-instance  # Should be: describe-instances
```

**Explanation**: Aliyun CLI plugin mode uses lowercase kebab-case (words connected with hyphens), NOT PascalCase from API names.

---

### Parameter Validation

#### ✅ CORRECT - Valid parameter names and formats
```bash
# Instance query with correct parameters
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]' \
  --user-agent AlibabaCloud-Agent-Skills

# Query by instance name
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --instance-name "my-instance" \
  --user-agent AlibabaCloud-Agent-Skills

# Query by private IP
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --private-ip-addresses '["192.168.1.10"]' \
  --user-agent AlibabaCloud-Agent-Skills

# Security group query
aliyun ecs describe-security-group-attribute \
  --region-id cn-hangzhou \
  --security-group-id sg-xxxxx \
  --direction ingress \
  --user-agent AlibabaCloud-Agent-Skills

# System events query
aliyun ecs describe-instance-history-events \
  --region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --instance-event-cycle-status.1 Executing \
  --instance-event-cycle-status.2 Inquiring \
  --user-agent AlibabaCloud-Agent-Skills

# Cloud Assistant command execution
aliyun ecs run-command \
  --region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunShellScript \
  --command-content "dXB0aW1l" \
  --timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills

# Monitoring metrics query
aliyun cms describe-metric-last \
  --region-id cn-hangzhou \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions '[{"instanceId":"i-xxxxx"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - Invalid parameter names or formats
```bash
# Wrong parameter names (API-style PascalCase)
aliyun ecs describe-instances \
  --RegionId cn-hangzhou \  # Should be: --region-id
  --InstanceIds '["i-xxxxx"]'  # Should be: --instance-ids

# Wrong array format for instance IDs
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --instance-ids i-xxxxx  # Should be: '["i-xxxxx"]' (JSON array)

# Wrong multiple instance specification
aliyun ecs run-command \
  --region-id cn-hangzhou \
  --instance-ids '["i-xxxxx","i-yyyyy"]' \  # Wrong parameter name
  --type RunShellScript \
  --command-content "dXB0aW1l"

# Correct way for multiple instances
aliyun ecs run-command \
  --region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --instance-id.2 i-yyyyy \  # Correct: use .1, .2, .3, etc.
  --type RunShellScript \
  --command-content "dXB0aW1l"

# Wrong dimensions format
aliyun cms describe-metric-last \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions instanceId:i-xxxxx  # Should be: '[{"instanceId":"i-xxxxx"}]' (JSON)
```

**Explanation**:
1. Plugin mode uses kebab-case for parameter names (--region-id, not --RegionId)
2. Array parameters use JSON format with quotes
3. Repeated parameters use .1, .2, .3 suffix notation
4. Dimensions parameter requires JSON format

---

### User-Agent Header

#### ✅ CORRECT - Always include user-agent
```bash
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - Missing user-agent
```bash
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]'
```

**Explanation**: All commands in this skill MUST include `--user-agent AlibabaCloud-Agent-Skills` for tracking and analytics.

---

## 2. Enum Value Validation

### Instance Event Cycle Status

#### ✅ CORRECT - Valid enum values
```bash
# Valid status values
--instance-event-cycle-status.1 Executing
--instance-event-cycle-status.2 Inquiring
--instance-event-cycle-status.3 Scheduled
--instance-event-cycle-status.4 Avoided
--instance-event-cycle-status.5 Canceled
--instance-event-cycle-status.6 Failed
```

#### ❌ INCORRECT - Invalid enum values
```bash
--instance-event-cycle-status.1 Running  # Wrong: Use "Executing"
--instance-event-cycle-status.1 Pending  # Wrong: Use "Scheduled"
--instance-event-cycle-status.1 Active  # Wrong: Not a valid value
```

---

### Security Group Direction

#### ✅ CORRECT
```bash
--direction ingress  # Inbound rules
--direction egress   # Outbound rules
```

#### ❌ INCORRECT
```bash
--direction inbound   # Wrong: Use "ingress"
--direction outbound  # Wrong: Use "egress"
--direction in        # Wrong: Use "ingress"
```

---

### Cloud Assistant Command Type

#### ✅ CORRECT
```bash
--type RunShellScript      # For Linux
--type RunPowerShellScript # For Windows
```

#### ❌ INCORRECT
```bash
--type ShellScript        # Wrong: Add "Run" prefix
--type Bash               # Wrong: Use "RunShellScript"
--type PowerShell         # Wrong: Use "RunPowerShellScript"
```

---

## 3. Parameter Confirmation Patterns

### ✅ CORRECT - Confirm before use
```
Agent: I'll help diagnose your ECS instance. Please confirm the following parameters:
- Region ID: cn-hangzhou
- Instance ID: i-bp1234567890abcde

User: Confirmed

Agent: [Proceeds with diagnostics using the confirmed values]
```

### ❌ INCORRECT - Using hardcoded defaults
```
Agent: I'll diagnose the instance in cn-hangzhou region with default VPC settings.
[Proceeds without user confirmation]
```

**Explanation**: All user-specific parameters (RegionId, InstanceId, etc.) must be confirmed with the user before execution.

---

## 4. Credential Handling Patterns

### ✅ CORRECT - Check credential status only
```bash
# Check if credentials are configured
aliyun configure list
```

### ❌ INCORRECT - Reading or displaying credentials
```bash
# NEVER do this - reads credential values
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
cat ~/.aliyun/config.json
aliyun configure get

# NEVER ask user to input credentials directly
read -p "Enter your AccessKey ID: " AK
```

**Explanation**: For security, NEVER read, display, or ask users to input AccessKey/SecretKey directly. Only check if credentials exist.

---

## 5. Output Handling Patterns

### Base64 Decoding for Cloud Assistant

#### ✅ CORRECT - Decode output properly
```bash
# Get invocation result and decode
aliyun ecs describe-invocation-results \
  --region-id cn-hangzhou \
  --invoke-id t-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' \
  | base64 -d
```

#### ❌ INCORRECT - Display without decoding
```bash
# Wrong: Shows Base64 encoded string
aliyun ecs describe-invocation-results \
  --region-id cn-hangzhou \
  --invoke-id t-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output'
```

---

### Base64 Encoding for Command Content

#### ✅ CORRECT - Encode commands before sending
```bash
# Encode command content
COMMAND=$(echo 'df -h' | base64)

aliyun ecs run-command \
  --region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunShellScript \
  --command-content "$COMMAND" \
  --timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - Send plain text commands
```bash
# Wrong: Command content must be Base64 encoded
aliyun ecs run-command \
  --region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunShellScript \
  --command-content "df -h" \
  --timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## 6. Error Handling Patterns

### Permission Errors

#### ✅ CORRECT - Handle permission failures
```
Error: Forbidden.RAM - User not authorized to operate on the specified resource

Action:
1. Read references/ram-policies.md
2. Inform user of required permissions
3. Wait for user to grant permissions
4. Retry after confirmation
```

#### ❌ INCORRECT - Ignore or skip
```
Error: Forbidden.RAM

Action: Skip this check and continue
```

---

### Invalid Instance ID

#### ✅ CORRECT - Validate and inform
```
Error: InvalidInstanceId.NotFound

Action:
1. Inform user the instance ID does not exist in the specified region
2. Ask user to verify the instance ID and region
3. Suggest checking the console or listing instances
```

#### ❌ INCORRECT - Assume and guess
```
Error: InvalidInstanceId.NotFound

Action: Try with a different region automatically
```

---

## 7. Workflow Execution Patterns

### Basic and Deep Diagnostics Separation

#### ✅ CORRECT - Execute Basic Diagnostics first, ask for Deep Diagnostics
```
1. Execute all Basic Diagnostics (read-only APIs)
2. Present Basic Diagnostics results to user
3. Ask: "Would you like to proceed with Deep Diagnostics (System & Service Checks)?"
4. If yes, execute Deep Diagnostics commands
```

#### ❌ INCORRECT - Execute everything without asking
```
1. Execute Basic Diagnostics
2. Automatically execute Deep Diagnostics
3. Present all results
```

**Explanation**: Deep Diagnostics execute commands inside the instance and require explicit user consent.

---

### Command Execution Order

#### ✅ CORRECT - Follow diagnostic workflow
```
Basic Diagnostics:
1. Identify instance
2. Check instance status
3. Query system events
4. Check security groups
5. Check network config
6. Query monitoring data
7. Present summary and ask for Deep Diagnostics

Deep Diagnostics (if approved):
7. System load diagnostics
8. Disk usage diagnostics
9. Network connectivity diagnostics
10. System log diagnostics
11. Process status diagnostics
12. Present final report
```

#### ❌ INCORRECT - Random order or skipping steps
```
1. Query monitoring data
2. Check security groups
3. Skip instance status check
4. Execute Deep Diagnostics without asking
```

---

## 8. Regional Parameters

### ✅ CORRECT - Always specify region
```bash
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]' \
  --user-agent AlibabaCloud-Agent-Skills
```

### ❌ INCORRECT - Omit region or use wrong format
```bash
# Missing region
aliyun ecs describe-instances \
  --instance-ids '["i-xxxxx"]' \
  --user-agent AlibabaCloud-Agent-Skills

# Wrong region format
aliyun ecs describe-instances \
  --region hangzhou \  # Should be: cn-hangzhou
  --instance-ids '["i-xxxxx"]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Explanation**: Region ID is required for most ECS/VPC APIs and must use the full format (e.g., cn-hangzhou, not hangzhou).

---

## 9. JSON Output Parsing

### ✅ CORRECT - Use jq for reliable parsing
```bash
# Extract instance ID
aliyun ecs describe-instances \
  --region-id cn-hangzhou \
  --instance-name "my-instance" \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Instances.Instance[0].InstanceId'

# Extract CPU utilization value
aliyun cms describe-metric-last \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions '[{"instanceId":"i-xxxxx"}]' \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Datapoints' | jq -r '.[0].Average'
```

### ❌ INCORRECT - Use grep/sed/awk on JSON
```bash
# Wrong: Fragile parsing
aliyun ecs describe-instances --region-id cn-hangzhou \
  | grep InstanceId | cut -d'"' -f4
```

**Explanation**: Always use `jq` for JSON parsing to ensure reliability and correctness.

---

## 10. Timeout and Retry Patterns

### Cloud Assistant Command Timeout

#### ✅ CORRECT - Set appropriate timeout
```bash
# Short command: 30-60 seconds
aliyun ecs run-command \
  --region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunShellScript \
  --command-content "$(echo 'uptime' | base64)" \
  --timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills

# Long command: 120-600 seconds
aliyun ecs run-command \
  --region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunShellScript \
  --command-content "$(echo 'du -sh /*' | base64)" \
  --timeout 600 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT - No timeout or too short
```bash
# Missing timeout (may use default)
aliyun ecs run-command \
  --region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunShellScript \
  --command-content "$(echo 'du -sh /*' | base64)" \
  --user-agent AlibabaCloud-Agent-Skills

# Timeout too short for long operation
aliyun ecs run-command \
  --region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --type RunShellScript \
  --command-content "$(echo 'find / -name "*.log"' | base64)" \
  --timeout 10 \  # Too short!
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Testing Checklist

Before considering the skill complete, verify:

- [ ] All CLI commands use plugin mode format (kebab-case)
- [ ] All commands include `--user-agent AlibabaCloud-Agent-Skills`
- [ ] All parameters use correct naming (kebab-case, not PascalCase)
- [ ] Array parameters use correct JSON format
- [ ] Enum values are valid and correct
- [ ] Region ID is always specified
- [ ] User parameters are confirmed before execution
- [ ] Credentials are checked via `aliyun configure list` only
- [ ] Cloud Assistant output is Base64 decoded
- [ ] Cloud Assistant input is Base64 encoded
- [ ] Basic and Deep Diagnostics are properly separated
- [ ] Permission errors trigger help workflow
- [ ] JSON output parsed with `jq`
- [ ] Appropriate timeouts set for commands
- [ ] Diagnostic report follows template format

---

## Related Documentation

- [Aliyun CLI Plugin Mode](https://www.alibabacloud.com/help/cli/user-guide/use-alibaba-cloud-cli-in-plugin-mode)
- [ECS API Reference](https://www.alibabacloud.com/help/ecs/developer-reference/api-overview)
- [Cloud Assistant Documentation](https://www.alibabacloud.com/help/ecs/user-guide/cloud-assistant-overview)
- [Cloud Monitor Metrics](https://www.alibabacloud.com/help/cms/developer-reference/metrics-of-ecs)
