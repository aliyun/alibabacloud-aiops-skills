# Verification Method: alibabacloud-bailian-videoanalysis

Step-by-step verification commands to confirm successful execution at each workflow stage.

---

## Step 1: Environment Check Verification

**Command:**
```bash
python scripts/check_env.py
```

**Expected Output (Success):**
```json
{
  "pythonPackagesInstalled": {
    "alibabacloud-quanmiaolightapp20240801": true,
    "alibabacloud-openapi-util": true,
    "alibabacloud-credentials": true,
    "alibabacloud-tea-openapi": true,
    "alibabacloud-tea-util": true
  },
  "allPythonPackagesInstalled": true,
  "credentialsConfigured": true,
  "ready": true,
  "errors": []
}
```

**Verification Criteria:**
- `ready` field is `true`
- `allPythonPackagesInstalled` field is `true`
- `credentialsConfigured` field is `true`
- `errors` array is empty

**Failure Actions:**
- If `allPythonPackagesInstalled` is `false` → Run `pip install -r scripts/requirements.txt`
- If `credentialsConfigured` is `false` → Guide user to run `aliyun configure` outside session

**Additional CLI Verification:**
```bash
# Verify Aliyun CLI version >= 3.3.1
aliyun version

# Verify credentials are configured
aliyun configure list
```

---

## Step 2: Workspace Listing Verification

**Command:**
```bash
aliyun modelstudio list-workspaces --user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis
```

**Expected Output (Success):**
```json
{
  "RequestId": "...",
  "Workspaces": [
    {
      "WorkspaceId": "llm-xxx",
      "Name": "Default Workspace"
    }
  ]
}
```

**Verification Criteria:**
- `Workspaces` array is non-empty
- Each workspace has `WorkspaceId` and `Name` fields
- `WorkspaceId` starts with `llm-` prefix

**Failure Actions:**
- If `Workspaces` is empty → User may not have activated Bailian service; guide to [Bailian console](https://bailian.console.aliyun.com/cn-beijing#/app/app-market/quanmiao/video-comprehend)
- If error contains `No workspace permissions` → Check RAM permissions and Bailian workspace authorization

---

## Step 3: OSS Upload Verification

**Commands:**
```bash
# List available buckets
aliyun ossutil ls --user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis

# Upload file to OSS
aliyun ossutil cp <local-file> oss://<bucket>/<key> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis --region <region>

# Generate temporary URL
aliyun ossutil sign oss://<bucket>/<key> --expires-duration 7200 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis --region <region>
```

**Expected Output (Sign Command Success):**
```
https://my-bucket.oss-cn-beijing.aliyuncs.com/temp/quanmiao/20260409/video.mp4?Signature=xxx&Expires=xxx&OSSAccessKeyId=xxx
```

**Verification Criteria:**
- Generated URL is a valid HTTPS URL containing OSS domain and signature parameters
- URL includes `Signature`, `Expires`, and `OSSAccessKeyId` query parameters
- Bucket name and object key match the uploaded file

**Failure Actions:**
- If upload fails with permission error → Follow Permission Failure Handling in RAM Policy section
- If file not found → Verify local file path points to an existing file
- If no buckets available → Create an OSS bucket first or use user-provided video URL directly

---

## Step 4: Task Submission Verification

**Command:**
```bash
python scripts/quanmiao_submit_videoAnalysis_task.py --workspace_id <workspace_id> --file_url <tempUrl>
```

**Expected Output (Success):**
```json
{
  "task_id": "xxxx"
}
```

**Verification Criteria:**
- Response contains a non-empty `task_id` field
- No error code or message in response

**Failure Actions:**
- If `task_id` is missing → Check that `workspace_id` exists and `file_url` is valid and not expired
- If permission error → Follow Permission Failure Handling in RAM Policy section

---

## Step 5: Task Result Polling Verification

**Command:**
```bash
python scripts/quanmiao_get_videoAnalysis_task_result.py --workspace_id <workspace_id> --task_id <task_id>
```

**Expected Output (SUCCESSED):**
```json
{
  "header": {
    "taskId": "...",
    "event": "task-finished",
    "sessionId": "...",
    "eventInfo": "完成视频理解"
  },
  "payload": {
    "output": {
      "videoTitleGenerateResult": { "text": "..." },
      "videoCaptionResult": { "videoCaptions": [] },
      "videoAnalysisResult": { "text": "..." },
      "videoGenerateResults": [{ "text": "..." }],
      "videoMindMappingGenerateResult": { "text": "...", "videoMindMappings": [] },
      "videoCalculatorResult": { "items": [] }
    },
    "usage": {
      "inputTokens": 1,
      "outputTokens": 1,
      "totalTokens": 2
    }
  },
  "requestId": "..."
}
```

**Verification Criteria:**
- `header.event` equals `"task-finished"`
- `payload.output` contains all expected result fields
- `payload.usage` contains token counts

**Status Handling:**

| Status      | Action                                      |
|-------------|---------------------------------------------|
| `PENDING`   | Wait 10-15s, retry                          |
| `RUNNING`   | Display partial results, wait 10-15s, retry |
| `SUCCESSED` | Proceed to Step 6                           |
| `FAILED`    | Check error message, inform user            |
| `CANCELED`  | Inform user task was canceled               |

**Maximum retries:** 180 (approximately 30 minutes)

---

## Step 6: Summary Verification

**Verification Criteria:**
- Summary uses data from Step 5 result directly (no additional API calls)
- Output includes all sections: title, outline, overview, captions, shot analysis, timeline, summary, token usage
- Token usage numbers match `payload.usage` from Step 5 result

--- 