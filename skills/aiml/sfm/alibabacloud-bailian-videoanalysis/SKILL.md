---
name: alibabacloud-bailian-videoanalysis
description: |
  Alibaba Cloud Bailian (Quanmiao) Video Analysis Skill. Use for intelligent video comprehension and analysis via the Bailian Quanmiao SDK.
  Triggers: "analyze video", "understand this video", "what is this video about", "summarize this video", "split video into shots", "video analysis", "video comprehension", "video summary", "video breakdown", "extract video insights", "transcribe video", "extract video captions", "generate video title", "generate video outline", "video mindmap", "analyze this video", "breakdown this video".
---

# Bailian (Quanmiao) Video Analysis

This skill provides video analysis functionality based on Alibaba Cloud Bailian (Quanmiao) Video Analysis Light Application. It uses the Bailian SDK for intelligent video comprehension, including shot analysis, ASR transcription, title generation, caption extraction, and mind mapping.

**Architecture:** `CLI (Credential Chain) + OSS (File Storage) + Bailian Workspace + Quanmiao Video Analysis Service + Python SDK Scripts`

---

## Installation

### Python Dependencies

```bash
cd scripts
pip install -r requirements.txt
```

### Alibaba Cloud CLI

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

---

## Environment Variables

The Bailian SDK relies on the Alibaba Cloud default credential chain. No additional environment variables are required if credentials are configured via CLI.

The credential chain resolves in this priority order:

1. **Environment variables:** `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
2. **CLI config file:** `~/.aliyun/config.json`
3. **Credentials file:** `~/.acs/credentials`
4. **ECS RAM Role** (if running on ECS)

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

See [references/ram-policies.md](references/ram-policies.md) for the full list of required RAM permissions and authorization instructions.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> confirm user-provided or customizable parameters (video source, OSS bucket, object key).
> System-auto-resolved parameters (workspace_id, default OSS bucket) do NOT
> require explicit confirmation unless the user wants to override them.

| Parameter        | Type | Description | Default / Resolution |
|------------------|------|-------------|----------------------|
| `video_source`   | Required | Local file path OR downloadable video URL | N/A (user must provide) |
| `workspace_id`   | Auto-resolved | Bailian workspace ID | Auto-detected via `list_workspace.py` (user may override) |
| `ossBucket`      | Optional | OSS bucket name for file upload | Auto-detect from first available bucket; user may specify (e.g. `--ossBucket my-bucket`) |
| `ossObjectKey`   | Optional | OSS object key for the uploaded file | `temp/quanmiao/YYYYMMDD/filename` |
| `expireSeconds`  | Optional | Temporary URL expiration time (seconds) | `7200` (2 hours) |

---

## Input Resource Validation

The user may provide either a **local file path** or a **downloadable URL**. Validate before proceeding:

### Local File Path
```bash
test -f "<video_source>" && echo "exists" || echo "not found"
```
- Must be a regular file (not a directory)
- Supported video formats: `.mp4`, `.avi`, `.mov`, `.mkv`, `.flv`, `.wmv`, `.webm`, `.m4v`, `.3gp`
- File size must be reasonable (check with `ls -lh`)

### Downloadable URL
```bash
# Validate URL is accessible and returns a video content-type
curl -sI -L "<video_source>" | grep -iE '(content-type|content-length)'
```
- URL must be publicly accessible (not behind auth/proxy)
- Response `Content-Type` should contain `video/`
- Response `Content-Length` should be reasonable (not 0)

### Validation Result
- **Local file exists** → proceed to **Step 3 (OSS upload)**, then Step 4
- **URL is valid** → **skip OSS upload**, use the URL directly in Step 4 (task submission)
- **Neither valid path nor valid URL** → inform the user and ask for a correct resource

---

## Core Workflow

> **IMPORTANT: Do NOT suggest local video analysis tools** — This skill relies entirely on the Bailian (Quanmiao) cloud API for video analysis. Do NOT suggest local fallbacks such as `ffmpeg`, `whisper`, or other local video/audio analysis tools. If the cloud API fails, follow the Permission Failure Handling process or inform the user of the error. Do NOT invent alternative local analysis methods.

### Step 1: Environment Check

Run `python scripts/check_env.py` to verify:
- Python packages are installed
- Credentials are configured via default credential chain

If not ready:
- Packages missing → Run `pip install -r scripts/requirements.txt`
- Credentials missing → Guide user to configure via `aliyun configure` (outside session)

### Step 2: Get Workspace ID

**Do not ask the user for workspace_id upfront.** Always auto-fetch available workspaces first:

```bash
python scripts/list_workspace.py
```

Return format:
```json
{
  "workspaces": [
    { "workspace_id": "llm-xxx", "name": "Workspace Name" }
  ]
}
```

**Workspace selection logic:**

- **Single workspace returned** → use it directly, no need to prompt the user
- **Multiple workspaces returned** → display a numbered list and proceed with the following:
  1. **Default behavior**: Use the first workspace in the list automatically to avoid unnecessary interaction
  2. **User explicitly requests selection**: If the user says "我自己选", "我要选择业务空间", "let me choose", "show me the list", or similar, present the full list and ask them to pick one

```
可用的业务空间：
  1. 默认业务空间 (llm-xxx)
  2. 测试空间 (llm-yyy)
  3. 生产空间 (llm-zzz)

默认使用「默认业务空间」，如需切换请选择编号，或回复 "auto" 使用默认。
```

- **No workspaces returned** → inform the user that no Bailian workspace is available, guide them to create one at the [Bailian Console](https://bailian.console.aliyun.com/)
- **Record user selection** in the session to avoid repeated inquiries

### Step 3: Upload File(video_source) to OSS

Based on the input resource type from Input Resource Validation:

**Case A: User provided a downloadable URL**
→ Skip this step. Use the video_source as `file_url` in Step 4.

**Case B: User provided a local file path**
→ Upload to OSS and get a temporary URL:

```bash
# Auto-detect OSS bucket (uses first available)
python scripts/quanmiao_upload_file_to_oss_and_get_file_url.py --localFilePath <video_source>

# User-specified OSS bucket
python scripts/quanmiao_upload_file_to_oss_and_get_file_url.py --localFilePath <video_source> --ossBucket <bucket_name>

# User-specified bucket, object key, and custom expiration
python scripts/quanmiao_upload_file_to_oss_and_get_file_url.py --localFilePath <video_source> --ossBucket <bucket_name> --ossObjectKey <custom_key> --expireSeconds <seconds>
```

Return format:
```json
{
  "status": "success",
  "ossBucket": "my-bucket",
  "ossObjectKey": "temp/quanmiao/20260409/video.mp4",
  "file_url": "https://xxx.oss-cn-beijing.aliyuncs.com/...",
  "expireSeconds": 7200
}
```

### Step 4: Submit Video Analysis Task

```bash
python scripts/quanmiao_submit_videoAnalysis_task.py --workspace_id <workspace_id> --file_url <file_url>
```

Return format:
```json
{ "task_id": "xxxx" }
```

### Step 5: Poll for Task Result

Video analysis is asynchronous. Poll until completion:

**Task Status:** `PENDING` → `RUNNING` → `SUCCESSED` | `FAILED` | `CANCELED`

1. Wait 10 seconds after submission
2. Run: `python scripts/quanmiao_get_videoAnalysis_task_result.py --workspace_id <workspace_id> --task_id <task_id>`
3. Check the returned `status` field:
   - **`SUCCESSED`** → proceed to Step 6 with the complete result
   - **`FAILED`** or **`CANCELED`** → check error message, inform user, stop
   - **`PENDING`** or **`RUNNING`** → display any partial results available, wait 10s, go to step 2
4. Max 180 retries (approximately 30 minutes)

### Step 5.1: Save Complete Result Locally

When the task reaches `SUCCESSED` status, save the full JSON result to a local file associated with the original video. This enables secondary analysis without re-calling the API.

**Save path convention:** `~/.quanmiao/results/<video_filename_without_ext>_<task_id>.json`

```bash
# Create results directory if it doesn't exist
mkdir -p ~/.quanmiao/results

# Derive filename from the original video source
# e.g. "xxxx.mp4" → "xxxx_52e52f93a17b46f1be0f14415aa07175.json"
echo '<FULL_JSON_RESULT>' > ~/.quanmiao/results/<video_name>_<task_id>.json
```

Also maintain a mapping file at `~/.quanmiao/results/index.jsonl` (append-only):
```json
{"task_id": "<task_id>", "video_source": "<original_path_or_url>", "workspace_id": "<workspace_id>", "result_file": "<saved_path>", "timestamp": "<ISO8601>"}
```

> **Before starting a new analysis**, check `~/.quanmiao/results/index.jsonl` for existing results matching the same video source. If found, offer the cached result to the user instead of re-running the analysis.

---

Return format:
```json
{ 
   "taskStatus": "SUCCESSED",
   "header": {
      "event": "task-finished",
      "eventInfo": "完成视频理解",
      "errorCode": "InvalidParam",
      "errorMessage": "视频地址有误：Server returned HTTP response code: 403 for URL: https://xx.mp41"
    },
   "payload": {
      "output": {
         "videoAnalysisResult": {},
         "videoGenerateResults": {
            "text": "视频分镜头分析结果.."
         },
         "videoTitleGenerateResult": {
            "text": "视频标题结果.."
         },
         "videoMindMappingGenerateResult": {
            "text": "视频大纲结果..",
            "videoMindMappings": []
         },
         "videoCalculatorResult": {
            "items":  []
         },
         "videoCaptionResult": {
            "videoCaptions": []
         }
      },
      "usage": {
            "inputTokens": 607,
            "outputTokens": 563,
            "totalTokens": 1512
        }
   }
}
```


### Step 6: Summarize Video Content

**Use the results from Step 5 directly. Do NOT call the API again.**

Extract data from the SUCCESSED response and summarize according to user requirements.

**If the user has a specific analysis request** (e.g., "analyze the speaker's body language", "extract key business insights", "compare two people in the video"), base your answer primarily on:

- **`payload.output.videoGenerateResults`** — scene-by-scene analysis, descriptions, interpretations
- **`payload.output.videoAnalysisResult.text`** — visual shot analysis, object/person recognition, action detection

Combine these two fields to construct a targeted answer. Supplement with other fields (captions, mind map, title) as context if relevant.

**If no specific request**, use the standard output format:

```markdown
# 视频理解结果

## 视频标题
{payload.output.videoTitleGenerateResult.text}

## 视频大纲
{payload.output.videoMindMappingGenerateResult.videoMindMappings 结构化展示}

## 视频总结
{payload.output.videoGenerateResults[0].text}

## 视频语音内容
{payload.output.videoCaptionResult.videoCaptions 按时间顺序展示}

## 视觉镜头分析
{payload.output.videoAnalysisResult.text 按镜头总结}

## 时间线总结
[基于 payload.output.videoAnalysisResult.text 提取关键事件（可选）]

## 总结
[综合分析 payload.output.videoGenerateResults 和 payload.output.videoAnalysisResult]

## Token消耗
- 总输入Token: {payload.usage.inputTokens}
- 总输出Token: {payload.usage.outputTokens}
- 总计Token: {payload.usage.totalTokens}
- 详细费用: {videoCalculatorResult.items 中各模型的费用明细}
```

---

## Success Verification

See [references/verification-method.md](references/verification-method.md) for step-by-step verification commands and expected outcomes.

---

## Cleanup

To clean up resources created by this skill:

1. **Delete uploaded OSS objects:**
   ```bash
   aliyun oss rm oss://<bucket>/<object-key> --user-agent AlibabaCloud-Agent-Skills
   ```

2. **Delete Bailian task records** (tasks are auto-cleaned by Bailian after retention period; no manual cleanup needed for task records)

3. **No workspace cleanup needed** — workspaces are shared resources and should not be deleted unless explicitly requested by the user

---

## Best Practices

1. **Always verify environment first** — run `check_env.py` before any other operation to catch missing dependencies or credentials early.
2. **Auto-detect workspace_id** — always fetch workspaces via `list_workspace.py`; default to the first result, but present a selection list when the user explicitly asks to choose.
3. **Use default OSS settings** — unless the user specifies a particular bucket, let the script auto-detect the bucket and generate the object key.
4. **Display partial results during polling** — when task status is `RUNNING`, show available results (title, captions) to give the user real-time feedback.
5. **Save complete result for summary** — when status becomes `SUCCESSED`, use the full result payload directly for Step 6 without re-calling the API.
6. **Respect URL expiration** — temporary OSS URLs expire after `expireSeconds` (default 7200s); ensure the task is submitted before the URL expires.
7. **Handle permission errors gracefully** — follow the Permission Failure Handling process in the RAM Policy section; never improvise credential fixes.

---

## Command Tables

See [references/related-commands.md](references/related-commands.md) for the full list of available scripts and their parameters.

---

## Reference Links

| Reference | Purpose |
|-----------|---------|
| `references/cli-installation-guide.md` | Installing and upgrading Aliyun CLI |
| `references/ram-policies.md` | RAM permission checklist and authorization guide |
| `references/acceptance-criteria.md` | Acceptance criteria and correct/incorrect usage patterns |
| `references/related-commands.md` | Available scripts and CLI command reference |
| `references/verification-method.md` | Step-by-step success verification commands |
