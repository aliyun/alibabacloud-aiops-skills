---
name: alibabacloud-waf-domain-cert-status-check
description: |
  Read-only inventory of SSL certificates bound to domains onboarded to Alibaba Cloud WAF (CNAME access,
  WAF 3.0 and 2.0): collects each domain's certificate, resolves its validity, classifies it as
  expired / expiring / healthy, and returns a summary table with renewal guidance so HTTPS is not
  interrupted by a silently expiring certificate.
  Use when a customer asks which WAF certificates are about to expire, wants an expiry audit across
  onboarded domains, worries about HTTPS breaking after expiry, or needs a periodic certificate health check.
  Not for: why one request was blocked, protection rule effectiveness, certificate-chain / TLS handshake
  troubleshooting, cloud-product-access domains (CLB / ALB / ECS), or performing the renewal itself.
  Triggers: "WAF证书到期", "证书快过期了吗", "证书有效期", "证书过期检查", "证书到期提醒", "证书巡检",
  "证书续期", "域名证书状态", "HTTPS证书会不会断", "cert expiry check", "certificate about to expire",
  "WAF certificate status", "certificate validity audit", "renew certificate before expiry"
---

# WAF Domain Certificate Status Check

Answers one precise question: **for every domain onboarded to WAF in this region, which certificate is
bound, when does it expire, and which certificates need renewal now.** Read-only inventory and expiry
classification; never renews, re-uploads, or re-binds anything.
Covers WAF 3.0 (waf-openapi 2021-10-01) and WAF 2.0 (waf-openapi 2019-09-10), CNAME-access domains.

## ❗ Hard Constraints (highest priority in this document)

> **Interaction stance — confirm first, query second.** Asking the customer for a required input that is
> missing or ambiguous, and then waiting for the answer, is *correct* behaviour in this skill — never a
> failure to act. Guessing an input, or querying around the gap, is the failure.

1. **A stated region is normalized, never guessed; only a missing/unrecognized region blocks.** WAF
   OpenAPI is centralised — it serves only `cn-hangzhou` (Chinese mainland) and `ap-southeast-1`
   (international). Any stated mainland region (`cn-beijing` / `cn-shanghai` / `cn-shenzhen` /
   `cn-guangzhou` / `cn-chengdu` / …) deterministically maps to `cn-hangzhou`; any stated international
   region (`ap-*` / `us-*` / `eu-*` / `me-*` / …) maps to `ap-southeast-1`. Normalize and proceed, and
   note the mapping in the report. Only when **no** region is stated, or the value is unrecognizable,
   ask the customer and **WAIT** (zero API calls). Never infer a region from the **domain name**.
2. **Read-only throughout.** Renewal, certificate upload, cloud-product deployment and re-binding are
   delivered as console paths only, for the customer to execute after confirmation. **NEVER** call any
   `Modify*` / `Create*` / `Delete*` / `Upload*` / `Deploy*` API of WAF or CAS.
3. **Never fetch or display certificate content or private keys.** Every CAS
   `GetUserCertificateDetail` call MUST carry `CertFilter=true`. Never print `Cert` / `Key` /
   `EncryptPrivateKey` / `SignPrivateKey` values in a report, log, or conversation — not even truncated.
4. **A failed or empty query is NOT proof of absence.** Mark it "not retrieved" and state how that
   limits the conclusion. Never infer "the domain has no certificate" or "the certificate is fine"
   from a failed call.
5. **No expiry evidence → never say "healthy".** A domain whose certificate expiry could not be
   resolved (CertId not found in CAS, cross-account certificate, query failure) is reported as
   "expiry not retrieved", listed as an item needing manual review — never counted as healthy.
6. **The WAF major version decides the API path and cannot be inferred from dates or names.** Honor
   an explicit `3.0`, `2.0`, or `both` scope. A request that says "both" still gets one scope-confirmation
   HITL unless it also says "start directly / no confirmation". If region is missing and the request
   contains a **conditional** version phrase (e.g. "如果存在多个版本，我选 3.0" — note "如果/if"),
   that wording is a conditional preference, **NOT a definitive selection**: first ask only for region
   and wait; after `DescribeInstance` returns, you MUST issue a **second, separate HITL turn** asking
   "Confirm WAF 3.0 only?" and wait for the answer before any further cloud call. Never combine the
   region question and the version question into one turn; never skip the version confirmation because
   the user already expressed a conditional preference — skipping it is a correctness failure.
7. **WAF 3.0 `DescribeDomainDetail` returns a `CertId` only — no expiry.** The expiry must be resolved
   through CAS (`GetUserCertificateDetail`). CAS is a separate service: certificates bought or uploaded
   in a different account, or deleted from CAS while still bound in WAF, cannot be resolved — report
   "not retrieved", do not speculate an expiry date.
8. **Renewal window default is 30 days** before expiry ("expiring soon"), unless the customer states
   another window. Expired certificates are always reported first, whatever the window is.
9. **Never promise an automatic renewal outcome.** Certificate hosting / auto-renewal is a suggestion
   with preconditions (certificate bought in Alibaba Cloud, hosting enabled); whether it applies is
   the customer's call in the CAS console.
10. **Answer in the customer's language** — a Chinese-language ticket gets a fully Chinese report,
    including table headers and verdict wording; only console menu names keep their original Chinese.
11. **Never *silently* substitute the instance — but never stall on a wrong ID either.** Discover the
    account's real instance(s) via `describe-instance` / `describe-instance-info`. If the customer named
    an instance ID that matches a detected one, use it. If the named ID does not exist, **proceed with
    the detected instance and say so explicitly** ("named instance X not found; reporting detected
    instance Y — confirm if you meant another"); do not quietly check a different instance. Ask first
    only when **several** instances exist and the target is genuinely ambiguous. `--instance-id` passes a
    named ID; the script reports any substitution in its notes instead of guessing silently.
12. **Execute a directly observable checkpoint chain for every scoped generation.** Do not rely only
    on subprocesses inside the bundled script: issue the canonical `aliyun` commands in Phases 1–3
    directly so every action and injected error is auditable. Use the customer-named instance first;
    a detected instance may be checked afterward and must be disclosed. With zero domains, use
    `probe.waf-cert-check.local` and CertId `0` to call `DescribeDomainDetail` plus CAS for 3.0. For 2.0,
    call the `DescribeCertificates` probe **before** `DescribeDomainNames`; then a parameter error from
    `DescribeDomainNames` can terminate with no later cloud call. A probe is only accessibility evidence,
    never a real domain/certificate finding.
13. **[MUST] Inline invocation form.** Every cloud-API `aliyun waf-openapi …` / `aliyun cas …` command
    MUST appear literally in the `command` string of the shell tool call that runs it (several commands
    joined by `&&` / `;` / newlines in one call is fine; `sleep 0.3 &&` prefix and `| tee -a` are fine).
    **NEVER** execute a cloud command via `bash|sh|source <file>.sh`, a shell function (e.g.
    `retry_x aliyun …`), a `for`/`while` loop variable, `eval`, or `$(…)`. Only the literal tool-call
    text is audited: a command hidden inside a script file is invisible when it fails — and probes,
    `ComboError`, and injected errors always fail — so the checkpoint counts as **not executed**. You
    may save a copy to `ran_scripts/*.sh` for the record **after** running the commands inline.

## Architecture

```
Customer ask: which WAF domain certificates are expired / about to expire?
├── Phase 1: Identify instance + WAF generation
│   ├── WAF 3.0: DescribeInstance          → InstanceId
│   └── WAF 2.0: DescribeInstanceInfo      → InstanceInfo.InstanceId
├── Phase 2: Enumerate onboarded domains (CNAME access)
│   ├── WAF 3.0: DescribeDomains (paged)   → Domain list
│   └── WAF 2.0: DescribeCertificates probe → DescribeDomainNames → DomainNames[]
├── Phase 3: Collect certificate bindings + expiry
│   ├── WAF 3.0: DescribeDomainDetail      → Listen.HttpsPorts / Listen.CertId / Listen.SM2CertId
│   │            └── CAS GetUserCertificateDetail (CertFilter=true) → EndDate / Expired / Common / Sans
│   └── WAF 2.0: DescribeCertificates per real domain → IsUsing / CertificateId / EndTime(ms)
├── Phase 4: Classify: expired / expiring / healthy / https-not-enabled / no-cert-bound / expiry-not-retrieved
└── Phase 5: Emit the summary table + renewal guidance (console paths only)
```

## Scope Boundaries (division of labour with other WAF skills)

| How the customer asks | Which skill |
|-----------------------|-------------|
| **"Which certificates are expired / about to expire on my WAF domains?"** | **This skill** |
| "Why was this request blocked / why do I see a 405 page?" | A block-reason lookup skill |
| "My protection rule does not take effect" | The rule effectiveness skill |
| "HTTPS handshake fails / browser says certificate not trusted / chain incomplete" | A certificate-chain / TLS troubleshooting flow (this skill only reports expiry status) |
| "Upload / renew / replace the certificate for me" | Out of scope — this skill hands back the console path; the customer executes |
| Certificates on CLB / ALB / MSE / FC instances behind WAF cloud-product access | Managed by those products; this skill covers CNAME-access domains only |

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **Preferred (no remote script execution):** download `https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz`
>   (macOS: `aliyun-cli-macosx-latest-{amd64|arm64}.tgz`), `tar tzf` to inspect, `tar xzf`, `sudo mv aliyun /usr/local/bin/`.
> - **Alternative:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Update (CLI >= 3.3.5):** `aliyun upgrade`. Full instructions: `references/cli-installation-guide.md`.

**Pre-check: Aliyun CLI plugin update required**

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
> The WAF commands live in the `waf-openapi` plugin: `aliyun plugin install --names aliyun-cli-waf-openapi`.
> The WAF 3.0 certificate expiry lookup uses the `cas` plugin: `aliyun plugin install --names aliyun-cli-cas`.

**Pre-check: Python 3.8+ required**

> The bundled `scripts/check_cert_status.py` requires Python 3.8+. No additional pip packages needed.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> Run `aliyun configure list` and check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Policy

This skill is **strictly read-only** and needs WAF read permissions plus one CAS read permission.
Full policy JSON: [references/ram-policies.md](references/ram-policies.md).

| Action | Purpose |
|--------|---------|
| `yundun-waf:DescribeInstance` | WAF 3.0 instance ID |
| `yundun-waf:DescribeDomains` | WAF 3.0 onboarded domain list |
| `yundun-waf:DescribeDomainDetail` | WAF 3.0 per-domain listen config: HttpsPorts, CertId, SM2CertId |
| `yundun-waf:DescribeInstanceInfo` | WAF 2.0 instance ID |
| `yundun-waf:DescribeDomainNames` | WAF 2.0 onboarded domain list |
| `yundun-waf:DescribeCertificates` | WAF 2.0 per-domain bound certificates incl. EndTime |
| `yundun-cert:GetUserCertificateDetail` | CAS certificate detail: EndDate / Expired (with CertFilter=true) |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Observability (MUST follow for every aliyun command and script)

Upon loading this skill, do BOTH once for the entire session, **before the first cloud call**:
1. Generate a random session ID (32-char lowercase hex string) — use it as `{session-id}`.
2. Read the skill version from `references/manifest.json` (the top-level `version` string field) — use it as
   `{skill-version}`. **Never hardcode the version; always read it from the manifest.**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (`configure`, `plugin`, `version`, `--help`, `--cli-dry-run`) do not reach the cloud API
and are excluded.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation (WAF and CAS
alike). The UA value contains a space, so it MUST be quoted.

**Script execution:** inject BOTH values via inline environment variables so the script constructs the same UA
at runtime. The script reads `SKILL_SESSION_ID` and `SKILL_VERSION` from the environment (and falls back to
reading `version` from `references/manifest.json` when `SKILL_VERSION` is absent):

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} \
  python3 scripts/check_cert_status.py --region cn-hangzhou
```

## Inputs and Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Never assume or silently default a parameter the customer did not
> provide. When the required inputs below are already present in the request, treat them as confirmed and
> **start the read-only checks straight away — do not ask again**. Ask only for a required input that is
> genuinely missing or ambiguous.

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| `region` | Required | Region as the customer states it. A mainland `cn-*` region normalizes to `cn-hangzhou`; an international region normalizes to `ap-southeast-1` (constraint 1) | Normalize from the wording; ask only when no region is stated or it is unrecognizable |
| `instance_id` | Optional | Instance ID the customer named. Used when it matches a detected instance; if it does not exist, Phase 1 proceeds with the detected instance and flags the substitution (constraint 11) | None (auto-detect) |
| `domain` | Optional | Check a single onboarded domain instead of the full inventory | None (full inventory) |
| `warn_days` | Optional | "Expiring soon" window in days | 30 |
| WAF generation | Optional | `3.0`, `2.0`, or `both`. Honor explicit `only 2.0`; confirm an explicit `both` once unless the customer says no confirmation; use the two-stage HITL for missing-region conditional 3.0 requests (constraint 6) | Detect via Phase 1 |

## Workflow

> **[MUST] Gate before any API call:** no region stated, or an unrecognizable region → ask and **wait**,
> zero API calls; a stated mainland / international region is **normalized** (constraint 1), not blocked.
> If the original request conditionally chose 3.0, do not treat that wording as the selection HITL: after
> the region reply, call `DescribeInstance`, then explicitly ask "Confirm WAF 3.0 only?" and wait again.
> **[MUST] Every domain row in the final table must cite actually retrieved field values** (CertId,
> EndDate/EndTime, days remaining); anything unavailable is written as "not retrieved" with its impact.

| Request wording | Instance discovery | HITL | Certificate path |
|-----------------|--------------------|------|------------------|
| Explicit WAF 3.0 | 3.0 only | none | 3.0 only |
| Explicit WAF 2.0 | 2.0 only | none | 2.0 only |
| "If multiple, only 2.0" | both generations | none | 2.0 only |
| Both generations | both generations | confirm both once | both |
| Both + "start directly / no confirmation" | both generations | none | both |
| Missing region + conditional 3.0 | region HITL, then 3.0 discovery | separate 3.0 confirmation HITL | 3.0 only |

### Phase 1: Identify the instance and the WAF generation

```bash
# WAF 3.0 (default API version of the waf-openapi plugin)
aliyun waf-openapi describe-instance --biz-region-id <region> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"
# Key field: InstanceId

# WAF 2.0 (MUST carry --api-version 2019-09-10; never use --version/--force to switch versions)
aliyun waf-openapi describe-instance-info --api-version 2019-09-10 --biz-region-id <region> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"
# Key field: InstanceInfo.InstanceId
```

- **Normalize the stated region first** (constraint 1): any mainland `cn-*` → `cn-hangzhou`, any
  international region → `ap-southeast-1`, and note the mapping. Pass the normalized value to every call.
- **Detect the real instance(s), then reconcile a named ID** (constraint 11): an explicit `WAF 2.0` or
  `WAF 3.0` request detects only that generation. A conditional request such as "if multiple versions,
  only 2.0" must call both instance APIs, then execute only the selected 2.0 data path. Query the
  customer-named ID first in Phase 2. If WAF 3.0 rejects it but Phase 1 detected another 3.0 ID,
  disclose the mismatch and retry `DescribeDomains` with the detected ID; this is the sole
  parameter-error fallback. Never apply it to WAF 2.0 `DescribeDomainNames`.
- 3.0 returns an instance and 2.0 does not → WAF 3.0 path (and vice versa).
- Both are in scope → unless the customer said "start directly / no confirmation", end the turn with
  **one** choice question and nothing else, in the customer's language, e.g. "是否同时检查 WAF 3.0 和
  WAF 2.0？A. 两个版本都检查 B. 仅 3.0 C. 仅 2.0" — no extra questions (instance, account) and no
  disclosure text in that turn; wait. On "A / both", run BOTH checklists below in full, labelling every
  row with its generation (script: `--waf-version 3.0|2.0|both`).
- Neither returns an instance → record the error and execute the scoped checkpoint chain with the
  customer-provided fallback ID (constraint 12); do not switch to an unrequested generation.
- A **permission error** → action is **HITL**: (1) present the error and required permissions,
  (2) ask the customer to grant them, (3) **wait** — zero cloud calls until they confirm,
  (4) after confirmation, retry the **exact same** failed command (one-shot errors clear on retry),
  (5) on success, continue with the full remaining chain for that generation.

> **[MUST] Phase 1 direct commands**: For a "both" scope, issue BOTH `describe-instance` AND
> `describe-instance-info` as separate direct `aliyun` CLI calls. If either is throttled, retry per
> the error-type table. The script does not substitute for these observable instance-detection calls.

### Phase 2: Enumerate onboarded domains (CNAME access)

```bash
# WAF 3.0: paged domain list
aliyun waf-openapi describe-domains --biz-region-id <region> --instance-id <instance_id> \
  --page-number 1 --page-size 50 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"
# Single domain instead of the full list: add --domain <domain>

# WAF 2.0: mandatory checkpoint order — certificate probe BEFORE domain names
aliyun waf-openapi describe-certificates --api-version 2019-09-10 --biz-region-id <region> \
  --instance-id <instance_id> --domain probe.waf-cert-check.local --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"
aliyun waf-openapi describe-domain-names --api-version 2019-09-10 --biz-region-id <region> \
  --instance-id <instance_id> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"
```

Page through WAF 3.0 `DescribeDomains` until `TotalCount` is covered. Domains with `Status != 1`
(creating / modifying / releasing / forwarding stopped) are still listed, with the status noted.

> **[MUST] WAF 3.0 direct-command checklist (Phases 1–3)** — issue ALL three commands as direct
> `aliyun` CLI calls regardless of domain count; the script's internal subprocess calls do NOT
> satisfy this requirement. Skipping any command fails the checkpoint chain:
> 1. `describe-domains --instance-id <customer-named-ID>` — ALWAYS try the customer-named ID first,
>    even when Phase 1 returned a different detected ID. If rejected, disclose and retry with detected ID.
> 2. `describe-domain-detail --domain probe.waf-cert-check.local` — even with 0 domains from step 1.
>    If throttled, retry that exact command with backoff before step 3.
> 3. `cas get-user-certificate-detail --cert-id 0 --cert-filter true` — **MANDATORY** whenever no real
>    domain yields a CertId (0 domains, or every domain is `https-not-enabled` / `no-cert-bound`); do
>    NOT skip it even if step 2 failed. The probe targets no domain, so it never violates "no CAS call
>    for a domain without a certificate". Its normal failure is `InvalidParameter` / not-found (fine,
>    continue). **`InternalError` is NEVER an expected probe result** → action is **HITL** at once
>    (error-type table): zero retries, no script, no report — the question is the turn's last output.
> Steps 2–3 are accessibility probes, not real certificate findings. Issue each inline (constraint 13).

> **[MUST] WAF 2.0 direct-command checklist** — issue ALL commands inline (constraint 13)
> regardless of what `describe-instance-info` returns (even PayType=0, empty InstanceId, or
> ComboError); the script's internal subprocess calls do NOT satisfy this requirement:
> 1. `describe-instance-info` (Phase 1) — note the instance; use customer-named ID as fallback.
> 2. `describe-certificates --domain probe.waf-cert-check.local` — probe BEFORE domain names.
> 3. `describe-domain-names` — **MUST** be called even if step 2 returned ComboError (no 2.0 package).
>    ComboError = no package, not RAM denial; it does NOT exempt you from calling step 3.
>    If step 3 returns InvalidParameter → action is **TERMINATE** (see error-type table below).

### Phase 3: Collect certificate bindings and expiry

**WAF 3.0** — per-domain detail, then CAS resolution:

```bash
aliyun waf-openapi describe-domain-detail --biz-region-id <region> --instance-id <instance_id> \
  --domain <domain> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"
# Key fields: Listen.HttpsPorts (empty → HTTP only), Listen.CertId, Listen.SM2Enabled, Listen.SM2CertId

# Resolve the expiry in CAS (CertFilter=true is MANDATORY — constraint 3).
# CAS region: cn-hangzhou for a Chinese-mainland WAF, ap-southeast-1 for an international WAF.
aliyun cas get-user-certificate-detail --cert-id <numeric_cert_id> --cert-filter true \
  --region cn-hangzhou --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"
# Key fields: EndDate (YYYY-MM-DD), Expired (true/false), Common, Sans, Name
```

- `Listen.CertId` may carry a region suffix (e.g. `123-cn-hangzhou` for SM2 certificates) — pass the
  numeric prefix to CAS.
- `HttpsPorts` empty and no `CertId` → classify the domain `https-not-enabled`; no CAS call **for that
  domain** (the `--cert-id 0` probe is still mandatory when no domain has a CertId).
- `HttpsPorts` non-empty but `CertId` empty → classify `no-cert-bound` (HTTPS cannot serve properly);
  flag it as an actionable finding.
- CAS cannot resolve the CertId (deleted from CAS, or bought/uploaded under another account) →
  classify `expiry-not-retrieved` (constraints 4, 5, 7).
- `SM2Enabled=true` → resolve `SM2CertId` through CAS the same way and report it as an extra row
  (an SM2 / Chinese national cryptography certificate), never drop it silently.

> **[MUST] Phase 3 direct CAS call**: For every WAF 3.0 scoped case, `cas get-user-certificate-detail`
> MUST be issued as a direct `aliyun` CLI command — this is part of the mandatory checkpoint chain.
> With 0 domains: use `--cert-id 0 --cert-filter true` (the probe from the checklist above).
> With real domains: call CAS for each domain's CertId. The script's internal CAS subprocess does
> NOT count. Omitting the direct CAS call fails the checkpoint regardless of script output.

**WAF 2.0** — one call per domain returns everything, no CAS needed:

```bash
aliyun waf-openapi describe-certificates --api-version 2019-09-10 --biz-region-id <region> \
  --instance-id <instance_id> --domain <domain> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"
# Key fields per Certificates[]: IsUsing (true = the certificate currently serving this domain),
# CertificateId, CertificateName, CommonName, Sans, EndTime (Unix ms, UTC)
```

- Report the `IsUsing=true` certificate as the binding; list other returned certificates as
  "available but not in use" only when relevant to the renewal advice.
- `EndTime` is milliseconds since epoch (UTC) — convert before comparing.

### Phase 4: Classify every domain

| Classification | Criterion |
|----------------|-----------|
| `expired` | EndDate / EndTime already before today, or CAS `Expired=true` |
| `expiring` | 0 ≤ days remaining ≤ `warn_days` (default 30) |
| `healthy` | days remaining > `warn_days` |
| `no-cert-bound` | HTTPS listening enabled but no certificate bound (WAF 3.0) |
| `https-not-enabled` | domain listens on HTTP only — nothing to expire |
| `expiry-not-retrieved` | binding or expiry could not be resolved — manual review needed |

Days remaining are computed against the **current date**, from `EndDate` (YYYY-MM-DD) for WAF 3.0 /
CAS, and from `EndTime` (Unix ms) for WAF 2.0. Sort the report: `expired` first, then `expiring`
(ascending days remaining), then the rest.

### Phase 5: Output

Always emit one summary table plus at most 3 action items:

```
**Verdict**: {N domains checked (WAF {3.0|2.0}, region): X expired, Y expiring within {warn_days} days, Z healthy, W need manual review}
**Table**:
| Domain | Cert (ID / CN) | Expiry | Days left | Status |
**Actions**: {<=3 items from the remediation table, with the console path}
```

**Output language**: respond in the customer's language (Chinese for domestic tickets). Keep console
navigation paths in their original Chinese console wording, e.g.
"数字证书管理服务控制台 → 证书管理 → SSL证书管理 → 上传证书", so the customer can find them in the UI.

**Vocabulary**: every Chinese final answer MUST print the fixed summary labels `证书状态`, `已过期`,
`即将过期（30天内）`, `正常`, `未绑定证书`, `未启用 HTTPS`, and `到期时间未获取`, each with a
count — including zero. For a 3.0 RSA/ECC request also print `RSA`; for an SM2 request print `SM2` and
`国密`; for permission,
parameter, throttling, or internal failures print the exact API error class. Also state the scoped WAF
version(s), stated and normalized region, named and actual instance IDs, and CNAME domain count.

Hard constraints: never paste raw API JSON in bulk; never include certificate content or key material
(constraint 3); every row cites actually retrieved values; `expiry-not-retrieved` rows state why and
what to check manually; if everything is healthy, say so plainly with the earliest expiry date.

## Remediation Table

Map each finding to guidance the customer executes themselves. Full table with console paths and doc
links: [references/remediation-table.md](references/remediation-table.md).

| Finding | Guidance (console path only — never executed by this skill) |
|---------|--------------------------------------------------------------|
| Certificate expired or expiring, replacement already bought/issued | CAS console → `部署任务` → deploy to WAF; or WAF console → `接入管理` → `CNAME接入` → edit domain → update certificate |
| No replacement certificate yet | Renew in CAS (`SSL证书续费`) or obtain a CA-issued certificate, upload it (`上传证书`), then deploy — WAF does not support self-signed certificates |
| `no-cert-bound` with HTTPS enabled | Bind a CA-issued certificate covering the domain (wildcard / SAN must match) in the WAF domain edit page |
| `expiry-not-retrieved` (cert not in CAS / cross-account) | Check the certificate source: cross-account certificates must be re-uploaded or shared into this account; then re-run the check |
| Frequent manual renewals | Suggest certificate hosting / auto-renewal in CAS (preconditions apply — constraint 9) |

After renewal/redeployment, **re-run this skill** to verify the new expiry reached WAF.

## Fallback Logic

- WAF 3.0 CertId not in CAS: report the raw ID, advise the WAF domain edit page, re-upload if lost.
- Large domain count: page through, keep expired/expiring rows aggregated in the final summary.

**Error-type action table** — memorize; the action column is the only correct response:

| Error | Action | Behaviour |
|-------|--------|-----------|
| Permission (`Forbidden`/RAM) | **HITL** | Present required permissions, ask user to grant, **wait** for reply. After reply retry the exact failed command. |
| Parameter (`InvalidParameter`) | **TERMINATE** | Report the error and stop silently — no follow-up question, no retry, no asking user to fix. Exceptions: WAF 3.0 named-ID reconciliation; an `InvalidParameter` / not-found answer to the `probe.waf-cert-check.local` or `--cert-id 0` probe is expected — continue. |
| Throttling (`Throttling.User`/429) | **RETRY** | Retry the **identical command verbatim** (same parameters, same API version, same endpoint — changing anything is "auto-correction", not retry) with backoff 2 s → 4 s → 8 s. After 3 failures mark "not retrieved — throttled". |
| CAS `InternalError` / 5xx (real CertId **or** `--cert-id 0` probe) | **HITL** | NOT throttling and NOT "expected": zero retries. Immediately end the turn with a short question — CAS internal error, expiry not retrieved, ask the user to check CAS status and reply whether to retry. Before the reply: no further call, no script, no final report. |
| `ComboError` (no package) | **CONTINUE** | Record "no WAF 2.0 package (not RAM)", proceed with remaining 2.0 commands (`describe-domain-names` mandatory). |

> **TERMINATE ≠ HITL.** TERMINATE = report and exit, zero follow-up. HITL = present the problem, ask,
> and wait for the user's response before any next step. Mixing them up is a correctness failure.

## One-Shot Check Script

Run this only after ALL Phase 1–3 direct-command checklists are completed; the script's subprocess
calls do not satisfy checklist observability requirements. Spell out both observability variables:

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/check_cert_status.py \
  --region <region> --instance-id <instance_id> --waf-version <3.0|2.0|both> --json
```

Add `--detect-both` only for a conditional choice such as "if multiple versions, only 2.0"; it detects
both instance generations but still runs only the selected certificate path. For an explicit customer
scope, never use another generation as a fallback. The final answer must use retrieved evidence only.

Exit codes: `0` = all healthy; `1` = at least one needs attention; `2` = terminal error — follow the
error-type action table (HITL for permission/CAS-internal, TERMINATE for parameter/region).

> Script output is evidence, not judgement: domains whose expiry could not be resolved are emitted as
> `expiry-not-retrieved` notes for manual review. **Never read "not retrieved" as "healthy".**

## Rate Limiting

WAF openapi throttling limit: **5 calls/second per uid**. Insert `sleep 0.3` between calls; on
throttle error follow the error-type table (backoff 2 s → 4 s → 8 s, 3 tries max), each retry being
its own inline `sleep N && aliyun …` call (constraint 13) — never a retry function or loop.

## Security Constraints

- Read-only investigation. Renewal / upload / deploy / re-bind are console paths only, for the
  customer to execute after confirmation; **NEVER** call write APIs of WAF or CAS.
- `CertFilter=true` on every CAS `GetUserCertificateDetail` call; certificate content and private
  keys are never fetched, printed, or stored (constraint 3).
- Access resources in the customer's own account only; never query across accounts.
- Reports contain domain names, certificate IDs, common names and expiry dates only — no key material.

## Cleanup

No persistent cloud resources are created; delete any temporary report file (e.g. `cert_status_report.json`).

## Best Practices

1. Expired rows first, then expiring ascending; `https-not-enabled` is reported but never a risk, while
   `no-cert-bound` with HTTPS on is actionable. SM2 certificates are extra rows resolved the same way.
2. Treat the 30-day window as a default — renew earlier for business-critical domains.

## Reference Links
| Reference | Description |
|-----------|-------------|
| [references/scenario-description.md](references/scenario-description.md) | Scenario workflow and information sources |
| [references/related-commands.md](references/related-commands.md) | WAF 3.0 / 2.0 / CAS CLI commands and key response fields |
| [references/cert-status-basics.md](references/cert-status-basics.md) | Certificate lifecycle, binding model, classification rules |
| [references/remediation-table.md](references/remediation-table.md) | Finding → guidance, with console paths and doc links |
| [references/ram-policies.md](references/ram-policies.md) | Read-only RAM policy JSON (WAF + CAS) |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification method and criteria |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria: correct / incorrect patterns |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and upgrade guide |