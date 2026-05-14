---
name: alibabacloud-bailian-image-creator
description: AI image creation skill supporting text-to-image, image editing, image understanding, and more. Uses qwen-image-2.0-pro, wan2.7-image, qwen3.5-plus and other models. Use this skill when users need to generate images, edit images, analyze image content, or perform image-related tasks. Note: on first run, it will auto-manage DashScope API Keys (create/recycle) and may auto-install the Alibaba Cloud CLI ModelStudio plugin.
---

# AI Image Creator

Professional-grade AI image creation skill built on Alibaba Cloud DashScope API.

> **Warning: Before executing any image task, you must read and follow the "Mandatory Rules" section. Violations will cause task failure.**

## Mandatory Rules

### First Principle: Must Use Existing Scripts

**All image generation, editing, and understanding tasks must and can only be completed by running existing scripts in the `scripts/` directory.**

- **Do NOT write your own API call code** -- Do not create new Python scripts to call DashScope API. You must use the scripts specified in the "Task-to-Script Mapping" table below
- **Do NOT use PIL/Pillow or other local libraries** for image generation or editing (only allowed for auxiliary operations such as size validation)
- **Do NOT use third-party APIs** -- Including but not limited to Pollinations.ai, Stability.ai, DALL-E, Midjourney
- **Do NOT create mock/simulated scripts** -- Do not bypass real API calls in any way
- **Do NOT use deprecated models** -- `wanx-v1`, `wanx-v2`, `wan2.6-image` and other legacy models are discontinued
- **Do NOT mix APIs** -- Qwen models (qwen-*) can only use `MultiModalConversation.call()`, Wanx models (wan2.7-*) can only use `ImageGeneration.call()`
- **Do NOT use curl to call DashScope REST API** -- Must call through provided scripts, do not write shell scripts as substitutes
- **Do NOT generate placeholder/blank images** -- Do not use hardcoded byte streams, blank canvases, or PIL-scaled images to impersonate API-generated images
- **Do NOT claim success when API calls fail** -- Must truthfully report failure reasons, do not generate false success reports

### Task-to-Script Mapping (The Only Execution Method)

Based on user request keywords, look up the table to select the script. **No other methods are allowed**:

| User Request Keywords | Script | API | Default Model |
|----------------------|--------|-----|---------------|
| Wanx, wan2.7, reference image + generation, style fusion, multi-image fusion, graffiti-on-car, virtual try-on | `wanx_generate.py` | `ImageGeneration.call()` | `wan2.7-image` |
| 4K HD text-to-image | `wanx_generate.py` | `ImageGeneration.call()` | `wan2.7-image-pro` |
| A set of coherent images, image series generation | `wanx_generate.py` | `ImageGeneration.call()` | `wan2.7-image-pro` |
| Text-to-image, generate image, draw a picture (no reference image) | `text_to_image.py` | `MultiModalConversation.call()` | `qwen-image-2.0-pro` |
| Edit image (URL input) | `image_edit.py` | `MultiModalConversation.call()` | `qwen-image-edit-max` |
| Edit image (local file) | `image_edit_base64.py` | `MultiModalConversation.call()` | `qwen-image-edit-max` |
| Analyze/understand image content, describe image | `image_understanding.py` | `chat.completions.create()` | `qwen3.5-plus` |

**Disambiguation Priority Rules** (when multiple keywords match simultaneously):
1. User mentions "Wanx" or "wan2.7" -> Use `wanx_generate.py` directly, regardless of whether "generate image" or similar words are present
2. User provides **reference image URLs** and requests generating a new image -> Use `wanx_generate.py` (Wanx supports multi-image reference input)
3. Text description only, no reference image -> Use `text_to_image.py`

**Allowed Models**:

| Script | Allowed Models |
|--------|---------------|
| `text_to_image.py` | `qwen-image-2.0-pro`, `qwen-image-2.0` |
| `wanx_generate.py` | `wan2.7-image-pro`, `wan2.7-image` |
| `image_edit.py` / `image_edit_base64.py` | `qwen-image-edit-max`, `qwen-image-2.0-pro`, `qwen-image-edit-plus`, `qwen-image-edit` |
| `image_understanding.py` | `qwen3.5-plus`, `qwen-vl-max`, `qwen-vl-plus` |

### API Key Security Management

**Scripts automatically handle key retrieval via `api_key.py`. The Agent does not need to and should not manually extract, set, or pass API Key values.**

1. **Key retrieval is automated**: Scripts internally call `api_key.py` to automatically obtain keys from config files/environment variables, or auto-create via CLI. The Agent only needs to run the script command
2. **Never hardcode any form of key**: Including `api_key = "sk-..."`, `export DASHSCOPE_API_KEY="sk-..."`, and assigning keys in shell scripts
3. **Never extract keys from CLI output**: The key value returned by `aliyun modelstudio create-api-key` is automatically saved by `api_key.py`. The Agent must not write this value into any script, variable, or file
4. **Never expose keys in any output**: Including generated scripts, shell commands, log files (summary.md, task_summary.md, execution_log.md, etc.), and terminal output containing strings starting with `sk-`
5. **Never read or print keys from config files**: Do not use `cat ~/.aliyun/config.json`, `jq`, `python -c`, or other commands to read and output API Key values from config files
6. **Never directly call CLI key commands**: Do not directly run `aliyun modelstudio create-api-key` or `aliyun modelstudio list-api-keys`. These commands are only called internally by `api_key.py`
7. **Mandatory self-check before task completion**: Run `grep -rn "sk-" <output_directory>/` to check all output files; if any strings starting with `sk-` are found (excluding "sk-xxx" placeholders), delete the affected files and regenerate

### API Call Result Validation

1. **Check status code**: API response `status_code` must be `200`, otherwise abort the task
2. **Check output content**: Response must contain valid image URLs (starting with `http`). No valid URL means failure
3. **Never fabricate results**: Do not generate simulated data, false success reports, or placeholder image URLs
4. **Never mock/simulate**: Do not create mock scripts or simulate API calls to bypass real calls
5. **Correct behavior on failure**:
   - Print error information (status code, error code, error message)
   - Stop executing subsequent steps
   - If it's a key issue, `api_key.py` will automatically retry creation
   - If retries still fail, report the real error reason without concealment

### Output Validation (Must execute before reporting task completion)

1. **Check output files**: Confirm image files exist in the output directory and have reasonable size (typically > 10KB)
2. **Key leak scan**: Run `grep -rn "sk-" <output_directory>/` to check all output files (including logs, summaries, scripts). If leaks are found, delete and regenerate
3. **No false claims**: If API calls actually failed or were not executed, do not claim success in the task summary (e.g., listing checkmarks)
4. **Blank image detection**: If output images are blank, solid color, or merely scaled versions of input images, treat as task failure

### Output Size Control

| Model Family | Size Format | Supported Values |
|-------------|-------------|------------------|
| `qwen-image-2.0-pro` / `qwen-image-2.0` (text-to-image) | `"width*height"` | `1024*1024`, `720*1280`, `1280*720`, `1440*720`, `720*1440` |
| `qwen-image-edit-*` / `qwen-image-2.0-pro` (editing) | `"width*height"` | Width and height each [512, 2048], freely combined |
| `wan2.7-image-pro` (text-to-image) | Preset tier | `1K`, `2K`, `4K` |
| `wan2.7-image-pro` (editing/series) | Preset tier | `1K`, `2K` |
| `wan2.7-image` | Preset tier | `1K`, `2K` |

**Mapping Rules**:
1. User requests exact pixels (e.g., `1280x720`) -> Choose Qwen series, set `size='1280*720'`
2. User requests portrait/landscape -> Use the closest fixed size for Qwen text-to-image (e.g., portrait -> `720*1280`)
3. Wanx models -> `size` can only be `1K`/`2K`/`4K`, not pixel values

---

## Execution Flow

### Step 1: Install Dependencies

```bash
pip install -r scripts/requirements.txt
```

### Step 2: Select and Run Script Based on "Task-to-Script Mapping" Table

**Selection Logic**: First check if the user mentions "Wanx"/"wan2.7" or provides reference image URLs -> If yes, use `wanx_generate.py`; otherwise match by other keywords in the mapping table.

API Key is automatically managed by scripts (three-level retrieval: config file -> environment variable -> auto-create). **No manual key handling is needed**. The Agent only needs to run the commands in the table below. Do not write your own scripts, set environment variables, or use curl to call APIs.

| Scenario | Command | Example |
|----------|---------|---------|
| Text-to-image (Qwen) | `python scripts/text_to_image.py <prompt> [size] [model]` | `python scripts/text_to_image.py 'An orange cat sitting on a windowsill, 8K' 1024*1024 qwen-image-2.0-pro` |
| Text-to-image / Multi-image fusion (Wanx) | `python scripts/wanx_generate.py <prompt> [ref_image_URLs...]` | `python scripts/wanx_generate.py 'Paint the graffiti from image 2 on the car in image 1' url1 url2` |
| Image editing (URL input) | `python scripts/image_edit.py <instruction> <image_URL1> [URL2] [URL3]` | `python scripts/image_edit.py 'Change the background to white' https://example.com/photo.png` |
| Image editing (local file) | `python scripts/image_edit_base64.py <instruction> <local_image1> [image2] [image3]` | `python scripts/image_edit_base64.py 'Change the background to white' ./photo.png` |
| Image understanding | `python scripts/image_understanding.py <image_URL> [question]` | `python scripts/image_understanding.py https://example.com/photo.jpg 'What is in this image?'` |

### Step 3: Return Results

Scripts will print the list of generated image URLs; `text_to_image.py` also auto-downloads images to the current directory.

---

## Model Selection Guide

| Condition | Choice | Reason |
|-----------|--------|--------|
| Need accurate in-image text rendering | `qwen-image-2.0-pro` | Qwen series has the strongest text rendering capability |
| Need 4K ultra-high definition | `wan2.7-image-pro` | Only Wanx pro text-to-image supports 4K |
| Need a set of style-consistent images | `wan2.7-image-pro` + `enable_sequential` | Wanx exclusive image series capability |
| Product/industrial design editing | `qwen-image-edit-max` | Stronger geometric reasoning and character consistency |
| Multi-image reference + composition | `wan2.7-image` | Wanx supports flexible multi-image reference editing |
| Image content analysis/Q&A | `qwen3.5-plus` | General multimodal understanding, cost-effective |
| Complex visual reasoning | `qwen-vl-max` | Stronger visual understanding capability |
| Low cost priority | `qwen-image-2.0` / `wan2.7-image` | Standard version at lower cost |
| No special requirements (default) | `qwen-image-2.0-pro` | Most balanced overall capability |

## Prompt Design Guide

> For detailed guide, see [Prompt Design Guide](references/prompt-guide.md)

Prompt structure formula: `[Subject description] + [Scene/environment] + [Lighting/mood] + [Composition/angle] + [Art style] + [Quality parameters]`

**Complete example**:
```
A 30-year-old Asian male detective standing on a rainy night Tokyo street, wearing a dark gray trench coat, holding a black umbrella, neon red and blue lights reflecting on his face, raindrops dripping along the umbrella edge, puddles on the ground reflecting brilliant city lights, Rembrandt lighting, volumetric fog, cinematic composition, 35mm anamorphic lens, film grain, moody atmosphere, high detail, photorealistic, 8K
```

**Negative prompt template** (Qwen series supports `negative_prompt`, Wanx series does not):
```
low quality, blurry, pixelated, oversaturated, deformed hands, extra fingers, distorted face, uncanny valley, text, watermark, logo, signature, cropped, out of frame, worst quality
```

---

## Reference Information

### Environment & Dependencies

| Package | Version Constraint | Purpose |
|---------|-------------------|---------|
| `dashscope` | `==1.25.16` | Text-to-image, image editing, Wanx generation |
| `openai` | `==2.23.0` | Image understanding (OpenAI-compatible interface) |

### API Key Configuration

This skill manages DashScope API Keys through `scripts/api_key.py`, which automatically validates key format (detects invalid keys like `sk-sp-`).

**Retrieval Priority**: `~/.aliyun/config.json` > Environment variable `DASHSCOPE_API_KEY` > Auto-create via Alibaba Cloud CLI

**Method 1: Alibaba Cloud CLI Config File (Recommended)**

Add a `dashscope` field to the current profile in `~/.aliyun/config.json`:
```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "AK",
      "access_key_id": "...",
      "access_key_secret": "...",
      "dashscope": {
        "api_key": "sk-xxx",
        "api_key_id": "4359606"
      }
    }
  ]
}
```

**Method 2: System Environment Variable**

```bash
export DASHSCOPE_API_KEY=sk-xxx
```

| Item | Description |
|------|-------------|
| **Key Format** | `sk-xxx` (standard DashScope API Key) |
| **Not Supported** | `sk-sp-xxx` (Coding Plan Key, does not support image generation) |
| **Get Key** | https://help.aliyun.com/zh/model-studio/get-api-key |
| **Security** | Never hardcode; use `from api_key import get_api_key`; **never output full API Key values to terminal, logs, or any files** |

### Alibaba Cloud CLI Configuration (API Key Auto-Create/Delete)

`scripts/api_key.py` creates and deletes API Keys via `aliyun modelstudio` commands. Complete the following setup before use:

```bash
# Enable AI-Mode (allow Agent to call CLI)
aliyun configure ai-mode enable

# Set User-Agent
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"

# Update plugins to latest version
aliyun plugin update

# Install ModelStudio plugin (if not already installed)
aliyun plugin install --names aliyun-cli-modelstudio --enable-pre

# Disable AI-Mode after task completion
aliyun configure ai-mode disable
```

| Command | Purpose | Called From |
|---------|---------|------------|
| `aliyun modelstudio list-workspaces` | Get Bailian Workspace ID | `api_key.py: generate_api_key()` |
| `aliyun modelstudio create-api-key` | Create DashScope API Key | `api_key.py: generate_api_key()` |
| `aliyun modelstudio list-api-keys` | List existing API Keys (used for limit recycling) | `api_key.py: generate_api_key()` |
| `aliyun modelstudio delete-api-key` | Delete cloud API Key | `api_key.py: delete_api_key()` / `generate_api_key()` |

### Regions & API Endpoints

| Region | DashScope API | OpenAI Compatible Mode |
|--------|---------------|------------------------|
| Beijing (China) | `https://dashscope.aliyuncs.com/api/v1` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Singapore | `https://dashscope-intl.aliyuncs.com/api/v1` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| Virginia (US) | `https://dashscope-us.aliyuncs.com/api/v1` | `https://dashscope-us.aliyuncs.com/compatible-mode/v1` |

**Note**: API Keys are not interchangeable between regions.

### Script Parameter Reference

#### text_to_image.py -- Text-to-Image (Qwen Series)

| Parameter | Description |
|-----------|-------------|
| `size` | Only supports `1024*1024`, `720*1280`, `1280*720`, `1440*720`, `720*1440` |
| `prompt_extend` | True to auto-optimize prompts |
| `negative_prompt` | Negative prompt to avoid generating undesired content |
| `watermark` | Whether to add watermark |

#### image_edit.py / image_edit_base64.py -- Image Editing (Qwen Series)

| Parameter | Type | Description |
|-----------|------|-------------|
| `n` | int | Number of output images, 1-6 (`qwen-image-edit` fixed at 1) |
| `size` | str | Output resolution, format `"width*height"`, range [512, 2048] |
| `negative_prompt` | str | Negative prompt |
| `prompt_extend` | bool | Smart prompt rewriting, default true |
| `watermark` | bool | Whether to add watermark, default false |
| `seed` | int | Random seed [0, 2147483647], for result reproduction |

**Editing Model Comparison**:

| Model | Strengths | Use Case |
|-------|-----------|----------|
| `qwen-image-edit-max` | Strong geometric reasoning, character consistency | Product design, precise editing |
| `qwen-image-2.0-pro` | Strong text rendering, realistic quality | General editing, text editing |
| `qwen-image-edit-plus` | Multi-image output and custom resolution | General editing |
| `qwen-image-edit` | Basic version, fixed single image output | Simple editing |

**Common Resolution Recommendations**:

| Aspect Ratio | Recommended Resolution |
|-------------|----------------------|
| 1:1 | `1024*1024`, `1536*1536` |
| 2:3 | `768*1152`, `1024*1536` |
| 3:2 | `1152*768`, `1536*1024` |
| 3:4 | `960*1280`, `1080*1440` |
| 4:3 | `1280*960`, `1440*1080` |
| 9:16 | `720*1280`, `1080*1920` |
| 16:9 | `1280*720`, `1920*1080` |
| 21:9 | `1344*576`, `2048*872` |

**Image Input Methods**:
- **HTTP/HTTPS URL**: `"https://example.com/image.png"`
- **Base64 Encoding**: `"data:image/png;base64,..."` -- See `scripts/image_edit_base64.py`
- Input: 1-3 reference images; Output: 1-6 images (controlled via `n` parameter)

#### wanx_generate.py -- Wanx Image Generation

| Parameter | Description |
|-----------|-------------|
| `size` | `1K`, `2K`, `4K` (4K only for `wan2.7-image-pro` text-to-image) |
| `enable_sequential` | Series mode, generates 1-12 style-consistent images |
| `thinking_mode` | Default true, enhances reasoning quality (increases latency) |
| `n` | Normal mode 1-4, series mode 1-12 |

| Model | Strengths |
|-------|-----------|
| `wan2.7-image-pro` | Pro version, text-to-image supports 4K HD |
| `wan2.7-image` | Standard version, faster generation |

#### image_understanding.py -- Image Understanding

Uses OpenAI-compatible mode to call DashScope. Default model `qwen3.5-plus` (general understanding), optional `qwen-vl-max` (complex reasoning).

### Pricing

| Model | Unit Price | Notes |
|-------|-----------|-------|
| qwen-image-2.0-pro | CN price | Pro version, strongest text rendering and realistic quality |
| qwen-image-edit-max | CN price | Pro version, image generation and editing fusion |
| qwen-image-2.0 | CN price | Standard version |
| qwen-image-edit-plus | CN price | Standard editing |
| wan2.7-image-pro | CN price | Wanx pro version |
| wan2.7-image | CN price | Wanx standard version |

New users get 100 free image credits (valid for 90 days) after activating Bailian. View bills: https://usercenter2.aliyun.com/finance/expense-center/overview

### Best Practices

1. Use `prompt_extend=True` to let the model auto-optimize prompts
2. Qwen series supports `negative_prompt`, Wanx series does not support this parameter
3. Choose appropriate sizes based on requirements to avoid unnecessary large image generation
4. Use the `n` parameter to generate multiple images at once for selection
5. Use URLs for online images, Base64 for small local files, `file://` protocol for large files

### Error Handling

Scripts have built-in error handling logic. For errors, refer to: https://help.aliyun.com/zh/model-studio/developer-reference/error-code

### Related Resources

- [Prompt Design Guide](references/prompt-guide.md) - Professional prompt construction methods
- [API Documentation](references/api-docs.md) - Detailed API parameter reference
- [Model List](references/models.md) - Supported models and features
- [Error Code Reference](references/error-codes.md) - Common error codes and solutions
- [Example Scripts](scripts/) - Ready-to-use scripts

| Script | Function | Description |
|--------|----------|-------------|
| `text_to_image.py` | Text-to-image | Generate images from text descriptions, supports auto-download |
| `image_edit.py` | Image editing | Supports URL, local file, and Base64 input methods |
| `image_edit_base64.py` | Base64 image editing | Demonstrates Base64 encoding method |
| `base64_tool.py` | Base64 tool | CLI tool for image-Base64 conversion |
| `wanx_generate.py` | Wanx generation | Uses wan2.7-image model for generation |
| `image_understanding.py` | Image understanding | Analyze image content, answer questions |
