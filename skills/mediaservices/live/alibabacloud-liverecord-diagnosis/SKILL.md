---
name: alibabacloud-liverecord-diagnosis
description: |
  Alibaba Cloud Live Recording Diagnostic Skill. Use for diagnosing live stream record issues including missing recordings, file generation problems, unexpected recording behavior, and callback issues.
  Triggers: "live record", "live stream record diagnosis", "record not working", "record file missing", "record callback issue", "录制诊断", "直播录制问题".
---

# Alibaba Cloud Live Recording Diagnostic Skill

## Scenario Description

This skill provides comprehensive diagnostic capabilities for Alibaba Cloud ApsaraVideo Live recording issues. It helps identify and troubleshoot problems related to:

- Live stream not being recorded
- Recording files not generated
- Recording files not meeting expectations (missing audio/video, wrong format, etc.)
- Recording callbacks not received or incorrect
- Other live recording-related issues

**Architecture**: ApsaraVideo Live + OSS/VOD + Recording Configuration + Callback Configuration

### Diagnostic Scope

**Within Scope:**
1. Live stream not being recorded
2. Recording files not generated or incomplete
3. Recording files missing audio or video tracks
4. Recording callback issues (not received, incorrect data)
5. Recording configuration validation
6. Stream quality issues affecting recording

**Out of Scope:**
- Issues unrelated to live recording (use Alibaba Cloud official AI assistant)
- Writing/modifying user configurations (user must modify via console or CLI themselves)

---

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low, run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update, or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for detailed installation instructions.

**Pre-check: Aliyun CLI plugin update required**

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**Install Live Plugin:**

```bash
aliyun plugin install --names live
```

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

The following RAM permissions are required for this diagnostic skill. See [references/ram-policies.md](references/ram-policies.md) for the complete policy document.

**Required Actions:**
- `live:DescribeLiveDomainMapping` - Query domain mappings
- `live:DescribeLiveStreamRecordContent` - Query recording content
- `live:DescribeLiveStreamRecordIndexFiles` - Query recording index files
- `live:DescribeLiveRecordConfig` - Query recording configuration
- `live:DescribeLiveRecordVodConfigs` - Query VOD recording configuration
- `live:DescribeLiveRecordNotifyConfig` - Query callback configuration
- `live:DescribeLiveStreamsOnlineList` - Query online streams
- `live:DescribeLiveStreamsPublishList` - Query stream publish history
- `live:DescribeLiveCenterStreamRateData` - Query stream rate data
- `live:DescribeLiveRecordNotifyRecords` - Query callback records

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call, ALL user-customizable parameters (e.g., domain names, stream names, application names, time ranges, region IDs, etc.) MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval. Note that Alibaba Cloud Live API or CLI may UTC timezone. Convert the time from user local zone when calling API/CLI.

**Required Parameters:**

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|-------------------|-------------|---------------|
| `live-stream-url` | **Required** | The live stream URL to diagnose (used to extract DomainName, AppName, StreamName) | N/A |
| `issue-description` | **Required** | Description of the recording issue | N/A |
| `time-range` | Optional | Time range for diagnosis (format: YYYY-MM-DD HH:mm:ss, user local zone) | Past 1 day (expand to 7 days if no data) |
| `biz-region-id` | Optional | Business region ID | Default region from CLI config |

---

## Core Workflow

> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-liverecord-diagnosis"
> ```

### Step 1: Identify User Intent and Validate Information Completeness

**1.1 Validate Diagnostic Scope**

Check if the issue is within the diagnostic scope:
- Live stream not recorded
- Recording files not generated
- Recording files not meeting expectations
- Callback issues
- Other recording-related problems

**If out of scope**, politely inform the user to contact Alibaba Cloud support or use the official AI assistant.

**1.2 Extract Required Information**

From the live stream URL (e.g., `rtmp://example.com/live/stream123`), extract:
- **DomainName**: The main playback domain (e.g., `example.com`)
- **AppName**: The application name (e.g., `live`)
- **StreamName**: The stream name (e.g., `stream123`)

**1.3 Determine Time Range**

- If user provides time range, use it
- If not provided, default to past 1 day
- If no data found in 1 day, expand to 7 days

**1.4 Confirm Parameters with User**

Present extracted parameters to user for confirmation:
```
Diagnostic Parameters:
- Domain: play.example.com
- Application: live
- Stream: stream123
- Time Range: 2025-01-20T00:00:00Z to 2025-01-21T00:00:00Z

Please confirm these parameters are correct before proceeding.
```

---

### Step 2: Query Domain Mapping and Recording Results

**2.1 Query Domain Mapping**

First, query the domain mapping to get the main playback domain:

```bash
aliyun live describe-live-domain-mapping \
  --domain-name <DomainName>
```

See [Expected Output](references/api-response-examples.md#step-21-domain-mapping) for response format. Extract the main playback domain (Type: vhost) for subsequent queries.

**2.2 Query Recording Content**

Query recording content for the specified time range:

```bash
aliyun live describe-live-stream-record-content \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

See [Expected Output](references/api-response-examples.md#step-22-recording-content) for response format.

**2.3 Query Recording Index Files (OSS)**

If recording to OSS, query index files:

```bash
aliyun live describe-live-stream-record-index-files \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

See [Expected Output](references/api-response-examples.md#step-23-recording-index-files) for response format.

**2.4 Verify User's Issue**

Compare the query results with the user's reported issue:
- If recordings exist but user says no recordings → Issue may be with access or playback
- If no recordings found → Proceed to Step 3 to check configuration
- If recordings exist but incomplete → Check stream quality in Step 5

---

### Step 3: Query Recording Configuration

The recording to VOD/OSS configuration may have wildcard (*) matches for app name, stream name. Use the best matching configuration if there're multiple ones.

**3.1 Query Recording to OSS Configuration**

```bash
aliyun live describe-live-record-config \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName>
```

See [Expected Output](references/api-response-examples.md#step-31-recording-to-oss-configuration) for response format.

OnDemand flag in the recording configuration affects whether the record task can be started. Values are as below:
- 0: auto record
- 1: call OnDemandUrl in notify configuration to determine if record should be started
- 7: manual record, user needs to call **RealTimeRecordCommand** OpenAPI to manual start/stop recording

**Validation Checklist:**
- ✅ Configuration exists for the stream
- ✅ OssBucket and OssEndpoint are correct
- ✅ RecordFormat includes desired formats (m3u8, flv, mp4)
- ✅ OssObjectPrefix is properly configured

**3.2 Query Recording to VOD Configuration**

```bash
aliyun live describe-live-record-vod-configs \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName>
```

See [Expected Output](references/api-response-examples.md#step-32-recording-to-vod-configuration) for response format.

**Validation Checklist:**
- ✅ Configuration exists for the stream

**3.3 Diagnostic Conclusion**

- If no configuration exists: Inform user to create recording configuration before starting the stream. See: https://help.aliyun.com/live/user-guide/live-stream-recording
- If configuration is incorrect: Identify the specific issue and advise user to update via console or CLI.
- If configuration is correct: Proceed to check callback configuration.
- If OnDemand is 7: Process to check live stream information, if there're streams, remind user to call RealTimeRecordCommand OpenAPI.

---

### Step 4: Query Callback Configuration

ONLY execute this step if the user question is about callback.

**4.1 Query Recording Callback Configuration**

```bash
aliyun live describe-live-record-notify-config \
  --domain-name <PlaybackDomain>
```

See [Expected Output](references/api-response-examples.md#step-41-recording-callback-configuration) for response format.

**Validation Checklist:**
- ✅ NotifyUrl is configured (required for callbacks)
- ✅ NeedStatusNotify is enabled (for status callbacks)
- ✅ OnDemandUrl is configured (for on-demand recording)

**4.2 Diagnostic Conclusion**

- If NotifyUrl is missing: Inform user to configure callback URL.
- If NotifyUrl exists but NeedStatusNotify is false: Advise enabling NeedStatusNotify for status callbacks.
- If configuration is correct: Proceed to check stream information.

---

### Step 5: Query Live Stream Information

**5.1 Query Online Streams**

Check if the stream is currently online:

```bash
aliyun live describe-live-streams-online-list \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName>
```

See [Expected Output](references/api-response-examples.md#step-51-online-streams) for response format.

**5.2 Query Historical Stream Publish Records**

Check historical publish records:

```bash
aliyun live describe-live-streams-publish-list \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

See [Expected Output](references/api-response-examples.md#step-52-historical-stream-publish-records) for response format.

**5.3 Query Stream Rate Data (Audio/Video Frame Rates)**

If there are online/publish stream records, check audio and video frame rates to identify quality issues:

```bash
aliyun live describe-live-center-stream-rate-data \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime>
```

See [Expected Output](references/api-response-examples.md#step-53-stream-rate-data) for response format and analysis guidelines.

**5.4 Diagnostic Conclusion**

- If no publish records found: Inform user to verify the stream is being pushed to the correct URL: `rtmp://<push-domain>/<app-name>/<stream-name>`
- If stream quality issues detected (e.g., AudioFrameRate=0): Advise checking the streaming source for proper audio/video encoding.
- If stream information is normal: Proceed to check callback records.

---

### Step 6: Query Recording Callback Records

**6.1 Query Recording Callback Events**

Query callback records to identify recording issues:

```bash
aliyun live describe-live-record-notify-records \
  --domain-name <PlaybackDomain> \
  --app-name <AppName> \
  --stream-name <StreamName> \
  --start-time <StartTime> \
  --end-time <EndTime> \
  --page-size <PageSize, e.g. 20> \
  --page-number <PageNumber, e.g. 1>
```

See [Expected Output](references/api-response-examples.md#step-61-recording-callback-records) for response format.

**6.2 Analyze Callback Events**

**Recording Event Types:**

1. **record_started** - Recording started successfully
2. **record_paused** - Recording paused/stopped
3. **record_error** - Recording error occurred
4. **transformat_error** - Transcoding error (for MP4/FLV)

For detailed error codes, resolution steps, and diagnostic conclusions, see [references/error-codes.md](references/error-codes.md).

**6.3 Diagnostic Conclusion**

Based on callback events, identify the error code and follow the resolution in [references/error-codes.md](references/error-codes.md).

**If no errors found:**
```
✅ No recording errors found in callback records.

If you're still experiencing issues, please provide more details about the specific problem.
```

---

### Step 7: Generate Diagnostic Report

After completing all diagnostic steps, generate a comprehensive report using the template in [references/diagnostic-report-template.md](references/diagnostic-report-template.md).

The report should cover:
1. Stream Information (domain, app, stream, time range)
2. Diagnostic Results for each step (domain mapping, recording content, configuration, callback, stream, quality, events)
3. Root Cause summary
4. Action Required items
5. Recommended Next Steps

> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

---

## Success Verification Method

After completing the diagnostic workflow:

1. **Verify Recording Configuration**: Check that recording config exists and is correct
2. **Verify Callback Configuration (optional) **: Check that callback URL is configured if the user question is about callback or necessary
3. **Verify Stream Status**: Check that stream has been published
4. **Verify Callback Records**: Check for any error events
5. **Verify Recording Files**: Check that files exist in OSS or VOD

For detailed verification steps and commands, see [references/verification-method.md](references/verification-method.md).

---

## Cleanup

This diagnostic skill does not create any resources, so no cleanup is required.

**Note**: This skill is read-only and does NOT modify any configurations. If configuration changes are needed, users must update them via console or CLI.

---

## Best Practices

1. **Always verify domain mapping first** - Ensure you're querying the correct playback domain
2. **Use appropriate time ranges** - Start with 1 day, expand to 7 days if needed
3. **Check recording configuration before stream starts** - Recording config must be created before pushing the stream
4. **Enable status callbacks** - Set NeedStatusNotify=true to receive detailed recording events
5. **Monitor callback events regularly** - Check for error events to identify issues early
6. **Verify OSS permissions** - Ensure ApsaraVideo Live has access to the OSS bucket
7. **Check stream quality** - Monitor audio/video frame rates to ensure proper encoding
8. **Use the correct domain type** - Recording APIs require the main playback domain, not ingest domain
9. **Wait for recording segments to complete** - Recordings are written after the segment duration (e.g., 3600 seconds)
10. **Test with a simple stream first** - Use a basic stream to verify configuration before testing complex scenarios

---

## Reference Links

| Reference Document | Description |
|-------------------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | Complete RAM permissions required for this skill |
| [references/related-commands.md](references/related-commands.md) | Complete list of CLI commands used in this skill |
| [references/verification-method.md](references/verification-method.md) | Detailed verification steps and commands |
| [references/error-codes.md](references/error-codes.md) | Complete list of recording error codes and resolutions |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Alibaba Cloud CLI installation and configuration guide |
| [references/api-response-examples.md](references/api-response-examples.md) | API response format examples for diagnostic commands |
| [references/diagnostic-report-template.md](references/diagnostic-report-template.md) | Diagnostic report template and example |

---

## Additional Resources

- [ApsaraVideo Live Recording Documentation](https://help.aliyun.com/live/user-guide/live-stream-recording)
- [Recording Callback Documentation](https://help.aliyun.com/live/user-guide/manage-callbacks)
- [OSS Authorization Guide](https://help.aliyun.com/live/user-guide/live-stream-recording)
- [Live Streaming Best Practices](https://help.aliyun.com/live/user-guide/live-stream-ingest)
