# Video Safety Rules

## Credentials

- ODPS auth uses env vars: `ODPS_ACCESS_ID`, `ODPS_ACCESS_KEY`,
  `ODPS_PROJECT`, `ODPS_ENDPOINT`. Read with `os.getenv` or
  `dotenv.load_dotenv`. Never embed values literally.
- OSS access uses STS via `role_arn` for the **mount / download paths**
  — `with_fs_mount(..., storage_options={"role_arn": OSS_ROLE_ARN})`
  and `url.download(storage_options={"role_arn": OSS_ROLE_ARN})`.
- OSS access for **AI FUNC multi-modal `cp.image(...)`** is the
  exception: the inference service runs in its own context and cannot
  use the caller's role_arn. Pass static OSS AK/SK on every
  `cp.image(data=..., type=ImageContentType.IMAGE_URL, storage_options={
  "access_key_id": OSS_ACCESS_KEY_ID, "access_key_secret":
  OSS_ACCESS_KEY_SECRET})`. Keys come from env vars; never hardcode.
- `DASHSCOPE_API_KEY` must not appear in generated code. AI FUNC models
  loaded via `read_odps_model` use platform-managed credentials.

## Path safety

- Treat OSS paths as opaque strings; don't synthesize them by
  concatenating user-controlled fragments.
- Frame extraction UDFs must only translate `OSS_ROOT/...` paths into
  mount paths. If an input row's `video_path` is outside `OSS_ROOT`,
  fail the row with `error_stage="frame_extraction"`,
  `error_msg="path_outside_root"` rather than silently mounting another
  bucket.
- Keyframe expansion UDFs must reject `..` traversal and absolute /
  local paths.
- OSS write-back paths (frame JPEGs, derived embeddings if any) must
  stay under a declared output prefix.

## Customer-data safety

- Do not mention real customer names, OSS buckets, ODPS projects, or
  domain-specific labeling rules in generated code or walkthroughs.
- Use `LABEL_PROMPT_STYLE` as a parameter, not as a baked-in literal.
  When the customer provides a label prompt, treat it as untrusted text
  inside the generated file (no executable injection, no path joins).
- Do not log raw image bytes or full transcripts to stdout in production
  scaffolds; show only counts and summary stats.

## Resource safety

- Default `FFMPEG_TIMEOUT_SEC=300` to avoid runaway ffmpeg subprocesses.
- Default `FRAME_FPS=1/1` (1 frame/sec) to keep frame counts bounded.
  Raise only when the customer asks.
- Default `TRANSCRIBE_MAX_DURATION_SEC=120` for any audio-side work
  (this skill normally doesn't do audio, but if a hybrid pipeline pulls
  audio for video clips, follow the audio skill's rule).

## What to never invent

- `ContentPart.image(...)` **without** `storage_options={"access_key_id":
  OSS_ACCESS_KEY_ID, "access_key_secret": OSS_ACCESS_KEY_SECRET}` when
  the data is an OSS URL — the AI FUNC inference service can't fetch
  the image without these credentials inline.
- `running_options={"gu_quota_name": ...}` / `{"inference_quota_name": ...}`
  on AI FUNC `model.generate` / `model.embed` calls — AI FUNC is
  MaxFrame's built-in Bailian inference; it does not take a GPU quota
  on this code path. The lookup will fail. Valid AI FUNC
  `running_options` keys are behavior knobs only:
  `enable_thinking` (False for Qwen3 reasoning models to skip CoT in
  the response), `enable_real_rpm_stats`, `verbose`. See
  ai_func_calls.md for details. (Audio ASR via the audio accessor —
  `df["x"].audio.transcribe(gu=..., gu_quota=...)` — is a different
  API surface that DOES take `gu` / `gu_quota` directly; it is NOT AI
  FUNC.)
- `params={"dimension": EMBEDDING_DIM}` — wrong key (singular) and
  wrong location. Use top-level `dimensions=EMBEDDING_DIM` for text
  embedding only.
- A "video" Series accessor — there is no `df["x"].video.*` API in 2.7.
  Frame extraction must go through the `apply_chunk` + ffmpeg pattern.
