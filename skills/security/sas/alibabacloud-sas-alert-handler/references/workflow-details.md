# Workflow Details

This document contains detailed workflow instructions for alert handling operations.

---

## Step 5: Build Handling Parameters - Detailed Guide

### 5.1 OperationParams Format Requirements

> **⚠️ Strict Format Requirement: `OperationParams` must be a valid JSON string**
>
> **Correct Format:**
> ```json
> {"subOperation":"killAndQuaraFileByMd5andPath"}
> ```
>
> **Incorrect Format (common errors):**
> ```
> subOperation:killAndQuaraFileByMd5andPath   ❌ Not JSON
> {subOperation:killAndQuaraFileByMd5andPath}  ❌ Missing quotes
> ```
>
> For CLI calls, wrap with single quotes: `--OperationParams '{"subOperation":"killAndQuaraFileByMd5andPath"}'`
>
> For API/SDK calls, ensure a **JSON string** is passed, not key-value text.

### 5.2 Parameter Requirements by OperationCode

| OperationCode | Required Additional Parameters | Parameter Example (must be JSON format) |
|---------------|--------------------------------|-----------------------------------------|
| block_ip | expireTime (millisecond timestamp) | `{"expireTime":1773991205392}` |
| kill_and_quara | subOperation | `{"subOperation":"killAndQuaraFileByMd5andPath"}` |
| virus_quara | subOperation | `{"subOperation":"quaraFileByMd5andPath"}` |
| virus_quara_bin | subOperation | `{"subOperation":"quaraFileByMd5andPath"}` |
| advance_mark_mis_info | MarkMissParam (optional) | See Advanced Whitelist section |
| Others | None | `{}` (empty JSON object, not empty string) |

### 5.3 subOperation Mapping Table

| operateCode | subOperation Value | Control Type | Options |
|-------------|-------------------|--------------|----------|
| `kill_and_quara` | `killByMd5andPath`, `killAndQuaraFileByMd5andPath` | Radio | Choose 1 of 2 |
| `virus_quara` | `quaraFileByMd5andPath` | Checkbox | 1 option |
| `virus_quara_bin` | `quaraFileByMd5andPath` | Checkbox(disabled) | 1 option (fixed) |

### 5.4 expireTime Calculation Rules

```python
import time

# Block duration options (milliseconds)
DURATION_MAP = {
    "6 hours": 6 * 60 * 60 * 1000,
    "1 day": 24 * 60 * 60 * 1000,
    "7 days": 7 * 24 * 60 * 60 * 1000,
    "30 days": 30 * 24 * 60 * 60 * 1000
}

# Calculate expireTime (millisecond timestamp)
expire_time = int(time.time() * 1000) + DURATION_MAP["7 days"]
```

---

## Advanced Whitelist Operation Process (advance_mark_mis_info)

**⚠️ IMPORTANT: Advanced whitelist requires asking user whether to deploy whitelist rules**

### Step 1: Display existing rules, available fields, and whitelist scope

```
You selected [Advanced Whitelist], please confirm the following configuration:

⚠️ Existing Whitelist Rules (from MarkField):
| Field | Match Rule | Value | Scope |
|-------|------------|-------|-------|
| Rule Link | Contains | fyfhchcg | All Machines |

[Whitelist Fields]
Available whitelist fields (from MarkFieldsSource):
| # | Field Name | Current Value |
|---|------------|---------------|
| 1 | Login Source IP | 140.205.xx.xx |
| 2 | Login Account | root |

Recommended fields: Login Source IP, Login Account

1. ✅ Use recommended fields
2. 🔧 Custom fields (specify field numbers to whitelist, separate with commas)
3. ⏭️ Don't add rules (only whitelist this alert)

[Whitelist Scope]
1. ALL - All machines (future alerts matching rules on all machines will be auto-whitelisted)
2. part - Current machine only

Please select fields and scope (e.g., "Use recommended fields, scope 1")
```

### Step 2: Build MarkMissParam

**⚠️ IMPORTANT: Whitelist rules are full replacement, must preserve existing rules!**

```json
// Final MarkMissParam = Existing rules + New rules
[
  {"uuid":"ALL","field":"ruleLinkUrl","operate":"contains","fieldValue":"fyfhchcg"},
  {"uuid":"ALL","field":"repoName","operate":"strEqual","fieldValue":"o11y-addon-controller"}
]
```

**Conversion Rules:**
- `FiledName` → `field`
- `MarkMisValue` → `fieldValue`
- `SupportedMisType[i]` → `operate` (default strEqual)
- `uuid`: `ALL` (all machines) or `part` (current machine only)

### Match Rule Description

| operate | Description | Use Case |
|---------|-------------|----------|
| strEqual | Equals | Exact match |
| strNotEqual | Not equals | Exclude specific value |
| contains | Contains | Fuzzy match |
| notContains | Does not contain | Exclude containing content |
| regex | Regex match | Complex rules |
| inIpSegment | IP segment match | IP fields only |

---

## CLI Call Examples - Complete Reference

### block_ip (Block IP)
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009607xx \
  --OperationCode block_ip \
  --OperationParams '{"expireTime":1773991205392}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler
```

### kill_and_quara (Kill and Quarantine Virus)
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7008619xx \
  --OperationCode kill_and_quara \
  --OperationParams '{"subOperation":"killAndQuaraFileByMd5andPath"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler
```

### advance_mark_mis_info (Advanced Whitelist + Rules)
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009586xx \
  --OperationCode advance_mark_mis_info \
  --OperationParams '{}' \
  --MarkMissParam '[{"uuid":"ALL","field":"loginSourceIp","operate":"strEqual","fieldValue":"59.82.xx.xx"}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler
```

### ignore (Ignore)
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009586xx \
  --OperationCode ignore \
  --OperationParams '{}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler
```

### manual_handled (Mark as Handled)
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009586xx \
  --OperationCode manual_handled \
  --OperationParams '{}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler
```

### virus_quara (Quarantine File)
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7008619xx \
  --OperationCode virus_quara \
  --OperationParams '{"subOperation":"quaraFileByMd5andPath"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler
```

### quara (Quarantine)
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7008619xx \
  --OperationCode quara \
  --OperationParams '{}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-alert-handler
```

---

## CLI Call Notes

### Array Parameter Format

```bash
# Single alert
--SecurityEventIds.1 7009607xx

# Multiple alerts
--SecurityEventIds.1 7009607xx \
--SecurityEventIds.2 7008557xx \
--SecurityEventIds.3 7008619xx
```

### JSON String Parameters

> **⚠️ Key Reminder: `OperationParams` and `MarkMissParam` must be valid JSON strings**
>
> **Common Errors:**
> - `subOperation:killAndQuaraFileByMd5andPath` ❌ Wrong, this is not JSON
> - `{subOperation:killAndQuaraFileByMd5andPath}` ❌ Wrong, missing quotes
>
> **Correct Format:**
> - `'{"subOperation":"killAndQuaraFileByMd5andPath"}'` ✅ Correct

```bash
# OperationParams must be valid JSON, wrapped with single quotes
--OperationParams '{"expireTime":1773991205392}'
--OperationParams '{"subOperation":"killAndQuaraFileByMd5andPath"}'

# MarkMissParam must also be a JSON array
--MarkMissParam '[{"uuid":"ALL","field":"loginSourceIp","operate":"strEqual","fieldValue":"59.82.xx.xx"}]'

# Other operations pass empty JSON object
--OperationParams '{}'
```

---

## CLI Unsupported Operations

The following operations **cannot be performed via CLI** and require the Alibaba Cloud Console:

| Operation | Description | Console Path |
|-----------|-------------|---------------|
| client_problem_check | Problem Investigation | Cloud Security Center Console → Security Alerts → Details → Problem Investigation |

---

## Batch Processing Notes

- Maximum 20 alerts per batch
- `client_problem_check` (Problem Investigation) is **NOT supported** via CLI
- Save the returned `TaskId` for querying status in the next step
