# API Response Examples

This document contains expected output examples for the CLI commands used in the live recording diagnostic workflow.

---

## Step 2.1: Domain Mapping

Command: `aliyun live describe-live-domain-mapping`

```json
{
  "RequestId": "...",
  "LiveDomainModels": {
    "LiveDomainModel": [
      {
        "DomainName": "pull.example.com",
        "Type": "vhost"
      },
      {
        "DomainName": "push.example.com",
        "Type": "publish"
      }
    ]
  }
}
```

Extract the main playback domain (Type: vhost) for subsequent queries.

---

## Step 2.2: Recording Content

Command: `aliyun live describe-live-stream-record-content`

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
  "RequestId": "..."
}
```

---

## Step 2.3: Recording Index Files

Command: `aliyun live describe-live-stream-record-index-files`

```json
{
  "RecordIndexInfoList": {
    "RecordIndexInfo": [
      {
        "RecordUrl": "http://bucket.oss-cn-hangzhou.aliyuncs.com/record/live/stream123.m3u8",
        "RecordId": "...",
        "CreateTime": "2025-01-20T10:00:00Z",
        "EndTime": "2025-01-20T11:00:00Z",
        "Duration": 3600,
        "Height": 1080,
        "Width": 1920,
        "Format": "m3u8"
      }
    ]
  },
  "RequestId": "..."
}
```

---

## Step 3.1: Recording to OSS Configuration

Command: `aliyun live describe-live-record-config`

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
          }
        ],
        "CreateTime": "2025-01-15T10:00:00Z"
      }
    ]
  },
  "RequestId": "..."
}
```

---

## Step 3.2: Recording to VOD Configuration

Command: `aliyun live describe-live-record-vod-configs`

```json
{
  "LiveRecordVodConfigs": {
    "LiveRecordVodConfig": [
      {
        "AppName": "live",
        "StreamName": "stream123",
        "VodTranscodeGroupId": "...",
        "CycleDuration": 3600,
        "CreateTime": "2025-01-15T10:00:00Z"
      }
    ]
  },
  "RequestId": "..."
}
```

---

## Step 4.1: Recording Callback Configuration

Command: `aliyun live describe-live-record-notify-config`

```json
{
  "LiveRecordNotifyConfig": {
    "DomainName": "play.example.com",
    "NotifyUrl": "https://callback.example.com/live/record",
    "NeedStatusNotify": true,
    "OnDemandUrl": "https://callback.example.com/live/ondemand"
  },
  "RequestId": "..."
}
```

---

## Step 5.1: Online Streams

Command: `aliyun live describe-live-streams-online-list`

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
  "RequestId": "..."
}
```

---

## Step 5.2: Historical Stream Publish Records

Command: `aliyun live describe-live-streams-publish-list`

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
  "RequestId": "..."
}
```

---

## Step 5.3: Stream Rate Data

Command: `aliyun live describe-live-center-stream-rate-data`

```json
{
  "StreamRateDataList": {
    "StreamRateData": [
      {
        "Time": "2025-01-20T10:00:00Z",
        "AudioFrameRate": 25,
        "VideoFrameRate": 30
      },
      {
        "Time": "2025-01-20T10:05:00Z",
        "AudioFrameRate": 0,
        "VideoFrameRate": 30
      }
    ]
  },
  "RequestId": "..."
}
```

**Analysis:**
- **AudioFrameRate = 0**: Recording may have no audio
- **VideoFrameRate = 0**: Recording may have no video
- **Normal range**: Audio 15-60 fps, Video 15-60 fps
- **Abnormal**: Frame rate consistently 0 or > 200

---

## Step 6.1: Recording Callback Records

Command: `aliyun live describe-live-record-notify-records`

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
  "RequestId": "..."
}
```
