---
name: alibabacloud-oss-transfer-error-code-diagnosis
description: |
  Zero-cloud-API routing of OSS upload/download error codes to root
  causes. Do NOT use for: endpoint (alibabacloud-oss-endpoint-internal-diagnosis),
  billing (alibabacloud-oss-billing-diagnosis), multipart
  (alibabacloud-oss-multipart-upload-diagnosis), presigned URL
  (alibabacloud-oss-presigned-url-v4-diagnosis), image processing
  (alibabacloud-oss-image-processing-diagnosis), deletion/residue
  (alibabacloud-oss-deletion-recovery-diagnosis), forensics
  (alibabacloud-oss-security-incident-forensics), client tools
  (alibabacloud-oss-client-tools-diagnosis), throttling
  (alibabacloud-oss-quota-throttling-diagnosis). Triggers: "403 AccessDenied during OSS upload", "SignatureDoesNotMatch", "OSS RequestTimeout", "OSS upload timeout", "EntityTooLarge", "SlowDown", "InvalidAccessKeyId", "SecurityTokenExpired", "OSS download fails with 403", "OSS upload failed", "409 BucketAlreadyExists". Skip non-OSS errors (SSH/MySQL/CDN).
---

# OSS Transfer Error Code Diagnosis

Diagnose Alibaba Cloud OSS upload/download failures by error code: "my upload returns 403 AccessDenied", "SignatureDoesNotMatch when pushing objects", "download keeps hitting RequestTimeout", "PostObject rejects a small image with EntityTooLarge", "requests get SlowDown", "cannot create the bucket: 409 BucketAlreadyExists".

Core approach: take the customer-reported error code / HTTP status / operation, map it through the embedded official error-code catalog to a root-cause direction (permission, credential/signature, client network, tool usage, file limits, or server side), distinguish client-side vs server-side responsibility, and deliver verbatim troubleshooting steps plus network optimization / transfer acceleration suggestions. This skill makes zero cloud API calls and performs no live network probing; all reasoning comes from the catalog distilled from official documentation and 472 real support tickets.

## Absolute Rules

1. **MANDATORY entry script:** All diagnosis MUST be performed by running `python3 scripts/oss_transfer_error_diagnosis.py` with the parameters gathered from the user. The Agent is forbidden from diagnosing by free-form reasoning alone or bypassing the script - the script embeds the official error-code catalog, the matching ladder, and the ticket-based troubleshooting steps.
2. **ABSOLUTE PROHIBITION (no writes, no cloud calls):** Under **NO** circumstances may you invoke any mutating OSS operation, any aliyun CLI command, or any cloud API from this skill. This skill is knowledge-driven and read-only by design: it never probes the network, never touches buckets or objects, and never executes commands "for the user to run" that mutate resources. Do not read, print, or accept AK/SK/STS tokens; no credentials are needed at all.
3. **NO FABRICATION:** Every error code, HTTP status, root-cause direction, and troubleshooting step MUST come from the script output (which reflects the embedded official catalog and ticket clustering). Never invent error codes, limits, or doc links. If the input matches no catalog entry, say so and ask for the full error response body. `--error-code` and `--http-status` accept only values quoted verbatim from the user's own messages: never substitute a candidate code taken from the catalog, the docs, or your own knowledge, and never present an invented error body as user-provided - when no code was supplied the run stays `STATUS: FAIL`.
4. **EXECUTION RULE FOR ERRORS:** If the script exits with `STATUS: FAIL`, report the failure reason verbatim from `NEXT_ACTION` and ask the user for the missing input (full error body: Code, Message, RequestId). Never silently guess a diagnosis. On `STATUS: DEGRADED`, present the candidate list and ask for the exact error code before concluding.
5. **SCOPE BOUNDARY:** This skill only diagnoses OSS upload/download error codes and attributes root cause. It does NOT handle DDoS sandbox mitigation, deleted-data recovery, commercial refunds, or presigned-URL generation - for such requests, state the boundary, point to the sibling skill listed in the description where applicable, and recommend a human support ticket.

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

- "403 AccessDenied during OSS upload"
- "SignatureDoesNotMatch"
- "OSS RequestTimeout"
- "OSS upload timeout"
- "EntityTooLarge"
- "SlowDown throttling"
- "InvalidAccessKeyId"
- "SecurityTokenExpired"
- "OSS download fails with 403"
- "OSS upload failed"
- "409 BucketAlreadyExists"

Context limits (guard rails against cross-product absorption):

- Timeout / 403 / connection-reset wording qualifies ONLY inside an OSS
  transfer context: the failing request must target Alibaba Cloud OSS. SSH,
  MySQL, Redis, MongoDB, PostgreSQL, RDS, CDN, k8s, docker connectivity
  failures - or an ECS host-level curl probe against a non-OSS address -
  are NOT this skill's cases even when the same trigger words (timeout, 403,
  or their non-English equivalents) appear; confirm the target product first (see
  references/scope-and-limitations.md).
- Symptom-only sentences stay in scope: when the customer describes the
  phenomenon without any error code ("large-file uploads keep breaking",
  "downloads die halfway", "the bucket domain is unreachable while the
  plain endpoint works"), run the entry script with `--question "<customer
  original wording>"` - the symptom layer lists candidate directions as a
  degraded list and asks for the error response body.

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

## Execution Principle

Run the entry script once with all known parameters; read the structured JSON it prints, then compose the answer strictly from it. The matching ladder is deterministic: exact catalog hit (`STATUS: OK`) -> fuzzy match or HTTP-status-only candidates (`STATUS: DEGRADED`) -> no recognizable input (`STATUS: FAIL`). Do not re-implement the matching or the catalog in chat; the pure matching functions live in the script and are covered by its inline assertions.

## Observability

The entry script generates per run, even though this skill makes zero cloud API calls:
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) created once per run and embedded in the output JSON.
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-transfer-error-code-diagnosis`; the assembled string is emitted in the `user_agent` field so any future HTTP usage would be traceable.

### Exit codes (contract)

- `0` -- the run produced a conclusion: `STATUS: OK`, or `STATUS: DEGRADED`
  when part of the evidence was unavailable (missing steps are recorded in
  `errors[]` and as `[WARN]` on stderr; the conclusion is still usable).
- `1` -- no usable conclusion: `STATUS: FAIL`, typically because required input
  is missing. `NEXT_ACTION` states what to ask the user for; never treat exit
  `1` as a successful diagnosis.
- `2` -- argparse usage error only (unknown option). A diagnosed condition never
  exits with `2`.

## Credentials

This skill makes zero cloud API calls and needs NO credentials at all: it never reads, writes, asks for, or accepts AK/SK/STS tokens, and never prompts the user for any credential. All inputs are the user-supplied error details (error code, HTTP status, RequestId, bucket, operation), processed entirely offline. If a user volunteers credentials, refuse them and continue with the error details only.

## User Confirmation

This skill is read-only: it never creates, changes or deletes configuration,
objects or buckets, so its own execution needs no change-approval gate.

Confirmation IS required in these two situations:

1. The target resource (bucket, object key, endpoint, domain) was inferred by
   the agent rather than stated by the customer -- echo the inferred value back
   and get agreement before running the script.
2. The conclusion recommends a mutating console action (create a rule, change
   ACL or policy, enable versioning, delete fragments). This skill only drafts
   the steps; the customer performs them.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/oss_transfer_error_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

## Input Parameters

All parameters are optional; auto-fill from the user's message when present and never block on missing ones - run the script with what is known and let `STATUS`/`NEXT_ACTION` drive follow-up questions.

| Parameter | Meaning | Auto-fill source |
| --- | --- | --- |
| `--error-code` | OSS error code from the response body (`<Code>`), fuzzy matching allowed; EC numeric aliases (e.g. `0015-00000001`) and SDK stack-trace names (e.g. `ConnectionReset`, `getaddrinfo failed`) route too | quoted error text, e.g. `AccessDenied`, `SignatureDoesNotMatch` |
| `--http-status` | HTTP status such as 400/403/404/429/500/503 | "HTTP 403 error", "got a 503" |
| `--request-id` | OSS RequestId, echoed for support escalation; when it is the ONLY input the run stays FAIL and attaches the `request_id_guidance` block (per-client-type paths to recover the error body) | `RequestId: ...` in the error body |
| `--bucket` | Bucket name for context (never validated remotely) | bucket mentioned by the user |
| `--operation` | `upload` or `download` | "upload fails" -> upload, "download errors" -> download |
| `--question` | Customer's original wording; drives the symptom-keyword routing layer (candidate directions when no code can be extracted), the out-of-domain guards, and the official-doc verification leg | the customer's first message, quoted verbatim |

## Module Index

| Reference | Purpose |
| --- | --- |
| `references/error-code-catalog.md` | Full error-code catalog with official documentation sources |
| `references/troubleshooting-playbook.md` | Four-track playbook: permission / credential / network / tool usage, aligned to ticket root-cause clusters |
| `references/scope-and-limitations.md` | Out-of-scope topics and the human-escalation wording |
| `references/ram-policies.md` | RAM/permission posture declaration for this zero-cloud-API skill |

## Diagnostic Flow

1. **Collect** whatever the user provides: error code, HTTP status, RequestId, bucket, operation. Auto-fill the parameters; do not demand everything up front.
2. **Run** `python3 scripts/oss_transfer_error_diagnosis.py --error-code <code> [--http-status <n>] [--request-id <rid>] [--bucket <b>] [--operation <op>] [--question "<customer original wording>"]`.
3. **Interpret** the JSON: `diagnosis.category` gives the root-cause track; `diagnosis.side` tells whether the fix is client-side or server-side; `root_cause_directions` and `troubleshooting_steps` are reported verbatim; `network_optimization_suggestions` appears for network-category errors. `match.type` values: `exact`/`fuzzy`/`synonym` (diagnosis), `synonym_family` (a bare family word for "timeout" yields both timeout candidates), `status_only`/`ambiguous` (candidate list), `symptom` (symptom-keyword candidates), `domain_guard` (non-OSS product refusal), `none` (FAIL). An `ec_code_referral` block routes wrong-door EC codes (e.g. `0003-00000005`) to the owning sibling skill; a `request_id_guidance` block appears when only a RequestId is available.
4. **Follow up** per `NEXT_ACTION`: on `DEGRADED`, ask for the exact error code to disambiguate candidates; on `FAIL`, request the full error response body.
5. **Report** following the Final Answer Contract below.

## Important Notes

- Error-code semantics follow the official Alibaba Cloud OSS documentation (HTTP 400/403/404/503 error-code references); root-cause directions and troubleshooting steps are distilled from 472 real support tickets (permissions 196, client network 87, credential/signature 57, tool usage 49, custom domain 25, CORS 13, hotlink 9).
- 403-family errors are permission-or-credential problems in the overwhelming majority of tickets; timeout-family errors are client-network problems unless proven otherwise by a same-region ECS control test.
- The script performs no DNS lookups, no TCP connections, and no API calls; it is safe to run in restricted environments.

## Examples

**Example 1 - exact code hit (upload, limit track)**
User: "OSS upload fails with EntityTooLarge when posting a 20KB image via PostObject to bucket img-bucket-prod."
Action: `python3 scripts/oss_transfer_error_diagnosis.py --error-code EntityTooLarge --http-status 400 --operation upload --bucket img-bucket-prod`
Answer: `STATUS: OK`; report verbatim that the Post Policy `content-length-range` caps the allowed body smaller than the file (real ticket case: 20 KB image rejected), plus the multipart/5 GB PutObject limit note and the troubleshooting steps from the diagnosis block.

**Example 2 - timeout (download, network track)**
User: "Downloads from bucket data-lake-cn keep failing with RequestTimeout."
Action: `python3 scripts/oss_transfer_error_diagnosis.py --error-code RequestTimeout --operation download --bucket data-lake-cn`
Answer: `STATUS: OK`; report the client-network root-cause directions, the isolation test from a same-region ECS, endpoint choice guidance, and the `network_optimization_suggestions` (transfer acceleration, multipart tuning) verbatim.

**Example 3 - HTTP status only (degraded)**
User: "My OSS upload returns HTTP 403."
Action: `python3 scripts/oss_transfer_error_diagnosis.py --http-status 403`
Answer: `STATUS: DEGRADED`; present the candidate codes (AccessDenied, SignatureDoesNotMatch, InvalidAccessKeyId, SecurityTokenExpired, ...) and ask for the exact `<Code>` field from the error response body before concluding.

<!-- production-pattern-example -->

**Example N - Download timeouts that are not an OSS fault**

> User: "Large downloads intermittently die with a timeout while small ones are fine; nothing shows in the OSS console."

```bash
python3 scripts/oss_transfer_error_diagnosis.py --error-code "RequestTimeout" --http-status "400" --operation "GetObject"
```

Map the code to its official cause, split client-link from service-side, and only then recommend acceleration for a cross-border path; a media decode error is not a storage fault.


## Available Scripts

| Script | Purpose |
| --- | --- |
| `scripts/oss_transfer_error_diagnosis.py` | Entry point: maps error code / HTTP status / client-term synonyms / symptom wording to root-cause directions and troubleshooting steps; out-of-domain guards refuse non-OSS product wording; prints structured JSON plus `STATUS`/`NEXT_ACTION`; optional `--question "<customer original wording>"` enables the symptom routing layer, the domain guards and the `doc_verification` block (official-doc verification, llms-index) |
| `scripts/_error_catalog.py` | Embedded official error-code catalog (Python constant, no data files) |
| `scripts/_doc_lookup.py` | Runtime official-doc verification module (llms-index leg + body leg, help.aliyun.com only, 3-day cache); imported by the entry script for `--question`, never blocks the diagnosis |
| `scripts/requirements.txt` | Dependency declaration: pure Python standard library only |

## Error Handling

| Script status | Exit code | Agent behavior |
| --- | --- | --- |
| `STATUS: OK` | 0 | Report diagnosis verbatim per the Final Answer Contract |
| `STATUS: DEGRADED` | 0 | Present candidates (status-only / ambiguous / wording-family / symptom lists), ask for the exact error code, do not conclude; an `ec_code_referral` block routes EC codes owned by sibling skills onward |
| `STATUS: FAIL` | 1 | Report `NEXT_ACTION` verbatim and request the full error response body; on `match.type: domain_guard` additionally confirm whether the failing request actually targets OSS; a `request_id_guidance` block adds the per-client-type recovery paths |

## Final Answer Contract

- Every conclusion in the final answer MUST come from the script output: root-cause directions, troubleshooting steps, category, side attribution, and doc references are transcribed verbatim.
- When the run carries a `doc_verification` block, the final answer MUST cite the official doc URLs from `doc_verification.docs`; if `doc_verification.note` starts with `DEGRADED`, the answer MUST explicitly state that online official-doc verification was unavailable.
- The Agent MUST NOT polish, re-rank, extrapolate, or invent beyond the script output; additions are limited to the user's own context (bucket, RequestId) and the boundary statement from Absolute Rule 5.
- Out-of-scope requests (DDoS sandbox, data recovery, refunds) end with the escalation wording from `references/scope-and-limitations.md`.
- **Delivery location:** the conclusion must be present in the final answer text itself - the error code, `diagnosis.category` and `side`, the root-cause directions, the troubleshooting steps, and every cited doc URL. Writing them into a file under `outputs/` or `ran_scripts/` does NOT count as answering; never end with only a one-line pointer to such a file.
- **MANDATORY pre-send self-check:** before sending, verify the final answer carries all of the items above; if any is missing, append it to the answer. File artifacts are optional extras, never a substitute.
