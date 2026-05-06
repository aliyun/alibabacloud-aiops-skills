# Diagnostic Report Template

Use the following template to generate a comprehensive diagnostic report after completing all diagnostic steps.

---

## Template

```
=== Live Recording Diagnostic Report ===

Stream Information:
- Domain: <PlaybackDomain>
- Application: <AppName>
- Stream: <StreamName>
- Time Range: <StartTime> to <EndTime>

Diagnostic Results:

1. [✅/⚠️/❌] Domain Mapping: <result>
2. [✅/⚠️/❌] Recording Content: <result>
3. [✅/⚠️/❌] Recording Configuration: <result>
4. [✅/⚠️/❌] Callback Configuration: <result>
5. [✅/⚠️/❌] Stream Publish: <result>
6. [✅/⚠️/❌] Stream Quality: <result>
7. [✅/⚠️/❌] Callback Events: <result>

Root Cause:
<Summary of the identified root cause>

Action Required:
1. <First action item>
2. <Second action item>
3. <Third action item>

Recommended Next Steps:
1. <First recommendation with link>
2. <Second recommendation>
3. <Third recommendation>

For further assistance, contact Alibaba Cloud Support.
```

---

## Example Report

```
=== Live Recording Diagnostic Report ===

Stream Information:
- Domain: play.example.com
- Application: live
- Stream: stream123
- Time Range: 2025-01-20T00:00:00Z to 2025-01-21T00:00:00Z

Diagnostic Results:

1. ✅ Domain Mapping: Configured correctly
2. ✅ Recording Content: Found 5 record content items
3. ✅ Recording Configuration: OSS recording enabled
4. ⚠️  Callback Configuration: NeedStatusNotify is disabled
5. ✅ Stream Publish: 1 publish session found
6. ⚠️  Stream Quality: Audio frame rate = 0 (no audio)
7. ❌ Callback Events: record_error detected

Root Cause:
Recording failed due to OSS bucket access denied (Error: UserDisable).

Action Required:
1. Grant OSS access permissions to ApsaraVideo Live service
2. Enable NeedStatusNotify in callback configuration to receive status callbacks
3. Check stream source to resolve audio issue (frame rate = 0)

Recommended Next Steps:
1. Follow OSS authorization guide: https://help.aliyun.com/live/user-guide/live-stream-recording
2. Update callback configuration via console
3. Verify stream audio encoding settings

For further assistance, contact Alibaba Cloud Support.
```
