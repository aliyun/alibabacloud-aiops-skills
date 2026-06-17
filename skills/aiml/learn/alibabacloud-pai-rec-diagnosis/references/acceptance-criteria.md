# Acceptance Criteria: alibabacloud-pai-rec-diagnosis

**Scenario**: PAI-Rec Engine Diagnosis and Configuration Validation
**Purpose**: Skill testing acceptance criteria

This document defines correct and incorrect patterns for the PAI-Rec diagnosis skill to ensure proper implementation and usage.

---

## Correct CLI Command Patterns

### 1. Product Names — Verify product name exists

#### ✅ CORRECT

```bash
# EAS product commands
aliyun eas describe-service --cluster-id cn-hangzhou --service-name test
aliyun eas describe-service-log --cluster-id cn-hangzhou --service-name test

# PAI-RecService product commands
aliyun pairecservice list-engine-configs --instance-id pairec-cn-xxxxx
aliyun pairecservice get-engine-config --instance-id pairec-cn-xxxxx --engine-config-id config-123
```

**Why correct:** Uses valid product names `eas` and `pairecservice` that exist in Aliyun CLI.

#### ❌ INCORRECT

```bash
# Wrong product names
aliyun pai-eas describe-service ...        # Product is 'eas', not 'pai-eas'
aliyun rec describe-service ...            # Product is 'pairecservice', not 'rec'
aliyun pairec list-engine-configs ...      # Product is 'pairecservice', not 'pairec'
aliyun pai list-engine-configs ...         # Product is 'pairecservice', not 'pai'
```

**Why incorrect:** These product names don't exist in the Aliyun CLI.

---

### 2. Command Names — Verify action exists under the product

#### ✅ CORRECT

```bash
# EAS commands
aliyun eas describe-service
aliyun eas describe-service-log

# PAI-RecService commands
aliyun pairecservice list-engine-configs
aliyun pairecservice get-engine-config
aliyun pairecservice apply-engine-config
aliyun pairecservice create-engine-config
aliyun pairecservice get-experiment-group
aliyun pairecservice get-experiment
```

**Why correct:** All commands use lowercase words connected with hyphens (plugin mode format).

#### ❌ INCORRECT

```bash
# Traditional API format (not plugin mode)
aliyun eas DescribeService                  # Use describe-service
aliyun eas DescribeServiceLog               # Use describe-service-log
aliyun pairecservice ListEngineConfigs      # Use list-engine-configs
aliyun pairecservice GetEngineConfig        # Use get-engine-config

# Wrong command names
aliyun eas get-service                      # Command is describe-service
aliyun eas list-logs                        # Command is describe-service-log
aliyun pairecservice get-configs            # Command is list-engine-configs
aliyun pairecservice describe-config        # Command is get-engine-config
```

**Why incorrect:** Must use plugin mode format (lowercase with hyphens), and exact command names.

---

### 3. Parameter Names — Verify each parameter exists for the command

#### ✅ CORRECT - EAS describe-service

```bash
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall \
  --region cn-hangzhou
```

**Parameters:**
- `--cluster-id`: Required, the cluster ID
- `--service-name`: Required, the service name
- `--region`: Optional, region override

#### ✅ CORRECT - EAS describe-service-log

```bash
aliyun eas describe-service-log \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall \
  --keyword "941b4e14-d1c5-489f-a184-b2b17f8b4fdb" \
  --start-time "2025-04-28T08:00:00Z" \
  --end-time "2025-04-28T09:00:00Z" \
  --page-num 1 \
  --page-size 500
```

**Parameters:**
- `--cluster-id`: Required
- `--service-name`: Required
- `--keyword`: Optional, filter keyword
- `--start-time`: Optional, UTC format
- `--end-time`: Optional, UTC format
- `--page-num`: Optional, default 1
- `--page-size`: Optional, default 500

#### ✅ CORRECT - PAI-RecService list-engine-configs

```bash
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Prod \
  --name my_config \
  --status Released \
  --version v1.2.3 \
  --page-number 1 \
  --page-size 20
```

**Parameters:**
- `--instance-id`: Required
- `--environment`: Optional, valid values: `Prod` or `Pre`
- `--name`: Optional, config name filter
- `--status`: Optional, e.g., `Released`, `Draft`, `Archived`
- `--version`: Optional
- `--page-number`: Optional
- `--page-size`: Optional

#### ✅ CORRECT - PAI-RecService get-engine-config

```bash
aliyun pairecservice get-engine-config \
  --instance-id pairec-cn-xxxxx \
  --engine-config-id config-12345
```

**Parameters:**
- `--instance-id`: Required
- `--engine-config-id`: Required

#### ✅ CORRECT - PAI-RecService get-experiment-group

```bash
aliyun pairecservice get-experiment-group \
  --instance-id pairec-cn-xxxxx \
  --experiment-group-id 21
```

**Parameters:**
- `--instance-id`: Required
- `--experiment-group-id`: Required, numeric ID extracted from experiment_id string (EG{id} pattern)

#### ✅ CORRECT - PAI-RecService get-experiment

```bash
aliyun pairecservice get-experiment \
  --instance-id pairec-cn-xxxxx \
  --experiment-id 44
```

**Parameters:**
- `--instance-id`: Required
- `--experiment-id`: Required, numeric ID extracted from experiment_id string (E{id} pattern)

#### ❌ INCORRECT - Wrong parameter names

```bash
# EAS describe-service - wrong parameters
aliyun eas describe-service \
  --cluster cn-hangzhou \              # Use --cluster-id
  --name embedding_recall              # Use --service-name

# EAS describe-service-log - wrong parameters
aliyun eas describe-service-log \
  --cluster-id cn-hangzhou \
  --service-name test \
  --search-keyword "test" \            # Use --keyword
  --from "2025-04-28T08:00:00Z" \      # Use --start-time
  --to "2025-04-28T09:00:00Z" \        # Use --end-time
  --page 1 \                           # Use --page-num
  --limit 500                          # Use --page-size

# PAI-RecService list-engine-configs - wrong parameters
aliyun pairecservice list-engine-configs \
  --instance pairec-cn-xxxxx \         # Use --instance-id
  --env Prod \                         # Use --environment
  --config-name my_config \            # Use --name
  --page 1                             # Use --page-number

# PAI-RecService get-engine-config - wrong parameters
aliyun pairecservice get-engine-config \
  --instance pairec-cn-xxxxx \         # Use --instance-id
  --config-id config-12345             # Use --engine-config-id

# PAI-RecService get-experiment-group - wrong parameters
aliyun pairecservice get-experiment-group \
  --instance pairec-cn-xxxxx \         # Use --instance-id
  --group-id 21                        # Use --experiment-group-id

# PAI-RecService get-experiment - wrong parameters
aliyun pairecservice get-experiment \
  --instance pairec-cn-xxxxx \         # Use --instance-id
  --exp-id 44                          # Use --experiment-id
```

**Why incorrect:** Parameter names must match exactly as defined in `--help` output.

---

### 4. Parameter Values — Verify format and enum values

#### ✅ CORRECT - Environment parameter values

```bash
# Environment must be "Prod" or "Pre" (case-sensitive)
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Prod

aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Pre
```

**Valid values:** `Prod`, `Pre` (capitalized)

#### ❌ INCORRECT - Wrong environment values

```bash
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment product            # Use Prod

aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment prepub             # Use Pre

aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment prod               # Use Prod (capital P)

aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment pre                # Use Pre (capital P)
```

#### ✅ CORRECT - Time format (UTC)

```bash
aliyun eas describe-service-log \
  --start-time "2025-04-28T08:00:00Z" \
  --end-time "2025-04-28T09:00:00Z"
```

**Format:** ISO 8601 UTC format with 'Z' suffix

#### ❌ INCORRECT - Wrong time formats

```bash
aliyun eas describe-service-log \
  --start-time "2025-04-28 08:00:00" \        # Missing 'T' and 'Z'
  --end-time "04/28/2025 09:00:00"            # Wrong format

aliyun eas describe-service-log \
  --start-time "2025-04-28T16:00:00+08:00" \  # Use UTC, not local timezone
  --end-time "2025-04-28T17:00:00+08:00"
```

---

### 5. Per-command --user-agent (Observability)

#### ✅ CORRECT

```bash
# Session-id is a 32-char lowercase hex string generated once per session
# Every aliyun API command includes --user-agent with session-id
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

#### ❌ INCORRECT

```bash
# Missing --user-agent flag
aliyun eas describe-service --cluster-id cn-hangzhou --service-name test

# Wrong user-agent format (missing session-id)
aliyun eas describe-service --cluster-id cn-hangzhou --service-name test \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis

# Using quoted user-agent value (should not be quoted)
aliyun eas describe-service --cluster-id cn-hangzhou --service-name test \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/a1b2c3d4"
```

---

### 6. Plugin Management Commands

#### ✅ CORRECT

```bash
# Enable auto plugin install
aliyun configure set --auto-plugin-install true

# Update plugins
aliyun plugin update
```

#### ❌ INCORRECT

```bash
# Wrong command
aliyun plugin install --auto           # Use configure set
aliyun update-plugins                   # Use plugin update
```

---

## Correct Workflow Patterns

### 1. Diagnosis Workflow

#### ✅ CORRECT - Complete workflow

```bash
# 1. Session-id is a 32-char lowercase hex string generated once per session
# Example: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6

# 2. Get service information
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6

# 3. Query service logs by request_id
aliyun eas describe-service-log \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall \
  --keyword "941b4e14-d1c5-489f-a184-b2b17f8b4fdb" \
  --page-size 500 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6

# 4. List engine configs
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Prod \
  --status Released \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6

# 5. Get specific config
aliyun pairecservice get-engine-config \
  --instance-id pairec-cn-xxxxx \
  --engine-config-id config-12345 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

**Why correct:**
- Session-id is a 32-char lowercase hex string generated once per session
- Every API command includes --user-agent (without quotes) with session-id
- Local utility commands (configure, plugin, version) excluded
- Logical sequence of operations
- Proper parameter usage

#### ❌ INCORRECT - Missing steps or wrong order

```bash
# Missing --user-agent (no observability)
aliyun eas describe-service --cluster-id cn-hangzhou --service-name test

# Wrong environment mapping (using "product" instead of "Prod")
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment product
```

---

### 2. Configuration Validation Workflow

#### ✅ CORRECT

```bash
# 1. Session-id is a 32-char lowercase hex string generated once per session
# Example: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6

# 2. List config versions (if user didn't provide ID)
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Prod \
  --name my_config \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6

# 3. Get specific config for validation
aliyun pairecservice get-engine-config \
  --instance-id pairec-cn-xxxxx \
  --engine-config-id config-12345 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

#### ❌ INCORRECT

```bash
# Skipping version listing when user didn't provide ID
# (Should list versions for user to choose)

# Using wrong status filter
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --status Active                    # Use Released, Draft, or Archived
```

---

## Correct Environment Mapping

#### ✅ CORRECT

| Service Environment Variable | CLI Parameter Value |
|------------------------------|---------------------|
| `PAIREC_ENVIRONMENT=product` | `--environment Prod` |
| `PAIREC_ENVIRONMENT=prepub`  | `--environment Pre`  |

```bash
# From service config: PAIREC_ENVIRONMENT=product
# Map to CLI parameter:
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Prod

# From service config: PAIREC_ENVIRONMENT=prepub
# Map to CLI parameter:
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Pre
```

#### ❌ INCORRECT

```bash
# Using service env value directly (wrong)
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment product            # Should be Prod

aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment prepub             # Should be Pre
```

---

## Correct Parameter Confirmation Patterns

#### ✅ CORRECT - Confirm before execution

```
Before executing, please confirm the following parameters:
- Cluster ID: cn-hangzhou
- Service Name: embedding_recall
- Instance ID: pairec-cn-xxxxx
- Environment: Prod (mapped from "product")
- Time Range: 2025-04-28 08:00:00 to 09:00:00 UTC

Proceed? (yes/no)
```

#### ❌ INCORRECT - Using hardcoded or assumed values

```bash
# Hardcoded region without confirmation
aliyun eas describe-service \
  --cluster-id cn-hangzhou \           # Never assume
  --service-name embedding_recall

# Assumed time range without asking user
--start-time "2025-04-28T00:00:00Z" \  # Should confirm with user
--end-time "2025-04-28T23:59:59Z"
```

---

## Correct Error Handling Patterns

#### ✅ CORRECT - Handle errors gracefully

```bash
# Check if command succeeded
if ! SERVICE_INFO=$(aliyun eas describe-service --cluster-id cn-hangzhou --service-name test --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 2>&1); then
  echo "Error: Failed to retrieve service information"
  echo "Details: $SERVICE_INFO"
  exit 1
fi
```

**Why correct:** Includes --user-agent for observability and handles errors gracefully.

#### ❌ INCORRECT - No error handling

```bash
# No error checking
SERVICE_INFO=$(aliyun eas describe-service --cluster-id cn-hangzhou --service-name test)

# Process results without checking if command succeeded
# (May fail silently or with confusing errors)
```

---

## Correct Time Range Patterns

#### ✅ CORRECT - Appropriate time windows

```bash
# For specific issue diagnosis (±30 min to ±1 hour)
--start-time "2025-04-28T08:00:00Z" \
--end-time "2025-04-28T09:00:00Z"

# For pattern analysis (last 1-24 hours)
--start-time "2025-04-27T08:00:00Z" \
--end-time "2025-04-28T08:00:00Z"

# For recent issues (last hour)
START_TIME=$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ')
END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

#### ❌ INCORRECT - Inappropriate time windows

```bash
# Too broad (entire year - too many logs)
--start-time "2025-01-01T00:00:00Z" \
--end-time "2025-12-31T23:59:59Z"

# Too narrow (1 minute - may miss logs)
--start-time "2025-04-28T08:15:00Z" \
--end-time "2025-04-28T08:16:00Z"

# Wrong timezone (not UTC)
--start-time "2025-04-28T16:00:00+08:00"
```

---

## Verification Patterns

#### ✅ CORRECT - Verify results

```bash
# Check if service info contains required fields
if echo "$SERVICE_INFO" | jq -e '.Resource' > /dev/null; then
  echo "✅ Service info retrieved successfully"
else
  echo "❌ Failed to get service resource ID"
fi

# Check if logs found
LOG_COUNT=$(echo "$LOGS" | jq -r '.TotalCount // 0')
if [ "$LOG_COUNT" -gt 0 ]; then
  echo "✅ Found $LOG_COUNT log entries"
else
  echo "❌ No logs found for request_id"
fi

# Check if configs exist
CONFIG_COUNT=$(echo "$CONFIGS" | jq -r '.EngineConfigs | length')
if [ "$CONFIG_COUNT" -gt 0 ]; then
  echo "✅ Found $CONFIG_COUNT configurations"
else
  echo "❌ No configurations found"
fi
```

#### ❌ INCORRECT - No verification

```bash
# Assume commands always succeed
SERVICE_INFO=$(aliyun eas describe-service ...)
# Process without checking if result is valid

# No check if logs/configs found
# May process empty results
```

---

## Summary Checklist

### CLI Commands
- [ ] Use correct product names: `eas`, `pairecservice`
- [ ] Use plugin mode format: lowercase with hyphens
- [ ] Use exact parameter names from `--help`
- [ ] Use correct enum values (e.g., `Prod`/`Pre`, not `product`/`prepub`)
- [ ] Use UTC time format: `YYYY-MM-DDTHH:MM:SSZ`

### Workflow
- [ ] Generate session-id (32-char lowercase hex) at start
- [ ] Include `--user-agent` on every `aliyun` API command
- [ ] Exclude `--user-agent` from local utility commands (configure, plugin, version)
- [ ] Confirm parameters with user before execution
- [ ] Execute commands in logical order

### Environment Mapping
- [ ] Map `product` → `Prod`
- [ ] Map `prepub` → `Pre`

### Error Handling
- [ ] Check command success
- [ ] Handle errors gracefully

### Verification
- [ ] Verify command results
- [ ] Check required fields present
- [ ] Validate data formats
- [ ] Confirm counts when listing

---

## Related Documentation

- [Related Commands](related-commands.md) - Full CLI command reference
- [Verification Method](verification-method.md) - Detailed verification steps
- [Troubleshooting Guide](troubleshooting-guide.md) - Common issues and solutions
