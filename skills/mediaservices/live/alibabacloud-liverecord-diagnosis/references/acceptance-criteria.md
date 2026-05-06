# Acceptance Criteria: alibabacloud-liverecord-diagnosis

**Scenario**: Live Recording Diagnostic Skill
**Purpose**: Skill testing acceptance criteria

---

## 1. CLI Command Patterns

All CLI commands used in this skill must follow the correct syntax and use valid product/command names.

### ✅ CORRECT: Valid Product Name

```bash
aliyun live describe-live-domain-mapping --domain-name example.com
```

**Why**: `live` is the correct product identifier for ApsaraVideo Live service.

### ❌ INCORRECT: Invalid Product Name

```bash
aliyun livevideo describe-live-domain-mapping --domain-name example.com
aliyun video-live describe-live-domain-mapping --domain-name example.com
```

**Why**: Product name must be exactly `live`, not `livevideo` or `video-live`.

---

### ✅ CORRECT: Valid Command Name (Plugin Mode)

```bash
aliyun live describe-live-stream-record-content \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T00:00:00Z \
  --end-time 2025-01-21T00:00:00Z
```

**Why**: Command uses lowercase words with hyphens (plugin mode format).

### ❌ INCORRECT: Wrong Command Format

```bash
# API format (not plugin mode)
aliyun live DescribeLiveStreamRecordContent \
  --domain-name play.example.com

# Wrong command name
aliyun live get-live-stream-record-content \
  --domain-name play.example.com
```

**Why**: Must use plugin mode format with correct command name `describe-live-stream-record-content`.

---

### ✅ CORRECT: Valid Parameters

```bash
aliyun live describe-live-record-config \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --page-size 20
```

**Why**: All parameters exist for this command:
- `--domain-name` (required)
- `--app-name` (optional)
- `--stream-name` (optional)
- `--page-size` (optional, valid range: 5-30)

### ❌ INCORRECT: Invalid Parameters

```bash
aliyun live describe-live-record-config \
  --domain play.example.com \
  --application live \
  --stream stream123
```

**Why**: Parameter names are incorrect:
- Should be `--domain-name`, not `--domain`
- Should be `--app-name`, not `--application`
- Should be `--stream-name`, not `--stream`

---

### ✅ CORRECT: Required Parameters Provided

```bash
aliyun live describe-live-stream-record-content \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T00:00:00Z \
  --end-time 2025-01-21T00:00:00Z
```

**Why**: All required parameters are provided:
- `--domain-name` (required)
- `--app-name` (required)
- `--stream-name` (required)
- `--start-time` (required)
- `--end-time` (required)

### ❌ INCORRECT: Missing Required Parameters

```bash
aliyun live describe-live-stream-record-content \
  --domain-name play.example.com \
  --app-name live
```

**Why**: Missing required parameters `--stream-name`, `--start-time`, `--end-time`.

---

### ✅ CORRECT: Time Format (ISO 8601 UTC)

```bash
aliyun live describe-live-stream-record-content \
  --domain-name play.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T10:00:00Z \
  --end-time 2025-01-20T11:00:00Z
```

**Why**: Time is in ISO 8601 format with UTC timezone (Z suffix).

### ❌ INCORRECT: Wrong Time Format

```bash
# Missing 'T' separator
aliyun live describe-live-stream-record-content \
  --start-time "2025-01-20 10:00:00Z"

# Missing 'Z' (UTC indicator)
aliyun live describe-live-stream-record-content \
  --start-time 2025-01-20T10:00:00

# Wrong format entirely
aliyun live describe-live-stream-record-content \
  --start-time "2025-01-20"
```

**Why**: Must be in exact format: `YYYY-MM-DDTHH:mm:ssZ`.

---

### ✅ CORRECT: Parameter Value Range

```bash
aliyun live describe-live-record-config \
  --domain-name play.example.com \
  --page-size 10 \
  --page-num 1
```

**Why**:
- `--page-size`: 10 is within valid range (5-30)
- `--page-num`: 1 is valid (minimum is 1)

### ❌ INCORRECT: Parameter Out of Range

```bash
aliyun live describe-live-record-config \
  --domain-name play.example.com \
  --page-size 50 \
  --page-num 0
```

**Why**:
- `--page-size`: 50 exceeds maximum (30)
- `--page-num`: 0 is below minimum (1)

---

## 2. Diagnostic Workflow Patterns

### ✅ CORRECT: Proper Workflow Sequence

1. Extract domain, app, stream from URL
2. Confirm parameters with user
3. Query domain mapping to get playback domain
4. Query recording content/files
5. If issues found, check configuration
6. Check stream status and quality
7. Check callback events for errors
8. Generate diagnostic report

**Why**: This sequence builds context progressively and avoids unnecessary queries.

### ❌ INCORRECT: Querying Before Parameter Confirmation

1. Extract domain, app, stream from URL
2. Immediately query recording content (without user confirmation)
3. Query configuration
4. Ask user to confirm parameters

**Why**: Must confirm parameters with user BEFORE executing any commands.

---

### ✅ CORRECT: Error Handling

```bash
# Execute command
OUTPUT=$(aliyun live describe-live-record-config \
  --domain-name play.example.com 2>&1)

# Check for errors
if echo "$OUTPUT" | grep -q "Forbidden.RAM"; then
  echo "❌ Permission error: RAM permissions required"
  echo "See references/ram-policies.md for required permissions"
  exit 1
fi
```

**Why**: Handles permission errors gracefully and directs user to resolution.

### ❌ INCORRECT: Ignoring Errors

```bash
# Execute command without error handling
aliyun live describe-live-record-config \
  --domain-name play.example.com

# Continue with next step regardless of errors
```

**Why**: Must check for and handle errors appropriately.

---

### ✅ CORRECT: Domain Type Usage

```bash
# Step 1: Get domain mapping
MAPPING=$(aliyun live describe-live-domain-mapping \
  --domain-name example.com)

# Extract playback domain from mapping
PLAYBACK_DOMAIN="play.example.com"

# Step 2: Use playback domain for recording queries
aliyun live describe-live-stream-record-content \
  --domain-name "$PLAYBACK_DOMAIN" \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T00:00:00Z \
  --end-time 2025-01-21T00:00:00Z
```

**Why**: Recording APIs require the main **playback domain**, not ingest domain.

### ❌ INCORRECT: Using Ingest Domain

```bash
# Using ingest domain directly
aliyun live describe-live-stream-record-content \
  --domain-name push.example.com \
  --app-name live \
  --stream-name stream123 \
  --start-time 2025-01-20T00:00:00Z \
  --end-time 2025-01-21T00:00:00Z
```

**Why**: Must use playback domain from domain mapping, not ingest domain.

---

## 3. Parameter Confirmation Patterns

### ✅ CORRECT: Confirming All Parameters

```
Diagnostic Parameters:
- Domain: play.example.com
- Application: live
- Stream: stream123
- Time Range: 2025-01-20T00:00:00Z to 2025-01-21T00:00:00Z
- Region: cn-hangzhou

Please confirm these parameters are correct before proceeding. (yes/no)
```

**Why**: All user-specific parameters are clearly listed and require explicit confirmation.

### ❌ INCORRECT: Assuming Default Values

```
Using default parameters:
- Region: cn-hangzhou
- Time Range: Last 24 hours

Proceeding with diagnostic...
```

**Why**: Must not assume default values without user confirmation.

---

### ✅ CORRECT: Extracting from URL

```bash
# Given URL: rtmp://push.example.com/live/stream123
# Extract:
DOMAIN="push.example.com"
APP_NAME="live"
STREAM_NAME="stream123"

# Then query domain mapping to get playback domain
MAPPING=$(aliyun live describe-live-domain-mapping --domain-name "$DOMAIN")
# Extract PLAYBACK_DOMAIN from mapping
```

**Why**: Correctly extracts components from stream URL and converts to playback domain.

### ❌ INCORRECT: Manual String Parsing Errors

```bash
# Given URL: rtmp://push.example.com/live/stream123?param=value
# Incorrect extraction:
STREAM_NAME="stream123?param=value"  # Should strip query parameters
```

**Why**: Must properly parse URL and remove query parameters.

---

## 4. Callback Event Interpretation

### ✅ CORRECT: Identifying Error Events

```json
{
  "NotifyType": "record_error",
  "ErrorCode": "BucketNotFound",
  "ErrorMessage": "Bucket not found"
}
```

**Interpretation**:
```
❌ Recording Error: OSS Bucket Not Found

Root Cause: OSS bucket does not exist or was deleted.

Resolution:
1. Verify bucket exists in OSS console
2. Create bucket if deleted
3. Update recording configuration if needed
```

**Why**: Correctly identifies error type and provides actionable resolution.

### ❌ INCORRECT: Misinterpreting Events

```json
{
  "NotifyType": "record_error",
  "ErrorCode": "BucketNotFound"
}
```

**Incorrect Interpretation**:
```
Recording completed successfully but files not found.
Please check OSS bucket permissions.
```

**Why**: `record_error` indicates failure, not success. Must distinguish between error types.

---

### ✅ CORRECT: Event Sequence Analysis

```
Events found:
1. record_started (2025-01-20T10:00:00Z)
2. record_paused (2025-01-20T11:00:00Z)

Conclusion: Recording completed successfully.
```

**Why**: Correct sequence indicates normal recording lifecycle.

### ❌ INCORRECT: Ignoring Missing Events

```
Events found:
1. record_started (2025-01-20T10:00:00Z)

Conclusion: Recording completed successfully.
```

**Why**: Missing `record_paused` event may indicate recording is still active or failed.

---

## 5. Diagnostic Report Patterns

### ✅ CORRECT: Comprehensive Report

```
=== Live Recording Diagnostic Report ===

Stream Information:
- Domain: play.example.com
- Application: live
- Stream: stream123
- Time Range: 2025-01-20T00:00:00Z to 2025-01-21T00:00:00Z

Diagnostic Results:
1. ✅ Domain Mapping: Configured correctly
2. ⚠️  Recording Content: No segments found
3. ✅ Recording Configuration: OSS recording enabled
4. ✅ Callback Configuration: Configured with status notifications
5. ❌ Stream Publish: No publish records found
6. N/A Stream Quality: No data (stream not published)
7. N/A Callback Events: No events (no recording occurred)

Root Cause:
No stream publish records found for the specified time range.

Action Required:
1. Verify stream is being pushed to: rtmp://push.example.com/live/stream123
2. Check encoder configuration and network connectivity
3. Ensure stream URL matches configuration

Recommended Next Steps:
1. Test stream push with OBS Studio or FFmpeg
2. Monitor stream status in Live console
3. Re-run diagnostic after stream starts
```

**Why**: Report is structured, identifies root cause, and provides actionable steps.

### ❌ INCORRECT: Incomplete Report

```
Diagnostic Results:
- Some configuration issues found
- Recording not working
- Please check your settings
```

**Why**: Too vague, no specific findings, no actionable steps.

---

## 6. AI-Mode Management Patterns

### ✅ CORRECT: Enable AI-Mode Before Workflow

```bash
# At the START of workflow
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-liverecord-diagnosis"

# Execute diagnostic commands...
aliyun live describe-live-domain-mapping --domain-name example.com
```

**Why**: AI-mode must be enabled before any CLI commands are executed.

### ❌ INCORRECT: Forgetting to Enable AI-Mode

```bash
# Directly execute commands without enabling AI-mode
aliyun live describe-live-domain-mapping --domain-name example.com
```

**Why**: AI-mode is required for agent skill execution tracking.

---

### ✅ CORRECT: Disable AI-Mode at ALL Exit Points

```bash
# Success path
aliyun configure ai-mode disable
echo "Diagnostic completed successfully"
exit 0

# Error path
if [ $error ]; then
  aliyun configure ai-mode disable
  echo "Diagnostic failed"
  exit 1
fi

# User cancellation path
if [ $user_cancelled ]; then
  aliyun configure ai-mode disable
  echo "Diagnostic cancelled by user"
  exit 0
fi
```

**Why**: AI-mode must be disabled at EVERY exit point, regardless of success/failure.

### ❌ INCORRECT: Only Disabling on Success

```bash
# Success path
aliyun configure ai-mode disable
echo "Diagnostic completed successfully"

# Error path - MISSING disable
if [ $error ]; then
  echo "Diagnostic failed"
  exit 1
fi
```

**Why**: AI-mode remains enabled after error exit, which is incorrect.

---

## 7. Security Patterns

### ✅ CORRECT: Credential Verification

```bash
# Check credentials exist without exposing values
aliyun configure list

# Expected output shows profile with credentials
# DO NOT echo credential values
```

**Why**: Verifies credentials exist without exposing sensitive values.

### ❌ INCORRECT: Exposing Credentials

```bash
# DO NOT DO THIS
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET

# DO NOT DO THIS
aliyun configure get access_key_id
```

**Why**: Never expose or print credential values.

---

### ✅ CORRECT: Read-Only Operations

```bash
# Query operations only
aliyun live describe-live-record-config --domain-name example.com
aliyun live describe-live-stream-record-content --domain-name example.com ...
```

**Why**: Diagnostic skill should only read data, never modify configurations.

### ❌ INCORRECT: Modifying Configuration

```bash
# DO NOT DO THIS in diagnostic skill
aliyun live add-live-app-record-config --domain-name example.com ...
aliyun live delete-live-app-record-config --domain-name example.com ...
```

**Why**: Diagnostic skill must not modify user configurations.

---

## 8. Time Range Patterns

### ✅ CORRECT: Default Time Range with Expansion

```bash
# Start with 1 day
START_TIME=$(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ)
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Query recording content
RESULT=$(aliyun live describe-live-stream-record-content ... \
  --start-time "$START_TIME" \
  --end-time "$END_TIME")

# If no data, expand to 7 days
if [ -z "$RESULT" ]; then
  START_TIME=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)
  RESULT=$(aliyun live describe-live-stream-record-content ... \
    --start-time "$START_TIME" \
    --end-time "$END_TIME")
fi
```

**Why**: Starts with reasonable default (1 day) and expands if needed (7 days).

### ❌ INCORRECT: Hardcoded Time Range

```bash
# DO NOT DO THIS
aliyun live describe-live-stream-record-content \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-12-31T23:59:59Z
```

**Why**: Hardcoded times become outdated and may query too much data.

---

## 9. Output Formatting Patterns

### ✅ CORRECT: Structured Output with Emojis

```
✅ Recording configuration found
⚠️  Callback configuration missing NeedStatusNotify
❌ No recording files found
ℹ️  Stream is currently offline
```

**Why**: Visual indicators make status clear and easy to scan.

### ❌ INCORRECT: Plain Text Only

```
Recording configuration found
Callback configuration missing NeedStatusNotify
No recording files found
Stream is currently offline
```

**Why**: Harder to quickly identify issues without visual indicators.

---

### ✅ CORRECT: Actionable Error Messages

```
❌ Recording Error: OSS Access Denied

Root Cause:
ApsaraVideo Live service does not have permission to write to OSS bucket.

Action Required:
1. Log in to ApsaraVideo Live Console: https://live.console.aliyun.com/
2. Navigate to Recording Management > Authorization
3. Click "Authorize" to grant OSS access permissions
4. Restart recording after authorization

Reference:
- OSS Authorization Guide: https://help.aliyun.com/live/user-guide/live-stream-recording
- RAM Policies: references/ram-policies.md
```

**Why**: Clearly explains problem, cause, and specific steps to resolve.

### ❌ INCORRECT: Vague Error Messages

```
Error: Recording failed
Please check your configuration
```

**Why**: No specific cause or resolution steps provided.

---

## 10. Validation Checklist

Before considering the skill complete, verify:

**CLI Commands**:
- [ ] All commands use `aliyun live` (correct product name)
- [ ] All commands use plugin mode format (lowercase-with-hyphens)
- [ ] All parameters exist for each command (verified via `--help`)
- [ ] Required parameters are always provided
- [ ] Time parameters use ISO 8601 format with Z suffix
- [ ] Parameter values are within valid ranges

**Workflow**:
- [ ] AI-mode enabled at workflow start
- [ ] Parameters confirmed with user before execution
- [ ] Domain mapping queried to get playback domain
- [ ] Playback domain used for recording queries (not ingest domain)
- [ ] Errors handled gracefully with specific messages
- [ ] AI-mode disabled at ALL exit points

**Security**:
- [ ] Credentials verified without exposing values
- [ ] Only read-only operations performed
- [ ] No configuration modifications

**Output**:
- [ ] Structured diagnostic report with clear findings
- [ ] Root cause identified when possible
- [ ] Actionable resolution steps provided
- [ ] References to relevant documentation

---

## References

- [ApsaraVideo Live CLI Documentation](https://help.aliyun.com/document_detail/110244.html)
- [ISO 8601 Time Format](https://en.wikipedia.org/wiki/ISO_8601)
