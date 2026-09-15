---
name: alibabacloud-oss-transfer-acceleration-diagnosis
description: |
  Read-only OSS transfer acceleration diagnosis: detects acceleration not taking
  effect (client still on the plain endpoint), separates OSS Data Accelerator
  (same-region hot data) from Transfer Acceleration (cross-region links),
  attributes slow cross-border access and fees; never changes anything.
  Triggers: "transfer acceleration not working", "oss-accelerate endpoint",
  "cross-border access slow", "overseas upload slow", "transfer acceleration
  fee", "accelerator vs transfer acceleration". Do NOT use for bill line-item
  attribution (defer alibabacloud-oss-billing-diagnosis), endpoint choice
  (alibabacloud-oss-endpoint-internal-diagnosis), multipart fragments
  (alibabacloud-oss-multipart-upload-diagnosis), presigned URL errors
  (alibabacloud-oss-presigned-url-v4-diagnosis), QPS/bandwidth throttling
  (alibabacloud-oss-quota-throttling-diagnosis), GA/ESA/CDN back-to-origin, or
  executing enablement (write, out of scope).
---

# OSS Transfer Acceleration Diagnosis

Diagnose Alibaba Cloud OSS transfer acceleration problems: "I enabled transfer acceleration but downloads from overseas are still slow", "is oss-accelerate.aliyuncs.com the right endpoint for my cross-border access", "what is the difference between the OSS accelerator and transfer acceleration", "why am I billed for transfer acceleration traffic".

Core approach: verify the caller identity, fetch the bucket metadata with the read-only GetBucketInfo control-plane query, read the bucket's transfer-acceleration status with the read-only GetBucketTransferAcceleration query (measured on oss2 2.19.1: OSS answers 404 `NoSuchTransferAccelerationConfiguration` when the feature was never enabled - that 404 is the "feature disabled" finding, not an error), then run a pure-function decision tree: feature enabled + client still on a plain endpoint -> acceleration not taking effect (endpoint never replaced); accelerate domain in use while the feature is disabled -> requests will fail until the user enables the feature; selection questions are answered by a fixed product matrix (Data Accelerator = same-region hot-data caching; Transfer Acceleration = cross-border/cross-region link optimization); fee questions are answered with the official billing semantics. Conclude with evidence-based findings only; this skill never enables, disables, or changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API - e.g. the transfer-acceleration switch (oss2 `put_bucket_transfer_acceleration` / the console Enable action), any ACL/policy/lifecycle/CNAME change, or any object/bucket mutation. Enabling transfer acceleration is described as manual guidance in words only and is executed by the user in the OSS console. If the user asks to enable/disable the feature, only output the guidance and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All OSS diagnostics MUST be performed by running the scripts under `scripts/` (`oss_transfer_acceleration_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts - the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The scripts already resolve the default credential chain for you - `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` / `ALIBABA_CLOUD_SECURITY_TOKEN` environment variables first, then the current aliyun CLI profile (`~/.aliyun/config.json`) - entirely in memory. Therefore parsing, cat-ing, or exporting values from that config file is forbidden too: if a query degrades with `NoCredentials`, record the degradation and continue the report; never "bridge" credentials yourself. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / GetBucketTransferAcceleration / ListBuckets / GetCallerIdentity. If a query fails or returns empty, record it and state the limitation - never invent the enablement status, and never fabricate method names or APIs. If the transfer-acceleration status cannot be queried at all (permission gap / interface unavailable), degrade to the user-provided evidence form: ask for a console screenshot or a plain-language status description of the bucket's Transfer Acceleration page, run the knowledge-based judgment on that evidence, and declare the evidence source explicitly.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback and the real-region retry), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line - never silently skip or abort without a report.
6. **SCOPE BOUNDARY:** This skill only answers transfer-acceleration adoption ("not taking effect") detection, Data-Accelerator-vs-Transfer-Acceleration selection, cross-border slowness attribution, and fee-semantics explanation. It does NOT handle bill line-item attribution (defer to the billing skill), plain internal/public endpoint and region choice (defer to the endpoint skill), multipart fragment issues (defer to the multipart-upload diagnosis skill), or presigned URL errors (defer to the presigned-url-v4 diagnosis skill).

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `transfer_acceleration` / `verdict` / `selection` / `billing_notes` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Trigger Conditions

Route here when the user reports: transfer acceleration enabled but no speedup / not taking effect; the accelerate domain (oss-accelerate.aliyuncs.com) being used, misconfigured, or returning errors; slow cross-border / cross-region upload or download - including real-ticket phrasings like "overseas upload slow", "fast abroad but slow at home", "cross-border transfer slow"; confusion between the OSS accelerator and transfer acceleration; or questions about transfer acceleration fees. Do NOT route here for Global Accelerator (GA) instances, ESA, or CDN back-to-origin configuration - defer to the respective product docs.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-transfer-acceleration-diagnosis`
- **skill-version**: read at runtime from `references/manifest.json` (`version`), the single place where this skill's version is declared. It is never hardcoded, guessed or reused: the entry script resolves and validates it **before the first cloud call** and stops with `STATUS: FAIL` (exit 1) when the manifest is missing or its `version` is invalid.
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every OSS SDK request (User-Agent header) and every `--user-agent` argument of the aliyun CLI identity call of that run, so all calls of one diagnosis can be correlated.

The shared client layer (`scripts/_oss_client.py`) implements this automatically: the session-id is generated lazily on the first call of each run and cached for the rest of the run, and the skill-version is resolved lazily from `references/manifest.json` on the first User-Agent build.

### Exit codes (contract)

- `0` -- the run produced a conclusion: `STATUS: OK`, or `STATUS: DEGRADED`
  when part of the evidence was unavailable (the missing steps are recorded in
  `errors[]` and as `[WARN]` lines on stderr; the conclusion is still usable).
- `1` -- no usable conclusion: `STATUS: FAIL`, because required input is
  missing or every evidence call failed (the identity pre-check alone is a
  traceability label, NOT evidence - a run where GetBucketInfo, the
  ListBuckets fallback and GetBucketTransferAcceleration all failed exits 1
  even when the aliyun CLI identity check succeeded). `NEXT_ACTION` states
  what to ask the user for or what to fix; do not treat this as a success.
- `2` -- argparse usage error only (unknown option). A diagnosed condition never
  exits with `2`.

## Credentials

Credentials are resolved exclusively by the default credential chain:
- OSS control-plane calls (Python oss2 SDK): `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and optionally `ALIBABA_CLOUD_SECURITY_TOKEN` (STS sessions); when those are unset the scripts fall back to the current aliyun CLI profile in `~/.aliyun/config.json` (modes `AK` / `StsToken`), read in memory.
- Identity check (`aliyun sts get-caller-identity`): the same aliyun CLI default credential chain (environment or `~/.aliyun/config.json`).

Do not read, print, or pass AK/SK/STS tokens explicitly - including parsing `~/.aliyun/config.json` to "bridge" credentials: the scripts already do that. If the identity check fails, guide the user to run `aliyun configure` - never ask for AK/SK.

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

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request asks to actually enable/disable transfer acceleration or apply any mutation (Absolute Rule 1), do not execute it - output manual guidance only. When a request falls outside adoption / selection / cross-border attribution / fee semantics (Absolute Rule 6), state the boundary and defer to the responsible skill or manual handling.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket to diagnose.
- **Client endpoint** (`--endpoint`): optional; the endpoint/domain the affected clients currently use - classified to detect whether the accelerate domain was adopted.
- **Client location** (`--client-location mainland|overseas|unknown`): optional; where the affected clients run.
- **Access pattern** (`--access-pattern cross-border|cross-region|same-region|unknown`): optional; drives the accelerator-vs-transfer-acceleration selection advice.
- **Workload** (`--workload hot-cache-read|upload-download|unknown`): optional; refines the selection advice.
- **Expected region** (`--region`): optional; used to derive the query endpoint.
- **Scope** (`--scope adoption|selection|fee|all`): optional; default `all`.
- **UID**: can always be omitted - it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted or re-derived from the bucket location, UID derived), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Adoption decision tree | [references/adoption-decision-tree.md](references/adoption-decision-tree.md) | Not-taking-effect detection matrix, accelerate-domain forms, propagation window, disabled-feature behavior, 502/504 retry, VPN testing caveat |
| M2: Accelerator vs Transfer Acceleration | [references/accelerator-vs-transfer-acceleration.md](references/accelerator-vs-transfer-acceleration.md) | Product selection matrix, the ticket-proven confusion pattern, and the Data Accelerator status-query API boundary (why GetBucketDataAccelerator is never called) |
| M3: Fee fact sheet | [references/fee-facts.md](references/fee-facts.md) | Official fee semantics, per-direction billing item codes, acceleration-fee attribution fields |
| M4: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Orchestration

Symptom routing before running the entry script:
- "enabled but still slow / no speedup" -> `--scope adoption` with `--endpoint <what-the-client-uses>`.
- "accelerator or transfer acceleration, which one" -> `--scope selection` with `--access-pattern` and `--workload`.
- "slow from overseas / cross-border" -> `--scope adoption` with `--client-location overseas --access-pattern cross-border`.
- "why am I paying for acceleration / how is it billed" -> `--scope fee`.
- mixed symptoms -> `--scope all`.

## Execution Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the bucket name, the endpoint the clients currently use, the client location, and the symptom; map the symptom with the Orchestration section above.

### Step 2: Run the Transfer Acceleration Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/oss_transfer_acceleration_diagnosis.py \
    --bucket <name> [--endpoint <client-endpoint>] \
    [--client-location mainland|overseas|unknown] \
    [--access-pattern cross-border|cross-region|same-region|unknown] \
    [--workload hot-cache-read|upload-download|unknown] \
    [--region <region>] [--scope adoption|selection|fee|all]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Classifies the client endpoint (accelerate / accelerate-overseas / malformed / public / internal / custom domain); the query endpoint is always a regioned endpoint because accelerate domains cannot serve control-plane metadata queries.
3. Calls OSS `GetBucketInfo` through the oss2 SDK with the resolved endpoint, carrying the session-id User-Agent and a per-call timeout; on failure falls back to `ListBuckets` (prefix lookup) to locate the bucket's region.
4. Calls `GetBucketTransferAcceleration` (404 `NoSuchTransferAccelerationConfiguration` is measured as status=disabled; other failures degrade with `[WARN]` plus a retry on the bucket's real-region endpoint).
5. Runs the adoption decision tree, the selection matrix and the fee notes, and emits a structured JSON report plus the contract lines `STATUS: OK | DEGRADED | FAIL` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdict and Advise

Read `verdict.adoption` from the report:
- **effective** - feature on + accelerate endpoint in use; relay the 502/504 retry guidance and the ISP-link caveat for cross-border results.
- **not_effective_endpoint_not_replaced** - the classic "enabled but not taking effect" root cause: instruct the user to replace the client endpoint with oss-accelerate.aliyuncs.com (endpoint string without the bucket name) and wait out the ~30-minute propagation window.
- **accelerate_endpoint_without_feature** - the accelerate domain is used while the feature is disabled; requests fail until the user enables the feature in the console (manual action).
- **feature_not_enabled** - nothing is switched on; advise whether enabling is worthwhile based on the access pattern, and state that same-region access should use plain endpoints instead.
- **unknown (DEGRADED/FAIL)** - relay the recorded errors and `NEXT_ACTION` honestly; when every evidence call failed the status is FAIL (exit 1). Fall back to the user-provided console-screenshot/status-description evidence form (Absolute Rule 4) instead of inventing the state.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual fields from the report. Base the conclusion on the script's `status` / `verdict` / `selection` / `billing_notes` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any change).

## Important Notes

- **Enabling alone has no effect**: after switching the feature on, clients MUST also replace their endpoint with the accelerate domain (oss-accelerate.aliyuncs.com); "enabled but still slow" almost always means the endpoint was never replaced (source: help.aliyun.com transfer acceleration FAQ).
- **Endpoint value must not contain the bucket name**: SDK/ossutil Endpoint is exactly `oss-accelerate.aliyuncs.com`; configuring `<BucketName>.oss-accelerate.aliyuncs.com` fails DNS resolution.
- **Propagation window**: enabling/disabling takes about 30 minutes to propagate globally; verify the effect only after the window.
- **Accelerate domains serve object access only**: they support bucket-prefixed third-level domain requests and cannot serve management operations such as ListBuckets; the scripts therefore always query control-plane metadata through a regioned endpoint.
- **Fee semantics**: enabling is free; acceleration traffic is billed separately from and in addition to public internet traffic - using the accelerate domain incurs both, using the plain domain never incurs acceleration fees (source: help.aliyun.com transfer-acceleration-fees).
- **502/504 on the accelerate domain** can be normal automatic path switching; clients should retry with exponential backoff rather than treating it as an outage.
- **Cross-border results are bounded by ISP link quality**: acceleration optimizes the route but cannot fully eliminate cross-border fluctuation; clients testing through a VPN exit from an unexpected location, which distorts the measured effect.
- **Read-only operations**: only GetBucketInfo, GetBucketTransferAcceleration, ListBuckets, and `sts:GetCallerIdentity`; never enables or modifies anything.
- **Data Accelerator status-query boundary (TAC-2)**: this skill never calls `GetBucketDataAccelerator` - first-hand probes measured 403 `EC 0024-00000008` "Configuration is disabled for the current user" on the public endpoint (function gating, not a RAM gap), ConnectTimeout on the intranet-only `oss-data-acc` domain, and no `get_bucket_data_accelerator` method in oss2 2.19.1. `EC 0024-00000008` is **first-hand measured, officially uncatalogued** - it is NOT in the official 0024 EC family (37 codes; `search "0024-00000008"` returns no doc), so never present it as an officially catalogued code; its evidence is the RequestId-level probes (`6A981BB5B636B739365322C1` / `6A981BB55F75A93532097BFA`) recorded in the reference. Check the Data Accelerator state via the console pages (or a user-provided screenshot); transfer acceleration state stays with `GetBucketTransferAcceleration`. See [references/accelerator-vs-transfer-acceleration.md](references/accelerator-vs-transfer-acceleration.md).

## Examples

**Example 1 - enabled transfer acceleration but still slow (transfer acceleration not working)**

> User: "We switched bucket test-agentceping to transfer acceleration but downloads from Germany are still slow (UID 1552974654746705). The app uses endpoint oss-cn-hangzhou.aliyuncs.com."

```bash
python3 scripts/oss_transfer_acceleration_diagnosis.py --bucket test-agentceping --endpoint oss-cn-hangzhou.aliyuncs.com --client-location overseas --access-pattern cross-border
```

Report the measured verdict: if the feature is actually not enabled (`NoSuchTransferAccelerationConfiguration`), state plainly that nothing is switched on yet and give the console enablement guidance plus the endpoint replacement; if enabled but the endpoint is plain, flag the endpoint-not-replaced root cause. Declare auto-filled parameters. If `STATUS: DEGRADED`, relay the errors and `NEXT_ACTION` honestly.

**Example 2 - accelerator vs transfer acceleration selection**

> User: "We configured the OSS accelerator but users overseas still load images slowly - is that the right product?"

```bash
python3 scripts/oss_transfer_acceleration_diagnosis.py --bucket <name> --scope selection --access-pattern cross-border --workload upload-download
```

Relay the selection verdict: cross-border latency is the transfer-acceleration use case; the Data Accelerator only caches hot data within the same region (see references/accelerator-vs-transfer-acceleration.md). Enabling transfer acceleration stays a user console action.

**Example 3 - transfer acceleration fee question**

> User: "Why does my bill contain acceleration traffic fees, and are they charged on top of normal traffic?"

```bash
python3 scripts/oss_transfer_acceleration_diagnosis.py --bucket <name> --scope fee
```

Relay the fee semantics from `billing_notes`: separate per-direction billing items (AccM2M*/AccM2O*/AccO2M*/AccO2O*) that stack on public internet traffic only when the accelerate domain carries the data; detailed bill line-item attribution belongs to the billing skill.

<!-- production-pattern-example -->

**Example N - Acceleration enabled but nothing got faster**

> User: "I turned on transfer acceleration and pointed DNS at the accelerate domain, yet overseas uploads are still slow."

```bash
python3 scripts/oss_transfer_acceleration_diagnosis.py --bucket "my-bucket" --client-location "overseas"
```

Verify the acceleration switch state and that the client endpoint actually uses the accelerate domain; separate the accelerator product from transfer acceleration, and explain that DNS alone does not redirect SDK traffic.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/oss_transfer_acceleration_diagnosis.py` | Transfer acceleration entry: GetBucketInfo + GetBucketTransferAcceleration adoption decision tree + selection matrix + fee notes, with ListBuckets fallback and real-region retry |

CLI options for `oss_transfer_acceleration_diagnosis.py`: `--bucket <name>` (required), `--endpoint <client-endpoint>` (optional), `--client-location mainland|overseas|unknown` (default `unknown`), `--access-pattern cross-border|cross-region|same-region|unknown` (default `unknown`), `--workload hot-cache-read|upload-download|unknown` (default `unknown`), `--region <region>` (optional), `--scope adoption|selection|fee|all` (default `all`).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 | Missing `oss:GetBucketInfo` / `oss:GetBucketTransferAcceleration`, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, run the ListBuckets fallback + real-region retry, point to [references/ram-policies.md](references/ram-policies.md). STATUS follows the evidence gate (see Exit codes): `DEGRADED` (exit 0) if the bucket was still located by a leg, `FAIL` (exit 1) if every evidence leg was denied |
| `NoSuchBucket` / 404 | Bucket name does not exist | Verify spelling and owning account. The bucket does not exist, so GetBucketInfo + the ListBuckets fallback + GetBucketTransferAcceleration all return `not_found` - zero evidence - hence `STATUS: FAIL` (exit 1) with a `NEXT_ACTION` to re-check the bucket name/account (per the TAC-5 exit-code contract, NOT `DEGRADED`; measured 2026-09 with STS role skillsclienttest) |
| `NoSuchTransferAccelerationConfiguration` / 404 | Transfer acceleration never enabled on the bucket | This is the diagnostic finding status=disabled, not a failure - report it as the verdict |
| `EC 0024-00000008` / 403 on a `dataAccelerator` query | Function gating: "Configuration is disabled for the current user" - NOT a RAM permission gap (measured with a ReadOnlyAccess role). This code is **first-hand measured, officially uncatalogued** (NOT in the official 0024 EC family; RequestId-level evidence in [references/accelerator-vs-transfer-acceleration.md](references/accelerator-vs-transfer-acceleration.md)) | Do not chase it with RAM policy changes and never present it as an officially catalogued code; use the console pages or a user-provided screenshot for the Data Accelerator state |
| Network timeout / connection reset | Transient network failure | Report honestly per the evidence gate: `STATUS: DEGRADED` (exit 0) if some evidence still succeeded, `STATUS: FAIL` (exit 1) if every leg timed out; retry later, never conclude "enabled" or "disabled" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the STATUS follows the evidence gate (`DEGRADED`/exit 0 with partial evidence, `FAIL`/exit 1 if every leg failed). Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED` / `FAIL`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the adoption verdict with the actual evidence fields (transfer-acceleration status, endpoint kind, verdict) - no fabricated states.
3. Declare every auto-filled parameter (endpoint default, region retry, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions, and switch to the user-provided console-screenshot/status-description evidence form when the status cannot be queried.
5. Give enablement/configuration suggestions as manual guidance only (this skill never applies changes).
6. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."

