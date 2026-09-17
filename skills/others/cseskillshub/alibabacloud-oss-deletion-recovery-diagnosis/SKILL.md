---
name: alibabacloud-oss-deletion-recovery-diagnosis
description: |
  Read-only OSS diagnosis of accidental-deletion recovery and deletion residue: uses
  versioning to decide if a deleted object is recoverable, explains delete markers,
  leftover fragments, and why capacity/cost does not drop.
  States honestly when data is unrecoverable by official policy (versioning never
  enabled, lifecycle noncurrent version expiration, overdue-payment release).
  Triggers: "accidentally deleted how to recover", "delete marker", "BucketNotEmpty",
  "failed to delete bucket", "capacity not reduced after deletion",
  "file/object suddenly disappeared or returns 404, can it be recovered",
  "restore the deleted object to its previous version". Not for bill line-items
  (alibabacloud-oss-billing-diagnosis), the fragment cleanup procedure
  (alibabacloud-oss-multipart-upload-diagnosis), transfer or endpoint/region
  issues, lifecycle rule design, or restore/delete writes.
  Invoke immediately; missing bucket/region/object details are handled internally,
  never ask for supplements before invoking.
---

# OSS Accidental Deletion Recovery & Residue Diagnosis

Diagnose Alibaba Cloud OSS deletion problems: "I accidentally deleted uploads/report.pdf, how can I recover it", "deleting my bucket fails with BucketNotEmpty", "I deleted files yesterday but the storage usage and cost did not drop", "what is a delete marker and can I restore the object".

Core approach: verify the caller identity, fetch the bucket metadata with the read-only GetBucketInfo control-plane query, check the bucket versioning status with GetBucketVersioning, and run a pure-function decision tree on the result: versioning enabled means the deletion only inserted a delete marker and the historical versions are recoverable (manual restore guidance); versioning suspended means a delete without version id creates a null delete marker (historical versions remain recoverable), while a delete with an explicit version id permanently removes that version; versioning never configured means the data is not recoverable from OSS itself and expectations must be managed honestly. For residue questions, ListMultipartUploads counts leftover fragments and the versioning state explains historical-version storage. Conclude with evidence-based findings only; this skill never changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API — e.g. `DeleteObject`, `DeleteObjects`, `DeleteBucket`, any version restore (`ossutil revert`), delete-marker removal, multipart abort (`AbortMultipartUpload`), `PutBucketVersioning`, or any ACL/policy/lifecycle change. This includes commands "for the user to run manually" issued from the scripts; recovery and cleanup are described as manual guidance in words only, and the user executes them. If the user asks to restore a version or clean fragments, only output the guidance and declare this skill is read-only. **Empty / not-found is a valid result — never react to it with a write.** If the bucket or object does not exist (`NoSuchBucket` / 404), a query returns empty, or versioning was never configured, that already is a complete conclusion: report it honestly and STOP. Never try to create / re-create / verify / test / validate / restore / repair the bucket or object, and never fall back to hand-written ossutil / SDK / curl calls — stay inside the read-only entry-script flow.
2. **MANDATORY entry-point enforcement:** All OSS diagnostics MUST be performed by running the scripts under `scripts/` (`oss_deletion_recovery_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts — the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / GetBucketVersioning / ListMultipartUploads / ListBuckets / GetCallerIdentity. If a query fails or returns empty, record it and state the limitation — never invent versioning states, version ids, or residue counts. Never promise recovery without an enabled (or pre-suspension) version to restore.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line — never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill answers deletion recoverability (including a bucket released after an overdue-payment suspension, whose data official policy declares unrecoverable — state that verdict honestly with the doc citation), deletion residue attribution (objects / multipart fragments / historical versions), and prevention advice. It does NOT pursue an out-of-band or ticket-based restoration of data official policy already made unrecoverable, does NOT attribute bill line items (defer to the billing skill), and does NOT walk the detailed multipart fragment cleanup procedure (defer to the multipart-upload diagnosis skill).

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be
invoked with --question "<customer original wording>". The script first
matches embedded knowledge, then verifies against official OSS docs
(doc_verification, llms-index). The final answer MUST cite the URLs from
doc_verification.docs. If doc_verification.note starts with DEGRADED, state
explicitly: "Unable to verify against online official docs (offline)."
Never fabricate doc URLs; only URLs returned by the script may be cited.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `recovery` / `residue` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Trigger Conditions

Route here when the user reports: an accidentally deleted OSS object they want back; an object/file that suddenly disappeared or returns 404 and they are not sure whether it was deleted; a question about restoring a deleted object to its previous version; a bucket that cannot be deleted because it is "not empty" (BucketNotEmpty); storage capacity or cost that did not drop after deleting data; delete markers or versioning-based restore questions; leftover multipart fragments after interrupted uploads; files that vanished when a lifecycle expiration rule fired and whether they can still be recovered; whether data of a bucket released after an overdue-payment suspension can be recovered.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-deletion-recovery-diagnosis`
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

Credentials are resolved exclusively by the default credential chain:
- OSS control-plane calls (Python oss2 SDK): the environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and optionally `ALIBABA_CLOUD_SECURITY_TOKEN` (STS sessions).
- Identity check (`aliyun sts get-caller-identity`): the aliyun CLI default credential chain (environment or `~/.aliyun/config.json`).

Do not read, print, or pass AK/SK/STS tokens explicitly. If the identity check fails, guide the user to run `aliyun configure` — never ask for AK/SK.

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

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request asks for an actual restore, cleanup, or any mutation (Absolute Rule 1), do not execute it — output manual guidance only. When a request falls outside deletion recovery / residue attribution (Absolute Rule 6), state the boundary and defer to the responsible skill or manual handling.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket to diagnose.
- **Deleted object key** (`--object`): optional; the accidentally deleted object key, used to personalize the recovery guidance.
- **Scope** (`--scope`): optional; `recover` (recoverability assessment), `residue` (residue/attribution), or `all` (default).
- **Expected region** (`--region`): optional; used to derive the query endpoint.
- **Customer wording** (`--question`): optional; the customer's original question wording passed verbatim. Enables the official-doc verification leg (`doc_verification` section) — read-only, help.aliyun.com only, never blocks the diagnosis.
- **UID**: can always be omitted — it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted or re-derived from the bucket location, UID derived), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Recovery decision tree | [references/recovery-decision-tree.md](references/recovery-decision-tree.md) | Versioning-based recoverability decision tree, delete marker semantics, restore guidance, recovery boundaries |
| M2: Deletion residue checklist | [references/deletion-residue-checklist.md](references/deletion-residue-checklist.md) | BucketNotEmpty residue classes (objects / fragments / versions), capacity-not-dropping attribution, prevention |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Orchestration

Symptom routing before running the entry script:
- "accidentally deleted X, can I recover" → `--scope recover` with `--object X`.
- "bucket cannot be deleted / BucketNotEmpty" → `--scope residue`.
- "capacity or cost did not drop after deletion" → `--scope residue` (fragment + historical-version attribution), and note bill line-item questions belong to the billing skill.
- mixed symptoms → `--scope all`.

## Execution Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the bucket name, the deleted object key if known, and the deletion symptom; map the symptom with the Orchestration section above.

### Step 2: Run the Deletion Recovery Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/oss_deletion_recovery_diagnosis.py \
    --bucket <name> [--object <key>] [--scope recover|residue|all] [--region <region>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK with the resolved endpoint, carrying the session-id User-Agent and a per-call timeout; on failure falls back to `ListBuckets` (prefix lookup) to locate the bucket's region.
3. Calls `GetBucketVersioning` (degraded with `[WARN]`) and feeds the status into the recoverability decision tree.
4. Calls `ListMultipartUploads` for residue scope (degraded with `[WARN]`) to count leftover fragments.
5. Emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdict and Advise

Read `recovery.recoverable` and `residue` from the report:
- **yes** (versioning enabled) — the deletion only inserted a delete marker; give the manual restore guidance (restore the pre-deletion version or remove the topmost delete marker); this skill never executes the restore.
- **partial** (versioning suspended) — a delete without version id creates a null delete marker and historical versions remain recoverable (same restore path as enabled); only a delete with an explicit version id permanently removes that version. Objects newly written during suspension carry versionId=null and lack true version protection.
- **no** (versioning never configured) — OSS has no recycle bin; the data is not recoverable from OSS. Point to external backups / replication copies and advise enabling versioning for the future.
- **residue findings** — relay fragment counts and historical-version storage as the cause of BucketNotEmpty / capacity not dropping; cleanup is user-executed guidance only.
- **DEGRADED report** — relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent the versioning state.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual numbers/fields from the report. Base the conclusion on the script's `status` / `recovery` / `residue` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any change).

## Important Notes

- **OSS provides no recycle bin**: without versioning, a plain delete is permanent; never promise recovery before the versioning status is verified (source: help.aliyun.com versioning overview).
- **Delete marker semantics**: with versioning enabled, deleting without a version id inserts a delete marker and keeps all historical versions recoverable; deleting WITH a version id permanently removes that version (irreversible). With versioning suspended, deleting without a version id also creates a delete marker (versionId=null) and historical versions are NOT affected; only deleting WITH an explicit version id permanently removes that version (source: help.aliyun.com `/zh/oss/user-guide/manage-objects-in-a-versioning-suspended-bucket`).
- **Lifecycle deletion semantics**: a lifecycle `Expiration` on a versioned bucket turns the current version into a historical version (still recoverable) instead of erasing it; `NoncurrentVersionExpiration` permanently deletes noncurrent versions and cannot be undone. If data vanished "on its own", check lifecycle rules before concluding accidental deletion.
- **BucketNotEmpty precondition**: deleting a bucket fails while objects, unfinished multipart fragments, or (if versioned) historical versions and delete markers remain — all three classes must be checked.
- **Overdue-payment release is unrecoverable**: if the account was released after overdue service suspension without repayment in time, the data was cleaned and cannot be recovered per official policy (source: help.aliyun.com OSS overdue-payments); state this honestly instead of investigating a restore path.
- **Read-only operations**: only GetBucketInfo, GetBucketVersioning, ListMultipartUploads, ListBuckets, and `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 — accidentally deleted object, versioning status unknown**

> User: "I accidentally deleted uploads/report.pdf from bucket test-agentceping (UID 1552974654746705), how can I recover it?"

```bash
python3 scripts/oss_deletion_recovery_diagnosis.py --bucket test-agentceping --object uploads/report.pdf --scope recover --region cn-hangzhou
```

Report the `recovery` verdict with the measured versioning status: if versioning was never configured, state plainly that OSS cannot recover the data (no recycle bin), point to backups/replication, and advise enabling versioning; declare any auto-filled parameters. If `STATUS: DEGRADED`, relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 — bucket cannot be deleted (BucketNotEmpty)**

> User: "Deleting my bucket keeps failing with 'the bucket is not empty' but I already deleted all files."

```bash
python3 scripts/oss_deletion_recovery_diagnosis.py --bucket <name> --scope residue
```

Relay the residue classes: leftover multipart fragments (from interrupted uploads) and, if versioning is/was active, historical versions and delete markers — both invisible in the plain file list. Give the user-executed cleanup guidance from references/deletion-residue-checklist.md.

**Example 3 — capacity/cost not reduced after deletion**

> User: "I deleted most objects last week but storage usage and cost did not drop."

```bash
python3 scripts/oss_deletion_recovery_diagnosis.py --bucket <name> --scope residue
```

Attribute the residual storage to unfinished multipart fragments and/or historical versions (lifecycle `NoncurrentVersionExpiration` guidance); note bill line-item detail questions belong to the billing skill.

<!-- production-pattern-example -->

**Example N — Capacity did not drop after deleting objects**

> User: "I deleted everything in the bucket but the used capacity and the bill did not go down."

```bash
python3 scripts/oss_deletion_recovery_diagnosis.py --bucket "my-bucket" --object "docs/report.pdf"
```

Answer with a recoverability verdict first (versioning state decides it), then enumerate what still occupies capacity: delete markers, noncurrent versions and unfinished multipart parts.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/oss_deletion_recovery_diagnosis.py` | Deletion recovery entry: GetBucketInfo + GetBucketVersioning decision tree + ListMultipartUploads residue check, with ListBuckets fallback |
| `scripts/_doc_lookup.py` | Official-doc verification leg: help.aliyun.com llms-index lookup + cached index + .md body excerpts (stdlib only, zero credentials, never blocks the diagnosis) |

CLI options for `oss_deletion_recovery_diagnosis.py`: `--bucket <name>` (required), `--object <key>` (optional), `--scope recover|residue|all` (default `all`), `--region <region>` (optional), `--question "<customer original wording>"` (optional, enables the `doc_verification` leg).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing `oss:GetBucketInfo` / `oss:GetBucketVersioning`, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, run the ListBuckets fallback, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (or the bucket itself was deleted) | Verify spelling and owning account; if the bucket was deleted, object data is unrecoverable without a backup; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "unrecoverable" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the recoverability verdict with the actual evidence fields (versioning status, fragment count, residue classes) — no fabricated values, and no recovery promises without a recoverable version.
3. Declare every auto-filled parameter (endpoint default, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Give restore/cleanup suggestions as manual guidance only (this skill never applies changes).
6. When `doc_verification` is present, cite the doc URLs from `doc_verification.docs` verbatim, and state the offline-degradation sentence when `doc_verification.note` starts with DEGRADED.
