---
name: alibabacloud-oss-endpoint-internal-diagnosis
description: |
  Read-only OSS endpoint and internal-network diagnostics for wrong endpoint/region choice: which endpoint to use, ECS and OSS in different regions, internal network access failing, same-region internal traffic fee, custom domain not opening. Triggers: "no such host", "must use specified endpoint", "internal endpoint", "public network traffic cost", "wrong region endpoint", "endpoint region mismatch", "does not belong to you".
  Do NOT use for billing (alibabacloud-oss-billing-diagnosis), errors (alibabacloud-oss-transfer-error-code-diagnosis), multipart (alibabacloud-oss-multipart-upload-diagnosis), images (alibabacloud-oss-image-processing-diagnosis), emergencies (alibabacloud-oss-security-incident-forensics), signed URL (alibabacloud-oss-presigned-url-v4-diagnosis), ossfs (alibabacloud-oss-ossfs-mount-diagnosis), client tools (alibabacloud-oss-client-tools-diagnosis), static hosting (alibabacloud-oss-static-website-diagnosis), direct-access links (alibabacloud-oss-direct-access-link-diagnosis).
---

# OSS Endpoint & Internal Network Diagnosis

Diagnose Alibaba Cloud OSS endpoint and internal network access problems: "my client reports no such host when using the internal endpoint", "OSS says it must use specified endpoint", "which endpoint should I use for my ECS in the same region", "why am I paying public network traffic cost when my ECS reads the bucket".

Core approach: verify the caller identity, fetch the bucket's real location and its public/internal endpoints with the read-only GetBucketInfo control-plane query, match them against the endpoint the user configured, classify the endpoint form (public / internal / transfer acceleration), and attribute errors such as "no such host", "must use specified endpoint", or "does not belong to you" to a concrete cause. Conclude with evidence-based findings only; this skill never changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API - e.g. `PutBucket*`, `DeleteBucket*`, `PutObject*`, `DeleteObject*`, `PutBucketPolicy`, or any ACL/policy/endpoint configuration change. This includes commands "for the user to run manually". If the user asks to change a bucket ACL or enable transfer acceleration, only output manual guidance and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All OSS diagnostics MUST be performed by running the scripts under `scripts/` (`oss_endpoint_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts - the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries. Every run MUST contain BOTH commands below, in this order, each as its own command; neither one replaces the other:
   `cd $SKILL_DIR && python3 scripts/sts_token.py`
   `cd $SKILL_DIR && python3 scripts/oss_endpoint_diagnosis.py --bucket <name> [--endpoint <user-endpoint>] [--region <region>] [--question "<customer original wording>"]`
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / ListBuckets / GetCallerIdentity. If a query fails or returns empty, record it and state the limitation - never invent bucket locations, endpoints, or traffic figures.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line - never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill only answers endpoint selection and internal/public access attribution questions (which endpoint matches the bucket region, why an access error occurs, why public network traffic cost is generated), **including custom-domain (CNAME) access diagnosis** - whether a custom domain resolves, is bound to the bucket (read-only `ListCname`), and points at the right endpoint. It does NOT handle bandwidth quota approval, attack tracing/mitigation, or the custom-domain ICP **filing procedure** itself (how to file) - for those, state the boundary and give manual guidance only. It also never runs a dial-test on the customer's behalf; for region/ISP reachability it guides the customer through self-service CloudMonitor site monitoring / `ossutil probe` (see M4).

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

- "no such host"
- "must use specified endpoint"
- "internal endpoint"
- "public network traffic cost"
- "wrong region endpoint"
- "endpoint region mismatch"
- "does not belong to you"

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| billing | `alibabacloud-oss-billing-diagnosis` |
| errors | `alibabacloud-oss-transfer-error-code-diagnosis` |
| multipart | `alibabacloud-oss-multipart-upload-diagnosis` |
| images | `alibabacloud-oss-image-processing-diagnosis` |
| emergencies | `alibabacloud-oss-security-incident-forensics` |
| signed URL | `alibabacloud-oss-presigned-url-v4-diagnosis` |
| ossfs | `alibabacloud-oss-ossfs-mount-diagnosis` |
| client tools | `alibabacloud-oss-client-tools-diagnosis` |
| static hosting | `alibabacloud-oss-static-website-diagnosis` |
| direct-access links | `alibabacloud-oss-direct-access-link-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

**Custom-domain (CNAME) symptoms are IN scope** (they are an endpoint-form question, not a separate skill): "custom domain won't open", "bound domain stuck at pending verification", "domain won't resolve / no such host / UnknownHostException", "ICP-filed but the webpage won't open". Pass the custom domain as `--endpoint`; the script classifies it as `cname` and runs the CNAME diagnosis flow (DNS probe + read-only `ListCname`). Do NOT route these to static-website/direct-access first - those are only the downstream fan-out once the CNAME binding itself is confirmed healthy.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `verdict` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-endpoint-internal-diagnosis`
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
# Verify caller identity (informational only; credentials always come from the default chain)
cd $SKILL_DIR && python3 scripts/sts_token.py
```

## User Confirmation

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request falls outside endpoint / internal-network attribution (bandwidth quota approval, attack tracing/mitigation, custom-domain ICP filing per Absolute Rule 6), do not proceed with any diagnosis - state the boundary and give manual guidance only.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/oss_endpoint_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: Endpoint rules | Region-to-endpoint mapping, internal vs public endpoint selection, public network traffic cost attribution, custom-domain (CNAME) troubleshooting path |
| M2: Diagnosis tree | Error routing: no such host / must use specified endpoint / 403 AccessDenied / does not belong to you / custom-domain (CNAME) |
| M3: RAM policies | Minimal read-only RAM policy required by this skill |
| M4: Dial-test guidance | Region/ISP reachability: guiding the customer through self-service CloudMonitor site monitoring + `ossutil probe`, interpreting 6xx/timeout results (this skill never runs a dial-test itself) |

Documented run order: Step 1: Confirm Identity and Collect Inputs; Step 2: Run the Endpoint Diagnosis; Step 3: Interpret the Verdict and Advise; Step 4: Conclusion and Suggestions.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket to diagnose.
- **User endpoint** (`--endpoint`): optional; the endpoint the user currently configured (e.g. `oss-cn-beijing.aliyuncs.com` or `oss-cn-shanghai-internal.aliyuncs.com`), or a **custom domain (CNAME)** such as `img.example.com`. When provided it is classified (public / internal / accelerate / dualstack / cname / invalid) and matched against the bucket's real region; a `cname` value triggers the custom-domain diagnosis flow (DNS probe + read-only `ListCname`).
- **Expected region** (`--region`): optional; used to derive the query endpoint when `--endpoint` is absent.
- **UID**: can always be omitted - it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted, UID derived), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --endpoint/--region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Endpoint rules | [references/endpoint-rules.md](references/endpoint-rules.md) | Region-to-endpoint mapping, internal vs public endpoint selection, public network traffic cost attribution, custom-domain (CNAME) troubleshooting path |
| M2: Diagnosis tree | [references/diagnosis-tree.md](references/diagnosis-tree.md) | Error routing: no such host / must use specified endpoint / 403 AccessDenied / does not belong to you / custom-domain (CNAME) |
| M3: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |
| M4: Dial-test guidance | [references/dial-test-guidance.md](references/dial-test-guidance.md) | Region/ISP reachability: self-service CloudMonitor site monitoring + `ossutil probe` targets, 6xx/timeout result interpretation, dial-test SOP and anti-patterns (customer self-service; this skill never runs a dial-test) |

## Diagnostic Flow

### Step 1: Confirm Identity and Collect Inputs

MANDATORY, and not substitutable: run `cd $SKILL_DIR && python3 scripts/sts_token.py` as its own command **before** the entry script, to verify credentials and derive the UID (traceability label only). The UID that `scripts/oss_endpoint_diagnosis.py` derives internally does NOT replace this standalone run; a diagnosis whose transcript never shows `python3 scripts/sts_token.py` as a separate command is an incomplete run. Collect the bucket name and, if the user has it, the endpoint currently configured. If the user only reports an error message, map it first with [references/diagnosis-tree.md](references/diagnosis-tree.md).

### Step 2: Run the Endpoint Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/oss_endpoint_diagnosis.py \
    --bucket <name> [--endpoint <user-endpoint>] [--region <region>] \
    [--question "<customer original wording>"]
```

`--question` is required whenever the customer message contains a question or symptom sentence (in any language): quote that wording verbatim as the value so the official-doc verification leg runs; omit it only when the customer gave no wording to verify.

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK with the resolved endpoint, carrying the session-id User-Agent and a per-call timeout.
3. On failure, falls back to `ListBuckets` (prefix lookup) to locate the bucket's region, logging `[WARN]` for every degraded step.
4. When the supplied `--endpoint` is a **custom domain (CNAME)**: probes its DNS resolution (OS resolver only, not a cloud API) and calls read-only `ListCname` (`oss:ListCname`) to check the binding, then emits a `cname_diagnosis` block with a `CUSTOM_DOMAIN_CNAME_*` verdict; both legs degrade gracefully with `[WARN]`.
5. Emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdict and Advise

Read `verdict.region_match` and `recommendations` from the report:
- **mismatch** - the configured endpoint's region differs from the bucket location: the user must rebuild the endpoint from the bucket location ("must use specified endpoint"); same-region Alibaba Cloud clients should use the internal endpoint.
- **matched + public endpoint** - same-region clients running on Alibaba Cloud should switch to the internal endpoint to eliminate public network traffic cost.
- **internal endpoint used from the Internet** - internal endpoints only resolve inside the Alibaba Cloud network of that region; from outside it fails DNS ("no such host").
- **custom domain (CNAME)** - read `cname_diagnosis.verdict`:
  - `CUSTOM_DOMAIN_CNAME_NOT_RESOLVED` - the domain does not resolve (the customer-side `UnknownHostException` / "no such host"); fix the CNAME record at the DNS provider so it points at the bucket's public endpoint.
  - `CUSTOM_DOMAIN_CNAME_NOT_BOUND` - resolves but not bound to this bucket (read-only `ListCname` shows no match); bind it in the OSS console (Transmission Management > Domain Names) after ICP filing.
  - `CUSTOM_DOMAIN_CNAME_DISABLED` - bound but `ListCname` Status is `Disabled`; re-enable it.
  - `CUSTOM_DOMAIN_CNAME_PENDING` - a non-Enabled status; note the console's "pending verification" state is a CnameToken verification state, NOT an API Status value (the official enum is only Enabled/Disabled) - complete ownership verification + ICP filing.
  - `CUSTOM_DOMAIN_CNAME_MISRESOLVED` - bound (Enabled) but the resolution chain misses the bucket endpoint (e.g. points at a CDN); re-point it, or if a CDN is intentional use `alibabacloud-oss-cdn-origin-config-diagnosis`.
  - `CUSTOM_DOMAIN_CNAME_OK` - binding healthy; if access still fails, check the HTTPS certificate (`ListCname` reports whether a certificate is bound), the SDK CNAME mode (`is_cname=True`), and Bucket Policy/ACL. Downstream fan-out: a webpage that won't open -> `alibabacloud-oss-static-website-diagnosis`; object preview / hotlink protection -> `alibabacloud-oss-direct-access-link-diagnosis`.
  - `CUSTOM_DOMAIN_CNAME_UNKNOWN` - DNS probe and/or `ListCname` degraded; walk [references/endpoint-rules.md](references/endpoint-rules.md) sec.3.3 manually and never invent the binding state.
- **DEGRADED report** - relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent the bucket region.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual numbers/fields from the report. Base the conclusion on the script's `status` / `verdict` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any change).

## Important Notes

- **Wrong-region access symptom**: querying a bucket through another region's endpoint fails with AccessDenied EC 0003-00001403 ("must be addressed using the specified endpoint"); the error's `<Endpoint>` field carries the correct endpoint. A DIFFERENT error - "The bucket you access does not belong to you" (EC 0003-00000001) - means the bucket belongs to another account, not a region mismatch. Always cross-check the endpoint region against the bucket location before concluding an ownership problem (D-10, measured 2026-09-07).
- **Internal endpoint scope**: `oss-<region>-internal.aliyuncs.com` resolves only from the Alibaba Cloud network of the same region; internet clients get "no such host".
- **Traffic attribution**: public network traffic cost is generated only by traffic through the public endpoint; same-region internal traffic is free of that charge. For deduction/resource-pack questions, defer to the billing skill instead. For **per-bucket traffic cost attribution** (which bucket generates the most outbound cost), refer to `alibabacloud-oss-billing-diagnosis --bucket-usage` (NetOut/CdnOut per-bucket breakdown).
- **Read-only operations**: only GetBucketInfo, ListBuckets, ListCname (custom-domain binding), an OS-level DNS resolution probe, and `sts:GetCallerIdentity`; never modifies anything.
- **Custom-domain (CNAME) semantics**: a custom domain is served through the bucket's own region endpoint, so endpoint-region rules still apply underneath. `ListCname` `Status` is officially only `Enabled`/`Disabled`; the console's "pending verification" state is a CnameToken ownership-verification state and may not surface in `ListCname` until verified - never report a domain as healthy while verification is outstanding. Binding/resolution diagnosis is in scope; the ICP filing *procedure*, static-website hosting, and CDN origin config are downstream fan-outs (route to the sibling skills named in the verdict guidance).

## Examples

**Example 1 - wrong region endpoint ("must use specified endpoint")**

> User: "My app configured oss-cn-beijing.aliyuncs.com for bucket test-agentceping but OSS says it must use specified endpoint."

```bash
python3 scripts/oss_endpoint_diagnosis.py --bucket test-agentceping --endpoint oss-cn-beijing.aliyuncs.com
```

Report the `verdict` (endpoint region vs bucket location), the correct public/internal endpoints from the recommendations, and declare any auto-filled parameters. If the report is `STATUS: DEGRADED` (e.g. missing RAM permission), relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 - public network traffic cost from endpoint choice**

> User: "My ECS in cn-shanghai downloads from my bucket through the public endpoint and I see public network traffic cost. Which endpoint should I use, internal or public endpoint?"

```bash
python3 scripts/oss_endpoint_diagnosis.py --bucket <name> --endpoint oss-cn-shanghai.aliyuncs.com
```

If the bucket location matches cn-shanghai, advise switching same-region ECS clients to `oss-cn-shanghai-internal.aliyuncs.com` (free of public network traffic cost); cite the report's recommendations.

**Example 3 - no such host on the internal endpoint**

> User: "Running ossutil from my office network with the internal endpoint fails: no such host."

```bash
python3 scripts/oss_endpoint_diagnosis.py --bucket <name> --endpoint oss-cn-shanghai-internal.aliyuncs.com
```

Explain that internal endpoints resolve only inside the Alibaba Cloud network of that region; from the Internet use the public endpoint. Route further DNS failures with [references/diagnosis-tree.md](references/diagnosis-tree.md).

**Example 4 - custom domain (CNAME) won't open / stuck pending / no such host**

> User: "I bound the custom domain img.example.com to bucket nicer; the console keeps showing 'pending verification' and customers get UnknownHostException when they access it."

```bash
python3 scripts/oss_endpoint_diagnosis.py --bucket nicer --endpoint img.example.com
```

The script classifies the value as `cname`, probes DNS and calls read-only `ListCname`, and reports a `cname_diagnosis.verdict`. Relay that verdict (e.g. `CUSTOM_DOMAIN_CNAME_NOT_RESOLVED` / `_NOT_BOUND` / `_PENDING`), walk the [references/endpoint-rules.md](references/endpoint-rules.md) sec.3.3 path, and declare the auto-filled query endpoint (a custom domain is not a valid OSS query endpoint, so the region is re-derived via GetBucketInfo/ListBuckets). Note that the console "pending verification" state is a CnameToken verification state, not an API `Status` value.

<!-- production-pattern-example -->

**Example N - ECS in the same region still pays for public egress**

> User: "My service runs on an ECS in Hangzhou and I set an internal endpoint, yet the OSS bill still shows external traffic."

```bash
python3 scripts/oss_endpoint_diagnosis.py --bucket "my-bucket" --endpoint "oss-cn-beijing.aliyuncs.com"
```

Show the mismatch between the bucket's real region and the configured endpoint, and explain that browser-side links to the public endpoint bypass the ECS internal path entirely, so those bytes are billable.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/oss_endpoint_diagnosis.py` | Endpoint diagnosis entry: GetBucketInfo + region match + endpoint selection advice, with ListBuckets fallback; optional `--question "<customer original wording>"` adds the `doc_verification` block (official-doc verification, llms-index) |
| `scripts/_doc_lookup.py` | Runtime official-doc verification module (llms-index leg + body leg, help.aliyun.com only, 3-day cache); imported by the entry script for `--question`, never blocks the diagnosis |

CLI options for `oss_endpoint_diagnosis.py`: `--bucket <name>` (required), `--endpoint <endpoint>` (optional, the user's configured endpoint), `--region <region>` (optional, derives the query endpoint when `--endpoint` is absent), `--question "<customer original wording>"` (optional, enables the official-doc verification leg).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing `oss:GetBucketInfo`, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, run the ListBuckets fallback, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| "no such host" / DNS failure | Internal endpoint used outside the Alibaba Cloud network, or local DNS issue | Route with [references/diagnosis-tree.md](references/diagnosis-tree.md); suggest the public endpoint for internet clients |
| `AccessDenied` / 403 on `ListCname` | Missing `oss:ListCname`, or the cluster has not enabled the custom-domain feature (OSS error 0018-00000002: PutCname/ListCname/DeleteCname fail until it is enabled) | Record `[WARN]`, degrade the CNAME binding to `unknown` (`CUSTOM_DOMAIN_CNAME_UNKNOWN`), point to [references/ram-policies.md](references/ram-policies.md); never invent the binding state |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the root cause with the actual evidence fields (bucket location, endpoint kind, region match) - no fabricated values.
3. Declare every auto-filled parameter (endpoint default, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Give endpoint-change suggestions as manual guidance only (this skill never applies changes).
6. When the run carries a `doc_verification` block, cite the official doc URLs from `doc_verification.docs`; if `doc_verification.note` starts with `DEGRADED`, explicitly state that online official-doc verification was unavailable.
