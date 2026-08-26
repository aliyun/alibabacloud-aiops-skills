# Generate Command Family

Read this document when `yike generate image`, `yike generate video`, or generation parameter selection is involved. See root `SKILL.md` for shared rules.

When the user expresses a natural-language request such as "generate an image / make a picture / create a video / animate this image / generate based on a reference video", first read the corresponding specialized reference to translate natural language into prompt, taskType, aspect ratio, duration, and reference asset parameters:

- For image generation intent, see [`generate-image.md`](generate-image.md).
- For video generation intent, see [`generate-video.md`](generate-video.md).
- For local image/video paths and Agent conversation attachments, see [`upload.md`](upload.md).

When this document conflicts with the CLI help, run `yike generate ... --help` and report the inconsistency to the user; only modify this document when the user explicitly requests skill maintenance.

## Common Parameters

The following parameters apply to most `generate` commands:

- `--format <format>`: Use `json` when the Agent executes; use `text` when the user explicitly requests human-readable output.
- `--wait`: After submitting the task, poll continuously until the task reaches a terminal state or times out.
- `--interval <seconds>`: Polling interval; default `3` seconds.
- `--timeout <seconds>`: Polling timeout; default `600` seconds.
- `--dry-run`: Output credit estimation and pre-submission info without submitting the generation task or deducting credits. The Agent must use this parameter before every real submission; do not pass `--wait`, `--interval`, or `--timeout` together with dry-run as they have no effect.
- `--yes`: Skip the CLI's own interactive confirmation. The Agent may only use this parameter to submit after the user has seen the current dry-run estimate and explicitly confirmed.

- Without `--wait`: Record `jobId` / `resumeCommand` and do not report completion; continue tracking per [`media-and-jobs.md`](media-and-jobs.md).

Execution rules:

1. Assemble complete generation parameters, then run `--dry-run --format json`; read `estimation.credits`, `estimation.balance`, `estimation.insufficient`, and `estimation.warnings` from the stdout JSON. Do not pass `--wait`, `--interval`, or `--timeout` with the dry-run command.
2. Present the estimated credits and warnings to the user. If the user intends to submit, ask whether to proceed and wait for explicit confirmation; if the user only requested an estimate, stop after presenting it.
3. The user's initial generation request, prior agreement, or auto-approval conditions do not substitute for manual confirmation after seeing the current estimate. Stop if the user declines or does not respond.
4. After user confirmation, keep the prompt, model, resolution, size, duration, count, and reference assets — parameters that affect credits or generation output — unchanged; replace `--dry-run` with `--yes` for the real submission. `--wait`, `--interval`, `--timeout` are polling parameters and are not among the parameters that must remain unchanged; add them to the real submission if the user wants to wait for results, omit them if the user only wants the `jobId`. Do not rely on interactive prompts in the Agent's terminal to confirm on behalf of the user.
5. When parameters change, a re-upload yields a different mediaId, or the dry-run estimate becomes stale, re-run dry-run and confirm again.
6. Read `jobId` and `resumeCommand` from the real submission's stdout JSON output; do not parse structured fields from stderr.

Multiple tasks can be confirmed in one batch, but all estimated credits and their total must be presented item by item first, and the user must explicitly confirm this group of tasks; do not submit unconfirmed tasks.

- User only wants `jobId`: do not pass polling parameters in dry-run; after confirmation, the real submission uses `--yes --format json` without `--wait`.
- User wants the final result: do not pass polling parameters in dry-run; after confirmation, the real submission uses `--yes --wait --format json`; pass `--interval` / `--timeout` only when overriding polling configuration.

## Reference Input Preprocessing

- Agent conversation attachments or local image/video paths are first processed per [`upload.md`](upload.md) via `yike media upload "<path>" --format json`.
- After the upload JSON returns a non-empty mediaId with status `Normal`, pass the typed reference parameter according to mediaType; if the type of an existing mediaId is unclear, first run `yike media info <mediaId> --format json`.
- Local images use `--reference-image <mediaId>`; local videos use `--reference-video <mediaId>`.
- Select the typed parameter based on mediaType. Images in `reference_to_video` or R2V models still use `--reference-image` — do not use `--reference-video` or the video generation `--reference-media-id`.
- `reference_to_video` / R2V is a task classification and does not mean the reference input must be a video; see [`video-model-capabilities.md`](video-model-capabilities.md) for model reference input capabilities.
- For a mediaId with a known type, pass the corresponding typed parameter directly — do not re-run `media upload`.
- HTTP(S) URLs can be used for tasks like `image_to_video` that accept URLs. Reference assets for `reference_to_video` must use mediaId; stop and report an error if a URL is received. Upload local files per [`upload.md`](upload.md).
- Reuse already-recorded path → mediaId within the same task; do not re-upload after a generation failure, timeout, or prompt adjustment.
- Process multiple attachments one by one per [`upload.md`](upload.md); do not submit the generation task until all uploads are complete.

## Image Generation

Use case: Standalone text-to-image or reference-image-to-image.

```bash
# Estimate first; present credits and wait for user confirmation
yike generate image "a futuristic coffee brand poster" --aspect-ratio 16:9 --n 2 --dry-run --format json
yike generate image "generate a poster based on reference image" --reference-image https://example.com/ref.png --dry-run --format json
yike generate image "generate a poster based on reference image" --reference-media-id <mediaId> --dry-run --format json

# After explicit user confirmation, keep generation parameters unchanged; examples below add --wait for waiting-for-result scenarios
yike generate image "a futuristic coffee brand poster" --aspect-ratio 16:9 --n 2 --yes --wait --format json
yike generate image "generate a poster based on reference image" --reference-image https://example.com/ref.png --yes --wait --format json
yike generate image "generate a poster based on reference image" --reference-media-id <mediaId> --yes --wait --format json
```

Parameter reference:

- `[prompt...]`: Image prompt text.
- `--prompt <text>`: Explicitly pass prompt text; equivalent to the positional argument. Passing both will cause an error.
- `--prompt-file <path>`: Read prompt from a file.
- `--negative-prompt <prompt>`: Negative prompt.
- `--reference-image <urlOrMediaId>`: Reference image URL or mediaId; repeatable. When provided, the default task type becomes `image_to_image`.
- `--reference-media-id <id>`: Reference image mediaId; repeatable.
- `--task-type <taskType>`: Auto-detected by default; commonly `text_to_image`, `image_to_image`.
- `--model <model>`: Model code; defaults to `wan2.7-image`, can also be overridden by `defaultModel`. Common model codes by taskType are listed in `yike generate image --help`; other codes can also be passed explicitly — actual availability is determined by the server.
- `--aspect-ratio <ratio>`: Default `16:9`; built-in size mappings support `16:9`, `9:16`, `1:1`, `3:4`, `4:3`, `21:9`.
- `--resolution <resolution>`: Default `1K`.
- `--size <size>`: Explicit size, e.g., `1728*972`; overrides the default size mapping.
- `--n <number>`: Number of images to generate; default `1`.
- `--seed <seed>`: Random seed.
- `--prompt-extend`: Enable prompt expansion.
- `--workspace-id <id>`, `--project-id <id>`, `--production-id <id>`: Override default context.

Local reference images and Agent conversation image attachments must be uploaded first; only use image mediaIds with status `Normal`.

## Video Generation

Use case: Standalone text-to-video, image-to-video, or reference-video generation.

```bash
# Estimate first; present credits and wait for user confirmation
yike generate video "a 5-second coffee ad clip" --duration 5 --resolution 720P --dry-run --format json
yike generate video "animate the reference image" --reference-image https://example.com/ref.png --duration 5 --dry-run --format json
yike generate video "reference this video motion" --reference-video <mediaId> --duration 5 --dry-run --format json

# After explicit user confirmation, keep generation parameters unchanged; examples below add --wait for waiting-for-result scenarios
yike generate video "a 5-second coffee ad clip" --duration 5 --resolution 720P --yes --wait --format json
yike generate video "animate the reference image" --reference-image https://example.com/ref.png --duration 5 --yes --wait --format json
yike generate video "reference this video motion" --reference-video <mediaId> --duration 5 --yes --wait --format json
```

Parameter reference:

- `[prompt...]`: Video prompt text.
- `--prompt <text>`: Explicitly pass prompt text; equivalent to the positional argument. Passing both will cause an error.
- `--prompt-file <path>`: Read prompt from a file.
- `--negative-prompt <prompt>`: Negative prompt.
- `--reference-image <urlOrMediaId>`: Reference image URL or mediaId; repeatable. Default task type becomes `image_to_video`. When explicitly specifying `reference_to_video`, mediaId must be used.
- `--reference-video <urlOrMediaId>`: Reference video URL or mediaId; repeatable. Default task type becomes `reference_to_video`; mediaId must be used in this case.
- `--reference-media-id <id>`: Only for reference video mediaIds with confirmed mediaType of video; repeatable. Default task type becomes `reference_to_video`. Use `--reference-image` for image mediaIds.
- `--task-type <taskType>`: Auto-detected by default; commonly `text_to_video`, `image_to_video`, `reference_to_video`.
- `--model <model>`: Model code; text-to-video defaults to `happyhorse-1.1-t2v`, image-to-video defaults to `happyhorse-1.1-i2v`; `reference_to_video` with only images defaults to `happyhorse-1.1-r2v`, with videos defaults to `wan2.7-r2v`. These input-sensitive defaults take priority over the global `defaultModel`; only an explicit `--model` can override them. When the account has Wonder video series enabled (determined by server-side account configuration), all video taskTypes without an explicit `--model` default to `Wonder-Pro`, taking priority over the above defaults and `defaultModel`. Common model codes by taskType are listed in `yike generate video --help`; other codes can also be passed explicitly — actual availability is determined by the server.
- `--aspect-ratio <ratio>`: Default `16:9`; built-in 720P size mappings support `16:9`, `9:16`, `1:1`, `3:4`, `4:3`.
- `--resolution <resolution>`: Default `720P`.
- `--size <size>`: Explicit size, e.g., `1280*720`.
- `--duration <seconds>`: Default `5` seconds.
- `--seed <seed>`: Random seed.
- `--prompt-extend`: Enable prompt expansion.
- `--workspace-id <id>`, `--project-id <id>`, `--production-id <id>`: Override default context.

Local reference videos and Agent conversation video attachments must be uploaded first; only use video mediaIds with status `Normal`.

## Parameter Selection Rules

When the user asks about models, resolution, aspect ratio, size, duration, or task type, answer according to the following order. The model code list is authoritative from the corresponding `yike generate image --help` / `yike generate video --help`; for model reference input capabilities, read [`video-model-capabilities.md`](video-model-capabilities.md).

### Input Text

- The positional argument prompt takes priority from command-line text; `--prompt <text>` is equivalent to the positional argument — use either one.
- Passing both the positional argument and `--prompt`, or both `--prompt` and `--prompt-file`, causes a direct error — it will not silently pick one.
- When `--prompt-file <path>` is passed, the content is read from the file and trimmed.
- If the prompt is missing, stop and request it — do not submit the generation task.

### Prompt Writing Rules

Convert user intent into an actionable media generation prompt. Preserve the subject, brand, characters, copy, scene, and constraints given by the user; supplement specific visual descriptions when key visual information is missing; do not fabricate facts.

General prompt structure reference: medium, subject, details, environment & composition, quality or style constraints. See [`generate-image.md`](generate-image.md) for more detailed image generation rules and [`generate-video.md`](generate-video.md) for more detailed video generation rules.

Image prompts include:

- Subject: characters, objects, brand elements, clothing, actions, or poses.
- Scene: location, era, weather, time of day, background layers.
- Visuals: style, composition, lens distance, lighting, color, material.
- Deliverable: canvas purpose, whether whitespace is needed, whether text is included.

Video prompts include:

- Subject continuity: who is in frame, consistent appearance and key props.
- Action and pacing: starting state, main action, ending state, speed or mood changes.
- Camera language: shot scale, camera position, camera movement, transitions, frame stability.
- Reference asset usage: reference image as first frame / style / subject constraint; reference video for motion, pacing, or camera reference.

When using local attachments, reference images, reference videos, URLs, or mediaIds, explicitly pass the corresponding typed parameter — do not merely describe "refer to the previous image" in the prompt. Use `--negative-prompt` when there are clear negative constraints, e.g., to exclude text, watermarks, deformed fingers, or unwanted background elements. Use `--prompt-extend` only when the user wants automatic expansion or creative completion; do not enable it by default when strict adherence to the user's original text is required.

### Context IDs

`productionId` / project ownership is selected in this order:

1. `--project-id`
2. `--production-id`
3. `config.projectId`
4. `config.defaultProductionId`

`workspaceId` uses `--workspace-id` first, then `config.workspaceId`.

### Task Type (taskType)

Image:

| Condition | taskType |
| --- | --- |
| `--task-type` explicitly passed | Use the passed value |
| Has `--reference-image` or `--reference-media-id` | `image_to_image` |
| No reference image | `text_to_image` |

Video:

| Condition | taskType |
| --- | --- |
| `--task-type` explicitly passed | Use the passed value |
| Has `--reference-video` or enters video reference via `--reference-media-id` | `reference_to_video` |
| Has `--reference-image` | `image_to_video` |
| No reference input | `text_to_video` |

- `reference_to_video` means generating a video using reference assets; it does not mean the reference asset's mediaType must be video.
- When only `--reference-media-id` is passed in video generation, the taskType is `reference_to_video`.
- Only use video generation's `--reference-media-id` when the mediaType is confirmed to be video; if the type is unknown, run `media info` first — do not guess based on the R2V model name.
- When an image mediaId serves as a first frame, subject, or style reference, pass `--reference-image <mediaId>`; this applies to `reference_to_video` taskType or R2V models as well.

### Model

Model selection order:

1. Explicit `--model <model>`
2. Account's Wonder video series default `Wonder-Pro` when enabled (video commands only, see below)
3. `yike config set defaultModel <model>`
4. taskType default model

- When the user does not specify a model, do not pass `--model` and do not modify `defaultModel`.
- Pure text-to-image/video uses `text_to_image` / `text_to_video`.
- Reference-image-to-image uses `image_to_image`.
- Reference-image-to-video uses `image_to_video`.
- When the user provides a reference video or requests reference to a video's motion/camera, use `reference_to_video`.
- When the user explicitly specifies model, resolution, size, duration, or reference assets, explicitly pass the corresponding parameters.

taskType default models:

| taskType | Default Model |
| --- | --- |
| `text_to_image` | `wan2.7-image` |
| `image_to_image` | `wan2.7-image` |
| `text_to_video` | `happyhorse-1.1-t2v` |
| `image_to_video` | `happyhorse-1.1-i2v` |
| `reference_to_video`, image reference only | `happyhorse-1.1-r2v` |
| `reference_to_video`, includes video reference | `wan2.7-r2v` |

When the account has Wonder video series enabled, the default model for the three video taskTypes above becomes `Wonder-Pro`; such accounts' `yike generate video --help` will also list `Wonder-Pro` / `Wonder-Standard`. The help model catalog updates after login, running `yike whoami` / `yike account`, or submitting a video generation; if help does not list Wonder models, first run `yike account --format json` then check help.

- Do not guess model reference input capabilities from model suffixes, model names, taskTypes, or help groupings.
- Read [`video-model-capabilities.md`](video-model-capabilities.md) for model reference input capabilities; if the model is not in the table, report insufficient information.
- On model failure, report the error and the parameters used.
- Only modify the model, resolution, aspect ratio, duration, or reference assets for a retry when the user confirms the adjustment.
- Do not silently switch models or downgrade parameters.

### Image Resolution, Aspect Ratio, and Size

Image defaults:

- `resolution`: `1K`
- `aspectRatio`: `16:9`
- `n`: `1`

When `--size` is not passed and resolution is `1K`, the CLI maps size by aspect ratio:

| aspectRatio | Default size |
| --- | --- |
| `16:9` | `1728*972` |
| `9:16` | `972*1728` |
| `1:1` | `1328*1328` |
| `3:4` | `1110*1480` |
| `4:3` | `1480*1110` |
| `21:9` | `1974*846` |

- When `--size` is explicitly passed, use that size.
- When `--resolution` is not `1K` and `--size` is not passed, do not derive a size.

### Video Resolution, Aspect Ratio, Size, and Duration

Video defaults:

- `resolution`: `720P`
- `aspectRatio`: `16:9`
- `duration`: `5`

When `--size` is not passed and resolution is `720P`, the CLI maps size by aspect ratio:

| aspectRatio | Default size |
| --- | --- |
| `16:9` | `1280*720` |
| `9:16` | `720*1280` |
| `1:1` | `960*960` |
| `3:4` | `832*1088` |
| `4:3` | `1088*832` |

- When `--size` is explicitly passed, use that size.
- When `--resolution` is not `720P` and `--size` is not passed, do not derive a size.
- When `--duration` is not passed, use `5`.
- Do not trim duration or rewrite model-level parameters.

## Common Workflows

### Standalone Image Generation

```bash
# Estimate first; present credits and wait for user confirmation
yike generate image "a futuristic coffee brand poster" --aspect-ratio 16:9 --n 2 --dry-run --format json
yike generate image "generate a poster based on reference image" --reference-image https://example.com/ref.png --dry-run --format json

# After explicit user confirmation, keep generation parameters unchanged; examples below add --wait for waiting-for-result scenarios
yike generate image "a futuristic coffee brand poster" --aspect-ratio 16:9 --n 2 --yes --wait --format json
yike generate image "generate a poster based on reference image" --reference-image https://example.com/ref.png --yes --wait --format json
```

The reference image can be a URL, an existing mediaId, or a mediaId from a local image upload with status `Normal`.

### Standalone Video Generation

```bash
# Estimate first; present credits and wait for user confirmation
yike generate video "a 5-second coffee ad clip" --duration 5 --resolution 720P --dry-run --format json
yike generate video "animate the reference image" --reference-image https://example.com/ref.png --duration 5 --dry-run --format json

# After explicit user confirmation, keep generation parameters unchanged; examples below add --wait for waiting-for-result scenarios
yike generate video "a 5-second coffee ad clip" --duration 5 --resolution 720P --yes --wait --format json
yike generate video "animate the reference image" --reference-image https://example.com/ref.png --duration 5 --yes --wait --format json
```

Select taskType based on reference input; when the user explicitly specifies, pass `--task-type` and `--model`.

### Parameter Query

When querying parameter defaults or selection order, read the "Parameter Selection Rules" section of this document and run:

```bash
yike config get --format json
yike generate image --help
yike generate video --help
```

Also read [`video-model-capabilities.md`](video-model-capabilities.md) for model reference input types and counts.

## Quick Error Reference

| Condition | Resolution |
| --- | --- |
| `Missing image/video prompt` | Provide the prompt; do not submit an empty task |
| Local path or Agent conversation attachment | First upload per [`upload.md`](upload.md) and wait for status `Normal` |
| Upload wait timeout | Execute the returned `media wait` resumeCommand; do not use `job watch/recover` |
| Upload mediaType does not match the reference usage | Report the actual type; do not submit the generation task |
| Explicit model does not match recorded reference input capabilities | Report the original CLI error; do not switch models or rewrite media types |
| Submission response missing `jobId` | Expose the raw error/response summary; do not report submission success |
| Model/resolution documentation inconsistent with CLI help | Execute per the current CLI help and report the inconsistency to the user |
