# PDS Document and Audio/Video Analysis

**Scenario**: When you need to perform document or audio/video analysis on a PDS file
**Purpose**: Perform analysis on files and get structured analysis results

> **This is the ONLY correct way to analyze/summarize a PDS file's content.** For any "analyze / summarize / close-read / extract key points / what does it say" request, use `pds analyze` below. **Do NOT** `download-to-local` and then read/parse the file yourself — that produces none of the structured results here and pulls large media into context. Downloading is only for when the user explicitly wants the raw file saved locally.
>
> - ✅ "analyze this pdf for me" → `aliyun pds analyze --type doc`.
> - ❌ "analyze this pdf for me" → download the file, then read it yourself. **Never do this.**

---

## Inputs

`pds analyze` needs `drive_id` and exactly one of `--path` / `--file-id`. An absolute path is resolved internally. `revision_id` is **optional** — if omitted, the command auto-fetches the latest revision, so no separate `get-file` call is needed.

---

## Core Workflow

### Submit Analysis Task and Poll for Results

Use `aliyun pds analyze` to submit the analysis task and poll until processing completes. The command handles retries internally. It automatically selects the best available analysis path on the server, so you always call the same command regardless of domain capabilities.

```bash
# Document analysis — one call prints the readable analysis directly
aliyun pds analyze \
  --type doc \
  --drive-id "1" \
  --path "/Docs/report.pdf" \
  --sum true --kn 10 --qn 10 --chsum true \
  --format text

# Video analysis with feature flags (tr and ppt are video-only)
aliyun pds analyze \
  --type video \
  --drive-id "1" \
  --file-id "66e7e860a2360204b9414d5c866dd3a20af1974e" \
  --sum true --kn 10 --qn 10 --tr true --ppt true \
  --format text
```

Always use stdout. The command's tool result already contains the complete readable analysis; answer directly from it. Do **not** use `--save-to`, and do not save to a text file and then read that file by another tool. Make a **single** analyze call: once you have the stdout result, do not re-run `analyze` a second time with `--save-to` to "keep a copy" — the stdout result IS the deliverable, and a redundant save-to run is treated as a failure when the user only asked to see it in the conversation.

**Do not persist the analysis to any local file.** The stdout result shown in the conversation is the complete deliverable. Beyond avoiding `--save-to` and save-then-read, you **MUST NOT** take the stdout result and write it out with a separate `write_file`/save step — not as a `.md`/`.txt` report, not as a reformatted "analysis report", not as an archived copy. **This applies even if the runtime or task template says "save outputs to <dir>" or "any output files MUST go in <dir>": that generic instruction does not cover analysis results and never overrides the user's "no need to save a local result file / just show it in the conversation" instruction.** Persist the analysis only when the user *explicitly* asks you to save it. (A separately-mandated action/operation log is a different artifact and may be written — but it must not embed the analysis content.)

> **CRITICAL — boolean flags**: Every boolean feature flag below **MUST** carry an explicit value: `--sum true`, `--chsum true`, `--tr true`, etc. A bare `--sum` (without `true`) consumes the next token as its value and causes a parse error like `invalid boolean value: --kn`, wasting an entire retry cycle. Write the value explicitly every time.

**Parameter Description**:
- `--type`: `doc` (document) or `video` (audio/video).
- `--drive-id` plus exactly one of `--path` / `--file-id`: the file to analyze. `--revision-id` optional (latest auto-fetched if omitted).
- `--format`: `text` (readable formatted analysis) or `json` (raw result; the default).
- **Boolean feature flags (`--sum`, `--chsum`, `--nar`, `--img`, `--lay`, `--tr`, `--ppt`, `--keep-aspect-ratio`) require an explicit value — write `--sum true`, never a bare `--sum`. A bare flag consumes the next token as its value and fails (e.g. `--sum --kn` → `invalid boolean value: --kn`), forcing a retry.**
- `--sum`: Enable full-text summary (doc and video).
- `--kn <n>`: Number of keywords (e.g. `--kn 10`) (doc and video).
- `--qn <n>`: Number of guiding questions (e.g. `--qn 10`) (doc and video).
- `--chsum`: Enable chapter summaries, first page (doc only).
- `--chsumm <index>`: Chapter summary pagination — load page starting at `next_marker` (doc only).
- `--chsuml <size>`: Chapter summary page size (doc only).
- `--chsumv <token>`: Chapter summary version token from previous response (doc only).
- `--nar`: Enable paper narration/reading guide (doc only).
- `--img`: Enable image extraction (doc only). **Emits a long Image List — every extracted image with two long signed URLs — which can bloat the output past the tool's size cap and get it truncated. Only enable when the user explicitly asks for images; do NOT add it to a text-only close-reading/summary request.**
- `--lay`: Enable layout analysis (doc only). Only enable when the user asks about document layout/structure.
- `--tr`: Enable dialogue transcript (video only).
- `--ppt`: Enable PPT extraction (video only).
- `--extract-ppt <path>`: For `--type video` only — also export detected PPT slides to a PPTX file in the same call.
- `--keep-aspect-ratio`: With `--extract-ppt`, keep image aspect ratio (default fills the slide).
- `--lang <locale>`: Output language (doc and video). Supported values: `zh_CN`, `en_US`, `ja_JP`, `ko_KR`, `fr_FR`, `de_DE`, `es_ES`, `it_IT`, `ru_RU`, `pt_PT`, `tr_TR`, `ar_SA`, `hi_IN`, `th_TH`.
- `--save-to`: Optional local path to save the output (raw JSON in json mode, formatted text in text mode).
- `--max-attempts`: Optional max polling attempts (default 30).

**Parameter combinations**: A "complete deep analysis" is not a single flag — it requires combining multiple parameters. Scope the flags to what the request actually asks for:
- Text close-reading / summary / keywords / chapters (the common case): `--sum true --kn 10 --qn 10 --chsum true` (add `--nar true` for a reading guide). Do **NOT** add `--img`/`--lay` here — they add nothing to a textual analysis and `--img` can overflow/truncate the output (see the `--img` note above).
- Only add `--img true` / `--lay true` when the user explicitly wants extracted images or layout/structure analysis.
- Full video analysis: `--sum true --kn 10 --qn 10 --tr true --ppt true`

### Format Results

When `--format text` is passed above, the result is already formatted — no separate `format-analysis` step is needed.

If you have a raw JSON file (saved without `--format text`), use `format-analysis` to convert it:

```bash
aliyun pds format-analysis --type doc --input analysis_result.json --save-to formatted_output.txt
aliyun pds format-analysis --type video --input analysis_result.json --save-to formatted_output.txt
```

**Parameter Description**:
- `--type`: `doc` or `video`.
- `--input`: JSON result file path from `pds analyze --save-to`, json mode.
- `--save-to`: Formatted output file path (optional; prints to stdout if omitted).

### Chapter Summary Lazy Load (Optional)

If the initial response contained `doc_chapter_summaries_content.next_marker` and `doc_chapter_summaries_content.version`, you can load more chapters:

```bash
aliyun pds analyze \
  --type doc \
  --drive-id "1" \
  --file-id "66e7e860a2360204b9414d5c866dd3a20af1974e" \
  --chsumm <next_marker> --chsumv <version> \
  --format text
```

Use the `next_marker` and `version` values from the previous `doc_chapter_summaries_content` response. Repeat until `next_marker` is absent.

---

### Extract PPT from Video (one call)

If a video contains PPT, generate a PPTX — one slide per detected PPT shot, in order, with page/timestamp notes — in the same `analyze` call:

```bash
aliyun pds analyze \
  --type video \
  --drive-id 1 \
  --file-id <file_id> \
  --extract-ppt slides.pptx
```

- `--extract-ppt <path>`: run the analysis and, in the same call, write the PPTX. Only valid with `--type video`.
- `--keep-aspect-ratio`: preserve image proportions (default fills the slide).

**On success** returns: `{ "output": "...", "slides": <n>, "skipped": <n> }` (`skipped` counts pages whose image was missing or failed to download).

---

### Common Issues

##### 1. MultimodalAnalysisNotEnabled
```json
{
  "code": "MultimodalAnalysisNotEnabled",
  "message": "Multimodal analysis not enabled."
}
```
**Solution**: The analysis feature is not enabled for this domain. Contact PDS technical support.

##### 2. Signed URL Expired

**Cause:** Download took too long, signed URL has expired.

**Solution:** Re-request analysis results.
