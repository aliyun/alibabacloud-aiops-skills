---
name: alibabacloud-oss-cross-account-auth-diagnosis
description: |
  Read-only OSS cross-account auth diagnosis: attributes NoPermission/AccessDenied to
  trust-policy gaps, RAM-policy scope, Bucket-Policy+RAM dual-grant, AssumeRole failures;
  emits templates only. Triggers: "cross-account access failed", "trust policy error",
  "cross-account replication permission error", "AssumeRole failed on OSS",
  "cross-account migration authorization", "peer account cannot read my bucket",
  company/partner account, account transfer, EncodedDiagnosticMessage decode.
  Do NOT use: transfer/timeout (use alibabacloud-oss-transfer-error-code-diagnosis);
  endpoint (use alibabacloud-oss-endpoint-internal-diagnosis); CRR health (use
  alibabacloud-oss-crr-config-check); ossfs (use
  alibabacloud-oss-ossfs-mount-diagnosis); direct-link 403 (use
  alibabacloud-oss-direct-access-link-diagnosis); signed-URL (use
  alibabacloud-oss-presigned-url-v4-diagnosis); same-account RAM (use
  alibabacloud-oss-security-incident-forensics).
---

# OSS Cross-Account Authorization Diagnosis

Diagnose Alibaba Cloud OSS cross-account authorization problems: "another account gets AccessDenied reading my bucket", "cross-account replication keeps failing with NoPermission", "the replication role trust policy errors out", "AssumeRole returns not authorized when my peer tries to access OSS", "cross-account migration is blocked by authorization".

Core approach: verify the caller identity, compare the caller UID with the bucket owner UID via the read-only GetBucketInfo control-plane query to establish same-account vs cross-account, check the bucket's Bucket Policy existence and content with GetBucketPolicy (a 404 NoSuchBucketPolicy is the measured "not configured" fact, not an error), run pure-function attribution over the evidence - trust-policy gap vs RAM-policy resource-granularity mistake vs the Bucket-Policy + RAM dual-grant requirement vs AssumeRole failure routing - and emit ready-to-apply authorization templates (trust policy with the `oss.aliyuncs.com` service principal, cross-account RAM policy, replication Bucket Policy). Conclude with evidence-based findings only; this skill never changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (no authorization changes):** Under **NO** circumstances may you generate, write, or execute any command/script that APPLIES an authorization change - e.g. `PutBucketPolicy`, RAM `CreatePolicy` / `AttachPolicyToRole` / `UpdateRole` (trust-policy edit), `PutBucketReplication`, `ossutil`/console equivalents, or any AssumeRole used to mutate resources. This includes commands "for the user to run" issued from the scripts. Fixes are emitted as JSON TEMPLATES in the report and in `references/auth-config-templates.md`, described in words, and **applied by the user manually**. If the user asks to apply an authorization, only output the template + manual steps and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All OSS diagnostics MUST be performed by running the scripts under `scripts/` (`oss_cross_account_auth_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts - the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / GetBucketPolicy / ListBuckets / GetCallerIdentity. If a query fails or returns empty, record it and state the limitation - never invent an owner UID, a policy document, or an attribution. When the STS-RequestId evidence is not collected, say the attribution is inconclusive rather than picking a branch.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line - never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill only answers cross-account access / replication / migration authorization attribution and template output. It does NOT handle: upload/download transfer error codes or RequestTimeout (use `alibabacloud-oss-transfer-error-code-diagnosis`); endpoint/region or internal-network endpoint errors (use `alibabacloud-oss-endpoint-internal-diagnosis`); CRR rule health/status checks or copy-rule health checks (use `alibabacloud-oss-crr-config-check`); ossfs mount failures (use `alibabacloud-oss-ossfs-mount-diagnosis`); direct object-link 403 (use `alibabacloud-oss-direct-access-link-diagnosis`); signed/expired URL 403 (use `alibabacloud-oss-presigned-url-v4-diagnosis`); SAME-account RAM user/sub-account permission errors (use `alibabacloud-oss-security-incident-forensics` for identity-visibility forensics); or actually applying any authorization. Colloquial Chinese ticket synonyms for these boundaries (and for the positive triggers) are embedded in `scripts/_doc_lookup.py` (SKILL_TOPICS + VOCAB_MAP), so the doc-verification layer still routes real-ticket wording correctly.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `ownership` / `bucket_policy` / `policy_check` / `attribution` / `templates` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Trigger Conditions

Route here when the user reports: another account (a peer / partner / company account) getting AccessDenied or NoPermission while reading/writing a bucket; cross-account or cross-region replication failing with a permission error; a replication/migration role trust-policy error; AssumeRole rejected when a peer tries to obtain an OSS temporary credential; cross-account migration blocked by authorization; data sync or migration between two Alibaba Cloud accounts; OSS account transfer. Do NOT route: same-account RAM sub-account 403, direct-link 403, signed-URL expiry 403, RequestTimeout / transfer error codes, copy-rule (CRR) health checks, ossfs mount failures, internal-endpoint questions (see Absolute Rule 6 for the exact target skills). Real-ticket Chinese phrasings for both directions are mapped by `scripts/_doc_lookup.py` (SKILL_TOPICS + VOCAB_MAP) at the doc-verification layer.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-cross-account-auth-diagnosis`
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

Do not read, print, or pass AK/SK/STS tokens explicitly. If the identity check fails, guide the user to run `aliyun configure` - never ask for AK/SK. The identity chain and the data plane MUST belong to the same account: the identity check follows the aliyun CLI credential chain while the OSS data plane follows the environment variables. The bucket-owner side of the ownership relation always comes from the GetBucketInfo owner_id (data-plane credential); when the caller UID differs from the bucket owner UID and a data-plane credential is present, the `cross_account` verdict carries an `[WARN]` identity-consistency caveat - align both chains to the same account (e.g. lock `ALIBABA_CLOUD_PROFILE`) before treating it as real cross-account access.

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

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request asks to actually apply an authorization (Absolute Rule 1), do not execute it - output the template + manual guidance only. When a request falls outside cross-account authorization attribution (Absolute Rule 6), state the boundary and defer to the responsible skill or manual handling.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket at the center of the cross-account scenario.
- **Scenario** (`--scenario`): optional; `access` (cross-account read/write), `replication` (cross-account replication NoPermission), `migration` (cross-account migration authorization), or `all` (default).
- **Peer account UID** (`--peer-uid`): optional; the other account's UID, used to verify the Bucket Policy Principal list and fill the cross-account trust policy.
- **Role name** (`--role-name`): optional; the replication/migration RAM role name, used in the assumed-role Principal checks and templates.
- **Expected region** (`--region`): optional; used to derive the query endpoint.
- **Encoded diagnostic message** (`--encoded-diagnostic-message`): optional; the `EncodedDiagnosticMessage` from a 403 `AccessDeniedDetail`, or the whole 403 error body (OSS XML / POP JSON). When present the script runs the G3-5 403-localization main path (`ram_403_diagnosis`): it interprets the PLAIN `AccessDeniedDetail` fields (who / which action / which policy layer / deny kind - no extra permission needed) and, when the credential allows `ram:DecodeDiagnosticMessage`, decodes the message for the exact missing action/resource/condition and matched Deny policies. On a credential without that permission it degrades gracefully (`[WARN]` + `manual_decode_guidance`: RAM permission-diagnosis console page / OpenAPI Explorer / administrator handoff) and never flips the core STATUS.
- **UID**: can always be omitted - it is derived via `aliyun sts get-caller-identity` and used as the caller side of the ownership comparison plus a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted or re-derived from the bucket location, UID derived), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Cross-account authorization decision tree | [references/cross-account-auth-decision-tree.md](references/cross-account-auth-decision-tree.md) | Ownership comparison, STS-RequestId attribution method, access-failure ladder (Effect-aware policy checks), AssumeRole failure routing, explicit-Deny attribution (EC 0003-00000201), Condition anti-patterns (StringLike / oss:Prefix), 403 EncodedDiagnosticMessage / AccessDeniedDetail localization main path (RAM DecodeDiagnosticMessage + Message/EC trap + degrade), extend_information cross-account verification + SLS template, official sources |
| M2: Authorization configuration templates | [references/auth-config-templates.md](references/auth-config-templates.md) | Trust-policy templates (service + cross-account), cross-account RAM policy, replication dual grant, Bucket Policy Principal rules |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Orchestration

Symptom routing before running the entry script:
- "peer account gets AccessDenied reading/writing my bucket" -> `--scenario access` (add `--peer-uid` if known).
- "cross-account replication fails with NoPermission" -> `--scenario replication` (add `--role-name` if known).
- "cross-account migration blocked by authorization" -> `--scenario migration`.
- mixed or unclear symptoms -> `--scenario all`.
- the user pastes a 403 `AccessDenied` body / an `EncodedDiagnosticMessage` -> add `--encoded-diagnostic-message <msg-or-body>` (plus the usual `--bucket`/`--scenario`) to run the G3-5 localization path (`ram_403_diagnosis`).

## Execution Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the caller UID (the caller side of the ownership comparison). Collect the bucket name, the scenario, and any peer UID / role name; map the symptom with the Orchestration section above.

### Step 2: Run the Cross-Account Authorization Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/oss_cross_account_auth_diagnosis.py \
    --bucket <name> [--scenario access|replication|migration|all] \
    [--peer-uid <uid>] [--role-name <name>] [--region <region>] \
    [--encoded-diagnostic-message <encoded-msg-or-403-body>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK with the resolved endpoint, carrying the session-id User-Agent and a per-call timeout; reads the bucket owner UID + location; on failure falls back to `ListBuckets` (prefix lookup) to locate the bucket's region.
3. Compares caller UID with bucket owner UID to establish same-account vs cross-account.
4. Calls `GetBucketPolicy` (degraded with `[WARN]`; 404 NoSuchBucketPolicy is the measured "not configured" fact) and runs a static Principal/Resource sanity check.
5. Runs the pure-function attribution (trust-policy vs RAM-policy resource-granularity vs dual-grant vs AssumeRole routing) and emits the authorization templates for the selected scenario.
6. Emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdict and Advise

Read `ownership`, `bucket_policy`, `policy_check`, `attribution`, `templates` from the report:
- **cross_account** - the grant must come from the owning account; relay the dual-side requirement.
- **policy not_configured** - the owning account must add a Bucket Policy; relay the emitted template.
- **policy_check gaps/malformed** - relay the specific findings (Principal syntax, missing peer UID, case mismatch).
- **policy_check protective-deny info** - a Deny statement with Principal `"*"` is the Alibaba Cloud automatic security-protection shape ("Created by Alibaba Cloud Security, do not modify this action"): relay it as a NORMAL security configuration, and explicitly tell the user NOT to remove or re-create it (an Allow `"*"` is the anonymous-access problem, a Deny `"*"` never grants anything).
- **policy_check.deny_statements** - when the peer is hit by a Deny, quote the actual Deny Statement JSON in the answer (EC 0003-00000101: naming the policy is not a diagnosis) and explain that an explicit Deny always wins over every Allow (EC 0003-00000201).
- **attribution** - relay trust-policy vs RAM-policy direction; if inconclusive, say both branches must be checked.
- **ram_403_diagnosis** (present when `--encoded-diagnostic-message` is passed or a 403 body was captured) - relay `interpretation`: the missing `missing_action`, the `policy_layer` + `policy_layer_fix`, and the `deny_kind` (ExplicitDeny -> remove/narrow the Deny, adding Allow cannot fix it; ImplicitDeny -> add an Allow). If `interpretation.message_ec_trap` is set, WARN the user that the response `Message` text is misleading (the official 0003-00000201 example says "Access denied by bucket policy." while `EC` + `PolicyType` prove a RAM identity-policy-side deny) - attribute by `EC` + `PolicyType`, never by the `Message` wording. When `decode.available` is true, relay `decoded_interpretation` (exact missing action/resource/condition + matched Deny policies); when false, relay `manual_decode_guidance` and state honestly that the current credential lacks `ram:DecodeDiagnosticMessage` (the PLAIN-field interpretation above still stands).
- **DEGRADED report** - relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent an owner UID or policy.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual numbers/fields from the report. Base the conclusion on the script's `status` / `ownership` / `policy_check` / `attribution` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any authorization change).

## Important Notes

- **Cross-account authorization is dual-sided**: the bucket-owning account grants access (Bucket Policy and/or a RAM role created there); a one-sided grant is a top measured failure cause.
- **Effect-aware policy reading (CAA-1)**: only Allow statements grant anything. A Deny statement with Principal `"*"` is the measured Alibaba Cloud automatic security-protection shape - a normal configuration, never anonymous access, never to be removed or re-created. A peer UID found in a Deny statement is an explicit rejection: an explicit Deny always wins over every Allow (EC 0003-00000201: an explicit RAM Deny takes precedence), so adding more Allow statements cannot fix it; remove or narrow the Deny instead.
- **StringEquals does not support wildcards**: to match "any VPC" or prefix-style source values in a Condition, use `StringLike` (e.g. `"acs:SourceVpc": ["*"]` with `StringLike`); `StringEquals` is literal-only - see references/cross-account-auth-decision-tree.md anti-patterns.
- **oss:Prefix only applies to prefix-parameter APIs**: ListObjects/ListObjectsV2 requests carry `prefix`; GetObject/PutObject/DeleteObject do not, so an `oss:Prefix` condition never matches them - restrict by key suffix in the Resource element instead (`acs:oss:*:uid:bucket/*.html`).
- **STS-RequestId attribution**: a replication/migration NoPermission whose server-log carries a separate STS RequestId is a TRUST-policy problem (`oss.aliyuncs.com` missing from Principal.Service); without it, it is a RAM-policy resource-granularity problem. Collect the reqId/server-log before concluding.
- **Bucket Policy != RAM Policy syntax**: Bucket Policy Principal uses bare UID digits or `arn:sts::<uid>:assumed-role/<role>/<session>`, NOT `acs:ram::...` ARNs; the two must not be mixed.
- **UID comparison caveat**: a RAM-user UID differing from the main-account UID does NOT by itself mean cross-account; for assumed-role requests compare the role-owning account UID with the bucket owner (use the `extend_information` field in access logs - first value for normal requests, 4th value for STS AssumeRole requests; see references/auth-config-templates.md sec.5 and the SLS query template there).
- **404 NoSuchBucketPolicy is normal**: it means "no policy configured", not a permission failure - treat it as the not_configured fact.
- **Account scope of every conclusion**: all findings reflect ONLY the account of the current credential (for an assumed-role credential, the role-owning account). A `not_configured`/empty result means "not visible to THIS account's credential", never "no policy exists in absolute terms" - state this limitation in the final answer.
- **403 EncodedDiagnosticMessage localization (G3-5)**: a 403 `AccessDeniedDetail` carries both PLAIN fields (`AuthPrincipal*`, `AuthAction`, `PolicyType`, `NoPermissionType`, `EC`) and an opaque `EncodedDiagnosticMessage`. Interpret the PLAIN fields first - this needs NO decode and NO extra permission and already answers who / which action / which policy layer / deny kind. Decoding the `EncodedDiagnosticMessage` via `ram:DecodeDiagnosticMessage` adds the exact resource + conditions + matched Deny policies, but requires that RAM permission; the evaluation role (skillsclienttest) lacks it (measured 403 NoPermission), so the script degrades to `manual_decode_guidance` (RAM permission-diagnosis console page / OpenAPI Explorer / hand the encoded message to the account administrator) and never flips the core STATUS. **Message/EC trap**: the OSS `Message` text can say "Access denied by bucket policy." while `EC` (0003-00000201/202/203) and `PolicyType` prove a RAM identity-policy-side deny - always trust `EC` + `PolicyType` (+ the decoded `MatchedPolicies`), never the `Message` wording.
- **Read-only operations**: only GetBucketInfo, GetBucketPolicy, ListBuckets, `sts:GetCallerIdentity`, and the read-only `ram:DecodeDiagnosticMessage` (conditional, degrade-safe); never modifies anything.

## Examples

**Example 1 - cross-account replication NoPermission**

> User: "Cross-account replication from bucket test-agentceping (UID 1552974654746705, Hangzhou) to a peer account keeps failing with NoPermission, the role is oss-crr-role."

```bash
python3 scripts/oss_cross_account_auth_diagnosis.py --bucket test-agentceping --scenario replication --role-name oss-crr-role --region cn-hangzhou
```

Report the `attribution` direction and the `templates` (service trust policy with `oss.aliyuncs.com` + replication RAM policy + destination Bucket Policy); declare any auto-filled parameters. If `STATUS: DEGRADED`, relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 - peer account AccessDenied reading a bucket**

> User: "Another account gets AccessDenied when reading objects from my bucket test-agentceping."

```bash
python3 scripts/oss_cross_account_auth_diagnosis.py --bucket test-agentceping --scenario access --peer-uid <peer-uid>
```

Relay the `ownership` verdict and `policy_check`: if no Bucket Policy is configured, the owning account must add one using the emitted template (cross-account trust policy + RAM policy); never apply it for the user.

**Example 3 - AssumeRole rejected for a peer**

> User: "My peer calls AssumeRole to get an OSS temp credential but gets 'You are not authorized to do this action'."

```bash
python3 scripts/oss_cross_account_auth_diagnosis.py --bucket <name> --scenario access --peer-uid <peer-uid> --role-name <role>
```

Relay the `assume_role_failure_routes` ladder (wrong-account RoleArn, RAM-user ARN instead of role ARN, resource-group-scoped grant, trust-policy gap, stale long-lived AK) as manual checks.

<!-- production-pattern-example -->

**Example N - Cross-account replication rejected with Assume role failed**

> User: "I granted the role full OSS permissions but starting the copy from the destination account fails with Assume role failed."

```bash
python3 scripts/oss_cross_account_auth_diagnosis.py --bucket "target-bucket" --role-name "AliyunOSSReplicationRole"
```

Explain that the role must be assumed from the source side and that the trust policy plus the replicate actions belong to two different accounts; report which of the two is failing.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the caller UID (`--json` optional) |
| `scripts/oss_cross_account_auth_diagnosis.py` | Cross-account auth entry: GetBucketInfo ownership + GetBucketPolicy check + attribution + template output, with ListBuckets fallback |

CLI options for `oss_cross_account_auth_diagnosis.py`: `--bucket <name>` (required), `--scenario access|replication|migration|all` (default `all`), `--peer-uid <uid>` (optional), `--role-name <name>` (optional), `--region <region>` (optional), `--encoded-diagnostic-message <encoded-msg-or-403-body>` (optional; runs the G3-5 403-localization path).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing `oss:GetBucketInfo` / `oss:GetBucketPolicy`, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, run the ListBuckets fallback, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist, OR the bucket belongs to another account (invisible to non-owners) | Verify spelling and owning account; for cross-account buckets, run the diagnosis from the owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| `NoSuchBucketPolicy` / 404 | Bucket has no Bucket Policy configured | NOT an error - record it as the `not_configured` fact and emit the add-policy template |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no authorization" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |
| `ram:DecodeDiagnosticMessage` NoPermission / expired / not-supported | The current credential lacks the optional RAM permission (measured for the eval role), or the `EncodedDiagnosticMessage` is expired/invalid | NOT fatal - the script logs `[WARN]`, still emits the PLAIN-field `interpretation`, and returns `manual_decode_guidance` (RAM permission-diagnosis console page / OpenAPI Explorer / administrator handoff). The core `STATUS` is not flipped by a decode failure |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the ownership verdict (same-account / cross-account) and the policy/attribution findings with the actual evidence fields - no fabricated owner UIDs or policy documents.
3. Declare every auto-filled parameter (endpoint default, UID derivation).
4. State the account scope explicitly: conclusions reflect only the current credential's account (the role-owning account under an assumed-role credential); a not_configured/empty result is visibility-scoped, not absolute (report key `account_scope`).
5. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
6. Give authorization fixes as JSON templates + manual guidance only (this skill never applies any change).
7. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."

