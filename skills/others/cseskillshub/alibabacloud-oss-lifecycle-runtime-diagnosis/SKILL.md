---
name: alibabacloud-oss-lifecycle-runtime-diagnosis
description: |
  Read-only OSS diagnosis for lifecycle runtime and archive restore.
  Use when a lifecycle rule does not take effect (loading window, prefix/tag matching,
  one-way transition, versioning), when an archive / cold archive / deep cold archive
  object cannot be read (restore tiers, archive direct read), or for storage tiering
  advice and restore/retrieval fee composition.
  Triggers: "lifecycle rule not working", "archive file cannot download",
  "InvalidObjectState", "RestoreAlreadyInProgress", "Overlap for same action type",
  "The operation is not valid for the object's state", "restore fee",
  "storage class transition", "cold archive restore duration", "storage tiering".
  Do NOT use for bill line-items (alibabacloud-oss-billing-diagnosis), data recovery
  (alibabacloud-oss-deletion-recovery-diagnosis), transfer error codes
  (alibabacloud-oss-transfer-error-code-diagnosis), backup-tool retrieval fees
  (alibabacloud-oss-backup-integration-diagnosis), or write operations.
---

# OSS Lifecycle Runtime & Archive Restore Diagnosis

Diagnose Alibaba Cloud OSS lifecycle and archive problems: "I configured a lifecycle rule but the files are still Standard / not deleted", "my archive file cannot download and returns InvalidObjectState", "how long does a cold archive restore take and what is the restore fee", "how should I tier my storage to cut cost".

Core approach: verify the caller identity, fetch the bucket metadata with the read-only GetBucketInfo control-plane query, read the versioning state with GetBucketVersioning and the actual lifecycle configuration with GetBucketLifecycle, then run a pure-function attribution engine on the evidence: rule loading window (24 hours after creation + daily 08:00 Beijing-time execution), prefix/tag matching against the object key, longest-prefix conflict coverage, delete-over-transition priority on identical scopes, the one-way storage-class transition ladder, and versioning-specific expiration semantics. For restore questions, map the storage class and the reported error code to the official restore tier table (duration and replica validity) and fee composition; the restore itself is always described as user-executed guidance. Conclude with evidence-based findings only; this skill never changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API - e.g. `PutBucketLifecycle`, `DeleteBucketLifecycle`, `RestoreObject`, `PutObject`/copy-based storage-class conversion, `ossutil restore`, `ossutil set-meta`, `PutBucketVersioning`, or any ACL/policy change. This includes commands "for the user to run manually" issued from the scripts; rule creation and restores are described as manual guidance in words only, and the user executes them. When a lifecycle rule change is needed, MANDATORY behavior: output a configuration template (XML/JSON shape or console path) as advice - never call the write API.
2. **MANDATORY entry-point enforcement:** All OSS diagnostics MUST be performed by running the scripts under `scripts/` (`oss_lifecycle_runtime_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts - the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / GetBucketVersioning / GetBucketLifecycle / ListBuckets / GetCallerIdentity. If a query fails or returns empty, record it and state the limitation - never invent rule definitions, restore states, or fee amounts. `NoSuchLifecycle` means "no rule configured" - report it as a finding, not as an error.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line - never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill only answers lifecycle rule runtime attribution, archive/cold-archive/deep-cold-archive restore diagnosis (including the restore and retrieval fee composition and the replica validity window tied to unfreezing), and storage tiering advice. It does NOT handle the consequences/recoverability of data already deleted by lifecycle expiry or by mistake (defer to the deletion-recovery skill), bill line-item attribution or resource-package deduction (defer to the billing skill - only the fee composition of a restore/retrieval is answered here), multipart fragment cleanup (defer to the multipart-upload diagnosis skill), or generic upload/download error codes unrelated to restore state (defer to the transfer-error-code skill).

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `findings` / `restore` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Trigger Conditions

Route here when the user reports: a lifecycle rule that does not take effect (files not converted / not deleted, rule stuck in the console "loading" state forever, rules seemingly ignored, two rules with overlapping prefixes rejected with `Overlap for same action type`, a tag-filtered rule that never matches); an archive / cold archive / deep cold archive object that cannot be downloaded or read (`InvalidObjectState`, "The operation is not valid for the object's state", `RestoreAlreadyInProgress`, "restore in progress", restore duration questions, or Archive Direct Read as the no-restore alternative); the restore / retrieval fee composition and replica validity window behind an unfreeze; versioning-specific results such as a delete marker instead of a real delete or cleaning up non-current versions; or requests for storage tiering strategy advice.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-lifecycle-runtime-diagnosis`
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
- OSS control-plane calls (Python oss2 SDK): the environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and optionally `ALIBABA_CLOUD_SECURITY_TOKEN` (STS sessions).
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

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request asks for an actual rule write, a restore execution, or any mutation (Absolute Rule 1), do not execute it - output the configuration template / manual guidance only. When a request falls outside lifecycle runtime / restore attribution (Absolute Rule 6), state the boundary and defer to the responsible skill or manual handling.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket to diagnose.
- **Scope** (`--scope`): optional; `lifecycle` (rule-not-working attribution), `restore` (archive restore diagnosis), `strategy` (tiering advice), or `all` (default).
- **Object key** (`--object`): optional; the object the user cares about, used for prefix-matching attribution.
- **Object storage class** (`--object-class`): optional; the object's actual class (`Standard`/`IA`/`Archive`/`ColdArchive`/`DeepColdArchive`); when absent it is auto-defaulted to the bucket default class and declared.
- **Error** (`--error`): optional; the data-plane error the user hit (e.g. `InvalidObjectState`, `RestoreAlreadyInProgress`).
- **Days since last modification** (`--days-since-created`): optional; checks the Days-policy 24-hour spacing requirement.
- **Expected region** (`--region`): optional; used to derive the query endpoint.
- **UID**: can always be omitted - it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted or derived from --region, object class defaulted to the bucket default class, UID derived), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Lifecycle playbook | [references/lifecycle-playbook.md](references/lifecycle-playbook.md) | Rule loading/execution mechanism, matching conditions, conflict/coverage semantics, versioning behavior, one-way transition ladder, not-working attribution tree |
| M2: Restore guide | [references/restore-guide.md](references/restore-guide.md) | Archive/ColdArchive/DeepColdArchive restore tiers and duration, replica validity, fee composition, InvalidObjectState/RestoreAlreadyInProgress routing, storage tiering advice |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Orchestration

Symptom routing before running the entry script:
- "rule not taking effect / files not converted or deleted" -> `--scope lifecycle` with `--object <key>` (and `--days-since-created <N>` when known).
- "archive file cannot download / InvalidObjectState / how long does restore take / restore fee" -> `--scope restore` with `--object-class <class>` and `--error <code>` when reported.
- "how to cut storage cost / tiering advice" -> `--scope strategy`.
- mixed symptoms -> `--scope all`.
- Data already vanished and the user wants it back -> route to the deletion-recovery skill instead (Absolute Rule 6).

## Execution Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the bucket name, the symptom family, the object key / storage class / error code when known; map the symptom with the Orchestration section above.

### Step 2: Run the Lifecycle Runtime Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/oss_lifecycle_runtime_diagnosis.py \
    --bucket <name> [--scope lifecycle|restore|strategy|all] \
    [--object <key>] [--object-class <class>] [--error <code>] \
    [--days-since-created <N>] [--region <region>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK with the resolved endpoint, carrying the session-id User-Agent and a per-call timeout; on failure falls back to `ListBuckets` (prefix lookup) to locate the bucket's region.
3. Calls `GetBucketVersioning` and `GetBucketLifecycle` (each degraded with `[WARN]`); `NoSuchLifecycle` is normalized to "no rules configured", a finding rather than an error.
4. Runs the pure-function attribution engine (loading window, prefix/tag matching, longest-prefix coverage, delete-over-transition conflicts, Days spacing, versioning semantics) and the restore tier/fee table.
5. Emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdict and Advise

Read `findings`, `restore`, and `recommendations` from the report:
- **no_rules_configured** - nothing will ever run; output the configuration template as manual guidance (console path or PutBucketLifecycle XML shape) and state the 24-hour loading window plus the daily 08:00 Beijing-time execution; this skill never applies the rule.
- **loading_window / days_policy_spacing** - the rule exists but the timing mechanism explains the delay; relay the wait semantics honestly.
- **prefix_not_matched / longest_prefix_only / delete_beats_transition / disabled_rules** - relay exactly which rule covers the object and why another rule is shadowed or blocked.
- **invalid_object_state / restore_already_in_progress** - relay the restore tier table for the object's class, the replica validity window, and the fee composition; the restore is user-executed.
- **DEGRADED report** - relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent rule definitions or restore states.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual fields from the report. Base the conclusion on the script's `findings` / `restore` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any change; PutBucketLifecycle is only ever shown as a template).

## Important Notes

- **Rule loading is not instant**: a lifecycle rule is loaded within 24 hours after creation and always executes starting 08:00 Beijing time daily; frequent rule updates can abort the same day's task (source: help.aliyun.com lifecycle rules based on the last modified time).
- **Time basis**: lifecycle evaluates the object's LAST MODIFIED time (or the last access time only when access-tracking based rules are enabled); a transition does NOT refresh the timestamp - later rules still judge by the original modified time (source: help.aliyun.com lifecycle overview).
- **Matching semantics**: prefix matching is literal (no wildcards/suffix/regex) with longest-prefix-wins coverage - overlapping rules never stack; tag rules require the object to carry ALL configured tags; deletion actions beat transition actions on the same scope (source: help.aliyun.com lifecycle overview).
- **One-way transition ladder**: Standard -> IA -> Archive -> ColdArchive -> DeepColdArchive only; the sole automatic upward path is access-time based IA -> Standard on re-access (when enabled) - otherwise converting back is a manual user operation (source: help.aliyun.com storage class conversion).
- **Restore tiers are fixed by class and tier, NOT by file size**: Archive ~1 minute; ColdArchive Expedited ~1h / Standard ~2-5h / Bulk ~5-12h; DeepColdArchive Expedited ~12h / Standard ~48h. Replica validity: Archive 1-7 days, ColdArchive/DeepColdArchive 1-365 days (source: help.aliyun.com restore objects).
- **Restore fee composition**: restoring bills a capacity-based data-retrieval fee plus a per-request restore fee (Archive as Put-type request; ColdArchive/DeepColdArchive as retrieval requests); ColdArchive/DeepColdArchive replicas additionally bill temporary storage per day within the validity window. Restoring within the replica validity window does not re-bill retrieval; minimum-storage-duration fees (IA 30d / Archive 60d / ColdArchive 180d / DeepColdArchive 180d) still apply on early delete (source: help.aliyun.com storage fees & restore docs).
- **Versioning semantics**: on a versioned bucket, lifecycle Expiration of the current version adds a delete marker (data remains as a restorable historical version); permanent deletion requires NoncurrentVersionExpiration (source: help.aliyun.com lifecycle overview).
- **Read-only operations**: only GetBucketInfo, GetBucketVersioning, GetBucketLifecycle, ListBuckets, and `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 - lifecycle rule not working**

> User: "I set a lifecycle rule on bucket test-agentceping (UID 1552974654746705, cn-hangzhou) to convert logs/ to IA after 30 days, but the files are still Standard - lifecycle rule not working."

```bash
python3 scripts/oss_lifecycle_runtime_diagnosis.py --bucket test-agentceping --scope lifecycle --object logs/2026/07/a.log --days-since-created 35 --region cn-hangzhou
```

Relay the fetched rule list and the attribution findings (measured: this bucket has no rule at all, so the report says `no_rules_configured`); output the configuration template as manual guidance, declare the 24-hour loading window, and declare any auto-filled parameters. If `STATUS: DEGRADED`, relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 - archive file cannot download (InvalidObjectState)**

> User: "Downloading my archive file fails with InvalidObjectState; the object is ColdArchive. How do I restore it, how long does it take, and does it cost anything?"

```bash
python3 scripts/oss_lifecycle_runtime_diagnosis.py --bucket <name> --scope restore --object-class ColdArchive --error InvalidObjectState
```

Relay the ColdArchive restore tier table (Expedited ~1h / Standard ~2-5h / Bulk ~5-12h), the 1-365 day replica validity window, and the fee composition (retrieval capacity fee + restore request fees); the restore command itself is user-executed guidance only.

**Example 3 - storage tiering strategy**

> User: "I want to tier my bucket's storage to cut cost - any strategy advice?"

```bash
python3 scripts/oss_lifecycle_runtime_diagnosis.py --bucket <name> --scope strategy
```

Relay the tiering ladder advice with minimum-storage-duration and retrieval-fee caveats; emphasize conversion is one-way downward and the restore cost trade-off; never apply any rule.

<!-- production-pattern-example -->

**Example N - An archived object cannot be read right after the rule fired**

> User: "A lifecycle rule moved my objects to Archive and now every download returns InvalidObjectState."

```bash
python3 scripts/oss_lifecycle_runtime_diagnosis.py --bucket "my-bucket" --object "data/archive.tar" --error "InvalidObjectState" --object-class "Archive"
```

Explain that Archive-class objects must be restored first, quote the restore tier and the retrieval fee basis, and list the rule-match conditions (prefix, tag, version status) that decide whether the rule applied at all.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/oss_lifecycle_runtime_diagnosis.py` | Lifecycle runtime entry: GetBucketInfo + GetBucketVersioning + GetBucketLifecycle attribution engine + restore tier/fee routing, with ListBuckets fallback |

CLI options for `oss_lifecycle_runtime_diagnosis.py`: `--bucket <name>` (required), `--scope lifecycle|restore|strategy|all` (default `all`), `--object <key>`, `--object-class <class>`, `--error <code>`, `--days-since-created <N>`, `--region <region>` (all optional).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing `oss:GetBucketInfo` / `oss:GetBucketLifecycle` / `oss:GetBucketVersioning`, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, run the ListBuckets fallback, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (or the bucket itself was deleted) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| `NoSuchLifecycle` / 404 | No lifecycle rule configured on the bucket | NOT an error: report it as the `no_rules_configured` finding and output the configuration template as guidance |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "rule missing" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the attribution verdict with the actual evidence fields (rule list, matching prefixes, versioning status, restore tier table) - no fabricated values, and no invented rule definitions or restore states.
3. Declare every auto-filled parameter (endpoint default, object-class default, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Give rule-change/restore suggestions as manual guidance only (this skill never applies changes; PutBucketLifecycle appears only as a template).
6. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."

