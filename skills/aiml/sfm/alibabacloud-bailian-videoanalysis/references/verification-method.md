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
    "alibabacloud-bailian20231229": true,
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

---

## Step 2: Workspace Listing Verification

**Command:**
```bash
python scripts/list_workspace.py
```

**Expected Output (Success):**
```json
{
  "workspaces": [
    { "workspace_id": "llm-xxx", "name": "Default Workspace" }
  ]
}
```

**Verification Criteria:**
- `workspaces` array is non-empty
- Each workspace has `workspace_id` and `name` fields
- `workspace_id` starts with `llm-` prefix

**Failure Actions:**
- If `workspaces` is empty → User may not have activated Bailian service; guide to [Bailian console](https://bailian.console.aliyun.com/cn-beijing#/app/app-market/quanmiao/video-comprehend)
- If error contains `No workspace permissions` → Check RAM permissions and Bailian workspace authorization

---

## Step 3: OSS Upload Verification

**Command:**
```bash
python scripts/quanmiao_upload_file_to_oss_and_get_file_url.py --localFilePath <localFilePath>
```

**Expected Output (Success):**
```json
{
  "status": "success",
  "ossBucket": "my-bucket",
  "ossObjectKey": "temp/quanmiao/20260409/video.mp4",
  "tempUrl": "https://xxx.oss-cn-beijing.aliyuncs.com/...?Signature=xxx",
  "expireSeconds": 7200
}
```

**Verification Criteria:**
- `status` field equals `"success"`
- `tempUrl` is a valid HTTPS URL containing OSS domain and signature
- `ossBucket` and `ossObjectKey` are non-empty strings

**Failure Actions:**
- If upload fails with permission error → Follow Permission Failure Handling in RAM Policy section
- If file not found → Verify `localFilePath` points to an existing file

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
      "videoCaptionResult": { "videoCaptions": [...] },
      "videoAnalysisResult": { "text": "..." },
      "videoGenerateResults": [{ "text": "..." }],
      "videoMindMappingGenerateResult": { "text": "...", "videoMindMappings": [...] },
      "videoCalculatorResult": { "items": [...] }
    },
    "usage": {
      "inputTokens": N,
      "outputTokens": N,
      "totalTokens": N
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
| Status | Action |
|--------|--------|
| `PENDING` | Wait 10-15s, retry |
| `RUNNING` | Display partial results, wait 10-15s, retry |
| `SUCCESSED` | Proceed to Step 6 |
| `FAILED` | Check error message, inform user |
| `CANCELED` | Inform user task was canceled |

**Maximum retries:** 180 (approximately 30 minutes)

---

## Step 6: Summary Verification

**Verification Criteria:**
- Summary uses data from Step 5 result directly (no additional API calls)
- Output includes all sections: title, outline, overview, captions, shot analysis, timeline, summary, token usage
- Token usage numbers match `payload.usage` from Step 5 result
