---
name: alibabacloud-oss-quota-throttling-diagnosis
description: |
  Read-only OSS QPS/bandwidth quota and throttling diagnostics. Use when requests persistently hit 503/SlowDown or clients time out with no server errors. Covers watermark guidance, a throttling attribution decision tree, optimization (concurrency, prefix hashing, backoff), quota-increase guidance, ActiveRequestLimitExceeded concurrency throttling, and resource pool QoS / dedicated bandwidth consultation.
  Triggers: "QPS limit exceeded", "bandwidth saturated", "timeout without server errors", "persistent SlowDown 503", "quota increase request", "TotalQpsLimitExceeded", "x-oss-qos-delay-time", "ActiveRequestLimitExceeded", "resource pool QoS", "dedicated bandwidth".
  Not for one-off SlowDown / single-request error codes, client-tool connection timeouts, transfer acceleration selection, endpoint errors, or billing (use the matching OSS diagnosis skill); never applies changes.
---

# OSS QPS/Bandwidth Quota & Throttling Diagnosis

Diagnose Alibaba Cloud OSS quota and throttling problems: "my requests get 503 TotalQpsLimitExceeded at peak hours", "the bucket bandwidth seems saturated during nightly backups", "clients time out but the OSS side shows no errors", "how do I apply for a higher QPS/bandwidth quota or dedicated bandwidth".

Core approach: verify the caller identity, locate the bucket's real region and attributes with the read-only GetBucketInfo control-plane query, report the official quota context of that region (bandwidth/QPS defaults, sourced from the official documentation), then run a symptom decision tree that attributes 503 / SlowDown / timeout symptoms to server-side throttling, hotspot partitions, or the client-side/network path. OSS exposes **no public API to query the actual bandwidth/QPS watermark (utilization)** - watermark assessment is knowledge guidance only (console Usage Query > Basic Data, CloudMonitor, `x-oss-qos-delay-time` header). Conclude with evidence-based findings only; this skill never changes anything and never submits quota applications.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API - e.g. `PutBucket*`, `PutObject*`, `DeleteObject*`, any ACL/policy/QoS configuration change. This includes commands "for the user to run manually". Quota increases and dedicated-resource (resource pool QoS) applications are ticket-based: only output the application guidance, never submit anything.
2. **MANDATORY entry-point enforcement:** All diagnostics MUST be performed by running the scripts under `scripts/` (`oss_quota_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts - the scripts embed timeout, error degradation, and observability guarantees. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass raw credential values (key pair or session token) explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept credential values from the user or from another script.
4. **NO FABRICATION (watermark honesty):** OSS has no public API to read the actual bandwidth/QPS utilization. Never present guessed or invented watermark/utilization numbers as measured data; the quota context this skill reports is the official default limits, and actual utilization must be checked in the OSS console (Usage Query > Basic Data) or CloudMonitor, or via the `x-oss-qos-delay-time` header of throttled responses. Every conclusion must be grounded in script output or user-provided evidence.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line - never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill only answers quota/throttling attribution and performance-optimization questions. It does NOT handle single-request error code troubleshooting, transfer acceleration selection, endpoint/DNS errors, billing disputes, or attack-induced traffic abuse - for such requests, state the boundary and defer to the matching skill or manual guidance only.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)."

DOC CITATION RULE (closed set, EXECUTION RULE): every doc URL in the final answer MUST appear verbatim in one of these two places - (a) the JSON output produced by this run of the scripts, in any field (e.g. `doc_verification.docs[*].url`, `quota_reference.*.source`), or (b) the reference modules shipped under `references/` in this skill. Never write a doc URL from memory, never extend or repair a path to make a link look plausible, and never treat a non-help.aliyun.com link as official documentation. A link copied from this run's script output is always allowed, even when it is not inside `doc_verification.docs`.

## Trigger Conditions

Use this skill when the customer's own wording matches one of these phrases (the same list the `description` advertises):

- "QPS limit exceeded"
- "bandwidth saturated"
- "timeout without server errors"
- "persistent SlowDown 503"
- "quota increase request"
- "TotalQpsLimitExceeded"
- "x-oss-qos-delay-time"

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| one-off SlowDown / single-request error codes | `alibabacloud-oss-transfer-error-code-diagnosis` |
| client-tool connection timeouts | `alibabacloud-oss-client-tools-diagnosis` |
| transfer acceleration selection | `alibabacloud-oss-transfer-acceleration-diagnosis` |
| endpoint errors | `alibabacloud-oss-endpoint-internal-diagnosis` |
| or billing | `alibabacloud-oss-billing-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `verdict` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-quota-throttling-diagnosis`
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

Do not read, print, or pass raw credential values (key pair or session token) explicitly. If the identity check fails, guide the user to run `aliyun configure` - never ask for credential values.

### aliyun CLI version requirement

The scripts shell out to the aliyun CLI (at minimum the `aliyun sts get-caller-identity` identity pre-check), which MUST be **version 3.3.3 or newer**: older builds resolve the default credential chain differently and can drop the STS session token. Verify the installed version and upgrade it before the first run:

```bash
aliyun version        # must print 3.3.3 or newer (measured with 3.4.5)
aliyun upgrade --yes  # upgrade the installed CLI in place to the latest version
```

If the CLI is not installed at all, install the Alibaba Cloud CLI package for the host OS from the official release channel and then run `aliyun configure` (the profile stays in `~/.aliyun/config.json`; this skill never asks for raw credential values). When the CLI is missing, too old to upgrade, or unauthenticated, the identity pre-check degrades instead of aborting: `scripts/_oss_client.py` logs `[WARN] identity pre-check failed: ...` on stderr, records the empty UID, and the diagnosis still runs to a conclusion, because the identity label is traceability only and never evidence.

```bash
cd $SKILL_DIR

# Verify caller identity (informational only; credentials always come from the default chain)
python3 scripts/sts_token.py
```

## User Confirmation

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request asks for actually applying a quota increase, enabling resource pool QoS, or changing any configuration (per Absolute Rule 1), do not proceed with any change - output the manual application guidance only.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/oss_quota_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: Throttling rules | Official quota framework: per-region bandwidth defaults, QPS limits, 503 error-code table, `x-oss-qos-delay-time` semantics |
| M2: Diagnosis tree | Symptom routing: 503/SlowDown/timeout-without-server-errors attribution decision tree |
| M3: Performance guide | Prefix hash distribution, concurrency control, multipart/range transfer, exponential backoff, CDN offload |
| M4: Quota increase | Quota-increase application path (ticket), resource pool QoS / dedicated bandwidth prerequisites |
| M5: RAM policies | Minimal read-only RAM policy required by this skill |

Documented run order: Step 1: Confirm Identity and Collect Inputs; Step 2: Run the Quota/Throttling Diagnosis; Step 3: Interpret the Verdict and Advise; Step 4: Conclusion and Suggestions.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket whose region/quota context anchors the diagnosis.
- **Symptom** (`--symptom`): optional; one of `503`, `timeout`, `slow`, `slowdown`.
- **Error code** (`--error-code`): optional; the error code the client captured (e.g. `TotalQpsLimitExceeded`, `DownloadTrafficRateLimitExceeded`, or `503 SlowDown`).
- **Direction** (`--direction`): optional; `upload` / `download` / `both` (default `both`).
- **Measured peaks** (`--peak-qps`, `--peak-bandwidth-gbps`): optional; user-provided measurements compared against the official limits.
- **Sequential prefix** (`--sequential-prefix`): optional; `yes`/`no` - whether object keys use sequential prefixes (hotspot risk).
- **UID**: can always be omitted - it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted, UID derived), the Agent MUST explicitly declare this in the response or report metadata.

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Throttling rules | [references/throttling-rules.md](references/throttling-rules.md) | Official quota framework: per-region bandwidth defaults, QPS limits, 503 error-code table, `x-oss-qos-delay-time` semantics |
| M2: Diagnosis tree | [references/diagnosis-tree.md](references/diagnosis-tree.md) | Symptom routing: 503/SlowDown/timeout-without-server-errors attribution decision tree |
| M3: Performance guide | [references/performance-guide.md](references/performance-guide.md) | Prefix hash distribution, concurrency control, multipart/range transfer, exponential backoff, CDN offload |
| M4: Quota increase | [references/quota-increase.md](references/quota-increase.md) | Quota-increase application path (ticket), resource pool QoS / dedicated bandwidth prerequisites |
| M5: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the bucket name plus every symptom detail the user has: error code, direction, measured peaks, time window, whether object keys use sequential prefixes. Map raw symptoms first with [references/diagnosis-tree.md](references/diagnosis-tree.md).

### Step 2: Run the Quota/Throttling Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/oss_quota_diagnosis.py \
    --bucket <name> [--symptom 503|timeout|slow|slowdown] \
    [--error-code <code>] [--direction upload|download|both] \
    [--peak-qps <N>] [--peak-bandwidth-gbps <N>] \
    [--sequential-prefix yes|no] [--region <region>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK to locate the bucket's real region and attributes, carrying the session-id User-Agent and a per-call timeout; on failure it falls back to `ListBuckets` (prefix lookup), logging `[WARN]` for every degraded step.
3. Reports the official quota context of the bucket region (bandwidth/QPS defaults) and states explicitly that no public watermark query API exists.
4. Runs the attribution decision tree and emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdict and Advise

Read `verdict.verdict` and `recommendations` from the report:
- **server-throttle-confirmed** - a throttle-family error code proves server-side rate limiting: apply concurrency control + exponential backoff; check the console watermark; ticket-based quota increase if needed.
- **region-quota-pressure-likely** - the reported peak exceeds the official region default: reduce concurrency now, apply via ticket.
- **hotspot-partition-likely** - sequential prefixes concentrate load on one partition (~2,000 req/s): hash or reverse key prefixes before any quota increase.
- **client-or-network-likely** - timeout without server errors: verify DNS / cross-region link / client bandwidth against OSS access logs; do not conclude throttling.
- **evidence-insufficient** - collect the error code, peaks, and console watermark before attributing.
- **DEGRADED report** - relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent the bucket region or utilization.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual fields from the report. Base the conclusion on the script's `status` / `verdict` / `recommendations` / `next_action` fields rather than re-deriving them. Quota-increase and dedicated-resource steps are manual guidance only ([references/quota-increase.md](references/quota-increase.md)); this skill never applies changes or submits applications.

## Important Notes

- **Verification boundary (public vs internal)**: this skill's verifiable surface is public and doc-confirmed - the official per-region bandwidth/QPS default limits, the thresholds at which throttling fires, `x-oss-qos-delay-time` semantics, the 503/429 error-code table, and the quota-increase / resource-pool process wording. Three things have NO public OSS API and must never be queried inside the sandbox nor fabricated: (1) the account/bucket's REAL bandwidth/QPS utilization watermark (the actual Gbps-level water level) - verify only via console Usage Query > Basic Data or CloudMonitor; (2) real throttling-event records; (3) the approval status or decision of a quota-increase / dedicated-bandwidth request - ticket channel only. Throttled responses carry the `x-oss-qos-delay-time` header (upload: precise delay in ms; download: estimated). All defaults reported by this skill come from the official limits documentation and are context, not measurements.
- **Timeout without server errors**: 5xx-free client timeouts are attributed to the client-side/network path first (DNS, cross-region/cross-border links, client bandwidth); confirm with OSS access logs before mentioning throttling.
- **Sequential-prefix hotspot**: even below the account-wide QPS limit, requests concentrated on one partition are throttled at ~2,000 req/s; randomize prefixes (4-char hex hash) or reverse timestamp keys.
- **Quota increase path**: QPS increases are not self-service in the quota center - submit a ticket; resource pool QoS (dedicated bandwidth) requires the region bandwidth to reach 400 Gbps plus a ticket application.
- **Read-only operations**: only GetBucketInfo, ListBuckets, and `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 - 503 TotalQpsLimitExceeded at peak hours**

> User: "My app gets 503 with error code TotalQpsLimitExceeded every evening on bucket test-agentceping, peak QPS around 12000."

```bash
python3 scripts/oss_quota_diagnosis.py --bucket test-agentceping \
    --symptom 503 --error-code TotalQpsLimitExceeded --peak-qps 12000
```

Report the verdict (`server-throttle-confirmed`, peak vs. the 10,000 non-sequential QPS default), the backoff/concurrency recommendations, and the ticket-based increase path. Declare any auto-filled parameters.

**Example 2 - timeout without server errors**

> User: "Clients time out downloading from my bucket, but the OSS console shows no 5xx errors at all."

```bash
python3 scripts/oss_quota_diagnosis.py --bucket <name> --symptom timeout --direction download
```

Relay the `client-or-network-likely` verdict: verify DNS, cross-region links, and client bandwidth against OSS access logs before concluding throttling.

**Example 3 - quota increase request for bandwidth**

> User: "We need 80 Gbps internal download bandwidth for our training bucket next month. How do we apply?"

```bash
python3 scripts/oss_quota_diagnosis.py --bucket <name> --direction download
```

Report the region's official bandwidth defaults, then give the manual application guidance from [references/quota-increase.md](references/quota-increase.md) (ticket path; resource pool QoS prerequisites). This skill never submits the application.

<!-- production-pattern-example -->

**Example N - Throughput caps far below the documented regional bandwidth**

> User: "Sequential reads top out around 7 Gbps although the region document promises 100 Gbps, and adding concurrency does not help."

```bash
python3 scripts/oss_quota_diagnosis.py --bucket "my-bucket" --direction "download" --peak-bandwidth-gbps "15"
```

Classify it as a server-side flow-control or partition-hotspot question, explain the per-key sequential QPS ceiling and prefix hashing, and state that a quota raise or dedicated bandwidth is an approval path, not a self-service switch.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/oss_quota_diagnosis.py` | Quota/throttling diagnosis entry: GetBucketInfo region anchor + quota context + attribution decision tree, with ListBuckets fallback |

CLI options for `oss_quota_diagnosis.py`: `--bucket <name>` (required), `--symptom`, `--error-code`, `--direction`, `--peak-qps`, `--peak-bandwidth-gbps`, `--sequential-prefix`, `--region`, `--endpoint` (all optional).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing `oss:GetBucketInfo`, bucket owned by another account | Record `[WARN]`, run the ListBuckets fallback, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no throttling" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the attribution with the actual evidence fields (verdict, error-code classification, peaks vs. limits, bucket region) - no fabricated values.
3. Declare that quota watermark is not API-queryable whenever utilization is discussed, and point to the console/CloudMonitor verification path.
4. Declare every auto-filled parameter (endpoint default, UID derivation).
5. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
6. Give quota-increase / configuration suggestions as manual guidance only (this skill never applies changes or submits applications).
7. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)." Other official URLs emitted by this run's script output (such as the `source` fields under `quota_reference`) may be cited as-is - see DOC CITATION RULE.

