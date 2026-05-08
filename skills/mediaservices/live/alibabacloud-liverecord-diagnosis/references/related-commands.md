# Related CLI Commands

This document lists all Alibaba Cloud CLI commands used in the Live Recording Diagnostic Skill.

## Command Summary

| Category | Command | Description |
|----------|---------|-------------|
| Domain | `aliyun live describe-live-domain-mapping` | Query domain mappings |
| Recording | `aliyun live describe-live-stream-record-content` | Query recording content |
| Recording | `aliyun live describe-live-stream-record-index-files` | Query recording index files |
| Configuration | `aliyun live describe-live-record-config` | Query OSS recording configuration |
| Configuration | `aliyun live describe-live-record-vod-configs` | Query VOD recording configuration |
| Configuration | `aliyun live describe-live-record-notify-config` | Query callback configuration |
| Stream | `aliyun live describe-live-streams-online-list` | Query online streams |
| Stream | `aliyun live describe-live-streams-publish-list` | Query stream publish history |
| Stream | `aliyun live describe-live-center-stream-rate-data` | Query stream rate data |
| Callback | `aliyun live describe-live-record-notify-records` | Query callback records |

---

## Domain Commands

### describe-live-domain-mapping

**Purpose**: Query the mappings between ingest domain, main playback domain, and sub-playback domains.

**Syntax**:
```bash
aliyun live describe-live-domain-mapping \
  --domain-name <DomainName> \
  [--biz-region-id <RegionId>]
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The domain name (ingest, main playback, or sub-playback) |
| `--biz-region-id` | String | No | The business region ID |

**Example**:
```bash
aliyun live describe-live-domain-mapping \
  --domain-name play.example.com
```

**Sample Output**:
```json
{
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8",
  "DomainMapping": {
    "PullDomain": "play.example.com",
    "PushDomain": "push.example.com"
  }
}
```

---

## Recording Commands

### describe-live-stream-record-content

**Purpose**: Query the recordings of a live stream.

**Syntax**:
```bash
aliyun live describe-live-stream-record-content \
  --domain-name <DomainName> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The main playback domain |
| `--app-name` | String | Yes | The application name |
| `--stream-name` | String | Yes | The stream name |
| `--start-time` | String | Yes | Start time in ISO 8601 format (UTC) |
| `--end-time` | String | Yes | End time in ISO 8601 format (UTC) |

**Example**:
```bash
aliyun live describe-live-stream-record-content \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T00:00:00Z \
  --end-time 2025-01-21T00:00:00Z
```

**Sample Output**:
```json
{
  "RecordContentInfoList": {
    "RecordContentInfo": [
      {
        "OssObjectPrefix": "record/live/stream123/",
        "StartTime": "2025-01-20T10:00:00Z",
        "EndTime": "2025-01-20T11:00:00Z",
        "Duration": 3600,
        "Format": "m3u8"
      }
    ]
  },
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8"
}
```

---

### describe-live-stream-record-index-files

**Purpose**: Query all index files within a specific time range.

**Syntax**:
```bash
aliyun live describe-live-stream-record-index-files \
  --domain-name <DomainName> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime> \
  [--page-num <PageNum>] \
  [--page-size <PageSize>]
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The main playback domain |
| `--app-name` | String | Yes | The application name |
| `--stream-name` | String | Yes | The stream name |
| `--start-time` | String | Yes | Start time in ISO 8601 format (UTC) |
| `--end-time` | String | Yes | End time in ISO 8601 format (UTC) |
| `--page-num` | Integer | No | Page number (default: 1) |
| `--page-size` | Integer | No | Records per page (default: 10, max: 100) |

**Example**:
```bash
aliyun live describe-live-stream-record-index-files \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T00:00:00Z \
  --end-time 2025-01-21T00:00:00Z \
  --page-size 20
```

**Sample Output**:
```json
{
  "RecordIndexInfoList": {
    "RecordIndexInfo": [
      {
        "RecordUrl": "http://bucket.oss-cn-hangzhou.aliyuncs.com/record/live/stream123.m3u8",
        "RecordId": "c4d7f0a4-b506-43f9-8de3-07732c3f****",
        "CreateTime": "2025-01-20T10:00:00Z",
        "EndTime": "2025-01-20T11:00:00Z",
        "Duration": 3600,
        "Height": 1080,
        "Width": 1920,
        "Format": "m3u8"
      }
    ]
  },
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8"
}
```

---

## Configuration Commands

### describe-live-record-config

**Purpose**: Query all recording configurations of an application for a streaming domain.

**Syntax**:
```bash
aliyun live describe-live-record-config \
  --domain-name <DomainName> \
  [--app-name <AppName>] \
  [--stream-name <StreamName>] \
  [--page-num <PageNum>] \
  [--page-size <PageSize>] \
  [--order <Order>]
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The main playback domain |
| `--app-name` | String | No | The application name |
| `--stream-name` | String | No | The stream name |
| `--page-num` | Integer | No | Page number (default: 1) |
| `--page-size` | Integer | No | Records per page (5-30, default: 10) |
| `--order` | String | No | Sort order: asc or desc (default: asc) |

**Example**:
```bash
aliyun live describe-live-record-config \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123
```

**Sample Output**:
```json
{
  "LiveAppRecordList": {
    "LiveAppRecord": [
      {
        "AppName": "live",
        "StreamName": "stream123",
        "OssBucket": "my-bucket",
        "OssEndpoint": "oss-cn-hangzhou.aliyuncs.com",
        "OssObjectPrefix": "record/{AppName}/{StreamName}/",
        "OnDemond": 0,
        "RecordFormat": [
          {
            "Format": "m3u8",
            "CycleDuration": 3600
          },
          {
            "Format": "mp4",
            "CycleDuration": 1800
          }
        ],
        "CreateTime": "2025-01-15T10:00:00Z"
      }
    ]
  },
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8"
}
```

---

### describe-live-record-vod-configs

**Purpose**: Query Live-to-VOD configurations.

**Syntax**:
```bash
aliyun live describe-live-record-vod-configs \
  --domain-name <DomainName> \
  [--app-name <AppName>] \
  [--stream-name <StreamName>] \
  [--page-num <PageNum>] \
  [--page-size <PageSize>]
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The main playback domain |
| `--app-name` | String | No | The application name |
| `--stream-name` | String | No | The stream name |
| `--page-num` | Integer | No | Page number (default: 1) |
| `--page-size` | Integer | No | Records per page (default: 10) |

**Example**:
```bash
aliyun live describe-live-record-vod-configs \
  --domain-name play.example.com \
  --app-name live
```

**Sample Output**:
```json
{
  "LiveRecordVodConfigs": {
    "LiveRecordVodConfig": [
      {
        "AppName": "live",
        "StreamName": "stream123",
        "VodTranscodeGroupId": "e2d796d3d5c6472b8c35a****",
        "CycleDuration": 3600,
        "CreateTime": "2025-01-15T10:00:00Z"
      }
    ]
  },
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8"
}
```

---

### describe-live-record-notify-config

**Purpose**: Query the configuration of callbacks for a streaming domain.

**Syntax**:
```bash
aliyun live describe-live-record-notify-config \
  --domain-name <DomainName>
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The main playback domain |

**Example**:
```bash
aliyun live describe-live-record-notify-config \
  --domain-name play.example.com
```

**Sample Output**:
```json
{
  "LiveRecordNotifyConfig": {
    "DomainName": "play.example.com",
    "NotifyUrl": "https://callback.example.com/live/record",
    "NeedStatusNotify": true,
    "OnDemandUrl": "https://callback.example.com/live/ondemand"
  },
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8"
}
```

---

## Stream Commands

### describe-live-streams-online-list

**Purpose**: Query information about all active streams.

**Syntax**:
```bash
aliyun live describe-live-streams-online-list \
  --domain-name <DomainName> \
  [--app-name <AppName>] \
  [--stream-name <StreamName>] \
  [--page-num <PageNum>] \
  [--page-size <PageSize>]
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The main playback domain |
| `--app-name` | String | No | The application name |
| `--stream-name` | String | No | The stream name |
| `--page-num` | Integer | No | Page number (default: 1) |
| `--page-size` | Integer | No | Records per page (default: 10, max: 100) |

**Example**:
```bash
aliyun live describe-live-streams-online-list \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123
```

**Sample Output**:
```json
{
  "OnlineInfo": {
    "LiveStreamOnlineInfo": [
      {
        "StreamName": "stream123",
        "AppName": "live",
        "DomainName": "play.example.com",
        "PublishTime": "2025-01-20T10:00:00Z",
        "PublishUrl": "rtmp://push.example.com/live/stream123"
      }
    ]
  },
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8"
}
```

---

### describe-live-streams-publish-list

**Purpose**: Query the stream ingest records of a domain name.

**Syntax**:
```bash
aliyun live describe-live-streams-publish-list \
  --domain-name <DomainName> \
  [--app-name <AppName>] \
  [--stream-name <StreamName>] \
  [--start-time <StartTime>] \
  [--end-time <EndTime>] \
  [--page-num <PageNum>] \
  [--page-size <PageSize>]
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The main playback domain |
| `--app-name` | String | No | The application name |
| `--stream-name` | String | No | The stream name |
| `--start-time` | String | No | Start time in ISO 8601 format (UTC) |
| `--end-time` | String | No | End time in ISO 8601 format (UTC) |
| `--page-num` | Integer | No | Page number (default: 1) |
| `--page-size` | Integer | No | Records per page (default: 10, max: 100) |

**Example**:
```bash
aliyun live describe-live-streams-publish-list \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T00:00:00Z \
  --end-time 2025-01-21T00:00:00Z
```

**Sample Output**:
```json
{
  "PublishInfo": {
    "LiveStreamPublishInfo": [
      {
        "StreamName": "stream123",
        "AppName": "live",
        "DomainName": "play.example.com",
        "PublishTime": "2025-01-20T10:00:00Z",
        "StopTime": "2025-01-20T11:00:00Z",
        "PublishUrl": "rtmp://push.example.com/live/stream123"
      }
    ]
  },
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8"
}
```

---

### describe-live-center-stream-rate-data

**Purpose**: Query the audio and video frame rates and bitrates.

**Syntax**:
```bash
aliyun live describe-live-center-stream-rate-data \
  --domain-name <DomainName> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  [--start-time <StartTime>] \
  [--end-time <EndTime>]
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The main playback domain |
| `--app-name` | String | Yes | The application name |
| `--stream-name` | String | Yes | The stream name |
| `--start-time` | String | No | Start time in ISO 8601 format (UTC) |
| `--end-time` | String | No | End time in ISO 8601 format (UTC) |

**Example**:
```bash
aliyun live describe-live-center-stream-rate-data \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T10:00:00Z \
  --end-time 2025-01-20T11:00:00Z
```

**Sample Output**:
```json
{
  "StreamRateDataList": {
    "StreamRateData": [
      {
        "Time": "2025-01-20T10:00:00Z",
        "AudioFrameRate": 25,
        "VideoFrameRate": 30,
        "AudioBitrate": 128000,
        "VideoBitrate": 2000000
      },
      {
        "Time": "2025-01-20T10:05:00Z",
        "AudioFrameRate": 0,
        "VideoFrameRate": 30,
        "AudioBitrate": 0,
        "VideoBitrate": 2000000
      }
    ]
  },
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8"
}
```

---

## Callback Commands

### describe-live-record-notify-records

**Purpose**: Query the recording callback records.

**Syntax**:
```bash
aliyun live describe-live-record-notify-records \
  --domain-name <DomainName> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  [--start-time <StartTime>] \
  [--end-time <EndTime>] \
  [--page-num <PageNum>] \
  [--page-size <PageSize>]
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain-name` | String | Yes | The main playback domain |
| `--app-name` | String | Yes | The application name |
| `--stream-name` | String | Yes | The stream name |
| `--start-time` | String | No | Start time in ISO 8601 format (UTC) |
| `--end-time` | String | No | End time in ISO 8601 format (UTC) |
| `--page-num` | Integer | No | Page number (default: 1) |
| `--page-size` | Integer | No | Records per page (default: 10, max: 100) |

**Example**:
```bash
aliyun live describe-live-record-notify-records \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T00:00:00Z \
  --end-time 2025-01-21T00:00:00Z
```

**Sample Output**:
```json
{
  "RecordNotifyRecordList": {
    "RecordNotifyRecord": [
      {
        "StreamName": "stream123",
        "AppName": "live",
        "DomainName": "play.example.com",
        "NotifyTime": "2025-01-20T10:00:00Z",
        "NotifyType": "record_started",
        "NotifyResult": "success"
      },
      {
        "StreamName": "stream123",
        "AppName": "live",
        "DomainName": "play.example.com",
        "NotifyTime": "2025-01-20T10:05:00Z",
        "NotifyType": "record_error",
        "NotifyResult": "failed",
        "ErrorCode": "BucketNotFound",
        "ErrorMessage": "Bucket not found"
      }
    ]
  },
  "RequestId": "16A96B9A-F203-4EC5-8E43-CB92E68F4CD8"
}
```

---

## Common Options

All commands support the following global flags:

| Flag | Description |
|------|-------------|
| `--region` | Override region ID (e.g., `--region cn-hangzhou`) |
| `--endpoint` | Override service endpoint |
| `--cli-query` | Filter output with JMESPath expression |
| `--cli-dry-run` | Print request details without sending API call |
| `--log-level` | Set log level: DEBUG, INFO, WARN, ERROR |
| `-q, --quiet` | Suppress output (quiet mode) |
| `--pager, --all-pages` | Merge pages for pageable APIs |

**Example with JMESPath filter**:
```bash
aliyun live describe-live-stream-record-content \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T00:00:00Z \
  --end-time 2025-01-21T00:00:00Z \
  --cli-query "RecordContentInfoList.RecordContentInfo[?Duration>3600]"
```

---

## References

- [ApsaraVideo Live CLI Documentation](https://help.aliyun.com/cli)
- [API Reference](https://help.aliyun.com/live/developer-reference/api-live-2016-11-01-overview)
- [CLI Global Options](https://help.aliyun.com/cli/command-line-options)
