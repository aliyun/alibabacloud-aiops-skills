# Acceptance Criteria: alibabacloud-ecs-diagnose

**Scenario**: ECS Instance Comprehensive Diagnostics
**Purpose**: Skill testing acceptance criteria

---

## 1. CLI Command Patterns

### Product Validation

#### ✅ CORRECT - Valid product names

```bash
aliyun ecs describe-instances --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
aliyun vpc describe-vpcs --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
aliyun cms describe-metric-last --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
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
aliyun ecs describe-instances --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
aliyun ecs describe-instance-attribute --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
aliyun ecs describe-instance-status --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
aliyun ecs describe-instance-history-events --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
aliyun ecs describe-security-group-attribute --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
aliyun ecs run-command --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
aliyun ecs describe-invocation-results --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# VPC actions
aliyun vpc describe-vpcs --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
aliyun vpc describe-eip-addresses --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# CMS actions
aliyun cms describe-metric-last --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
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
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Query by instance name
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-name "my-instance" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Query by private IP
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --private-ip-addresses '["192.168.1.10"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Security group query
aliyun ecs describe-security-group-attribute \
  --biz-region-id cn-hangzhou \
  --security-group-id sg-xxxxx \
  --direction ingress \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# System events query
aliyun ecs describe-instance-history-events \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --instance-event-cycle-status.1 Executing \
  --instance-event-cycle-status.2 Inquiring \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Cloud Assistant command execution (--instance-id is a list: space-separated;
# --command-content is PLAINTEXT — the plugin base64-encodes it automatically)
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --type RunShellScript \
  --command-content "uptime" \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Monitoring metrics query (cms plugin 0.9.x has NO --biz-region-id flag)
aliyun cms describe-metric-last \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions '[{"instanceId":"i-xxxxx"}]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

#### ❌ INCORRECT - Invalid parameter names or formats

```bash
# Wrong parameter names (API-style PascalCase)
aliyun ecs describe-instances \
  --RegionId cn-hangzhou \  # Should be: --biz-region-id
  --InstanceIds '["i-xxxxx"]'  # Should be: --instance-ids

# Wrong array format for instance IDs
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids i-xxxxx  # Should be: '["i-xxxxx"]' (JSON array)

# Wrong multiple instance specification (indexed .1/.2 syntax was REMOVED in plugin 0.9.x)
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id.1 i-xxxxx \
  --instance-id.2 i-yyyyy \
  --type RunShellScript \
  --command-content "uptime"   # Wrong: --instance-id.1 fails with `unknown flag`

# Correct way for multiple instances (list, space-separated values)
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx i-yyyyy \
  --type RunShellScript \
  --command-content "uptime"

# Wrong dimensions format
aliyun cms describe-metric-last \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions instanceId:i-xxxxx  # Should be: '[{"instanceId":"i-xxxxx"}]' (JSON)
```

**Explanation**:

1. Plugin mode uses kebab-case for parameter names (--biz-region-id, not --RegionId)
2. Array parameters use JSON format with quotes
3. List parameters take space-separated values (`--instance-id i-xxx i-yyy`); the indexed
   `.1`/`.2` suffix syntax was REMOVED for instance IDs in plugin 0.9.x (some enums such
   as `--instance-event-cycle-status.1` still use it — check each command's `--help`)
4. Dimensions parameter requires JSON format
5. cms commands take NO `--biz-region-id` flag (plugin 0.9.x)

---

### User-Agent Header

#### ✅ CORRECT - Always include user-agent

```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

#### ❌ INCORRECT - Missing user-agent

```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]'
```

**Explanation**: All commands in this skill MUST include `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"` for tracking and analytics.

**`{session-id}` / `{skill-version}` specification:**

- `{session-id}`: a random 32-character lowercase hex string, generated ONCE at skill
  load and reused unchanged for every CLI invocation in that session (e.g. an
  `openssl rand -hex 16` output). Two invocations within one session MUST carry the
  identical `{session-id}`; a new session gets a new one.
- `{skill-version}`: the skill's published version, read once at skill load following
  the skill's Observability rules (current published version: `1.0.0`).
- Local utility commands (`configure`, `plugin`, `version`) do not support `--user-agent`
  and are excluded.

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
  --biz-region-id cn-hangzhou \
  --invoke-id t-xxxxx \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}" \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' \
  | base64 -d
```

#### ❌ INCORRECT - Display without decoding

```bash
# Wrong: Shows Base64 encoded string
aliyun ecs describe-invocation-results \
  --biz-region-id cn-hangzhou \
  --invoke-id t-xxxxx \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}" \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output'
```

---

### Command Content Encoding (input plaintext, output Base64)

> **[MUST] In plugin 0.7.x+ (including 0.9.x), `--command-content` takes the PLAINTEXT
> command string — the plugin Base64-encodes it automatically.** Pre-encoding the input
> causes double encoding: the guest executes the literal Base64 text, the invocation
> still reports `Success` / `ExitCode 0`, and the output is empty — a silent false
> negative that misreports a broken system as healthy. The **response `Output` field**
> is the only part that IS Base64-encoded and must be decoded after retrieval.

#### ✅ CORRECT - Send the plaintext command

```bash
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --type RunShellScript \
  --command-content "df -h" \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

#### ❌ INCORRECT - Base64-encode the command before sending

```bash
# Wrong: double encoding — guest runs the literal base64 string,
# returns Success/ExitCode 0 with EMPTY output (silent false negative)
COMMAND=$(echo 'df -h' | base64)

aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --type RunShellScript \
  --command-content "$COMMAND" \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

---

## 6. Error Handling Patterns

### Permission Errors

#### ✅ CORRECT - Handle permission failures

```
Error: Forbidden.RAM - User not authorized to operate on the specified resource

Action:
1. Identify the missing permission from the error
2. Use `ram-permission-diagnose` to guide the permission request
3. Wait for the user to confirm the grant
4. Retry after confirmation
```

#### ❌ INCORRECT - Ignore or skip

```
Error: Forbidden.RAM

Action: Skip this check and continue
```

---

### Invalid Instance ID / Empty Result

> **[MUST] Follow the Phase 0 empty-result protocol in `SKILL.md` (single source of truth).**
> Cross-region lookup is allowed ONLY with the SAME instance ID (traverse candidate
> regions with BOTH `--region` and `--biz-region-id`). Once the region is confirmed
> and the instance is still not found, STOP — do not enumerate other instances in the
> account and do not suggest the user pick a different one.

#### ✅ CORRECT - Validate and inform

```text
Error: InvalidInstanceId.NotFound / DescribeInstances returns TotalCount = 0

Action:
1. Traverse candidate regions with the SAME instance ID (BOTH --region and --biz-region-id per query)
2. If still not found after traversal: follow the Phase 0 empty-result protocol verbatim
   (terminate workflow, output the fixed message template, ask user to re-check the ID/region)
3. Do NOT list other instances in the account; do NOT switch the diagnostic target
```

#### ❌ INCORRECT - Assume, guess, or substitute

```text
Error: InvalidInstanceId.NotFound

Action: Try with a different region automatically            # Wrong: blind region hopping without the SAME-ID rule
Action: List the account's instances and pick one to diagnose # Wrong: never substitute the user's target
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
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxxxx"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

### ❌ INCORRECT - Omit region or use wrong format

```bash
# Missing region
aliyun ecs describe-instances \
  --instance-ids '["i-xxxxx"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Wrong region format
aliyun ecs describe-instances \
  --region hangzhou \  # Should be: cn-hangzhou
  --instance-ids '["i-xxxxx"]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

**Explanation**: Region ID is required for most ECS/VPC APIs and must use the full format (e.g., cn-hangzhou, not hangzhou).

---

## 9. JSON Output Parsing

### ✅ CORRECT - Use jq for reliable parsing

```bash
# Extract instance ID
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-name "my-instance" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}" \
  | jq -r '.Instances.Instance[0].InstanceId'

# Extract CPU utilization value
aliyun cms describe-metric-last \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions '[{"instanceId":"i-xxxxx"}]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}" \
  | jq -r '.Datapoints' | jq -r '.[0].Average'
```

### ❌ INCORRECT - Use grep/sed/awk on JSON

```bash
# Wrong: Fragile parsing
aliyun ecs describe-instances --biz-region-id cn-hangzhou \
  | grep InstanceId | cut -d'"' -f4
```

**Explanation**: Always use `jq` for JSON parsing to ensure reliability and correctness.

---

## 10. Timeout and Retry Patterns

### Cloud Assistant Command Timeout

#### ✅ CORRECT - Set appropriate timeout

```bash
# Short command: 30-60 seconds (command content is PLAINTEXT)
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --type RunShellScript \
  --command-content "uptime" \
  --timeout 60 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Long command: 120-600 seconds
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --type RunShellScript \
  --command-content "du -sh /*" \
  --timeout 600 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

#### ❌ INCORRECT - No timeout or too short

```bash
# Missing timeout (may use default)
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --type RunShellScript \
  --command-content "du -sh /*" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Timeout too short for long operation
aliyun ecs run-command \
  --biz-region-id cn-hangzhou \
  --instance-id i-xxxxx \
  --type RunShellScript \
  --command-content "find / -name \"*.log\"" \
  --timeout 10 \  # Too short!
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

---

## Testing Checklist

Before considering the skill complete, verify:

- [ ] All CLI commands use plugin mode format (kebab-case)
- [ ] All commands include `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"`
- [ ] All parameters use correct naming (kebab-case, not PascalCase)
- [ ] Array parameters use correct JSON format
- [ ] Enum values are valid and correct
- [ ] Region ID is always specified
- [ ] User parameters are confirmed before execution
- [ ] Credentials are checked via `aliyun configure list` only
- [ ] Cloud Assistant output is Base64 decoded (and polled until per-instance `InvocationStatus` is `Success` first)
- [ ] Cloud Assistant input (`--command-content`) is PLAINTEXT — never pre-encoded
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
