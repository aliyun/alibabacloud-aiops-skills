---
name: alibabacloud-oss-ossfs-mount-diagnosis
description: |
  Read-only diagnostics for ossfs and container OSS mounts. Use when an
  ossfs mount fails, a mounted directory disappears, an ACK/ACS storage
  volume mount returns 403, or reading archive objects through a mount
  returns 403. Attributes causes (credential file, endpoint region, RAM
  permission, FUSE dependency) and checks bucket region/storage class
  read-only for the archive direct-read judgment; never executes mounts,
  never changes anything. Triggers: "ossfs mount failed",
  "mount directory disappeared", "mount OSS in container",
  "storage volume mount 403", "ossfs archive read 403".
  Do NOT use for endpoint selection
  (use alibabacloud-oss-endpoint-internal-diagnosis), authorization
  config (use alibabacloud-oss-cross-account-auth-diagnosis), archive
  restore or lifecycle (use
  alibabacloud-oss-lifecycle-runtime-diagnosis), or transfer acceleration
  error codes (use alibabacloud-oss-transfer-error-code-diagnosis).
---

# OSS ossfs & Container Mount Diagnosis

Diagnose Alibaba Cloud OSS ossfs and container storage-volume mount problems: "ossfs mount failed with 403", "my mounted OSS directory disappeared and ls says Transport endpoint is not connected", "mounting an OSS bucket as a storage volume in ACK/ACS returns 403", "reading a file through the mount returns 403 and the bucket is archive storage".

Core approach: verify the caller identity, fetch the bucket's real location, endpoints and storage class with the read-only GetBucketInfo control-plane query, match the user's mount endpoint against the bucket region, judge archive direct-read risk from the storage class, and route the reported symptom / error message to evidence-based attribution knowledge (credential file, endpoint, RAM permission, FUSE dependency, authorization-model confusion). **This skill only diagnoses and advises: it never executes any mount / fusermount / kubectl command and never changes anything** - the runtime environment cannot perform a real mount, so knowledge judgment plus read-only configuration checks are the primary form, and this is stated honestly in every report.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (no execution):** Under **NO** circumstances may you execute, or generate for direct execution, any mount-class command - `ossfs`, `ossfs2`, `fusermount`, `mount`/`umount`, `modprobe fuse`, `kubectl apply`, or any command that changes bucket configuration (including PutBucketArchiveDirectRead, PutBucketPolicy, ACL changes). All corrective steps are output as MANUAL GUIDANCE for the user to run themselves.
2. **ABSOLUTE PROHIBITION (read-only enforcement):** Never generate, write, or execute any command/script calling a mutating OSS API - e.g. `PutBucket*`, `DeleteBucket*`, `PutObject*`, `DeleteObject*`, RestoreObject, or any ACL/policy change, including commands "for the user to run manually" beyond the manual guidance allowed by rule 1's scope.
3. **MANDATORY entry-point enforcement:** All cloud-side checks MUST be performed by running the scripts under `scripts/` (`ossfs_mount_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts - the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
4. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script, and never ask the user to paste them into the conversation.
5. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / ListBuckets / GetCallerIdentity or in the documented knowledge of `references/`. If a query fails or returns empty, record it and state the limitation - never invent bucket locations, storage classes, or error causes.
6. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line - never silently skip or abort without a report.
7. **SCOPE BOUNDARY:** This skill only answers ossfs / container OSS mount attribution questions (mount failure, disappeared mountpoint, container volume 403, archive read 403 through a mount). General endpoint selection, generic authorization authoring, archive restore procedures, billing disputes, and NAS/CPFS volumes are out of scope - state the boundary and defer to the matching skill (see the description's Do NOT use list).

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Trigger Conditions

Use this skill when the customer's own wording matches one of these phrases (the same list the `description` advertises):

- "ossfs mount failed"
- "mount directory disappeared"
- "mount OSS in container"
- "storage volume mount 403"
- "ossfs archive read 403"

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| endpoint selection | `alibabacloud-oss-endpoint-internal-diagnosis` |
| authorization config | `alibabacloud-oss-cross-account-auth-diagnosis` |
| archive restore or lifecycle | `alibabacloud-oss-lifecycle-runtime-diagnosis` |
| transfer acceleration error codes | `alibabacloud-oss-transfer-error-code-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `verdict` / `archive_verdict` / `recommendations`, combine them with the knowledge modules in `references/`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-ossfs-mount-diagnosis`
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

The identity pre-check shells out to the aliyun CLI, which MUST be **version 3.3.3 or newer**: older builds resolve the default credential chain differently and can drop the STS session token. Verify the installed version and upgrade it before the first run:

```bash
aliyun version        # must print 3.3.3 or newer (measured with 3.4.5)
aliyun upgrade --yes  # upgrade the installed CLI in place to the latest version
```

If the CLI is not installed at all, install the Alibaba Cloud CLI package for the host OS from the official release channel and then run `aliyun configure` (the profile stays in `~/.aliyun/config.json`; this skill never asks for AK/SK). When the CLI is missing, too old to upgrade, or unauthenticated, the identity pre-check degrades instead of aborting: `scripts/_oss_client.py` logs `[WARN] identity pre-check failed: ...` on stderr, records the empty UID, and the mount diagnosis still runs to a conclusion, because the identity label is traceability only and never evidence.

```bash
cd $SKILL_DIR

# Verify caller identity (informational only; credentials always come from the default chain)
python3 scripts/sts_token.py
```

## User Confirmation

Because every action of this skill is strictly read-only and no mount command is ever executed, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request falls outside mount attribution (rule 7), do not proceed with any diagnosis - state the boundary and give manual guidance or defer to the matching skill only.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/ossfs_mount_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: ossfs mount knowledge | Mount failure attribution: credential file, endpoint, RAM, FUSE dependency, mountpoint; disappeared mountpoint / process-exit analysis; error-message routing table |
| M2: Container volume 403 | K8s/ACK/ACS storage-volume mount 403 attribution: mount credential (Secret AK / RRSA) vs Bucket Policy confusion, diagnosis order |
| M3: Archive direct read | Storage-class judgment table for archive read 403 through mounts; archive-direct-read rules, limits and cost |
| M4: RAM policies | Minimal read-only RAM policy required by this skill |

Documented run order: Step 1: Confirm Identity and Route the Symptom; Step 2: Run the Mount Pre-Check / Diagnosis; Step 3: Interpret the Verdicts and Advise; Step 4: Conclusion and Suggestions.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket being mounted / diagnosed.
- **Mount endpoint** (`--endpoint`): optional; the endpoint configured in the user's ossfs / PV configuration. When provided it is classified (public / internal / accelerate / invalid) and matched against the bucket's real region.
- **Expected region** (`--region`): optional; used to derive the query endpoint when `--endpoint` is absent.
- **Symptom** (`--symptom`): optional free text describing the symptom or the exact error message (e.g. `mount failed`, `Transport endpoint is not connected`, `container volume 403`, `archive read 403`, or the verbatim ossfs error). It is routed to a diagnosis category and to the knowledge modules.
- **Platform** (`--platform`): optional mount host type: `ecs` | `ack` | `acs` | `docker` | `pai` | `local`; used for internal-vs-public endpoint advice.
- **UID**: can always be omitted - it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted, UID derived), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --endpoint/--region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: ossfs mount knowledge | [references/ossfs-mount-knowledge.md](references/ossfs-mount-knowledge.md) | Mount failure attribution: credential file, endpoint, RAM, FUSE dependency, mountpoint; disappeared mountpoint / process-exit analysis; error-message routing table |
| M2: Container volume 403 | [references/container-volume-403.md](references/container-volume-403.md) | K8s/ACK/ACS storage-volume mount 403 attribution: mount credential (Secret AK / RRSA) vs Bucket Policy confusion, diagnosis order |
| M3: Archive direct read | [references/archive-direct-read.md](references/archive-direct-read.md) | Storage-class judgment table for archive read 403 through mounts; archive-direct-read rules, limits and cost |
| M4: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Route the Symptom

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Map the user's symptom to a category with [references/ossfs-mount-knowledge.md](references/ossfs-mount-knowledge.md) (error-message routing table) or [references/container-volume-403.md](references/container-volume-403.md).

### Step 2: Run the Mount Pre-Check / Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/ossfs_mount_diagnosis.py \
    --bucket <name> [--endpoint <mount-endpoint>] [--region <region>] \
    [--symptom "<symptom-or-error-text>"] [--platform <ecs|ack|acs|docker|local>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Routes `--symptom` to a category (archive_read_403 / container_403 / dir_disappeared / mount_failed / generic) and classifies any verbatim ossfs error message.
3. Calls OSS `GetBucketInfo` through the oss2 SDK, carrying the session-id User-Agent and a per-call timeout; on failure falls back to `ListBuckets` (prefix lookup), logging `[WARN]` for every degraded step.
4. Computes `verdict` (endpoint region match) and `archive_verdict` (storage-class-based archive direct-read judgment).
5. Emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdicts and Advise

Read `verdict.region_match`, `archive_verdict` and `recommendations`:
- **region mismatch** - the mount endpoint's region differs from the bucket location: ossfs will fail with "must be addressed using the specified endpoint"; give the correct public/internal endpoints as manual guidance.
- **archive_check_required** - bucket storage class is Archive: mount reads of unrestored archive objects return 403 unless archive direct read is enabled or the objects are restored; the switch state is NOT visible via GetBucketInfo, so ask the user to check it and relay the options from [references/archive-direct-read.md](references/archive-direct-read.md).
- **archive_direct_read_not_applicable** - ColdArchive/DeepColdArchive: restore is the only path; advise honestly.
- **no_archive_issue** - truthfully state "no archive direct-read problem for this bucket" and continue with credential/endpoint/FUSE attribution per M1.
- **DEGRADED report** - relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent the bucket region or storage class. A nonexistent bucket (NoSuchBucket) is itself a classic mount-failure root cause - say so.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual numbers/fields from the report, then attach the matching knowledge guidance from M1/M2/M3 as MANUAL steps for the user. Base the conclusion on the script's `status` / `verdict` / `archive_verdict` / `recommendations` / `next_action` fields rather than re-deriving them. Never execute mount or configuration commands.

## Important Notes

- **Environment limitation, stated honestly**: the evaluation/runtime environment cannot perform a real mount; this skill's primary form is knowledge judgment plus read-only configuration checks (bucket region/storage class/endpoint match). Reports say so explicitly instead of pretending a mount was tested.
- **403 on a single file inside a working mount** is typically an unrestored Archive object, not a bucket-level permission gap - check `archive_verdict` before concluding permission problems.
- **Container mount 403**: separate the mount credential's RAM permission from the bucket's Bucket Policy - a same-account mount 403 is almost always the credential side (see M2).
- **Disappeared mountpoint** ("Transport endpoint is not connected"): the ossfs process has exited while the mount entry remains; the stale entry must be `fusermount -u`'d before remounting - guidance only.
- **Read-only operations**: only GetBucketInfo, ListBuckets, and `sts:GetCallerIdentity`; never modifies anything and never mounts.

## Examples

**Example 1 - ossfs mount failed on ECS (pre-mount check)**

> User: "My ECS in cn-hangzhou fails to mount bucket test-agentceping with ossfs. I configured oss-cn-hangzhou.aliyuncs.com. Account UID 1552974654746705."

```bash
python3 scripts/ossfs_mount_diagnosis.py --bucket test-agentceping \
    --endpoint oss-cn-hangzhou.aliyuncs.com --symptom "ossfs mount failed" --platform ecs
```

Report the `verdict` (endpoint region vs bucket location), the `archive_verdict` (storage class), the pre-flight checklist recommendations, and declare any auto-filled parameters. All remediation (credential file, chmod 640, remount) is output as manual guidance.

**Example 2 - container storage volume mount 403**

> User: "Mounting my bucket as an OSS storage volume in ACS fails with 403; network is fine and the AK works in ossutil."

```bash
python3 scripts/ossfs_mount_diagnosis.py --bucket <name> \
    --symptom "container storage volume mount 403" --platform acs
```

If `archive_verdict.at_risk` is true, lead with the archive direct-read path from [references/archive-direct-read.md](references/archive-direct-read.md); otherwise walk the M2 diagnosis order (credential account vs owner, RAM permission, Secret freshness, endpoint, subpath).

**Example 3 - mount directory disappeared**

> User: "The ossfs mount directory disappeared overnight; ls says Transport endpoint is not connected."

```bash
python3 scripts/ossfs_mount_diagnosis.py --bucket <name> \
    --symptom "Transport endpoint is not connected, mount directory disappeared"
```

Explain the stale-mount-entry / ossfs-process-exit attribution, give the evidence-collection guidance (debug log, dmesg/OOM check) and the manual fusermount/remount steps from M1 - without executing any of them.

<!-- production-pattern-example -->

**Example N - Files uploaded by SDK are invisible inside the mounted directory**

> User: "After mounting with ossfs2 I upload through the SDK, but the mounted folder stays empty for a very long time."

```bash
python3 scripts/ossfs_mount_diagnosis.py --bucket "my-bucket" --region "cn-hangzhou" --symptom "mounted directory does not show files uploaded by SDK"
```

Attribute it to metadata and negative caching plus close_to_open defaults rather than data loss, and give the mount-option change; never run a mount yourself.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/ossfs_mount_diagnosis.py` | Mount diagnosis entry: GetBucketInfo + endpoint match + archive direct-read verdict + symptom routing, with ListBuckets fallback |

CLI options for `ossfs_mount_diagnosis.py`: `--bucket <name>` (required), `--endpoint <endpoint>`, `--region <region>`, `--symptom <text>`, `--platform <ecs|ack|acs|docker|pai|local>` (all optional).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing `oss:GetBucketInfo`, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, run the ListBuckets fallback, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account - this is itself a classic mount-failure cause; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| "no such host" / DNS failure | Internal endpoint used outside the Alibaba Cloud network, or local DNS issue | Route with [references/ossfs-mount-knowledge.md](references/ossfs-mount-knowledge.md); suggest the public endpoint for off-cloud mount hosts |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the root cause with the actual evidence fields (bucket location, storage class, endpoint match, symptom category) - no fabricated values.
3. Declare every auto-filled parameter (endpoint default, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Give all remediation (credential fixes, chmod, archive direct read switch, fusermount/remount) as manual guidance only - this skill never executes mount or configuration commands, and says so honestly.
6. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."

