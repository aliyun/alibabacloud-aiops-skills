---
name: alibabacloud-oss-crr-config-check
description: |
  Read-only OSS cross-region replication (CRR) configuration checks. Verify a
  replication rule and explain why replication is not starting; never creates or
  modifies a rule. Covers whether a bucket has any replication rule configured
  before it is relied on for DR, the authorization role, prefix scope,
  delete-marker and historical-data sync switches, and cold archive or
  cross-border transfer-acceleration mis-configurations. Also use for a
  replication investigation plan before execution. Triggers:
  "cross-region replication not starting", "replication rule config error",
  "AliyunOSSRole authorization", "replication delete marker sync",
  "verify whether a bucket has cross-region replication configured",
  "rely on replication for DR", "replication investigation plan",
  "replication check", "cold archive replication",
  "transfer acceleration not enabled for cross-region replication",
  "replication slow", "replication capacity".
---

# OSS Cross-Region Replication Config Check

Check Alibaba Cloud OSS cross-region replication (CRR) configuration and explain why data is or is not being replicated: "I set up cross-region replication but no files appear in the target bucket", "replication shows only a rule ID and never starts", "does my replication rule sync deletes", "which authorization role does replication need".

Core approach: verify the caller identity, fetch the bucket's storage class and region with the read-only GetBucketInfo control-plane query, then read the bucket's replication rule with the read-only GetBucketReplication query. When no rule exists, report the legitimate "replication not configured" finding; when a rule exists, inspect its authorization role, prefix scope, delete-sync switch, historical-data switch, and transfer-acceleration dependency, and attribute "replication not starting" to a concrete configuration cause. Conclude with evidence-based findings and manual guidance only; this skill never creates, modifies, or deletes any replication rule.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API — e.g. `PutBucketReplication`, `DeleteBucketReplication`, `PutBucket*`, `DeleteBucket*`, `PutObject*`, or any replication-rule / ACL / policy change. This includes commands "for the user to run on your behalf". If the user asks to create or change a replication rule, only output manual guidance and declare this skill is read-only. **Empty / not-found is a valid result — never react to it with a write.** When `GetBucketReplication` returns no rule, the bucket is not found, `target_verification.verdict` is `target_unreachable`, or every query returns empty, that is already a complete conclusion: relay it and STOP. Never issue a create / re-create / verify / test / validate / repair call to "confirm" an empty result, and never fall back to hand-written `ossutil`, SDK, or `aliyun` commands for the same purpose.
2. **MANDATORY entry-point enforcement:** All CRR checks MUST be performed by running the scripts under `scripts/` (`crr_config_check.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts — the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries. This mandate is UNCONDITIONAL: it also covers a request that names no bucket, no region, or only a consultation question (e.g. online migration vs cross-region replication selection). You MUST still run `crr_config_check.py` — with no `--bucket` it exits `STATUS: FAIL` whose `NEXT_ACTION` names the missing input and whose `buckets_in_account` lists up to 30 buckets visible to the current credential, and that output is exactly what to put back to the customer. NEVER answer a replication question from memory alone and NEVER guess a bucket name. A missing-input `STATUS: FAIL` is **NOT** a terminal conclusion: relay it **and** ask the customer for the missing input exactly as `NEXT_ACTION` directs, then re-run the script with the answer — Rule 1's "relay it and STOP" applies only to a result obtained for a bucket the customer actually named.
3. **ABSOLUTE PROHIBITION (consultation questions):** Even when the user asks a consultation question — e.g. "online migration vs cross-region replication", "does ACL affect replication", "which data volume needs which approach" — without naming a specific bucket, you MUST still run `scripts/crr_config_check.py` (without `--bucket` it exits `STATUS: FAIL` whose `NEXT_ACTION` names the missing input and whose `buckets_in_account` lists visible buckets). NEVER answer a replication or migration question from memory alone. The script output is the only sanctioned evidence base.
4. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
5. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketReplication / GetBucketInfo / ListBuckets / GetCallerIdentity. If a query fails or returns empty, record it and state the limitation — never invent replication rules, statuses, or role names.
6. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line — never silently skip or abort without a report.
7. **SCOPE BOUNDARY:** This skill only answers replication configuration correctness and "why is replication not running" attribution questions. It does NOT handle billing disputes (defer to the billing skill), deleted-object recovery (defer to the deletion-recovery skill), endpoint / internal-network access errors (defer to the endpoint skill), or generic cross-account RAM authorization design (defer to the cross-account-auth skill) — for such requests, state the boundary and give manual guidance only.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." **ABSOLUTE PROHIBITION — NO URL FABRICATION:** Every official URL in the final answer must be copied verbatim from a source this skill itself produces or documents — `doc_verification.docs`, the links inside `region_migration_guidance` (emitted when the verdict is `no_replication_configured`), or the official URLs already listed in this skill's `references/` modules. When the customer's question is not covered by any of those, say that it is unverified. **When doc_verification.note starts with DEGRADED, you MUST state "Unable to verify against online official docs (offline)" and MUST NOT supply any URL from memory — this is a hard prohibition, not a suggestion.**

## Trigger Conditions

Use this skill when the customer's own wording matches one of these phrases (the list the `description` advertises, plus wording variants and their Chinese equivalents):

- "cross-region replication not starting" / "跨区域复制不生效"
- "replication rule config error" / "复制规则配置错误"
- "AliyunOSSRole authorization" / "跨区域复制授权"
- "replication delete marker sync" / "删除标记同步"
- "confirm the replication delete marker sync behavior" / "确认删除是否同步到目标桶"
- "verify whether a bucket has cross-region replication configured" / "有没有配置跨区域复制规则"
- "verify whether bucket has any cross-region replication" / "检查桶是否配置了跨区域复制"
- "rely on replication for DR" / "跨地域容灾"
- "replication investigation plan" / "跨区域复制排查方案"
- "replication check" / "复制检查"
- "cold archive replication" / "冷归档复制"
- "transfer acceleration not enabled for cross-region replication" / "传输加速未开启"
- "replication slow" / "复制慢" / "复制延迟"
- "replication capacity" / "复制容量"

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| generic cross-account authorization | `alibabacloud-oss-cross-account-auth-diagnosis` |
| deleted-object recovery | `alibabacloud-oss-deletion-recovery-diagnosis` |
| billing | `alibabacloud-oss-billing-diagnosis` |
| endpoint access | `alibabacloud-oss-endpoint-internal-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

## Execution Principle

All checks MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `verdict` / `findings` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly. This applies to every request, including one that names no bucket or only asks a consultation question — run the entry script and answer from its output, never from memory (see Absolute Rule 2).

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-crr-config-check`
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every OSS SDK request (User-Agent header) and every `--user-agent` argument of the aliyun CLI identity call of that run, so all calls of one check can be correlated.

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

Because every action of this skill is strictly read-only, no user confirmation is required before running the check scripts. Confirmation discipline applies at the scope boundary instead: when a request falls outside replication configuration correctness / attribution (billing disputes, deleted-object recovery, endpoint access errors, generic cross-account authorization design per Absolute Rule 6), do not proceed with any check — state the boundary and give manual guidance only. If the user asks to create or modify a replication rule, refuse the mutation and give manual guidance.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/crr_config_check.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: Replication rules | CRR field semantics, official limits (cold archive / transfer acceleration / versioning), authorization-role trust-policy vs RAM-policy attribution |
| M2: Diagnosis tree | "Replication not starting" routing: historical-data switch / role authorization / prefix scope / already-replicated objects |
| M3: RAM policies | Minimal read-only RAM policy required by this skill |

Documented run order: Step 1: Confirm Identity and Collect Inputs; Step 2: Run the CRR Config Check; Step 3: Interpret the Verdict and Advise; Step 4: Conclusion and Suggestions.

## Input Parameters

- **Bucket name** (`--bucket`): the source OSS bucket whose replication configuration to check. Needed to inspect a rule, but NEVER guess it: when the customer has not named one, run the script with `--bucket` omitted — it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and a `buckets_in_account` list — and relay that instead of inventing a bucket name.
- **User endpoint** (`--endpoint`): optional; the endpoint the user currently uses to reach the bucket (e.g. `oss-cn-hangzhou.aliyuncs.com`). When provided it is used to derive the control-plane query endpoint.
- **Expected region** (`--region`): optional; used to derive the query endpoint when `--endpoint` is absent.
- **Customer symptom** (`--symptom`): optional; the customer's original symptom wording (Chinese or English). The embedded symptom-routing table maps it to a concrete branch — progress-stuck / target-empty / not-syncing / rule-not-effective / slow-replication / replication-failed / cross-account-auth / region-decommission / region-migration. When it matches, the report carries `symptom_routing` and the `NEXT_ACTION` is prefixed with the matched branch guidance (and a cross-skill `referral` when the symptom belongs to a sibling skill). Purely advisory: it never changes which OSS calls are made.
- **Verify target** (`--verify-target`): optional flag; when set (and a replication rule exists) the script performs a bounded read-only source-vs-target object count under the rule prefix (`ListObjectsV2`, `oss:ListObjects`) and reports `target_verification` with `verdict` = match / mismatch / target_unreachable / truncated. A cross-account target that cannot be listed is reported as the LIMIT `target_unreachable`, not an error. This is a spot-check PATH only — it never promises full integrity.
- **UID**: can always be omitted — it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: every auto-filled parameter (query endpoint defaulted, UID derived) and every input the customer never named MUST be declared on the `PARAMETER SOURCE:` line of the final answer — see the Final Answer Contract, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --endpoint/--region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Replication rules | [references/replication-rules.md](references/replication-rules.md) | CRR field semantics, official limits (cold archive / transfer acceleration / versioning), authorization-role trust-policy vs RAM-policy attribution |
| M2: Diagnosis tree | [references/diagnosis-tree.md](references/diagnosis-tree.md) | "Replication not starting" routing: historical-data switch / role authorization / prefix scope / already-replicated objects |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the source bucket name and, if the user has it, the endpoint/region. If the user reports a symptom, map it first with [references/diagnosis-tree.md](references/diagnosis-tree.md).

### Step 2: Run the CRR Config Check

```bash
cd $SKILL_DIR && python3 scripts/crr_config_check.py \
    --bucket <name> [--endpoint <user-endpoint>] [--region <region>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK to read storage class and location, carrying the session-id User-Agent and a per-call timeout.
3. Calls OSS `GetBucketReplication`; a 404 `NoSuchReplicationConfiguration` is treated as the legitimate "replication not configured" finding, not an error.
4. When a rule exists, calls the read-only `GetBucketReplicationProgress` and reports `replication_progress` (historical-backlog % vs new-object watermark) plus `runtime_semantics`; under `--verify-target` it also runs a bounded read-only source-vs-target object count (`ListObjectsV2`) into `target_verification`. Both degrade to `[WARN]` on failure and never block the report.
5. On any other failure, falls back where possible and logs `[WARN]` for every degraded step.
6. Emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`; when `--symptom` matched, `symptom_routing` guidance prefixes `NEXT_ACTION`.

### Step 3: Interpret the Verdict and Advise

Read `verdict.result` and `findings` from the report:
- **no_replication_configured** — the bucket has no replication rule: if replication is intended, give manual guidance only — tell the user to create a rule via the OSS console and authorize a RAM role such as `AliyunOSSRole` whose trust policy allows `oss.aliyuncs.com`. NEVER call any write API to create the rule on the user's behalf.
- **replication_configured / replication_starting / replication_closing** — a rule exists; relay the findings: delete-sync switch, historical-data switch (the most common cause of "replication not starting"), prefix scope, and transfer-acceleration dependency for cross-border pairs.
- **DEGRADED report** — relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent the rule or its status.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual fields from the report. Base the conclusion on the script's `status` / `verdict` / `findings` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any change).

## Important Notes

- **"Replication not starting" is almost always the historical-data switch**: a rule with historical-data sync disabled replicates only objects written after the rule was created; pre-existing objects never sync. Check this first.
- **Consultation questions still require the script**: when the user asks "online migration vs cross-region replication" or "does ACL affect replication" without naming a bucket, you MUST still run `crr_config_check.py` (without `--bucket`). The script's `STATUS: FAIL` output with `NEXT_ACTION` and `buckets_in_account` is the correct response — relay it to the user together with the bucket-name question that `NEXT_ACTION` asks, then re-run the script once the customer answers. Never answer from memory.
- **Incomplete information — explicit acknowledgment required**: when the user provides partial input (e.g. UID only, no bucket name; or a symptom with no locatable resource), you MUST explicitly state in your output that key information is missing (e.g. "bucket name not specified", "信息不足", "missing: bucket name"). Then either (a) ask the user for the missing information, or (b) run the script without `--bucket` to auto-discover visible buckets and proceed. After receiving the missing information (via user reply or HITL answer), continue the diagnosis and declare the information source on the `PARAMETER SOURCE:` line. Never silently skip the acknowledgment of what was missing.
- **Empty / not-found is a valid result — never react to it with a write or improvisation.** If no replication rule exists, no bucket is found, or all queries return empty *for a bucket the customer actually named*, that is a complete and valid conclusion: report it honestly and STOP. Do not attempt to create, verify, test, or repair any resource, and never fall back to hand-written CLI commands. Stay within the read-only script flow at all times.
- **Already-replicated objects are not re-replicated**: OSS does not replicate objects that were themselves produced by another replication task, so cascading chains (A→B→C) do not propagate the second hop.
- **ColdArchive / DeepColdArchive objects are never replicated**, whether or not they are restored. Cross-border (mainland ↔ non-mainland) replication MUST enable transfer acceleration.
- **Authorization attribution**: a NoPermission during replication with an extra STS RequestId in the server-log points to the role trust policy (Principal.Service must include `oss.aliyuncs.com`); no STS RequestId points to the RAM policy missing the action. See [references/replication-rules.md](references/replication-rules.md).
- **Replication does NOT thaw or charge retrieval fees**: copying IA / Archive objects that are already restorable does not trigger a restore and does not incur a data-retrieval fee; ColdArchive / DeepColdArchive objects are not replicated at all. CRR traffic and the RTC feature are billed to the SOURCE account. See `report.cost_ownership` and [references/replication-rules.md](references/replication-rules.md) §5.7.
- **"Replication is slow" is a capacity limit, not a config defect**: compare the load against the RTC bandwidth/QPS ceilings (`report.rtc_capacity`, [references/replication-rules.md](references/replication-rules.md) §5.5) — mainland region-pair 10 Gbps / 10,000 QPS, single mainland region 20 Gbps / 20,000 QPS, non-mainland pair 2 Gbps / 5,000 QPS, single non-mainland region 4 Gbps / 10,000 QPS; the SEQUENTIAL-write QPS cap is 2,000 for every scope. Avoid sequential prefix file names for large uploads; higher limits need a ticket. **When the customer reports slow replication or the symptom routing matches `slow_replication`, the final answer MUST explicitly cite these RTC bandwidth/QPS ceiling numbers and the sequential-write 2,000 QPS cap so the customer has a concrete capacity-planning basis.**
- **Prefix scope per rule is capped at 10**: a replication rule's PrefixSet holds at most 10 prefixes; the script flags a rule that reports more than 10 as exceeding the official per-rule limit.
- **Read-only operations**: only GetBucketReplication, GetBucketReplicationProgress, GetBucketInfo, ListBuckets, ListObjectsV2 (under `--verify-target`), and `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 — replication not starting (no rule or historical-data off)**

> User: "I set up cross-region replication on bucket test-agentceping but no files show up in the target bucket after a day. Account UID is 1552974654746705."

```bash
python3 scripts/crr_config_check.py --bucket test-agentceping
```

Report the `verdict.result`. If `no_replication_configured`, explain no rule exists and give creation guidance; if a rule exists with historical-data disabled, flag it as the cause. Declare any auto-filled parameters. If the report is `STATUS: DEGRADED`, relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 — replication rule config error / delete-marker sync**

> User: "Please check my replication rule on bucket src-bucket: I need deletes to sync to the target too, and I want to know the prefix scope."

```bash
python3 scripts/crr_config_check.py --bucket src-bucket --region cn-hangzhou
```

Read the findings for the delete-sync switch and prefix scope; if the user needs deletes replicated, tell them they must enable delete-marker sync themselves via the console — this skill is read-only and NEVER enables anything on the user's behalf.

**Example 3 — AliyunOSSRole authorization / NoPermission**

> User: "Configuring cross-region replication returns NoPermission. My role is AliyunOSSRole."

```bash
python3 scripts/crr_config_check.py --bucket src-bucket
```

Use [references/replication-rules.md](references/replication-rules.md) to attribute by the server-log (STS RequestId present → trust policy; absent → RAM policy) and give the `oss.aliyuncs.com` trust-policy template as manual guidance.

<!-- production-pattern-example -->

**Example N — Cold-archive objects never appear in the replica bucket**

> User: "Replication is enabled and the rule shows no error, but the cold archive objects are missing on the target side."

```bash
python3 scripts/crr_config_check.py --bucket "source-bucket" --region "cn-hangzhou"
```

Report the rule inventory and whether the objects' storage class is replicable at all; if historical-data sync is off, say only new writes will replicate.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/crr_config_check.py` | CRR config check entry: GetBucketInfo + GetBucketReplication + rule inspection, with ListBuckets fallback |

CLI options for `crr_config_check.py`: `--bucket <name>` (required), `--endpoint <endpoint>` (optional), `--region <region>` (optional, derives the query endpoint when `--endpoint` is absent), `--question "<customer original wording>"` (optional, drives the official-doc verification leg), `--symptom "<customer symptom wording>"` (optional, activates the embedded symptom-routing table), `--verify-target` (optional flag, bounded read-only source-vs-target object count when a rule exists).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing `oss:GetBucketReplication` / `oss:GetBucketInfo`, or bucket owned by another account | Record `[WARN]`, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| `NoSuchReplicationConfiguration` / 404 | No replication rule on the bucket | This is a valid finding, not an error: report `STATUS: OK` with `verdict=no_replication_configured` and give creation guidance |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

**MANDATORY OUTPUT FORMAT.** The final answer MUST be self-contained in the reply
itself: saving the conclusion into a file under `outputs/` and replying with a pointer
to that file is NOT a final answer. Every final answer MUST contain these lines:

1. `STATUS:` the script's `STATUS:` (`OK` / `DEGRADED` / `FAIL`) and its `NEXT_ACTION:`
   line, relayed verbatim in meaning. `NEXT_ACTION` MUST NEVER be dropped, not even when
   the answer is long or the diagnosis already looks conclusive.
2. `FINDING:` the verdict plus the evidence fields behind it (replication verdict, rule
   fields, storage class, bucket location) — no fabricated values.
3. `PARAMETER SOURCE:` one entry for EACH key input — bucket, region / query endpoint,
   UID, symptom or question — labelled `provided by customer`, `auto-filled from
   <source>`, or `missing: <what the customer still has to supply>`. This covers every
   value the script defaulted or derived (query endpoint, UID from
   `aliyun sts get-caller-identity`) AND every input the customer never named. State it;
   do not silently pick a value and do not stop to interrogate the customer for inputs
   the script already resolved.
4. `READ-ONLY:` a declaration that this check is read-only and nothing was created,
   modified, or deleted.
5. On `DEGRADED`, the recorded errors and limitations stated explicitly instead of
   inventing conclusions.
6. Configuration-change suggestions as manual guidance only (this skill never creates,
   modifies, or deletes replication rules).
7. When the report carries `doc_verification`, the doc titles and URLs from
   `doc_verification.docs`; when `doc_verification.note` starts with `DEGRADED`, the
   explicit sentence "Unable to verify against online official docs (offline)".
   **This is mandatory whenever `--question` was passed to the script**: the final
   answer MUST contain either the `doc_verification` field reference or the
   `help.aliyun.com` URLs from `doc_verification.docs`. Never omit the
   doc-verification result when the script produced one.

**MANDATORY POST-OUTPUT VERIFICATION.** Before sending, you MUST re-read your own draft
and confirm items 1-4 are all present; if any is missing, you MUST append it before
presenting. Never present raw script JSON, a bare file path, or a partial answer as the
final report.

