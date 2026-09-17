---
name: alibabacloud-oss-access-log-trace-diagnosis
description: |
  Read-only diagnosis of OSS request failures and access-log tracing from the
  customer's own log and configuration. Use when a request returns 403
  AccessDenied, 404 NoSuchKey, SignatureDoesNotMatch or an unexplained EC error
  code, when a bucket policy seems to deny a request that should be allowed,
  when anonymous access is rejected, when the customer asks who accessed or
  deleted an object, or when log enablement must be checked. Shows which policy
  statement matched, degrades to console statements when logs cannot be read,
  and states which causes need a ticket. Never changes configuration. Do NOT
  use for billing, traffic abuse, endpoint or transfer-acceleration errors.
  Triggers: "OSS 403 error diagnosis", "bucket policy denied my request",
  "SignatureDoesNotMatch", "presigned upload fails", "OSS EC error code lookup",
  "NoSuchKey diagnosis", "who accessed my files", "who deleted my object",
  "access log not enabled", "which IP accessed my bucket".
---

# OSS Access-Log Trace Diagnosis

Explain why an Alibaba Cloud OSS request failed, and trace who touched an object: "my file returns 403", "the bucket policy denies a request that should be allowed", "SignatureDoesNotMatch on a presigned URL", "NoSuchKey but the file was there", "what does this EC error code mean", "who accessed my files last night", "who deleted my object", "is realtime log enabled on my bucket", "I want to trace access but no log exists".

Core approach: confirm the scope, resolve the bucket's real region, probe whether the realtime access log is readable, trace the failing request, read the authorization configuration that governs it, then correlate the two to identify which statement matched — or state plainly which causes cannot be confirmed from the customer side. When the log cannot be read, degrade to deriving the log target and handing over ready-to-run console statements instead of reporting nothing.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write or execute any command calling a mutating operation — no change to a bucket ACL, a bucket policy, block public access, a referer list, a lifecycle rule, a logging configuration, a website configuration, an object ACL, or an object itself. This includes commands "for the user to run manually" that you execute on their behalf. Enabling realtime log query is console guidance only. Report findings and hand over guidance; the customer applies changes.
2. **CHANNEL WHITELIST:** OSS configuration reads go through the Python oss2 SDK (the aliyun CLI carries no OSS control-plane metadata and ossutil is not assumed to be installed). The caller-identity check, log reads and RAM reads go through the aliyun CLI. The permitted actions are exactly those listed in [references/ram-policies.md](references/ram-policies.md). Any other action is forbidden.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, store or pass an AccessKey pair or a security token. The SDK resolves credentials from the `ALIBABA_CLOUD_*` environment variables and the CLI from its own profile. Never accept credentials from the user, and never run a command that echoes them. **This extends to credential FILES and environment dumps: never read, open, `cat`, `head`, grep or otherwise inspect `~/.aliyun/config.json`, `~/.alibabacloud/credentials`, and never run `printenv` / `env` / `set` to view credentials -- NOT EVEN to debug an authentication error such as `InvalidSecurityToken` or `NoCredentials`. When a credential error occurs the ONLY permitted action is: record it, degrade honestly, and tell the user to refresh the credential (`aliyun configure` or re-assume the role). Opening a credential file to "fix" the error leaks secrets and is forbidden.
4. **NO FABRICATION — the honesty contract:** Every conclusion carries a verdict class (see Verdict Classes). A class C cause **MUST** be escalated, never inferred. A class B cause **MUST** be reported as ranked candidates with a verification step each, never as a single confident finding. When a log query could not be executed, say "no query was executed" — never word it as an empty log, and never conclude "no problem occurred". Do not upgrade a verdict because the customer sounds certain or because a cause looks plausible.
5. **CRITICAL — MANDATORY EXECUTION:** All diagnosis **MUST** run through `scripts/diagnose_access_log.py`. You are **STRICTLY FORBIDDEN** from hand-assembling log queries, ossutil commands, SDK snippets or curl calls, and from bypassing the script to call APIs directly — the script embeds region resolution, the mandatory topic filter, index-safe query shapes, timeout, retry, degradation logging and the verdict discipline that ad-hoc commands lack. If you hit an error, **DO NOT** attempt a manual workaround; the entry script handles recovery and reports what degraded.
6. **EXECUTION RULE FOR ERRORS:** On any failed read, record `[WARN] <category>: <message>` on stderr, add it to the Graceful Degradation Log, mark that evidence unavailable, and continue with the remaining evidence. Never silently skip a step and never abort without a report. The report is always emitted with `STATUS: OK` or `STATUS: DEGRADED` and a `NEXT_ACTION` line.
7. **SCOPE BOUNDARY:** This skill explains request failures and traces access from the customer's own log. It does **NOT** handle: billing or cost attribution; traffic-abuse or theft emergency mitigation (blocking IPs, disabling keys); endpoint resolution errors; transfer-acceleration error codes; event notification or upload callback faults; multipart upload tuning. For those, state the boundary and defer to the matching capability or the console.

## Official Doc Verification

MANDATORY for configuration and usage questions: invoke the entry script with `--question "<the customer's original wording>"`. The script first matches its embedded knowledge, then verifies against the official OSS help-center document index, and returns up to three candidate documents under `doc_verification.docs`.

The final answer **MUST** cite only URLs returned in `doc_verification.docs`. **Never fabricate a documentation URL** and never recall one from memory. When `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)." A routine run without `--question` issues no network request at all.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured report, interpret `status` / `verdict_class` / `conclusion` / `root_cause` / `recommendations` / `generated_queries`, and compose the answer; do not re-implement the queries. Reference modules are loaded on demand — read one only when the task needs it.

## Observability

All API calls issued by the scripts include:

- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id}/skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-access-log-trace-diagnosis`
- **session-id**: a 32-character hex string (`uuid.uuid4().hex`) generated once per run and attached to every OSS SDK request (User-Agent header) and every `--user-agent` argument of the aliyun CLI calls of that run, so all calls of one diagnosis can be correlated.
- **skill-version**: resolved from the `SKILL_VERSION` environment variable, else from the top-level `version` string of `references/manifest.json`. Version resolution is a **failure gate**: it runs on the path of every cloud call, so if no version can be resolved the run stops **before** the first Alibaba Cloud call rather than issuing an unversioned request.

One run produces exactly one session-id and one skill-version: the CLI layer delegates to the SDK client layer, so the two channels never emit different values. The session-id is printed to stderr and included in the report and in any ticket package.

## Prerequisites

1. **Python 3.9 or newer** with the pinned dependency in `scripts/requirements.txt` (`oss2>=2.19.0,<3`). No other third-party package is used.
2. **aliyun CLI >= 3.3.3** (plugin-ecosystem baseline; this skill uses plugin-mode kebab-case commands) — used for the caller-identity check, log reads and RAM reads. Install or upgrade per the official guide <https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli>: Homebrew `brew install aliyun-cli` then `brew upgrade aliyun-cli`; non-Homebrew installs `aliyun upgrade` (built-in one-click update, available since 3.3.5); or download the installer from that guide. Verify with `aliyun version`. When the CLI is absent the skill still runs: it reports the log channel as unavailable and degrades to generated console statements.
3. **Credentials** from the default chain (see Credentials). Never an AccessKey pair passed to the scripts.
4. **Read permissions** per [references/ram-policies.md](references/ram-policies.md). The log permission is an optional enhancement; without it the skill degrades rather than fails.

## Credentials

Credentials are resolved exclusively by the default credential chain:

- OSS configuration reads (oss2 SDK): the environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and optionally `ALIBABA_CLOUD_SECURITY_TOKEN` for STS sessions.
- Identity check, log reads and RAM reads (aliyun CLI): the CLI default credential chain (environment or `~/.aliyun/config.json`).

Do not read, print or pass an AccessKey pair or a security token explicitly. If the identity check fails, guide the user to run `aliyun configure` — never ask for credentials.

**Identity consistency:** the two chains must belong to the same account. The realtime log project name `oss-log-<uid>-<region>` is therefore derived from the bucket **owner** UID returned by the bucket information read (always consistent with the bucket); the caller UID serves only as the fallback and as a traceability label. A mismatch is logged as a `[WARN]` and declared.

```bash
cd $SKILL_DIR

# Optional standalone identity check (the entry script does this itself)
python3 scripts/sts_token.py
```

## User Confirmation

Because every action of this skill is strictly read-only, no confirmation is required before running the scripts. Confirmation discipline applies at the scope boundary instead: when a request requires a mutation (enabling logging through an API, changing an ACL, blocking an IP) or falls into another capability's scope per Absolute Rules 1 and 7, do not proceed with any mutation — state the boundary and give manual guidance only.

Before the first run, confirm the diagnosis scope with the user: which bucket, which region, and which failing request (request ID, object key, or error code). If no bucket was named, ask for it; never guess a bucket name, enumerate buckets to pick a candidate, or scan for one.

## Trigger Conditions

Trigger this skill when the user reports any of: an OSS request returning 403 AccessDenied; a bucket policy that appears to deny a request which should be allowed; SignatureDoesNotMatch on a header-signed or presigned request; 404 NoSuchKey or NoSuchBucket; an EC error code they want explained; anonymous access being rejected; an object that cannot be read although the bucket is public; a forced download instead of an inline preview; a form-upload policy rejected as expired; a request ID that needs tracing; who accessed, downloaded or deleted an object; which IP or AccessKey made requests; whether realtime log query or log delivery is enabled and how to enable it; or the "want to trace access but no log exists" blocker.

Do **not** trigger for: billing or cost attribution; traffic-abuse or theft emergency mitigation; endpoint resolution errors; transfer-acceleration error codes; event notification or upload callback faults; multipart upload tuning; creating, deleting or modifying buckets and objects; or general OSS best-practice consulting.

## Input Parameters

| Parameter | Required | Description |
|---|---|---|
| `--bucket` | Yes | Bucket name. Must come from the user; never guessed |
| `--region` | No | Expected region. The script resolves the bucket's **real** region itself and declares the source, because a wrong region makes the log project name wrong and surfaces as a misleading permission error |
| `--request-id` | No | Exact request ID — the most precise entry point; prefer it whenever available |
| `--ec` | No | EC error code, when taken from the error response body instead of the log |
| `--object` | No | Object key; traces that object's history and enables the object ACL read |
| `--ip` / `--status` / `--operation` / `--ak` | No | Filters embedded into the generated console statements |
| `--batch-delete` | No | Also query the batch-delete topic (a batch delete logs one request row only; the removed keys live in that topic) |
| `--concurrency` | No | Also scan concurrent writes to `--object` (version-conflict failures) |
| `--hours` | No | Look-back window, default 24, maximum 168 |
| `--uid` | No | Account UID; derived when omitted |
| `--ram-user` / `--role-name` | No | Enable the RAM explicit-Deny scan / read an assumed-role trust relationship |
| `--post-policy` | No | Base64 form-upload policy to decode and compare against the request time |
| `--question` | No | The customer's original wording, for runtime official-doc verification |
| `--exclude-cdn` | No | Exclude CDN back-to-origin rows from generated statements |
| `--format` / `--output` | No | `text` (default) or `json`; report file path |

**Auto-fill declaration requirement (MANDATORY):** whenever a parameter is filled in by you or by the script rather than given by the user, the final reply or the report **MUST** declare the item and its source — for example "UID auto-derived via the caller-identity check: 1234567890123456", "Region auto-resolved from the bucket itself: cn-hangzhou", "Log project derived from the naming rule: oss-log-…". The report carries these in `autofill_declarations` and in the `Information Sources (mandatory)` section. A scope statement is not a declaration. Auto-fill first, ask second; never fabricate a value.

## Module Index

Reference modules, strictly 1:1 with the `references/` directory. Load on demand.

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Log source | [references/module1_log_source.md](references/module1_log_source.md) | Realtime log versus log delivery, project naming, the three topics, field catalog, indexing, retention, billing, probe outcomes, why a row may be absent |
| M2: Request trace | [references/module2_request_trace.md](references/module2_request_trace.md) | Tracing modes, syntax constraints that change the answer, time windows, reading a traced row |
| M3: Error codes | [references/module3_error_codes.md](references/module3_error_codes.md) | EC code table with verdict classes, per-code diagnosis paths, forbidden conclusions |
| M4: Policy analysis | [references/module4_policy_analysis.md](references/module4_policy_analysis.md) | Evaluation order, bucket-policy grammar, condition-key whitelist, hit-analysis method, cross-account determination |
| M5: Escalation | [references/module5_escalation.md](references/module5_escalation.md) | Scope boundary, unverifiable evidence, ticket package, customer-facing wording and banned phrasing |
| M6: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only policy, mandatory versus optional statements, action-to-script mapping |
| M7: Query templates | [references/query-templates.md](references/query-templates.md) | The generated console statements, what each answers, and how to run them |

## Orchestration

One diagnosis run touches these services, always in this order, always read-only:

```
user confirms bucket + region + failing request
   |
   v
[1] STS  caller identity            -- derive the UID (never asked for)
   |
   v
[2] OSS  resolve the real region    -- GetBucketInfo, ListBuckets fallback
   |                                   (a wrong region looks like a permission
   |                                    error AND breaks the project name)
   v
[3] SLS  realtime log probe         -- readable? enabled? permitted? channel up?
   |                                   unusable -> degrade, do not guess
   v
[4] SLS  trace the request          -- by request ID, by EC, by object, batch
   |                                   delete topic, or the error distribution
   v
[5] OSS  authorization evidence     -- bucket info, ACL, policy, block public
   |                                   access; conditional: object ACL, referer
   |                                   lists, website docs, log shipping, RAM
   v
[6] rule engine                     -- EC code -> verdict class A / B / C
   |                                   A: conclude with verbatim evidence
   |                                   B: ranked candidates + verification steps
   |                                   C: escalate, no inference
   v
report: STATUS + conclusion / root cause / recommendations
        + matched statement + condition hit table
        + generated console statements
        + doc verification (when --question was given)
        + Information Sources (auto-filled parameters)
        + what was verified / what could NOT be verified
        + Graceful Degradation Log + NEXT_ACTION
```

## Execution Flow

### Step 1: Confirm scope, then go straight to the entry script

Confirm the bucket, the region and the failing request with the user. There is
no separate identity step: the entry script in Step 2 verifies the caller
identity and derives the UID itself. When the user already gave the UID, pass
`--uid <UID>` so the run does not depend on the identity call at all (this also
avoids a wasted round-trip when the CLI sts plugin is unavailable). Run
`scripts/sts_token.py` only when the user asks for a standalone identity check.

### Step 2: Run the diagnosis (single entry point)

```bash
cd $SKILL_DIR && python3 scripts/diagnose_access_log.py \
    --bucket <BUCKET> [--region <REGION>] [--request-id <ID>] [--ec <CODE>] \
    [--object <KEY>] [--ip <IP>] [--status <CODE>] [--operation <OP>] \
    [--batch-delete] [--hours 24] [--question "<customer wording>"] \
    [--output output/<BUCKET>-diagnosis.md]
```

The script performs region resolution, the log probe, the trace, the configuration reads, the correlation and the verdict assignment in one run, and always emits a report — including a report that states its own gaps.

**Run it once.** One invocation of the entry script produces the complete report, including every degraded step. Do not re-run it to "retry" a degraded read, do not re-read the reference modules to re-derive what the report already states, and do not call the supporting scripts to duplicate work the entry script already did. Interpret the single report and deliver. Re-running only repeats the same environment-limited failures and wastes turns.

Supporting scripts remain available for a focused re-run: `log_source_check.py` (probe only), `trace_request.py` (trace or `--generate-only` for statements without executing), `collect_config_evidence.py` (configuration evidence only).

### Step 3: Interpret and deliver

Read `status`, `verdict_class`, `conclusion`, `root_cause`, `recommendations`. State the verdict class in words. Quote the matched policy statement and the condition hit table verbatim when the finding is a configuration match. Relay the generated statements when the log could not be read. Build the customer-facing message per [references/module5_escalation.md](references/module5_escalation.md), including its banned-phrasing rules.

## Verdict Classes

The discipline that keeps this skill honest. Definitions and per-code assignments are in [references/module3_error_codes.md](references/module3_error_codes.md).

| Class | Evidence situation | What the report may claim |
|---|---|---|
| **A** | Provable from the customer's own log and configuration | One conclusion, with the matching evidence quoted verbatim |
| **B** | Narrowed to a few candidates; confirmation needs customer input or an action | Ranked candidates, each with its verification step, plus what could not be checked |
| **C** | Decisive evidence is service-side only | Escalation with a ticket package, plus an explicit statement of what could not be verified |

Two automatic downgrades are enforced in code, because both are ways a confident answer gets fabricated:

1. No logged request row was available → an A verdict becomes B.
2. The error code is normally decided from logged request attributes and the log channel was unusable → an A verdict becomes B.

The report records the downgrade reason in `verdict_downgraded`.

Class C exists because the server-side log carrying the string-to-sign and the precise denial message, the sandbox state of a bucket, throttling records and compliance records are not reachable through any customer-facing API. A signature mismatch can therefore be narrowed but not pinpointed from the customer side.

## Report Delivery

1. Write the full report to a file with `--output output/<bucket>-diagnosis.md`.
2. In the conversation, reply with the file link, the `STATUS` value, the verdict class in words, and one key conclusion. Do not paste full tables into the chat.
3. Present results as tables inside the report; never paste a raw API response.
4. A field obtained from more than one source appears once.
5. The customer-facing message goes in the conversation body, **not** into the report file, so it can be copied directly.

## Final Answer Contract

The final answer to the user MUST:

1. Relay the report's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line in meaning.
2. State the conclusion, the root cause and the verdict class **in words** — never as a bare letter, and never as raw JSON.
3. Quote the matched policy statement and the per-condition comparison verbatim when the finding is a configuration match.
4. When no log query could be executed, say so plainly and hand over the generated console statements with the project, logstore, region and time-window guidance. Never word an unexecuted query as an empty log. When realtime log query is not enabled, or the queried window returned no rows, the answer **MUST** state that realtime logs are **not retroactive** -- they capture only requests made after enablement, so a past window cannot be recovered -- and point to log delivery (for offline history) and ActionTrail (for management-plane history).
5. Declare every auto-filled parameter (UID derivation, region resolution, log project derivation, defaulted window) with its source.
6. List what was verified and what could **not** be verified. On `DEGRADED`, list the recorded errors instead of inventing conclusions. **ABSOLUTE anti-fabrication (weak-model guard):** any configuration item the report renders as `UNAVAILABLE` / `unavailable` / `[WARN] ... unavailable` -- bucket ACL, block-public-access, policy statement count, region, creation time, versioning, object ACL -- **MUST** be relayed as "could not be verified". You are **FORBIDDEN** to state a concrete value for an item whose read failed: never write "ACL is private", "block public access is on", "no policy configured", or "created on <date>" when that read returned unavailable. A failed read means *unknown*, not a value; the script already renders `UNAVAILABLE (not verified)` for exactly this reason, so relay that marker verbatim. Do not "reason out" a likely configuration to fill the gap. **Bucket existence and region are the special case that matters most:** when the bucket read itself failed (`NoCredentials`, `AccessDenied`, a timeout, or any other error), the answer **MUST** state that the bucket was `not found` in any successful read and could not be located or verified, and **MUST** add in the same breath that this does **not** establish that the bucket does not exist. Keep the literal marker `not found` in that sentence whatever language the rest of the answer is written in. Never upgrade a failed read into `NoSuchBucket`, and never assert the bucket exists either.
7. When the customer supplied an EC code, error code or error description in their message but the log query could not be executed (verdict downgraded to B), the final answer **MUST** still present the ranked candidates from [references/module3_error_codes.md](references/module3_error_codes.md) for that EC — preceded by the honest caveat that no log row was read, so the candidates are knowledge-based rather than evidence-based. This ensures the customer receives actionable troubleshooting directions even when the automated pipeline degraded. Never suppress all analysis just because the rule engine was not reached.
8. When `doc_verification` is present, cite only the titles and URLs from `doc_verification.docs`; when its `note` starts with `DEGRADED`, state that online official docs could not be verified.
9. State that the run was read-only and changed nothing.
10. When the request concerns deletion (who deleted an object, objects that disappeared, or a `--batch-delete` run), the answer **MUST** use these canonical spellings verbatim: `batch delete` (two words) for the operation, `oss_batch_delete_log` for the topic that holds the removed keys, and `request_id` for the field that joins that topic to the access-topic row. Do not write them as `batch-delete` or `requester_id` -- `requester_id` is a different field (the caller), and a hyphenated form makes the handover ambiguous. Also name lifecycle expiry (`ExpireObject`) as the other deletion source the customer must rule out. State this deletion model even when no log row could be read: it is domain knowledge about where the evidence lives, not a claim about who deleted anything.

**MANDATORY OUTPUT VERIFICATION:** before replying, you **MUST** confirm the output contains all of: `STATUS`, the conclusion, the root cause (or ranked candidates when verdict is B), the verdict class in words, the recommendations, `NEXT_ACTION`, the auto-fill declarations, and the two lists (verified / could not verify). If any part is missing, you **MUST** explicitly append it. Never present raw JSON to the user. Never omit ranked candidates for a class-B verdict even when the rule engine did not run. **Before sending, re-scan your own answer: every configuration value you state MUST appear as a verified value in the script output; if the script marked it `UNAVAILABLE`, delete your stated value and replace it with "could not be verified". Also confirm no credential file was read and no secret appears anywhere in the answer.** **Two token checks before sending:** if any bucket read failed, the answer must contain the literal `not found` together with the non-existence disclaimer; if the request concerns deletion, it must contain `batch delete`, `oss_batch_delete_log` and `request_id` spelled exactly so.

## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify the caller identity and derive the UID needed for the log project name |
| `scripts/log_source_check.py` | Probe whether the realtime access log is readable, enabled and producing rows; report the log-shipping fallback and the five probe outcomes |
| `scripts/trace_request.py` | Trace one request by ID, one object's history, the batch-delete topic, or the error distribution; `--generate-only` produces console statements without executing anything |
| `scripts/collect_config_evidence.py` | Collect bucket, object and RAM authorization evidence and correlate it into plain findings |
| `scripts/diagnose_access_log.py` | **Mandatory entry point**: orchestrate the six steps, run the rule engine, emit the report |

Shared modules, not run directly:

| Module | Responsibility |
|---|---|
| `scripts/_constants.py` | Field catalog, topic names, log-store and retention facts, policy grammar, escalation thresholds, the A/B/C verdict classes, documentation sources |
| `scripts/_ec_knowledge.py` | EC error-code knowledge base: 19 documented codes, each with its verdict class, the evidence to collect and the public documentation link |
| `scripts/_oss_client.py` | oss2 SDK channel, structured error categories, region resolution with the bucket-listing fallback, caller identity |
| `scripts/_cli.py` | aliyun CLI channel for the log and RAM reads, retry with backoff, channel-availability guard |
| `scripts/_policy_hit.py` | Statement matching (action / resource / principal / condition), CIDR matching, cross-account determination, bucket-name and form-upload-policy derivation |
| `scripts/_rule_common.py` | Shared rule scaffolding: the logged-attribute view, the verdict-C rule and the support-ticket package |
| `scripts/_rules_authz.py` | Authorization rules: bucket-policy hit analysis, anonymous access refused, object ACL, RAM explicit Deny |
| `scripts/_rules_resource.py` | Resource rules: bucket naming and existence, object existence, forced download, image source validation |
| `scripts/_rules_signature.py` | Signature rules: signature mismatch, clock skew, form-upload expiry, concurrent-write contention |
| `scripts/_rules.py` | EC resolution and the diagnosis-kind dispatch table; the facade over the rule modules above |
| `scripts/_report.py` | Report rendering and the machine-consumable summary fields |
| `scripts/_doc_lookup.py` | Runtime official-documentation verification against the help-center index |

The rule layer is split by concern so that no module carries more than one kind
of logic, and `_rules.py` is the only rule-layer module the entry script imports.

Every script accepts `--json` where applicable. Inline boundary assertions run with `--self-test` on `diagnose_access_log.py` (which delegates to `_rules` and `_report`), on `_rules.py` (covering every rule module and the ticket package), on `_report.py`, on `_constants.py` and on `_oss_client.py`.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| oss2 SDK not installed | Missing dependency | Install from `scripts/requirements.txt`; report `STATUS: DEGRADED` |
| aliyun CLI not found | CLI missing from the host | Not fatal: the log channel is reported unavailable and the skill degrades to generated console statements |
| No credentials found | Default credential chain not configured | Run `aliyun configure` or export the `ALIBABA_CLOUD_*` variables of an assumed-role session; never ask for an AccessKey pair |
| `AccessDenied` on a bucket read | Missing permission, another account's bucket, **or a wrong-region endpoint** (measured: wrong-region access also reports "does not belong to you") | Region resolution runs first and falls back to the bucket listing; record `[WARN]`, mark the evidence unavailable, continue |
| `NoSuchBucket` | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| Bucket policy read returns "not configured" | No policy exists | A valid finding, **not** a permission failure — report it as such |
| Log project does not exist | Realtime log query not enabled | State that logs are not retroactive; give the console path; report the log-shipping state |
| Log read denied | Missing log read permission | Degrade to generated statements; point to [references/ram-policies.md](references/ram-policies.md) |
| Log query returns no row | Wrong region, narrow window, encoded key, logging off, or one of the four documented absence causes | Widen `--hours`, verify the region, compare the encoded key form, quote the absence causes; never report "no problem" |
| `Throttling` / 5xx / timeout | Transient | Retried automatically with backoff (up to 3 attempts), then `[WARN]` and continue |
| A rule raised an unexpected error | A defect in one rule | Recorded, the "not covered by the knowledge base" answer is used instead, and the report is still emitted |

All errors follow a structured `category / code / message / hint` shape recorded in the report; every degraded step logs `[WARN]` on stderr.

## Important Notes

- **Region first, always.** The log project name embeds the region. Deriving it from an unverified `--region` makes a wrong region look exactly like "realtime logging is not enabled".
- **Three topics, not one.** The logstore carries access rows, batch-delete rows and hourly metering rows. Every query pins `__topic__`; without it, aggregations silently mix kinds. A batch delete logs **one** request row in the access topic while the removed keys live in the batch-delete topic, joined by `request_id`.
- **The logstore index cannot be modified.** Do not tell the customer to add an index; move the predicate into the SQL part instead.
- **Object keys are URL encoded** in the log, so matching uses `url_decode(object)`.
- **`NoSuchBucketPolicy` is a finding, not a failure.** Reporting it as a permission denial is the most common misdiagnosis in this domain.
- **An absent row is not an absent request.** Four documented causes exist (CDN cache hit, client-side interruption, log push loss, cross-region endpoint); quote them instead of concluding "no such request happened".
- **CDN back-to-origin rows** carry the CDN node IP, not the end user; exclude them when tracing end users, and if every row is CDN, the question belongs to the CDN side.
- **Data plane only.** Management-plane events (who changed a RAM policy, an ACL or any bucket configuration) are in ActionTrail, not in this log.
- **Account scope:** results describe the account behind the configured credential. An empty result under an assumed role or a cross-account credential does not prove the absence of a problem elsewhere.
- **Privacy:** never characterise the customer's data from an object key. Keys are the customer's own naming; drawing conclusions about file contents from a path is unreliable and a privacy violation.
- **Read-only:** only the whitelisted read actions are ever issued. Nothing is modified, deleted or reconfigured.

## Examples

**Example 1 — a 403 with a request ID**

> User: "GetObject on bucket example-bucket in cn-hangzhou returns 403 AccessDenied, EC 0003-00000101, request ID 65A1B2C3D4E5F6G7H8I9J0K1."

```bash
python3 scripts/diagnose_access_log.py --bucket example-bucket \
    --region cn-hangzhou --request-id 65A1B2C3D4E5F6G7H8I9J0K1 \
    --question "GetObject returns 403 AccessDenied with EC 0003-00000101, which bucket policy rule matched?" \
    --output output/example-bucket-diagnosis.md
```

Report `STATUS`, the EC code, the matched statement verbatim, the condition hit table (expected versus actual per condition), the fix, and any doc URLs returned by the verification. Declare every auto-filled parameter.

**Example 2 — who accessed or deleted an object, and no log exists**

> User: "I want to know who deleted images/report.png in bucket example-bucket last week, but I think access log is not enabled."

```bash
python3 scripts/diagnose_access_log.py --bucket example-bucket \
    --object images/report.png --batch-delete --hours 168
```

Explain the no-log blocker honestly: logs are not retroactive, so the past window cannot be recovered. Give the console paths to verify and enable realtime log query, hand over the generated object-history and batch-delete statements for future use, and mention ActionTrail for management-plane history.

**Example 3 — an object that cannot be read although the bucket is public**

> User: "Bucket example-bucket is public-read but images/a.png returns 403."

```bash
python3 scripts/diagnose_access_log.py --bucket example-bucket \
    --region cn-hangzhou --object images/a.png --hours 72
```

The object ACL read is enabled automatically for this branch. If the object ACL is `private` while the bucket is public, that is a class A conclusion with a fix the customer applies. If the object ACL does not explain it, the verdict is class C: escalate with the ticket package and state that a platform-side block cannot be verified from the customer side — do not invent a third cause.
