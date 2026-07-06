# Verification Method for EMAS APM TLog Operations

This document provides specific verification steps and commands for each stage of the EMAS APM remote log retrieval workflow.

## Step 1: Verify Plugin Installation

### Command
```bash
aliyun plugin list | grep emas-appmonitor
```

### Expected Result
Output should show `aliyun-cli-emas-appmonitor` with version `0.3.1` or higher.

### Failure Handling
If not found, install:
```bash
aliyun plugin install --names aliyun-cli-emas-appmonitor
```

## Step 2: Verify Credentials

### Command
```bash
aliyun configure list
```

### Expected Result
Output shows at least one profile with valid `AccessKeyId` (masked) and `RegionId`.

### Failure Handling
If no valid profile, configure credentials via `aliyun configure` or environment variables. See [cli-installation-guide.md](cli-installation-guide.md).

## Step 3: Verify Device Resolution

### Command
```bash
aliyun emas-appmonitor get-tlog-device-list \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --user-nick <userNick> \
  --page-index 1 \
  --page-size 10
```

### Expected Result
- HTTP status: 200
- Response contains `Success: true`
- `Model.Items` contains at least one device entry (array of camelCase fields)
- Each device entry has: `deviceId`, `appKey`, `appId`, `appVersion`, `userId`, `userName`, `brand`, `deviceModel`, `os`, `osVersion`, `geo`, `ip`, `online`, `clientTime`, `serverTime`, `updateTime`, `conType`

### Verification Checks
- [ ] Response contains `Success: true`
- [ ] `Model.Items` is non-empty when valid userNick/deviceId provided
- [ ] Each entry contains required fields (`deviceId`, `userName`)

## Step 4: Verify Device Detail Query

### Command
```bash
aliyun emas-appmonitor get-tlog-device-info \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --device-id <deviceId>
```

### Expected Result
- HTTP status: 200
- Response contains `Success: true`
- `Model` directly contains device details (no nesting). Fields are **PascalCase**: `Brand`, `DeviceModel`, `Os`, `OsVersion`, `AppKey`, `AppId`, `AppVersion`, `DeviceId`, `UserId`, `UserName`, `Geo`, `Ip`, `ClientTime`, `ServerTime`, `UpdateTime`

### Verification Checks
- [ ] Response contains `Success: true`
- [ ] Device details are complete and match expected device
- [ ] **Note**: `get-tlog-device-info` returns PascalCase fields directly under `Model`, while `get-tlog-device-list` items use camelCase. Don't confuse the two.

## Step 5: Verify Task Creation (Dry-Run)

### Command
```bash
aliyun emas-appmonitor create-tlog-task \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --ali-yun-name <operatorName> \
  --days 1 \
  --task-name <taskName> \
  --source-type USER \
  --device-json '<deviceJson>' \
  --cli-dry-run
```

### Expected Result
- HTTP status: 200
- Output shows the request body/parameters that would be sent
- No actual task is created

### Verification Checks
- [ ] Dry-run output shows correct parameters
- [ ] Device list in request matches intended devices
- [ ] Days, task-name, source-type are correct

## Step 6: Verify Task Creation (Actual)

### Command
```bash
aliyun emas-appmonitor create-tlog-task \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --ali-yun-name <operatorName> \
  --days 1 \
  --task-name <taskName> \
  --source-type USER \
  --device-json '<deviceJson>'
```

### Expected Result
- HTTP status: 200
- Response contains `Success: true`
- `Model` returns a string `taskId` (not a JSON object)

### Verification Checks
- [ ] Response contains `Success: true`
- [ ] `Model` field contains a valid taskId string
- [ ] Save taskId for subsequent operations

## Step 7: Verify Task Status Query

### Command
```bash
aliyun emas-appmonitor get-tlog-task-info \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --task-id <taskId>
```

### Expected Result
- HTTP status: 200
- Response contains `Success: true`
- `Model` directly contains task info (no nesting). Fields are **camelCase**: `taskId` (or `id`), `status`, `createTime`, `modifyTime`, `taskName`, `taskType`, `mode`, `progress`, `sourceType`, `dayNum`, `appKey`, `appId`, `author`, `collectionNums`, `successNums`, `failNums`, `fileNums`, `firstTime`, `succeededTime`, `notifySetting`, `reason`, `templateConfig`

### Status Values (read from `Model.status`)
| Status | Meaning | Action |
|--------|---------|--------|
| `NORMAL` | Task in progress | Continue polling |
| `SUCCEEDED` | Task completed successfully | Proceed to query logs |
| `FAILED` | Task failed | Check error details |
| `SUSPENDED` | Task expired | Task expired |
| `CANCELLED` | Task cancelled | Task cancelled |

### Verification Checks
- [ ] Response contains `Success: true`
- [ ] `Model.status` is a valid enum value
- [ ] `Model.createTime` and `Model.modifyTime` are present (Unix milliseconds)

## Step 8: Verify Device Collection Status

### Command
```bash
aliyun emas-appmonitor get-tlog-task-collections \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --task-id <taskId>
```

### Expected Result
- HTTP status: 200
- Response contains `Success: true`
- Response uses a **two-level nested** structure: `Model.collectionsList[].list[]`
  - `Model.collectionNums` — total number of collection entries (integer)
  - `Model.collectionsList[]` — array of collection groups, each with `name` and `list`
  - `Model.collectionsList[].list[]` — per-device collection records (camelCase fields)
- Each device record under `list[]` has: `deviceId`, `appKey`, `appId`, `appVersion`, `brand`, `deviceModel`, `os`, `osVersion`, `geo`, `status`, `createTime`, `modifyTime`, `expireTime`, `dayNum`, `fileSize`, `id`, `reason`

### Collection Status Values (read from `Model.collectionsList[].list[].status`)
| Status | Meaning | Action |
|--------|---------|--------|
| `START` | Task created, device not yet pulled | Wait |
| `PULL_REPLIED` | Device has task, token not applied | Wait |
| `TOKEN_APPLIED` | Token issued, waiting for upload | Wait |
| `FILE_SENDED` | File metadata saved, waiting for parsing | Wait |
| `FINISHED` | Logs queryable | Query logs |
| `FAIL_OVER` | Collection failed | Investigate |
| `SUSPENDED` | Task expired | Task expired |
| `CANCELLED` | Task cancelled | Task cancelled |

### JMESPath helpers
- All device statuses: `Model.collectionsList[].list[].status`
- Specific device's status: `Model.collectionsList[].list[?deviceId=='<deviceId>'].status | [0]`

### Verification Checks
- [ ] Response contains `Success: true`
- [ ] `Model.collectionsList[].list[]` is non-empty
- [ ] Each device record has a valid `status` enum value
- [ ] At least one device reaches `FINISHED` state for log query

## Step 9: Verify Log Query

### Command
```bash
aliyun emas-appmonitor search-tlog \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --device-id <deviceId> \
  --begin-date <beginTimeMillis> \
  --end-date <endTimeMillis> \
  --page-index 1 \
  --page-size 100
```

### Expected Result
- HTTP status: 200
- Response contains `Success: true`
- `Model.Data` contains log entries (array; may be empty if no logs in the time window)
- Each entry has fields (mixed snake_case + camelCase):
  - Top-level: `app`, `client_time`, `server_time`, `message`, `taskId`, `udid`, `collectionId`, `type`, `sub_type_1`, `sub_type_2`, `md5`
  - Nested `properties`: `level` (e.g. `E`/`W`/`I`/`D`), `module`, `tag`, `type`, `clientTime`, `seq`

### Verification Checks
- [ ] Response contains `Success: true`
- [ ] Time window is valid (begin < end, 13-digit milliseconds)
- [ ] `Model.Data[]` entries contain expected fields (`message`, `properties.level`, `taskId`, `udid`)
- [ ] Pagination works correctly (`--page-index`, `--page-size`)

## Step 10: Verify Active Submission Query

### Command
```bash
aliyun emas-appmonitor get-tlog-collect-list \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --source-type POSITIVE \
  --page-index 1 \
  --page-size 20 \
  --device-id <deviceId>
```

### Expected Result
- HTTP status: 200
- Response contains `Success: true`
- `Model.Items` contains submission records (array; pagination via `Model.PageNum`, `Model.PageSize`, `Model.Pages`, `Model.Total`)
- Each entry has (camelCase): `id`, `taskId`, `taskType`, `deviceId`, `appKey`, `appId`, `appVersion`, `brand`, `deviceModel`, `os`, `osVersion`, `geo`, `author`, `userName`, `sourceType`, `status`, `createTime`, `modifyTime`, `expireTime`, `dayNum`, `fileSize`, `positiveComment`, `requestId`, `sessionId`, `reason`

### Verification Checks
- [ ] Response contains `Success: true`
- [ ] `Model.Items[]` records contain `deviceId`, `createTime`, `status`, `taskId`, `sourceType`
- [ ] **Note**: the `taskId` returned here is a system-generated association ID and CANNOT be queried via `get-tlog-task-info`. Use `deviceId` + a window around `createTime` to call `search-tlog` instead.

---

## Polling Strategy for Task Status

When waiting for task completion, use this polling pattern:

```bash
# Poll every 30 seconds, up to 60 times (30 minutes max)
for i in $(seq 1 60); do
  STATUS=$(aliyun emas-appmonitor get-tlog-task-info \
    --region cn-shanghai \
    --app-key <appKey> \
    --os <android|iphoneos> \
    --task-id <taskId> \
    --cli-query 'Model.status' 2>/dev/null | tr -d '"')

  echo "Attempt $i: Task status = $STATUS"

  if [ "$STATUS" = "SUCCEEDED" ]; then
    echo "Task completed successfully!"
    break
  elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "CANCELLED" ] || [ "$STATUS" = "SUSPENDED" ]; then
    echo "Task ended with status: $STATUS"
    break
  fi

  sleep 30
done
```

> **Note**: Use `--cli-query` (JMESPath) to extract a single field from the JSON response. Field name is **`Model.status`** (lowercase `s`, since `get-tlog-task-info` Model uses camelCase fields).

---

## Common Error Responses and Troubleshooting

| Error Code | Cause | Resolution |
|------------|-------|------------|
| `InvalidAppKey` | AppKey does not exist or is invalid | Verify appKey in EMAS console |
| `InvalidDeviceId` | Device ID not found | Check device ID format, verify device exists |
| `TaskNotFound` | Task ID does not exist | Verify taskId, check if task was deleted |
| `Forbidden.RAM` | Insufficient permissions | Attach required RAM policies (see ram-policies.md) |
| `InvalidParameter` | Parameter format error | Check parameter formats (JSON, timestamps, etc.) |
| `ServiceUnavailable` | Service temporarily unavailable | Retry after a short delay |
