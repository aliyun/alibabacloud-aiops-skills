---
name: alibabacloud-oss-media-process
description: |
  Process images, audio, and video files stored in Alibaba Cloud OSS.
  Supports 14+ image operations (resize, crop, rotate, watermark, blur, format conversion, etc.),
  image-intelligent features via IMM (blind watermark, face/body/car detection, QR recognition, labeling, scoring),
  and audio/video processing (transcoding, screenshot, animation, sprite sheet, concatenation, metadata extraction, HLS streaming).
  Results can be returned as signed URL, downloaded locally, or saved as new OSS object.
  Also supports plain file upload/download.
  Use when the user needs to process or transform media files in OSS, such as generating thumbnails, transcoding video,
  extracting audio, adding watermarks, detecting faces, compressing images, or converting formats.
  Triggers on media processing requests in English or Chinese
  (resize, crop, thumbnail, transcode, video convert, audio convert, watermark,
  face detection, 缩略图, 裁剪, 压缩, 转码, 视频转换, 音频处理, 水印, 盲水印, 人脸检测, 截帧, 拼接).
license: Apache-2.0
metadata:
  domain: aiops
  owner: oss-team
  contact: oss-agent@alibaba-inc.com
  language: Chinese (default). Use English only when user explicitly writes in English.
compatibility: >
  Aliyun CLI >=3.3.3, Python >=3.8, oss2 ==2.19.1 (pip install oss2==2.19.1),
  alibabacloud-credentials ==1.0.8.
  Optional for IMM operations: alibabacloud_imm20200930 ==4.8.2,
  alibabacloud_tea_openapi ==0.4.4.
  Install all: pip install -r scripts/requirements.txt.
  Credentials managed via Aliyun CLI (`aliyun configure`);
  Python scripts auto-discover credentials through the alibabacloud-credentials default chain.
allowed-tools: Bash Read
---

# Alibaba Cloud OSS Media Processing

Process images, audio, and video files stored in Alibaba Cloud OSS using native OSS media processing capabilities. Synchronous processing returns immediate results via `x-oss-process`; asynchronous processing handles long-running jobs via `x-oss-async-process` with polling.

**Default language**: 默认中文回复。Only use English when the user explicitly writes in English.

## Quick Start

### Working directory

All script commands run from the skill package root. **Use full absolute paths** to invoke scripts:
```bash
python /path/to/skill/scripts/process.py ...
```
Do not `cd` into the directory and use relative paths. If a script fails with "No such file or directory", use Glob to find `**/alibabacloud-oss-media-process/scripts/process.py` and use its full path.

**Setup workspace output directory** (run once per session):
```bash
WORKSPACE_OUTPUT=$(pwd)/outputs && mkdir -p "$WORKSPACE_OUTPUT"
```
All `--output-path` arguments MUST use `$WORKSPACE_OUTPUT/<filename>` — files saved inside the skill directory will NOT be renderable.

### Credentials (Aliyun CLI)

This skill uses Aliyun CLI for credential management. Python scripts auto-discover credentials via the `alibabacloud-credentials` default chain (supporting `~/.aliyun/config.json`, environment variables, ECS instance roles, etc.).

**Security rules**:
- Never read, echo, print, `cat`, or dump `~/.aliyun/config.json`, credential files, or any raw command output that contains `access_key_id`, `access_key_secret`, `sts_token`, `AccessKeyId`, `AccessKeySecret`, or `SecurityToken` values.
- Never ask the user to input AK/SK directly in the conversation or command line
- Guide users to use `aliyun configure` to set up credentials securely
- Never write `AccessKeyId`, `AccessKeySecret`, or `SecurityToken` into any temporary Python/Shell script, here-doc, env export, or intermediate file. All credentials must be discovered through Aliyun CLI or the SDK default credential chain.
- For credential diagnostics, use `aliyun configure list`, `python scripts/load_env.py`, or other non-secret checks. If you must inspect configuration structure, only inspect non-sensitive fields and do not print secret or token values to the transcript.
- Treat full presigned URLs as sensitive whenever they contain signing parameters such as `OSSAccessKeyId`, `accessKeyId`, `x-oss-credential`, `Signature`, `x-oss-signature`, `security-token`, `SecurityToken`, or `sts_token`. Do not print these full URLs into the conversation transcript, command echo, markdown summary, or ordinary log files.
- When a signed URL is needed for user consumption, distinguish between delivery and display: it is acceptable to generate a usable signed URL, but unless the runtime provides a secure private-output channel that does not enter the transcript or logs, only display a redacted URL or an OSS path in normal user-facing text.

### Prerequisites

| Step | Action | Command |
|------|--------|---------|
| 1 | Install Aliyun CLI (>=3.3.3) | `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` |
| 2 | Configure credentials | `aliyun configure` |
| 3 | Run blocking preflight check 1 | `python scripts/load_env.py` |
| 4 | Run blocking preflight check 2 | `aliyun configure list` |
| 5 | Enable plugins | `aliyun configure set --auto-plugin-install true && aliyun plugin update` |
| 6 | Install Python deps | `pip install -r scripts/requirements.txt` |
| 7 | Set bucket/region (choose one) | `export ALIBABA_CLOUD_OSS_BUCKET=<b> ALIBABA_CLOUD_OSS_REGION=<r>` (add to `~/.bashrc`/`~/.zshrc` for persistence), or pass `--bucket <b> --region <r>` on every command |

**Blocking preflight policy**:
- `python scripts/load_env.py` may report missing SDKs, missing credentials, missing bucket/region, or RAM permission problems.
- `aliyun configure list` must show a usable configured CLI profile.
- Treat preflight results as stale after any environment or runtime change. If you install Python packages, run `aliyun configure`, change env vars, edit shell profiles, switch users, or otherwise modify credential/runtime state, you must rerun both `python scripts/load_env.py` and `aliyun configure list` before the next `python scripts/process.py ...` command.
- If either command fails these checks, stop immediately.
- Do not run `python scripts/process.py ...`.
- Do not retry media processing.
- Do not simulate a successful result.
- Return only configuration guidance until both checks pass.

### AI-Mode

Enable at session start:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-oss-media-process"
```

**Disable on every exit**: success, failure, error, cancellation, or session end:
```bash
aliyun configure ai-mode disable
```

### Preflight then Execute

When the user requests a media operation (resize, detect faces, watermark, etc.), apply the blocking preflight policy above before running any `python scripts/process.py ...` command. `process.py` also performs a runtime dependency preflight and exits with `pip install -r scripts/requirements.txt` guidance if required SDKs are missing. If you change the environment after a failed attempt (for example by installing dependencies, editing env vars, or re-running `aliyun configure`), do not assume the earlier preflight still holds — rerun the full blocking preflight first.

### First-time setup

Direct users to run `aliyun configure` to set up credentials, then verify with:
```bash
aliyun configure list
```
Python scripts use the `alibabacloud-credentials` SDK to auto-discover credentials from the Aliyun CLI config. Bucket and region are read from the `ALIBABA_CLOUD_OSS_BUCKET` / `ALIBABA_CLOUD_OSS_REGION` environment variables, or from `--bucket` / `--region` CLI flags. `load_env.py` scans shell config files (`~/.bashrc`, `~/.zshrc`) for these exports and loads them into `os.environ`.

## Recommended Workflow

Follow this numbered workflow for every request:

1. **Prepare**
   Confirm the bucket and region are available through `--bucket` / `--region` or the `ALIBABA_CLOUD_OSS_BUCKET` / `ALIBABA_CLOUD_OSS_REGION` environment variables. Apply the blocking preflight policy before any media command. Create `$WORKSPACE_OUTPUT` once per session for all local downloads.

2. **Choose the source**
   Use `--source` for an existing OSS object key. Use `--uri` for a local file path or HTTP(S) URL that should be uploaded temporarily before processing.

3. **Decide the execution path**
   Use `python scripts/process.py` for all media processing and file operations. If the request involves video, audio, HLS, or image-intelligent features, run `python scripts/imm_admin.py auto-setup --bucket <b> --region <r>` first to ensure IMM bucket binding exists.

4. **Execute**
   Build exactly one valid operation chain. Prefer `--output-mode download --output-path $WORKSPACE_OUTPUT/<name>` for sync image outputs, `--output-mode save --target-key <key>` for async media outputs, and `--output-mode url` when the result is meant to be consumed remotely.

5. **Verify**
   Read the returned JSON. Check `success`, `request_id`, `task_id` (async only), `target_key`, local `path`, and any `validation_warnings`. If the command downloaded a local file, present the absolute path to the user.
   Only report a local output path after the file was actually written to `$WORKSPACE_OUTPUT` and the returned absolute path matches the real downloaded file. Do not claim that a file was saved to `outputs/...` or any other local path unless it truly exists there.
   If you need to record `task_id`, `request_id`, `target_key`, `generated_keys`, or similar fields in logs, notes, or output files, extract them directly from the `process.py` JSON response. Do not transcribe, rewrite, or manually retype these values.
   If the user or eval explicitly requires verification of any machine-verifiable output property (for example codec, bitrate, sample rate, channel count, duration, resolution, frame rate, width, height, or format), prefer running one additional read-only verification step against a persisted OSS output object before finalizing the summary. Use `audio/info` or `video/info` for audio/video outputs, and use a separate `--operations info` command for image outputs. Do not download the file locally just for this purpose.
   For image width, height, format, and file-size verification, treat OSS-side `--operations info` on the saved target object as the default and preferred verification path. `info` is a standalone read-only image metadata operation, not a follow-up segment that should be appended to a basic image processing chain. Do not switch to local image-library inspection when `info` can answer the question.
   If a read-only verification step was performed and its result differs from the requested value, report the actual verified output value. Do not substitute the request value, and do not claim the request was fully satisfied when the verification result shows otherwise.
   If no read-only verification step was performed, do not describe machine-verifiable output properties as independently confirmed.
   Do not assume local verification tools such as `PIL`/`Pillow`, `ffprobe`, or similar utilities are installed. If a tool is unavailable, do not claim that you performed the corresponding local pixel-level or media-property verification.
   For image-property verification in particular, do not introduce ad hoc local-library checks such as `PIL`/`Pillow` unless the workflow explicitly requires a local-file-only inspection and OSS-side `info` cannot provide the property. In normal skill usage and evals, prefer OSS-side verification and avoid emitting local `PIL`/`Pillow` commands entirely.
   If the workflow returns only a signed URL and does not persist a reusable OSS target object, do not claim that you performed a follow-up `info` check on the final output object unless such an object actually exists. In that case, either save the result to OSS first and verify the saved object, or state that only the immediate processing result was available and no persisted-object verification was performed.
   Before sending the final user-facing summary, follow the `Language rule` in `Result Presentation`.

6. **Recover**
   If the command fails, use the `Error Recovery` table below. Retry only after correcting the concrete cause, such as missing IMM binding, bad parameters, or insufficient RAM permissions.

---

## Quick Decision Guide

### All processing goes through `process.py`

Image, video, and audio operations MUST be executed via `python scripts/process.py --operations "..."`. The agent must not write its own SDK or CLI calls to bypass `process.py` or `imm_admin.py` for video/audio/image processing. Underlying SDK or API requests triggered internally by these scripts (including IMM requests such as `CreateMediaConvertTask`) are expected implementation behavior and do not count as direct agent-side SDK usage. The only intentional script-level IMM entry points are `imm_admin.py` for project setup and `blindwatermark-extract` for async watermark extraction.

Never create your own Python scripts or wrappers to bypass `process.py`. When `process.py` doesn't support a feature, check SKILL.md and `references/` documentation, use `--dry-run` to preview, and report to the user if it truly cannot be done.

### IMM setup (before IMM-dependent ops)

Before running video, audio, HLS, or image-intelligent operations, first run `imm_admin.py auto-setup` to ensure the bucket is bound to an IMM project. Pass `--imm-project <project_name>` only for `blindwatermark-extract`, or if you intentionally want to override the optional `ALIBABA_CLOUD_IMM_PROJECT` fallback used by that operation.

### Source selection

- OSS object → `--source object-key`
- Local file or URL → `--uri /path/to/file` (auto-uploads, processes, cleans up)

### Sync vs Async (auto-detected)

- Sync (`x-oss-process`): image ops, `video/snapshot`, `video/info`, `audio/info`, `hls/m3u8`, AI detection
- Async (`x-oss-async-process`): `video/convert`, `video/animation`, `video/snapshots`, `video/sprite`, `video/concat`, `audio/convert`, `audio/concat`, `blindwatermark-extract`

The script auto-detects async-only operations and handles routing/polling automatically — no `--async` or `--wait` flags needed.

### Output rules

| Operation type | Output mode | Command pattern |
|----------------|-------------|-----------------|
| Sync (image) | `download` | `--output-mode download --output-path $WORKSPACE_OUTPUT/<file>` |
| Async (video/audio) | `save` then `download` | 1. `--output-mode save --target-key output/<file>` → 2. `--operations download --output-path $WORKSPACE_OUTPUT/<file>` |
| `video/snapshots` | `save` with auto-download | `--output-mode save --target-key output/frames/frame --output-path $WORKSPACE_OUTPUT/` — script auto-polls and downloads all frames |
| `hls/m3u8` | `url` | `--output-mode url` — returns signed URL for browser/player (not a downloadable file) |

All `--output-path` MUST use `$WORKSPACE_OUTPUT/<filename>` — files saved inside the skill directory will NOT be renderable.

**No-local-download rule**: if the user explicitly says not to download locally, only to save in OSS, or only to return a link/URL, do not pass `--output-path` and do not perform any follow-up download for verification. Use `--output-mode url` for sync results meant to be consumed remotely, and use `--output-mode save --target-key ...` for async media results that should remain in OSS. Never download to `$WORKSPACE_OUTPUT`, `/tmp`, or any local path just to verify success; rely on the `process.py` JSON response instead.

**Ambiguous save wording rule**: if the user says "保存", "保存下来", "存起来", or similar wording but does not explicitly say "下载到本地", "本地查看", "给我本地文件", or another clear local-destination phrase, default to saving the result back to OSS with `--output-mode save --target-key ...`. Only use `--output-mode download --output-path ...` when the user explicitly asks for a local file. If the user only wants to inspect the result and does not require a persisted local copy, prefer `--output-mode url` for sync outputs and `--output-mode save` plus the OSS path for async outputs.

**Signed-URL delivery rule**: the purpose of `--output-mode url` is to make a remote result accessible, not to force the full signed query string into the transcript. In ordinary text responses, prefer an OSS path or a redacted URL. Only provide a full presigned URL when the runtime offers a secure private-output channel that keeps the raw URL out of transcript/log surfaces. If no such channel exists, explain the limitation briefly and avoid printing the full signed query parameters. A redacted URL should keep the path and any non-sensitive query parameters, while replacing sensitive signing values with `***`, for example: `https://bucket.oss-cn-hangzhou.aliyuncs.com/output/result.webp?OSSAccessKeyId=***&x-oss-credential=***&Signature=***&security-token=***&Expires=1700000000`.

**Unique suffix rule**: when you need a unique OSS target key suffix for evals, retries, or parallel runs, prefer Python-generated UUIDs or a timestamp-plus-random suffix. Do not rely on `uuidgen` being available. If you must generate a suffix from shell commands, first verify the command exists; otherwise fall back to a timestamp plus random digits. Safe shell example: `SUFFIX=$(python3 -c "import uuid; print(uuid.uuid4().hex[:8])" 2>/dev/null || date +%Y%m%d_%H%M%S_$RANDOM)`.

### Chaining rules

See the dedicated `Chaining Rules` section below for full chaining guidelines.

---

## Core Parameter Rules

1. **Only pass parameters the user specifies** — do not invent defaults. OSS uses official defaults for unspecified parameters (e.g., keep original width/height, original bitrate, original framerate).
2. **Recipes are examples, not defaults** — parameter values in recipe tables (e.g., `w=800`, `vb=2000000`) are for specific scenarios and should NOT be used as defaults.
3. **video/convert — remux vs re-encode**: omitting `vcodec` means OSS only does **remux** (stream copy without re-encoding). Parameters like `videoslim`, `vb`, `crf`, `s`, `fps` are silently ignored in remux mode. **Always specify `vcodec` (default `h264`) when the user says "transcode", "compress", or "slim".** Only omit `vcodec` for pure remux (e.g., AVI→MP4 container switch) or audio extraction.
4. **video/concat — when input params differ**: if input videos have different resolution, framerate, or codec, **you must ask the user** which video to align to (option A: first video, B: second video, C: custom params). Never auto-decide.
5. **video/concat — validation scope**: `process.py` always performs input compatibility checks before submitting the async task. Additional local `ffprobe` output validation only runs when the command also downloads the result via `--output-path`. If you use `--output-mode save` without a local download path, there is no post-download media validation step.
6. **Snapshots vs snapshot**: use `video/snapshots` (async) for multi-frame extraction. Never use multiple `video/snapshot` calls as a workaround. `video/snapshots` target-key must NOT have a file extension.
7. For full parameter specifications, see the corresponding reference files in `references/`.

---

## Result Presentation

After every successful `process.py` execution, present results in this format:

**Language rule**: unless the user explicitly requested English, the final user-facing result summary in this section must be written in Chinese.
Use a result template that matches the response language. For Chinese responses, use a Chinese lead-in such as `处理结果如下：` and Chinese field labels such as `状态` / `请求 ID` / `任务 ID` / `源文件` / `输出` / `参数` / `文件大小` / `OSS 路径`. For English responses, use `Result summary:` and the corresponding English labels `Status` / `RequestID` / `Task ID` / `Source` / `Output` / `Params` / `File Size` / `OSS Path`.

**1. File path**: output the local absolute path in a code block (e.g., `/path/to/outputs/snapshot.jpg`). Never use `open` or Read tool to display files.
Only include this section when the file was actually downloaded or written locally. Do not present an `outputs/...` path that was only planned, inferred, or mentioned in a transcript.

**2. Result table**:

| Item | Detail |
|------|--------|
| Status | ✅ Completed |
| RequestID | `<request_id>` (or `N/A`) |
| Task ID | `<task_id>` (async only) |
| Source | `source/input.mp4` |
| Output | `output/result.mp4` |
| Params | Dynamic — from your command (e.g., MP4/H.264/2Mbps, or 800x600/JPEG) |
| File Size | From download output |
| OSS Path | `oss://<bucket>/<target-key>` (save mode only) |

**Field sourcing rules**: `Status` and `Params` must be quoted directly from the `process.py` JSON response. `Status` must come from the returned `success` field, and `Params` must come from the returned `operations` field. Never rewrite, estimate, normalize, or summarize numeric/media values by hand, including confidence scores, bitrate, resolution, dimensions, frame rate, or codec details.

If you need a textual summary, include the original command or process string in a fenced code block and describe it conservatively. Do not invent parameter values or restate them in free-form prose when they are not explicitly present in the `process.py` response.

**Final summary constraints**:
- Do not insert fixed English filler such as `Task Completed Successfully`.
- Numeric values such as sample rate, bitrate, resolution, duration, frame rate, and file count must be copied directly from `process.py` JSON fields or an explicitly performed read-only verification result.
- If a value was not obtained directly from machine output, omit it instead of rewriting, estimating, rounding, or normalizing it by hand.
- If an explicitly performed read-only verification result differs from the requested value, report the actual verified output value and describe the request as only partially satisfied when necessary. Do not replace the verified value with the requested one.
- If no read-only verification result was obtained, do not claim that machine-verifiable output properties were independently confirmed.

If the user forbids local downloads, omit the `File path` row/section entirely and do not create temporary local files for validation. In that case, present only the JSON-backed metadata returned by `process.py`, such as `success`, `request_id`, `task_id`, `target_key`, `generated_keys`, or `url`.

If `process.py` returns a signed URL, treat the full query string as sensitive output. In normal visible summaries, prefer the OSS path, target key, or a redacted URL. Do not expand raw signing parameters into the final summary unless the runtime has a secure private-output channel for secret delivery.

If independent verification was requested but the workflow returned only a signed URL and did not create a persisted OSS target object, do not claim that a follow-up `info` check was performed on a final output object. Either save the result first and verify the saved object, or state clearly that no persisted-object verification was available.

For image outputs and visual effects such as watermarks, overlays, blur regions, or face redaction, distinguish between metadata verification and visual verification. If the output was not downloaded or rendered locally, do not claim that a visual element was independently confirmed by inspection; state that only the service-reported processing result was verified unless a local render or explicit inspection step was actually performed.

**Rules**:
- Do not run `video/info`, `audio/info`, or image `--operations info` after processing for ordinary result reporting. However, if the user explicitly asks you to verify concrete machine-verifiable output properties such as codec, bitrate, sample rate, channel count, duration, resolution, frame rate, width, height, or format, or if the eval/acceptance criteria explicitly require an independent property check, prefer running one additional read-only verification step against a persisted OSS output object and report that verification separately from the main `process.py` result. Use `audio/info` or `video/info` for audio/video outputs, and use a separate `--operations info` command for image outputs.
- Do not assume local verification libraries or binaries such as `PIL`/`Pillow`, `ffprobe`, or similar tools are preinstalled. Use them only when they are actually available and the workflow genuinely requires a local-file check; otherwise rely on `process.py` JSON output and permitted read-only OSS-side checks.
- For image width/height/format verification, prefer OSS-side `--operations info` on the saved target object even if a local file is present. Do not use `PIL`/`Pillow` as the default verification method for evals or routine skill runs.
- Requests to verify image width, height, format, or similar machine-verifiable properties do not by themselves authorize a local download. If the user did not explicitly request a local file, and a saved OSS target object can be verified with `info`, do not switch to `--output-mode download` solely for verification.
- Do not use `head_object` as a substitute for media-property verification.
- Avoid `sleep` + retry loops; the script handles async polling internally.
- All media processing goes through `process.py`; if unsupported, check `references/` and report — do not write custom scripts.

---

## Chaining Rules

### Image Operations
- Basic operations can be freely chained with each other
- `blindwatermark-embed` can follow basic ops but must be the last operation
- `blindwatermark-extract` must be used alone — no chaining
- AI detection (`faces`, `bodies`, `cars`, `codes`, `labels`, `score`) must be used alone

### Video/Audio Operations
- Video/audio operations cannot be chained with image operations
- Only one video/audio operation per request (no chaining)
- For complex workflows, use multiple separate requests

---

## Credential & Environment Setup

Credentials are managed by Aliyun CLI (`~/.aliyun/config.json`). Python scripts auto-discover them via the `alibabacloud-credentials` SDK default chain. See **Prerequisites** above for setup steps.

**Diagnostic check**:
```bash
python scripts/load_env.py
```
This scans for legacy env vars and verifies RAM permissions. Use this if operations fail with access errors.

**Runtime dependency preflight**: `process.py` checks required Python packages before execution. Basic OSS/file operations require `oss2` and `alibabacloud-credentials`; video/audio/HLS/IMM operations also require the IMM SDK packages from `scripts/requirements.txt`. If any dependency is missing, the command fails fast with an install hint instead of starting a partial execution.

**IMM project** — usually discovered by `imm_admin.py auto-setup`. `process.py` only consumes `--imm-project` / `ALIBABA_CLOUD_IMM_PROJECT` for `blindwatermark-extract`.

---

## IMM Auto-Setup

Video/audio processing and image-intelligent features require an IMM project bound to the bucket. Follow this workflow for IMM-dependent operations:

**Step 1 — Detect IMM project** (before any processing command):
```bash
python scripts/imm_admin.py auto-setup --bucket <bucket> --region <region>
```
This ensures the bucket is bound to a usable IMM project and prints the resolved project name.

**Step 2 — Execute the media operation**:
```bash
python scripts/process.py --source video.mp4 \
  --operations "video/convert:f=mp4,vcodec=h264" \
  --output-mode save --target-key output/video.mp4
```

For `blindwatermark-extract`, append `--imm-project <project_name>` if you do not want to rely on the optional `ALIBABA_CLOUD_IMM_PROJECT` fallback.

**Step 3 — Present results** per Execution & Output Workflow above.

Operations that require IMM bucket setup: all video/audio/HLS ops, image-intelligent ops (faces, bodies, cars, codes, labels, score, blindwatermark-embed/extract), smart crop (`crop:g=auto`/`crop:g=face`), face blur (`blur:g=face`/`blur:g=faces`). Only `blindwatermark-extract` requires the project name as a direct `process.py` input.

---

## Available Operations

### Image Processing (Sync)

| Operation | Description | Reference |
|-----------|-------------|-----------|
| `resize`, `crop`, `indexcrop`, `rotate`, `flip` | Basic transformations | `references/image-basic-operations.md` |
| `quality`, `format`, `interlace` | Quality & format | `references/image-basic-operations.md` |
| `watermark`, `blur`, `sharpen`, `bright`, `contrast` | Effects | `references/image-basic-operations.md` |
| `auto-orient`, `circle`, `rounded-corners` | Utilities | `references/image-basic-operations.md` |
| `info`, `average-hue` | Metadata (JSON) | `references/image-basic-operations.md` |

### Image-Intelligent (IMM)

| Operation | Mode | Description | Reference |
|-----------|------|-------------|-----------|
| `blindwatermark-embed` | Sync | Embed invisible watermark. Must be last in chain. | `references/image-imm-operations.md` |
| `blindwatermark-extract` | Async | Extract watermark. Use alone. | `references/image-imm-operations.md` |
| `faces`, `bodies`, `cars` | Sync | Detect faces/bodies/cars (JSON). | `references/image-imm-operations.md` |
| `codes`, `labels`, `score` | Sync | QR/barcode recognition, labels, quality score (JSON). | `references/image-imm-operations.md` |

### Video Processing

| Operation | Mode | Description | Reference |
|-----------|------|-------------|-----------|
| `video/convert` | Async | Transcode video. **Must specify `vcodec` for re-encode.** | `references/video-operations.md` |
| `video/snapshot` | Sync | Extract single frame. `t` (time ms) required. | `references/video-operations.md` |
| `video/info` | Sync | Video metadata (JSON). | `references/video-operations.md` |
| `video/animation` | Async | Video to GIF/WebP. | `references/video-operations.md` |
| `video/snapshots` | Async | Multi-frame extraction. target-key must NOT have extension. | `references/video-operations.md` |
| `video/sprite` | Async | Sprite sheet. Must specify `num` or `inter`. | `references/video-operations.md` |
| `video/concat` | Async | Concatenate videos (max 11). Must verify input params match. | `references/video-operations.md` |

### Audio Processing

| Operation | Mode | Description | Reference |
|-----------|------|-------------|-----------|
| `audio/convert` | Async | Transcode audio. | `references/audio-operations.md` |
| `audio/concat` | Async | Concatenate audio files. | `references/audio-operations.md` |
| `audio/info` | Sync | Audio metadata (JSON). | `references/audio-operations.md` |

### HLS Streaming

| Operation | Mode | Description | Reference |
|-----------|------|-------------|-----------|
| `hls/m3u8` | Sync | HLS playlist (returns a playlist, not a file — use `--output-mode url`). | `references/video-operations.md` |

### File Operations

| Operation | Mode | Description |
|-----------|------|-------------|
| `upload` | Sync | Upload local file/URL to OSS. Use with `--uri` and `--target-key`. |
| `download` | Sync | Download OSS object. Use with `--source` and `--output-path`. |

---

## Processing Modes

- **Synchronous** (`x-oss-process`): image basic processing, `video/snapshot`, `video/info`, `audio/info`, `hls/m3u8`, AI detection — results returned immediately
- **Asynchronous** (`x-oss-async-process`): video/audio transcoding, animation, sprite, snapshots, concat, blindwatermark-extract — auto-detected, auto-polled until completion

---

## Usage

```bash
python scripts/process.py \
  [--bucket BUCKET_NAME] \
  [--region REGION_ID] \
  (--source OSS_OBJECT_KEY | --uri URI) \
  --operations OPERATION [OPERATION ...] \
  [--output-mode url|download|save] \
  [--expires SECONDS] \
  [--output-path LOCAL_PATH] \
  [--target-key OSS_TARGET_KEY] \
  [--endpoint CUSTOM_ENDPOINT] \
  [--imm-project IMM_PROJECT_NAME] \
  [--dry-run]
```

`--imm-project` is only consumed by `blindwatermark-extract`; other operations rely on IMM bucket binding, not this flag.

### `--uri`

Process a file from a local file path or URL (http/https) without pre-uploading. The script auto-uploads to a temp key, processes, and cleans up. `--uri` and `--source` are mutually exclusive.

### `--dry-run`

Prints the generated process string and operation details as JSON to stdout, then exits without connecting to OSS.

### Operation String Format

Each operation: `name:key=value,key=value`. No-param operations use just the name (e.g., `info`, `video/info`). Video/audio operations use slash notation: `video/convert`, `audio/convert`.

## End-to-End Example

**User request**:
```text
Resize `images/photo.jpg` in OSS to width 600px, add a bottom-right text watermark `Copyright 2026`, and download the result locally. The bucket is `my-media-bucket` in region `cn-shanghai`.
```

**Command**:
```bash
python scripts/process.py --bucket my-media-bucket --region cn-shanghai \
  --source images/photo.jpg \
  --operations "resize:w=600" "watermark:text=Copyright 2026,g=se,opacity=60,size=30" \
  --output-mode download \
  --output-path "$WORKSPACE_OUTPUT/photo-watermarked.jpg"
```

**Expected result shape**:
```json
{
  "success": true,
  "mode": "download",
  "path": "/absolute/path/to/outputs/photo-watermarked.jpg",
  "size": 12345,
  "request_id": "xxxxxx"
}
```

Interpretation:
- `success: true` means OSS processing completed successfully.
- `path` is the local file path you should present to the user.
- `request_id` is the server-side request trace ID for troubleshooting.

### Additional Examples

```bash
# HLS streaming (with IMM auto-setup)
python scripts/imm_admin.py auto-setup --bucket my-bucket --region cn-hangzhou
# → Capture project name from output
python scripts/process.py --bucket my-bucket --region cn-hangzhou \
  --source videos/input.mp4 \
  --operations "hls/m3u8:ss=15000,t=1800000,vcodec=h264,fps=25,s=1280x720,vb=2000000,acodec=aac,ab=128000" \
  --output-mode url

# Upload a local file to OSS
python scripts/process.py --bucket my-bucket --region cn-hangzhou \
  --uri /path/to/report.pdf --operations upload --target-key documents/report.pdf

# Download a file from OSS
python scripts/process.py --bucket my-bucket --region cn-hangzhou \
  --source documents/report.pdf --operations download --output-path $WORKSPACE_OUTPUT/report.pdf
```

## Edge Cases

- `watermark` values that contain commas should be quoted. For example: `preprocess="resize:w=200,text=demo,image/logo.png"`.
- `video/snapshots` target keys must not include a file extension. Use `output/frames/frame`, not `output/frames/frame.jpg`.
- `video/concat` always performs input compatibility checks before task submission. Additional local `ffprobe` output validation only runs when the result is also downloaded via `--output-path`.
- Async media polling defaults to 600 seconds. Override with `--timeout-seconds <n>` or `ALIBABA_CLOUD_ASYNC_TIMEOUT_SECONDS`.
- `blindwatermark-extract` must run alone. `blindwatermark-embed` can follow basic image operations, but it must be the last operation in the chain.

---

## Error Recovery

| Error | Cause | Recovery |
|-------|-------|----------|
| Repeated `AccessDenied` or `InvalidArgument` twice in a row | Configuration or authorization is still unresolved, and blind retries risk fabricated diagnosis | Stop immediately. Do not simulate output, do not fabricate logs, and do not keep retrying `process.py`. Run `aliyun configure list` to verify the active CLI profile, then check RAM permissions with `python scripts/check_permissions.py` or the relevant RAM policy setup. If you changed dependencies, env vars, or CLI configuration while recovering, rerun `python scripts/load_env.py` and `aliyun configure list` before any next `process.py` attempt. |
| `task_id: null` | IMM project not bound to bucket, or `blindwatermark-extract` missing `--imm-project` / `ALIBABA_CLOUD_IMM_PROJECT` | Run `python scripts/imm_admin.py auto-setup --bucket <b> --region <r>` first; for `blindwatermark-extract`, also pass `--imm-project <project>` if needed |
| `NoSuchKey` | Source file does not exist in OSS | Check `--source` path, or upload first with `--uri` and `upload` operation |
| `AccessDenied` / `403` | RAM policy missing required permissions | Run `python scripts/check_permissions.py` for diagnosis |
| `InvalidArgument` | Wrong parameter format or unsupported combination | Check parameter spelling; verify against `references/` docs |
| Async timeout / polling exceeds limit | Job too large or queue backlog | Note the `task_id`, tell user to retry later; do NOT use `sleep` loops |

---

## Quick References

- **Parameter details**: `references/image-basic-operations.md`, `references/image-imm-operations.md`, `references/video-operations.md`, `references/audio-operations.md`
- **RAM Permissions**: `references/ram-policies.md`
- **Format Support & Limitations**: `references/limitations.md`
- **IMM Administration**: `references/imm-admin.md`
