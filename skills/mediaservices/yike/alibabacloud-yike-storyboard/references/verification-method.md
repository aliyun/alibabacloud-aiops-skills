# Verification Method - Yike Storyboard Skill

This document describes how to verify successful execution of the Yike Storyboard skill.

## Verification Flow

### 1. Credential Verification

**Command:**
```bash
aliyun configure list
```

**Success Criteria:**
- Output shows valid profile configuration
- Contains AccessKeyId or STS credential information

### 2. Upload Credential Verification

**Command:**
```bash
aliyun ice create-yike-asset-upload \
  --file-ext txt \
  --file-type StoryboardInput \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard
```

**Success Criteria:**
- HTTP status code 200
- Response contains `UploadAddress`, `UploadAuth`, `FileURL` fields
- No `Code` or `code` error fields

**Expected Response Format:**
```json
{
  "UploadAddress": "base64...",
  "UploadAuth": "base64...",
  "FileURL": "https://...",
  "RequestId": "xxx"
}
```

### 3. File Upload Verification

**Steps:**
1. Decode `UploadAuth` to get STS credentials
2. Decode `UploadAddress` to get OSS info
3. Upload file using `aliyun oss cp`

**Success Criteria:**
- Upload command returns success
- No error messages in output
- Output shows "Succeed: Total num: 1"

### 4. Job Submission Verification

**Command:**
```bash
aliyun ice submit-yike-storyboard-job \
  --file-url "<FileURL>" \
  --source-type Script \
  --style-id CinematicRealism \
  --narration-voice-id sys_GentleYoungMan \
  --shot-split-mode dialogue \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard
```

**Success Criteria:**
- HTTP status code 200
- Response contains `JobId` field
- No `Code` or `code` error fields

**Expected Response Format:**
```json
{
  "JobId": "xxx",
  "RequestId": "xxx"
}
```

### 5. Job Status Verification

**Command:**
```bash
aliyun ice get-yike-storyboard-job \
  --job-id <JobId> \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard
```

**Success Criteria:**
- HTTP status code 200
- `JobStatus` is `Running`, `Succeeded`, `Failed`, or `Suspended`

**Status Flow Verification:**

See [SKILL.md Task 3](../SKILL.md#task-3-query-job-status) for complete status flow and user prompts.

### 6. Final Verification

**Storyboard Link Verification:**
1. Parse `StoryboardInfoList` from `JobResult`
2. Extract `storyboardId`
3. Construct link: `https://www.yikeai.com/#/storyboard/editing?storyboardId={storyboardId}`
4. Open link in browser to confirm storyboard content displays correctly

## Common Error Troubleshooting

| Error Type | Possible Cause | Solution |
|------------|----------------|----------|
| `MainAccountUserNotFound` | Yike service not activated | Apply for whitelist access at https://www.yikeai.com |
| `InvalidAccessKeyId` | Invalid AK/SK | Check credentials via `aliyun configure` |
| `Forbidden` | Insufficient permissions | Check RAM policies |
| `InvalidFileType` | Unsupported file format | Use txt or docx |
| `FileSizeExceed` | File too large | Compress or split file (limit 5MB) |
| `InvalidStyleId` | Style ID not found | Refer to style mapping table |
| `InvalidVoiceId` | Voice ID not found | Refer to voice mapping table |
| `ParseFailed` | Script parsing failed | Check text format and content |
| `region can't be empty` | Missing region parameter | Add `--region cn-shanghai` |
