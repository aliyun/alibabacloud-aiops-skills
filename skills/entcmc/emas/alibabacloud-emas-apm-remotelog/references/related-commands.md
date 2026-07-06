# Related CLI Commands for EMAS APM TLog Operations

This document lists all `aliyun` CLI commands used in the EMAS APM Remote Log (TLog) workflow. All commands use the plugin mode format (`aliyun emas-appmonitor <action>`).

## Plugin Installation

```bash
# Install the EMAS APM plugin
aliyun plugin install --names aliyun-cli-emas-appmonitor

# Update all plugins
aliyun plugin update

# Enable automatic plugin installation
aliyun configure set --auto-plugin-install true
```

## Core Commands

### 1. Device Resolution

#### GetTlogDeviceList
Query the list of devices available for remote log retrieval by identity.

```bash
aliyun emas-appmonitor get-tlog-device-list \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  [--user-nick <userNick>] \
  [--utdid <deviceId>] \
  [--keyword <userId|customId>] \
  [--page-index 1] \
  [--page-size 10]
```

#### GetTlogDeviceInfo
Get detailed information about a specific device.

```bash
aliyun emas-appmonitor get-tlog-device-info \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --device-id <deviceId>
```

### 2. Task Management

#### CreateTlogTask
Create a remote log retrieval task.

```bash
aliyun emas-appmonitor create-tlog-task \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --ali-yun-name <operatorName> \
  --days <days> \
  --task-name <taskName> \
  --source-type USER \
  --device-json '<deviceJsonArray>' \
  [--cli-dry-run]
```

#### GetTlogTaskInfo
Query the overall progress and status of a log retrieval task.

```bash
aliyun emas-appmonitor get-tlog-task-info \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --task-id <taskId>
```

#### GetTlogTaskCollections
Query the collection status of each device in a task.

```bash
aliyun emas-appmonitor get-tlog-task-collections \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --task-id <taskId>
```

### 3. Log Query

#### SearchTlog
Search and query log details by device and time window.

```bash
aliyun emas-appmonitor search-tlog \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --device-id <deviceId> \
  --begin-date <beginTimeMillis> \
  --end-date <endTimeMillis> \
  [--page-index 1] \
  [--page-size 100] \
  [--level-json '["debug","info","warning","error"]'] \
  [--keyword <keyword>]
```

#### GetTlogCollectList
Query the list of actively submitted log records.

```bash
aliyun emas-appmonitor get-tlog-collect-list \
  --region cn-shanghai \
  --app-key <appKey> \
  --os <android|iphoneos> \
  --source-type POSITIVE \
  [--page-index 1] \
  [--page-size 20] \
  [--device-id <deviceId>]
```

## Common Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--region` | string | Yes | Region ID, typically `cn-shanghai` |
| `--app-key` | string | Yes | Application key from EMAS console |
| `--os` | string | Yes | Operating system: `android` or `iphoneos` |
| `--task-id` | string | Task operations | Task ID returned from create-tlog-task |
| `--device-id` | string | Log query | Device unique identifier (UTDID) |
| `--begin-date` | string | Log query | Start time in Unix milliseconds (13 digits) |
| `--end-date` | string | Log query | End time in Unix milliseconds (13 digits) |
| `--page-index` | integer | No | Page number, default 1 |
| `--page-size` | integer | No | Page size, default 10 |
| `--level-json` | string | No | Log level filter as JSON array |
| `--keyword` | string | No | Search keyword for filtering |

## API Reference Links

| API | Documentation |
|-----|---------------|
| GetTlogDeviceList | https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogDeviceList |
| GetTlogDeviceInfo | https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogDeviceInfo |
| CreateTlogTask | https://api.aliyun.com/api/emas-appmonitor/2019-06-11/CreateTlogTask |
| GetTlogTaskInfo | https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogTaskInfo |
| GetTlogTaskCollections | https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogTaskCollections |
| SearchTlog | https://api.aliyun.com/api/emas-appmonitor/2019-06-11/SearchTlog |
| GetTlogCollectList | https://api.aliyun.com/api/emas-appmonitor/2019-06-11/GetTlogCollectList |
