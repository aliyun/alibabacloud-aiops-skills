# Recording Error Codes and Resolutions

This document provides a comprehensive list of error codes that may appear in live recording callback events, along with their descriptions and recommended resolutions.

---

## Recording Errors (record_error)

Recording errors occur when the recording service encounters issues writing to OSS or processing the stream.

### BucketNotFound

**Error Code**: `BucketNotFound`

**Error Message**: `Bucket not found`

**Description**: The OSS bucket specified in the recording configuration does not exist or has been deleted.

**Root Causes**:
1. OSS bucket was deleted after recording configuration was created
2. Bucket name in configuration is incorrect
3. Bucket exists in a different region than expected

**Resolution**:
1. Verify the bucket exists in the [OSS Console](https://oss.console.aliyun.com/)
2. Check the bucket name in the recording configuration:
   ```bash
   aliyun live describe-live-record-config --domain-name <domain>
   ```
3. If the bucket was deleted, create a new bucket with the same name or update the recording configuration
4. Ensure the bucket is in the same region as the live stream domain

**Prevention**:
- Use bucket lifecycle policies to prevent accidental deletion
- Set up CloudMonitor alerts for bucket deletion events
- Document bucket names and their purposes

---

### AccessDenied

**Error Code**: `AccessDenied`

**Error Message**: `Bucket not belong config userId`

**Description**: The OSS bucket does not belong to the account ID configured for recording.

**Root Causes**:
1. Bucket ownership was transferred to another account
2. Recording configuration references an incorrect account ID
3. Cross-account bucket access not properly configured

**Resolution**:
1. Verify the bucket owner in the OSS Console
2. Check the account ID in the recording configuration:
   ```bash
   aliyun live describe-live-record-config --domain-name <domain>
   ```
3. Ensure the bucket belongs to the same Alibaba Cloud account as the live domain
4. If using cross-account access, configure RAM roles and bucket policies correctly

**Prevention**:
- Keep buckets and live domains in the same account
- Use resource groups to organize related resources
- Implement access control policies to prevent unauthorized transfers

---

### StreamFormatError

**Error Code**: `StreamFormatError`

**Error Message**: `video stream format error`

**Description**: The live stream format is incorrect, corrupted, or not supported by the recording service.

**Root Causes**:
1. Unsupported video codec (not H.264 or H.265)
2. Unsupported audio codec (not AAC or MP3)
3. Corrupted stream data
4. Invalid container format
5. Missing or malformed stream headers

**Resolution**:
1. Verify encoder settings:
   - **Video codec**: H.264 (AVC) or H.265 (HEVC)
   - **Audio codec**: AAC or MP3
   - **Container**: FLV or RTMP
2. Check stream quality using diagnostic tools:
   ```bash
   aliyun live describe-live-center-stream-rate-data \
     --domain-name <domain> \
     --app-name <app> \
     --stream-name <stream>
   ```
3. Test with a known-good stream configuration
4. Review encoder logs for errors or warnings
5. Consider using OBS Studio or FFmpeg with verified settings

**Recommended Encoder Settings**:
```
Video:
  Codec: H.264 (x264)
  Profile: Main or High
  Bitrate: 1000-4000 kbps
  Keyframe Interval: 2-4 seconds
  Frame Rate: 25 or 30 fps
  Resolution: 1280x720 or 1920x1080

Audio:
  Codec: AAC
  Bitrate: 128 kbps
  Sample Rate: 44100 Hz or 48000 Hz
  Channels: Stereo (2 channels)
```

**Prevention**:
- Use standard encoder presets
- Test stream configuration before production
- Monitor stream health metrics regularly

---

### UserDisable

**Error Code**: `UserDisable`

**Error Message**: `Unauthorized access to OSS by user`

**Description**: The user has not authorized ApsaraVideo Live to access OSS, or the authorization was revoked.

**Root Causes**:
1. OSS authorization for ApsaraVideo Live was never granted
2. Authorization was deleted or expired
3. RAM role or policy was modified incorrectly

**Resolution**:
1. Grant OSS access permissions to ApsaraVideo Live:
   - Log in to the [ApsaraVideo Live Console](https://live.console.aliyun.com/)
   - Navigate to **Recording Management** > **Authorization**
   - Click **Authorize** to grant OSS access
2. Verify RAM role exists:
   ```bash
   aliyun ram get-role --role-name AliyunLiveDefaultRole
   ```
3. Ensure the following RAM policy is attached:
   ```json
   {
     "Version": "1",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "oss:PutObject",
           "oss:GetObject"
         ],
         "Resource": [
           "acs:oss:*:*:*"
         ]
       }
     ]
   }
   ```

**Manual Authorization Steps**:
1. Create RAM role for ApsaraVideo Live (if not exists)
2. Attach OSS write policy to the role
3. Update recording configuration to use the role

**Prevention**:
- Document authorization requirements
- Set up alerts for role or policy changes
- Use infrastructure-as-code to manage RAM configurations

---

### TsSegmenterFail

**Error Code**: `TsSegmenterFail`

**Error Message**: `ts segmenter error`

**Description**: The TS (Transport Stream) segmentation process failed during recording.

**Root Causes**:
1. Stream discontinuity or dropped packets
2. Incorrect stream format or codec
3. High stream bitrate causing processing issues
4. Internal service error

**Resolution**:
1. Check stream quality and stability:
   ```bash
   aliyun live describe-live-center-stream-rate-data \
     --domain-name <domain> \
     --app-name <app> \
     --stream-name <stream>
   ```
2. Verify network stability between encoder and ingest point
3. Reduce stream bitrate if too high (>8 Mbps)
4. Ensure consistent keyframe interval (2-4 seconds)
5. Test with a stable, low-bitrate stream first
6. If issue persists, contact Alibaba Cloud support

**Prevention**:
- Use stable network connection with low latency
- Implement error recovery in encoder
- Monitor stream health metrics
- Use adaptive bitrate if network is unstable

---

## Transcoding Errors (transformat_error)

Transcoding errors occur when converting recorded segments from TS format to MP4 or FLV format.

### InvalidParameter.ResourceContentBad

**Error Code**: `InvalidParameter.ResourceContentBad`

**Error Message**: `The resource operated InputFile is bad`

**Description**: The source stream quality is poor, causing transcoding to fail.

**Root Causes**:
1. Corrupted or incomplete TS segments
2. Stream format errors propagated to recording
3. Dropped frames or packets during recording
4. Unsupported codec or format

**Resolution**:
1. Check source stream quality and encoding settings
2. Verify stream stability during recording period
3. Review stream rate data for anomalies:
   ```bash
   aliyun live describe-live-center-stream-rate-data \
     --domain-name <domain> \
     --app-name <app> \
     --stream-name <stream>
   ```
4. Test with a new stream using verified encoder settings
5. If issue persists, provide stream details to support

**Prevention**:
- Use stable, high-quality stream sources
- Monitor stream health in real-time
- Implement encoder error handling
- Use recommended encoder settings (see StreamFormatError)

---

### PermissionDenied.ResourceAccess

**Error Code**: `PermissionDenied.ResourceAccess`

**Error Message**: `MTS not authorized to operate on the OutputBucket`

**Description**: Media Transcoding Service (MTS) does not have permission to write to the OSS bucket.

**Root Causes**:
1. MTS authorization for OSS was never granted
2. MTS role or policy was deleted
3. Bucket policy blocks MTS access

**Resolution**: Grant OSS access permissions to MTS per OSS authorization guide: https://help.aliyun.com/live/user-guide/live-stream-recording

**File Information in Error**:
```json
{
  "file_info": {
    "uri": "record/live/stream123/2025-01-20-10-00-00.flv",
    "start_time": 1763493420,
    "stop_time": 1763494119
  }
}
```

**Prevention**:
- Complete all authorizations during initial setup
- Document service dependencies
- Monitor role and policy changes
- Use infrastructure-as-code for consistent configurations

---

## Callback Event Types

### record_started

**Event**: `record_started`

**Description**: Recording task started successfully.

**Example Payload**:
```json
{
  "domain": "example.com",
  "app": "live",
  "stream": "stream123",
  "event": "record_started",
  "time": "2025-01-20T10:00:00Z"
}
```

**When to Expect**: When a live stream starts and recording configuration is active.

---

### record_paused

**Event**: `record_paused`

**Description**: Recording task stopped or paused.

**Example Payload**:
```json
{
  "domain": "example.com",
  "app": "live",
  "stream": "stream123",
  "event": "record_paused",
  "time": "2025-01-20T11:00:00Z"
}
```

**When to Expect**: When a live stream stops or recording is manually paused.

---

### record_error

**Event**: `record_error`

**Description**: Recording encountered an error.

**Example Payload**:
```json
{
  "domain": "example.com",
  "app": "live",
  "stream": "stream123",
  "event": "record_error",
  "error_info": {
    "code": "BucketNotFound",
    "message": "Bucket not found"
  },
  "time": "2025-01-20T10:05:00Z"
}
```

**When to Expect**: When recording fails due to configuration, permissions, or stream issues.

---

### transformat_error

**Event**: `transformat_error`

**Description**: Transcoding to MP4/FLV failed.

**Example Payload**:
```json
{
  "domain": "example.com",
  "app": "live",
  "stream": "stream123",
  "event": "transformat_error",
  "error_info": {
    "code": "PermissionDenied.ResourceAccess",
    "message": "MTS not authorized to operate on the OutputBucket"
  },
  "file_info": {
    "uri": "record/live/stream123/2025-01-20-10-00-00.flv",
    "start_time": 1763493420,
    "stop_time": 1763494119
  },
  "time": "2025-01-20T10:05:00Z"
}
```

**When to Expect**: When MP4 or FLV format recording is configured and transcoding fails.

---

## Diagnostic Workflow by Error Code

### Quick Reference Table

| Error Code | Category | First Check | Common Fix |
|------------|----------|-------------|------------|
| `BucketNotFound` | OSS | Bucket exists | Create/verify bucket |
| `AccessDenied` | OSS | Bucket ownership | Verify account ID |
| `StreamFormatError` | Stream | Encoder settings | Fix codec/format |
| `UserDisable` | Authorization | Live→OSS auth | Grant OSS access |
| `TsSegmenterFail` | Stream | Stream quality | Check network/bitrate |
| `InvalidParameter.ResourceNotFound` | OSS | Bucket exists | Verify bucket |
| `InvalidParameter.ResourceContentBad` | Stream | Stream quality | Fix source stream |
| `PermissionDenied.ResourceAccess` | Authorization | MTS→OSS auth | Grant MTS access |

---

## Getting Help

If you've followed the resolution steps and the issue persists:

1. **Gather diagnostic information**:
   - Domain name, app name, stream name
   - Time range when error occurred
   - Error code and message from callback
   - Recording configuration details
   - Stream encoder settings

2. **Run diagnostic commands**:
   ```bash
   # Check recording configuration
   aliyun live describe-live-record-config --domain-name <domain>

   # Check callback records
   aliyun live describe-live-record-notify-records \
     --domain-name <domain> \
     --app-name <app> \
     --stream-name <stream> \
     --start-time <start> \
     --end-time <end>

   # Check stream quality
   aliyun live describe-live-center-stream-rate-data \
     --domain-name <domain> \
     --app-name <app> \
     --stream-name <stream>
   ```

3. **Contact Alibaba Cloud Support**:
   - Open a ticket in the [Support Console](https://workorder.console.aliyun.com/)
   - Include all diagnostic information
   - Reference this skill: `alibabacloud-liverecord-diagnosis`

---

## References

- [ApsaraVideo Live Error Codes](https://help.aliyun.com/live/developer-reference/api-live-2016-11-01-errorcodes)
- [Recording Callback Events](https://help.aliyun.com/live/user-guide/manage-callbacks)
- [OSS Authorization Guide](https://help.aliyun.com/live/user-guide/live-stream-recording)
