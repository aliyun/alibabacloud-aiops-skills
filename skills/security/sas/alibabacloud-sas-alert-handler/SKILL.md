---
name: alibabacloud-sas-alert-handler
description: |
  Alibaba Cloud Security Center (SAS) CWPP host security alert handling skill. Used for querying, analyzing, and handling security alerts from Cloud Security Center.
  Triggers: "security alert", "alert handling", "CWPP alert", "Cloud Security Center alert", "SAS alert", "Aegis alert", "view alerts", "handle alerts"
---

# Cloud Security Center CWPP Alert Handling Skill

## Scenario Description

This skill helps users query and handle CWPP host security alerts from Alibaba Cloud Security Center (SAS/Aegis).

**Core Capabilities:**
- Query security alert list
- Analyze alert details and recommend handling methods
- Execute alert handling operations (ignore, whitelist, block, quarantine, etc.)
- Query handling status and summarize results

**Architecture:** `Alibaba Cloud Security Center (SAS) + RAM Permissions + CLI Tools`

---

## Installation Requirements

> **Pre-check: Aliyun CLI >= 3.3.1**
> Run `aliyun version` to verify version >= 3.3.1. If not installed or version is too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
aliyun version
aliyun configure set --auto-plugin-install true
```

---

## Authentication Configuration

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, output, or print AK/SK values
> - **NEVER** ask users to input AK/SK directly
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile. **If no valid profile exists, STOP here.**

---

## RAM Permission Requirements

| Permission Name | Description |
|-----------------|-------------|
| `yundun-sas:DescribeSuspEvents` | Query alert list |
| `yundun-sas:DescribeSecurityEventOperations` | Query available operations |
| `yundun-sas:HandleSecurityEvents` | Handle alerts |
| `yundun-sas:DescribeSecurityEventOperationStatus` | Query handling status |

For detailed policies, see [references/ram-policies.md](references/ram-policies.md)

> **[MUST] Permission Failure Handling:** When permission errors occur:
> 1. Read `references/ram-policies.md` for required permissions
> 2. Use `ram-permission-diagnose` skill to guide user
> 3. Wait until user confirms permissions granted

---

## Core Workflow

### Step 0: Identify Query Scenario (Critical)

> **⚠️ IMPORTANT: Choose the correct API based on user input**

| Scenario | User Input Example | Correct Approach |
|----------|-------------------|------------------|
| **User specified alert ID** | "Query alert 702173474" | **Directly call** `DescribeSecurityEventOperations --SecurityEventId {ID}` |
| **User did not specify alert ID** | "View my alerts" | Execute Step 1 to query alert list |

**Scenario A: User specified alert ID** → Verify alert exists:
```bash
aliyun sas DescribeSecurityEventOperations \
  --SecurityEventId {AlertID} \
  --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills
```
- **Success** → Alert exists, proceed to Step 5
- **Failure** (`SecurityEventNotExists`) → See [references/error-handling.md](references/error-handling.md)

**Scenario B: User did not specify alert ID** → Proceed to Step 1

---

### Step 1: Query Alert List

```bash
aliyun sas DescribeSuspEvents \
  --Lang zh \
  --From sas \
  --CurrentPage 1 \
  --PageSize 10 \
  --Levels "serious,suspicious,remind" \
  --Dealed N \
  --user-agent AlibabaCloud-Agent-Skills 2>/dev/null | jq '.SuspEvents[] | {Id, Name: .AlarmEventNameDisplay, AlarmEventType, Level, InternetIp, IntranetIp, LastTime, EventStatus, Uuid}'
```

**Key Response Fields:**

| Field | Description |
|-------|-------------|
| Id | Alert event ID (core field) |
| AlarmEventNameDisplay | Alert name |
| AlarmEventType | Alert type |
| Level | Severity (serious/suspicious/remind) |
| EventStatus | 1=pending, 2=ignored, 8=false positive, 32=completed |

---

### Step 2: Display Alert Information and Recommendations

**Display Format:**
```
Alert List (Total X items):

[Alert 1] ID: 7009607xx
- Name: ECS login from unusual location
- Type: Unusual Login
- Severity: suspicious
- Asset: 47.xxx.xxx.xxx / 10.xxx.xxx.xxx
- Status: Pending
- Time: 2026-03-19 14:11:05
- Recommended Action: Block IP
- Reason: Unusual login behavior detected
```

For operateCode mappings and recommendation rules, see [references/operation-codes.md](references/operation-codes.md)

---

### Step 3: Determine Handling Intent

**Case A: User specified handling method** → Proceed to Step 4

**Case B: User did not specify** → **Must ask user:**
```
Please confirm how to handle these alerts:

1. ✅ Handle all using recommended methods
2. 🔧 Custom handling method
3. ❌ Cancel

Please select (enter number):
```

---

### Step 4: Query Available Handling Operations

> **⚠️ Strict Constraint: Each alert's available operations must be queried individually**
> - **NEVER** assume one alert's operations apply to another
> - **MUST** call `DescribeSecurityEventOperations` for each alert

```bash
aliyun sas DescribeSecurityEventOperations \
  --SecurityEventId {AlertID} \
  --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills
```

**⚠️ Critical: Only execute operations where `UserCanOperate=true`**

---

### Step 5: Build Parameters and Execute

**Quick Reference - Common Operations:**

| OperationCode | OperationParams | Notes |
|---------------|-----------------|-------|
| block_ip | `{"expireTime":1773991205392}` | expireTime = current + duration (ms) |
| kill_and_quara | `{"subOperation":"killAndQuaraFileByMd5andPath"}` | |
| virus_quara | `{"subOperation":"quaraFileByMd5andPath"}` | |
| quara | `{}` | |
| ignore | `{}` | |
| manual_handled | `{}` | |
| advance_mark_mis_info | `{}` + MarkMissParam | See workflow-details.md |

**Example - ignore:**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009586xx \
  --OperationCode ignore \
  --OperationParams '{}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example - kill_and_quara:**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7008619xx \
  --OperationCode kill_and_quara \
  --OperationParams '{"subOperation":"killAndQuaraFileByMd5andPath"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example - block_ip (7 days):**
```bash
# Calculate: current_timestamp_ms + 7*24*60*60*1000
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009607xx \
  --OperationCode block_ip \
  --OperationParams '{"expireTime":1773991205392}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example - advance_mark_mis_info:**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009586xx \
  --OperationCode advance_mark_mis_info \
  --OperationParams '{}' \
  --MarkMissParam '[{"uuid":"ALL","field":"loginSourceIp","operate":"strEqual","fieldValue":"59.82.xx.xx"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

> **⚠️ For advanced whitelist (advance_mark_mis_info):**
> - Must ask user about whitelist rules and scope
> - Must preserve existing MarkField rules
> - See [references/workflow-details.md](references/workflow-details.md) for detailed process

For complete CLI examples and parameter details, see [references/workflow-details.md](references/workflow-details.md)

---

### Step 6: Query Handling Status

> **⚠️ CLI Requirement: Must pass both TaskId and SecurityEventIds**

```bash
aliyun sas DescribeSecurityEventOperationStatus \
  --TaskId 290511xx \
  --SecurityEventIds.1 7009607xx \
  --user-agent AlibabaCloud-Agent-Skills
```

**Polling Logic:**
1. `TaskStatus=Processing` → Wait 2s, retry (max 5 times)
2. After 10s still not complete → Mark as failed
3. `TaskStatus=Success` → Handling successful
4. `TaskStatus=Failure` → Check ErrorCode

---

### Step 7: Loop to Handle Other Alerts

If there are other alerts, repeat Steps 3-6. Maximum 20 alerts per batch.

---

### Step 8: Results Summary

```
========== Handling Results Summary ==========

✅ Successfully Handled: 3 items
  [Alert 7009607xx] Block IP - Success

❌ Handling Failed: 1 item
  [Alert 7008557xx] Kill and Quarantine - Failed (AgentOffline)

Total: 4 items, Success 3, Failed 1
```

For detailed format, see [references/error-handling.md](references/error-handling.md)

---

## operateCode Quick Reference

| operateCode | Description | Additional Params |
|-------------|-------------|-------------------|
| block_ip | Block IP | expireTime (required) |
| kill_and_quara | Kill and Quarantine | subOperation (required) |
| virus_quara | Quarantine File | subOperation (required) |
| quara | Quarantine | None |
| advance_mark_mis_info | Advanced Whitelist | MarkMissParam |
| ignore | Ignore | None |
| manual_handled | Mark as Handled | None |
| kill_process | Kill Process | None |

For complete operateCode categories and details, see [references/operation-codes.md](references/operation-codes.md)

---

## Error Handling

| Error Scenario | Handling Method |
|----------------|------------------|
| UserCanOperate=false | Operation not supported, version limitation |
| Timeout (>10s) | Mark as failed, continue next |
| *.AgentOffline | Client offline, cannot handle |
| *.ProcessNotExist | Suggest using virus_quara_bin |
| NoPermission | Contact admin for authorization |
| SecurityEventNotExists | Search in handled alerts first |

For detailed error handling procedures, see [references/error-handling.md](references/error-handling.md)

---

## Best Practices

1. **Query before handling**: Call `DescribeSecurityEventOperations` first
2. **Batch limit**: Maximum 20 alerts per batch
3. **Preserve existing rules**: When using advanced whitelist, merge existing MarkField rules
4. **Timeout handling**: Polling over 10 seconds = failed
5. **User confirmation**: Must confirm intent before handling
6. **Logging**: Record all operations for auditing

---

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/workflow-details.md](references/workflow-details.md) | Detailed workflow, CLI examples, advanced whitelist |
| [references/operation-codes.md](references/operation-codes.md) | Complete operateCode reference |
| [references/error-handling.md](references/error-handling.md) | Error handling procedures |
| [references/related-apis.md](references/related-apis.md) | API parameter details |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/verification-method.md](references/verification-method.md) | Verification methods |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
