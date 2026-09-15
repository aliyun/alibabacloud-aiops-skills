---
name: alibabacloud-oss-image-processing-diagnosis
description: |
  Read-only diagnostics for OSS image processing. Use when an x-oss-process error occurs, an image style or watermark is not applied, image preview fails or the default domain forces download, original image protection 403, unsupported-format BadRequest, WebP conversion errors, HEIC thumbnail 400 errors, image-processing action order differences, or dynamic WebP processing failures.
  Triggers: "x-oss-process error", "image style not working", "original image protection 403", "watermark not applied", "image preview fails", "image forced download", "WebP conversion error", "HEIC thumbnail 400", "image-processing action order", "dynamic WebP processing".
  Not for transfer error codes, endpoints, billing, presigned URL/V4, direct-access links, or static hosting (use the matching OSS diagnosis skill); video / blind-watermark / document-preview (IMM) is out of scope.
---

# OSS Image Processing Diagnosis

Diagnose Alibaba Cloud OSS image processing (IMG) problems: "my x-oss-process URL returns BadRequest", "the image style is not working after I saved it", "why does my browser download the image instead of previewing it", "adding a watermark is not applied to the output", "original image protection returns 403".

Core approach: validate the `x-oss-process` parameter string offline against the official syntax and value ranges, then verify the source object with the three-step SOP - declared Content-Type (mime type), object size against the official 20 MB limit, and magic-number bytes of the file head - and finally probe a rendering with a read-only GET carrying the rendering query. Attribute "processing not effective" to a concrete cause (unsupported source format, size beyond the limit, invalid parameters, missing object, original-image protection 403, default-domain forced download). Conclude with evidence-based findings only; this skill never changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API - any object upload, deletion, ACL change, style creation/update, or bucket configuration change. This includes commands "for the user to run manually". If the user asks to create or change an image style, only output manual console guidance and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All diagnostics MUST be performed by running the scripts under `scripts/` (`image_processing_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against OSS or bypassing the scripts - the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by the scripts (HeadObject metadata, GET probe headers, magic bytes, GetBucketInfo). If a query fails or returns empty, record it and state the limitation - never invent formats, sizes, or error causes.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps, and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line - never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill only answers image-processing attribution questions (parameter syntax, source format/size verification, rendering failures, preview vs download, original-image protection). It does NOT handle video processing, blind watermarking (invisible watermark) or document preview (these belong to IMM intelligent media), CDN domain configuration (CDN cache effects are knowledge-level notes only), or billing - for such requests, state the boundary and give manual guidance only.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be
invoked with --question "<customer original wording>". The script first
matches embedded knowledge, then verifies against official OSS docs
(doc_verification, llms-index). The final answer MUST cite the URLs from
doc_verification.docs. If doc_verification.note starts with DEGRADED, state
explicitly: "Unable to verify against online official docs (offline)."
Never fabricate doc URLs; only URLs returned by the script may be cited.

## Trigger Conditions

Use this skill when the customer's own wording matches one of these phrases (the same list the `description` advertises):

- "x-oss-process error"
- "image style not working"
- "original image protection 403"
- "watermark not applied"
- "image preview fails"
- "image forced download"
- "WebP conversion error"
- "HEIC thumbnail 400"
- "image-processing action order"
- "dynamic WebP processing"

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| transfer error codes | `alibabacloud-oss-transfer-error-code-diagnosis` |
| endpoints | `alibabacloud-oss-endpoint-internal-diagnosis` |
| billing | `alibabacloud-oss-billing-diagnosis` |
| presigned URL / V4 signature issues | `alibabacloud-oss-presigned-url-v4-diagnosis` |
| direct-access links | `alibabacloud-oss-direct-access-link-diagnosis` |
| static hosting | `alibabacloud-oss-static-website-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the object key and processing string or style name are missing, do not infer either value or enumerate object candidates. State the evidence gap and request the object key plus the process/style or a specific symptom; do not run a live probe until the bucket and object are both present.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `source_screen` / `render_probe` / `process_validation` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-image-processing-diagnosis`
- **skill-version**: read at runtime from `references/manifest.json` (`version`), the single place where this skill's version is declared. It is never hardcoded, guessed or reused: the entry script resolves and validates it **before the first cloud call** and stops with `STATUS: FAIL` (exit 1) when the manifest is missing or its `version` is invalid.
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every OSS SDK request (User-Agent header) and every `--user-agent` argument of the aliyun CLI identity call of that run, so all calls of one diagnosis can be correlated.

The shared client layer (`scripts/_oss_client.py`) implements this automatically: the session-id is generated lazily on the first call of each run and cached for the rest of the run, and the skill-version is resolved lazily from `references/manifest.json` on the first User-Agent build.

### Exit codes (contract)

- `0` -- the run produced a conclusion: `STATUS: OK`, or `STATUS: DEGRADED`
  when part of the evidence was unavailable (the missing steps are recorded in
  `errors[]` and as `[WARN]` lines on stderr; the conclusion is still usable).
- `1` -- no usable conclusion: `STATUS: FAIL`, because required input is
  missing or every evidence call failed. `NEXT_ACTION` states what to ask the
  user for or what to fix; do not treat this as a success.
- `2` -- argparse usage error only (unknown option). A diagnosed condition never
  exits with `2`.

## Credentials

Credentials are resolved exclusively by the default credential chain:
- OSS calls (Python oss2 SDK): the environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and optionally `ALIBABA_CLOUD_SECURITY_TOKEN` (STS sessions).
- Identity check (`aliyun sts get-caller-identity`): the aliyun CLI default credential chain (environment or `~/.aliyun/config.json`).

Do not read, print, or pass AK/SK/STS tokens explicitly. If the identity check fails, guide the user to run `aliyun configure` - never ask for AK/SK.

### aliyun CLI version requirement

The scripts shell out to the aliyun CLI (at minimum the `aliyun sts get-caller-identity` identity pre-check), which MUST be **version 3.3.3 or newer**: older builds resolve the default credential chain differently and can drop the STS session token. Verify the installed version and upgrade it before the first run:

```bash
aliyun version        # must print 3.3.3 or newer (measured with 3.4.5)
aliyun upgrade --yes  # upgrade the installed CLI in place to the latest version
```

If the CLI is not installed at all, install the Alibaba Cloud CLI package for the host OS from the official release channel and then run `aliyun configure` (the profile stays in `~/.aliyun/config.json`; this skill never asks for AK/SK). When the CLI is missing, too old to upgrade, or unauthenticated, the identity pre-check degrades instead of aborting: `scripts/_oss_client.py` logs `[WARN] identity pre-check failed: ...` on stderr, records the empty UID, and the diagnosis still runs to a conclusion, because the identity label is traceability only and never evidence.

```bash
cd $SKILL_DIR

# Verify caller identity (informational only; credentials always come from the default chain)
python3 scripts/sts_token.py
```

## User Confirmation

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request falls outside image-processing attribution (style creation, video/IMM processing, CDN domain work, billing per Absolute Rule 6), do not proceed with any diagnosis - state the boundary and give manual guidance only.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/image_processing_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: Diagnosis playbook | Three-step source SOP (mime type -> size -> magic number), magic-number table, "processing not effective" attribution tree, resize/quality/animation semantics (lfit no-enlarge, lossy-only quality, GIF flattening, dynamic-WebP whitelist, IMG QPS quotas), default-domain forced download, original-image protection |
| M2: Parameters & limits | Official x-oss-process syntax, action set, parameter value ranges (incl. resize `limit`/`e`, quality q/Q, bare-value format), processing QPS/throughput quotas and source/output limits (with official documentation sources) |
| M3: RAM policies | Minimal read-only RAM policy required by this skill |

Documented run order: Step 1: Confirm Identity and Collect Inputs; Step 2: Validate the Parameter String (Offline); Step 3: Probe the Source and the Rendering; Step 4: Interpret the Verdict and Advise; Step 5: Conclusion and Suggestions.

## Input Parameters

- **Process string** (`--process`): optional; the exact `x-oss-process` value the client uses (e.g. `image/resize,w_300` or `style/small`). Validated offline against the official syntax; when a bucket/object is also given, it is additionally probed against the real object.
- **Bucket name** (`--bucket`) and **object key** (`--object`): required together for live probes; the image object to inspect.
- **Endpoint** (`--endpoint`) or **region** (`--region`): optional; used to reach the bucket. When both are absent the query endpoint is auto-defaulted and the bucket's real location from GetBucketInfo corrects it (auto-fill is always declared in the report).
- **Customer wording** (`--question`): optional; the customer's original question wording passed verbatim. Enables the official-doc verification leg (`doc_verification` section) - read-only, help.aliyun.com only, never blocks the diagnosis.
- **UID**: can always be omitted - it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted, probe endpoint derived from the bucket location, UID derived), the Agent MUST explicitly declare this in the response or report metadata.

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Diagnosis playbook | [references/image-processing-playbook.md](references/image-processing-playbook.md) | Three-step source SOP (mime type -> size -> magic number), magic-number table, "processing not effective" attribution tree, resize/quality/animation semantics (lfit no-enlarge, lossy-only quality, GIF flattening, dynamic-WebP whitelist, IMG QPS quotas), default-domain forced download, original-image protection |
| M2: Parameters & limits | [references/params-limits.md](references/params-limits.md) | Official x-oss-process syntax, action set, parameter value ranges (incl. resize `limit`/`e`, quality q/Q, bare-value format), processing QPS/throughput quotas and source/output limits (with official documentation sources) |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the bucket, object key and the exact `x-oss-process` string the client used. If the user only reports an error message, map it first with [references/image-processing-playbook.md](references/image-processing-playbook.md).

### Step 2: Validate the Parameter String (Offline)

```bash
cd $SKILL_DIR && python3 scripts/image_processing_diagnosis.py \
    --process "<x-oss-process-value>"
```

The pure-function validator checks the official syntax without any network call: `image/<action>,<key_value>/...` action names, parameter names and value ranges (resize w/h/l/s 1..16384, p 1..1000, modes lfit/mfit/fill/pad/fixed, `limit`/`e` switches 0/1; rotate; quality q/Q 1..100; format bare-value targets like `format,webp` - the `f_<target>` form is rejected live with EC 0040-00000206; interlace, sharpen, bright, contrast ranges), and the `style/<style-name>` form.

### Step 3: Probe the Source and the Rendering

```bash
cd $SKILL_DIR && python3 scripts/image_processing_diagnosis.py \
    --bucket <name> --object <key> [--process "<x-oss-process-value>"] \
    [--endpoint <endpoint>] [--region <region>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls GetBucketInfo to confirm the bucket region (ListBuckets fallback on degradation).
3. Runs the three-step source SOP: HeadObject for the declared Content-Type and size (steps 1+2), then a range GET of the first 16 bytes of the original object for magic-number verification (step 3).
4. When `--process` is given, issues the read-only rendering GET with that exact `x-oss-process` value and interprets status, Content-Type and Content-Disposition.
5. Emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 4: Interpret the Verdict and Advise

Read `source_screen.cross`, `render_probe` and `recommendations`:
- **mime_unsupported** - the declared Content-Type is not an image type (e.g. video or document): image processing cannot apply; advise the correct service for that media type.
- **placeholder_content / unknown_magic / magic_mismatch** - the stored bytes are not a real image of the declared type: the client must re-upload a valid file with the correct Content-Type.
- **over_limit** - the source exceeds the official 20 MB image-processing limit.
- **render 400 (image format not supported)** - the source fails processing despite its declared type; the magic-number result above distinguishes corrupted content from a wrong declaration.
- **render 403** - missing permission, or original-image protection is enabled (style-based access keeps working while direct original access is denied).
- **Content-Disposition: attachment / image preview fails** - OSS default-domain access serves images as downloads (only for buckets created AFTER 2019-09-30 15:00, and only for the 12 official image MIME types; response carries both `Content-Disposition: attachment` and `x-oss-force-download: true`); advise binding a custom domain (CNAME) or serving via CDN.
- **DEGRADED report** - relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent a cause.

### Step 5: Conclusion and Suggestions

Summarize the root cause with the actual fields from the report. Base the conclusion on the script's `status` / `source_screen` / `render_probe` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any change; style creation is manual console work).

## Important Notes

- **Supported source formats**: JPG, PNG, BMP, GIF, WebP, TIFF, HEIC, AVIF only; the source must be within 20 MB and the dimension limits in [references/params-limits.md](references/params-limits.md). Dynamic images (e.g. GIF, animated/dynamic WebP) support only resize/crop/watermark (downscaling only); rotate is NOT supported on GIF (silently flattens to static); other actions extract a single frame - an animated GIF becomes a static image after absolute-quality compression or format conversion.
- **Resize never enlarges by default (lfit semantics)**: when the target resolution exceeds the source (e.g. `resize,w_1500,h_1125` against a 1504x1120 original), the default `limit_1` returns the original resolution - output = min(target, source). Add `limit_0` to allow enlarging. "Resized output equals the original size" is this expected behavior, not a processing failure.
- **Quality applies to lossy formats only**: `q` = relative (percent of the source quality), `Q` = absolute (never above the source), range [1,100], effective on JPG/WebP; PNG and other lossless formats are unaffected - a PNG "quality not effective" report is expected behavior.
- **Dynamic WebP whitelist**: processing dynamic (animated) WebP sources fails with `BadWebPImage` unless the account has the animated-WebP whitelist - file a support ticket to enable it.
- **IMG QPS/throughput quotas**: default 50 QPS / 20 MB/s in cn-hangzhou, cn-shanghai, cn-beijing, cn-zhangjiakou, cn-shenzhen; 5 QPS / 2 MB/s elsewhere; higher limits require a support ticket (see the quotas table in params-limits.md).
- **OSS never compresses images by default**: storage keeps the original bytes; compression requires an explicit `x-oss-process` action (quality/format) or an IMM pipeline, and video files never accept image-processing parameters.
- **Trigger boundary (Do NOT use here)**: blind watermarking (invisible watermark), document preview, and any video/media processing belong to IMM intelligent media, not OSS IMG - hand off instead of diagnosing.
- **Declared type can lie**: a `.png` key may hold placeholder text or a JPEG body; the magic-number step is mandatory whenever the declared type looks like an image (see the SOP in the playbook).
- **Default-domain forced download**: accessing images through the OSS default domain makes browsers download instead of preview (only for buckets created AFTER 2019-09-30 15:00; the response carries `Content-Disposition: attachment` AND `x-oss-force-download: true`; 12 MIME types affected: image/jpeg, image/gif, image/tiff, image/png, image/webp, image/svg+xml, image/bmp, image/x-ms-bmp, image/x-cmu-raster, image/exr, image/x-icon, image/heic); the fix is a custom domain (CNAME) or CDN. Note: a signed SDK probe may not surface this header - attribute from the browser-visible behavior. CDN caching of processed results is a knowledge-level note only; this skill does not test domains.
- **Original-image protection**: when enabled on the bucket, direct access to the original is denied (403) while style-based access still works - this is configuration behavior, not a failure.
- **Style limit**: at most 50 styles per bucket; a style that was never saved or was deleted cannot apply. This skill cannot create styles (read-only).
- **Read-only operations**: only GetBucketInfo, HeadObject, GET probes, ListBuckets, and `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 - x-oss-process parameter error**

> User: "My app calls image/resize,w_99999 on bucket test-agentceping and gets an x-oss-process error."

```bash
python3 scripts/image_processing_diagnosis.py \
    --process "image/resize,w_99999" \
    --bucket test-agentceping --object test-assets/sample.jpg
```

The offline validator reports the width out of the official [1,16384] range; relay the `process_validation.issues` and the corrected URL form.

**Example 2 - image style not working**

> User: "The style URL x-oss-process=style/small returns the unchanged original - image style not working."

```bash
python3 scripts/image_processing_diagnosis.py \
    --bucket <name> --object <key> --process "style/small"
```

If the render probe fails or the output equals the original, point to style existence (max 50 per bucket, must be saved in the console) per the playbook; style creation is manual guidance only.

**Example 3 - image preview fails (forced download)**

> User: "Browsers download the picture instead of showing it - image preview fails."

```bash
python3 scripts/image_processing_diagnosis.py \
    --bucket <name> --object <key>
```

Explain the default-domain `Content-Disposition: attachment` behavior and advise a custom domain (CNAME) or CDN, quoting the report's recommendations.

<!-- production-pattern-example -->

**Example N - A style stops applying after CDN is put in front**

> User: "The watermark and resize style worked until I accelerated the bucket domain; now the original image is served."

```bash
python3 scripts/image_processing_diagnosis.py --process "image/resize,w_400/quality,q_80" --bucket "my-bucket" --object "img/photo.png"
```

Diagnose parameter stripping by the acceleration layer (ignore-parameters drops the x-oss-process query), not the processing service; then check the style existence and the source-size ceiling.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/image_processing_diagnosis.py` | Diagnosis entry: offline x-oss-process validation, three-step source SOP, rendering GET probe, attribution and advice |
| `scripts/_doc_lookup.py` | Official-doc verification leg: help.aliyun.com llms-index lookup + cached index + .md body excerpts (stdlib only, zero credentials, never blocks the diagnosis) |

CLI options for `image_processing_diagnosis.py`: `--process <value>` (optional), `--bucket <name>` + `--object <key>` (required together for live probes), `--endpoint <endpoint>` / `--region <region>` (optional), `--question "<customer original wording>"` (optional, enables the `doc_verification` leg).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 on probes | Missing read permission or original-image protection enabled | Record `[WARN]`, point to [references/ram-policies.md](references/ram-policies.md) and the protection section of the playbook; report `STATUS: DEGRADED` |
| `NoSuchKey` / 404 | Object key does not exist | Verify key spelling/case/prefix; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| 400 BadRequest "image format not supported" | Source not processable as an image | Follow the three-step SOP; relay the magic-number finding |
| Network timeout / DNS failure | Transient network issue or wrong-region endpoint | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the root cause with the actual evidence fields (declared Content-Type, object size, magic number, render status, Content-Disposition) - no fabricated values.
3. Declare every auto-filled parameter (endpoint default, location-derived endpoint, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Give style/configuration suggestions as manual guidance only (this skill never applies changes).
6. When `doc_verification` is present, copy the script's `Doc verification:` output line into the final answer (the matched wording or the `DEGRADED (offline)` wording, whichever the script printed) and cite the URLs from `doc_verification.docs` verbatim; when `doc_verification.note` starts with DEGRADED, state the offline-degradation sentence.
