---
name: alibabacloud-yike-cli
description: "Use when the user needs Yike CLI for local image/video upload or uploading media to the cloud (including Agent chat attachments exposed as local paths), standalone image/video generation, media info or quality inspection, async media/job wait and recovery, account/auth/config/update checks, listing or installing bundled skill packages, or help showing and choosing Yike CLI model, resolution, ratio, size, duration, and task type parameters for video generation."
---

# Using Yike CLI

This skill is the Agent operation protocol for the `yike` command. Load the appropriate `references/` sub-module based on the user's request, then execute the command. When commands conflict with documentation, treat the current CLI help as authoritative and report the inconsistency to the user; only modify documentation when the user explicitly requests skill maintenance.

## Mandatory Loading Rules

Load this skill whenever the user raises any of the following needs:

- Standalone image or video generation.
- Upload local images/videos or upload a video/image to the cloud, or use image/video attachments provided as local paths in Agent chat.
- Generate images/videos based on local attachments, reference images, reference videos, URLs, or mediaIds.
- Query a mediaId's URL, status, duration, resolution, or file size.
- Perform quality gating on generation results.
- Continue, recover, or troubleshoot a known `jobId` / `resumeCommand`.
- Check Yike CLI login, account info, configuration, version, or list/install available bundled skill packages.
- Query Yike CLI model, resolution, ratio, size, duration, or show all task type parameters for video generation.
- Query which reference media types (image/video) and how many references a video model accepts.

## Orchestration Logic

This skill orchestrates the **Alibaba Cloud Yike CLI** — a single-binary tool that manages media upload, image/video generation, job lifecycle, and account authentication against the Yike cloud API.

### Module Routing Decision Criteria

When a user request arrives, the agent selects the reference module(s) to load based on the primary intent:

1. **Authentication / Setup** → load `references/account-and-setup.md`
   - Trigger: login, logout, whoami, config, update, skill install
2. **Upload** → load `references/upload.md`
   - Trigger: local file path, Agent chat attachment, or need to convert a local asset to a mediaId
3. **Generation** → load `references/generate.md` (core), plus optionally:
   - `references/generate-image.md` — natural-language image generation
   - `references/generate-video.md` — natural-language video generation
   - Trigger: user wants to create an image or video from a prompt/reference
4. **Model Capabilities** → load `references/video-model-capabilities.md`
   - Trigger: need to determine which reference types (image/video) or how many references a model accepts
5. **Media Info / Jobs** → load `references/media-and-jobs.md`
   - Trigger: query media status, run quality gate, poll/recover a job

### Call Order

```
[Auth Check] → [Upload if local files] → [Generate with --dry-run] → [User confirms] → [Generate with --yes] → [Job Wait] → [Media Info / Doctor]
```

### Module Interactions

- **Upload** produces a `mediaId` (status `Normal`) that feeds into **Generate** as `--reference-image` or `--reference-video`.
- **Generate** produces a `jobId` and `resumeCommand` consumed by **Media & Jobs** for polling.
- **Media & Jobs** returns the final `mediaId` of the output, which can be inspected with `media info` or validated with `media doctor`.
- **Account & Setup** must succeed (authenticated state) before any Upload or Generate call.

## Module Routing Table

Load the relevant sub-module based on the request:

| Need | Command Family | Sub-module |
| --- | --- | --- |
| Local image/video upload, Agent chat attachment → mediaId, upload status wait | `yike media upload`, `yike media wait` | [`references/upload.md`](references/upload.md) |
| Standalone image/video generation, model/resolution/ratio/size/duration/taskType selection | `yike generate image`, `yike generate video` | [`references/generate.md`](references/generate.md); natural-language image gen: [`references/generate-image.md`](references/generate-image.md); natural-language video gen: [`references/generate-video.md`](references/generate-video.md) |
| Video model accepted reference media types and counts | `yike generate video` | [`references/video-model-capabilities.md`](references/video-model-capabilities.md) |
| Media info / quality gating, job polling and recovery | `yike media info/doctor`, `yike job watch/recover` | [`references/media-and-jobs.md`](references/media-and-jobs.md) |
| Authentication/context, account info, updates, skill installation | `yike auth/config`, `yike whoami/account/update`, `yike self skill install` | [`references/account-and-setup.md`](references/account-and-setup.md) |

## Shared Execution Protocol

The following rules apply to all command families.

### 1. Verify Authentication and Context

Before any operation that accesses the Yike API, run:

```bash
yike auth status --format json
yike config get --format json
```

If not logged in, complete browser authorization with `yike auth login --format json`; do not proceed with upload or generation tasks until authorization completes. Use `yike auth logout --format json` when logout is needed. Do not report internal authentication handling to the user during normal flow; only surface authentication failures and recover using `details.reauthCommand`. Full rules for login, configuration, and context overrides are in [`references/account-and-setup.md`](references/account-and-setup.md).

### 2. Always Use JSON Format for Skill Execution

All commands that require parsing, decision-making, recovery, or delivery must explicitly append `--format json`. Only use the default text or `--format text` when the user explicitly requests human-readable terminal output.

When unsure about command usage, run the corresponding `--help` first. Never extract `jobId`, `mediaId`, `mediaType`, `resumeCommand`, URLs, error codes, or status from text output.

Execute generation in the following order:

1. Assemble all generation parameters and run `--dry-run --format json` first; do not pass `--yes` at the same time, nor pass `--wait`, `--interval`, or `--timeout` (which have no effect in dry-run); do not submit the task.
2. Read `estimation.credits` from stdout JSON output; also check `estimation.balance`, `estimation.insufficient`, and `estimation.warnings`; explicitly display the estimated credits and any warnings to the user.
3. When the user has submission intent, ask whether to proceed based on this estimate, then stop and wait for explicit user confirmation. The user's initial generation request does not count as confirmation; confirmation must occur after the user has seen the current estimate. If the user only requested an estimate, display it and stop without asking about submission.
4. After explicit user confirmation, keep prompt, model, resolution, size, duration, quantity, and reference media (all parameters affecting credits or generation results) unchanged, replace `--dry-run` with `--yes`, and execute the real submission. Add `--wait` plus polling parameters when the user wants to wait for results; omit them when the user only wants a `jobId`. `--yes` only passes the user's already-given confirmation to the CLI — it cannot substitute for user confirmation.
5. If any parameter affecting credits or generation results changes, re-run `--dry-run`, display the new estimate, and wait for confirmation again. Do not submit if the user rejects, does not reply, if estimation fails, or if information is incomplete before submission.
6. Read `jobId` and `resumeCommand` from the real submission stdout JSON output; never parse structured fields from stderr.

For multiple generation tasks, display estimated credits for each item individually; only submit tasks explicitly confirmed by the user. When a single confirmation covers multiple tasks, list each task's estimated credits and the total before confirmation.

### 3. Preserve Recovery Keys for Long-Running Tasks

- When `resumeCommand` / `nextAction.command` is returned, execute the returned command as-is.
- If `media upload` fails before producing a mediaId, prefer executing `nextAction.command`; if no recovery command is returned, re-run with the same local path and context.
- `media upload` waits for media status by default — do not append `--wait`; after timeout, execute the returned `resumeCommand` (which uses `media wait` with preserved polling parameters).
- `media upload/wait` must not use `yike job watch` or `yike job recover`.
- Record `jobId` and `resumeCommand` from `generate` JSON output and preserve them in the final reply.
- Append `--wait` when terminal state polling is needed.
- After timeout, execute `resumeCommand`.
- Only report completion when the job has entered a successful terminal state and media info is readable.
- Detailed rules in [`references/media-and-jobs.md`](references/media-and-jobs.md).

### 4. Deliverables Must Include Verifiable Media Information

After generation enters a successful terminal state:

1. Extract mediaId from the job result.
2. Run `yike media info <mediaId> --format json`.
3. Run `yike media doctor <mediaId> ... --format json` when quality gating is required.
4. Deliver: task status, mediaId, accessible URL, duration, dimensions, file size, and warnings.

### 5. Inputs Must Be Explicit; Never Swallow Errors

- Pass HTTP(S) URLs and existing mediaIds directly to the corresponding generation parameter — do not re-upload.
- For Agent chat attachments or local paths, execute `media upload` per [`references/upload.md`](references/upload.md); only pass the returned mediaId to generation commands after it reaches `Normal` status.
- Confirm the true `mediaType` of each reference input from the upload result or `yike media info <mediaId> --format json` before selecting the typed parameter. Model name and taskType must not be used to guess or override media type.
- Image references always go to `--reference-image`, including when using `reference_to_video` taskType or R2V models; an image mediaId must never be passed to `--reference-video` or video generation's `--reference-media-id`. Video references always go to `--reference-video`.
- `reference_to_video` / R2V is a task classification — it does not mean the reference input must be video.
- Accepted reference media types for a model cannot be inferred from model suffix, model name, taskType, or help grouping; read [`references/video-model-capabilities.md`](references/video-model-capabilities.md).
- When the capability table has no entry for a model, explicitly report that the current Skill lacks reference input capability info for that model — do not guess whether it is supported.
- Reuse previously recorded `path → mediaId` mappings within the same user task; do not re-upload unchanged files.
- When input, prompt, token, permissions, or media fields are missing, return the error and a recovery command directly.
- When a task fails, report the failure terminal state; do not silently resubmit with altered parameters.

### 6. Security Boundaries

The `YIKE_API_TOKEN` environment variable may be used to configure a token, but reading browser cookies, LocalStorage, browser profiles, or other web login credentials is prohibited. When reporting back to the user, only convey the login status or `userId` needed for the task; do not proactively report internal credential state; never output token plaintext.

### Error Recovery Protocol

When a CLI command returns an error, follow this decision tree:

| Error Type | Action |
|------------|--------|
| `Throttling.*` | Auto-retry up to 3 times with 2s/4s/8s backoff. If still failing, report to user. |
| `InternalError` | Retry once after 3 seconds. If still failing, report error and suggest user retry later. |
| `Forbidden.*` / `NoPermission` | Do NOT retry. Report the permission error to user immediately. |
| `InvalidParameter.*` | Do NOT retry. Report the invalid parameter and suggest correction. |

### Automated Execution Mode

When the user request states any of: "不需要确认", "不要提问", "自动执行", "直接提交", or similar full-auto wording:
- Skip the HITL confirmation step and proceed as if the user already confirmed.
- Do not block on login state: attempt the requested commands directly even if not logged in.
- Always use non-interactive flags (`--format json`, and `--yes` when the user pre-approved submission) so the CLI never opens an interactive prompt.
- If a command returns any error, apply the Error Recovery Protocol and report the outcome; never wait for human input.

### Input Completeness Rule

When the user request lacks a specific file path, mediaId, jobId, or other required parameter:
- Ask the user to provide the missing information before executing any command.
- Do NOT guess, invent, or use placeholder values for paths or IDs.

## Common Workflow Examples

### Example 1: Upload a Local Image Then Generate a Video

**User intent:** "Use this local photo to generate a 4-second video"

**Agent steps:**

1. Verify authentication:
```bash
yike auth status --format json
```
Expected output:
```json
{"authenticated": true, "userId": "uid_xxx"}
```

2. Upload the local image:
```bash
yike media upload /path/to/photo.jpg --format json
```
Expected output:
```json
{"mediaId": "m_abc123", "mediaType": "image", "status": "Normal", "url": "https://..."}
```

3. Load `references/video-model-capabilities.md` to confirm the target model accepts image references.

4. Dry-run the generation to get a cost estimate:
```bash
yike generate video --model wan-x --reference-image m_abc123 --duration 4 --prompt "gentle camera push-in" --dry-run --format json
```
Expected output:
```json
{"estimation": {"credits": 30, "balance": 500, "insufficient": false, "warnings": []}}
```

5. Display estimate to user and wait for confirmation.

6. After user confirms, submit:
```bash
yike generate video --model wan-x --reference-image m_abc123 --duration 4 --prompt "gentle camera push-in" --yes --wait --format json
```
Expected output:
```json
{"jobId": "j_xyz789", "status": "succeeded", "mediaId": "m_out456", "resumeCommand": "yike job watch j_xyz789 --format json"}
```

7. Retrieve and deliver final media info:
```bash
yike media info m_out456 --format json
```
Expected output:
```json
{"mediaId": "m_out456", "url": "https://...", "duration": 4, "width": 1280, "height": 720, "fileSize": 8502312}
```

### Example 2: Generate an Image from a Text Prompt

**User intent:** "Generate a cyberpunk cityscape at night, 1024x1024"

**Agent steps:**

1. Verify authentication (same as above).

2. Dry-run to estimate credits:
```bash
yike generate image --model wanx-poster --prompt "cyberpunk cityscape at night, neon lights, rain-slicked streets" --size 1024x1024 --dry-run --format json
```
Expected output:
```json
{"estimation": {"credits": 10, "balance": 500, "insufficient": false, "warnings": []}}
```

3. Display estimate ("This will cost 10 credits") and wait for confirmation.

4. After confirmation, submit:
```bash
yike generate image --model wanx-poster --prompt "cyberpunk cityscape at night, neon lights, rain-slicked streets" --size 1024x1024 --yes --wait --format json
```
Expected output:
```json
{"jobId": "j_img001", "status": "succeeded", "mediaId": "m_img002"}
```

5. Deliver media info:
```bash
yike media info m_img002 --format json
```
Expected output:
```json
{"mediaId": "m_img002", "url": "https://...", "width": 1024, "height": 1024, "fileSize": 1245678}
```

### Example 3: Recover from a Generation Timeout

**User intent:** "My video generation timed out, the jobId is j_xyz789"

**Agent steps:**

1. Attempt recovery using job watch:
```bash
yike job watch j_xyz789 --format json
```
Expected output (still running):
```json
{"jobId": "j_xyz789", "status": "running", "resumeCommand": "yike job watch j_xyz789 --timeout 300 --format json"}
```

2. If still not terminal, execute the resumeCommand:
```bash
yike job watch j_xyz789 --timeout 300 --format json
```
Expected output (succeeded):
```json
{"jobId": "j_xyz789", "status": "succeeded", "mediaId": "m_out456"}
```

3. On success, retrieve and deliver media info:
```bash
yike media info m_out456 --format json
```
Expected output:
```json
{"mediaId": "m_out456", "url": "https://...", "duration": 4, "width": 1280, "height": 720, "fileSize": 8502312}
```

4. If the job failed (`"status": "failed"`), report the failure state, error details, and any `resumeCommand` — do not silently retry with different parameters.

## Common Mistakes Quick Reference

| Problem | Fix | Details |
| --- | --- | --- |
| Proceeding with generation while not logged in | Complete `yike auth login` or set `YIKE_API_TOKEN` env var first | [`account-and-setup.md`](references/account-and-setup.md) |
| Reporting completion after only receiving `jobId` | Wait for job terminal state and verify with `media info/doctor` | [`media-and-jobs.md`](references/media-and-jobs.md) |
| Losing `resumeCommand` | Record from JSON output and relay the recovery command | [`media-and-jobs.md`](references/media-and-jobs.md) |
| Receiving a local image/video path or Agent chat attachment | Run `media upload` first; only use the returned mediaId after status is `Normal` | [`upload.md`](references/upload.md) |
| R2V model receives an image reference | Keep the image type and pass `--reference-image`; never pass `--reference-video` or video generation's `--reference-media-id` | [`generate-video.md`](references/generate-video.md) |
| Inferring "only accepts video" from `r2v` / `reference_to_video` | Stop inferring and read the model reference input capability table | [`video-model-capabilities.md`](references/video-model-capabilities.md) |
| Upload wait timeout | Execute the returned `media wait` resumeCommand; do not use `job watch/recover` | [`upload.md`](references/upload.md) |
| Treating CLI help taskType grouping as model reference input capabilities | Help is only for model code listings; read the capability table for input types and counts | [`video-model-capabilities.md`](references/video-model-capabilities.md) |
| Silently retrying with smaller parameters after failure | Surface the error first, preserve logs and recovery keys | Per-module "Common Mistakes" sections |
