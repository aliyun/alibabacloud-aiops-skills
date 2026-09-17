---
name: alibabacloud-oss-client-tools-diagnosis
description: |
  Read-only diagnosis of OSS client tool failures. Use when the customer reports an
  ossbrowser login failure or 403, an ossutil error such as InvalidAccessKeyId,
  AccessDenied, a missing or expired STS token, a connect timeout while uploading
  files, or a RequestTimeTooSkewed clock skew, when a client cannot connect to OSS,
  or when the customer asks which ossbrowser or ossutil version to standardize on.
  Also use for a troubleshooting plan or information checklist. Triggers: "ossbrowser
  login failed", "ossbrowser 403", "ossutil AccessDenied", "ossutil InvalidAccessKeyId",
  "client cannot connect to OSS", "RequestTimeTooSkewed", "SecurityTokenExpired",
  "SigningContext.Credentials", "region must be set in sign version 4", "The Security
  Token may be lost". Answers only; runs no client commands, calls no cloud API. Do
  NOT use for SDK/API errors not naming ossbrowser or ossutil, endpoint selection,
  presigned URL, billing, or throttling (503/SlowDown).
---

# OSS Client Tools Diagnosis

Diagnose Alibaba Cloud OSS client-tool problems: "ossbrowser login failed with AccessDenied", "ossutil reports InvalidAccessKeyId / The Security Token may be lost", "ossutil says region must be set in sign version 4", "uploads keep failing with RequestTimeTooSkewed", "client cannot connect to OSS although the AccessKey is fine", "which version of ossbrowser or ossutil should I use".

Core approach: take the customer-reported tool, error text / EC code / symptom, map it through the embedded client-tool catalog to a root-cause direction (login & authentication, permission & least privilege, credential & signature, tool configuration, connectivity, or version selection), and deliver verbatim troubleshooting steps plus the ossutil config template and the least-privilege RAM policy template where relevant. This skill makes zero cloud API calls, performs no network probing, and never executes any ossutil/ossbrowser command on the user's behalf; all reasoning comes from the catalog distilled from official documentation and ticket root-cause clusters.

## Trigger Conditions

Route here when the user reports any of: ossbrowser login failure or 403 after login; ossutil errors (InvalidAccessKeyId, AccessDenied, "The Security Token may be lost", SecurityTokenExpired, SigningContext.Credentials is null or empty, "region must be set" in sign version 4, connect timeout); client cannot connect to OSS although the AccessKey is fine; RequestTimeTooSkewed clock errors; a version-choice question about ossbrowser/ossutil; or asks for a troubleshooting plan or investigation outline for any of these issues.

## User Confirmation

This skill makes zero cloud API calls, so there are no cloud resources to confirm before running the entry script — no bucket ownership, UID, or credential confirmation is needed. The only collection required is the tool name (ossbrowser / ossutil) and the verbatim error text / EC code; ask for those when missing, then run the diagnosis directly.

## Absolute Rules

1. **MANDATORY entry script:** All diagnosis MUST be performed by running `python3 scripts/oss_client_tools_diagnosis.py` with the parameters gathered from the user. The Agent is forbidden from diagnosing by free-form reasoning alone or bypassing the script — the script embeds the catalog, the EC decision table, and the matching ladder.
2. **ABSOLUTE PROHIBITION (no execution, no writes, no cloud calls):** Under **NO** circumstance may you execute any ossutil or ossbrowser command, run any aliyun CLI command, or call any cloud API from this skill. You only OUTPUT commands/templates for the user to run themselves. This skill is knowledge-driven and read-only by design: it never probes the network and never touches buckets or objects. Do not read, print, or accept AK/SK/STS tokens; no credentials are needed at all.
3. **NO FABRICATION:** Every error text, EC interpretation, root-cause direction, template, and doc reference MUST come from the script output (which reflects the embedded catalog). Never invent error codes, config fields, or doc links. If the input matches no catalog entry, say so and ask for the complete error message.
4. **EXECUTION RULE FOR ERRORS:** If the script exits with `STATUS: FAIL`, report the failure reason verbatim from `NEXT_ACTION` and ask the user for the missing input (tool + complete error message including EC code). Never silently guess a diagnosis. On `STATUS: DEGRADED`, present the candidate list and ask for the exact error text before concluding.
5. **SCOPE BOUNDARY:** This skill only diagnoses ossbrowser/ossutil client-side failures and outputs guidance. It does NOT handle API/SDK-level transfer error codes, endpoint-selection strategy, presigned URLs, billing disputes, or data recovery — for such requests, state the boundary, point to the sibling skill listed in the description, and recommend a human support ticket when needed.
6. **EMPTY / NOT-FOUND IS A VALID RESULT — NEVER REACT WITH A WRITE.** If the script returns `STATUS: FAIL` or `STATUS: DEGRADED`, or the error matches no catalog entry, that is a normal and complete conclusion: report the status verbatim and ask for more information. Never attempt to verify, test, create, re-create, or repair any cloud resource. Never fall back to running `aliyun` CLI commands, `curl`, or any other cloud interaction. Stay within the entry script's read-only flow at all times.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Execution Principle

Run the entry script once with all known parameters; read the structured JSON it prints, then compose the answer strictly from it. The matching ladder is deterministic: exact alias hit (`STATUS: OK`) → symptom match / fuzzy match / tool-only candidates (`STATUS: OK` for unique symptom hits, otherwise `DEGRADED`) → no recognizable input (`STATUS: FAIL`). Do not re-implement the matching or the catalog in chat; the pure matching functions live in the script and are covered by its inline assertions.

## Observability

The entry script generates per run, even though this skill makes zero cloud API calls:
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) created once per run and embedded in the output JSON.
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-client-tools-diagnosis`; the assembled string is emitted in the `user_agent` field so any future HTTP usage would be traceable.

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

This skill makes zero cloud API calls and needs NO credentials at all: it never reads, writes, asks for, or accepts AK/SK/STS tokens, and never prompts the user for any credential. All inputs are the user-supplied tool name, error text, EC code, symptom, endpoint, and version — all non-sensitive strings. The embedded ossutil config template contains placeholders only. If a user volunteers credentials, refuse them and continue with the error details only.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/oss_client_tools_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

## Input Parameters

All parameters are optional; auto-fill from the user's message when present and never block on missing ones — run the script with what is known and let `STATUS`/`NEXT_ACTION` drive follow-up questions.

| Parameter | Meaning | Auto-fill source |
| --- | --- | --- |
| `--tool` | Client tool: `ossbrowser` or `ossutil` (variants like `ossbrowser2`, `ossutil64`, `ob2` accepted) | "ossbrowser 2.0 login failed" → ossbrowser |
| `--error-code` | Error text from the tool dialog/stderr (fuzzy OK) | `AccessDenied`, `InvalidAccessKeyId`, `RequestTimeTooSkewed` |
| `--ec-code` | EC code from the error body, e.g. `0003-00000101` | `EC: 0003-00000101` in ossutil output |
| `--symptom` | Free-text symptom | "login failed", "cannot connect" |
| `--endpoint` | Endpoint in use, echoed for region-mismatch context | endpoint quoted by the user |
| `--client-version` | Tool version, e.g. ossbrowser 2.1.1 / ossutil 2.x | version mentioned by the user |

## Module Index

| Reference | Purpose |
| --- | --- |
| `references/tool-troubleshooting.md` | Full client-tool catalog with official documentation sources and ticket-derived criteria |
| `references/config-templates.md` | ossutil config template and least-privilege RAM policy template |
| `references/scope-and-limitations.md` | Out-of-scope topics and the human-escalation wording |
| `references/ram-policies.md` | RAM/permission posture declaration for this zero-cloud-API skill |

## Diagnostic Flow

1. **Collect** whatever the user provides: tool name + version, error text, EC code, symptom, endpoint. Auto-fill the parameters; do not demand everything up front.
2. **Run** `python3 scripts/oss_client_tools_diagnosis.py --tool <t> [--error-code <c>] [--ec-code <ec>] [--symptom <s>] [--endpoint <e>] [--client-version <v>]`.
3. **Interpret** the JSON: `diagnosis.category` gives the root-cause track; `root_cause_directions` and `troubleshooting_steps` are reported verbatim; `ec_interpretation` appears when an EC code matches the decision table; `ossutil_config_template` / `least_privilege_policy_template` appear for credential / permission tracks.
4. **Follow up** per `NEXT_ACTION`: on `DEGRADED`, ask for the exact error text to disambiguate candidates; on `FAIL`, request the tool name and the complete error message.
5. **Report** following the Final Answer Contract below; commands and templates are OUTPUT for the user to run, never executed by the Agent.

## Important Notes

- Error semantics follow the official Alibaba Cloud OSS documentation (ossbrowser FAQ, ossutil config/options/2.0-new-features docs, HTTP 403 error-code reference); root-cause criteria are distilled from ticket clusters (ossbrowser 81, ossutil error/connection 253, login failure 35, STS 16, clock skew 4 in the July export).
- ossbrowser 2.x requires bucket-level `oss:GetBucketInfo` at login — directory-scoped policies that worked on 1.x fail on 2.x; this is the top login-failure cluster.
- EC codes steer ossutil AccessDenied: 0003-00000001 = the AccessKey ID/signature is incorrect OR the identity behind the credential lacks permission on the Bucket/Object (check AK/SK first, then authorization — it is NOT merely a platform-side security policy); 0003-00000101 = customer Bucket Policy; 0003-00000301 = STS session-policy intersection.
- The script performs no DNS lookups, no TCP connections, no API calls, and executes no client commands; it is safe to run in restricted environments.

## Examples

**Example 1 — ossbrowser 2.x login denied (permission track)**
User: "ossbrowser 2.1.1 login failed with AccessDenied: The bucket you access does not belong to you; my RAM policy only allows my directory."
Action: `python3 scripts/oss_client_tools_diagnosis.py --tool ossbrowser --error-code AccessDenied --symptom "login failed, The bucket you access does not belong to you" --client-version 2.1.1`
Answer: `STATUS: OK`; report verbatim that ossbrowser 2.x calls bucket-level GetBucketInfo at login, the directory-scoped policy does not cover it, plus the least-privilege policy template.

**Example 2 — ossutil AccessDenied with EC code (permission track)**
User: "ossutil AccessDenied with EC 0003-00000301 although our role has AliyunOSSFullAccess; we access via STS."
Action: `python3 scripts/oss_client_tools_diagnosis.py --tool ossutil --error-code AccessDenied --ec-code 0003-00000301`
Answer: `STATUS: OK`; report the EC decision-table interpretation: effective permission = role permissions ∩ AssumeRole session Policy; the missing action must be added to the session Policy.

**Example 3 — clock skew (credential track)**
User: "Uploads intermittently fail with RequestTimeTooSkewed from a container host."
Action: `python3 scripts/oss_client_tools_diagnosis.py --error-code RequestTimeTooSkewed --symptom "uploads intermittently fail"`
Answer: `STATUS: OK`; report the 15-minute skew limit, NTP synchronization steps, and the ossutil 2.x auto-correction note.

**Example 4 — tool only known (degraded)**
User: "ossutil is throwing an error, no idea what it says."
Action: `python3 scripts/oss_client_tools_diagnosis.py --tool ossutil`
Answer: `STATUS: DEGRADED`; present the common ossutil issue list and ask for the complete error message including any EC code.

<!-- production-pattern-example -->

**Example N — ossbrowser login fails with AccessDenied and an EC number**

> User: "ossbrowser 2.0 says AccessDenied with EC 0003-00000202 right after I pasted a valid AccessKey."

```bash
python3 scripts/oss_client_tools_diagnosis.py --tool "ossbrowser" --error-code "AccessDenied" --ec-code "0003-00000202"
```

Route by the EC: name the exact policy gap or the account-scope problem instead of a generic permission hint, and state the minimum read-only actions the tool needs.


## Available Scripts

| Script | Purpose |
| --- | --- |
| `scripts/oss_client_tools_diagnosis.py` | Entry point: maps tool / error / EC code / symptom to root-cause directions, templates, and troubleshooting steps; prints structured JSON plus `STATUS`/`NEXT_ACTION` |
| `scripts/_tools_catalog.py` | Embedded client-tool catalog, config template, and least-privilege policy template (Python constants, no data files) |
| `scripts/requirements.txt` | Dependency declaration: pure Python standard library only |

## Error Handling

| Script status | Exit code | Agent behavior |
| --- | --- | --- |
| `STATUS: OK` | 0 | Report diagnosis verbatim per the Final Answer Contract |
| `STATUS: DEGRADED` | 0 | Present candidates, ask for the exact error text, do not conclude |
| `STATUS: FAIL` | 1 | Report `NEXT_ACTION` verbatim and request tool + complete error message |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
## Final Answer Contract

- Every conclusion in the final answer MUST come from the script output: root-cause directions, troubleshooting steps, EC interpretations, templates, category, and doc references are transcribed verbatim.
- The Agent MUST NOT polish, re-rank, extrapolate, or invent beyond the script output; additions are limited to the user's own context (bucket, endpoint, version) and the boundary statement from Absolute Rule 5.
- Commands and templates are presented for the user to execute locally; the Agent never runs them. Out-of-scope requests end with the escalation wording from `references/scope-and-limitations.md`.
1. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."

