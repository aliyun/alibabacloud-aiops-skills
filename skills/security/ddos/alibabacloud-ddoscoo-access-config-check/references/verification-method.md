# Verification Method & Report Template

Per-step verification commands and success criteria, the scenario → action → help-doc mapping, and the exact
`report.md` structure with the Finalize checklist.

## Artifact names and working directory (applies to every step)

**[MUST] Keep the canonical output filenames** — `access-config.json`, `local-evidence.json`, `taskids.json`,
`probe-evidence.json`, `report.md` — and point every script at the **same** `$OUT_DIR`.

- Renaming an output breaks the hand-off between steps: `parse_probe_log.py` discovers `local-evidence.json`
  **by filename** next to `--taskids` in order to merge the C2 verdicts. A renamed file silently drops C2 from
  `probe-evidence.json`, and the report then looks complete while a whole check is missing.
- **Do `cd` into the skill's base directory and use the documented relative form** `python3 scripts/<name>.py`.
  Observed failing forms: `python3 .qwen/skills/<skill>/scripts/check_local.py` (relative to the *workspace*,
  so the skill prefix leaks into the command) and a bare absolute interpreter path. Both ran the correct
  script, but neither is recognisable as the documented invocation, so a reviewer or an automated check of the
  transcript cannot tell which script produced which artifact.
- **`$OUT_DIR` / `$RS_DIR` must be absolute, precisely because of that `cd`.** The default `./outputs` is
  relative to the working directory, so cd-ing into the skill tree with a relative `$OUT_DIR` redirects every
  artifact into the skill directory and the later steps lose the earlier ones — the pipeline then derails
  part-way, typically at `create_probes.py` / `parse_probe_log.py`. The scripts resolve
  their own version metadata from their own location, so the `cd` is safe for them; it is only the output
  paths that must be pinned.
- Correction of an earlier revision: this section once withdrew the relative-path mandate on the grounds that
  it pushed agents to `cd`. That was half right — `cd` combined with a *relative* `$OUT_DIR` is the harmful
  combination, not `cd` itself. Both requirements now stand together.

None of this is a reason to skip a script: see the SKILL.md rule that `check_local.py` runs in every mode.

## Domains with no layer-7 rule: `--extra-domains`

`--domains` **filters** `web_rules`; it never adds a target. When the domain the user asked about has no
layer-7 forwarding rule in this account — the degraded / baseline-free case they explicitly opted into —
filtering finds nothing, `create_probes.py` stops with exit code 2 (its no-probe-target error), `check_local.py`
checks 0 domains, and the run produces no observation at all even though the user authorised one.

`--extra-domains a.example.com,b.example.com` appends those targets instead (both scripts take it, plus an
optional `--extra-region`). Internally each one becomes a rule with an empty `Cname`, empty endpoints and
empty origin set, marked `baseline_free`, so the existing judging code runs unchanged; with no endpoints to
derive from, the probe falls back to the default `https:443`.

Because there is no baseline, the three verdicts are fixed and must not be anything else:

| Check | Verdict | Why |
|---|---|---|
| C1 | `NOT_APPLICABLE_NO_WEB_RULE` | No rule, so no expected CNAME to compare against (precondition branch 1) |
| C2 | `NOT_APPLICABLE_NO_CERT_BOUND` | No rule, so no bound-certificate name to look up in `cas` |
| C3 | `NOT_APPLICABLE_NO_CONFIG_BASELINE` | No expected CNAME and no origin-IP set, so "is Anti-DDoS first?" has no basis |

C4 **is** a real result — public reachability needs no baseline. That is the whole point of the degraded mode.

**[MUST] Nothing on this path may be presented as an onboarding verdict.** The report and the chat reply must
say the run was degraded and baseline-free, must name the domain that has no rule here, and must give the fix (add a layer-7 forwarding
rule, associate an Anti-DDoS IP to generate the CNAME, switch DNS, re-run). Before this flag existed the
documented degraded mode could not actually be carried out: the scripts had no way to observe a domain the
account has no rule for.

## Vocabulary discipline in generated files

Credential-leak checks are substring matches, so a generated file can read as a disclosure without leaking
anything. Two rules follow:

- **`report.md` and the chat reply never quote `aliyun configure list` output.** Report only that credentials are valid, and stop there.
  The profile's credential-type label is not a secret, but a substring of it matches the keyword list, and the
  report then looks like it exposed credentials.
- **`ran_scripts/action_log.md` records commands verbatim, including the mandated `SKILL_SESSION_ID` /
  `SKILL_VERSION` prefix. That is correct and must not be redacted** — a faithful command log is the audit
  trail, and the UA prefix is required by the skill spec. Redacting it would break the UA contract to satisfy a
  keyword filter.

Do not contort the artifacts to avoid a substring: fix what is genuinely over-disclosed (CLI output in a
customer report) and leave the command log intact.

## Per-step verification

### Step 1 — config fetch succeeded
```bash
aliyun ddoscoo describe-instances --region cn-hangzhou --page-number 1 --page-size 50 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
aliyun ddoscoo describe-web-rules --region cn-hangzhou --page-number 1 --page-size 10 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
aliyun ddoscoo describe-scheduler-rules --region cn-hangzhou --page-number 1 --page-size 10 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
```
- Criteria: `describe-instances` returns `TotalCount > 0` and each instance carries `InstanceId` + `Ip`;
  `describe-web-rules` returns `WebRules[]` with `Domain`, `Cname`, `ProxyTypes[]`, `RealServers[]`,
  `CertName`; `describe-scheduler-rules` returns `SchedulerRules[]` (may legitimately be empty).
- Completeness gate: cumulative fetched count == `TotalCount` for all three. Any mismatch → re-fetch or warn;
  do not continue silently.
- `describe-scheduler-rules` treats `PageSize` as required and takes no `RegionId` parameter (the CLI still
  needs `--region` for endpoint routing). If the plugin rejects the hyphenated form, use the generic RPC
  channel with PascalCase (`--PageSize 10 --PageNumber 1 --version 2020-01-01`).
- Empty `WebRules` across the whole account → stop with the "no layer-7 website configured" message; layer-4
  is out of scope. Empty `WebRules` **only after filtering to the requested scope** is a different case — go
  to Step 1.5, do not report "no configuration".

### Step 1.5 — scope ownership gate resolved the target
```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/fetch_config.py \
  --regions cn-hangzhou,ap-southeast-1 --expect-domains "www.example.com" --out "$OUT_DIR/access-config.json"
```
- Criteria: `scope_gate.gate == "PASS"`, and every requested target carries one of `FOUND_EXACT` /
  `FOUND_WILDCARD` / `FOUND_VIA_SCHEDULER` / `FOUND_INSTANCE`.
- `searched_regions` must list **every region where the account has instances**. A gate that searched one
  region and returned `NOT_FOUND_IN_ACCOUNT` is not evidence of absence.
- `FOUND_WILDCARD` entries must name the covering `*.parent` rule; `FOUND_VIA_SCHEDULER` entries must carry
  the observed `cname_chain`, the matched scheduler CNAME, **and** `c1_verdict` + `c1_prompt`.
- A `FOUND_VIA_SCHEDULER` target is C1 precondition **branch 2**: `c1_verdict` must read
  `NOT_APPLICABLE_SCHEDULER_ONLY`. A `NOT_FOUND_IN_ACCOUNT` target is **branch 1**: `NOT_APPLICABLE_NO_WEB_RULE`.
  If either entry lacks `c1_prompt`, the run is incomplete — the prompt is the deliverable, not decoration.
- On `FAIL_UNRESOLVED`: verify the evidence you will show the user is present — `cname_chain_observed`,
  `near_miss_same_registrable_domain`, `wildcard_rules_in_account`. Then stop and ask; do not proceed to
  Step 2. If the user opts into degraded mode, confirm C1 is recorded as `NOT_APPLICABLE_NO_WEB_RULE`, C3 as
  `NOT_APPLICABLE_NO_CONFIG_BASELINE`, and that no probe task was created without their consent.

### Step 3 — C1 evidence is real
```bash
dig +short www.example.com CNAME            # first hop
dig +short www.example.com A                # final IPs (may include the CNAME chain lines)
dig @223.5.5.5 +short www.example.com CNAME # second resolver view, exposes per-line records
aliyun cms create-instant-site-monitor --address "www.example.com" --task-type "DNS" \
  --task-name "ddoscoo-acc-www-example-com-dns" --isp-cities '[{"city":"357","isp":"132"}]' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
aliyun cms describe-site-monitor-log --task-ids "<TaskId>" --metric-name "ProbeLog" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
```
- **Precondition first**: record which of the four C1 branches each domain is in. Branches 1–2 are already
  decided by Step 1.5. For branches 3–4 read `web_rules[].cname` — empty means branch 3
  (`NOT_APPLICABLE_NO_CNAME_ASSIGNED`), non-empty means branch 4 and the comparison below runs. Cross-check
  the branch counts against `account_web_domains_total`; a large branch-3 population usually means instances
  were released or never associated, and the report must say which region has 0 instances.
- Criteria (branch 4 only): the chain has a first hop, and the observed value is compared against **this
  domain's own** `cname`, plus the scheduler CNAME set and the account-wide web-rule CNAME set (for cross-use
  detection). Normalized: lowercase, trailing dot stripped.
- **Cloud probing is the primary DNS source for C1 and C3.** Each cloud point returns `DNSRaw` (the whole
  ordered answer section, pipe-separated), a separate `cnames` field, the final `ips`, and `dnsServer` —
  so "first hop == configured CNAME" is proved from the cloud probe, at every vantage point, and C3 gets its
  hop order from the same record. One `DNS` task serves both C1 and C3; do not create a second task for C3.
  An earlier revision claimed cloud DNS returns final IPs only — that was wrong.
- `check_local.py` still runs under `ProbeMode=cloud` — it is the only judge of C2 and the module that owns
  the C1/C3 judging functions. Verify `local-evidence.json` exists and carries a `c2` verdict per domain;
  `parse_probe_log.py --local-evidence` merges those into `probe-evidence.json`. Running it does **not** make
  the run a local-probe run: report the mode the user chose. Under `ProbeMode=cloud` never describe the run
  as a local-probe run in the report or the final answer (SKILL.md names the exact forbidden wording) —
  that misstates the mode the user confirmed and contradicts the Step 0 disclosure.
- Local `dig` **as the authority for C1/C3 verdicts** is fallback only: use it when cloud probing is not
  activated, the task failed, or `DNSRaw` came back empty. Label those results `perspective=LOCAL_SINGLE_EGRESS`; a single egress cannot represent
  mainland vs overseas users, and this machine may sit behind a corporate proxy.
- Pass `--start-time` / `--end-time` when reading probe logs. Without an explicit window the service returns
  its own recent window, so tasks created tens of minutes earlier come back with empty `Data` — which looks
  exactly like "the domain does not resolve" and gets mis-recorded as `NOT_DETECTED`. `parse_probe_log.py`
  derives the window from `taskids.json.generated_at` minus 15 minutes when the flags are omitted.
- Disagreement between resolvers/points on the **first hop** or the **IP landing class** is a finding
  (`WARN_POINT_INCONSISTENT`). Disagreement **only** in the final IP list is not a finding by itself: the
  config APIs cannot enumerate the IP set behind an Anti-DDoS CNAME, and those A records are owned by the
  Anti-DDoS side. Do not write "normal GSLB behaviour" as the reason unless you measured per-location
  differences — state what was actually observed instead.

### Step 4 — C2 evidence is real (bound certificate only)
```bash
aliyun cas list-user-certificate-order --current-page 1 --show-size 50 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
# only when a bound certificate's list record carries no EndDate
aliyun cas get-user-certificate-detail --cert-id <CertId> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
```
- Criteria: `DescribeWebRules[].CertName` / `UserCertName` matched against the returned certificate `Name`;
  `EndDate` parsed into an ISO date and a `days_left` integer; `Expired` captured. Both are already in
  `access-config.json` under `cas_certs` — Step 4 judges, it does not probe.
- **[MUST] No local `openssl`, no served-certificate read.** C2's scope is the bound certificate's expiry only.
  Hostname coverage, chain completeness and served-vs-bound divergence are out of scope; do not add them back.
- **[MUST] `cas` is C2's only data source**, so it is fetched by default. `--no-cas`, a missing `yundun-cert`
  permission, an unmatched certificate name, or a record with no `EndDate` from either call all mean
  `NOT_DETECTED` for that domain — with the specific cause named. Never substitute a date.
- No bound certificate at all → `NOT_APPLICABLE_NO_CERT_BOUND`. That is not a FAIL and says nothing about
  whether an https port is configured.

### Step 5 — C3 chain is classified, not guessed
- Criteria: every hop carries a class and the tier that produced it (`config exact match` vs
  `signature auxiliary`). An `unknown` **first** hop sets `needs_agent_review=true` and must be resolved with
  evidence before the report is written.
- **[MUST] State what DNS cannot prove.** When the chain terminates at a CDN/WAF/GA or any third party's IPs
  with no Anti-DDoS hop, the report must say two things separately: Anti-DDoS **is not** the first layer
  (proven), and whether Anti-DDoS exists **behind** that layer is **not determinable from DNS** — the front
  layer's back-to-origin config is not public. Name the follow-up (read that layer's origin config). Never
  write "Anti-DDoS is behind the CDN" as a fact in this case.
- Scheduler cases must name the matched `RuleName` + `RuleType` label and quote the effective lines.
- C3 runs for domains whose C1 is `NOT_APPLICABLE_*` too. When a bare A record lands on an IP that is
  neither a configured origin nor a known Anti-DDoS instance IP, the verdict is `NOT_APPLICABLE_NO_IP_BASIS`
  — **not** `FAIL_DIRECT_TO_ORIGIN` and not any other `FAIL_*`, because this account cannot say whose IP that
  is. The detail must list the landing IP, that region's instance count and the account's known Anti-DDoS IPs,
  so the reader can see exactly what basis was missing.
- Verify the C3 `PASS_FIRST_LAYER` detail names **whose** CNAME the first hop is. If it reads "this domain's
  CNAME" while the hop actually belongs to another rule in this account, or matches only the
  `*.aliyunddos*.com` signature, the run is invalid.

### Step 6 — C4 vantage points are what you claim
```bash
aliyun cms describe-site-monitor-isp-city-list --ipv4 true --view-all true \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
aliyun cms create-instant-site-monitor --address "https://www.example.com/" --task-type "HTTP" \
  --task-name "ddoscoo-acc-www-example-com-https-443" --isp-cities '[{"city":"357","isp":"132"}]' \
  --options-json '{"time_out":5000}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
```
- Criteria: the selected point list is printed with country/city/ISP for both groups **before** probing, so
  the report can state exactly where the health result came from. Overseas points are those whose `Country.en`
  is not `China`; there are no hardcoded overseas codes.
- **[MUST] Both groups must be non-empty** (default 3 domestic + 3 overseas). Verify the domestic group's
  `Country.en` really is `China` — the response uses flat dotted keys and a bare `Country` that holds the
  numeric code, so reading it as a nested object silently puts every point in the overseas group.
  `create_probes.py` hard-stops before creating any paid task when this self-check fails.
- Cross-check the grouping against the probe log's own `countryCN` / `countryEN` per point: the log states where
  the probe actually ran, so it wins over the pre-selection when they disagree.
- HTTPS uses `--task-type HTTP` + an `https://` address. `TaskType` has no `HTTPS` enum.
- Per-point success = `HTTPResponseCode` ∈ 2xx/3xx **and** `errorCode` empty/0. Nothing else.
- If the overseas group is empty → C4-overseas `NOT_DETECTED`, with the coverage qualifier in the verdict.

## Scenario → recommended action → help doc

| Finding | Recommended action | Help doc |
|---------|--------------------|----------|
| C1 `NOT_APPLICABLE_NO_WEB_RULE` (branch 1) | Not a DNS defect — the Anti-DDoS side is not configured yet. Add a layer-7 forwarding rule (domain / protocol-port / origin), associate an Anti-DDoS IP so a CNAME is generated, then switch DNS. Report the prompt from `scope_gate[].c1_prompt` verbatim. | Protect a website: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/getting-started/protect-website-services · Onboarding best practices: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/best-practices-for-adding-a-service-to-an-anti-ddos-pro-or-anti-ddos-premium-instance |
| C1 `NOT_APPLICABLE_SCHEDULER_ONLY` (branch 2) | Scheduler onboarding is real, but scheduler rules are domain-agnostic and carry no layer-7 forwarding. Ask the customer whether this domain's traffic needs layer-7 forwarding through Anti-DDoS; if yes, a forwarding rule is required **in addition to** the scheduler rule. Name the matched `RuleName` + `RuleType` label. | Scheduler API: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/developer-reference/api-ddoscoo-2020-01-01-describeschedulerrules · Onboarding best practices (link above) |
| C1 `NOT_APPLICABLE_NO_CNAME_ASSIGNED` (branch 3) | Associate an Anti-DDoS IP with the existing forwarding rule — the CNAME is generated only after that, so no DNS change can fix it. When the region has 0 instances, say so explicitly: the rules are not backed by any instance. | Protect a website (link above) |
| C1 `FAIL_NO_RECORD` / `FAIL_CNAME_MISMATCH` | Switch the domain's DNS to the assigned Anti-DDoS CNAME. Lower the TTL beforehand, remove leftover A records, and verify per line (including any split-horizon records) after the switch. For the cross-use sub-case (the first hop is **another** domain's CNAME in this account) fix the binding rather than the DNS record. | Protect a website (link above) · Onboarding best practices (link above) |
| C1 `FAIL_A_RECORD_TO_ORIGIN` | Re-point to the Anti-DDoS CNAME **and** restrict the origin to Anti-DDoS back-to-origin ranges, otherwise the origin IP stays directly attackable. | Origin IP exposure solution: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/handle-exposure-of-the-origin-ip-address · Origin ACL: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/configure-acls-for-the-origin-server |
| C1 `FAIL_A_RECORD_TO_ANTIDDOS_IP` | Replace the A record with the assigned CNAME. Traffic does traverse Anti-DDoS today, but instance IPs change on migration/expansion and a hardcoded A record breaks without notice. Do **not** word this as "bypasses Anti-DDoS". | Onboarding best practices (link above) |
| C1 `FAIL_A_RECORD_UNKNOWN_TARGET` | Identify who owns the landing IP before recommending anything. If it is a stale record from a previous provider, delete it and switch to the CNAME; if the region has 0 instances the Anti-DDoS IP comparison set was incomplete, so mark the finding as needing human confirmation. | Onboarding best practices (link above) |
| C1 `WARN_POINT_INCONSISTENT` | Audit per-line/split-horizon records at the DNS provider, confirm the TTL switch finished, and re-check from the disagreeing regions. | — |
| C2 `FAIL_EXPIRED` / `FAIL_CRITICAL` | Renew the certificate, upload the new one to the certificate service, and **re-bind it on the Anti-DDoS website rule** — uploading without switching the binding is the common miss. Then re-run C2 to confirm the bound `EndDate` moved. | Certificate APIs: https://help.aliyun.com/en/ssl-certificate/developer-reference/api-cas-2020-04-07-getusercertificatedetail |
| C2 `WARN_EXPIRING` | Schedule the renewal now; note the bound certificate name and the exact `EndDate` in the report. | (same as above) |
| C2 `NOT_APPLICABLE_NO_CERT_BOUND` | Nothing to renew — no certificate is bound. Do not report it as a defect, and do not infer anything about https ports (out of C2's scope). | — |
| C2 `NOT_APPLICABLE_NO_CAS_DATA` | The account cannot supply the expiry: grant `yundun-cert` read access (`AliyunYundunCertReadOnlyAccess`), or confirm the certificate really is uploaded in this account, then re-run. Never report it as healthy. | (same as above) |
| C2 `NOT_DETECTED` | Basis present, observation missing: `cas` was skipped → re-run without `--no-cas`; `EndDate` unparseable → read it in the certificate console. | (same as above) |
| C3 `FAIL_NOT_FIRST_LAYER` | First establish the sub-case. **(b) Anti-DDoS visible at hop ≥ 2**: decide the intended layering — either put Anti-DDoS first (DNS → Anti-DDoS CNAME → WAF/CDN → origin), or keep the CDN/WAF in front and accept that volumetric attacks hit that layer first, then use a traffic scheduler to bring Anti-DDoS in. **(c) no Anti-DDoS hop, chain ends at a third party**: read that layer's back-to-origin configuration to find out whether Anti-DDoS is behind it — DNS cannot tell you. In both cases state the trade-off; do not silently "fix" the customer's architecture. | Onboarding best practices (link above) · Scheduler API: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/developer-reference/api-ddoscoo-2020-01-01-describeschedulerrules |
| C3 `FAIL_DIRECT_TO_ORIGIN` | Re-point DNS to Anti-DDoS and lock down the origin. Then run `alibabacloud-ddos-origin-exposure-detector` for the full exposure assessment. | Origin IP exposure solution (link above) |
| C3 `NOT_APPLICABLE_NO_IP_BASIS` | This account cannot say whose IP the domain resolves to, so C3 makes no claim. Establish the IP's owner by hand (previous provider, CDN, a released Anti-DDoS instance, or the customer's own ECS), then complete or re-point the onboarding. Note that C1 has usually already produced the actionable finding for the same domain, because C1 compares against that domain's own `Cname`. | Onboarding best practices (link above) |
| C3 `FAIL_SCHEDULER_NO_DDOS_LINE` | Add or enable an Anti-DDoS line (`ValueType=1`, `Status=1`) in the matched scheduler rule. | Scheduler API (link above) |
| C3 `INFO_SCHEDULER_ON_DEMAND` | No change needed. Tell the customer explicitly that peacetime traffic is not scrubbed by Anti-DDoS and that switch-in is governed by the rule's thresholds and `RestoreDelay`. | Scheduler API (link above) |
| C4 `BOTH_FAIL_5XX` | Back-to-origin failure: verify the origin allows Anti-DDoS back-to-origin ranges, and that the origin port/protocol match the forwarding rule. | Origin ACL: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/configure-acls-for-the-origin-server |
| C4 overseas fail, mainland ok | Check the served certificate chain manually first (overseas clients validate strictly — **this is outside C2's scope**, C2 only reads the bound certificate's expiry), then whether the scheduler's overseas acceleration line is effective, then instance-region fit (international edition in `ap-southeast-1` vs mainland-facing business). | Scheduler API (link above) |
| C4 mainland fail, overseas ok | Check ICP filing status and mainland-line DNS (correlate with C1). | — |
| Any bypass finding | Recommend a full origin-exposure run: skill `alibabacloud-ddos-origin-exposure-detector`. | https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/handle-exposure-of-the-origin-ip-address |

> Deep links move as the documentation structure changes. If one is broken, search the topic in the Alibaba
> Cloud Help Center https://help.aliyun.com rather than guessing a new URL.

## Report Template (`report.md` structure)

Write it to `$OUT_DIR` per SKILL.md Step 7. Do not omit sections, and do not paraphrase the ticket URL.

```markdown
# Anti-DDoS Proxy Onboarding Configuration Check Report

## 1. Verdict
Access configuration check found issues | Access configuration needs attention | Access configuration check passed
(if any coverage < 100%: "..., with N items not detected (see Not-Detected List)")
- Region(s) checked: ...  | Probe mode: cloud | local  | Traffic scheduler in use: yes/no
- Failures: C1 x, C2 y, C3 z, C4 w   Warnings: ...   Informational: ...   Config prerequisites (`NOT_APPLICABLE_*`): ...

## 2. Scope & Config
- Ownership gate (Step 1.5): PASS | FAIL_UNRESOLVED — per target: FOUND_EXACT / FOUND_WILDCARD (covering rule) / FOUND_VIA_SCHEDULER (matched scheduler CNAME) / FOUND_INSTANCE; regions searched: ...
- Instance(s): <InstanceId> / <RegionId> / <Ip>
- Layer-7 domains in scope: N (wildcards: M, handling chosen: ...)
- C1 precondition branches: 1->a, 2->b, 3->c, 4->d  (C1 applicable = d; instances per region: ...)
- Layer-4 port rules: out of scope for this skill (no DNS/certificate/HTTP path)
- Scheduler rules: <RuleName> (<RuleType label>) -> CNAME <Cname>, effective lines: ...

## 3. C1 — DNS resolution vs Anti-DDoS CNAME
| Domain | Branch | Configured CNAME | Observed First Hop | Observed Final IPs | Vantage Points | Verdict | Next Step for the Customer |
(Branch = 1/2/3/4 of the C1 precondition layer, decided in SKILL.md Step 3. Config / config / probe / probe
columns stay strictly separate;
empty resolution = "no resolution"; a branch-3 Configured CNAME reads "not generated" and branches 1-2 read
"no rule", never a blank that could be mistaken for a probed value. The Next Step column is mandatory for
every `NOT_APPLICABLE_*` row — copy it from `scope_gate[].c1_prompt` or the verdict detail.)

## 4. C2 — Bound certificate expiry
| Domain | Bound CertName / UserCertName | CAS EndDate | Days Left | Expired flag | Verdict |
(no served-certificate, hostname-match or chain-depth columns — those are out of C2's scope. For
`NOT_DETECTED` rows the Reason column must name which of the four causes applied.)

## 5. C3 — Architecture: is Anti-DDoS the first layer?
| Domain | CNAME Chain (hop -> class) | Anti-DDoS Position | Scheduler Rule | Verdict |
(plus one line of reasoning for every FAIL / INFO / UNKNOWN_HOP)

## 6. C4 — Access health
| Domain | URL Probed | Group | Points ok/total | HTTP Codes | TotalTime (ms) | errorCode | Verdict |
Group = mainland | overseas. Follow the table with the cross-region divergence signal and its likely causes.

## 7. Not-Detected List
| Item | Check | Reason | Suggested follow-up |
(write `None` if empty; never omit the section)

## 8. Coverage
- C1: applicable (branch 4) probed X / Y (Z%) — the denominator excludes branches 1-3 by design; their count is stated in section 2, never silently dropped
- Every check: `NOT_APPLICABLE_*` items are excluded from the denominator **and** listed separately with their reason; `NOT_DETECTED` items stay in the denominator as coverage gaps. The two are never merged into one number
- C2: X / Y (Z%) — denominator = domains with a certificate bound only; `NOT_APPLICABLE_NO_CERT_BOUND` domains are excluded and their count stated separately
- C3: probed X / total Y (Z%)
- C4 mainland: probed X / total Y (Z%)   C4 overseas: probed X / total Y (Z%)

## 9. Recommended Actions & Reference Docs
(one block per finding, from the mapping table above, with the help-doc links)

## Note
This is an automated check result based on the current configuration and the probe perspective used
(cloud site monitor / local). If you have questions about the verdict, you may submit an Alibaba Cloud
ticket: https://selfservice.console.aliyun.com/ticket/createIndex
```

## Finalize checklist — verify every item BEFORE returning `report.md`

1. **Verdict** is exactly one of the three levels, with the coverage qualifier appended when any coverage < 100%.
2. **C1 table** has the 8 columns in the order above. The configured CNAME column and the observed columns
   stay separate even when empty (write `-`). Every row states its precondition branch, and every
   `NOT_APPLICABLE_*` row carries the customer-facing prompt — a bare label with no next step is an
   incomplete report. Branches 1-3 must still show their C2/C3/C4 rows: C1 being inapplicable never skips
   the other checks.
3. **C2 table** shows the bound certificate name, the `cas` `EndDate` **and** `Days Left` for every domain that has a certificate bound, healthy ones included. It contains no served-certificate, hostname-match or chain-depth column, and every `NOT_DETECTED` row names its cause.
4. **C3 table** shows the classified chain, and every `FAIL_*` / `INFO_*` / `UNKNOWN_HOP` row has a written
   reason. Scheduler rows name the rule and its `RuleType`. Any `PASS_FIRST_LAYER` row states **whose** CNAME
   the first hop is — this domain's, another rule's in this account, or signature-only. Any
   `NOT_APPLICABLE_NO_IP_BASIS` row lists the landing IP, that region's instance count and the account's known
   Anti-DDoS IPs, so the reader can see exactly what basis was missing.
5. **C4 table** separates mainland from overseas, and the divergence signal is stated even when both groups
   are healthy (write `none`).
6. **Not-Detected List** is present. `None` if empty.
7. **Coverage** lines are per check, arithmetic verified. Correct: `5/5 (100.0%)`, `6/11 (54.5%)`.
   Wrong: `1/11 (100%)`, `11/1 (10%)`, `5/5 (10%)`. C1's denominator is the branch-4 (applicable) count only,
   and section 2 states the full branch distribution so the excluded domains stay visible.
8. **Closing Note** ends with the ticket URL verbatim:
   `... you may submit an Alibaba Cloud ticket: https://selfservice.console.aliyun.com/ticket/createIndex`.
   Never shortened, never paraphrased.
9. **No fabrication, no substitution.** Every domain / CNAME / IP / port / certificate name / date / status
   code is copied character-for-character from the raw API or probe output. Unknown = `-` plus a Not-Detected
   entry. **Spot-check**: after writing, grep 3 random CNAME/IP/date values from the raw JSON and confirm they
   appear verbatim in the report; on mismatch, regenerate that table from raw data.
10. **Chat reply is copied, not recomputed.** Use exactly:
    `Verdict: <from report.md> | C1: <x/y (z%)> | C2: <...> | C3: <...> | C4 mainland: <...> | C4 overseas: <...> | Not-Detected: <list or None> | ProbeMode: <cloud|local> | Region(s): <...>`.
    If a chat number differs from `report.md`, the chat reply is invalid — regenerate it from the file.
    The `ProbeMode` and `Region(s)` suffixes are mandatory, not decoration: they let the reader tell a
    multi-vantage cloud result from a single-egress local one without opening the report, and they echo the
    Step 0 disclosure (which APIs were called, and that cloud probing is pay-as-you-go) in the same message
    that delivers the verdict.

    **[MUST] Then append the situation lines that apply to this run.** The pipe-delimited line above reports
    *coverage*; on its own it does not tell the reader what happened. Add one short line per situation that
    actually occurred, in the plain words a reader would search for.

    *Where the zh wording lives*: this file is English-only. The exact Chinese tokens the reply must carry
    (not-found, degraded, baseline-free, not-detected, local single-egress, mainland/overseas) are listed
    once, in SKILL.md Step 7, and the pre-check item labels (CLI version / plugins / credentials / the
    pre-checks as a whole) are listed once, in SKILL.md Step 0.5 — use those verbatim rather than
    paraphrasing them here. They are not
    decoration: a Chinese-reading customer and the acceptance checks both look for those exact terms, so an
    English paraphrase in the reply reads as if the finding had been skipped.
    - Step 0.5 ran → name each pre-check item and its outcome: CLI version (against the 3.3.3 minimum), plugin list,
      whether a valid credential profile exists, and whether `dig` / `curl` are available.
    - The run began as a disclosure request → name the products and APIs (`ddoscoo`, `Cms`/`cms`, `cas`), the
      cost basis (the site-monitoring service, pay-as-you-go for cloud, free for local), and the parameters still to confirm
      (`ProbeMode`, `RegionId`, `Domain`). This applies **even when the user then supplied the parameters and the
      check continued**: the words must reach the *final* reply, not only the round that asked. A two-round run
      that discloses first and reports results last otherwise ends with a message that never answers the
      question the customer opened with.
    - The early-stop condition was evaluated → give the numbers (instance `TotalCount`, web-rule `TotalCount`), the region
      tested, and whether the run continued or stopped early.
    - The gate returned `NOT_FOUND_IN_ACCOUNT` → say explicitly that the target was not found, list the existing configured domains offered,
      and record the user's choice, or the substitute target actually checked.
    - Degraded mode was used → say the run was degraded, state that the results are baseline-free observations, and name the
      `NOT_APPLICABLE_*` verdicts that apply.
    - A wildcard was involved → say which option was taken (skip / common-prefix sample / user-supplied subdomains) and list
      the exact subdomains probed.
    - `ProbeMode=local` → say the run was local and single-egress, and that the mainland-vs-overseas C4 comparison was not detected.
    - C4 ran → report mainland and overseas separately, each with its group verdict (`HEALTHY` / `PARTIAL` /
      `UNAVAILABLE` / `WARN_SLOW`) and the cross-region difference signal.

    **[MUST] Never write the underscore token `NOT_DETECTED` in the chat reply.** Write the zh not-detected wording or "Not-Detected"
    followed by the concrete cause. Two reasons: (1) a bare token with no cause is exactly the incomplete
    answer SKILL.md forbids; (2) under `ProbeMode=cloud` the C4 mainland-vs-overseas comparison is never
    legitimately "not detected" — both groups have points by construction (3 + 3), and "every point failed" is
    `UNAVAILABLE`, which *is* an answer. The underscore tokens still belong in the `report.md` tables and the
    JSON evidence, where they are machine-checkable; only the customer-facing chat line uses words. **This is
    a wording rule, not a licence to omit anything** — an undetected item must still be listed here and in the
    Not-Detected List, with its cause.
11. **No `NEED_AGENT_REVIEW` label reaches the customer.** Resolve it first and record the reasoning.
12. **Layer-4 scope statement** is present, so the reader knows port-onboarding rules were not silently dropped.
13. **Ownership gate is stated.** Section 2 records the Step 1.5 result and the regions searched. If any
    target was `NOT_FOUND_IN_ACCOUNT`, the report must say so explicitly, carry C1 as
    `NOT_APPLICABLE_NO_WEB_RULE` (with the add-a-forwarding-rule prompt) and C3 as
    `NOT_APPLICABLE_NO_CONFIG_BASELINE`, and must not present any baseline-free observation as an onboarding
    verdict. If the gate was `FAIL_UNRESOLVED` and the user never opted into degraded mode, there is no
    report to write — the run stopped at Step 1.5.
14. **No `NOT_APPLICABLE_*` was upgraded to a FAIL, and none was dropped.** Branches 1-3 are config
    prerequisites with a named next step, not DNS defects and not passes. Verify the count of
    `NOT_APPLICABLE_*` rows in section 3 equals the branch 1+2+3 total in section 2.
