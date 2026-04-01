# Acceptance Criteria: alibabacloud-sas-alert-handler

**Scenario**: Cloud Security Center CWPP Alert Handling
**Purpose**: Skill Testing Acceptance Criteria

---

## Correct CLI Command Patterns

### 1. Product — Verify Product Name Exists

✅ **CORRECT**
```bash
aliyun sas DescribeSuspEvents ...
```

❌ **INCORRECT**
```bash
aliyun security DescribeSuspEvents ...  # Wrong product name
aliyun SAS DescribeSuspEvents ...       # Case error
```

### 2. Command — Verify Command Exists

✅ **CORRECT**
```bash
aliyun sas DescribeSuspEvents
aliyun sas DescribeSecurityEventOperations
aliyun sas HandleSecurityEvents
aliyun sas DescribeSecurityEventOperationStatus
```

❌ **INCORRECT**
```bash
aliyun sas describe-susp-events           # Wrong format (SAS uses PascalCase)
aliyun sas DescribeSuspEvent              # Singular/plural error
aliyun sas HandleSecurityEvent            # Singular/plural error
```

### 3. Parameters — Verify Parameter Names Exist

#### DescribeSuspEvents

✅ **CORRECT**
```bash
aliyun sas DescribeSuspEvents \
  --Lang zh \
  --From sas \
  --CurrentPage 1 \
  --PageSize 10 \
  --Levels "serious,suspicious,remind" \
  --Dealed N \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**
```bash
aliyun sas DescribeSuspEvents \
  --lang zh \                    # Lowercase error, should be --Lang
  --from sas \                   # Lowercase error, should be --From
  --current-page 1 \             # Format error, should be --CurrentPage
  --page-size 10 \               # Format error, should be --PageSize
  --levels "serious" \           # Lowercase error, should be --Levels
  --dealed N                     # Lowercase error, should be --Dealed
```

#### HandleSecurityEvents

✅ **CORRECT**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009607xx \
  --OperationCode block_ip \
  --OperationParams '{"expireTime":1773991205392}' \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds 7009607xx \           # Missing .1 index
  --security-event-ids.1 7009607xx \       # Format error
  --operation-code block_ip \              # Format error, should be --OperationCode
  --operation-params '{"expireTime":1773991205392}'  # Format error
```

### 4. Enum Values — Verify Enum Values Are Valid

#### OperationCode Values

✅ **CORRECT**
```bash
--OperationCode block_ip
--OperationCode advance_mark_mis_info
--OperationCode ignore
--OperationCode manual_handled
--OperationCode kill_and_quara
--OperationCode virus_quara
--OperationCode virus_quara_bin
--OperationCode kill_process
--OperationCode cleanup
--OperationCode quara
--OperationCode rm_mark_mis_info
--OperationCode disable_malicious_defense
```

❌ **INCORRECT**
```bash
--OperationCode blockip                    # Format error, should have underscore
--OperationCode BLOCK_IP                   # Case error
--OperationCode block-ip                   # Format error, should use underscore
--OperationCode advance-mark-mis-info      # Format error
```

#### Levels Values

✅ **CORRECT**
```bash
--Levels "serious"
--Levels "suspicious"
--Levels "remind"
--Levels "serious,suspicious,remind"
```

❌ **INCORRECT**
```bash
--Levels "critical"         # Non-existent level
--Levels "high"             # Non-existent level
--Levels "serious suspicious"  # Separator error, should use comma
```

#### Dealed Values

✅ **CORRECT**
```bash
--Dealed N    # Unhandled
--Dealed Y    # Handled
```

❌ **INCORRECT**
```bash
--Dealed n          # Lowercase error
--Dealed yes        # Format error
--Dealed no         # Format error
--Dealed false      # Format error
```

### 5. Parameter Value Formats — Verify Parameter Value Formats

#### RepeatList Format (Array Parameters)

✅ **CORRECT**
```bash
# Single value
--SecurityEventIds.1 7009607xx

# Multiple values
--SecurityEventIds.1 7009607xx \
--SecurityEventIds.2 7008557xx \
--SecurityEventIds.3 7008619xx
```

❌ **INCORRECT**
```bash
--SecurityEventIds 7009607xx              # Missing index
--SecurityEventIds "[7009607xx]"          # Wrong array format
--SecurityEventIds "7009607xx,7008557xx"  # Wrong separator format
```

#### JSON String Parameters

✅ **CORRECT**
```bash
--OperationParams '{"expireTime":1773991205392}'
--MarkMissParam '[{"uuid":"ALL","field":"loginSourceIp","operate":"strEqual","fieldValue":"59.82.xx.xx"}]'
```

❌ **INCORRECT**
```bash
--OperationParams {"expireTime":1773991205392}    # Missing quotes
--OperationParams "{'expireTime':1773991205392}"  # Single quotes inside
--MarkMissParam "[{uuid:ALL}]"                    # JSON keys missing quotes
```

### 6. user-agent Flag — Verify Must Be Included

✅ **CORRECT** — Every command includes `--user-agent`
```bash
aliyun sas DescribeSuspEvents ... --user-agent AlibabaCloud-Agent-Skills
aliyun sas HandleSecurityEvents ... --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT** — Missing `--user-agent`
```bash
aliyun sas DescribeSuspEvents --Lang zh --From sas
```

---

## Business Logic Validation

### 1. block_ip Must Include expireTime

✅ **CORRECT**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009607xx \
  --OperationCode block_ip \
  --OperationParams '{"expireTime":1773991205392}' \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**
```bash
# Missing expireTime
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009607xx \
  --OperationCode block_ip \
  --OperationParams '{}' \
  --user-agent AlibabaCloud-Agent-Skills
```

### 2. kill_and_quara Must Include subOperation

✅ **CORRECT**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7008619xx \
  --OperationCode kill_and_quara \
  --OperationParams '{"subOperation":"killAndQuaraFileByMd5andPath"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**
```bash
# Missing subOperation
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7008619xx \
  --OperationCode kill_and_quara \
  --OperationParams '{}' \
  --user-agent AlibabaCloud-Agent-Skills
```

### 3. subOperation Value Validation

| operateCode | Valid subOperation Values |
|-------------|---------------------------|
| kill_and_quara | killByMd5andPath, killAndQuaraFileByMd5andPath |
| virus_quara | quaraFileByMd5andPath |
| virus_quara_bin | quaraFileByMd5andPath |

### 4. MarkMissParam Structure Validation

✅ **CORRECT**
```json
[
  {
    "uuid": "ALL",           // or "part"
    "field": "loginSourceIp", // from MarkFieldsSource.FiledName
    "operate": "strEqual",    // from SupportedMisType
    "fieldValue": "59.82.xx.xx"
  }
]
```

❌ **INCORRECT**
```json
// uuid value error
[{"uuid": "all", "field": "loginSourceIp", "operate": "strEqual", "fieldValue": "59.82.xx.xx"}]

// operate value error
[{"uuid": "ALL", "field": "loginSourceIp", "operate": "equals", "fieldValue": "59.82.xx.xx"}]
```

### 5. DescribeSecurityEventOperationStatus Must Pass Both Parameters

✅ **CORRECT** — Pass both TaskId and SecurityEventIds
```bash
aliyun sas DescribeSecurityEventOperationStatus \
  --TaskId 290511xx \
  --SecurityEventIds.1 7009607xx \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT** — Only pass one of them
```bash
# Only pass TaskId (CLI will error)
aliyun sas DescribeSecurityEventOperationStatus \
  --TaskId 290511xx \
  --user-agent AlibabaCloud-Agent-Skills

# Only pass SecurityEventIds (CLI will error)
aliyun sas DescribeSecurityEventOperationStatus \
  --SecurityEventIds.1 7009607xx \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Process Validation

### 1. Must Query UserCanOperate Before Handling

**Correct Process:**
1. Call DescribeSecurityEventOperations to get available operations
2. Check if target operation's UserCanOperate is true
3. Only execute operations where UserCanOperate=true

### 2. Advanced Whitelist Must Preserve Existing Rules

**Correct Process:**
1. Call DescribeSecurityEventOperations to get MarkField (existing rules)
2. Build new rules
3. Merge existing rules + new rules and pass to MarkMissParam

### 3. Poll Status Until Complete

**Correct Process:**
1. Call HandleSecurityEvents to get TaskId
2. Call DescribeSecurityEventOperationStatus to query status
3. If TaskStatus=Processing, wait 2 seconds and retry
4. Maximum 5 retries (10 second timeout)
5. End when TaskStatus=Success or Failure

---

## CLI Unsupported Operations

| Operation | Description |
|-----------|-------------|
| client_problem_check | Problem investigation, requires console operation |

---

## Acceptance Checklist

- [ ] All CLI commands use correct product name `sas`
- [ ] All CLI commands use PascalCase format (e.g., DescribeSuspEvents)
- [ ] All parameter names use PascalCase format (e.g., --SecurityEventIds.1)
- [ ] All enum values use correct format (e.g., block_ip, serious)
- [ ] Array parameters use .N suffix format (e.g., --SecurityEventIds.1)
- [ ] JSON parameters wrapped with single quotes
- [ ] Every command includes `--user-agent AlibabaCloud-Agent-Skills`
- [ ] block_ip operation includes expireTime parameter
- [ ] kill_and_quara/virus_quara/virus_quara_bin includes subOperation parameter
- [ ] Advanced whitelist operation preserves existing rules
- [ ] DescribeSecurityEventOperationStatus passes both TaskId and SecurityEventIds
