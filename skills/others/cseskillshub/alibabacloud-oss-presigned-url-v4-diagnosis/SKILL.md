---
name: alibabacloud-oss-presigned-url-v4-diagnosis
description: |
  Zero-cloud-API diagnosis of OSS presigned (share) URL failures and
  V1-to-V4 migration: parses a pasted URL, routes to causes (expired,
  clock skew, V1 signature forbidden, credential rotation, method
  mismatch, malformed x-oss-credential, SDK config misuse, proxy
  header tampering).
  Triggers: "share link expired", "SignatureDoesNotMatch on presigned
  URL", "V1 signature is forbidden", "x-oss-credential error", "signed
  URL stops working"; Chinese ticket wording routes via the embedded
  catalog keyword layer.
  Do NOT use for transfer error codes, billing, endpoints, traffic
  abuse / AK-leak, CDN back-to-origin or Referer hotlink configuration
  requests, or other OSS domains (backup / image processing /
  direct-access links / static hosting) — route to the matching
  alibabacloud-oss-* skill. A presigned-URL signature failure stays here
  even when a CDN or a proxy sits in front of the bucket.
---

# OSS Presigned URL Diagnosis & V4 Upgrade Guidance

Diagnose Alibaba Cloud OSS presigned (signed/share) URL failures and guide the V1-to-V4 signature migration: "our share link expired", "SignatureDoesNotMatch on presigned URL", "V1 signature is forbidden after upgrading the SDK", "x-oss-credential error in the URL", "the signed URL stops working after one day". Chinese ticket wording lands here too (eval fix PR-2): overnight-dead share links, signature-mismatch or tampered-link reports, persistent V4 signing failures, custom-domain signed-URL errors, make-the-link-permanent requests, proxy header-rewrite and SDK-config causes — the embedded catalog carries the Chinese keyword layer.

Core approach: parse the pasted presigned URL locally as a pure string (never send it anywhere; access keys and signatures are masked), detect the signature version (V1 `OSSAccessKeyId+Expires+Signature` vs V4 `x-oss-credential+x-oss-date+x-oss-expires+x-oss-signature`), extract and evaluate the expiry (V1 absolute epoch; V4 `x-oss-date + x-oss-expires`, max 604800 seconds = 7 days for a long-term AccessKey; STS temporary credentials cap at 43200 seconds = 12 hours), then route the reported error code / HTTP status / symptom / original question wording through the embedded failure-mode catalog to root-cause directions (expired, clock skew beyond +/-15 minutes, V1 signature forbidden, URL parameter tampering incl. proxy header rewriting, credential rotation or STS expiry, permission change after signing incl. AK network-policy / IP-allowlist restrictions, HTTP method mismatch, malformed signature parameters, SDK configuration misuse such as pathStyleAccess), and deliver the V4 upgrade compatibility checklist plus share-link recovery steps. This skill makes zero cloud API calls and performs no live network probing; all reasoning comes from the catalog distilled from official documentation and the presigned-URL support-ticket cluster (~130 tickets/month).

## Absolute Rules

1. **MANDATORY entry script:** All diagnosis MUST be performed by running `python3 scripts/oss_presigned_url_diagnosis.py` with the parameters gathered from the user. The Agent is forbidden from diagnosing by free-form reasoning alone or bypassing the script — the script embeds the URL parser, the expiry arithmetic, the failure-mode catalog, and the V4 upgrade checklist.
2. **ABSOLUTE PROHIBITION (no writes, no cloud calls, no probing):** Under **NO** circumstances may you invoke any mutating OSS operation, any aliyun CLI command, or any cloud API from this skill, and you MUST NOT fetch, curl, or otherwise probe the presigned URL over the network. The URL is analyzed purely as a string by the script. Do not read, print, or accept AK/SK/STS tokens; no credentials are needed at all. When the user pastes a URL, pass it to `--url` only; the script masks keys and signatures in its output.
3. **NO FABRICATION:** Every signature-version rule, expiry limit, failure mode, root-cause direction, and troubleshooting step MUST come from the script output (which reflects the embedded catalog sourced from official documentation). Never invent error codes, limits, or doc links. If the input matches no catalog entry, say so and ask for the presigned URL or the full error response body.
4. **EXECUTION RULE FOR ERRORS:** If the script exits with `STATUS: FAIL`, report the failure reason verbatim from `NEXT_ACTION` and ask the user for the missing input (the presigned URL itself and/or the full error body: Code, Message, RequestId). Never silently guess a diagnosis. On `STATUS: DEGRADED`, present the candidate failure modes in order and ask for the discriminating evidence before concluding.
5. **SCOPE BOUNDARY:** This skill only diagnoses presigned-URL failures and V1→V4 migration readiness. It does NOT teach signature-algorithm implementation, generate signed URLs, handle DDoS sandbox mitigation, deleted-data recovery, or commercial refunds — for such requests, state the boundary, point to the sibling skill listed in the description where applicable, and recommend a human support ticket.

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

- "share link expired"
- "SignatureDoesNotMatch on presigned URL"
- "V1 signature is forbidden"
- "x-oss-credential error"
- "signed URL stops working"

Chinese ticket wording routes here through the same catalog (eval fix
PR-2; the keyword layer itself is embedded in `scripts/_url_catalog.py`):

- overnight-dead share link, "the link stopped working" (expired family)
- signature mismatch, signature error, "the link was tampered" (tamper family)
- persistent v4 signing failure, "v4 unavailable here" (V4 signing failure)
- custom-domain signed-URL errors, designated-domain wording (custom domain)
- "make the download address permanent", long-term sharing (long-term access)
- proxy rewrote request headers, SDK pathStyleAccess misconfig (proxy / SDK config)
- sub-account lacks permission, signed link still fails (permission causes)

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| transfer error codes | `alibabacloud-oss-transfer-error-code-diagnosis` |
| billing | `alibabacloud-oss-billing-diagnosis` |
| endpoints | `alibabacloud-oss-endpoint-internal-diagnosis` |
| traffic abuse / AK-leak | `alibabacloud-oss-security-incident-forensics` |
| CDN back-to-origin / Referer hotlink configuration requests (a presigned-URL signature failure behind a CDN stays here) | `alibabacloud-oss-cdn-origin-config-diagnosis` |
| backup integration | `alibabacloud-oss-backup-integration-diagnosis` |
| image processing | `alibabacloud-oss-image-processing-diagnosis` |
| direct-access links | `alibabacloud-oss-direct-access-link-diagnosis` |
| static hosting | `alibabacloud-oss-static-website-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

## Execution Principle

Run the entry script once with all known parameters; read the structured JSON it prints, then compose the answer strictly from it. The matching ladder is deterministic: parsed URL with a definitive expiry/malformed verdict (`STATUS: OK`) → error-code/status/symptom candidate modes (`STATUS: DEGRADED`) → no recognizable input (`STATUS: FAIL`). Do not re-implement the parsing, expiry arithmetic, or the catalog in chat; the pure functions live in the script and are covered by its inline assertions.

## Observability

The entry script generates per run, even though this skill makes zero cloud API calls:
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) created once per run and embedded in the output JSON.
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-presigned-url-v4-diagnosis`; the assembled string is emitted in the `user_agent` field so any future HTTP usage would be traceable.

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

This skill makes zero cloud API calls and needs NO credentials at all: it never reads, writes, asks for, or accepts AK/SK/STS tokens, and never prompts the user for any credential. All inputs are the user-supplied URL/error details, processed entirely offline with keys and signatures masked in the output. If a user volunteers credentials, refuse them and continue with the URL/error details only.

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

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` / `NEXT_ACTION` output tell you what to ask for next.
2. Run `scripts/oss_presigned_url_diagnosis.py` and read `status`, `candidate_modes`/`failure_modes`, `url_analysis` and `next_action`.
3. Interpret through the modules below: the failure catalog routes the symptom, the RAM module declares the permission posture, and the advisory FAQ answers consult-style questions (safety / trade-off / where-to-configure).
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then the declaration of inputs actually provided.

## Input Parameters

All parameters are optional; auto-fill from the user's message when present and never block on missing ones — run the script with what is known and let `STATUS`/`NEXT_ACTION` drive follow-up questions. Provide at least one parameter.

| Parameter | Meaning | Auto-fill source |
| --- | --- | --- |
| `--url` | The presigned URL itself, analyzed locally as a string (never sent over the network) | any pasted OSS URL with signature parameters |
| `--error-code` | OSS error code from the response body (`<Code>`), fuzzy matching allowed | quoted error text, e.g. `SignatureDoesNotMatch`, `RequestTimeTooSkewed` |
| `--http-status` | HTTP status such as 400/403/404 | "HTTP 403 error", "got a 400" |
| `--symptom` | Free-text symptom description | "share link expired", "V1 signature is forbidden" |
| `--question` | Customer's original question wording; participates in symptom routing exactly like `--symptom` (eval fix PR-5) AND enables the official-doc verification leg (`doc_verification` section) | the customer's own sentence, passed verbatim |

## Module Index

| Reference | Purpose |
| --- | --- |
| `references/presigned-url-failure-catalog.md` | Signature URL forms, failure-mode catalog, and error routing with official documentation sources |
| `references/v4-upgrade-checklist.md` | V4 upgrade compatibility checklist and the official V1 retirement policy |
| `references/scope-and-limitations.md` | Out-of-scope topics and the human-escalation wording |
| `references/ram-policies.md` | RAM/permission posture declaration for this zero-cloud-API skill |
| `references/faq-advisory.md` | Advisory FAQ from real tickets: OSSAccessKeyId safety verdict, private-vs-hotlink trade-off, SSL-certificate renewal path |

## Diagnostic Flow

1. **Collect** whatever the user provides: the presigned URL, error code, HTTP status, symptom text. Auto-fill the parameters; do not demand everything up front.
2. **Run** `python3 scripts/oss_presigned_url_diagnosis.py [--url <presigned-url>] [--error-code <code>] [--http-status <n>] [--symptom <text>] [--question "<customer wording>"]`.
3. **Interpret** the JSON: `url_analysis` gives the signature version, credential-scope check, and the expiry verdict (`expiry_state`); `candidate_modes` and `failure_modes` carry the routed root-cause directions and troubleshooting steps verbatim; `v4_upgrade_checklist` and `link_recovery_guidance` accompany every routed diagnosis.
4. **Follow up** per `NEXT_ACTION`: on `DEGRADED`, ask for the discriminating evidence (URL or full error body) before concluding; on `FAIL`, request the presigned URL or the full error response body.
5. **Report** following the Final Answer Contract below.

## Important Notes

- Signature-URL forms, the maximum validity (604800 seconds = 7 days for a long-term AccessKey; 43200 seconds = 12 hours for an STS temporary credential), the `x-oss-credential` scope format, and the V1 retirement policy follow the official Alibaba Cloud OSS documentation (see `scripts/_url_catalog.py` header for the exact source URLs, verified 2026-08).
- OSS allows at most +/-15 minutes (900 seconds) clock skew; exceeding it yields `RequestTimeTooSkewed` (EC 0002-00000504). An empty or missing `x-oss-expires` in a V4 URL yields the official error 0002-00000216.
- A wrong region in the V4 credential scope typically surfaces as `AuthorizationHeaderMalformed`, not `SignatureDoesNotMatch`.
- Presigned URLs do NOT bypass Bucket Policy, and they inherit the signer's permissions: permission revocation or policy changes break previously issued links.
- The script performs no DNS lookups, no TCP connections, and no API calls; it is safe to run in restricted environments.

## Examples

**Example 1 — expired share link (definitive)**
User: "Our customer says the share link stopped working; here it is: https://docs-bucket.oss-cn-hangzhou.aliyuncs.com/report.pdf?OSSAccessKeyId=LTAI5tXXXX&Expires=1600000000&Signature=abc%3D"
Action: `python3 scripts/oss_presigned_url_diagnosis.py --url "<that URL>"`
Answer: `STATUS: OK`; report verbatim that the V1 `Expires` epoch is in the past, the URL is expired, and transcribe the `expired` failure mode plus the link recovery guidance (regenerate with sufficient TTL, max 7 days).

**Example 2 — SignatureDoesNotMatch on a presigned URL (degraded)**
User: "Uploading with the presigned URL returns 403 SignatureDoesNotMatch."
Action: `python3 scripts/oss_presigned_url_diagnosis.py --error-code SignatureDoesNotMatch --http-status 403 --symptom "presigned URL upload"`
Answer: `STATUS: DEGRADED`; present the candidate modes (parameter tampering, credential rotation, method mismatch, V1 forbidden) in order and ask for the URL itself or the full error body before concluding.

**Example 3 — V4 URL with x-oss-credential problem (definitive malformed)**
User: "x-oss-credential error when opening our V4 share URL."
Action: `python3 scripts/oss_presigned_url_diagnosis.py --url "<V4 URL with malformed credential or empty x-oss-expires>"`
Answer: `STATUS: OK`; report the malformed-parameter verdict verbatim (credential-scope format / empty x-oss-expires = official error 0002-00000216) and the V4 upgrade checklist if the user is migrating from V1.

<!-- production-pattern-example -->

**Example N — A shared link expires instantly or is refused as V1**

> User: "Links generated by ossbrowser work at first, then fail with SignatureDoesNotMatch; the SDK says V1 signature is forbidden."

```bash
python3 scripts/oss_presigned_url_diagnosis.py --error-code "SignatureDoesNotMatch" --symptom "shared link expired"
```

Report the signature version, the validity ceiling for the credential type used, and whether the expiry is expected; keep the secret and signature values out of the answer.


## Available Scripts

| Script | Purpose |
| --- | --- |
| `scripts/oss_presigned_url_diagnosis.py` | Entry point: parses the presigned URL locally, routes error/status/symptom to failure modes; prints structured JSON plus `STATUS`/`NEXT_ACTION` |
| `scripts/_url_catalog.py` | Embedded failure-mode catalog, signature-form table, V4 upgrade checklist (Python constants, no data files) |
| `scripts/_doc_lookup.py` | Official-doc verification leg: help.aliyun.com llms-index lookup + cached index + .md body excerpts (stdlib only, zero credentials, never blocks the diagnosis) |
| `scripts/requirements.txt` | Dependency declaration: pure Python standard library only |

## Error Handling

| Script status | Exit code | Agent behavior |
| --- | --- | --- |
| `STATUS: OK` | 0 | Report the confirmed failure mode verbatim per the Final Answer Contract |
| `STATUS: DEGRADED` | 0 | Present candidate modes in order, ask for the discriminating evidence, do not conclude |
| `STATUS: FAIL` | 1 | Report `NEXT_ACTION` verbatim and request the presigned URL or the full error response body |

## Final Answer Contract

- Every conclusion in the final answer MUST come from the script output: signature version, expiry verdict, failure modes, root-cause directions, troubleshooting steps, V4 upgrade checklist, and doc references are transcribed verbatim.
- **MANDATORY DOC-REFERENCE LINE:** every final answer that reports the script's diagnosis MUST contain one line starting with `Official docs (doc_verification):` followed by the doc URLs verbatim — from `doc_verification.docs[].url` when present, otherwise from the routed `failure_modes[].official_doc_ref` — and, when `doc_verification.note` starts with DEGRADED, the offline-degradation sentence right after those URLs. Before presenting, verify that line exists; if it is missing you MUST append it. Never present a diagnosis without it, and never invent a URL for it: on a planning-only request where the script was not run, omit the line.
- The Agent MUST NOT polish, re-rank, extrapolate, or invent beyond the script output; additions are limited to the user's own context (their URL with keys masked, RequestId) and the boundary statement from Absolute Rule 5.
- Out-of-scope requests (URL generation, algorithm teaching, data recovery, refunds) end with the escalation wording from `references/scope-and-limitations.md`.
