---
name: alibabacloud-bailian-video-creator
description: AI video creation skill supporting text-to-video, image-to-video, reference-to-video, video editing, and video understanding. Uses wan2.6-t2v, wan2.6-i2v, wan2.6-r2v-flash, wanx2.1-vace-plus, qwen3.5-plus and other models. Use this skill when users need to generate videos, edit videos, or analyze video content. Note: on first run, it will auto-manage DashScope API Keys (create/recycle) and may auto-install the Alibaba Cloud CLI ModelStudio plugin.
---

# AI Video Creator

Professional-grade AI video creation skill supporting text-to-video, image-to-video, video editing, and video understanding. Built on Alibaba Cloud DashScope API.

## Prompt Design Guide

The core formula for high-quality video prompts: `[Scene Overview] + [Shot Design] + [Camera Movement] + [Lighting & Atmosphere] + [Visual Style]`

Key elements: Camera language (shot size, movement, angle), shot rhythm design, lighting and atmosphere control, visual style reference. For multi-shot videos, use the shot list format `Shot N [start-end time] Shot description`.

Negative prompt template: `blurry, low quality, distorted, glitchy, unnatural movement, jumpy cuts, inconsistent lighting, artifacts, watermark, text overlay, static, frozen frames, uncanny valley`

> For detailed camera language reference tables, shot list templates, lighting styles, and complete prompt examples, refer to [references/prompt-guide.md](references/prompt-guide.md)

## Version

v2.1.0 (2026-03-10)

## Feature List

| Feature | Model | Status | Description |
|---------|-------|--------|-------------|
| Video Understanding | qwen3.5-plus | ✅ | Analyze video content with configurable frame extraction rate |
| Text-to-Video (Multi-shot) | wan2.6-t2v | ✅ | Generate multi-shot videos from text descriptions |
| Image-to-Video | wan2.6-i2v | ✅ | Generate video from image + audio |
| Reference-to-Video | wan2.6-r2v-flash | ✅ | Generate multi-character video from multiple reference materials (video/image) |
| Video Editing (Repainting) | wanx2.1-vace-plus | ✅ | Video repainting while preserving original motion/structure |
| Video Region Edit | wanx2.1-vace-plus | ✅ | Fine-grained editing of specific video regions |

**Note**: The DashScope qwen3.5-plus model's `image_url` type only supports static image analysis and does not support direct video file upload. To analyze video, extract key frames first and use the image analysis feature.

## Prerequisites

Before executing any task, the following checks must be completed:

1. **Verify API Key availability**: Run `from api_key import get_api_key; api_key = get_api_key()`. If `get_api_key()` raises an exception (including "quota exceeded", `AuthenticationError`, `InvalidApiKey`, `401`, etc.), **you must immediately stop execution and display the error message to the user** -- do not skip API calls, do not continue with subsequent steps, do not fabricate execution results
2. **Confirm remote API availability**: This skill completes all video generation and content analysis tasks via the DashScope remote API, without relying on local GPU, PyTorch, Stable Diffusion, etc. As long as the API Key is valid, the skill has full capabilities. **Do not claim inability to complete tasks just because local tools are missing**
3. **API Key security**: Never write the full API Key in plain text in script files, logs, or terminal output. Must read via the `api_key.py` module or environment variable `os.environ.get("DASHSCOPE_API_KEY")`. Display in masked form when debugging (e.g., `sk-***xxx`)

## Orchestration Logic

### Products and Services Involved

All APIs in this skill are called through **Alibaba Cloud DashScope (Bailian)**; no other cloud products are involved.

| Component | Purpose |
|-----------|---------|
| `scripts/api_key.py` | Unified API Key management (reads from `~/.aliyun/config.json` or environment variable) |
| DashScope Video Generation API | Text-to-video, image-to-video, reference-to-video, video editing (async) |
| DashScope MultiModalConversation API | Video understanding (sync) |
| FFmpeg (local tool) | Video format conversion, key frame extraction, and other pre/post-processing (optional) |

### Feature Selection Decision Tree

Select the corresponding feature based on the user's **input materials** and **intent**:

```
User Request
│
├─ User has an existing video to analyze/understand?
│   └─ YES → Video Understanding (video_understanding.py, qwen3.5-plus)
│
├─ User has an existing video to modify?
│   ├─ Modify a local region (has mask)?
│   │   └─ YES → Video Region Edit (video_local_edit.py, wanx2.1-vace-plus)
│   └─ Overall style repainting?
│       └─ YES → Video Editing (video_edit.py, wanx2.1-vace-plus)
│
├─ User has multiple reference materials (character videos/images) to synthesize?
│   └─ YES → Reference-to-Video (reference_to_video.py, wan2.6-r2v-flash)
│
├─ User has a single image to generate video from?
│   └─ YES → Image-to-Video (image_to_video.py, wan2.6-i2v)
│
└─ User only has a text description?
    └─ YES → Text-to-Video (text_to_video.py, wan2.6-t2v)
```

### Quick Reference Table

| User Input | Feature | Script | Model |
|------------|---------|--------|-------|
| Video URL + analysis question | Video Understanding | `video_understanding.py` | qwen3.5-plus |
| Pure text description | Text-to-Video | `text_to_video.py` | wan2.6-t2v |
| Image URL (± audio URL) | Image-to-Video | `image_to_video.py` | wan2.6-i2v |
| Multiple reference materials (video/image mix) | Reference-to-Video | `reference_to_video.py` | wan2.6-r2v-flash |
| Video URL + new style description | Video Editing | `video_edit.py` | wanx2.1-vace-plus |
| Video URL + mask image + edit description | Video Region Edit | `video_local_edit.py` | wanx2.1-vace-plus |

### Invocation Flow

**You must directly run existing scripts in the `scripts/` directory to complete tasks. Creating new scripts from scratch as replacements is forbidden.** Each feature has a corresponding executable script (see Quick Reference Table). Simply pass the correct parameters and run. The scripts internally encapsulate the complete flow of API Key retrieval, API calls, polling, and result output.

All features share a unified invocation pattern, divided into two categories:

**Synchronous call (Video Understanding)**:
```python
from dashscope import MultiModalConversation
response = MultiModalConversation.call(model="qwen3.5-plus", messages=[...])
# Returns analysis result directly
```

**Asynchronous call (All video generation/editing)**:

Step 1 -- Create task (obtain task_id):
```python
response = requests.post(
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
    headers={"Authorization": f"Bearer {api_key}", "X-DashScope-Async": "enable"},
    json={"model": "wan2.6-t2v", "input": {"prompt": prompt}, "parameters": {...}}
)
task_id = response.json()["output"]["task_id"]
```

Step 2 -- Poll task status (until SUCCEEDED or FAILED):
```python
import time
for _ in range(60):  # Poll up to 60 times, 10-second intervals
    result = requests.get(
        f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {api_key}"}
    ).json()
    status = result["output"]["task_status"]
    if status == "SUCCEEDED":
        video_url = result["output"]["video_url"]
        break
    elif status == "FAILED":
        raise RuntimeError(result["output"].get("message", "Task failed"))
    time.sleep(10)
```

Step 3 -- Verify result: Confirm that a valid `video_url` or analysis result has been obtained. Do not end execution prematurely before the task completes.

### Key Orchestration Rules

1. **API Key retrieval must come first**: All scripts call `get_api_key()` at module load time. If no valid Key is found, an error is raised immediately without making API requests
2. **Async tasks require polling**: Video generation typically takes 1-5 minutes; you must poll via `poll_result()` and wait for completion
3. **Prompt optimization**: For text-to-video and image-to-video, setting `prompt_extend=True` is recommended to let the model auto-rewrite prompts; for video editing/region edit, set to `False` to avoid rewrites deviating from original intent
4. **Video Editing vs Region Edit selection**:
   - User provided a mask image → Use Region Edit
   - User only described a new style without mask → Use Video Editing (Repainting)
5. **control_condition selection (Video Editing)**:
   - Need to preserve facial expressions + body movements → `posebodyface`
   - Only preserve body movements, change face → `posebody`
   - Preserve composition and motion trajectories → `depth` (default, most versatile)
   - Preserve line art structure → `scribble`

### Constraints

**All tasks must be completed via the DashScope remote API. Using local tools (OpenCV, PyTorch, Stable Diffusion, FFmpeg analysis, etc.) to replace DashScope API for video generation or content analysis is forbidden. Using third-party alternative services (such as Pollinations.ai, RunwayML, Pika, Luma, etc.) to replace DashScope API is forbidden. Claiming "no video generation capability" or "missing tools" is forbidden -- as long as the API Key is valid, this skill has full remote video generation and understanding capabilities.**

1. **API Key pre-check**: Before any API call, you must verify the API Key is configured via `get_api_key()`. If `get_api_key()` fails (including "quota exceeded", `401`, `InvalidApiKey`, etc.), you must **immediately stop and report the error** -- do not skip API calls, do not fabricate subsequent results
2. **Correct model names** (no other names may be used):

| Feature | Required Model | Incorrect Examples (Forbidden) |
|---------|---------------|-------------------------------|
| Text-to-Video | `wan2.6-t2v` | `wanx2.6-t2v`, `wanx2.1-t2v-plus`, `wanx-video-generation-v1` |
| Image-to-Video (HTTP API) | `wan2.6-i2v` | - |
| Image-to-Video (SDK) | `wan2.6-i2v-flash` | - |
| Reference-to-Video | `wan2.6-r2v-flash` | - |
| Video Editing/Region Edit | `wanx2.1-vace-plus` | - |
| Video Understanding | `qwen3.5-plus` | `qwen-vl-plus`, `qwen-vl-max-latest` |

3. **Async tasks must be polled to completion**: After creating a task, you must poll `task_status` until `SUCCEEDED` or `FAILED`. Do not end prematurely before the task completes. If task creation fails (e.g., 401 error), you must report the error clearly and prompt the user to check API Key -- do not silently terminate
4. **Final result must be verified**: Confirm that a valid `video_url` (video generation) or analysis text (video understanding) has been obtained. Do not return empty results. **If the API call failed or was not actually executed, you must honestly report the error. Fabricating analysis results or fictitious video URLs is forbidden**
5. **API Key security**: Never write the full API Key in plain text in generated scripts, logs, or terminal commands. Specific rules:

   ❌ **Forbidden** (none of the following are allowed):
   ```python
   api_key = "sk-abc123..."                          # Hardcoding forbidden
   headers = {"Authorization": "Bearer sk-abc123..."}  # Plain text forbidden
   ```
   ```bash
   export DASHSCOPE_API_KEY="sk-abc123..."            # Plain text export in scripts forbidden
   ```

   ✅ **Correct** (must use the following methods):
   ```python
   from api_key import get_api_key
   api_key = get_api_key()                            # Securely obtained via module
   # or
   api_key = os.environ.get("DASHSCOPE_API_KEY")      # Obtained via environment variable
   ```

6. **No fabricating results**: If the DashScope API call was not actually executed or execution failed, you must clearly inform the user of the failure reason. Do not fabricate video analysis text, fictitious video URLs, or claim task completion when api.json is empty. **Writing a script containing API call code ≠ actually executing the API call. The standard: only when the script is actually run and the DashScope API (e.g., `MultiModalConversation.call` or `dashscope.aliyuncs.com/api/v1/...`) returns a real result can you claim task completion. API Key management calls (ListWorkspaces, CreateApiKey) do not count as task completion**
7. **Third-party alternative services forbidden**: All video generation and understanding tasks must be completed via DashScope API. Calling Pollinations.ai, RunwayML, Pika, Luma, Kling, or other third-party services as alternatives is forbidden
8. **Output file verification**: Before claiming task completion, you must confirm that actual output files have been written to disk (e.g., `video_analysis_result.txt`, downloaded video files, etc.). If the file does not exist or is empty, you must report failure
9. **Must use existing scripts and actually execute them**: Use existing scripts in the `scripts/` directory (e.g., `python scripts/video_understanding.py`). Creating new scripts from scratch as replacements is forbidden. Scripts must be actually executed (`python scripts/xxx.py`), and real stdout/stderr output must be captured as the basis for results. If script execution encounters errors, you must display the real error message

## Environment Setup

### 1. Install FFmpeg (Video Processing Tool)

FFmpeg is used for video format conversion, key frame extraction, video trimming/concatenation, and other local processing.

```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg

# Windows (Scoop)
scoop install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

### 2. Install Python Dependencies

```bash
pip install -r scripts/requirements.txt
```

| Package | Version Constraint | Purpose |
|---------|-------------------|---------|
| `dashscope` | `>=1.25.0,<2.0.0` | SDK-based image-to-video, video understanding |
| `requests` | `>=2.20.0,<3.0.0` | HTTP API-based video generation/editing |

### 3. Configure API Key

API Key is managed through the unified `scripts/api_key.py` module with three-tier retrieval logic:
1. Read `~/.aliyun/config.json` current profile's `dashscope.api_key` → return if found
2. Read environment variable `DASHSCOPE_API_KEY` → return if found
3. Detect Alibaba Cloud CLI available → auto-call `generate_api_key()` to create Key and save to config → return
4. All fail → raise error (with CLI installation instructions)

```python
# All scripts use this unified approach
from api_key import get_api_key
api_key = get_api_key()
```

Manual environment variable configuration:
```bash
export DASHSCOPE_API_KEY=sk-xxx
```

| Item | Description |
|------|-------------|
| **Key format** | `sk-xxx` (standard DashScope API Key) |
| **Not usable** | `sk-sp-xxx` (Coding Plan exclusive Key, does not support video generation) |
| **Obtain at** | https://bailian.console.aliyun.com/cn-beijing/?tab=app#/api-key |

### 4. Alibaba Cloud CLI Configuration (API Key Auto-Create/Delete)

This skill's `scripts/api_key.py` uses `aliyun modelstudio` commands to automatically create and delete API Keys. Complete the following configuration before use:

**1. Enable AI-Mode and update plugins**

```bash
# Enable AI-Mode (allow Agent to call CLI)
aliyun configure ai-mode enable

# Set User-Agent
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bailian-video-creator"

# Update plugins to latest version
aliyun plugin update
```

**2. Install ModelStudio plugin** (if not already installed)

```bash
aliyun plugin install --names aliyun-cli-modelstudio --enable-pre
```

**3. Disable AI-Mode after task completion**

```bash
aliyun configure ai-mode disable
```

**CLI commands involved**:

| Command | Purpose | Call Location |
|---------|---------|--------------|
| `aliyun modelstudio list-workspaces` | Get Bailian Workspace ID | `api_key.py: _get_workspace_id()` |
| `aliyun modelstudio create-api-key` | Create DashScope API Key | `api_key.py: generate_api_key()` |
| `aliyun modelstudio delete-api-key` | Delete cloud API Key | `api_key.py: delete_api_key()` |

## Directory Structure

```
alibabacloud-bailian-video-creator/
├── scripts/           # Example code (7 core features + API Key management)
│   ├── requirements.txt
│   ├── api_key.py
│   ├── video_understanding.py
│   ├── text_to_video.py
│   ├── image_to_video.py
│   ├── image_to_video_sdk.py
│   ├── reference_to_video.py
│   ├── video_edit.py
│   └── video_local_edit.py
├── references/        # Reference materials
│   ├── prompt-guide.md
│   ├── api-docs.md
│   ├── models.md
│   └── error-codes.md
└── SKILL.md
```

**Notes**:
- `scripts/` - Contains only official example code, one file per feature
- `references/` - Prompt guide, API documentation, model list, error codes, and other reference materials

## Usage Examples

Run any script directly to see detailed parameter descriptions (`python scripts/<script_name>.py`).

| Feature | Script | Key Parameters |
|---------|--------|---------------|
| Video Understanding | `video_understanding.py` | `video_url`, `prompt`, `fps` |
| Text-to-Video | `text_to_video.py` | `prompt` (with shot list), `duration`, `size` |
| Image-to-Video (HTTP) | `image_to_video.py` | `prompt`, `img_url`, `audio_url`, `resolution` |
| Image-to-Video (SDK) | `image_to_video_sdk.py` | `prompt`, `img_url`, `audio_url`, `duration` |
| Reference-to-Video | `reference_to_video.py` | `prompt` (with Character references), `reference_urls` |
| Video Editing | `video_edit.py` | `prompt`, `video_url`, `control_condition` |
| Video Region Edit | `video_local_edit.py` | `prompt`, `video_url`, `mask_image_url`, `mask_type` |

## Region URLs

API URLs differ by region. Choose based on your actual needs:

| Region | URL |
|--------|-----|
| Beijing | https://dashscope.aliyuncs.com/api/v1 |
| Virginia | https://dashscope-us.aliyuncs.com/api/v1 |
| Singapore | https://dashscope-intl.aliyuncs.com/api/v1 |

## Billing

### Video Generation Billing

Billed by the duration (seconds) of successfully generated videos. Failed requests are not billed.

#### Text-to-Video (wan2.6-t2v)

| Resolution | Unit Price |
|------------|-----------|
| 720P | ¥0.6/sec |
| 1080P | ¥1.0/sec |

**Billing examples**:
- Generate 10-second 720P video → ¥6.00
- Generate 10-second 1080P video → ¥10.00

#### Image-to-Video / Reference-to-Video (wan2.6-i2v-flash / wan2.6-r2v-flash)

| Resolution | Video Type | Unit Price |
|------------|-----------|-----------|
| 720P | With audio | ¥0.3/sec |
| 720P | Silent | ¥0.15/sec |
| 1080P | With audio | ¥0.5/sec |
| 1080P | Silent | ¥0.25/sec |

**Note**: Reference-to-video is billed by input + output total duration. Input video is billed for a maximum of 5 seconds.

#### Video Editing (wanx2.1-vace-plus)

| Resolution | Unit Price |
|------------|-----------|
| 720P | ¥0.72/sec |

**View billing**: https://usercenter2.aliyun.com/finance/expense-center/overview

### Free Quota

New users receive upon activating Bailian:
- 50 seconds of free video quota
- Valid for: 90 days after activation

## References

- [Text-to-Video API Documentation](https://help.aliyun.com/zh/model-studio/text-to-video-api-reference)
- [Image-to-Video API Documentation](https://help.aliyun.com/zh/model-studio/image-to-video-api-reference)
- [Video Editing API Documentation](https://help.aliyun.com/zh/model-studio/wanx-vace-api-reference)
- [Model List](https://help.aliyun.com/zh/model-studio/models)
