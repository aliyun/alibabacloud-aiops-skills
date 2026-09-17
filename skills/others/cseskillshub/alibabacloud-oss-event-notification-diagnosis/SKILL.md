---
name: alibabacloud-oss-event-notification-diagnosis
description: |
  Read-only OSS event notification and upload callback diagnostics. Use
  when event notifications do not trigger (rule configuration check,
  dependent service activation, event type matching) or upload callbacks
  fail (CallbackFailed, callback 502, 5-second response limit, certificate
  and network issues), plus configuration-correctness advice. Triggers:
  "event notification not triggering", "upload callback failed",
  "CallbackFailed error", "callback 502", "callback timeout 5 seconds",
  "OSS event to MNS", "x-oss-event-status". Only checks and advises;
  never creates or modifies notification rules. Do NOT use for
  access-log tracing (use
  alibabacloud-oss-access-log-trace-diagnosis), error codes (use
  alibabacloud-oss-transfer-error-code-diagnosis), endpoint issues (use
  alibabacloud-oss-endpoint-internal-diagnosis), or billing (use
  alibabacloud-oss-billing-diagnosis).
---

# OSS Event Notification & Upload Callback Diagnosis

Diagnose Alibaba Cloud OSS event-notification and upload-callback problems: "I configured an event notification rule but no message ever arrives", "my uploads return 203 CallbackFailed with Error status 502", "the callback server never receives the request", "does my bucket have any notification rule configured".

Core approach: verify the caller identity, confirm the bucket exists and locate its region with the read-only GetBucketInfo query, read the bucket's event-notification rules (GetBucketNotification) and its bucket-level callback policy (GetBucketCallbackPolicy), match the user's expected event type against the configured rules, and attribute CallbackFailed-style errors to a concrete cause (5-second response limit, non-JSON body, 502/unreachable callback server, HTTPS/SNI certificate, malformed callback parameter). Conclude with evidence-based findings only; this skill never creates or modifies any notification rule or callback policy.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API - e.g. `PutBucketNotification`, `PutBucketCallbackPolicy`, `DeleteBucketCallbackPolicy`, `PutObject*`, `DeleteBucket*`, or any configuration change. This includes commands "for the user to run manually". If the user asks to create/modify/delete an event-notification rule or callback policy, only output manual console guidance and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All diagnostics MUST be performed by running the scripts under `scripts/` (`oss_event_notification_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts - the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / GetBucketNotification / GetBucketCallbackPolicy / GetCallerIdentity. If a query fails or returns empty, record it and state the limitation - never invent configured rules, event types, or callback statuses. When "no rule configured" (404 NoSuchNotificationConfiguration) is returned, report it as the semantic finding "event notification is not configured" - NOT as an error.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps, and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line - never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill only answers event-notification triggering and upload-callback failure attribution questions. It CANNOT query the activation state of dependent services (SMQ/MNS, EventBridge) directly - no such read API is available to this skill; instead it states this limitation and gives the console check path. It does not handle billing, error-code glossaries, endpoint selection, or access-log tracing - defer to the sibling skills named in the frontmatter.
7. **ABSOLUTE PROHIBITION (no write to verify, no reproduction):** Never try to make the reported symptom happen again, and never "verify", "test", "validate" or "repair" a configuration by issuing a write: no object upload, copy, append, multipart-complete or delete (`PutObject` / `PostObject` / `AppendObject` / `CompleteMultipartUpload` / `DeleteObject`), no request carrying an `x-oss-callback` header, no test bucket, test object, test rule or test policy. Attribution is built only from the read-only queries run by `scripts/` plus the error text the customer supplies. **Empty / not-found is a valid, complete result:** `NoSuchBucket`, "event notification not configured", "no callback policy configured" or an empty rule list must be reported as the conclusion and then stop - never react to such a result with a mutating call, and never fall back to hand-written ossutil / SDK / curl commands to force more evidence.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Trigger Conditions

Use this skill when the customer's own wording matches one of these phrases (the same list the `description` advertises):

- "event notification not triggering"
- "upload callback failed"
- "CallbackFailed error"
- "callback 502"
- "callback timeout 5 seconds"
- "OSS event to MNS"
- "x-oss-event-status"

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| access-log tracing | `alibabacloud-oss-access-log-trace-diagnosis` |
| error codes | `alibabacloud-oss-transfer-error-code-diagnosis` |
| endpoint issues | `alibabacloud-oss-endpoint-internal-diagnosis` |
| billing | `alibabacloud-oss-billing-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `verdict fields` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-event-notification-diagnosis`
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

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request asks to create/modify/delete notification rules or callback policies, do not proceed with any mutation - output manual console guidance only and declare this skill is read-only (Absolute Rule 1).

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/oss_event_notification_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: Event notification rules | Rule limits, supported event types, dependent services, propagation delay, not-triggering checklist |
| M2: Callback troubleshooting | CallbackFailed attribution tree, 5-second limit, JSON/200 requirements, HTTPS/SNI, malformed callback parameter |
| M3: RAM policies | Minimal read-only RAM policy required by this skill |

Documented run order: Step 1: Confirm Identity and Collect Inputs; Step 2: Run the Diagnosis; Step 3: Interpret the Findings and Advise; Step 4: Conclusion and Suggestions.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket to diagnose.
- **Expected region** (`--region`): optional; used only to build the first query endpoint. The bucket's real region is always re-derived from GetBucketInfo before the notification query.
- **Expected event type** (`--expected-event`): optional; the event the user expects to be notified (e.g. `ObjectCreated:PutObject`). Matched against the configured rules (exact match or group wildcard `Group:*`).
- **Observed callback error** (`--callback-error`): optional; the exact error text of the failing upload (e.g. `CallbackFailed, Message: Error status : 502.`) used for root-cause attribution.
- **Callback URL** (`--callback-url`): optional; the user's callbackUrl for a static form check (scheme/host/SNI notes). No network probe is issued from this skill.
- **UID**: can always be omitted - it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query region defaulted, UID derived), the Agent MUST explicitly declare this in the response or report metadata.

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Event notification rules | [references/event-notification-rules.md](references/event-notification-rules.md) | Rule limits, supported event types, dependent services, propagation delay, not-triggering checklist |
| M2: Callback troubleshooting | [references/callback-troubleshooting.md](references/callback-troubleshooting.md) | CallbackFailed attribution tree, 5-second limit, JSON/200 requirements, HTTPS/SNI, malformed callback parameter |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the bucket name and, when available, the expected event type or the exact callback error text. Map symptoms first with [references/event-notification-rules.md](references/event-notification-rules.md) or [references/callback-troubleshooting.md](references/callback-troubleshooting.md).

### Step 2: Run the Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/oss_event_notification_diagnosis.py \
    --bucket <name> [--region <region>] [--expected-event <event-type>] \
    [--callback-error "<observed error>"] [--callback-url <url>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` to confirm the bucket exists and derive its real region.
3. Calls OSS `GetBucketNotification` (signature V4, bucket's real region): a configured rule set is parsed; 404 NoSuchNotificationConfiguration becomes the semantic finding "event notification not configured".
4. Calls OSS `GetBucketCallbackPolicy` to check the bucket-level callback policy (404 BucketCallbackPolicyNotExist means "no policy configured").
5. Attributes any `--callback-error` text to a root cause and emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Findings and Advise

Read `event_notification` and `upload_callback` from the report:
- **not configured** - no rule exists on the bucket: notifications can never fire; give the manual console creation path (Data Processing > Event Notifications) and the SMQ/MNS activation prerequisite.
- **configured but event not covered** - rules exist but none covers the expected event type or object prefix/suffix: advise extending/adding a rule (manual console task).
- **CallbackFailed attribution** - relay the `kind` / `attribution` / `advice`: 5-second response limit, non-JSON body, 502 (server down / TLS-SNI / network), non-200 status, or malformed callback parameter.
- **dependent services** - state honestly that SMQ/MNS or EventBridge activation/delivery cannot be queried by this skill; give the console check paths (SMQ/MNS console; EventBridge event tracing) and the `x-oss-event-status` response-header self-check.
- **DEGRADED report** - relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent configured rules.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual fields from the report. Base the conclusion on the script's `status` / `event_notification` / `upload_callback` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any change).

## Important Notes

- **No-rule semantics**: `404 NoSuchNotificationConfiguration` is a finding ("event notification is not configured"), not an error - report it with `STATUS: OK`.
- **Propagation delay**: a newly created rule takes about 10 minutes to take effect; a "not triggering" report right after rule creation must account for this window.
- **Dependent services**: the legacy notification path requires SMQ (formerly MNS) activated; EventBridge delivery must be verified in the EventBridge console. This skill cannot query their state directly - never fabricate an activation status.
- **Versioned buckets**: deleting without a versionId only adds a delete marker and does NOT fire ObjectRemoved events.
- **Callback timeout**: the 5-second callback response limit is fixed and not configurable; the callback server must return HTTP 200 with a JSON body; upload succeeds + callback fails = HTTP 203 CallbackFailed (the object IS stored).
- **HTTPS/SNI**: OSS does not send SNI by default; HTTPS callback servers relying on SNI need `callbackSNI=true`, otherwise the handshake fails and surfaces as a 502 CallbackFailed.
- **Read-only operations**: only GetBucketInfo, GetBucketNotification, GetBucketCallbackPolicy, and `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 - event notification not triggering**

> User: "I set up an event notification on bucket test-agentceping but my MNS queue receives nothing when files are uploaded. Account UID 1552974654746705."

```bash
python3 scripts/oss_event_notification_diagnosis.py --bucket test-agentceping --expected-event ObjectCreated:PutObject
```

Report the `event_notification` finding (configured or not, event coverage), the dependent-service console check path, the 10-minute propagation window, and declare any auto-filled parameters. If the report is `STATUS: DEGRADED` (e.g. missing RAM permission), relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 - upload callback failed with 502**

> User: "Our PutObject with callback returns 203 CallbackFailed, Message: Error status : 502. The callback URL is https://cb.example.com/notify."

```bash
python3 scripts/oss_event_notification_diagnosis.py --bucket <name> \
    --callback-error "CallbackFailed, Message: Error status : 502." \
    --callback-url https://cb.example.com/notify
```

Relay the attribution (server not listening / TLS-SNI handshake failure / network path) and the advice (callbackSNI=true, curl verification for the customer to run on their own host - this skill never probes the callback URL itself, HTTP while debugging). The 5-second limit and JSON-body requirements come from the report's mechanism notes.

**Example 3 - callback timeout**

> User: "Uploads fail intermittently with CallbackFailed saying reply timeout cost:5000ms."

```bash
python3 scripts/oss_event_notification_diagnosis.py --bucket <name> \
    --callback-error "CallbackFailed Error status : -1 reply timeout, cost:5000ms, timeout:5000ms"
```

Explain the fixed 5-second response limit and the async-processing advice from the report; never claim the limit is configurable.

<!-- production-pattern-example -->

**Example N - Upload callback fails with CallbackFailed and HTTP 502**

> User: "My callback URL works from curl but OSS keeps reporting CallbackFailed with a 502, and the certificate is valid."

```bash
python3 scripts/oss_event_notification_diagnosis.py --bucket "my-bucket" --callback-error "502" --callback-url "https://api.example.com/callback"
```

Report the 5-second response budget and the SNI behaviour: several HTTPS sites behind one IP need callbackSNI set explicitly, otherwise the origin rejects the handshake; also verify the URL is publicly resolvable, not an intranet address.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/oss_event_notification_diagnosis.py` | Diagnosis entry: GetBucketInfo + GetBucketNotification + GetBucketCallbackPolicy + CallbackFailed attribution |

CLI options for `oss_event_notification_diagnosis.py`: `--bucket <name>` (required), `--region <region>`, `--expected-event <event-type>`, `--callback-error "<error text>"`, `--callback-url <url>` (all optional).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing read permission, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| `NoSuchNotificationConfiguration` / 404 | Bucket has no event-notification rule | NOT an error: report the semantic finding "event notification not configured" with `STATUS: OK` |
| `BucketCallbackPolicyNotExist` / 404 | Bucket has no bucket-level callback policy | NOT an error: report "no callback policy configured"; request-level callback parameters may still be in use |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the root cause with the actual evidence fields (rule existence, event coverage, callback attribution) - no fabricated values.
3. Declare every auto-filled parameter (region default, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions; never fabricate the activation state of SMQ/MNS or EventBridge.
5. Give rule-creation / policy-change suggestions as manual console guidance only (this skill never applies changes).
6. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."

