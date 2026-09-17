---
name: alibabacloud-oss-browser-upload-cors-diagnosis
description: |
  Read-only diagnosis of browser/mini-program direct-upload failures and OSS CORS:
  preflight OPTIONS rejected,
  CORS rule missing/not effective,
  no Access-Control-Allow-Origin,
  expose-headers gaps (ETag / x-oss-request-id),
  PostObject policy issues.
  Templates only; never writes.
  Triggers:
  "upload reports CORS error",
  "CORS config not working",
  "browser direct upload 403",
  "mini program upload failed",
  "Please set the etag of expose-headers",
  "preflight OPTIONS failed",
  "No 'Access-Control-Allow-Origin'".
  Do NOT use for transfer error codes (alibabacloud-oss-transfer-error-code-diagnosis),
  multipart (alibabacloud-oss-multipart-upload-diagnosis),
  endpoints (alibabacloud-oss-endpoint-internal-diagnosis),
  signed URLs (alibabacloud-oss-presigned-url-v4-diagnosis),
  billing (alibabacloud-oss-billing-diagnosis),
  direct-access links (alibabacloud-oss-direct-access-link-diagnosis),
  static hosting (alibabacloud-oss-static-website-diagnosis).
---

# OSS Browser Direct Upload & CORS Diagnosis

Diagnose Alibaba Cloud OSS browser / mini-program / frontend direct-upload failures: "my web page upload reports a CORS error", "I configured CORS but it is not working", "the browser says No 'Access-Control-Allow-Origin'", "mini program upload failed with 403", "please set the ETag of expose-headers", "PostObject reports the policy is expired".

Core approach: verify the caller identity, confirm the bucket exists via the read-only GetBucketInfo control-plane query, read the bucket's real CORS rules with the read-only GetBucketCors query, match the browser Origin against the rules (preflight attribution), audit expose-headers for the headers browser SDKs need (ETag / x-oss-request-id), and check PostObject form-upload policy semantics (UTC expiration, form fields, x: custom variables). Conclude with evidence-based findings plus standard configuration templates. **This skill only outputs templates — it never writes any configuration** (applying CORS via PutBucketCors or the console is the user's own manual operation).

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API — e.g. `PutBucketCors`, `DeleteBucketCors`, `PutBucket*`, `DeleteBucket*`, `PutObject*`, `DeleteObject*`, or any ACL/policy/configuration change. This includes commands "for the user to run manually". When a CORS change is needed, only output the standard template as text and manual guidance, and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All diagnostics MUST be performed by running the scripts under `scripts/` (`oss_cors_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts — the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script. This prohibition covers the **command line itself**: never prefix a command with inline credential assignments such as `ALIBABA_CLOUD_ACCESS_KEY_ID=... ALIBABA_CLOUD_ACCESS_KEY_SECRET=... python3 ...`, and never pass credentials as CLI arguments, in heredocs, or in any echoed/executed command text — an inline assignment lands verbatim in the execution log and counts as a credential leak. The diagnosis environment already has the credential chain in place: run `python3 scripts/oss_cors_diagnosis.py ...` exactly as written (bare command, no credential prefix) and the scripts resolve credentials on their own. If a run fails with "no credentials found", report the failure and guide the user to run `aliyun configure` — never fetch, read, or inline credentials yourself.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / GetBucketCors / ListBuckets / GetCallerIdentity. If a query fails or returns empty, record it and state the limitation — never invent CORS rules, bucket locations, or request headers.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line — never silently skip or abort without a report. Note: a bucket with no CORS rule returns `NoSuchCORSConfiguration` from GetBucketCors — this is the semantic state "CORS not configured", NOT an error; report it as a finding and output the standard template.
6. **SCOPE BOUNDARY:** This skill only answers browser/mini-program direct-upload attribution and CORS/PostObject configuration-check questions. It does NOT handle server-side SDK upload/download error codes, multipart upload mechanics, endpoint/region selection, signed URLs, billing, or attack forensics — for such requests, state the boundary and defer to the sibling skill listed in the frontmatter.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Trigger Conditions

Route here when the user reports any of: browser/mini-program/frontend direct upload to OSS fails; the browser console shows a CORS error or `No 'Access-Control-Allow-Origin'`; preflight OPTIONS fails; a configured CORS rule seems not to take effect ("CORS config not working"); expose-headers are missing (ETag / x-oss-request-id, e.g. "Please set the etag of expose-headers"); PostObject form direct upload is rejected (policy expired / signature / form fields).

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `cors` / `recommendations` / `templates`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-browser-upload-cors-diagnosis`
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every OSS SDK request (User-Agent header) and every `--user-agent` argument of the aliyun CLI identity call of that run, so all calls of one diagnosis can be correlated.
- **skill-version**: resolved at runtime from the `SKILL_VERSION` environment variable, else from the top-level `version` string of [references/manifest.json](references/manifest.json) — never hardcoded and never guessed. Version resolution is a **failure gate**: it sits on the path of every cloud call, so when no version can be resolved the run stops **before** the first Alibaba Cloud call rather than issuing an unversioned request.

The shared client layer (`scripts/_oss_client.py`) implements this automatically: the session-id is generated lazily on the first call of each run and cached for the rest of the run, and `resolve_skill_version()` reads the manifest once per run and caches the version for every later call.

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
- OSS control-plane calls (Python oss2 SDK): the environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and optionally `ALIBABA_CLOUD_SECURITY_TOKEN` (STS sessions).
- Identity check (`aliyun sts get-caller-identity`): the aliyun CLI default credential chain (environment or `~/.aliyun/config.json`).

Do not read, print, or pass AK/SK/STS tokens explicitly. If the identity check fails, guide the user to run `aliyun configure` — never ask for AK/SK.

Credential commands — correct vs forbidden:

```bash
# CORRECT — bare command; the environment credential chain is already in place
python3 scripts/oss_cors_diagnosis.py --bucket <name>

# FORBIDDEN — credentials inline on the command line (leaks into execution logs)
ALIBABA_CLOUD_ACCESS_KEY_ID=<ak-id-placeholder> ALIBABA_CLOUD_ACCESS_KEY_SECRET=<ak-secret-placeholder> \
ALIBABA_CLOUD_SECURITY_TOKEN=<sts-token-placeholder> python3 scripts/oss_cors_diagnosis.py --bucket <name>
```

The forbidden form above is a hard failure regardless of whether the values are
real: any credential-shaped assignment in the command text is treated as a
credential leak. Placeholders included.

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

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request falls outside browser-upload / CORS attribution (server-side transfer error codes, multipart, billing, security forensics per Absolute Rule 6), do not proceed with any diagnosis — state the boundary and defer/give manual guidance only. Applying any CORS configuration always stays a manual user operation; never ask for confirmation to "apply" it on the user's behalf.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket the browser uploads to.
- **Browser Origin** (`--origin`): optional; the Origin header the upload page sends (e.g. `https://app.example.com`). When provided it is matched against the bucket's CORS rules to attribute preflight failures.
- **Query endpoint** (`--endpoint`): optional; the endpoint of the region where the bucket was created.
- **Expected region** (`--region`): optional; used to derive the query endpoint when `--endpoint` is absent.
- **Policy expiration** (`--policy-expiration`): optional; a PostObject policy `expiration` value (ISO8601 GMT, e.g. `2023-02-19T13:19:00.000Z`). Checked **offline** against the current UTC time (no network, no write) to attribute EC 0006-00000213 — see the timezone anti-pattern in Important Notes.
- **UID**: can always be omitted — it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted, UID derived), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --endpoint/--region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: CORS rules | [references/cors-rules.md](references/cors-rules.md) | CORS rule semantics, preflight (OPTIONS) cache, expose-headers, "rule not working" causes, standard CORS template |
| M2: Diagnosis tree | [references/diagnosis-tree.md](references/diagnosis-tree.md) | Error routing: No Access-Control-Allow-Origin / preflight failure / browser direct-upload 403 / PostObject policy errors |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Orchestration & Execution Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the bucket name and, if the user has it, the browser Origin and the browser-side error text. Map the error first with [references/diagnosis-tree.md](references/diagnosis-tree.md).

### Step 2: Run the CORS / Browser-Upload Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/oss_cors_diagnosis.py \
    --bucket <name> [--origin <browser-Origin>] [--region <region>] \
    [--policy-expiration <ISO8601-GMT>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK to confirm the bucket exists and fetch metadata; on failure falls back to `ListBuckets` (prefix lookup), logging `[WARN]` for every degraded step.
3. Calls OSS `GetBucketCors` (read-only). `NoSuchCORSConfiguration` is mapped to the semantic state **CORS not configured** (a finding, not an error); a 403 is degraded with `[WARN]`.
4. When `--origin` is given, matches it against the rules (at most one `*` wildcard per origin, scheme-sensitive, case-insensitive) and audits expose-headers for `ETag` / `x-oss-request-id`.
5. Emits the structured JSON report with the standard CORS template and the PostObject form template (text output only — never applied), plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdict and Advise

Read `cors` and `recommendations` from the report:
- **CORS not configured** — the bucket has no CORS rule: cross-origin browser requests are blocked by the browser's same-origin policy. Relay the standard template from `templates.cors_rule` and instruct the user to apply it manually (OSS console → Permission → CORS, or PutBucketCors — the user's own operation).
- **No rule matches the Origin** — check scheme inclusion (`http://` vs `https://`), subdomain coverage (`*.example.com` does not match the bare `example.com`), rule order, and the browser's preflight cache (stale OPTIONS results are the top "CORS config not working" cause — clear cache or test in private mode).
- **Expose-headers gap** — browsers hide `ETag` / `x-oss-request-id` from JavaScript unless listed; advise adding them per the template.
- **PostObject failures** — walk the policy checklist in `templates.postobject_form`: expiration is UTC (do not blame timezone fill-in for EC 0006-00000213; real causes are a too-short window, stale cached policy, or a skewed issuing-server clock), the `file` field must be last, STS signing needs `x-oss-security-token`, and each custom variable is its own `x:` form field.
- **DEGRADED report** — relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent CORS rules.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual fields from the report. Base the conclusion on the script's `status` / `cors` / `recommendations` / `next_action` fields rather than re-deriving them. All configuration suggestions are manual guidance quoting the report's templates; this skill never applies any change.

## Important Notes

- **Never write configuration**: PutBucketCors / DeleteBucketCors are absolutely prohibited; templates are output as text only.
- **"CORS not configured" is a valid finding**: GetBucketCors returning NoSuchCORSConfiguration means the bucket has no rule — output the standard template, do not surface it as an API failure.
- **Preflight cache**: after CORS rules change, browsers may keep using the cached OPTIONS response (MaxAgeSeconds); "still failing after I configured CORS" is usually stale cache or a CDN/proxy stripping headers — test in private mode.
- **Expose-headers**: `ETag` must be exposed for SDKs confirming uploads / resumable upload; `x-oss-request-id` for troubleshooting ("Please set the etag of expose-headers" targets exactly this).
- **PostObject timezone anti-pattern**: policy `expiration` is UTC; EC 0006-00000213 is NOT caused by filling Beijing time — check window length, cached stale policy, and issuing-server clock skew instead.
- **PostObject custom variables**: each is a standalone multipart form field with the `x:` prefix (not the `x-oss-callback-var` header used by PutObject / CompleteMultipartUpload); empty callback values trace back to empty/missing `x:` fields.
- **Read-only operations**: only GetBucketInfo, GetBucketCors, ListBuckets, and `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 — browser upload blocked: no Access-Control-Allow-Origin**

> User: "My web page at https://app.example.com uploads to bucket test-agentceping and the browser reports CORS error: No 'Access-Control-Allow-Origin'."

```bash
python3 scripts/oss_cors_diagnosis.py --bucket test-agentceping --origin https://app.example.com
```

Report the `cors` finding (e.g. the bucket has no CORS rule configured), relay the standard template from `templates.cors_rule` as manual guidance, and declare any auto-filled parameters. If the report is `STATUS: DEGRADED` (e.g. missing RAM permission), relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 — CORS configured but not working**

> User: "I already set CORS rules but the upload still fails. Upload reports CORS error every morning, works after clearing cache."

```bash
python3 scripts/oss_cors_diagnosis.py --bucket <name> --origin <page-origin>
```

If a rule matches the Origin, attribute the failure to the preflight cache / CDN stripping per the recommendations; advise clearing cache, verifying `Return Vary: Origin` behind CDN, and re-testing in private mode.

**Example 3 — expose-headers / PostObject policy**

> User: "Please set the etag of expose-headers for my bucket; also our PostObject uploads sometimes say the policy is expired."

```bash
python3 scripts/oss_cors_diagnosis.py --bucket <name>
```

State that expose-headers changes are manual (output the template with `ETag` / `x-oss-request-id`), and walk the PostObject policy checklist (UTC expiration semantics, fresh policy per session, `x-oss-security-token` for STS).

<!-- production-pattern-example -->

**Example N — Direct upload works once then fails again after a browser restart**

> User: "Browser POST upload fails with a CORS error. I already allowed all origins, but the console still complains about expose headers."

```bash
python3 scripts/oss_cors_diagnosis.py --bucket "my-bucket" --origin "https://app.example.com"
```

Point at the missing ExposeHeader for `ETag` and `x-oss-request-id` (the browser blocks reading them otherwise) and warn that a cached preflight response keeps failing until refreshed; hand over the standard CORS template.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/oss_cors_diagnosis.py` | Browser-upload/CORS diagnosis entry: GetBucketInfo + GetBucketCors + Origin matching + expose-headers audit + standard CORS/PostObject template output |

CLI options for `oss_cors_diagnosis.py`: `--bucket <name>` (required), `--origin <browser-Origin>` (optional), `--endpoint <endpoint>` (optional), `--region <region>` (optional), `--policy-expiration <ISO8601-GMT>` (optional; offline PostObject policy-expiration check for EC 0006-00000213).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `NoSuchCORSConfiguration` (404 from GetBucketCors) | The bucket has no CORS rule — a configuration state, not a failure | Report "CORS not configured" and output the standard template for manual application |
| `AccessDenied` / 403 | Missing `oss:GetBucketCors` / `oss:GetBucketInfo`, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| Browser still blocked after configuration | Stale preflight cache, CDN/proxy stripping CORS headers, scheme/subdomain mismatch | Route with [references/diagnosis-tree.md](references/diagnosis-tree.md); test in private mode |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the root cause with the actual evidence fields (CORS configured/not configured, matched rule, expose-headers gap) — no fabricated values.
3. Declare every auto-filled parameter (endpoint default, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Deliver CORS/PostObject changes as text templates plus manual guidance only (this skill never applies any configuration).
6. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."

