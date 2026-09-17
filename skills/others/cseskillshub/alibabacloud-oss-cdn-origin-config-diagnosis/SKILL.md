---
name: alibabacloud-oss-cdn-origin-config-diagnosis
description: |
  Read-only diagnostics for CDN back-to-origin to OSS. Use when CDN
  fetching from an OSS origin fails or looks wrong: back-to-origin 403
  on a private bucket, traffic bypassing the CDN straight to OSS, wrong
  origin host or port, or a CDN domain that is offline or never
  configured. Checks configuration and attributes the cause; never
  changes any CDN or OSS setting.
  Triggers: "CDN back-to-origin 403", "private bucket CDN origin",
  "traffic bypasses CDN", "origin host misconfigured", "CDN domain
  offline", "origin port check", "OSS origin authorization".
  Do NOT use for refresh/preload tasks (use
  alibabacloud-cdn-refresh-preload), CDN traffic anomaly analysis (use
  alibabacloud-cdn-traffic-anomaly), OSS endpoint selection or
  internal-endpoint errors (use
  alibabacloud-oss-endpoint-internal-diagnosis), or OSS billing (use
  alibabacloud-oss-billing-diagnosis).
---

# OSS CDN Origin Configuration Diagnosis

Diagnose Alibaba Cloud CDN back-to-origin problems where the origin is an OSS bucket: "CDN back-to-origin returns 403 on my private bucket", "my users reach the OSS bucket host directly instead of the CDN", "origin host header looks wrong", "the CDN domain is offline / not configured".

Core approach: verify the caller identity, query the CDN domain record and its back-to-origin configuration (read-only), cross-check the OSS origin bucket metadata (ACL, owner, region) through oss2, then attribute the symptom to one of the branches: private-bucket origin authorization missing, traffic bypassing the CDN, origin host/port misconfigured, or domain stopped / not configured. This skill only checks and advises; it never executes any CDN or OSS change.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating CDN or OSS API — e.g. origin configuration changes, domain start/stop, `PutBucketPolicy`, ACL changes, or any refresh/preload submission. This includes commands "for the user to run manually". If the user asks to change the origin or enable authorization, only output manual guidance and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All diagnostics MUST be performed by running the scripts under `scripts/` (`origin_config_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own aliyun CLI / SDK / curl commands against the CDN or OSS control plane or bypassing the scripts — the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. CDN/STS queries rely on the aliyun CLI default credential chain; OSS queries rely on the environment variables of the default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by the CDN domain queries and OSS GetBucketInfo. If a query fails or returns empty, record it and state the limitation — never invent origin configurations, ACL values, or authorization states. Notably, whether a private-bucket origin authorization is already enabled CANNOT be read by this skill; only advise verifying it.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps, and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line — never silently skip or abort without a report. A domain that cannot be found may simply have been cleaned up; report it as the "not configured / deleted" branch, not as an internal failure.
6. **SCOPE BOUNDARY:** This skill only answers back-to-origin configuration and attribution questions. It does NOT handle CDN cache/refresh/preload effectiveness, CDN traffic anomaly billing analysis, OSS endpoint selection errors, HTTPS certificate problems, or ICP filing — for such requests, state the boundary and route to the owning skill or manual guidance.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Trigger Conditions

Trigger this skill when the user reports any of: CDN back-to-origin 403 against an OSS origin, a private bucket used as CDN origin, traffic bypassing the CDN and hitting OSS directly, origin host misconfigured, origin port problems, or a CDN domain that is offline / stopped / not configured. Chinese equivalents (e.g. questions about back-to-origin 403, private-bucket origin authorization, traffic not going through CDN, or origin Host configuration) map to the same trigger set.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured output (`status` / `findings` / `recommendations` / `next_action`), interpret it, and compose the user-facing answer; do not re-implement the queries or call CDN/OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-cdn-origin-config-diagnosis`
- **skill-version**: read at runtime from `references/manifest.json` (`version`), the single place where this skill's version is declared. It is never hardcoded, guessed or reused: the entry script resolves and validates it **before the first cloud call** and stops with `STATUS: FAIL` (exit 1) when the manifest is missing or its `version` is invalid.
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every aliyun CLI call (`--user-agent`) and every OSS SDK request (User-Agent header) of that run, so all calls of one diagnosis can be correlated.

The shared client layer (`scripts/_oss_client.py`) implements this automatically: the session-id is generated lazily on the first call of each run and cached for the rest of the run, and the skill-version is resolved lazily from `references/manifest.json` on the first User-Agent build.

## Credentials

Credentials are resolved exclusively by the default credential chain:
- CDN/STS queries (aliyun CLI plugin mode): the CLI default credential chain (environment or `~/.aliyun/config.json` profile).
- OSS origin-bucket metadata (Python oss2 SDK): the environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and optionally `ALIBABA_CLOUD_SECURITY_TOKEN` (STS sessions).

Do not read, print, or pass AK/SK/STS tokens explicitly. If the identity check fails, guide the user to configure the credential chain — never ask for AK/SK.

### aliyun CLI version requirement

The scripts shell out to the aliyun CLI (at minimum the `aliyun sts get-caller-identity` identity pre-check), which MUST be **version 3.3.3 or newer**: older builds resolve the default credential chain differently and can drop the STS session token. Verify the installed version and upgrade it before the first run:

```bash
aliyun version        # must print 3.3.3 or newer (measured with 3.4.5)
aliyun upgrade --yes  # upgrade the installed CLI in place to the latest version
```

If the CLI is not installed at all, install the Alibaba Cloud CLI package for the host OS from the official release channel and then run `aliyun configure` (the profile stays in `~/.aliyun/config.json`; this skill never asks for AK/SK). When the CLI is missing, too old to upgrade, or unauthenticated, the identity pre-check degrades instead of aborting: `scripts/_oss_client.py` logs `[WARN] identity pre-check failed: ...` on stderr, records the empty UID, and the diagnosis still runs to a conclusion, because the identity label is traceability only and never evidence.

```bash
SKILL_DIR=~/.qoderwork/skills/alibabacloud-oss-cdn-origin-config-diagnosis
cd $SKILL_DIR

# Verify caller identity (informational only; credentials always come from the default chain)
python3 scripts/sts_token.py
```

## User Confirmation

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: any request to actually change an origin, start/stop a domain, or enable an authorization is refused as out of scope, with manual guidance only.

## Input Parameters

- **Accelerated domain** (`--domain`): required; the CDN-accelerated domain to diagnose.
- **User-reported origin host** (`--user-origin-host`): optional; the host the user's traffic is addressed to (e.g. `<bucket>.oss-<region>.aliyuncs.com`). When provided, the bypass-detection branch compares it with the CDN-configured origin.
- **UID** (`--uid`): can always be omitted — the caller UID is derived via `aliyun sts get-caller-identity` and used as a traceability label plus the same/cross-account origin attribution. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (UID derived, origin host inferred), the Agent MUST explicitly declare this in the response or report metadata, e.g. "UID auto-derived via sts GetCallerIdentity: 1552974654746705".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Origin authorization playbook | [references/origin-auth-playbook.md](references/origin-auth-playbook.md) | Private-bucket back-to-origin authorization: three methods (bucket policy, private-bucket authorization via STS, origin authentication), same-account vs cross-account |
| M2: Bypass detection | [references/bypass-detection.md](references/bypass-detection.md) | Detect traffic that bypasses the CDN and reaches OSS directly |
| M3: Origin config checklist | [references/origin-config-checklist.md](references/origin-config-checklist.md) | Origin host / port / domain-state checklist and error routing |
| M4: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Orchestration

1. Run `scripts/sts_token.py` to verify identity and derive the UID (skip only when already verified in this session).
2. Run `scripts/origin_config_diagnosis.py --domain <d> [--user-origin-host <host>]` — one entry call covers all branches (domain state, origin host/port, private-bucket attribution, bypass).
3. Interpret `findings` / `recommendations`; consult the matching reference module for the advice text.
4. Compose the final report per the Final Answer Contract below.

## Execution Flow

### Step 1: Confirm Identity and Collect Inputs

```bash
cd $SKILL_DIR && python3 scripts/sts_token.py
```

Collect the accelerated domain and, if the user has it, the origin host their traffic actually uses. UID is auto-derived; declare any auto-fill.

### Step 2: Run the Origin Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/origin_config_diagnosis.py \
    --domain <accelerated-domain> [--user-origin-host <host>] [--uid <UID>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Queries `aliyun cdn describe-cdn-domain-detail --domain-name <d>` — domain state (online/offline), CNAME, origin sources. `InvalidDomain.NotFound` routes to the "not configured / deleted" branch.
3. Queries `aliyun cdn describe-user-domains` — account domain inventory for candidate suggestions when the domain is not found.
4. Queries `aliyun cdn describe-cdn-domain-configs --domain-name <d> --function-names set_req_host_header` — the configured back-to-origin Host.
5. For each OSS-shaped origin, calls OSS GetBucketInfo through oss2 (ACL, owner, region) and attributes: private-bucket authorization required, same-account vs cross-account, region consistency, origin host/port sanity.
6. If `--user-origin-host` is given, compares it with the configured origins (bypass detection).
7. Emits the structured report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Findings and Advise

- **PRIVATE_ORIGIN_AUTH_REQUIRED / PRIVATE_ORIGIN_CROSS_ACCOUNT** — a 403 on back-to-origin is expected until the authorization exists; advise per [references/origin-auth-playbook.md](references/origin-auth-playbook.md). State clearly that this skill cannot read the authorization state itself.
- **DIRECT_OSS_ACCESS** — the reported host is an OSS endpoint, so traffic bypasses the CDN; advise per [references/bypass-detection.md](references/bypass-detection.md).
- **ORIGIN_HOST_MISMATCH / ORIGIN_HOST_DEFAULT / ORIGIN_PORT_SUSPECT** — advise per [references/origin-config-checklist.md](references/origin-config-checklist.md).
- **ORIGIN_INTERNAL_ENDPOINT** — the origin content is an OSS internal endpoint (`oss-<region>-internal.aliyuncs.com`), reachable only from same-region Alibaba Cloud intranet clients; public CDN nodes cannot back-to-origin through it — advise switching to the public endpoint (checklist §2).
- **ORIGIN_ACCELERATE_ENDPOINT** — the origin uses the transfer-acceleration endpoint (`oss-accelerate[-overseas].aliyuncs.com`); this is the official CDN + transfer-acceleration dual-acceleration architecture, NOT a misconfiguration; the region-consistency check does not apply (checklist §2).
- **DOMAIN_NOT_ONLINE / DOMAIN_NOT_FOUND / NO_ORIGIN_CONFIGURED** — domain-state branch; advise re-enabling or verifying the domain/account.
- **DEGRADED report** — relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent configuration values.

## Important Notes

- **Private-bucket authorization is not observable here**: GetBucketInfo reveals the ACL and owner, not whether CDN private-bucket authorization is enabled. Never claim the authorization "is missing" as a fact — phrase it as "403 occurs unless the authorization is in place; verify it".
- **Offline domains**: a stopped/offline domain produces any back-to-origin symptom; check the domain state before deeper attribution. Test assets may be cleaned up over time, so treat "not found" as a legitimate branch.
- **Cross-account origins**: when the origin bucket belongs to another account, GetBucketInfo is denied (403) by design; degrade with `[WARN]` and advise the cross-account authorization path from the bucket owner side.
- **Read-only operations**: only DescribeUserDomains / DescribeCdnDomainDetail / DescribeCdnDomainConfigs, OSS GetBucketInfo, and sts GetCallerIdentity; never modifies anything.

## Examples

**Example 1 — back-to-origin 403 on a private bucket origin**

> User: "My CDN domain test234.pier39.cn pulls from my OSS bucket and gets 403. UID 1552974654746705."

```bash
python3 scripts/origin_config_diagnosis.py --domain test234.pier39.cn
```

Relay the findings (origin bucket private, same account), advise verifying the private-bucket back-to-origin authorization per the playbook, and declare the auto-derived UID.

**Example 2 — traffic bypasses the CDN**

> User: "Our images are still served from mybucket.oss-cn-shanghai.aliyuncs.com, not through the CDN."

```bash
python3 scripts/origin_config_diagnosis.py --domain cdn.example.com \
    --user-origin-host mybucket.oss-cn-shanghai.aliyuncs.com
```

Report the DIRECT_OSS_ACCESS finding and the bypass-detection guidance (point clients at the accelerated domain, verify the CNAME record).

**Example 3 — CDN domain offline or not configured**

```bash
python3 scripts/origin_config_diagnosis.py --domain stopped.example.com
```

Report DOMAIN_NOT_ONLINE / DOMAIN_NOT_FOUND with the re-enable / verify-account guidance; on DEGRADED, relay the recorded errors honestly.

<!-- production-pattern-example -->

**Example N — ESA or CDN fronting a private OSS bucket returns 403 on origin fetch**

> User: "Traffic through my acceleration domain fails to fetch from OSS; direct access to the bucket endpoint works."

```bash
python3 scripts/origin_config_diagnosis.py --domain "cdn.example.com" --json
```

Report whether back-to-origin Host equals the bucket's public endpoint and whether private-bucket origin auth is required, then say which single switch to fix -- do not let the customer add redundant authorization or SNI options.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/origin_config_diagnosis.py` | Entry: CDN domain state + origin host/port check + private-bucket attribution + bypass detection, with degradation |

CLI options for `origin_config_diagnosis.py`: `--domain <d>` (required), `--user-origin-host <host>` (optional, bypass branch), `--uid <uid>` (optional, informational), `--json` / `--quiet`.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Default credential chain not configured | Configure the aliyun CLI / environment credential chain; never ask the user for AK/SK |
| `InvalidDomain.NotFound` | Domain not configured under this account, deleted, or wrong account | Report the not-configured branch; verify spelling and the owning UID |
| `Forbidden` / RAM denial on CDN queries | Caller lacks the CDN read actions | Record `[WARN]`, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| OSS 403 on GetBucketInfo | Origin bucket owned by another account (expected) or missing oss read permission | Degrade gracefully; advise the cross-account authorization path |
| Network timeout | Transient failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

**Exit-code contract** (unified with the sibling OSS skills): exit `0` means the diagnosis produced a conclusion — both `STATUS: OK` and `STATUS: DEGRADED` exit 0 ("a conclusion was produced successfully"); exit `1` is reserved for FAIL cases where no diagnosis can run at all (invalid `--domain` input, aliyun CLI missing on PATH). Upstream automation MUST NOT treat a `DEGRADED` run as a failure via exit codes — read the `STATUS:` line / `status` field of the report instead.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the root cause with the actual evidence fields (domain state, origin content, origin Host, bucket ACL/owner) — no fabricated values.
3. Declare every auto-filled parameter (UID derivation, inferred host).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Give every configuration change as manual guidance only (this skill never applies changes), and for private buckets clearly state that the authorization state itself is not readable by this skill.
6. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."

