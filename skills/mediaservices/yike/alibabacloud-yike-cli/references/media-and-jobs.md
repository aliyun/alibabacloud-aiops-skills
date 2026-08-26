# Media Inspection & Job Recovery (media & jobs)

Read this document when verifying media after generation submission, tracking terminal states, or recovering tasks. See root `SKILL.md` for shared rules.

## Long-Running Command Quick Reference

Handle asynchronous commands per the table below:

| Command | Default Behavior | With `--wait` | Return Key | Recovery / Polling |
| --- | --- | --- | --- | --- |
| `yike generate image` | **Async**: returns `jobId` immediately after submission | Blocks polling until terminal state/timeout; result in `wait` field | `jobId`, `resumeCommand` | `yike job recover <jobId>` or `yike job watch <jobId>` |
| `yike generate video` | Same as above | Same as above | `jobId`, `resumeCommand` | Same as above |
| `yike job watch <id>` | **Blocks polling** until terminal state/timeout; default type=`ai-generation` | — (already polling) | `status`, `media`, `result`; on timeout appends `timedOut` + `resumeCommand` | Do not pass `--type` by default |
| `yike job recover <id>` | **Blocks polling** until terminal state/timeout using recorded task info | — (already polling) | `record`, `watch.status`, `watch.media` | Fall back to `job watch` when no recoverable record exists |

Associated conventions:

- `generate --wait` uses `--interval 3` seconds and `--timeout 600` seconds by default.
- After `generate` returns `resumeCommand`, prioritize executing that command.
- Use `yike job recover <jobId>` only when job info has been recorded and recovery from the record is needed.
- Success terminal states: `Finished` / `Success` / `Succeeded`.
- Failure terminal states: `Failed` / `Error` / `Canceled` / `Cancelled`.
- When `submitted` or only `jobId` is returned, continue tracking.

## Common Parameters

- `--format <format>`: Use `json` when the Agent executes; use `text` when the user explicitly requests human-readable output.
- `--interval <seconds>`: Polling interval; default `3` seconds.
- `--timeout <seconds>`: Polling timeout; default `600` seconds.

## Media Info Inspection

Use case: After generation, read the status, URL, duration, resolution, and file size of an existing mediaId.

```bash
yike media info <mediaId> --format json
yike media info <mediaId1> <mediaId2> --format json
yike media doctor <mediaId> --expect-duration 30 --min-width 1280 --min-height 720 --format json
```

Execute with the following parameters:

- `media info <mediaIds...>`: Batch read media information.
- `media doctor <mediaIds...>`: Quality gate on top of `info`; returns `success:false` with exit code `1` when warnings exist. Text mode prints human-readable warnings with associated mediaIds.
- `--expect-duration <seconds>`: Expected duration; when not passed, images are not checked for duration, but video/audio still requires a duration.
- `--duration-tolerance <seconds>`: Allowed duration deviation; default `1` second.
- `--min-width <pixels>` / `--min-height <pixels>`: Minimum resolution requirements.
- `--details`: Return full response details.

Main warnings:

- `media_missing_url`
- `media_missing_duration` (video/audio missing duration; or `--expect-duration` was passed but duration is still missing)
- `media_duration_mismatch`
- `media_missing_resolution`
- `media_resolution_too_low`

### Delivery Verification

1. Extract mediaId from the successful job result.
2. Run `yike media info <mediaId> --format json`.
3. When quality requirements exist, run `yike media doctor <mediaId> ... --format json`.
4. Deliver the final task status, mediaId, accessible URL, duration, width/height, file size, and warnings.

## Job Polling & Recovery

Use case: The command did not wait for completion, the wait timed out, or the Agent needs to continue tracking results per `resumeCommand`.

```bash
yike job watch <jobId> --format json
yike job recover <jobId> --format json
```

Execute with the following parameters:

- `job watch <id>`: Poll the specified task; default type=`ai-generation` — usually do not pass `--type`.
- `job recover <id>`: Resume polling using recorded task info.
- `--type <type>`: Override the default / locally recorded task type (currently only `ai-generation`).
- `--interval <seconds>`: Polling interval; default `3` seconds.
- `--timeout <seconds>`: Polling timeout; default `600` seconds.

Terminal state reference:

- Success: `Finished`, `Success`, `Succeeded`.
- Failure: `Failed`, `Error`, `Canceled`, `Cancelled`.

On success terminal state, read `mediaId`, width/height, duration, file size, and URL from `wait.outputs` / `watch.outputs`. On failure or timeout, read `code`, `error`, and recovery commands from the JSON.

### Recovery Discipline

| Condition | Action |
| --- | --- |
| Has `resumeCommand` | Execute `resumeCommand` |
| Has only `jobId` | Execute `yike job watch <jobId> --format json` |
| Has a local task record and needs record-based recovery | Execute `yike job recover <jobId> --format json` |
| Timeout | Retain `status`, `media`, `resumeCommand`; continue tracking or report back to the user |
| Failure terminal state | Report the actual status and recovery command; do not re-submit a new task |
| `submitted` or only `jobId` returned | Continue tracking; do not report completion |

## Quick Error Reference

| Condition | Resolution |
| --- | --- |
| Only has `jobId` | Wait for job terminal state and verify with `media info/doctor` |
| `Unsupported job type` | Remove `--type`, or explicitly pass `--type ai-generation` |
| `media doctor` returns warnings | Report warnings and `issueIds` to the user; only re-run generation after user confirmation |
| Missing `resumeCommand` | Re-extract from the original JSON output; use `jobId` watch if extraction is not possible |
