---
name: alibabacloud-oss-security-incident-forensics
description: |
  Read-only forensics for OSS traffic abuse and security incidents
  (overnight traffic spikes, suspected AK leak, hotlinking). Audits
  exposure (ACL, policy, public-access block, Referer), runs the 6-step
  SLS log query sequence, routes root causes, outputs containment
  checklists. Triggers: "OSS traffic spike overnight", "traffic abuse", "strange files in my bucket", "suspected AK leak on OSS", "hotlinking abuse", "unexpected outbound traffic", "unauthorized downloads from my bucket".
  Do NOT use: for transfer error codes use alibabacloud-oss-transfer-error-code-diagnosis;
  for billing use alibabacloud-oss-billing-diagnosis; for endpoint choice use alibabacloud-oss-endpoint-internal-diagnosis;
  for signed-URL use alibabacloud-oss-presigned-url-v4-diagnosis; for access-log tracing use alibabacloud-oss-access-log-trace-diagnosis;
  for direct-link issues use alibabacloud-oss-direct-access-link-diagnosis.
---

# OSS Traffic Abuse & Security Incident Forensics

Diagnose Alibaba Cloud OSS traffic-abuse and suspected security incidents: "my OSS traffic spiked overnight and the bill exploded", "I see traffic abuse from IPs I do not recognize", "there are strange files in my bucket I never uploaded", "I have a suspected AK leak on OSS", "other websites are hotlinking my images".

Core approach: verify the caller identity, audit the bucket's exposure surface with read-only control-plane queries (ACL, bucket policy anonymous-grant detection, Block Public Access state, anti-hotlink Referer configuration, Requester Pays payer), derive the dedicated real-time-log (SLS) asset names, EXECUTE the 6-step traffic-source query sequence read-only against the customer's own log project (auth mode / daily trend / Top IP / UA / Referer / Top files / Top URLs, all excluding CDN origin-pull), interpret the returned rows into a log-evidence conclusion, route the evidence across the four-way root-cause classification, and hand over a manual containment + hardening checklist. Conclude with evidence-based findings only; this skill never changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API — e.g. `PutBucket*`, `DeleteBucket*`, `PutObject*`, `DeleteObject*`, `PutBucketPolicy`, `DeleteBucketPolicy`, or any ACL/policy/Referer configuration change. This includes commands "for the user to run manually". If the user asks to seal off attackers, change the ACL, or disable a leaked AccessKey, only output manual guidance and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All OSS forensics MUST be performed by running the scripts under `scripts/` (`oss_traffic_forensics.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts — the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by the control-plane queries or the executed real-time-log queries. If a query fails or returns empty, record it and state the limitation — never invent attacker IPs, traffic figures, or root causes. The SLS query leg EXECUTES read-only (the SLS `GetHistograms` and `GetLogs` API operations) against the customer's own dedicated log project (`oss-log-<owner-uid>-<regionId>`) and is strictly additive: it never raises, never contributes to `errors[]`, and on any failure (not enabled / no permission / over-cap window) degrades to handing over the statement sequence for the SLS console without changing the exposure audit's STATUS.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps, and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line — never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill only performs read-only traffic-abuse forensics (exposure audit, real-time-log query execution — strictly additive, log-query toolkit emission on degradation, root-cause routing, containment guidance). It does NOT execute blocking/ban actions, handle legal reporting, or process fee reductions — for such requests, state the boundary and give manual guidance only.

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

- "OSS traffic spike overnight"
- "traffic abuse"
- "strange files in my bucket"
- "suspected AK leak on OSS"
- "hotlinking abuse"
- "unexpected outbound traffic"
- "unauthorized downloads from my bucket"

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| transfer error codes | `alibabacloud-oss-transfer-error-code-diagnosis` |
| billing | `alibabacloud-oss-billing-diagnosis` |
| endpoint mismatch | `alibabacloud-oss-endpoint-internal-diagnosis` |
| signed URL expiry | `alibabacloud-oss-presigned-url-v4-diagnosis` |
| access-record tracing | `alibabacloud-oss-access-log-trace-diagnosis` |
| direct-access issues | `alibabacloud-oss-direct-access-link-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

## Execution Principle

All forensics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `exposure` / `realtime_log` / `log_evidence` / `root_cause_candidates` / `containment`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-security-incident-forensics`
- **skill-version**: read at runtime from `references/manifest.json` (`version`), the single place where this skill's version is declared. It is never hardcoded, guessed or reused: the entry script resolves and validates it **before the first cloud call** (OSS control plane, STS identity and the SLS query leg) and stops with `STATUS: FAIL` (exit 1) when the manifest is missing or its `version` is invalid.
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every OSS SDK request (User-Agent header) and every `--user-agent` argument of the aliyun CLI identity call of that run, so all calls of one forensics run can be correlated.

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
- Identity check (`aliyun sts get-caller-identity`) and real-time-log execution (`aliyun sls get-histograms` / `aliyun sls get-logs`, plugin mode): the aliyun CLI default credential chain (environment or `~/.aliyun/config.json`), so the identity label and the log queries always share one account.

Do not read, print, or pass AK/SK/STS tokens explicitly. If the identity check fails, guide the user to run `aliyun configure` — never ask for AK/SK. The identity chain and the data plane MUST belong to the same account: the identity check follows the aliyun CLI credential chain while the OSS data plane follows the environment variables. Bucket attribution and the SLS real-time-log project name in this skill are therefore derived from the bucket OWNER UID returned by GetBucketInfo (data-plane credential, always consistent with the bucket); the STS caller UID is only a traceability label, and any skew between the two is logged as an `[WARN]` identity-consistency alert.

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

Because every action of this skill is strictly read-only, no user confirmation is required before running the forensics scripts. Confirmation discipline applies at the scope boundary instead: when a request falls outside read-only forensics (executing blocking actions, legal reporting, fee reductions per Absolute Rule 6), do not proceed with any diagnosis — state the boundary and give manual guidance only.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/oss_traffic_forensics.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: Traffic-abuse playbook | Mandatory 6-step analysis over the 13-statement log query sequence, CDN origin-pull exclusion, four-way root-cause classification, containment checklist |
| M2: Exposure check | Bucket exposure-surface audit: ACL, bucket policy, Block Public Access, anti-hotlink Referer, Requester Pays |
| M3: RAM policies | Minimal read-only RAM policy required by this skill |

Documented run order: Step 1: Confirm Identity and Collect Inputs; Step 2: Run the Traffic Forensics; Step 3: Interpret the Evidence and Route the Root Cause; Step 4: Conclusion and Suggestions.

## Input Parameters

- **Bucket name** (`--bucket`): required; the affected OSS bucket.
- **Expected region** (`--region`): optional; derives the query endpoint. On mismatch the script falls back to `ListBuckets` (prefix lookup) to discover the bucket's real region and retries.
- **Time window** (`--time-window`): optional, human-readable anomaly window (default "last 7 days"); echoed into the report, and when it states a day/hour count that count wins over `--log-days` for the SLS query window.
- **Log scan days** (`--log-days`): optional (default 1, max 7, the OSS real-time log keeps a rolling 7 days); how many days back to execute the real-time-log queries. Ignored when `--time-window` already states a day/hour count.
- **Disable log execution** (`--no-log-execution`): optional flag; emit the query statement sequence without executing it (offline review, or the caller lacks SLS read permission).
- **Customer wording** (`--question`): optional; the customer's original question wording passed verbatim. Enables the official-doc verification leg (`doc_verification` section) — read-only, help.aliyun.com only, never blocks the diagnosis.
- **UID**: can always be omitted — it is derived via `aliyun sts get-caller-identity` and used only as a traceability label plus the SLS project-name derivation. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted, UID derived, region discovered via ListBuckets), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Traffic-abuse playbook | [references/traffic-abuse-playbook.md](references/traffic-abuse-playbook.md) | Mandatory 6-step analysis over the 13-statement log query sequence, CDN origin-pull exclusion, four-way root-cause classification, containment checklist |
| M2: Exposure check | [references/exposure-check.md](references/exposure-check.md) | Bucket exposure-surface audit: ACL, bucket policy, Block Public Access, anti-hotlink Referer, Requester Pays |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the affected bucket name and, if the user provides it, the anomaly time window. If the user only says "traffic is abnormal", ask once for the bucket name; everything else is derivable.

### Step 2: Run the Traffic Forensics

```bash
cd $SKILL_DIR && python3 scripts/oss_traffic_forensics.py \
    --bucket <name> [--region <region>] [--time-window "<window>"]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK, carrying the session-id User-Agent and a per-call timeout; on failure falls back to `ListBuckets` (prefix lookup) to locate the bucket's region and retries.
3. Audits the exposure surface with `GetBucketPolicy` / `GetBucketPublicAccessBlock` / `GetBucketReferer` / `GetBucketRequestPayment` (Requester Pays is an exposure neutralizer: either it or Block Public Access makes a nominally public bucket not anonymously readable), each independently degraded with `[WARN]` (an absent policy / public-access-block counts as a valid finding).
4. Derives the dedicated SLS real-time-log asset names from the bucket OWNER UID (`oss-log-<owner-uid>-<regionId>` project, `oss-log-store` logstore) and EXECUTES the 13-statement query sequence implementing the 6-step analysis read-only via `aliyun sls get-histograms` (volume pre-count) and `aliyun sls get-logs` (plugin mode) — CDN origin-pull excluded, byte sums kept at byte-level precision; `--no-log-execution` emits the statement sequence only. Any SLS failure (not enabled / no permission / over-cap window) degrades to emit-only and never changes the audit's STATUS.
5. Interprets the returned rows into `log_evidence` (auth-mode mix, daily-trend shape, endpoint/VPC split, Top IP by count AND by bytes, UA, referer, Top objects — including the "normal business traffic" conclusion) and routes the four-way root-cause candidates ordered by the combined exposure + log evidence, emitting the matching containment checklist.
6. Emits the structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Evidence and Route the Root Cause

Read `exposure.verdict`, `log_evidence` and `root_cause_candidates` from the report:
- **Exposure level high** (public-read ACL or policy allows anonymous access) — primary candidates are public-read scraping / hotlinking; confirm against `log_evidence.auth_mode` (sign_type=NotSign with access_id '-' dominating).
- **Exposure level low** (private ACL, policy closed) — primary candidate is AK leak; confirm against `log_evidence.auth_mode` (sign_type=NormalSign with an unrecognized AccessKey ID and foreign source IPs).
- **CDN check first**: if the step-0 cdn-origin check shows most requests are sync_request=cdn, the OSS-side Top IPs are CDN edge nodes — the investigation moves to the CDN side.
- **Daily-trend shape**: `log_evidence.daily_trend` classifies the window as burst / sustained / spiky — burst points to a trigger event (link got shared, scraper found the bucket), spiky to batch-pull scraping, sustained requires the endpoint split read (mostly-internal ⇒ likely legitimate) before calling it abuse.
- **DEGRADED report** — relay the recorded errors and the `NEXT_ACTION` guidance honestly; the emitted SLS query toolkit stays usable in the console even when the log leg degraded.

### Step 4: Conclusion and Suggestions

Summarize the exposure findings and the primary root-cause candidate with the actual fields from the report. Base the conclusion on the script's `status` / `exposure` / `log_evidence` / `root_cause_candidates` / `containment` / `next_action` fields rather than re-deriving them. Containment actions (switch ACL to private, rotate the leaked AccessKey, tighten the Referer whitelist, enable Block Public Access) must be presented as manual guidance only — this skill never applies any change. When the fix touches the read path, present the private-ACL vs anti-hotlink TRADE-OFF from [references/traffic-abuse-playbook.md](references/traffic-abuse-playbook.md) (decide by whether a legitimate anonymous public-read consumer exists; a one-sided "switch to private" broke a real customer's site and they reverted to public-read).

## Important Notes

- **Real-time log is the decisive evidence**: the exposure audit only ranks the candidates; the script executes the query sequence and the returned sign_type / access_id / client_ip / user_agent / referer distributions confirm which root cause is true. If the feature is not enabled, guide the user to enable it first (OSS console → bucket → Operations & Monitoring → Real-time Log) so the next anomaly is traceable.
- **CDN origin-pull exclusion is mandatory**: every Top-IP/UA/Referer query excludes `sync_request: cdn`; CDN edge-node IPs would otherwise poison the analysis.
- **Presigned-URL leak signature**: request_uri entries carrying signature parameters (OSSAccessKeyId / Signature) hit from many distinct IPs indicate a leaked or over-shared signed URL, not an open bucket.
- **Read-only operations**: only GetBucketInfo, GetBucketPolicy, GetBucketPublicAccessBlock, GetBucketReferer, GetBucketRequestPayment, ListBuckets, `sts:GetCallerIdentity`, and the SLS `GetHistograms` / `GetLogs` API operations against the customer's own OSS real-time-log project; never modifies anything.
- **ActionTrail guidance only**: for API-level audit questions (who changed the bucket configuration), point the user to ActionTrail data events delivered to SLS as manual guidance — this skill does not call ActionTrail APIs.

## Examples

**Example 1 — traffic spike overnight on a known bucket**

> User: "My OSS traffic spiked overnight on bucket test-agentceping and I suspect traffic abuse. My account UID is 1552974654746705."

```bash
python3 scripts/oss_traffic_forensics.py --bucket test-agentceping --region cn-hangzhou --time-window "last 24 hours"
```

Report the `exposure.verdict` (level + findings), the executed `realtime_log` / `log_evidence` conclusion for the stated window, and the ranked `root_cause_candidates`. Declare any auto-filled parameters. If the report is `STATUS: DEGRADED` (e.g. missing RAM permission), relay the recorded errors and `NEXT_ACTION` honestly; when the log leg degraded, hand over the emitted query sequence for the SLS console.

**Example 2 — suspected AK leak on a private bucket**

> User: "There is a suspected AK leak on OSS: my monitoring shows GetObject calls from IPs outside our office. Bucket test-agentceping, account 1552974654746705."

```bash
python3 scripts/oss_traffic_forensics.py --bucket test-agentceping --region cn-hangzhou
```

If the exposure surface is closed (private ACL, no anonymous policy), the report ranks `ak-leak` first; instruct the user to confirm with the step-1 auth-mode query (sign_type=NormalSign with an unrecognized AccessKey ID) and then follow the containment checklist (disable/rotate the key in the RAM console) manually.

**Example 3 — hotlinking / unauthorized downloads**

> User: "Other sites are hotlinking my images — unauthorized downloads from my bucket keep inflating my outbound traffic."

```bash
python3 scripts/oss_traffic_forensics.py --bucket <name> [--region <region>]
```

Read the referer finding from `exposure` and the step-4 referer query; advise the anti-hotlink whitelist and CDN-with-URL-authentication pattern from the containment checklist as manual guidance.

<!-- production-pattern-example -->

**Example N — Sudden multi-terabyte egress from a public-read bucket**

> User: "Our egress jumped to 1.7 TB overnight and the account went into arrears. We only make about a hundred playback calls a day."

```bash
python3 scripts/oss_traffic_forensics.py --bucket "my-bucket" --region "cn-hangzhou" --time-window "24"
```

Give the exposure audit verdict first (ACL, Block Public Access, hotlink protection), then the `log_evidence` conclusion from the executed SLS queries (or, when the real-time log is not enabled, the handed-over query sequence with the derived project/logstore names), then the containment checklist.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/oss_traffic_forensics.py` | Forensics entry: exposure audit + SLS real-time-log EXECUTION (the SLS `GetHistograms` / `GetLogs` API operations) + log-evidence interpretation + four-way root-cause routing + containment checklist |
| `scripts/_oss_client.py` | Shared read-only OSS control-plane client (oss2 SDK wrapper, session-id User-Agent, per-call timeout, retry/degradation, error taxonomy) |
| `scripts/_sls_query.py` | SLS real-time-log execution leg: window resolution (time-window text wins over `--log-days`), GetHistograms volume pre-count, GetLogs execution, strictly additive degradation |
| `scripts/_log_evidence.py` | Log-row interpretation: auth-mode mix, daily-trend shape classification (burst/sustained/spiky), endpoint/VPC split, byte-weighted verdicts, normal-business-traffic short-circuit |
| `scripts/_doc_lookup.py` | Official-doc verification leg: help.aliyun.com llms-index lookup + cached index + .md body excerpts (stdlib only, zero credentials, never blocks the diagnosis) |

CLI options for `oss_traffic_forensics.py`: `--bucket <name>` (required), `--region <region>` (optional, derives the query endpoint), `--time-window "<window>"` (optional, human-readable anomaly window echoed into the report and used to derive the log scan window), `--log-days <1-7>` (optional, default 1, ignored when `--time-window` carries a day/hour count), `--no-log-execution` (optional, emit the query statements without executing them), `--question "<customer original wording>"` (optional, enables the `doc_verification` leg).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing read-only permissions or bucket owned by another account | Record `[WARN]`, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED`; the SLS query toolkit stays usable |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| Wrong-region endpoint | `--region` absent and default endpoint mismatches | The script auto-discovers the region via ListBuckets and retries; declare the discovered region |
| GetBucketPolicy / GetPublicAccessBlock 404 | Feature simply not configured on the bucket | Treated as a valid finding (no policy / block not configured), not an error |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

All errors follow the structured `category/code/message` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the exposure findings and the primary root-cause candidate with the actual evidence fields (ACL grade, policy state, Block Public Access state, referer config) — no fabricated values.
3. Declare every auto-filled parameter (endpoint default, UID derivation, region discovery).
4. Relay the `log_evidence` conclusion when the SLS real-time-log queries executed (auth-mode mix, daily-trend shape, top sources by count AND by bytes); when the log leg degraded (not enabled / no permission / over-cap window), hand over the query statement sequence with the derived project/logstore names for the user to run in the SLS console and state the degradation reason.
5. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
6. Give containment/hardening suggestions as manual guidance only (this skill never applies changes).
7. When `doc_verification` is present, cite the doc URLs from `doc_verification.docs` verbatim, and state the offline-degradation sentence when `doc_verification.note` starts with DEGRADED.
