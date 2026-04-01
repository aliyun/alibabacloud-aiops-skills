# Related APIs

## API and CLI Command List

All APIs and CLI commands involved in this skill:

| Product | CLI Command | API Action | Description |
|---------|-------------|------------|-------------|
| SAS | `aliyun sas DescribeSuspEvents` | DescribeSuspEvents | Query security alert list |
| SAS | `aliyun sas DescribeSecurityEventOperations` | DescribeSecurityEventOperations | Query available handling operations for alerts |
| SAS | `aliyun sas HandleSecurityEvents` | HandleSecurityEvents | Execute alert handling operations |
| SAS | `aliyun sas DescribeSecurityEventOperationStatus` | DescribeSecurityEventOperationStatus | Query handling status |

---

## DescribeSuspEvents Parameter Details

Query security alert list

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Lang | String | No | Language type, default zh (zh/en) |
| From | String | No | Data source identifier, fixed as sas |
| CurrentPage | String | No | Current page number, default 1 |
| PageSize | String | No | Items per page, default 10, max 100 |
| Levels | String | No | Alert severity levels, comma-separated (serious,suspicious,remind) |
| Dealed | String | No | Whether handled (N=unhandled, Y=handled) |
| Status | String | No | Alert status code (1=pending, 2=ignored, 32=completed, etc.) |
| Id | Long | No | Alert ID |
| Uuids | String | No | Asset UUID list, comma-separated |
| TimeStart | String | No | Start time (2026-03-01 00:00:00) |
| TimeEnd | String | No | End time (2026-03-20 23:59:59) |

### Response Parameters

| Field | Type | Description |
|-------|------|-------------|
| Id | Long | Alert event ID |
| AlarmUniqueInfo | String | Alert unique identifier |
| AlarmEventNameDisplay | String | Alert event name |
| AlarmEventType | String | Alert type |
| Level | String | Severity (serious/suspicious/remind) |
| InternetIp | String | Public IP |
| IntranetIp | String | Private IP |
| EventStatus | Integer | Event status code |
| LastTime | String | Last occurrence time |
| Uuid | String | Server UUID |

### CLI Example

```bash
aliyun sas DescribeSuspEvents \
  --Lang zh \
  --From sas \
  --CurrentPage 1 \
  --PageSize 20 \
  --Levels "serious,suspicious,remind" \
  --Dealed N \
  --user-agent AlibabaCloud-Agent-Skills 2>/dev/null | jq '.SuspEvents[] | {Id, Name: .AlarmEventNameDisplay, AlarmEventType, Level, InternetIp, IntranetIp, LastTime, EventStatus}'
```

---

## DescribeSecurityEventOperations Parameter Details

Query available handling operations for alerts

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| SecurityEventId | Long | **Yes** | Alert ID |
| Lang | String | No | Language type, default zh |

### Response Parameters

| Field | Type | Description |
|-------|------|-------------|
| OperationCode | String | Handling operation code |
| UserCanOperate | Boolean | Whether current version supports this operation |
| OperationParams | String | Sub-operation configuration parameters (JSON string) |
| MarkFieldsSource | Array | Available whitelist field list |
| MarkField | Array | Existing whitelist rules |

### MarkFieldsSource Structure

| Field | Type | Description |
|-------|------|-------------|
| FiledName | String | Whitelistable field name |
| FiledAliasName | String | Field display name |
| MarkMisValue | String | Current alert value for this field |
| SupportedMisType | Array | Supported match types |

### SupportedMisType Values

| Value | Description |
|-------|-------------|
| contains | Contains |
| notContains | Does not contain |
| regex | Regex match |
| strEqual | Equals |
| strNotEqual | Not equals |
| inIpSegment | IP segment match (IP fields only) |

### CLI Example

```bash
aliyun sas DescribeSecurityEventOperations \
  --SecurityEventId 7009607xx \
  --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## HandleSecurityEvents Parameter Details

Execute alert handling operations

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| SecurityEventIds.N | RepeatList | **Yes** | Alert ID list, max 20 |
| OperationCode | String | **Yes** | Handling operation code |
| OperationParams | String | No | Sub-operation configuration parameters (JSON string) |
| MarkMissParam | String | No | Whitelist rule configuration (JSON string) |

### OperationCode Values

| Value | Description | Additional Parameters |
|-------|-------------|----------------------|
| block_ip | Block IP | expireTime (required) |
| kill_and_quara | Kill and Quarantine | subOperation (required) |
| virus_quara | Virus Quarantine | subOperation (required) |
| virus_quara_bin | Quarantine File | subOperation (required) |
| advance_mark_mis_info | Advanced Whitelist | MarkMissParam (optional) |
| mark_mis_info | Add to Whitelist | None |
| ignore | Ignore | None |
| manual_handled | Mark as Handled | None |
| kill_process | Kill Process | None |
| cleanup | Deep Scan | None |
| quara | Quarantine | None |
| rm_mark_mis_info | Remove from Whitelist | None |
| disable_malicious_defense | Disable Malicious Defense | None |
| client_problem_check | Problem Investigation | **CLI Not Supported** |

### OperationParams Format

**block_ip:**
```json
{"expireTime":1773991205392}
```
- expireTime: Millisecond timestamp, indicating when the IP block expires

**kill_and_quara:**
```json
{"subOperation":"killAndQuaraFileByMd5andPath"}
```
- subOperation options: `killByMd5andPath`, `killAndQuaraFileByMd5andPath`

**virus_quara / virus_quara_bin:**
```json
{"subOperation":"quaraFileByMd5andPath"}
```
- subOperation fixed value: `quaraFileByMd5andPath`

### MarkMissParam Format

```json
[
  {
    "uuid": "ALL",
    "field": "loginSourceIp",
    "operate": "strEqual",
    "fieldValue": "59.82.xx.xx"
  }
]
```

| Field | Description |
|-------|-------------|
| uuid | Scope: ALL (all machines) / part (current machine only) |
| field | Whitelist field name (from MarkFieldsSource.FiledName) |
| operate | Match method (from SupportedMisType) |
| fieldValue | Match value |

### Response Parameters

| Field | Type | Description |
|-------|------|-------------|
| TaskId | Long | Handling task ID |

### CLI Examples

**Block IP:**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009607xx \
  --OperationCode block_ip \
  --OperationParams '{"expireTime":1773991205392}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Kill and Quarantine Virus:**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7008619xx \
  --OperationCode kill_and_quara \
  --OperationParams '{"subOperation":"killAndQuaraFileByMd5andPath"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Advanced Whitelist (with rules):**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009586xx \
  --OperationCode advance_mark_mis_info \
  --OperationParams '{}' \
  --MarkMissParam '[{"uuid":"ALL","field":"loginSourceIp","operate":"strEqual","fieldValue":"59.82.xx.xx"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Ignore:**
```bash
aliyun sas HandleSecurityEvents \
  --SecurityEventIds.1 7009586xx \
  --OperationCode ignore \
  --OperationParams '{}' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## DescribeSecurityEventOperationStatus Parameter Details

Query handling status

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| TaskId | Long | Conditionally Required | Task ID (from HandleSecurityEvents response) |
| SecurityEventIds.N | RepeatList | Conditionally Required | Alert ID list |

**⚠️ CLI Special Requirement: Must pass both TaskId and SecurityEventIds**

### Response Parameters

| Field | Type | Description |
|-------|------|-------------|
| TaskStatus | String | Overall task status |
| SecurityEventOperationStatuses | Array | Status of each alert handling |
| SecurityEventOperationStatuses[].SecurityEventId | Long | Alert ID |
| SecurityEventOperationStatuses[].Status | String | Handling status |
| SecurityEventOperationStatuses[].ErrorCode | String | Error code |

### TaskStatus Values

| Value | Description |
|-------|-------------|
| Pending | Waiting |
| Processing | In progress |
| Success | Successful |
| Failure | Failed |

### Status Values

| Value | Description |
|-------|-------------|
| Processing | In progress |
| Success | Successful |
| Failed | Failed |

### ErrorCode Format

Format: `{OperationType}.{ResultCode}`

**Success Examples:**
- `ignore.Success`
- `kill_and_quara.Success`
- `advance_mark_mis_info.Success`
- `block_ip.Success`

**Failure Examples:**
- `kill_and_quara.ProcessNotExist` - Process does not exist
- `kill_and_quara.AgentOffline` - Client offline
- `block_ip.Failure` - Block failed

### CLI Example

```bash
aliyun sas DescribeSecurityEventOperationStatus \
  --TaskId 290511xx \
  --SecurityEventIds.1 7009607xx \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Parameter Flow Diagram

```
DescribeSuspEvents
    │ Id → SecurityEventId
    ▼
DescribeSecurityEventOperations
    │ OperationCode, MarkFieldsSource, MarkField → MarkMissParam
    ▼
HandleSecurityEvents
    │ TaskId + SecurityEventIds
    ▼
DescribeSecurityEventOperationStatus
```
