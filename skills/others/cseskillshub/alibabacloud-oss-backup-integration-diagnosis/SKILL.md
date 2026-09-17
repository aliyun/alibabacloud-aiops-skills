---
name: alibabacloud-oss-backup-integration-diagnosis
description: |
  Zero-cloud-API diagnosis of Alibaba Cloud OSS integration problems for third-party backup software (Veeam, Synology NAS, Rclone, generic S3 clients):
  S3 compatible interface checks (endpoint form, path-style), V1-signature-forbidden routing to V4,
  retrieval-fee attribution for IA/Archive backup buckets, whitelist (jia-bai) request guidance.
  Configuration advice only; never executes changes.
  Do NOT use for: upload/download error codes (use alibabacloud-oss-transfer-error-code-diagnosis),
  billing line-items (use alibabacloud-oss-billing-diagnosis),
  lifecycle rules (use alibabacloud-oss-lifecycle-runtime-diagnosis),
  presigned URLs (use alibabacloud-oss-presigned-url-v4-diagnosis).
  Triggers: "Veeam backup to OSS", "Synology backup OSS", "rclone sync OSS",
  "S3 compatible interface", "high retrieval fee from backup", "V1 signature forbidden on backup tool".
  Invoke immediately on any trigger; the entry script collects missing inputs via its
  "Inputs still missing" report instead of interviewing the user first.
---

# OSS Backup & Third-Party Tool Integration Diagnosis

Diagnose backup-software integration problems with Alibaba Cloud OSS: "Veeam backup to OSS keeps failing validation", "Synology backup OSS reports V1 signature is forbidden", "rclone sync over the S3 compatible interface deleted my files", "high retrieval fee from backup on an Infrequent Access bucket", "how do I get the Veeam whitelist for my bucket".

Core approach: take the customer-reported tool / error message / symptom / storage class, match it through the embedded tool x symptom attribution catalog to a root-cause direction (signature adaptation, endpoint form, request style, permission mapping, whitelist provisioning, retrieval-fee attribution, or tool usage), and deliver verbatim configuration advice. This skill makes zero cloud API calls and performs no live network probing; all reasoning comes from the catalog distilled from official OSS documentation (S3 compatibility, V1->V4 upgrade, retrieval billing) and 170 matched real support tickets.

## Trigger Conditions

Route here when the user reports any of: Veeam backup to OSS fails validation or asks for the Veeam whitelist; Synology / NAS backup reports V1 signature forbidden; rclone or AWS CLI sync over the S3 compatible interface fails or behaves unexpectedly; a backup workload on Infrequent Access / Archive storage triggers a high retrieval fee; or any third-party backup tool integration error against OSS.

## User Confirmation

This skill makes zero cloud API calls, so there are no cloud resources to confirm before running the entry script — no bucket ownership, UID, or credential confirmation is needed. The only collection required is the tool name/version and the verbatim error text (plus symptom or storage class when relevant); take everything available from the user's message and run the diagnosis directly, declaring what is still unknown instead of asking up front (see Information Completeness).

## Information Completeness

1. **Auto-fill first, ask second — never block.** Derive every parameter you can from the user's own message (tool name, verbatim error text, symptom, storage class, bucket, region) and run the entry script immediately. Do NOT ask a clarifying question before the first run, and do not demand a complete parameter set; one extra round of questions is acceptable only when the script returns `STATUS: FAIL`.
2. **Declare the gap in the answer, not in a lookup.** The final answer MUST carry one explicit line naming every input still unknown (for example: storage class of the billed objects, bucket name, tool version) and what each unknown would change in the conclusion. An unknown is stated as an unknown; it is never silently defaulted and never resolved by touching the cloud (see Absolute Rule 2).
3. **Declare the source of every fact.** Each fee attribution, endpoint form, signature rule and doc reference in the final answer MUST be traceable to the script output — cite the `doc_verification.docs` titles/URLs and, when `doc_verification.note` starts with `DEGRADED`, state plainly that online doc verification was unavailable.

## Absolute Rules

1. **MANDATORY entry script:** All diagnosis MUST be performed by running `python3 scripts/oss_backup_integration_diagnosis.py` with the parameters gathered from the user. The Agent is forbidden from diagnosing by free-form reasoning alone or bypassing the script — the script embeds the integration catalog, the matching ladder, and the ticket-based judgment criteria. **STRICTLY FORBIDDEN** as substitutes: hand-writing bash/Python to fetch or transform data, calling any helper script directly instead of the entry script, or "gathering a bit more context" first. If the entry script errors or a result looks incomplete, DO NOT attempt a manual workaround — re-run the entry script with an extra parameter, or report the gap. Any deviation from the entry script is a hard failure of this skill.
2. **ABSOLUTE PROHIBITION (zero cloud calls, no writes, no execution):** Under **NO** circumstances may this skill run **any** `aliyun` CLI command or **any** cloud OpenAPI — not even a read-only one. Explicitly banned, with no exceptions: billing/pricing/quota lookups (`bssopenapi QueryBill`, `DescribeInstanceBill`, `QueryBillOverview`, `GetPayAsYouGoPrice`, `GetSubscriptionPrice`, `QueryResourcePackageInstances`, `QueryAvailableInstances`), identity or profile probing (`sts GetCallerIdentity`, `aliyun configure list`, `aliyun configure get`), OSS `Get*`/`List*`, and fetching or scraping pricing pages to convert currencies into an estimate. The entry script above is the ONLY sanctioned command. Never run rclone/AWS CLI/backup tools against the user's bucket; never claim a whitelist has been opened. A bucket name, region or account UID supplied by the user is **context text only** — it is never a lookup key, and a missing parameter is never a reason to query the cloud. This skill is knowledge-driven and advice-only: it gives configuration advice and NEVER executes changes. Do not read, print, or accept AK/SK/STS tokens; no credentials are needed at all.
3. **NO FABRICATION:** Every endpoint form, signature rule, fee rule, and whitelist procedure MUST come from the script output (which reflects the embedded official-doc catalog and ticket clustering). Never invent API names, version numbers, or doc links. This skill reports fee **attribution mechanics** (which billing item is triggered, by which storage class, over which minimum duration) and never reports prices: no unit price, no monthly amount, no total-cost figure, no resource-package size or purchase recommendation, and no currency-converted estimate. Exact prices belong to the user's own console bill and the official pricing page — point there. If the input matches no catalog entry, say so and ask for the tool name/version plus the exact error message.
4. **EXECUTION RULE FOR ERRORS:** If the script exits with `STATUS: FAIL`, report the failure reason verbatim from `NEXT_ACTION` and ask the user for the missing input (tool name/version, exact error message, symptom, storage class). Never silently guess a diagnosis. On `STATUS: DEGRADED`, present the candidates and ask for the missing discriminator before concluding.
5. **SCOPE BOUNDARY:** This skill only diagnoses backup-tool integration and retrieval-fee attribution and gives configuration advice. It does NOT execute whitelist provisioning, change storage classes/lifecycle/RAM, perform restores, or handle billing refunds — for such requests, state the boundary, point to the sibling skill listed in the description where applicable, and recommend a human support ticket.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Execution Principle

Run the entry script once with all known parameters; read the structured JSON it prints, then compose the answer strictly from it. The matching ladder is deterministic: error-message routing → tool catalog → symptom routing (retrieval fee attaches the storage-class judgment) → storage-class-only profile → `FAIL`. Exact catalog hits give `STATUS: OK`, fuzzy/partial input gives `STATUS: DEGRADED`. Do not re-implement the matching or the catalog in chat; the pure matching functions live in the script and are covered by its inline assertions.

## Observability

The entry script generates per run, even though this skill makes zero cloud API calls:
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) created once per run and embedded in the output JSON.
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-backup-integration-diagnosis`; the assembled string is emitted in the `user_agent` field so any future HTTP usage would be traceable.

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

This skill makes zero cloud API calls and needs NO credentials at all: it never reads, writes, asks for, or accepts AK/SK/STS tokens, and never prompts the user for any credential. All inputs are user-supplied integration details (tool, error message, symptom, storage class, bucket, region), processed entirely offline. If a user volunteers credentials, refuse them and continue with the integration details only.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs from the user's own message. Never guess a bucket or region and never enumerate resources with credentials: fill what is known, declare what is missing (see Information Completeness), and let the script's `STATUS`/`NEXT_ACTION` drive any follow-up.
2. Run `scripts/oss_backup_integration_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

## Input Parameters

All parameters are optional; auto-fill from the user's message when present and never block on missing ones — run the script with what is known and let `STATUS`/`NEXT_ACTION` drive follow-up questions.

| Parameter | Meaning | Auto-fill source |
| --- | --- | --- |
| `--tool` | Backup tool: `veeam`, `synology`, `generic` (rclone/AWS CLI/SDK/s3cmd...), or the raw name | "Veeam Backup & Replication" → veeam, "Synology NAS / DSM" → synology, "rclone / AWS CLI" → generic |
| `--error-code` | Exact error message from the tool | quoted error, e.g. `V1 signature is forbidden`, `HeadBucket 403` |
| `--symptom` | Free-form symptom | "high retrieval fee" → retrieval, "whitelist / jia-bai" → whitelist, "path style" → style |
| `--storage-class` | `standard` / `ia` / `archive` / `coldarchive` / `deepcoldarchive` | bucket or billing context |
| `--bucket` | Bucket name for context (never validated remotely) | bucket mentioned by the user |
| `--region` | Region for context, e.g. `cn-shanghai` | region mentioned by the user |

## Module Index

| Reference | Purpose |
| --- | --- |
| `references/integration-playbook.md` | Five-track playbook: connection checklist / Veeam / V1->V4 adaptation / retrieval fees / escalation wording |
| `references/s3-compat-notes.md` | OSS S3 compatibility scope: endpoint forms, virtual-hosted style, API set, HeadBucket mapping, ETag/Restore differences |
| `references/retrieval-fee-guide.md` | Retrieval and minimum-duration fee judgment table by storage class, plus backup-workload fee generators |
| `references/ram-policies.md` | RAM/permission posture declaration for this zero-cloud-API, advice-only skill |

## Diagnostic Flow

1. **Collect** whatever the user provides: tool name/version, error message, symptom, storage class, bucket, region. Auto-fill the parameters; do not demand everything up front.
2. **Run** `python3 scripts/oss_backup_integration_diagnosis.py --tool <t> [--error-code <msg>] [--symptom <s>] [--storage-class <cls>] [--bucket <b>] [--region <r>]`.
3. **Interpret** the JSON: `match.type` tells which ladder rung hit; `diagnosis.category` gives the attribution track; `root_cause_directions` / `configuration_advice` / `known_issues` / `judgment` are reported verbatim; `retrieval_judgment` appears when a storage class is attached to a tool diagnosis; `tool_context` appears when a tool accompanies an error route.
4. **Follow up** per `NEXT_ACTION`: on `DEGRADED`, ask for the exact discriminator (error text / storage class); on `FAIL`, request tool name/version and the full error message.
5. **Report** following the Final Answer Contract below.

## Important Notes

- OSS accepts only the virtual-hosted request style and S3-compatible endpoints of the form `https://s3.oss-{region}.aliyuncs.com`; path-style URLs are rejected (official S3-compatibility doc).
- `V1 signature is forbidden` means the tool still signs with V1 while OSS phases V1 out; upgrading the tool version alone is NOT enough — V4 must be explicitly enabled and the bucket region ID configured (ticket-verified root cause).
- S3 `HeadBucket` maps to OSS `GetBucketInfo` for authorization purposes; a 403 on HeadBucket with otherwise working access usually misses `oss:GetBucketInfo` (ticket-verified).
- Retrieval fees are pay-as-you-go only (no resource package deducts them); IA objects younger than 30 days (Archive 60 / ColdArchive & DeepColdArchive 180) that get overwritten or deleted by backup rotation bill the remaining days (official billing docs).
- The Veeam compatibility whitelist is provisioned manually by the Alibaba Cloud backend via support ticket (UID + bucket + region + tool version); this skill produces the request guidance but never performs the provisioning.
- The script performs no DNS lookups, no TCP connections, and no API calls; it is safe to run in restricted environments.

## Examples

**Example 1 — Veeam whitelist request (real ticket form)**
User: "Veeam backup to OSS: bucket stt-backup-shanghai in cn-shanghai (East China 2) needs the compatibility whitelist, backup jobs cannot write, UID 1552974654746705."
Action: `python3 scripts/oss_backup_integration_diagnosis.py --tool veeam --symptom whitelist --bucket stt-backup-shanghai --region cn-shanghai`
Answer: `STATUS: OK`; report the Veeam checklist (S3 endpoint form, virtual-hosted style, V4 signature) and the whitelist provisioning guidance verbatim (support ticket with UID/bucket/region/Veeam version); state clearly the skill cannot open the whitelist itself.

**Example 2 — V1 signature forbidden routing**
User: "Our third-party backup tool reports 'V1 signature is forbidden' when connecting to OSS, and the SDK was already upgraded."
Action: `python3 scripts/oss_backup_integration_diagnosis.py --error-code "V1 signature is forbidden"`
Answer: `STATUS: OK`; report verbatim that upgrading alone is insufficient: explicitly enable V4 (Java SignVersion.V4 / Python ProviderAuthV4 / Go AuthV4), configure the bucket region ID, and check the minimum V4-capable version table.

**Example 3 — retrieval fee without storage class (degraded)**
User: "Our backups produced a high retrieval fee this month."
Action: `python3 scripts/oss_backup_integration_diagnosis.py --symptom "high retrieval fee from backup"`
Answer: `STATUS: DEGRADED`; present the storage-class candidates and ask which class the billed objects use before attributing the fee.

**Example 4 — "how much will it cost / which package should I buy" (prices are out of scope)**
User: "Which resource packages should I buy to cover my daily OSS backup billing? My account UID is <your-uid>."
Action: `python3 scripts/oss_backup_integration_diagnosis.py --symptom "high retrieval fee from backup" --question "<user's original wording>"`
Answer: relay the script's fee attribution mechanics (which billing item each storage class triggers, minimum-duration top-up, and that data retrieval is pay-as-you-go with no resource package covering it) plus the cited `doc_verification.docs` URLs; then `Inputs still missing: storage class, bucket, region` and the prices-out-of-scope statement. Never run a billing or pricing API, never write a script to fetch prices, and never quote a unit price, a monthly amount or a package size — the user's own console bill and the official OSS pricing page are the only sources for numbers, and package purchase goes to a human support ticket.

<!-- production-pattern-example -->

**Example N — Veeam reports InvalidLocationConstraint against an OSS bucket**

> User: "Our Veeam job to OSS fails with InvalidLocationConstraint although the bucket exists; the same credentials work in the console."

```bash
python3 scripts/oss_backup_integration_diagnosis.py --tool "veeam" --error-code "InvalidLocationConstraint"
```

Attribute it to a region/endpoint mismatch in the backup software's S3-compatible site configuration, then cover the whitelist path: Veeam access whitelisting is a manual application, not self-service.


## Available Scripts

| Script | Purpose |
| --- | --- |
| `scripts/oss_backup_integration_diagnosis.py` | Entry point: maps tool/error/symptom/storage-class to attribution and configuration advice; prints structured JSON plus `STATUS`/`NEXT_ACTION` |
| `scripts/_integration_catalog.py` | Embedded tool x symptom attribution catalog (Python constant, no data files) |
| `scripts/requirements.txt` | Dependency declaration: pure Python standard library only |

## Error Handling

| Script status | Exit code | Agent behavior |
| --- | --- | --- |
| `STATUS: OK` | 0 | Report diagnosis verbatim per the Final Answer Contract |
| `STATUS: DEGRADED` | 0 | Present candidates, ask for the discriminator, do not conclude |
| `STATUS: FAIL` | 1 | Report `NEXT_ACTION` verbatim and request tool/version/error/symptom |

- **Doc lookup module** (`scripts/_doc_lookup.py`): Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path.

## Final Answer Contract

- Every conclusion in the final answer MUST come from the script output: root-cause directions, configuration advice, known issues, fee judgments, endpoint forms and doc references are transcribed verbatim.
- The Agent MUST NOT polish, re-rank, extrapolate, or invent beyond the script output; additions are limited to the user's own context (bucket, region, UID) and the boundary statement from Absolute Rule 5.
- The final answer MUST explicitly state that the diagnosis is configuration advice only and that no change was executed; whitelist/execution/refund requests end with the escalation wording from `references/integration-playbook.md`.
- The final answer MUST contain an explicit "Inputs still missing" line listing every parameter the user did not supply and what it would refine; if nothing is missing, write "Inputs still missing: none".
- Any fee/billing question MUST end with the prices-out-of-scope statement: this skill explains which billing item the backup workload triggers, not how much it costs — exact amounts come from the user's own console bill and the official OSS pricing page, and resource-package or refund decisions go to a human support ticket.
- When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."
- When the report carries `doc_verification`, the final answer MUST contain a `doc_verification` line naming its outcome **even when `docs` is empty** (offline index or no matching topic): state matched=false and the reason. Never drop the section silently and never fabricate URLs.
- Keep report technical terms in their original language: tokens like `multipart`, `midway`, `large file`, `bucket`, `OSS`, `versioning` from `known_issues`/`config_checklist` MUST appear verbatim in the final answer even when the surrounding prose is Chinese — never translate the technical tokens away.

