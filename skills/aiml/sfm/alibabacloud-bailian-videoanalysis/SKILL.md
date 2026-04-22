---
name: alibabacloud-bailian-videoanalysis
description: |
  Alibaba Cloud Bailian Video Analysis Skill. Use for intelligent video comprehension and analysis via the Bailian (QuanMiaoLightApp) API.
  **Required API Product**: QuanMiaoLightApp (version 2024-08-01)
  **Required API Actions**: SubmitVideoAnalysisTask, GetVideoAnalysisTask
  **DO NOT use**: videorecog, Mts, or any other product for video analysis
  Triggers: "analyze video", "understand video", "analyze the local video /temp/xxx.mp4", "analyze the local video https://xxx.com/temp/xxx.mp4", "what is this video about", "summarize this video", "split video into shots", "video comprehension", "extract video insights", "transcribe video", "extract video captions", "generate video title", "generate video outline", "video mindmap".
---

# Bailian Video Analysis

This skill provides video analysis functionality based on Alibaba Cloud Bailian Video Analysis Light Application. It uses the Bailian (QuanMiaoLightApp) API for intelligent video comprehension, including shot analysis, ASR transcription, title generation, caption extraction, and mind mapping.

**Architecture:** `CLI (Credential Chain) + OSS (File Storage) + Bailian Workspace + Quanmiao Video Analysis Service + Python SDK Scripts`

---

## Output Language Policy

**Detection Priority:** User input language → Environment language → **Default: Chinese (中文)**

**Apply to:** All user-facing messages, summaries, error explanations, and interactive prompts.

**Keep original language:** Code snippets, API responses, file paths, technical identifiers, HTTP status codes.

---

## Installation

### 1. Python Dependencies

```bash
python -m pip install -r scripts/requirements.txt
# On some systems, use pyhon3 instead of python
```

### 2. Alibaba Cloud CLI

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

> **AI-Mode Configuration for aliyun CLI**
>
> When using the aliyun CLI in this skill, you MUST configure AI-Mode settings:
>
> ```bash
> # Enable AI-Mode (required before using CLI commands)
> aliyun configure ai-mode enable
>
> # Set User-Agent for tracking (required)
> aliyun configure ai-mode set-user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis
>
> # Update plugins to latest versions (recommended)
> aliyun plugin update
> ```
>
> **Note:** After completing your tasks, you can disable AI-Mode:
> ```bash
> aliyun configure ai-mode disable
> ```

### 3. Important Prerequisite: Activate Bailian and Video Analysis Service

**Before using this skill, you must first activate the Video Analysis service in the Alibaba Cloud Bailian console!**

1. Visit [Bailian Video_Analysis page](https://bailian.console.aliyun.com/cn-beijing#/app/app-market/quanmiao/video-comprehend)
2. Click the **"Paid activation"** button
3. Confirm activation and wait for the service to take effect (usually 1-2 minutes)

### 4. Important Prerequisite: Guide Users to Grant Permissions in Alibaba Cloud Access Control and Bailian

**Before using this skill, you must grant the following permissions to the previously configured AK, otherwise calls will fail and may cause 403 errors**

#### 1) RAM Permission Grant
See [references/ram-policies.md](references/ram-policies.md) for the full list of required RAM permissions and authorization instructions.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

#### 2) Bailian Workspace Permission Grant
1. Visit [Alibaba Cloud Bailian Permission Management](https://bailian.console.aliyun.com/cn-beijing?tab=app#/authority)
2. If the RAM user corresponding to the AK does not exist, click **"Add User"** in the upper right corner of the page, select the corresponding RAM user and click confirm to add.
3. There is a 30s effective time after configuration, please wait patiently for a while.

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

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> confirm user-provided or customizable parameters (video source, OSS bucket, oss object key).
> System-auto-resolved parameters (workspace_id, default OSS bucket) do NOT
> require explicit confirmation unless the user wants to override them.

| Parameter        | Type          | Description                               | Default / Resolution                                                                     |
|------------------|---------------|-------------------------------------------|------------------------------------------------------------------------------------------|
| `video_source`   | Required      | Local file path OR downloadable video URL | N/A (user must provide)                                                                  |
| `workspace_id`   | Auto-resolved | Bailian workspace ID                      | Auto-detected(user may override)                                                         |
| `ossBucket`      | Optional      | OSS bucket name for file upload           | Auto-detect from first available bucket; user may specify (e.g. `--ossBucket my-bucket`) |
| `ossObjectKey`   | Optional      | OSS object key for the uploaded file      | `/temp/quanmiao/YYYYMMDD/filename`                                                       |
| `expireSeconds`  | Optional      | Temporary URL expiration time (seconds)   | `14400` (4 hours)                                                                        |

**Confirmation Workflow:**
1. **Auto-detection first**: The skill will auto-detect `workspace_id` and `ossBucket` when possible
2. **User override**: If user wants to specify custom values, confirm before using
3. **Local vs URL**: Confirm whether user is providing a local file path or a public URL

---

## Core Workflow

> **⚠️ CRITICAL: Cloud API Mandatory** — This skill MUST use Bailian (QuanMiaoLightApp) API for video analysis. Local tools (ffmpeg, whisper, OpenCV, ffprobe, mediainfo, etc.) are FORBIDDEN. If API calls fail due to credentials or permissions, follow Permission Failure Handling process — DO NOT fall back to local analysis.

### Step 1: Environment Check

Run `python scripts/check_env.py` to verify:
- Python packages are installed
- Credentials are configured via default credential chain

**If check_env.py fails or returns {"ready": false}**:
- Packages missing → Run `python -m pip install -r scripts/requirements.txt`
- Credentials missing or invalid → **Follow Permission Failure Handling process**:
  1. Read `references/ram-policies.md` to get required permissions
  2. Use `ram-permission-diagnose` skill to guide user through permission request
  3. Wait for user confirmation before proceeding
  4. DO NOT proceed with local analysis tools

**Expected output:** `{"ready": true}` indicates environment is properly configured.

### Step 2: Get Workspace ID

**Do not ask the user for workspace_id upfront.** Always auto-fetch available workspaces first:

```bash
aliyun modelstudio list-workspaces --user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis
```

**Workspace selection logic:**

- **Single workspace returned** → use it directly, no need to prompt the user
- **Multiple workspaces returned** → display a numbered list and proceed with the following:
  1. **Default behavior**: Use the first workspace in the list automatically to avoid unnecessary interaction
  2. **User explicitly requests selection**: If the user says "let me choose workspace", "show me the workspace list", or similar, present the full list and ask them to pick one
- **No workspaces returned** → inform the user that no Bailian workspace is available, guide them to create one at the [Bailian Console](https://bailian.console.aliyun.com/)
- **Record user selection** in the session to avoid repeated inquiries

### Step 3: Upload File(video_source) to OSS

Based on the input resource type from Input Resource Validation:

**Case A: User provided a downloadable URL**
→ Verify URL accessibility: Test if the URL is downloadable using appropriate method for your OS
→ Skip this step. Use the video_source as `file_url` in Step 4.

**Case B: User provided a local file path**
→ Auto-detects OSS bucket、Upload local file to OSS and get a temporary URL(file_url) for Step 4:

- **(1) Auto-detect or use user-specified OSS bucket**:
  - If user specifies `--ossBucket <bucket_name>`, attempt to use that bucket
  - **If the specified bucket returns 403 AccessDenied or BucketAlreadyExists**: DO NOT switch to another bucket automatically. Instead:
    1. Inform the user that the specified bucket is not accessible
    2. Follow the Permission Failure Handling process in RAM Policy section
    3. Guide user to grant OSS bucket access permissions or specify an alternative bucket they own
    4. Wait for user confirmation before proceeding
  - If no bucket specified, auto-detect from first available bucket

```bash
aliyun ossutil ls --user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis
```

- **(2) Upload file to OSS**: Generate a unique key(oss_object_key) for the uploaded file.

**IMPORTANT - Upload Path Restriction:**
- **Default path**: MUST use `/temp/quanmiao/YYYYMMDD/filename` format (auto-generated with current date)
- **Custom path**: ONLY if user explicitly specifies a custom oss_object_key, otherwise always use default path
- **Security rule**: NEVER upload files outside `/temp/quanmiao/` prefix unless user explicitly requests it

```bash
aliyun ossutil cp <video_source> oss://{oss_bucket}/{oss_object_key} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis --region {oss_region}
```

- **(3) Generate temporary URL**: Generate a temporary URL for the uploaded file using the `ossutil sign` command.
  - `--expireSeconds`: Default 14400s (4 hours), confirm if different value needed

```bash
aliyun ossutil sign oss://{oss_bucket}/{oss_object_key} --expires-duration {expire_seconds} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis --region {oss_region}
```

- **(4) Verify URL accessibility**: Test if the generated URL is downloadable using appropriate method for your OS
    - **Note**: Prefer GET request over HEAD request for verification, as some OSS signature versions may reject HEAD requests.

**Recommended validation URL downloadable methods:**
- **macOS/Linux**: `curl -L --connect-timeout 10 --max-time 30 -o /dev/null -w "%{http_code}" <file_url>` (returns HTTP status code)
- **Windows**: `Invoke-WebRequest -Uri <file_url> -Method Head -TimeoutSec 30` (PowerShell)

**Validation criteria:**
- **HTTP 200** → URL is valid and accessible, proceed to Step 4
- **HTTP 403/404** → URL expired or invalid, regenerate with `ossutil sign`
- **Other errors** → Check network or OSS permissions

### Step 4: Submit Video Analysis Task

> **⚠️ MANDATORY API CALL** — You MUST call SubmitVideoAnalysisTask on QuanMiaoLightApp product (version 2024-08-01). Do NOT use videorecog, Mts, or any other product. Do NOT attempt local analysis.

> **API Selection Checklist** — Before calling, verify:
> - ✅ Product: QuanMiaoLightApp (NOT videorecog, NOT Mts)
> - ✅ Version: 2024-08-01
> - ✅ Action: SubmitVideoAnalysisTask
> - ✅ Parameters: workspace_id, file_url

```bash
python scripts/quanmiao_submit_videoAnalysis_task.py --workspace_id <workspace_id> --file_url <file_url>
```

**Parameters requiring confirmation:**
- `--workspace_id`: From Step 2 (confirm with user)
- `--file_url`: From Step 3 upload result or user-provided URL (confirm validity)

**Error Handling**:
- If API returns 401 InvalidApiKey or 403 AccessDenied: **STOP** and follow Permission Failure Handling process
- Do NOT attempt alternative APIs or local tools
- Inform user: "Video analysis requires Bailian service activation and proper RAM permissions. Please follow the permission grant guide."

Returns `task_id` for polling.

### Step 5: Poll for Task Result

> **⚠️ MANDATORY API CALL** — You MUST poll GetVideoAnalysisTask on QuanMiaoLightApp product (version 2024-08-01) until status is SUCCESSED. Do NOT generate summary from local tools or filename inference.

Video analysis is asynchronous. Poll until completion:

**Task Status:** `PENDING` → `RUNNING` → `SUCCESSED` | `FAILED` | `CANCELED`

**Variables:**
- `result_json_path`: `~/.quanmiao/videoanalysis/<video_filename_without_ext>_<task_id>.json`
- `index_file`: `~/.quanmiao/videoanalysis/index.jsonl`

**Polling Loop:**
1. Wait 10 seconds after submission
2. Run: `python scripts/quanmiao_get_videoAnalysis_task_result.py --workspace_id <workspace_id> --task_id <task_id> --save_path <result_json_path>`
3. Check the returned `status` field:
   - **`SUCCESSED`** → Script auto-saves JSON to `result_json_path`, append entry to `index_file`, display saved locations, then proceed to Step 6
   - **`FAILED`** or **`CANCELED`** → check error message, inform user, stop
   - **`PENDING`** or **`RUNNING`** → display any partial results available, wait 10s, repeat from step 2
4. Max 180 retries (approximately 30 minutes)

**When taskStatus = SUCCESSED:**

1. **Append to index file** (`index_file`):
    ```json
    {"task_id": "<task_id>", "video_source": "<original_path_or_url>", "workspace_id": "<workspace_id>", "result_file": "<result_json_path>", "timestamp": "<ISO8601>"}
    ```

2. **Display saved locations:**
```
✅ Files saved successfully:
- Raw JSON result: <result_json_path>
- Index updated: <index_file>
```

**Parameters requiring confirmation:**
- `--workspace_id`: Same as Step 4 (confirm consistency)
- `--task_id`: From Step 4 submission result (verify before polling)

### Step 6: Summarize Video Content

**CRITICAL: Use the results from Step 5 directly. Do NOT call the API again. Do NOT re-execute any analysis.**

Extract data from the SUCCESSED response obtained in Step 5 and summarize according to user requirements.

**Case A: If the user has a specific analysis request** (e.g., "analyze the speaker's body language", "extract key business insights", "compare two people in the video"), base your answer primarily on:
- **`payload.output.videoGenerateResults`** — scene-by-scene analysis, descriptions, interpretations
- **`payload.output.videoAnalysisResult.text`** — visual shot analysis, object/person recognition, action detection
Combine these fields to construct a targeted answer. Supplement with other fields (captions, mind map, title) as context if relevant.

**Case B: If no specific request**, use the standard output format: Title → Outline → Summary → Captions → Shot Analysis → Timeline → Token Usage

---

## Important Constraints

- **Cloud-only:** No local fallbacks (ffmpeg, whisper, etc.). If cloud API fails, follow Permission Failure Handling process.
- **Violation Consequence:** Using local tools instead of QuanMiaoLightApp API will result in task failure.
- **Security:** Never expose credentials in logs or prompts
- **Permissions:** On auth errors, see `ram-policies.md`
- **Caching:** Check `~/.quanmiao/videoanalysis/index.jsonl` before re-analyzing same video

---

## Success Verification

See [references/verification-method.md](references/verification-method.md) for step-by-step verification commands and expected outcomes.

---

## Cleanup

To clean up resources created by this skill:

**Delete uploaded OSS objects:**
```bash
aliyun ossutil rm oss://{oss_bucket}/{oss_object_key} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis
```

**Cleanup best practices:**
- Confirm bucket name and oss object key before deletion
- Only delete objects with `/temp/quanmiao/` prefix to avoid accidental data loss
- Cached results at `~/.quanmiao/videoanalysis/` can be kept for future reference or deleted manually

---

## Best Practices

1. **Always verify environment first** — run `check_env.py` before any other operation to catch missing dependencies or credentials early.
2. **Auto-detect workspace_id** — always fetch workspaces via `list-workspaces`; default to the first result, but present a selection list when the user explicitly asks to choose.
3. **Use default OSS settings** — unless the user specifies a particular bucket, let the script auto-detect the bucket and generate the oss object key.
4. **Display partial results during polling** — when task status is `RUNNING`, show available results (title, captions) to give the user real-time feedback.
5. **Save complete result for summary** — when status becomes `SUCCESSED`, use the full result payload directly for Step 6 without re-calling the API.
6. **Respect URL expiration** — temporary OSS URLs expire after `expireSeconds` (default 14400s); ensure the task is submitted before the URL expires.
7. **Handle permission errors gracefully** — follow the Permission Failure Handling process in the RAM Policy section; never improvise credential fixes.

---

## Command Tables

See [references/related-commands.md](references/related-commands.md) for the full list of available scripts and their parameters.

---

## Reference Links

| Reference                                | Purpose                                                  |
|------------------------------------------|----------------------------------------------------------|
| `references/cli-installation-guide.md`   | Installing and upgrading Aliyun CLI                      |
| `references/ram-policies.md`             | RAM permission checklist and authorization guide         |
| `references/acceptance-criteria.md`      | Acceptance criteria and correct/incorrect usage patterns |
| `references/related-commands.md`         | Available scripts and CLI command reference              |
| `references/verification-method.md`      | Step-by-step success verification commands               |

---

## Troubleshooting

**Common scenarios:**
- **Permission denied** → See [ram-policies.md](references/ram-policies.md)
- **CLI not found** → See [cli-installation-guide.md](references/cli-installation-guide.md)
- **Workspace not found** → Create at [Bailian Console](https://bailian.console.aliyun.com/)
- **Upload failed** → Check OSS bucket permissions
- **Task timeout** → Video too large or network issues

---