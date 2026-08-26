# Local Asset Upload (media upload)

Read this document when local image/video paths, Agent conversation image/video attachments, or waiting for an uploaded mediaId is involved. See root `SKILL.md` for shared rules.

## Input Routing

| Input | Action |
| --- | --- |
| Agent conversation attachment or local path | First run `yike media upload "<path>" --format json` |
| HTTP(S) URL | Pass directly to the corresponding `--reference-image` or `--reference-video`; do not upload |
| Existing mediaId | Pass directly to the corresponding typed parameter; if the type is unclear, first run `yike media info <mediaId> --format json` |

- Only process attachments explicitly used in the current user task.
- Resolve relative paths to actual paths under the current working directory; reference the full path in the command.
- Stop if the path does not exist, is not a regular file, or is not readable — do not proceed to upload or generation commands.
- Currently supported formats: images `png/jpg/jpeg/bmp/webp`, videos `mp4/mov`; report a format error for other extensions immediately.
- Stop for symlinks or content-extension mismatches; do not rename or link other files to bypass checks.

## Single File Upload

```bash
yike media upload "/path/to/reference.png" --format json
```

Execute in the following order:

1. Read `success`, `mediaId`, `status`, `mediaType`, `timedOut`, `resumeCommand`, and `outputs` from the JSON.
2. If `success` is not `true` or `mediaId` is empty, read `nextAction.command` from the error: if it exists, execute that exact recovery command; if not, stop and report the upload error.
3. When `success: true`, `status: Normal`, and mediaId is non-empty, record `path → mediaId → mediaType`; `outputs[]` contains the corresponding media information.
4. When `timedOut: true`, `status: Preparing`, and mediaId exists, execute the returned `resumeCommand`; that command uses `media wait` and retains the current `--interval` and `--timeout`.
5. Report any other non-`Normal` status directly; do not proceed to generation commands.

`media upload` accepts a single `<path>` and waits for media status by default with `--interval 2` and `--timeout 600`. Do not append `--yes`, `--dry-run`, or `--wait`.

When the upload fails before obtaining a mediaId, re-run `media upload` with the exact same path and context:

- When the error returns `nextAction.command`, prioritize executing the original command — do not omit workspace, production, or polling parameters.
- When an upload is incomplete, the CLI resumes progress for the same path.
- When the file has been fully transmitted but media registration fails, the CLI retries only the registration without re-transmitting the file.
- When the file content or modification time changes, old progress is not reused — it is uploaded as a new file.
- Do not run `media wait`, `job watch`, or `job recover` when there is no mediaId yet; re-run `media upload` with the same path first.

## Upload Wait

```bash
yike media wait <mediaIds...> --interval <seconds> --timeout <seconds> --format json
```

- `media wait` accepts one or more registered mediaIds; when polling parameters are not passed, it uses `--interval 2` and `--timeout 600`.
- Read `success`, `status`, `mediaIds`, `outputs`, `timedOut`, and `resumeCommand` from the JSON.
- Only pass these mediaIds to generation commands after `success: true`, `status: Normal`, and the corresponding `outputs[]` items contain non-empty mediaIds.
- If `media wait` times out again, retain mediaIds, status, timedOut, outputs, and resumeCommand, then execute the returned resumeCommand to continue waiting.
- Do not use `yike job watch` or `yike job recover` for upload and media status waiting.
- After a successful upload, recover generation tasks only using the `jobId` and `resumeCommand` returned by the generation command.

## Same-Task Reuse

- Within the same user task, record `path → mediaId → mediaType` for each successfully uploaded file.
- Reuse the recorded mediaId for the same path when the file has not changed; do not re-run `media upload`.
- Reuse the uploaded mediaId after a generation failure, timeout, or prompt adjustment.
- Do not run `media upload` when the user directly provides an HTTP(S) URL or mediaId.

## Multiple Attachments

1. First determine the attachments actually used by the current command and each attachment's purpose.
2. Execute single-file `media upload` sequentially in the order given by the user; do not pass multiple paths to a single upload.
3. After each item reaches `Normal` status, record path, mediaId, and mediaType.
4. If any item fails, stop subsequent generation; report the failed item and preserve already-successful mappings.
5. When resuming, only upload paths that do not yet have an available mediaId.

- `generate image` only accepts image references; pass multiple image mediaIds by repeating `--reference-image <mediaId>`.
- `generate video` image references use `--reference-image <mediaId>`; video references use `--reference-video <mediaId>`.
- When using `reference_to_video` taskType or R2V models, follow the same rule: image mediaIds must not be passed to `--reference-video` or video generation's `--reference-media-id`.
- Stop if the upload result's mediaType does not match the user's specified usage; do not switch command families or ignore attachments.

## Quick Error Reference

| Condition | Resolution |
| --- | --- |
| Path does not exist, is not a regular file, or is not readable | Report the path; do not upload |
| Symlink, content-extension mismatch, format error | Report the pre-check error; do not attempt to rename to bypass |
| Upload or media registration failed with no mediaId | Prioritize executing `nextAction.command`; otherwise re-run `media upload` with the same path and context |
| JSON missing mediaId or mediaId is empty — stop | Report upload failure; do not proceed to generation |
| Status is not `Normal` | Report current status; use `media wait` on timeout |
| `media wait` timeout | Retain mediaIds, status, timedOut, outputs, and resumeCommand; execute the returned resumeCommand |
| mediaType does not match usage | Report actual type; do not switch command families |
| One item in multiple attachments fails | Stop generation; preserve already-successful path → mediaId mappings |
