---
name: alibabacloud-oss-static-website-diagnosis
description: |
  Read-only diagnosis of OSS static website hosting: hosting config checks
  (homepage / 404 rules, IndexDocument / ErrorDocument),
  "website opens as a download" attribution, and domain filing (ICP) guidance.
  Triggers:
  "static website shows download",
  "index.html not rendered",
  "website hosting config",
  "404 page rule",
  "static site domain filing",
  "ICP filing for OSS domain",
  "static site opens as download",
  "custom domain filing".
  Do NOT use for hotlink protection, domain binding procedures or generic
  default-domain direct access links (use
  alibabacloud-oss-direct-access-link-diagnosis), endpoint selection (use
  alibabacloud-oss-endpoint-internal-diagnosis), image processing (use
  alibabacloud-oss-image-processing-diagnosis), browser upload CORS (use
  alibabacloud-oss-browser-upload-cors-diagnosis), signed URL / V4 (use
  alibabacloud-oss-presigned-url-v4-diagnosis).
---

# OSS Static Website Hosting Diagnosis

Diagnose Alibaba Cloud OSS static website hosting problems: "my static website opens as a download instead of rendering", "index.html is not rendered when I open the bucket URL", "did I configure the homepage and 404 page rules correctly", "can I use this bucket as a website without ICP filing", "why does my website page return 403 / stay blank".

Core approach: verify the caller identity, then read the bucket's hosting configuration (GetBucketWebsite), bucket metadata (GetBucketInfo: location / ACL) and bound custom domains (ListBucketCname). Attribute download-vs-render symptoms to concrete causes (hosting not configured, private ACL blocking anonymous access, default-domain browser download policy, missing custom domain), and conclude with evidence-based findings and manual guidance only; this skill never changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API — e.g. `PutBucketWebsite`, `DeleteBucketWebsite`, `PutBucketPolicy`, `PutBucketAcl`, `PutObject*`, `DeleteBucket*`, or any ACL / domain-binding / hosting configuration change. This includes commands "for the user to run manually". If the user asks to enable static website hosting, set the homepage/404 rules, or bind a custom domain, only output manual console guidance and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All OSS diagnostics MUST be performed by running the scripts under `scripts/` (`static_website_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent must not assemble its own ossutil / SDK / curl commands against the OSS control plane or bypass the scripts — the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain; the default-domain probe is anonymous and credential-free. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketWebsite / GetBucketInfo / ListBucketCname / the anonymous probe / GetCallerIdentity. If a query fails or returns empty, record it and state the limitation — never invent hosting rules, domain bindings, or probe results. Empty / not-found is a valid and complete conclusion — if the bucket does not exist, has no hosting configuration, or all queries return empty, that IS the final answer: report it and STOP. Never react to empty / not-found results by attempting to create, verify, test, validate, or repair the resource, and never fall back to hand-written CLI calls. Stay within the read-only entry-script flow at all times.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps, and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line — never silently skip or abort without a report. Note: `NoSuchWebsiteConfiguration` (404) from GetBucketWebsite is a legitimate FINDING ("hosting not configured"), not an error.
6. **SCOPE BOUNDARY:** This skill only answers static website hosting questions (hosting config verification, homepage/404 rule semantics, render-vs-download attribution, custom-domain / ICP filing requirements). It does NOT handle hotlink protection (Referer anti-hotlinking), the domain binding procedure itself, generic default-domain direct-access link problems, or object-level errors — for such requests, state the boundary and defer to alibabacloud-oss-direct-access-link-diagnosis with manual guidance only.

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

**ABSOLUTE PROHIBITION (citation scope):** Cite ONLY the title + URL pairs that appear in `doc_verification.docs`, verbatim. You MUST NOT add, substitute, or construct any document URL from any other source — not from your own knowledge and not from any URL or path that appears in `references/*.md`. Do not paraphrase or extend what a cited doc covers beyond its returned title and excerpt: if a returned doc title is about image forced-download, do not describe that doc as covering HTML pages. When `doc_verification.docs` is empty or its entries do not cover the diagnosed cause, that is a valid and complete result — state the mismatch explicitly (the online doc verification did not return a doc covering this root cause) and rely on the measured evidence; never reach for an extra link to fill the gap.

## Trigger Conditions

Use this skill when the customer's own wording matches one of these phrases (the same list the `description` advertises):

- "static website shows download"
- "index.html not rendered"
- "website hosting config"
- "404 page rule"
- "static site domain filing"
- "ICP filing for OSS domain"
- "static site opens as download"
- "custom domain filing"

Do NOT use it for the following -- those belong to a sibling skill:

| Customer topic | Route to |
|---|---|
| domain binding procedures or generic default-domain direct access links | `alibabacloud-oss-direct-access-link-diagnosis` |
| endpoint selection | `alibabacloud-oss-endpoint-internal-diagnosis` |
| image processing | `alibabacloud-oss-image-processing-diagnosis` |
| browser upload CORS | `alibabacloud-oss-browser-upload-cors-diagnosis` |
| signed URL / V4 | `alibabacloud-oss-presigned-url-v4-diagnosis` |

A customer rarely states the technical cause; match on the symptom sentence, the error code or the EC number, not on product vocabulary. When the customer gives no way to locate the resource, still run the entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input and lists the buckets visible to the current credential, which is what should be put back to the customer.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `verdict` / `recommendations`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-static-website-diagnosis` and `{skill-version}` is resolved from the `SKILL_VERSION` environment variable, else from the top-level `version` of [references/manifest.json](references/manifest.json)
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every OSS SDK request (User-Agent header), the anonymous default-domain probe, and the `--user-agent` argument of the aliyun CLI identity call of that run, so all calls of one diagnosis can be correlated.
- **Version gate**: the skill version is resolved on the first User-Agent construction, which sits on the path of every Alibaba Cloud call this skill issues (OSS SDK header, anonymous default-domain probe header, and the aliyun CLI `--user-agent`). If neither `SKILL_VERSION` nor the `version` field of `references/manifest.json` yields a non-empty string, the run raises and stops **before any cloud call** — an unversioned request must never reach the cloud.

The shared client layer (`scripts/_oss_client.py`) implements this automatically: the session-id is generated lazily on the first call of each run and cached for the rest of the run.

### Exit codes (contract)

- `0` -- the run produced a conclusion: `STATUS: OK`, or `STATUS: DEGRADED`
  when part of the evidence was unavailable (missing steps are recorded in
  `errors[]` and as `[WARN]` on stderr; the conclusion is still usable).
- `1` -- no usable conclusion: `STATUS: FAIL`, typically because required input
  is missing. `NEXT_ACTION` states what to ask the user for; never treat exit
  `1` as a successful diagnosis.
- `2` -- argparse usage error only (unknown option). A diagnosed condition never
  exits with `2`.

## Credentials

Credentials are resolved exclusively by the default credential chain:
- OSS control-plane calls (Python oss2 SDK): the standard `ALIBABA_CLOUD_*` environment variables for access key ID, access key secret, and optionally security token (STS sessions).
- Identity check (`aliyun sts get-caller-identity`): the aliyun CLI default credential chain (environment or `~/.aliyun/config.json`).
- Default-domain probe: anonymous HTTPS GET, no credentials attached.

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

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request falls outside static website hosting attribution (hotlink protection, domain binding procedure, direct-access link problems per Absolute Rule 6), do not proceed with any diagnosis — state the boundary and give manual guidance only. Any request to ENABLE hosting or CHANGE configuration gets manual console guidance only, never an executed command.

## Orchestration

One read-only script gathers evidence; the reference modules interpret it. Consult a module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess a bucket or region: let the script's `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can actually see.
2. Run `scripts/static_website_diagnosis.py` and read `status`, `verdict`/findings, `auto_filled` and `errors[]`.
3. Interpret through the modules below; the diagnosis tree routes the symptom, the field-semantics module explains the failing check, and the RAM module names the permission to grant when `category` is `permission`.
4. Answer per the Final Answer Contract: verdict first, then the fix steps, then a declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: Hosting configuration playbook | IndexDocument / ErrorDocument semantics, homepage/404 rule behavior, SPA redirect patterns via routing rules |
| M2: Render vs download | Default-domain browser download policy, private-ACL 403, Content-Type issues, custom-domain rendering path |
| M3: Domain filing requirements | ICP filing rules for mainland China regions, no-filing overseas regions, filing checklist |
| M4: RAM policies | Minimal read-only RAM policy required by this skill |

Documented run order: Step 1: Confirm Identity and Collect Inputs; Step 2: Run the Static Website Diagnosis; Step 3: Interpret the Verdict and Advise; Step 4: Conclusion and Suggestions.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket hosting (or intended to host) the static website.
- **User endpoint** (`--endpoint`): optional; overrides the default query endpoint when the user has a specific one.
- **Expected region** (`--region`): optional; used to derive the query endpoint when `--endpoint` is absent.
- **UID**: can always be omitted — it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted from region, UID derived), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --endpoint/--region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Hosting configuration playbook | [references/hosting-config-playbook.md](references/hosting-config-playbook.md) | IndexDocument / ErrorDocument semantics, homepage/404 rule behavior, SPA redirect patterns via routing rules |
| M2: Render vs download | [references/render-vs-download.md](references/render-vs-download.md) | Default-domain browser download policy, private-ACL 403, Content-Type issues, custom-domain rendering path |
| M3: Domain filing requirements | [references/filing-requirements.md](references/filing-requirements.md) | ICP filing rules for mainland China regions, no-filing overseas regions, filing checklist |
| M4: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Collect Inputs

Run `python3 scripts/sts_token.py` to verify credentials and derive the UID (traceability label only). Collect the bucket name. If the user reports "the website downloads instead of rendering", map it first with [references/render-vs-download.md](references/render-vs-download.md); if the user asks about hosting rules, map with [references/hosting-config-playbook.md](references/hosting-config-playbook.md).

### Step 2: Run the Static Website Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/static_website_diagnosis.py \
    --bucket <name> [--endpoint <user-endpoint>] [--region <region>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK to obtain location / ACL / extranet domain.
3. Calls OSS `GetBucketWebsite`: configured rules (IndexDocument / ErrorDocument / routing rules) or the measured `NoSuchWebsiteConfiguration` (404) finding "hosting not configured".
4. Calls OSS `ListBucketCname` to list bound custom domains.
5. Issues ONE anonymous HTTPS GET against the default domain to record the exact browser-visible answer (HTTP status / Content-Type / OSS error code).
6. Emits a structured report plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdict and Advise

Read `verdict.causes` / `verdict.knowledge` / `recommendations` from the report:
- **hosting not configured** (`NoSuchWebsiteConfiguration`) — the bucket has no homepage/404 rules at all; the user must enable static website hosting in the console (manual write operation), then re-run to verify.
- **private ACL + anonymous probe 403** — browsers cannot read any object; the site cannot open until anonymous read is granted (manual ACL / bucket policy change).
- **default-domain download policy** — even fully configured, a browser opening the DEFAULT domain `<bucket>.<region>.aliyuncs.com` is forced to download; rendering requires a bound custom domain (ICP filing required in mainland China regions). See [references/render-vs-download.md](references/render-vs-download.md) and [references/filing-requirements.md](references/filing-requirements.md).
- **DEGRADED report** — relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent the hosting configuration.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual numbers/fields from the report. Base the conclusion on the script's `status` / `verdict` / `recommendations` / `next_action` fields rather than re-deriving them. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any change).

## Important Notes

- **NoSuchWebsiteConfiguration is a finding, not a failure**: the measured 404 from GetBucketWebsite means hosting was never enabled — report it as the root cause branch, not as a degraded step.
- **Default-domain browser download policy**: for a bucket created after 2017-10-01 (Beijing time), OSS forces browsers to download objects served via the default domain when the name ends in `.htm`/`.html` or the Content-Type is `text/html` (EC 0048-00000001); this is the canonical cause of "the static website opens as a download". Only a bound custom domain renders HTML in the browser. (The 2019-09 cutoff belongs to the separate image MIME family 0048-00000100~105 — do not conflate them.)
- **Hosting requires anonymous read**: a private bucket without a public-read policy cannot serve any website traffic; the anonymous probe 403 is the evidence.
- **Domain binding and hotlink protection are out of scope**: defer them to alibabacloud-oss-direct-access-link-diagnosis by full name.
- **Read-only operations**: only GetBucketInfo, GetBucketWebsite, ListBucketCname, and `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 — static website opens as a download**

> User: "My bucket test-agentceping hosts a static site, but opening the OSS URL in Chrome downloads the file instead of rendering the page. Account UID 1552974654746705."

```bash
python3 scripts/static_website_diagnosis.py --bucket test-agentceping
```

Relay the findings: whether hosting is configured, whether the anonymous probe returns 403 (private ACL), and the default-domain browser download policy — the user must bind a custom domain (with ICP filing in mainland regions) to render pages. Declare any auto-filled parameters. If the report is `STATUS: DEGRADED`, relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 — homepage / 404 rule verification**

> User: "I enabled static website hosting; please verify whether the homepage and 404 page rules of bucket my-site-bucket are effective."

```bash
python3 scripts/static_website_diagnosis.py --bucket my-site-bucket
```

Report the `verdict.hosting_state` and the IndexDocument / ErrorDocument values from the report; when the homepage rule names an object that does not exist or whose Content-Type is not text/html, explain it with [references/hosting-config-playbook.md](references/hosting-config-playbook.md).

**Example 3 — domain filing (ICP) requirement**

> User: "Can I bind www.example.com to my OSS website bucket in cn-hangzhou without ICP filing?"

```bash
python3 scripts/static_website_diagnosis.py --bucket <name>
```

Use the bucket location from the report plus [references/filing-requirements.md](references/filing-requirements.md): mainland China regions require a valid ICP filing for any bound custom domain; overseas regions do not. Give manual guidance only.

<!-- production-pattern-example -->

**Example N — Site root returns a permission error although objects are public**

> User: "Opening my bucket domain root path says the bucket does not belong to me, but the object URLs work."

```bash
python3 scripts/static_website_diagnosis.py --bucket "my-bucket" --region "cn-hangzhou" --json
```

Report that static hosting is not enabled (so a bare root path has no index document to resolve) before any permission explanation, then the index/404 rule and the custom-domain prerequisite.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/static_website_diagnosis.py` | Static website hosting diagnosis entry: GetBucketInfo + GetBucketWebsite + ListBucketCname + anonymous default-domain probe, with full degradation |

CLI options for `static_website_diagnosis.py`: `--bucket <name>` (required), `--endpoint <endpoint>` (optional), `--region <region>` (optional), `--json` (structured report), `--selftest` (pure-function boundary assertions).

Output contract (shared with the sibling OSS skills): the `STATUS:` and `NEXT_ACTION:` contract lines are always printed on stdout — also in `--json` mode, where they follow the JSON document on stdout; stderr carries only `[WARN]` / `[INFO]` diagnostics.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `AccessDenied` / 403 (control plane) | Missing `oss:GetBucketInfo` / `oss:GetBucketWebsite` / `oss:ListBucketCname`, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| `NoSuchWebsiteConfiguration` / 404 | Hosting not configured on the bucket | Legitimate finding: report the "hosting not configured" branch with enable-hosting guidance (manual) |
| Anonymous probe 403 | Bucket ACL private / no anonymous read policy | Explain the site cannot open for browsers; give manual ACL/policy guidance |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the root cause with the actual evidence fields (hosting state, IndexDocument/ErrorDocument values, ACL, anonymous probe status, bound custom domains) — no fabricated values.
3. Declare every auto-filled parameter (endpoint default, UID derivation).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Give hosting-configuration / domain-binding suggestions as manual guidance only (this skill never applies changes), and defer hotlink protection or domain-binding procedures to alibabacloud-oss-direct-access-link-diagnosis by full name.
6. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)." No document link outside `doc_verification.docs` may appear in the answer (see Official Doc Verification — citation scope).

