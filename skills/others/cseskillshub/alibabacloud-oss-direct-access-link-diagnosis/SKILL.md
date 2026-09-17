---
name: alibabacloud-oss-direct-access-link-diagnosis
description: |
  Read-only OSS direct-access link diagnosis: attributes
  preview-turns-download (0048 default-domain forced download incl.
  images on post-2019-09 buckets, attachment disposition, wrong
  Content-Type, private-bucket 403), EC 0003-00000005 bisection
  (object private ACL / Block Public Access / AK-signature) for 403 on
  non-private buckets, domain binding failures (cname, ICP, CNAME),
  and referer whitelist/blacklist false positives. Templates only,
  never writes.
  Triggers: "open turns into download", "file cannot preview", "image downloads instead of previewing", "image downloads instead of showing it", "0003-00000005", "custom domain binding failed", "domain requires ICP filing", "referer whitelist blocks legitimate requests".
  Do NOT use for
  hotlinking forensics, static website hosting, endpoints, image
  styles, browser CORS, signed URLs, CDN origin-pull, cross-account
  authorization, or transfer acceleration - route to the matching
  alibabacloud-oss-* sibling skill.
---

# OSS Direct Access Link Diagnosis

Diagnose Alibaba Cloud OSS direct-access problems: "opening the file link turns into a download" (including the default-domain 0048 forced-download policy — images on post-2019-09 buckets included), "the image cannot preview in the browser", "my bucket is public-read but one object returns 403 / error code 0003-00000005" (3-cause attribution: object private ACL / authentication failure / Block Public Access), "binding my custom domain failed / the console says the domain is not ICP-filed", "after enabling hotlink protection my own site is blocked (referer whitelist/blacklist false positive)".

Core approach: confirm the caller identity, confirm the bucket exists via the read-only GetBucketInfo control-plane query, read the bucket's real referer whitelist AND blacklist (GetBucketReferer, official check order empty-referer -> blacklist -> whitelist), static-website-hosting state (GetBucketWebsite, reported as context only), and bound custom domains (ListBucketCname); optionally run an ANONYMOUS (credential-free) HEAD probe of the object over the default domain to attribute preview-vs-download from the actual Content-Type / Content-Disposition / X-Oss-Force-Download / status — and when that probe returns 403 on a NON-private bucket, run the EC 0003-00000005 3-cause attribution (referer precondition -> Block Public Access precondition -> Cause-1 object private ACL via GetObjectAcl -> Cause-2 authentication failure -> Cause-3 unattributed escalation); then conclude with evidence-based findings plus configuration templates. **This skill only outputs templates and guidance — it never writes any configuration** (applying referer rules, website hosting, or domain binding is the user's own manual operation).

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating OSS API — e.g. `PutBucketReferer`, `PutBucketWebsite`, `DeleteBucketWebsite`, `PutBucketCname`/domain-binding calls, `PutObject*`, `DeleteObject*`, or any ACL/policy/configuration change. This includes commands "for the user to run manually". When a configuration change is needed, only output the standard template as text and manual guidance, and declare this skill is read-only.
2. **MANDATORY entry-point enforcement:** All diagnostics MUST be performed by running the scripts under `scripts/` (`oss_direct_access_diagnosis.py` as the entry, `sts_token.py` for identity). The Agent is forbidden from assembling its own ossutil / SDK / curl commands against the OSS control plane or bypassing the scripts — the scripts embed timeout, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries. The anonymous default-domain probe is ONLY permitted through the entry script's `--object` option.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. The OSS SDK resolves credentials exclusively from the environment variables of the default credential chain; the identity check uses the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by GetBucketInfo / GetBucketReferer / GetBucketWebsite / ListBucketCname / ListBuckets / GetObjectAcl / GetCallerIdentity or the anonymous probe. If a query fails or returns empty, record it and state the limitation — never invent referer rules, bound domains, or response headers.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <category>: <message>` to stderr, continue with the remaining steps (including the ListBuckets fallback), and still produce the final report with `STATUS: DEGRADED` and a `NEXT_ACTION` line — never silently skip or abort without a report. Note: a bucket without website hosting returns `NoSuchWebsiteConfiguration` from GetBucketWebsite — this is the semantic state "static website hosting not configured", NOT an error; report it as a finding. Empty referer lists (both whitelist and blacklist) / an empty cname list are likewise normal configuration states ("hotlink protection not configured" / "no custom domain bound").
6. **SCOPE BOUNDARY:** This skill only answers direct-access-link questions: preview-vs-download attribution, EC 0003-00000005 bisection, custom domain binding check/failure attribution, and referer hotlink-protection false positives. Static website HOSTING rules (index/404 page configuration) belong to the sibling alibabacloud-oss-static-website-diagnosis skill; hotlinking traffic-theft forensics, image processing styles, browser-upload CORS, signed URLs (alibabacloud-oss-presigned-url-v4-diagnosis), CDN origin-pull configuration (alibabacloud-oss-cdn-origin-config-diagnosis), cross-account authorization (alibabacloud-oss-cross-account-auth-diagnosis), and transfer acceleration (alibabacloud-oss-transfer-acceleration-diagnosis) each belong to the sibling skills — for such requests, state the boundary and defer (the script's out-of-scope referral guard flags these signals automatically).

## Official Doc Verification

MANDATORY: For configuration or usage questions, the entry script MUST be invoked with --question "<customer original wording>". The script first matches embedded knowledge, then verifies against official OSS docs (doc_verification, llms-index). The final answer MUST cite the URLs from doc_verification.docs. If doc_verification.note starts with DEGRADED, state explicitly: "Unable to verify against online official docs (offline)." Never fabricate doc URLs; only URLs returned by the script may be cited.

## Trigger Conditions

Route here when the user reports any of: opening an OSS file link turns into a download instead of previewing ("open turns into download", "file cannot preview", "image downloads instead of preview" — including the 0048 default-domain forced-download policy for images on post-2019-09 cutoff buckets); a public-read bucket returns 403 / error code 0003-00000005 on a single object (EC bisection: object private ACL / Block Public Access / AK-or-signature); a custom domain cannot be bound to a bucket ("custom domain binding failed", "domain requires ICP filing", domain shows not filed although believed filed, binding done but access fails); or the referer whitelist / blacklist / hotlink protection blocks legitimate requests ("referer whitelist blocks legitimate requests", users get 403 from the bucket referer policy when opening links directly or from a specific page).

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. Read the structured JSON report, interpret `status` / `referer` / `cnames` / `website` / `probe` / `recommendations` / `templates`, and compose the user-facing answer; do not re-implement the queries or call OSS APIs directly.

## Observability

All API calls issued by the scripts include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where `{skill-name}` is `alibabacloud-oss-direct-access-link-diagnosis`
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every OSS SDK request (User-Agent header), the anonymous default-domain probe, and every `--user-agent` argument of the aliyun CLI identity call of that run, so all calls of one diagnosis can be correlated.

The shared client layer (`scripts/_oss_client.py`) implements this automatically: the session-id is generated lazily on the first call of each run and cached for the rest of the run.

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
- The preview-vs-download probe (`--object`) is an ANONYMOUS data-plane HEAD request and needs no credentials at all.

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

Because every action of this skill is strictly read-only, no user confirmation is required before running the diagnostic scripts. Confirmation discipline applies at the scope boundary instead: when a request falls outside direct-access-link attribution (hotlinking forensics, website hosting index/404 rules, image processing, browser CORS, signed URLs per Absolute Rule 6), do not proceed with any diagnosis — state the boundary and defer/give manual guidance only. Applying any referer / domain / hosting configuration always stays a manual user operation; never ask for confirmation to "apply" it on the user's behalf.

## Input Parameters

- **Bucket name** (`--bucket`): required; the OSS bucket whose direct-access link is being diagnosed.
- **Object key** (`--object`): optional; when provided, the script issues an ANONYMOUS HEAD probe of `https://<bucket>.<endpoint>/<key>` and attributes preview-vs-download from the real status / Content-Type / Content-Disposition / X-Oss-Force-Download (private-bucket anonymous 403 is a diagnosis branch itself; a 403 on a NON-private bucket triggers the EC 0003-00000005 bisection). Accepts a bare object key OR a full URL — `https://<bucket>.<endpoint>/<key>` is normalized to the key automatically.
- **Custom domain** (`--domain`): optional; checked against the bucket's bound cname list to attribute binding failures.
- **Page referer** (`--page-referer`): optional; the Referer header value of the embedding page, used to attribute referer false positives.
- **Query endpoint** (`--endpoint`): optional; the endpoint of the region where the bucket was created.
- **Expected region** (`--region`): optional; used to derive the query endpoint when `--endpoint` is absent.
- **UID**: can always be omitted — it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (query endpoint defaulted, UID derived, probe skipped), the Agent MUST explicitly declare this in the response or report metadata, e.g. "query endpoint auto-defaulted to oss-cn-hangzhou.aliyuncs.com (no --endpoint/--region provided)".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Preview-vs-download playbook | [references/preview-download-playbook.md](references/preview-download-playbook.md) | Default-domain forced-download policy, Content-Disposition / Content-Type attribution, private-bucket anonymous 403, fix checklist |
| M2: Domain binding guide | [references/domain-binding-guide.md](references/domain-binding-guide.md) | Custom domain binding steps, ICP filing requirement, CNAME resolution, HTTPS certificate, binding-failure attribution |
| M3: Referer rules | [references/referer-rules.md](references/referer-rules.md) | Hotlink-protection whitelist semantics, allow_empty_referer, wildcard rules, false-positive attribution |
| M4: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |
| M5: EC 0003-00000005 bisection SOP | [references/ec-0003-00000005-bisection.md](references/ec-0003-00000005-bisection.md) | Official cause attribution (object private ACL / AK-or-signature / Block Public Access) for anonymous-403-on-non-private-bucket, inference rule, verdict mapping |

## Orchestration & Execution Flow

### Step 1: Confirm Identity and Collect Inputs

**MANDATORY, never skip — run the identity pre-check as its own command before the entry script:**

```bash
cd $SKILL_DIR && python3 scripts/sts_token.py --json
```

Use it to verify credentials and derive the UID (traceability label only). If it fails, record the `[WARN]` and continue with Step 2 per Absolute Rule 5 — never abort, never print AK/SK/STS tokens. Collect the bucket name and, if the user has them, the failing URL / object key, the custom domain, and the embedding page URL. Route the symptom first: preview-vs-download vs domain-binding failure vs referer 403.

### Step 2: Run the Direct-Access Diagnosis

```bash
cd $SKILL_DIR && python3 scripts/oss_direct_access_diagnosis.py \
    --bucket <name> [--object <key>] [--domain <custom-domain>] \
    [--page-referer <url>] [--region <region>]
```

The script:
1. Derives the caller UID via `aliyun sts get-caller-identity` (degraded with `[WARN]` on failure).
2. Calls OSS `GetBucketInfo` through the oss2 SDK to confirm the bucket exists and fetch metadata (ACL, location, creation_date for the 0048 image cutoff); on failure falls back to `ListBuckets` (prefix lookup), logging `[WARN]` for every degraded step. An internal endpoint (`-internal.`) is auto-guarded with a short 5s timeout plus a `[WARN]` notice (VPC-only reachability).
3. Calls OSS `GetBucketReferer` (read-only, whitelist AND blacklist): BOTH lists empty means hotlink protection is NOT configured — a finding, not an error; a configured blacklist alone (empty whitelist) is still an ACTIVE deny-list.
4. Calls OSS `GetBucketWebsite` (read-only): `NoSuchWebsiteConfiguration` is mapped to the semantic state **static website hosting not configured** (context / boundary marker; hosting rules belong to the sibling skill).
5. Calls OSS `ListBucketCname` (read-only): an empty list means **no custom domain is bound**.
6. When `--object` is given, issues an ANONYMOUS HEAD probe against the default domain (no credentials; a full URL is normalized to the object key) and attributes preview-vs-download from status + Content-Type + Content-Disposition + X-Oss-Force-Download (private-bucket anonymous 403 is a diagnosis branch itself). When the probe returns 403 on a NON-private bucket, runs the EC 0003-00000005 bisection: referer rules first, then GetObjectAcl (cause-1 object private ACL), then the unattributed-403 boundary statement (check Block Public Access, then escalate) — see [references/ec-0003-00000005-bisection.md](references/ec-0003-00000005-bisection.md).
7. Emits the structured JSON report with the referer / preview-fix / domain-binding templates (text output only — never applied), plus the contract lines `STATUS: OK | DEGRADED` and `NEXT_ACTION: <action>`.

### Step 3: Interpret the Verdict and Advise

Read `referer`, `cnames`, `website`, `probe`, and `recommendations` from the report:
- **Preview turns into download** — Relay the probe analysis: `Content-Disposition: attachment` on the object, `Content-Type: application/octet-stream` misconfiguration, or the OSS default-domain 0048 forced-download policy (HTML — `.htm`/`.html`/`text/html` — for post-2017-10 buckets; the 12 image MIME types for post-2019-09 cutoff buckets; ALL file types for new users after 2022-10-09 — probe proof: `x-oss-force-download: true`; APK/IPA restricted outright); fixes are manual (re-upload with `Content-Disposition: inline` + correct MIME type, or bind a custom domain per `templates.preview_fix`).
- **Private bucket anonymous 403** — the 403 is expected behavior, not a network fault: preview requires a presigned GET URL or public-read ACL (the 403 alone does not prove a referer misconfiguration).
- **EC 0003-00000005 (403 on a NON-private bucket)** — relay `probe.analysis.verdict`: `object_acl_private_403` (cause-1: the object carries its own private ACL; fix template `ossutil set-acl oss://<BUCKET>/<OBJECT_KEY> default`, batch with `-r`), `unattributed_403` (cause-1 excluded and hotlink rules pass: check Block Public Access on the bucket/account per the official "Problem examples", then escalate via the violation-handling channel — no public query interface exists for internal block records), or `object_acl_unverifiable` (inference rule: cause-1 stays the leading hypothesis; have the owner verify). Attribute only within the official cause families (no read permission / AK-or-signature incorrect / Block Public Access).
- **Out-of-scope referral guard** — when the request carries CDN origin-pull / cross-account RAM / presigned-URL / transfer-acceleration signals, the report's `recommendations` LEAD with an OUT-OF-SCOPE REFERRAL to the owning sibling skill; relay it first and keep the bucket evidence as context only.
- **No custom domain bound** — access works only via the default domain; relay `templates.domain_binding` (add domain → CNAME record → ownership verification → ICP filing check → certificate) as manual guidance.
- **Binding failed attribution** — domain not in the cname list: check ICP filing sync (regions in mainland China require filing; "already filed but rejected" means filing not synced or domain occupied by another bucket/product), CNAME record conflicts, certificate domain mismatch.
- **Referer false positive** — `allow_empty_referer=false` blocks direct address-bar access and clients that send no Referer; otherwise match the embedding page against the whitelist (`*`/`?` wildcards). Fixes are manual per `templates.referer_rule`.
- **DEGRADED report** — relay the recorded errors and the `NEXT_ACTION` guidance honestly; never invent referer rules or bound domains.

### Step 4: Conclusion and Suggestions

Summarize the root cause with the actual fields from the report. Base the conclusion on the script's `status` / `recommendations` / `next_action` fields rather than re-deriving them. All configuration suggestions are manual guidance quoting the report's templates; this skill never applies any change.

## Important Notes

- **Never write configuration**: PutBucketReferer / PutBucketWebsite / domain-binding calls are absolutely prohibited; templates are output as text only.
- **"Not configured" is a valid finding**: empty referer lists (both whitelist and blacklist), an empty cname list, and `NoSuchWebsiteConfiguration` are configuration states — report them as findings with guidance, not as API failures.
- **Default-domain forced-download policy (0048 family)**: OSS default domains (`*.aliyuncs.com`) force attachment downloads as a security policy — HTML for post-2017-10 buckets, the 12 image MIME types for post-2019-09 cutoff buckets (probe proof: `x-oss-force-download: true`), APK/IPA outright; preview for those types requires a bound custom domain. "Images preview normally over the default domain" only holds for pre-2019-09 buckets (the report's `templates.preview_fix` carries the bucket-creation-date note).
- **allow_empty_referer semantics**: direct address-bar access carries NO Referer header; blocking empty referers always blocks address-bar users and some apps/WebView clients — the number-one referer false-positive cause.
- **Referer blacklist outranks the whitelist**: official check order is empty-referer -> blacklist -> whitelist; a blacklisted referer is denied even if it also matches the whitelist. The script reads `black_referers` explicitly (some SDK surfaces drop it) and reports the `denied_blacklist` verdict.
- **Internal endpoints**: an endpoint containing `-internal.` is VPC-only; the script auto-guards such queries with a 5s timeout + `[WARN]` instead of hanging, and flags the parameter so the Agent can advise the public endpoint.
- **ICP filing**: binding a custom domain to a bucket located in mainland China requires a valid ICP filing; overseas regions do not enforce it.
- **Scope split**: index/404 static website HOSTING rules belong to the sibling endpoint-internal skill; this skill reports hosting state only as context.
- **Read-only operations**: only GetBucketInfo, GetBucketReferer, GetBucketWebsite, ListBucketCname, ListBuckets, GetObjectAcl (EC bisection evidence), one anonymous HEAD probe, and `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 — open turns into download**

> User: "Opening my image URL downloads the file instead of previewing it."

```bash
python3 scripts/oss_direct_access_diagnosis.py --bucket test-agentceping --object www.example.com/header/a.png
```

(A full URL such as `https://test-agentceping.oss-cn-hangzhou.aliyuncs.com/test/header.png` is also accepted — the script normalizes it to the object key automatically.)

Relay the probe analysis (attachment disposition / octet-stream Content-Type / 0048 default-domain policy incl. `x-oss-force-download: true` for images on post-2019-09 buckets), the preview-fix checklist from `templates.preview_fix`, and declare any auto-filled parameters. If `STATUS: DEGRADED` (e.g. missing permission), relay the recorded errors and `NEXT_ACTION` honestly.

**Example 2 — custom domain binding failed**

> User: "Binding my custom domain img.example.com to the bucket failed; the console says the domain is not ICP-filed although I believe it is."

```bash
python3 scripts/oss_direct_access_diagnosis.py --bucket <name> --domain img.example.com
```

Report the cname list finding (bound or not), the ICP-filing guidance from `templates.domain_binding` (mainland regions require filing; verify filing sync and domain occupation), and the CNAME/certificate checklist.

**Example 3 — referer whitelist blocks legitimate requests**

> User: "After enabling hotlink protection, users opening links directly in the address bar get 403."

```bash
python3 scripts/oss_direct_access_diagnosis.py --bucket <name>
```

Attribute the false positive to `allow_empty_referer=false` (address-bar requests carry no Referer) per the report's referer verdict, and relay the referer template as manual guidance. (A `denied_blacklist` verdict means the page referer hit a blacklist entry, which outranks any whitelist match.)

**Example 4 — public bucket returns 403 on one object (EC 0003-00000005)**

> User: "My bucket is public-read, but opening one file anonymously returns 403 with error code 0003-00000005."

```bash
python3 scripts/oss_direct_access_diagnosis.py --bucket <name> --object <object-key>
```

Relay `probe.analysis.verdict` per the bisection SOP: cause-1 (`object_acl_private_403`) carries the `ossutil set-acl ... default` fix template (batch with `-r`); `unattributed_403` (cause-1 excluded) first checks Block Public Access then escalates through the violation-handling channel — no public query interface exists for internal block records; `object_acl_unverifiable` keeps cause-1 as the leading hypothesis. Attribute only within the official cause families.

<!-- production-pattern-example -->

**Example N — Opening a PDF from the default endpoint downloads instead of previewing**

> User: "Every PDF I open from the OSS default domain is downloaded instead of shown in the browser."

```bash
python3 scripts/oss_direct_access_diagnosis.py --bucket "my-bucket" --object "files/report.pdf"
```

Attribute it to the default domain's forced-download behaviour (and any Content-Disposition: attachment on the object), then state the prerequisite for preview: a bound custom domain, which for mainland regions requires ICP filing.


## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/oss_direct_access_diagnosis.py` | Direct-access diagnosis entry: GetBucketInfo + GetBucketReferer (incl. blacklist) + GetBucketWebsite + ListBucketCname + anonymous default-domain probe (URL normalization, X-Oss-Force-Download capture) + EC 0003-00000005 bisection (GetObjectAcl) + out-of-scope referral guard + referer/preview/domain template output |

CLI options for `oss_direct_access_diagnosis.py`: `--bucket <name>` (required), `--object <key>` (optional anonymous probe), `--domain <custom-domain>` (optional), `--page-referer <url>` (optional), `--endpoint <endpoint>` (optional), `--region <region>` (optional).

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Environment credential chain not configured | Run `aliyun configure` / configure environment variables; never ask the user for AK/SK |
| `NoSuchWebsiteConfiguration` (404 from GetBucketWebsite) | No static website hosting configured — a configuration state, not a failure | Report "website hosting not configured" as a finding |
| Empty referer lists / empty cname list | Hotlink protection not configured (BOTH lists empty) / no custom domain bound — configuration states | Report as findings with the standard templates for manual application |
| Anonymous probe 403 | Private bucket denies anonymous access (or referer/policy denial) | Attribute per ACL: private bucket → use presigned URL or public-read; non-private bucket → EC 0003-00000005 bisection (object private ACL / Block Public Access / AK-or-signature); referer denial → blacklist/whitelist rules |
| GetObjectAcl `AccessDenied` | Missing `oss:GetObjectAcl` during the EC 0003-00000005 bisection | Record `[WARN]`, report `object_acl_unverifiable` (cause-1 stays the leading hypothesis per the SOP inference rule); grant per [references/ram-policies.md](references/ram-policies.md) and re-run |
| Internal endpoint timeout | `--endpoint` contains `-internal.` (VPC-only) | Auto-guarded with a 5s timeout + `[WARN]`; re-run with the public endpoint or from inside the VPC |
| `AccessDenied` / 403 | Missing read permission, bucket owned by another account, or wrong-region endpoint | Record `[WARN]`, point to [references/ram-policies.md](references/ram-policies.md); report `STATUS: DEGRADED` |
| `NoSuchBucket` / 404 | Bucket name does not exist (global namespace) | Verify spelling and owning account; report `STATUS: DEGRADED` with `NEXT_ACTION` |
| Network timeout / connection reset | Transient network failure | Report `STATUS: DEGRADED` honestly; retry later, never conclude "no problem" from a failed call |
| `InternalError` / 5xx / `SlowDown` | Transient service-side failure or request throttling | Retried automatically inside `scripts/_oss_client.py` (2 extra attempts, 1s then 3s, each traced as `[WARN]` on stderr); if the call still fails the report carries `STATUS: DEGRADED`. Do not re-run the script in a loop and never conclude "no problem" from a failed call |

| Doc lookup module | `scripts/_doc_lookup.py` | Runtime official-doc verification against the OSS help center (llms-index); used by the `--question` path |
All errors follow the structured `category/code/message/hint` shape recorded in the report's `errors` array; every degraded step logs `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.

## Final Answer Contract

The final answer to the user MUST:
1. Relay the script's `STATUS:` (`OK` / `DEGRADED`) and `NEXT_ACTION:` line verbatim in meaning.
2. State the root cause with the actual evidence fields (referer whitelist/blacklist state, bound cname list, probe status/headers, `probe.analysis` bisection verdict, hosting state) — no fabricated values.
3. Declare every auto-filled parameter (endpoint default, UID derivation, probe skipped).
4. On `DEGRADED`, list the recorded errors and limitations explicitly instead of inventing conclusions.
5. Deliver referer/domain/preview fixes as text templates plus manual guidance only (this skill never applies any configuration).
6. When the report carries `doc_verification`, cite the doc titles and URLs from `doc_verification.docs` in the final answer; when `doc_verification.note` starts with `DEGRADED`, state explicitly: "Unable to verify against online official docs (offline)."

