# Verification Method

This document provides detailed verification steps to validate the diagnostic results and ensure the live recording system is functioning correctly.

---

## Overview

After completing the diagnostic workflow, use these verification steps to confirm:
1. Recording configuration is correct
2. Callback configuration is properly set
3. Streams are being published
4. Recording files are being generated
5. Callbacks are being received

---

## 1. Verify Recording Configuration

### 1.1 Verify OSS Recording Configuration

**Command**:
```bash
aliyun live describe-live-record-config \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName>
```

**Verification Checklist**:

✅ **Configuration exists**
- Output should contain `LiveAppRecord` array with at least one entry
- If empty, recording is not configured

✅ **Bucket settings are correct**
- `OssBucket`: Matches the intended bucket name
- `OssEndpoint`: Correct region endpoint (e.g., `oss-cn-hangzhou.aliyuncs.com`)
- `OssObjectPrefix`: Follows desired path pattern

✅ **Recording format is configured**
- `RecordFormat` array contains desired formats:
  - `m3u8` for HLS
  - `mp4` for MP4
  - `flv` for FLV
- `CycleDuration` is appropriate (typically 3600 seconds = 1 hour)

**Example Valid Output**:
```json
{
  "LiveAppRecordList": {
    "LiveAppRecord": [
      {
        "AppName": "live",
        "StreamName": "stream123",
        "OssBucket": "my-live-recordings",
        "OssEndpoint": "oss-cn-hangzhou.aliyuncs.com",
        "OssObjectPrefix": "record/{AppName}/{StreamName}/{Date}/{UnixTimestamp}",
        "RecordFormat": [
          {
            "Format": "m3u8",
            "CycleDuration": 3600
          }
        ],
        "CreateTime": "2025-01-15T10:00:00Z"
      }
    ]
  }
}
```

---

### 1.2 Verify VOD Recording Configuration

**Command**:
```bash
aliyun live describe-live-record-vod-configs \
  --domain-name <PlaybackDomain> \
  --app-name <AppName>
```

**Verification Checklist**:

✅ **Configuration exists** (if using VOD recording)
- Output should contain `LiveRecordVodConfig` array
- If empty and VOD recording is expected, configuration is missing

✅ **VOD settings are correct**
- `VodTranscodeGroupId`: Valid transcode template group ID
- `CycleDuration`: Appropriate segment duration
- `AutoCompose`: Set to `true` if auto-composition is desired

**Example Valid Output**:
```json
{
  "LiveRecordVodConfigs": {
    "LiveRecordVodConfig": [
      {
        "AppName": "live",
        "StreamName": "stream123",
        "VodTranscodeGroupId": "e2d796d3d5c6472b8c35a****",
        "CycleDuration": 3600,
        "AutoCompose": true,
        "CreateTime": "2025-01-15T10:00:00Z"
      }
    ]
  }
}
```

---

## 2. Verify Callback Configuration

### 2.1 Verify Recording Callback Settings

**Command**:
```bash
aliyun live describe-live-record-notify-config \
  --domain-name <PlaybackDomain>
```

**Verification Checklist**:

✅ **Callback URL is configured**
- `NotifyUrl`: Should be a valid HTTPS URL
- URL should be accessible from Alibaba Cloud

✅ **Status notifications are enabled** (recommended)
- `NeedStatusNotify`: Should be `true` to receive detailed events
- If `false`, only file completion callbacks are sent

✅ **On-demand callback is configured** (if using on-demand recording)
- `OnDemandUrl`: Valid URL for on-demand recording triggers

**Example Valid Output**:
```json
{
  "LiveRecordNotifyConfig": {
    "DomainName": "play.example.com",
    "NotifyUrl": "https://callback.example.com/live/record",
    "NeedStatusNotify": true,
    "OnDemandUrl": "https://callback.example.com/live/ondemand"
  }
}
```

**Validation Steps**:

1. **Test callback URL accessibility**:
   ```bash
   curl -I https://callback.example.com/live/record
   ```
   Expected: HTTP 200 or 405 (if POST-only)

2. **Verify HTTPS certificate** (for production):
   ```bash
   openssl s_client -connect callback.example.com:443 -servername callback.example.com
   ```
   Expected: Valid certificate, not expired

---

## 3. Verify Stream Status

### 3.1 Check Current Online Streams

**Command**:
```bash
aliyun live describe-live-streams-online-list \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName>
```

**Verification Checklist**:

✅ **Stream is online** (for active streams)
- Output should contain `LiveStreamOnlineInfo` array with the stream
- `PublishTime`: Should be recent
- `PublishUrl`: Should match expected ingest URL

**Example Valid Output**:
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
  }
}
```

---

### 3.2 Check Historical Publish Records

**Command**:
```bash
aliyun live describe-live-streams-publish-list \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

**Verification Checklist**:

✅ **Publish records exist** (for historical analysis)
- Output should contain `LiveStreamPublishInfo` array
- Records should cover the expected time range
- `PublishTime` and `StopTime` should align with recording periods

**Example Valid Output**:
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
  }
}
```

---

### 3.3 Verify Stream Quality

**Command**:
```bash
aliyun live describe-live-center-stream-rate-data \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

**Verification Checklist**:

✅ **Audio frame rate is normal**
- `AudioFrameRate`: Should be > 0 (typically 15-60 fps)
- If 0, recording will have no audio

✅ **Video frame rate is normal**
- `VideoFrameRate`: Should be > 0 (typically 15-60 fps)
- If 0, recording will have no video

✅ **Bitrates are appropriate**
- `AudioBitrate`: Typically 64000-256000 bps (64-256 kbps)
- `VideoBitrate`: Typically 500000-8000000 bps (0.5-8 Mbps)

**Example Valid Output**:
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
      }
    ]
  }
}
```

**Warning Signs**:
- ⚠️ `AudioFrameRate: 0` → No audio in recording
- ⚠️ `VideoFrameRate: 0` → No video in recording
- ⚠️ Frame rate > 200 → Possible data error
- ⚠️ Bitrate fluctuates wildly → Network instability

---

## 4. Verify Recording Files

### 4.1 Check Recording Content

**Command**:
```bash
aliyun live describe-live-stream-record-content \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

**Verification Checklist**:

✅ **Recording segments exist**
- Output should contain `RecordContentInfo` array
- Number of segments should align with stream duration and cycle duration
- Example: 2-hour stream with 1-hour cycle = 2 segments

✅ **Segment timing is correct**
- `StartTime` and `EndTime` should cover the streaming period
- `Duration` should match expected cycle duration (or remaining time)

✅ **Format is correct**
- `Format`: Should match configured recording format (m3u8, mp4, flv)

**Example Valid Output**:
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
      },
      {
        "OssObjectPrefix": "record/live/stream123/",
        "StartTime": "2025-01-20T11:00:00Z",
        "EndTime": "2025-01-20T12:00:00Z",
        "Duration": 3600,
        "Format": "m3u8"
      }
    ]
  }
}
```

---

### 4.2 Check Recording Index Files

**Command**:
```bash
aliyun live describe-live-stream-record-index-files \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

**Verification Checklist**:

✅ **Index files exist**
- Output should contain `RecordIndexInfo` array
- Each segment should have a corresponding index file

✅ **File URLs are accessible**
- `RecordUrl`: Should be a valid OSS URL
- Test accessibility: `curl -I <RecordUrl>`

✅ **File metadata is correct**
- `Duration`: Matches expected segment duration
- `Height` and `Width`: Match stream resolution
- `Format`: Matches configured format

**Example Valid Output**:
```json
{
  "RecordIndexInfoList": {
    "RecordIndexInfo": [
      {
        "RecordUrl": "http://my-bucket.oss-cn-hangzhou.aliyuncs.com/record/live/stream123/index.m3u8",
        "RecordId": "c4d7f0a4-b506-43f9-8de3-07732c3f****",
        "CreateTime": "2025-01-20T10:00:00Z",
        "EndTime": "2025-01-20T11:00:00Z",
        "Duration": 3600,
        "Height": 1080,
        "Width": 1920,
        "Format": "m3u8"
      }
    ]
  }
}
```

**Manual File Verification**:
```bash
# Test OSS file accessibility
curl -I http://my-bucket.oss-cn-hangzhou.aliyuncs.com/record/live/stream123/index.m3u8

# Expected: HTTP 200 OK
```

---

## 5. Verify Callback Events

### 5.1 Check Recording Callback Records

**Command**:
```bash
aliyun live describe-live-record-notify-records \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

**Verification Checklist**:

✅ **Callback events exist**
- Output should contain `RecordNotifyRecord` array
- Events should cover the recording lifecycle

✅ **Event sequence is correct**
- Typical sequence: `record_started` → `record_paused`
- If errors occurred: `record_error` or `transformat_error` events

✅ **No error events** (for successful recordings)
- `NotifyType`: Should be `record_started` or `record_paused`
- If `record_error` or `transformat_error`, investigate further

**Example Valid Output (Success)**:
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
        "NotifyTime": "2025-01-20T11:00:00Z",
        "NotifyType": "record_paused",
        "NotifyResult": "success"
      }
    ]
  }
}
```

**Example Output with Error**:
```json
{
  "RecordNotifyRecordList": {
    "RecordNotifyRecord": [
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
  }
}
```

If error events exist, refer to [references/error-codes.md](error-codes.md) for resolution steps.

---

## 6. End-to-End Verification

### 6.1 Complete System Check

Perform a complete end-to-end verification:

**Step 1: Verify Configuration**
```bash
# Check recording config
aliyun live describe-live-record-config \
  --domain-name play.example.com \
  --app-name live

# Check callback config
aliyun live describe-live-record-notify-config \
  --domain-name play.example.com
```

**Step 2: Verify Stream**
```bash
# Check if stream is online
aliyun live describe-live-streams-online-list \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123
```

**Step 3: Verify Recording**
```bash
# Check recording content (past 1 hour)
aliyun live describe-live-stream-record-content \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

**Step 4: Verify Callbacks**
```bash
# Check callback events (past 1 hour)
aliyun live describe-live-record-notify-records \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

---

### 6.2 Success Criteria

A fully functioning recording system should meet all of these criteria:

| Component | Success Criteria |
|-----------|------------------|
| **Configuration** | ✅ Recording config exists with valid OSS bucket |
| **Configuration** | ✅ Callback config exists with valid URL |
| **Stream** | ✅ Stream publish records exist for target time range |
| **Stream Quality** | ✅ Audio/video frame rates > 0 |
| **Recording Files** | ✅ Recording segments exist and cover streaming period |
| **Recording Files** | ✅ Index files are accessible via OSS URLs |
| **Callbacks** | ✅ `record_started` and `record_paused` events received |
| **Callbacks** | ✅ No `record_error` or `transformat_error` events |

---

## 7. Troubleshooting Failed Verification

### Configuration Issues

**Symptom**: No recording configuration found

**Verification**:
```bash
aliyun live describe-live-record-config --domain-name <domain>
# Result: Empty LiveAppRecordList
```

**Resolution**:
- Create recording configuration via console or CLI
- Ensure configuration is created for the correct domain/app/stream
- See: https://help.aliyun.com/live/user-guide/live-stream-recording

---

### Stream Issues

**Symptom**: No publish records found

**Verification**:
```bash
aliyun live describe-live-streams-publish-list \
  --domain-name <domain> \
  --app-name <app> \
  --stream-name <stream> \
  --start-time <start> \
  --end-time <end>
# Result: Empty PublishInfo
```

**Resolution**:
- Verify stream is being pushed to correct URL
- Check encoder settings and network connectivity
- Confirm domain/app/stream names match in encoder and query

---

### Recording File Issues

**Symptom**: No recording files generated

**Verification**:
```bash
aliyun live describe-live-stream-record-content \
  --domain-name <domain> \
  --app-name <app> \
  --stream-name <stream> \
  --start-time <start> \
  --end-time <end>
# Result: Empty RecordContentInfoList
```

**Resolution**:
1. Check callback events for errors
2. Verify OSS bucket permissions
3. Confirm stream quality (frame rates > 0)
4. Wait for cycle duration to complete (e.g., 1 hour)

---

### Callback Issues

**Symptom**: No callback events received

**Verification**:
```bash
aliyun live describe-live-record-notify-records \
  --domain-name <domain> \
  --app-name <app> \
  --stream-name <stream> \
  --start-time <start> \
  --end-time <end>
# Result: Empty RecordNotifyRecordList
```

**Resolution**:
1. Verify callback URL is configured
2. Check callback URL is accessible from internet
3. Enable NeedStatusNotify for detailed events
4. Review callback server logs for errors

---

## 8. Automated Verification Script

For regular monitoring, use this automated verification script:

```bash
#!/bin/bash

# Configuration
DOMAIN="play.example.com"
APP="live"
STREAM="stream123"
START_TIME=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "=== Live Recording Verification ==="
echo "Domain: $DOMAIN"
echo "App: $APP"
echo "Stream: $STREAM"
echo "Time Range: $START_TIME to $END_TIME"
echo ""

# Check recording config
echo "1. Checking recording configuration..."
CONFIG=$(aliyun live describe-live-record-config \
  --domain-name "$DOMAIN" \
  --app-name "$APP" \
  --stream-name "$STREAM" 2>&1)

if echo "$CONFIG" | grep -q "LiveAppRecord"; then
  echo "   ✅ Recording configuration found"
else
  echo "   ❌ Recording configuration not found"
fi
echo ""

# Check callback config
echo "2. Checking callback configuration..."
CALLBACK=$(aliyun live describe-live-record-notify-config \
  --domain-name "$DOMAIN" 2>&1)

if echo "$CALLBACK" | grep -q "NotifyUrl"; then
  echo "   ✅ Callback configuration found"
else
  echo "   ❌ Callback configuration not found"
fi
echo ""

# Check stream status
echo "3. Checking stream status..."
STREAM_STATUS=$(aliyun live describe-live-streams-online-list \
  --domain-name "$DOMAIN" \
  --app-name "$APP" \
  --stream-name "$STREAM" 2>&1)

if echo "$STREAM_STATUS" | grep -q "PublishTime"; then
  echo "   ✅ Stream is online"
else
  echo "   ℹ️  Stream is offline (checking history)"
fi
echo ""

# Check recording content
echo "4. Checking recording content..."
RECORDING=$(aliyun live describe-live-stream-record-content \
  --domain-name "$DOMAIN" \
  --app-name "$APP" \
  --stream-name "$STREAM" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" 2>&1)

if echo "$RECORDING" | grep -q "RecordContentInfo"; then
  echo "   ✅ Recording content found"
else
  echo "   ❌ No recording content found"
fi
echo ""

# Check callback events
echo "5. Checking callback events..."
CALLBACKS=$(aliyun live describe-live-record-notify-records \
  --domain-name "$DOMAIN" \
  --app-name "$APP" \
  --stream-name "$STREAM" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" 2>&1)

if echo "$CALLBACKS" | grep -q "record_error\|transformat_error"; then
  echo "   ⚠️  Errors detected in callbacks"
  echo "$CALLBACKS" | grep -A 2 "record_error\|transformat_error"
elif echo "$CALLBACKS" | grep -q "record_started"; then
  echo "   ✅ Recording callbacks received"
else
  echo "   ℹ️  No callback events found"
fi
echo ""

echo "=== Verification Complete ==="
```

Save as `verify-recording.sh` and run:
```bash
chmod +x verify-recording.sh
./verify-recording.sh
```

---

## References

- [ApsaraVideo Live API Reference](https://help.aliyun.com/live/developer-reference/api-live-2016-11-01-overview)
- [Recording Configuration Guide](https://help.aliyun.com/live/user-guide/live-stream-recording)
- [Callback Configuration Guide](https://help.aliyun.com/live/user-guide/manage-callbacks)
- [Error Codes Reference](error-codes.md)
