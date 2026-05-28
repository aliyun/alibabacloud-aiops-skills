# Acceptance Criteria: ECS Patch Management

**Scenario**: Scan and install OS patches on ECS instances using OOS
**Purpose**: Skill testing acceptance criteria for CLI command patterns and SDK usage

---

# Correct CLI Command Patterns

## 1. Product Verification — verify `oos` product exists
#### ✅ CORRECT
```bash
aliyun oos --help
# Should show OOS (CloudOps Orchestration Service) commands
```

#### ❌ INCORRECT
```bash
aliyun ops --help
# Wrong product name — should be 'oos' not 'ops'
```

## 2. Command Verification — verify `start-execution` action exists
#### ✅ CORRECT
```bash
aliyun oos start-execution --help
# Shows start-execution parameters
```

#### ❌ INCORRECT
```bash
aliyun oos StartExecution --help
# Wrong format — must use plugin mode (lowercase with hyphens), not API mode
```

## 3. Parameters Verification — verify JSON parameters format
#### ✅ CORRECT
```bash
aliyun oos start-execution \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --parameters '{"regionId":"cn-hangzhou","action":"scan","targets":{"ResourceIds":["i-xxx"],"RegionId":"cn-hangzhou","Type":"ResourceIds"}}'
```

#### ❌ INCORRECT
```bash
aliyun oos start-execution \
  --region cn-hangzhou \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --regionId cn-hangzhou \
  --action scan
# Wrong format — parameters must be passed as a single JSON string via --parameters flag
```

## 4. Template Name — must use exact template name
#### ✅ CORRECT
```bash
--template-name ACS-ECS-BulkyApplyPatchBaseline
```

#### ❌ INCORRECT
```bash
--template-name ACS-ECS-BulkyApplyPatchBaselines
--template-name BulkApplyPatchBaseline
--template-name acs-ecs-bulkyapplypatchbaseline
# Template names are case-sensitive and must match exactly
```

## 5. Action Parameter — must be 'scan' or 'install'
#### ✅ CORRECT
```json
{"action": "scan", ...}
{"action": "install", ...}
```

#### ❌ INCORRECT
```json
{"action": "Scan", ...}
{"action": "Install", ...}
{"action": "check", ...}
# Action values are case-sensitive and must be lowercase: 'scan' or 'install'
```

## 6. Targets Format — must use correct JSON structure
#### ✅ CORRECT
```json
{
  "targets": {
    "ResourceIds": ["i-bp1example0000000001"],
    "RegionId": "cn-hangzhou",
    "Type": "ResourceIds"
  }
}
```

#### ❌ INCORRECT
```json
{
  "targets": ["i-bp1example0000000001"]
}
# Missing required fields: RegionId and Type
```

## 7. Region Parameter — use --biz-region-id for OOS
#### ✅ CORRECT
```bash
aliyun oos start-execution \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --parameters '{...}'
```

#### ❌ INCORRECT
```bash
aliyun oos start-execution \
  --regionId cn-hangzhou \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --parameters '{...}'
# --regionId is not a valid parameter for aliyun oos start-execution;
# must use --biz-region-id for the region within parameters
```

## 8. Install Parameters — snapshot and reboot options
#### ✅ CORRECT
```json
{
  "action": "install",
  "rebootIfNeed": true,
  "whetherCreateSnapshot": true,
  "retentionDays": 7
}
```

#### ❌ INCORRECT
```json
{
  "action": "install",
  "rebootIfNeed": "true",
  "whetherCreateSnapshot": "true",
  "retentionDays": "7"
}
# Boolean and numeric values must not be quoted as strings in JSON
```

## 9. Execution Status Check
#### ✅ CORRECT
```bash
aliyun oos list-executions \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --status Success
```

#### ❌ INCORRECT
```bash
aliyun oos list-executions \
  --status success
# Status values are case-sensitive: 'Success' not 'success'
```

---

## Authentication Patterns

### ✅ CORRECT — Verify credentials before CLI invocation
```bash
aliyun configure list
# Check output shows a valid profile (AK, STS, or OAuth identity)
```

### ❌ INCORRECT — Never echo or print AK/SK values
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET
# FORBIDDEN — Never expose credentials in output
```

### ❌ INCORRECT — Never use configure set with literal credentials in session
```bash
aliyun configure set --access-key-id LTAI5tXXXX --access-key-secret XXXX
# FORBIDDEN — Never set credentials directly in the session
```

---

## Error Handling Patterns

### ✅ CORRECT — Handle permission errors
1. Identify the required RAM permissions for the failed action
2. Use `ram-permission-diagnose` skill to guide permission requests
3. Wait for user confirmation before retrying

### ❌ INCORRECT — Ignore permission errors
```bash
# If command fails with Forbidden.RAM, don't silently continue
# Must address permission issues before proceeding
```

---

## Parameter Safety Patterns

### ✅ CORRECT — All user-customizable parameters must be confirmed
```
Parameters requiring user confirmation:
- RegionId (e.g., cn-hangzhou, cn-shanghai)
- Instance IDs (e.g., i-bp1example0000000001)
- Action (scan or install)
- rebootIfNeed (true or false)
- whetherCreateSnapshot (true or false)
- retentionDays (number of days)
```

### ❌ INCORRECT — Never assume default values
```
Do NOT assume:
- Default region is cn-hangzhou
- Default action is scan
- Default rebootIfNeed is false
Always prompt user for these values
```
