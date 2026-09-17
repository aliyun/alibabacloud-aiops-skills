---
name: alibabacloud-oss-multipart-upload-diagnosis
description: |
  Read-only diagnostics for OSS multipart upload. Use when a multipart
  upload is stuck or interrupted, a large file upload fails, or
  multipart fragments occupy storage. Finds fragments via read-only
  ListMultipartUploads, checks part size/concurrency limits,
  attributes server/client/network causes; cleanup guidance is
  manual-only. Triggers: "multipart upload stuck", "upload stuck at 0%", "resume interrupted upload", "multipart fragments occupy storage", "large file upload fails", "fragment cleanup", "resumable upload", "breakpoint resume". Do NOT use for single-request upload errors (use
  alibabacloud-oss-transfer-error-code-diagnosis), billing (use
  alibabacloud-oss-billing-diagnosis), endpoints (use
  alibabacloud-oss-endpoint-internal-diagnosis), signed URL V4 (use
  alibabacloud-oss-presigned-url-v4-diagnosis), browser/mini-program
  direct upload with CORS (use
  alibabacloud-oss-browser-upload-cors-diagnosis).
---

# OSS Multipart Upload Diagnosis

Diagnose Alibaba Cloud OSS large-file upload problems: "my 40GB backup multipart upload is stuck at 0%", "the upload was interrupted halfway, how do I resume it", "uploading a large file keeps failing", "the bucket seems empty but storage capacity is occupied by multipart fragments".

Core approach: verify the caller identity, locate the bucket's real region with the read-only GetBucketInfo control-plane query (ListBuckets fallback), enumerate unfinished multipart upload events with the read-only ListMultipartUploads to identify fragments, check the user's part size / concurrency against the official OSS multipart limits, and attribute stuck / interrupted / failed uploads to a server-side, client-side, or network cause via a decision tree. Conclude with evidence-based findings only; this skill never changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API — including `AbortMultipartUpload` (fragment cleanup), `PutObject`, `UploadPart`, `CompleteMultipartUpload`, `DeleteObject`, `DeleteBucket`, or any ACL/policy/lifecycle configuration change. Fragment cleanup is a WRITE operation: this skill only outputs manual cleanup guidance and command templates for the user to execute themselves (see [references/fragment-cleanup-guide.md](references/fragment-cleanup-guide.md)).
2. **MANDATORY entry-point enforcement:** All OSS diagnostics MUST be performed by running the scripts under `scripts/` (`multipart_upload_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts — the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively through the Alibaba Cloud default credential chain library; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / ListBuckets / ListMultipartUploads / GetCallerIdentity or the user-provided parameters. If a query fails or returns empty, record it and state the limitation — never invent upload IDs, fragment counts, or speed figures.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line — never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill only answers multipart / resumable upload questions (stuck / interrupted / failed attribution, part parameter sanity, fragment identification and cost impact, resume guidance). It does NOT handle single-request upload error-code semantics (EntityTooLarge / SignatureDoesNotMatch / FileAlreadyExists — defer to alibabacloud-oss-transfer-error-code-diagnosis), download problems, billing deduction details, or executing any cleanup — for such requests, state the boundary and give manual guidance only.

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

- "multipart upload stuck"
- "upload stuck at 0%"
- "resume interrupted upload"
- "multipart fragments occupy storage"
- "large file upload fails"
- "fragment cleanup"
- "resumable upload"
- "breakpoint resume"

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| single-request upload errors | `alibabacloud-oss-transfer-error-code-diagnosis` |
| billing | `alibabacloud-oss-billing-diagnosis` |
| endpoints | `alibabacloud-oss-endpoint-internal-diagnosis` |
| signed URL V4 | `alibabacloud-oss-presigned-url-v4-diagnosis` |
| browser/mini-program direct upload with CORS | `alibabacloud-oss-browser-upload-cors-diagnosis` |
| bucket deletion blocked by fragments / versioning recovery | `alibabacloud-oss-deletion-recovery-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `fragments` / `parameter_check` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-multipart-upload-diagnosis`
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every OSS SDK request (User-Agent header) and every `--user-agent` argument of the aliyun CLI identity call of that run, so all calls of one diagnosis can be correlated.

The shared client layer (`scripts/_oss_client.py`) implements this automatically: the session-id is generated lazily on the first call of each run and cached for the rest of the run.

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

Credentials are resolved exclusively by the Alibaba Cloud default credential chain — the skill never reads, prints or passes an AccessKey pair:
- OSS control-plane calls (Python oss2 SDK): resolved by the chain library `alibabacloud-credentials`, which picks the source itself (standard environment credentials, a CLI/credentials profile, or an instance RAM role).
- Identity check (`aliyun sts get-caller-identity`): the aliyun CLI default credential chain.

The OSS SDK leg needs the Python dependencies declared in `scripts/requirements.txt` (`oss2` plus the `alibabacloud-credentials` chain library) — install them once with `pip install -r scripts/requirements.txt` before the first run.

If either fails, guide the user to configure the chain (`aliyun configure`) — never ask for AK/SK.

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

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the write boundary instead: any fragment cleanup (AbortMultipartUpload) or lifecycle change MUST be executed by the user themselves after reviewing [references/fragment-cleanup-guide.md](references/fragment-cleanup-guide.md) — this skill never executes it, even when explicitly asked.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/multipart_upload_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: Multipart playbook | Official limits, stuck/interrupted/failed attribution tree, client-side evidence collection (Request ID self-check, client logs, ossutil output), fragment completeness |
| M2: Fragment cleanup guide | Fragment billing impact and MANUAL cleanup options (console / ossutil / lifecycle) — executed by the user, never by this skill |
| M3: RAM policies | Minimal read-only RAM policy required by this skill |

Documented run order: Step 1: Confirm Identity and Collect Inputs; Step 2: Run the Multipart Upload Diagnosis; Step 3: Interpret the Evidence and Attribute; Step 4: Conclusion and Suggestions.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket receiving the upload.
- **File size** (`--file-size`): optional but recommended, e.g. `40GB` / `512MB` / `1048576`; drives the part size / concurrency recommendation.
- **Part size** (`--part-size`): optional, e.g. `10MB`; validated against the OSS limits (100 KB .. 5 GB, resulting part count <= 10,000).
- **Concurrency** (`--concurrency`): optional; sanity-checked against the part count.
- **Symptom** (`--symptom`): optional — `stuck` / `slow` / `interrupted` / `failed` / `fragment`; selects the attribution branch of the decision tree.
- **Prefix** (`--prefix`): optional object-key prefix filter for the fragment listing.
- **Endpoint** (`--endpoint`) / **Region** (`--region`): optional; used to locate the bucket when the default query endpoint does not match.
- **Customer wording** (`--question`): optional; the customer's original question wording passed verbatim. Enables the official-doc verification leg (`doc_verification` section) — read-only, help.aliyun.com only, never blocks the diagnosis.
- **UID**: can always be omitted — it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted, UID derived, fragment-listing endpoint derived from the bucket location), the Agent MUST explicitly declare this in the response or report metadata.

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Multipart playbook | [references/multipart-playbook.md](references/multipart-playbook.md) | Official limits, stuck/interrupted/failed attribution tree, client-side evidence collection (Request ID self-check, client logs, ossutil output), fragment completeness |
| M2: Fragment cleanup guide | [references/fragment-cleanup-guide.md](references/fragment-cleanup-guide.md) | Fragment billing impact and MANUAL cleanup options (console / ossutil / lifecycle) — executed by the user, never by this skill |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the bucket name, the file size being uploaded, and the symptom. If the user reports an error code from a plain single-request upload, route it to the transfer-error-code skill per Absolute Rule 6 first.

### Step 2: Run the Multipart Upload Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/multipart_upload_diagnosis.py \
    --bucket <name> [--file-size 40GB] [--part-size 10MB] [--concurrency 8] \
    [--symptom stuck] [--prefix <object-prefix>] [--region <region>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Checks the multipart parameters with pure functions: recommended part size / part count / concurrency for the file size, and validation of any user-supplied part size against the official limits (object <= 48.8 TB, parts 1..10,000, part 100 KB..5 GB, PutObject <= 5 GB).
3. Locates the bucket via OSS `GetBucketInfo` (ListBuckets fallback), then enumerates unfinished multipart uploads with the read-only `ListMultipartUploads` (pagination capped), aging each event since its InitiateMultipartUpload time.
4. Emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Evidence and Attribute

Read `fragments` and `parameter_check` from the report:
- **unfinished uploads found (count > 0)** — fragments exist: an earlier attempt was interrupted/abandoned and its parts keep incurring storage fees. Advise resume (breakpoint) if the upload is still wanted, otherwise relay the MANUAL cleanup guidance of [references/fragment-cleanup-guide.md](references/fragment-cleanup-guide.md). Never execute the cleanup.
- **no unfinished uploads** — the stuck/failed transfer is client-side or network-side: apply the attribution tree of [references/multipart-playbook.md](references/multipart-playbook.md) using the client's Request IDs, client logs, and ossutil output.
- **invalid part configuration** — relay the recorded validation errors and the recommended parameters.
- **DEGRADED report** — relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent fragment counts or upload IDs.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual numbers/fields from the report (fragment count and ages, recommended part size / concurrency, validation errors). Base the conclusion on the script's `status` / `fragments` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based; every cleanup action is stated as manual guidance for the user only (this skill never applies any change).

## Important Notes

- **Fragment billing**: uploaded-but-unfinished/unaborted parts occupy storage space and keep incurring storage fees until the upload is completed or aborted (official AbortMultipartUpload doc). A bucket can look "empty" in the object list while fragments still consume capacity.
- **Official limits** (verified against help.aliyun.com, see [references/multipart-playbook.md](references/multipart-playbook.md)): single object <= 48.8 TB via multipart, 1..10,000 parts, part size 100 KB..5 GB (only the last part may be smaller than 100 KB), PutObject <= 5 GB.
- **Completion semantics**: an upload only exists as an object after CompleteMultipartUpload succeeds; parts alone are invisible in the object list. "Upload returned 200 but the file is missing" usually means CompleteMultipartUpload was never called.
- **FileAlreadyExists boundary**: `FileAlreadyExists` (EC 0026-00000002) is triggered by the request-level header `x-oss-forbid-overwrite: true`, not by a bucket-level setting, and is ineffective on versioning-enabled buckets; it belongs to single-request upload error semantics — defer to alibabacloud-oss-transfer-error-code-diagnosis.
- **Read-only operations**: only GetBucketInfo, ListBuckets, ListMultipartUploads, and `sts:GetCallerIdentity`; never modifies anything, never aborts uploads.

## Examples

**Example 1 — interrupted upload of a 40GB file**

> User: "Our 40GB backup multipart upload to bucket test-agentceping was interrupted overnight. UID 1552974654746705. Did it leave fragments, and how do I resume?"

```bash
python3 scripts/multipart_upload_diagnosis.py --bucket test-agentceping \
    --file-size 40GB --symptom interrupted --region cn-hangzhou
```

Report the fragment count and age distribution, the recommended part size / concurrency for 40GB, and the breakpoint-resume guidance. Declare any auto-filled parameters. If the report is `STATUS: DEGRADED` (e.g. missing RAM permission), relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 — multipart fragments occupy storage**

> User: "The bucket looks empty but the storage usage keeps growing; I suspect unfinished multipart fragments."

```bash
python3 scripts/multipart_upload_diagnosis.py --bucket <name> --symptom fragment
```

Relay the enumerated unfinished uploads (key, uploadId, initiated time, age) and the storage-cost note, then point to [references/fragment-cleanup-guide.md](references/fragment-cleanup-guide.md) for the MANUAL cleanup options. Do not execute AbortMultipartUpload.

**Example 3 — upload stuck at 0% with a suspicious part size**

> User: "Uploading a 40GB file is stuck at 0%; the code uses part size 1KB."

```bash
python3 scripts/multipart_upload_diagnosis.py --bucket <name> \
    --file-size 40GB --part-size 1KB --symptom stuck
```

Relay the validation errors (part below the 100 KB minimum, part count exceeding 10,000) and the recommended parameters; attribute the remaining stall with the client-side / network checklist of [references/multipart-playbook.md](references/multipart-playbook.md).

<!-- production-pattern-example -->

**Example N — A 40 GB upload stalls at 0 percent and fragments keep charging**

> User: "Uploading a 40 GB file with resume support never gets past 0 percent, and the bucket capacity grew even though the file never appeared."

```bash
python3 scripts/multipart_upload_diagnosis.py --bucket "my-bucket" --file-size "42949672960" --prefix "data/"
```

Report the recommended part size and part count for that object size, separate client-side stalling from service-side errors, and quantify unfinished parts as the capacity the customer is paying for.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/multipart_upload_diagnosis.py` | Diagnosis entry: multipart parameter sanity, bucket location, unfinished-upload (fragment) listing with aging, attribution guidance |
| `scripts/_doc_lookup.py` | Official-doc verification leg: help.aliyun.com llms-index lookup + cached index + .md body excerpts (stdlib only, zero credentials, never blocks the diagnosis) |

CLI options for `multipart_upload_diagnosis.py`: `--bucket <name>` (required), `--file-size <size>`, `--part-size <size>`, `--concurrency <n>`, `--symptom <stuck|slow|interrupted|failed|fragment>`, `--prefix <object-prefix>`, `--endpoint <endpoint>`, `--region <region>`, `--question "<customer original wording>"` (all optional; `--question` enables the `doc_verification` leg).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing `oss:GetBucketInfo` / `oss:ListMultipartUploads`, or bucket owned by another account | Record `[WARN]`, run the ListBuckets fallback, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| `InvalidAccessKeyId` / `SecurityTokenExpired` | Stale or wrong credential in the chain | Refresh the default credential chain; report `STATUS: DEGRADED` |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the findings with the actual evidence fields (fragment count / ages, part parameter validation, recommended parameters) — no fabricated values.
3. Declare every auto-filled parameter (endpoint defaults, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Present fragment cleanup strictly as manual guidance for the user (this skill never executes AbortMultipartUpload or any write).
6. When `doc_verification` is present, cite the doc URLs from `doc_verification.docs` verbatim, and state the offline-degradation sentence when `doc_verification.note` starts with DEGRADED.
