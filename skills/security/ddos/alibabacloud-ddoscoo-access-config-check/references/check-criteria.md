# Check Criteria — C1 / C2 / C3 / C4

Judgment rules for `alibabacloud-ddoscoo-access-config-check`. Read this before turning probe output into a
verdict. The scripts compute the deterministic cases; everything marked *agent judgment* is yours to decide
using the rules here.

## Verdict levels

| Level | Meaning | Feeds overall verdict as |
|-------|---------|--------------------------|
| `PASS_*` | Config and reality agree. | no issue |
| `INFO_*` | Behaves as designed, but the customer may hold a wrong expectation (e.g. scheduler on-demand). Must be stated in the report. | attention |
| `WARN_*` | Works today, fragile or partially inconsistent; will break or already degrades under some condition. | attention |
| `FAIL_*` | The onboarding is wrong or ineffective for this domain. | issue |
| `NOT_DETECTED` | Could not be probed (no permission, no probe point, wildcard, tool missing, IPv6, timeout). | coverage gap — **never** counts as PASS |
| `NOT_APPLICABLE_*` (all four checks: C1 `NOT_APPLICABLE_NO_WEB_RULE` / `NOT_APPLICABLE_SCHEDULER_ONLY` / `NOT_APPLICABLE_NO_CNAME_ASSIGNED`; C2 `NOT_APPLICABLE_NO_CERT_BOUND` / `NOT_APPLICABLE_NO_CAS_DATA`; C3 `NOT_APPLICABLE_NO_IP_BASIS` / `NOT_APPLICABLE_NO_CONFIG_BASELINE`) | This account cannot supply the information the judgment needs — no rule, no generated CNAME, no bound certificate, no `cas` record for it, or a landing IP that matches nothing the account knows. C1's branches additionally carry a mandatory customer-facing prompt with the next config step. The other checks still run. | attention — **never** a FAIL and **never** a PASS; excluded from that check's coverage denominator and listed separately |
| `NOT_APPLICABLE_NO_CONFIG_BASELINE` | The target is not in this account (Step 1.5 gate returned `NOT_FOUND_IN_ACCOUNT`), so there is no `Cname` / `RealServers` / `ProxyTypes` / `CertName` to compare against. Only baseline-free public observation is possible (C4 single-egress health, descriptive chain). C2 has no bound-certificate name to look up, so it is `NOT_DETECTED`. Used for C3 and for the degraded observation mode; C1 uses `NOT_APPLICABLE_NO_WEB_RULE` in that situation. | out of scope — **never** an onboarding verdict |
**The account-basis principle (applies to all four checks).** C1-C4 are all judged against this account's Anti-DDoS instance and domain configuration. When the account cannot supply the information a judgment needs, the result is `NOT_APPLICABLE_*` — **not** `FAIL` and **not** `NOT_DETECTED`. Reserve `NOT_DETECTED` for the case where the basis *does* exist but the observation could not be made (dig errored, no public resolution, probe never ran, a returned value could not be parsed). The three must never be collapsed into one column: not-applicable = no basis, not-detected = basis present but unobserved, pass = measured and correct.

| `NEED_AGENT_REVIEW` | Evidence is ambiguous (e.g. an unclassifiable CNAME hop). Resolve it with the rules below before writing the report; never ship this label to the customer as a conclusion. | decide, then re-level |

---

## C1 — DNS resolution vs Anti-DDoS CNAME consistency

C1 asks one question: does the domain's public DNS point at the CNAME **this account generated for that
domain**? The question is only answerable when such a CNAME exists, so C1 runs a **precondition layer
first**; the comparison rules below apply only at the last branch.

### Precondition layer (decide this before comparing anything)

| # | Precondition | C1 verdict | What to tell the customer |
|---|--------------|------------|---------------------------|
| 1 | No layer-7 forwarding rule covers the domain (no `DescribeWebRules` entry, wildcards included), and DNS does not point at any scheduler CNAME of this account | `NOT_APPLICABLE_NO_WEB_RULE` | There is no baseline to compare against. If the domain needs Anti-DDoS protection, add a layer-7 forwarding rule (domain / protocol-port / origin), associate an Anti-DDoS IP so a CNAME is generated, and only then switch DNS. |
| 2 | No layer-7 rule, but DNS resolves to a scheduler CNAME from `DescribeSchedulerRules` | `NOT_APPLICABLE_SCHEDULER_ONLY` | Scheduler onboarding is legitimate, but scheduler rules are domain-agnostic and carry no layer-7 forwarding. Ask whether this domain's traffic needs layer-7 forwarding through Anti-DDoS — if it does, a layer-7 rule is still required **in addition to** the scheduler rule. Name the matched rule (`RuleName` + `RuleType` label). |
| 3 | A layer-7 rule exists but `DescribeWebRules[].Cname` is empty — no Anti-DDoS IP associated, so no CNAME was generated | `NOT_APPLICABLE_NO_CNAME_ASSIGNED` | Associate an Anti-DDoS IP with the rule; the CNAME appears only after that. If the queried region currently has 0 instances, say so explicitly: rules with no instance behind them are exactly why `Cname` is empty, and the customer cannot fix it by editing DNS. |
| 4 | A layer-7 rule exists **and** `Cname` is non-empty | **C1 applies** → run the comparison rules | |

`NOT_APPLICABLE_*` is **not** a pass and **not** a coverage gap. It is a config-side prerequisite finding
with its own remediation, and it must be reported as such. Turning it into a FAIL would tell the customer
"you configured DNS wrong" when the truth is "you have not finished configuring Anti-DDoS" — different
action, different owner.

Branches 1 and 2 are produced by the Step 1.5 ownership gate (`fetch_config.py` → `resolve_scope`), because in
those cases there is no web rule for the domain at all. Branches 3 and 4 are produced by `check_local.py`.

**Cases 1–3 still run C2 / C3 / C4.** C3 in particular stays meaningful: it reports what the path actually
is when Anti-DDoS is not in it. Never skip the remaining checks just because C1 has no baseline.

### Comparison rules (branch 4 only)

**Config truth**: `DescribeWebRules[].Cname` for the domain; `DescribeSchedulerRules[].Cname` when a
scheduler is in play. **Probe truth**: the CNAME chain and final IPs observed from each vantage point
(local `dig` per resolver + Cms `DNS` probe per point).

1. Normalize before comparing: lowercase, strip trailing dots. `DDOS123.ALIYUNDDOS1020.COM.` and
   `ddos123.aliyunddos1020.com` are the same value.
2. The comparison target is the **first CNAME hop**, not the final IP — for two measured reasons.
   **(a) The config side cannot enumerate the IP set behind an Anti-DDoS CNAME.** `DescribeInstances[].Ip`
   is incomplete: on a real account it listed only 2 instance IPs while 4 of the 6 resolvable Anti-DDoS
   CNAMEs resolved to IPs *outside* that set, and one configured CNAME had no A record at all after its
   instance was refunded. So "the final IP is not a known Anti-DDoS IP" proves nothing about correctness.
   **(b) Those A records are owned by the Anti-DDoS side** and change with node scheduling, migration and
   expansion, with no customer-side change. Differing final IPs alone are therefore **not** an inconsistency.
   Do **not** justify this with "Anti-DDoS CNAMEs sit behind GSLB, so IPs differ per region" unless you
   actually measured per-region differences — on that same account four resolvers (system, 223.5.5.5, 8.8.8.8,
   1.1.1.1) returned an identical single IP for every Anti-DDoS CNAME. (GSLB-style per-location answers are
   real for **CDN** domains; that is a different case.)
3. Only treat resolution as inconsistent when the **first hop differs** or the **IP landing class differs**
   (one point lands on the origin, another on Anti-DDoS).
4. **Cloud probing is the primary DNS source for C1 and C3; local `dig` is fallback only.**
   `DescribeSiteMonitorLog` returns `DNSRaw` — the whole ordered answer section, pipe-separated, e.g.
   `a.com CNAME b.aliyunddos0018.com TTL 600|b.aliyunddos0018.com A 1.2.3.4 TTL 10|any: type 41 string (…)|`.
   It also returns a separate `cnames` field, the final `ips`, and `dnsServer` (which resolver that point used).
   So a cloud point proves the first hop **and** the whole chain, from many vantage points at once.
   An earlier revision of this file claimed cloud DNS returns final IPs only — that was **wrong** and it pushed
   C1/C3 onto local `dig` unnecessarily. Skip the `any: type 41 …` OPT pseudosection when parsing; it is not
   an answer record. Cross-check `DNSRaw`'s first hop against the `cnames` field and record any disagreement.
   Local `dig` is used only when cloud probing is unavailable (service not activated, task failed, `DNSRaw`
   empty). It is a single-egress view and this machine may sit behind a corporate proxy, so its results must be
   labelled `perspective=LOCAL_SINGLE_EGRESS` and never reported as "resolution is consistent worldwide".
   Judging logic is **not** duplicated between the two sources: `parse_probe_log.py` imports `judge_c1`,
   `judge_c3`, `classify_ips` and `find_scheduler_rule` from `check_local.py`, so both observation sources
   share one implementation.
5. The IP-landing bucket (origin / Anti-DDoS IP / other) is **secondary** evidence, kept in
   `observed_ip_landing` and never allowed to overwrite the chain-based `verdict`. `NEED_AGENT_REVIEW` there
   only means "the final IP is in neither configured bucket" — it is not a C1 conclusion.
   In branches 1–3 the cloud observation is **not** a C1 verdict at all: record it as the IP-landing
   observation and let C3 decide it (`FAIL_DIRECT_TO_ORIGIN`), because C1 has no baseline to fail against.

**Verdicts (decision order = priority; stop at the first match)**

| Verdict | Condition | Level |
|---------|-----------|-------|
| `FAIL_NO_RECORD` | No CNAME and no A/AAAA from any vantage point. DNS never switched, or the record was deleted. **[MUST] Distinguish this from `NOT_DETECTED`.** A cloud point that returned `errorCode: 0` with a `DNSRaw` containing only the OPT pseudosection (`any: type 41 string (… EDNS …)`) and empty `ips`/`cnames` **succeeded** — the observation was made and the answer is "no records", so this is `FAIL_NO_RECORD`. Reserve `NOT_DETECTED` for a point that could not observe at all: non-zero `errorCode`, or no `DNSRaw` and no `ips` whatsoever. Getting this backwards downgrades the single most important finding (the domain does not resolve) into "not detected". Corroborate with the resolver status code: `NXDOMAIN` means the name does not exist, which is stronger evidence than an empty answer. | FAIL |
| `FAIL_A_RECORD_TO_ORIGIN` | Any observed IP (at any hop's terminus) is in the domain's origin IP set. Traffic bypasses Anti-DDoS. Overrides every CNAME-level verdict. | FAIL |
| `FAIL_CNAME_MISMATCH` | First CNAME hop is neither this domain's `Cname` nor any scheduler `Cname`. Three sub-cases, all FAIL, all named in the detail: (a) the hop is **another domain's** web-rule CNAME in this account — configuration cross-use; (b) the hop carries an Anti-DDoS signature (`*.aliyunddos*.com`) but is not this domain's value — instance migration or a re-created rule left a stale CNAME; (c) the hop is unrelated (third-party CDN/WAF/GSLB, or the customer's own record). | FAIL |
| `FAIL_A_RECORD_TO_ANTIDDOS_IP` | No CNAME; A records point at an Anti-DDoS instance IP. Because the domain reached branch 4 it *has* an assigned CNAME and is not using it, so C1 fails — traffic does traverse Anti-DDoS today, but the onboarding breaks the moment the instance IP changes. The detail must give the correct fix (switch to the CNAME), and must not be worded as "bypasses Anti-DDoS". | FAIL |
| `FAIL_A_RECORD_UNKNOWN_TARGET` | No CNAME; A records point at neither a known Anti-DDoS instance IP nor an origin IP (stale record / third party). `DescribeInstances[].Ip` is not a complete Anti-DDoS IP set, so when the region has 0 instances the detail must carry a human-confirm caveat about IP ownership. | FAIL |
| `WARN_MIXED_RECORDS` | The expected CNAME coexists with other records (leftover A record, per-line records). | WARN |
| `WARN_POINT_INCONSISTENT` | Vantage points disagree on the first hop or on the IP landing class. Split-horizon DNS, in-flight TTL switch, or pollution. List which regions/ISPs differ. | WARN |
| `PASS_CONSISTENT` | First hop == this domain's configured `Cname`. | PASS |
| `PASS_CONSISTENT_VIA_SCHEDULER` | First hop == a scheduler `Cname`. Under a scheduler this **is** consistent — do not report a mismatch just because it differs from the web-rule CNAME. | PASS |
| `NOT_DETECTED` | `dig` unavailable or errored for every resolver. | coverage gap |

**Field isolation (MUST)**: keep three columns separate in the report — configured `Cname`, origin IP set,
and observed resolution. Never fill the "observed" column from config. No resolution means write
`no resolution`. In branches 1–3 the configured-`Cname` column reads `not generated` (branch 3) or
`no rule` (branches 1–2), never a blank that could be mistaken for a probed value.

---

## C2 — Bound certificate expiry

**Scope (narrow, by design)**: C2 answers exactly one question — *when does the certificate bound on
Anti-DDoS for this domain expire?* Nothing else.

**The only data path**

`DescribeWebRules[].CertName` / `UserCertName` (which certificate is bound) → `cas` (`ListUserCertificateOrder`,
and `GetUserCertificateDetail --CertId <id>` when the list record carries no `EndDate`) → `EndDate` / `Expired`.

`cas` is therefore **required for C2**, not optional. `fetch_config.py` queries it by default; `--no-cas` skips
it and every domain's C2 becomes `NOT_DETECTED`.

**Explicitly out of C2's scope — do not judge, do not report**
- The certificate actually served to visitors (local `openssl s_client`): its validity, CN/SAN hostname
  coverage, chain completeness. Not probed at all.
- Configuration-consistency findings such as "https port configured but no certificate bound" or "certificate
  bound but no https port".
- Comparing the bound certificate's expiry against a served certificate's `notAfter`.

If the customer asks about any of these, say they are outside this check's scope rather than silently
re-adding them.

**Never** read `DescribeWebRules[].CertExpireTime` — the official API reference marks it *not currently used*.
Reporting it as an expiry date is a fabrication.

**Expiry thresholds** (`days_left` = `EndDate` − today, in days)

| days_left | Verdict | Level |
|-----------|---------|-------|
| `Expired=true`, or < 0 | `FAIL_EXPIRED` — the bound certificate has already expired | FAIL |
| 0 – 7 | `FAIL_CRITICAL` — renew immediately | FAIL |
| 8 – 30 | `WARN_EXPIRING` — schedule renewal | WARN |
| > 30 | `PASS` | PASS |

**Other C2 verdicts**

| Verdict | Condition | Level |
|---------|-----------|-------|
| `NOT_APPLICABLE_NO_CERT_BOUND` | `CertName` and `UserCertName` are both empty — there is no bound certificate, so there is no expiry to check. **Not a defect and not a FAIL**; the domain may simply be HTTP-only. Do not infer anything about whether an https port is configured. | n/a |
| `NOT_APPLICABLE_NO_CAS_DATA` | A certificate **is** bound but this account cannot supply its expiry: the bound name matched no `cas` record (certificate not in this account, deleted, or no `yundun-cert` read permission), or the matched record carries no `EndDate` from either `cas` call. Per the account-basis principle this is **not** a coverage gap — there is no basis to judge. Never report it as healthy and never fabricate a date. | n/a |
| `NOT_DETECTED` | The basis exists but the observation was not made or not usable: `cas` was skipped (`--no-cas`), or `cas` returned an `EndDate` that could not be parsed into a date. Say which, because re-running fixes the first and a console check fixes the second. | coverage gap |

**Report the bound certificate name, the `EndDate` and the remaining days for every domain that has one,
including healthy ones.** A bare "PASS" gives the customer nothing to plan a renewal around. For
`NOT_DETECTED`, report *which* of the four causes applied — they have different fixes (grant permission vs
re-upload the certificate vs re-run with `cas` enabled).

---

## C3 — Is Anti-DDoS the first layer on the Internet path?

Walk the CNAME chain (cap 8 hops, with loop detection) and classify **every** hop, then judge the **order**.
Presence of Anti-DDoS somewhere in the chain is not the same as Anti-DDoS being first.

**What DNS can and cannot prove here — state the difference in every report**

| Proposition | Provable from DNS? | Why |
|-------------|--------------------|-----|
| Anti-DDoS **is** the first layer | **Yes** (positive) | First hop == this domain's Anti-DDoS CNAME, or a scheduler CNAME with an effective Anti-DDoS line |
| Anti-DDoS **is not** the first layer | **Yes** (negative) | The first hop is something else. This alone answers the customer's question |
| Anti-DDoS sits at hop ≥ 2, i.e. genuinely *behind* another layer | **Only sometimes** | Visible only when the front layer **delegates onward via CNAME** — the traffic scheduler and GTM/GSLB-style delegation do. A typical CDN/WAF **does not** |
| Whether Anti-DDoS exists behind a CDN / WAF / GA that terminates the chain | **No** | The front layer's back-to-origin configuration is not in public DNS; it resolves its origin internally at request time. Public DNS shows `domain -> cdn.example.net -> CDN node IPs` and stops there |

So the honest C3 statement for a CDN-fronted domain is: *"Anti-DDoS is not the first layer — attack traffic
reaches the front layer unscrubbed. Whether Anti-DDoS exists behind that layer cannot be determined from DNS;
read the front layer's own back-to-origin configuration."* Never assert "Anti-DDoS is behind the CDN" as a
fact when the chain simply terminated at the CDN.

One reverse-direction signal that **is** available inside this skill: if the Anti-DDoS web rule's own origin
(`RealServers[]`, `RsType=1`) is a CDN/WAF domain, that proves the **opposite** order
(Anti-DDoS → CDN → real origin). It is not evidence for CDN → Anti-DDoS.

**Hop classification** — two tiers, and the tier must be visible in the evidence:

| Tier | Test | Example classes |
|------|------|-----------------|
| **Authoritative** | Exact match (normalized) against the `expected_cnames` set built in Step 2 | `antiddos_config`, `scheduler_config` |
| **Auxiliary** | Signature suffix in the CNAME. Non-exhaustive; a miss means `unknown`, never a guess | `antiddos` (`.aliyunddos`), `alicloud_waf` (`.aliyunwaf.com`, `.yundunwaf.com`), `alicloud_cdn` (`.kunlun`, `.tbcache.com`, `.cdngslb.com`), `alicloud_dcdn` (`.danuoyi.`), `alicloud_ga` (`.aliyunga`), `cloudflare` (`.cdn.cloudflare.net`), `akamai` (`.akamaized.net`, `.akamaiedge.net`), `aws_cloudfront` (`.cloudfront.net`), `azure_cdn` (`.azureedge.net`), `tencent_cdn` (`.cdn.dnsv1.com`, `.cdntip.com`) |

An `unknown` **first hop** blocks a confident C3 verdict → `needs_agent_review`. Judge it by: does the
customer say they use that CDN/WAF? Does the terminal IP belong to a known provider's range? Is it explained
by a scheduler rule's `Rules[].Value`? Record your reasoning in the report; do not silently bucket it.

**Verdicts**

| Verdict | Condition | Level |
|---------|-----------|-------|
| `PASS_FIRST_LAYER` | First hop is an Anti-DDoS CNAME, so attack traffic is scrubbed before anything else. **The detail must state whose CNAME it is**, in three tiers: (a) it equals this domain's own `Cname` — say so; (b) it is some other rule's `Cname` in this account — say it is *not* this domain's, name the domain's own `Cname` (or that it is empty), and require a human to confirm the binding, because the other rule's protocol/port and origin may not fit this domain; (c) it only matches the `*.aliyunddos*.com` signature and is no rule's `Cname` in this account — say the ownership is unconfirmed and set `needs_agent_review`. Never write "this domain's CNAME" for (b) or (c). | PASS |
| `PASS_VIA_SCHEDULER` | First hop is a scheduler CNAME whose rules contain an effective Anti-DDoS line (`ValueType=1` **and** `Status=1`), or the first hop is a line value of a matched scheduler rule (e.g. CDN interaction). | PASS |
| `INFO_SCHEDULER_ON_DEMAND` | Scheduler `RuleType` ∈ {2 tiered protection, 3 overseas acceleration, 8 secure acceleration}: by design, peacetime traffic takes the acceleration/cloud-resource line and Anti-DDoS only switches in under attack (`RestoreDelay` governs switching back). **Not a defect** — but the customer must know their normal traffic is not being scrubbed. | INFO |
| `WARN_FIRST_LAYER_VIA_A_RECORD` | Anti-DDoS is first, but reached through an A record to the instance IP instead of the CNAME. | WARN |
| `WARN_MULTI_PATH` | Different vantage points see different first layers (per-line DNS, scheduler mid-switch). | WARN |
| `WARN_SCHEDULER_UNMATCHED` | First hop matches a scheduler CNAME pattern but no rule could be located. | WARN |
| `FAIL_NOT_FIRST_LAYER` | The first hop is not Anti-DDoS and no scheduler rule explains the architecture. Attack traffic reaches that front layer unscrubbed. The detail **must** name which sub-case applies, because they have different follow-ups: **(b) provable-behind** — Anti-DDoS is visible at hop ≥ 2, so the front layer delegates onward by CNAME; state the hop position. **(c) undeterminable** — no Anti-DDoS hop anywhere and the chain terminates at a third party's IPs; state plainly that Anti-DDoS is not first **and** that whether it exists behind that layer cannot be determined from DNS, plus how to find out (read the front layer's back-to-origin config). Sub-case (c) is the common one for any CDN/WAF-fronted domain. | FAIL |
| `FAIL_DIRECT_TO_ORIGIN` | Resolution terminates on an **origin IP** with no Anti-DDoS hop. The IP set must actually contain a configured origin; otherwise use the next row. | FAIL |
| `NOT_APPLICABLE_NO_IP_BASIS` | No CNAME hop at all, and the bare A record matches **neither** an origin IP **nor** a known Anti-DDoS instance IP. This account cannot say whose IP that is, so C3 has no basis to judge — it may not claim "Anti-DDoS is not in the path" and may not claim "direct to origin". `DescribeInstances[].Ip` is measurably incomplete (on a real account: 2 instance IPs listed while 4 of 6 resolvable Anti-DDoS CNAMEs resolved outside that set), so a non-match is not evidence of absence. The detail must list the landing IP, the region's instance count and the account's known Anti-DDoS IPs, and name the human follow-up (identify the IP's owner). The onboarding problem is not lost: C1 still judges against **this domain's own** `Cname`, which the account does supply. | n/a |
| `FAIL_SCHEDULER_NO_DDOS_LINE` | A scheduler is in the path but no line has `ValueType=1` **and** `Status=1` — Anti-DDoS is configured on paper only. | FAIL |
| `NOT_DETECTED` | No resolution at all, or `dig` unavailable. Do not infer "direct to origin" from an empty answer. | coverage gap |

**C3 runs even when C1 is `NOT_APPLICABLE_*`.** In C1 branches 1–3 there is no Anti-DDoS CNAME to expect, but
the chain still shows what the traffic actually traverses, and that is exactly what the customer needs in
order to decide whether to finish the onboarding. Report the observed chain descriptively and say plainly that
Anti-DDoS is (or is not) in the path.

**Hand-off**: when C3 finds `FAIL_DIRECT_TO_ORIGIN`, or any bypass, the follow-up question "is the origin
itself locked down?" belongs to `alibabacloud-ddos-origin-exposure-detector`. Recommend it; do not re-implement
origin probing here.

---

## Traffic scheduler — special handling

This is the case that produces the most false findings, because it changes what "correct" looks like for C1
and C3.

**API facts** (`ddoscoo` `DescribeSchedulerRules`, version 2020-01-01)
- `PageSize` is **required**; there is no `RegionId` request parameter, but the CLI still needs `--region`
  for endpoint routing.
- Response: `TotalCount`, `SchedulerRules[]` = `RuleName`, `RuleType`, **`Cname`** (the scheduler CNAME the
  customer points their domain at, e.g. `4eru5229a843****.aliyunddos0001.com`), `Rules[]`, optional
  `Param` (`ParamType: "GA"`, `ParamData.CloudInstanceId`).
- `Rules[]` = `Type` (`A` | `CNAME`), `Value`, `ValueType`, `Priority`, `Status`, `RestoreDelay`, `Line`,
  `RegionId` (only when `RuleType=2`).
- **There is no `Domain` field.** Scheduler rules are domain-agnostic; the customer CNAMEs one or more
  domains to the rule's `Cname`.

**Enums**

| `RuleType` | Meaning | Anti-DDoS role in peacetime |
|-----------|---------|------------------------------|
| 2 | tiered protection | switch-in only → `INFO_SCHEDULER_ON_DEMAND` |
| 3 | overseas acceleration | switch-in only → `INFO_SCHEDULER_ON_DEMAND` |
| 5 | CDN interaction | CDN is the front layer by design |
| 6 | cloud-product interaction | the cloud product fronts; Anti-DDoS on demand |
| 8 | secure acceleration | switch-in only → `INFO_SCHEDULER_ON_DEMAND` |

| `ValueType` | Meaning | | `Status` | Meaning |
|------------|---------|-|---------|---------|
| 1 | Anti-DDoS IP | | 0 | inactive |
| 2 | cloud resource | | 1 | active |
| 3 | acceleration line | | | |
| 5 | CDN domain | | | |
| 6 | cloud product | | | |
| 8 | secure acceleration | | | |

**Binding a domain to a scheduler rule**: only by observed DNS — the domain's CNAME chain contains that
rule's `Cname`. Never assume a rule applies to a domain because both exist in the same account/region. If the
account has scheduler rules but a given domain resolves to none of their CNAMEs, the outcome depends on the
C1 precondition branch: branch 4 (own rule with a `Cname`) → `FAIL_CNAME_MISMATCH`; no rule at all →
branch 1 `NOT_APPLICABLE_NO_WEB_RULE`.

**What changes when `scheduler_in_use=true`**
- **C1**: the expected first hop becomes the scheduler CNAME — but only for domains that reach branch 4 (own
  layer-7 rule with a generated `Cname`); for those, `PASS_CONSISTENT_VIA_SCHEDULER` is a pass, and reporting
  `FAIL_CNAME_MISMATCH` because the value differs from `DescribeWebRules[].Cname` is the single most common
  false positive in this skill. A domain with **no** layer-7 rule whose DNS already points at a scheduler
  CNAME is branch 2, `NOT_APPLICABLE_SCHEDULER_ONLY` — not a pass. Scheduler rules carry no layer-7
  forwarding, so the prompt must ask whether the domain also needs a forwarding rule.
- **C3**: judge against `RuleType`. For 2/3/8 the Anti-DDoS line being inactive in peacetime is expected →
  `INFO_SCHEDULER_ON_DEMAND`, not FAIL. Still **require** at least one line with `ValueType=1` and `Status=1`
  to exist in the rule; if none exists, Anti-DDoS can never be switched in → `FAIL_SCHEDULER_NO_DDOS_LINE`.
- **C4**: with `RuleType=3` (overseas acceleration) or 8 (secure acceleration), overseas traffic is *supposed* to take the
  acceleration line. Overseas latency/health is then a property of that line, not of Anti-DDoS — say so
  instead of blaming Anti-DDoS. And if the acceleration line is not effective, overseas users fall back to
  the Anti-DDoS or origin path, which shows up as overseas degradation.
- **Report wording**: always name the matched rule (`RuleName` + `RuleType` label) and quote the effective
  lines, so the customer can see which line their traffic actually took.

---

## C4 — Access health, mainland China vs overseas

**Probe the domain**, over the scheme/port actually configured in `ProxyTypes` — never the origin IP.

**Documented `ProbeLog` fields to use** (`Data` is a JSON string; parse it twice):
`HTTPResponseCode`, `TotalTime`, `HTTPDNSTime`, `SSLConnectTime`, `tcpConnectTime`, `HTTPConnectTime`,
`errorCode` (**integer**; there is **no documented `errorMessage` field**), `ips`, `isp` / `ispCN` / `ispEN`,
`city` / `cityCN` / `cityEN`, `countryCN` / `countryEN`, `provinceCN` / `provinceEN`, `localDns`,
`suourceIp` (official spelling, typo included), `redirectCount`, `redirectTime`, `timestamp`, `taskId`.

**Success rule (MUST)**: a point succeeded iff `HTTPResponseCode` ∈ 2xx/3xx **and** `errorCode` is
empty/0. Never judge success by `TotalTime >= 0` (failed points still carry the exhausted timeout, e.g.
`5000.5`) and never by a `status` field. Classify failure causes by `errorCode` + `HTTPResponseCode`; do not
invent an error message the API never returned.

**Per-group verdicts** (compute mainland and overseas separately)

| Verdict | Condition |
|---------|-----------|
| `HEALTHY` | every point in the group succeeded |
| `WARN_SLOW` | every point succeeded but some `TotalTime` > `SlowThresholdMs` (default 2000ms; advisory) |
| `PARTIAL` | some points failed, some succeeded — list the failing ones with country/province/city/ISP + code + errorCode |
| `UNAVAILABLE` | every point failed |
| `NOT_DETECTED` | no point ran for this group: no overseas probe point available (`Country.en != "China"` with `IPV4ProbeCount > 0` not found), `OverseasCount=0`, task creation failed, or log fetch failed |

**Both groups are mandatory** — C4's purpose is *global* access health, so a run with only one half answers a
different question. Default when the user did not specify: **3 domestic + 3 overseas**. If either group is empty,
that half is `NOT_DETECTED` and the mainland-vs-overseas comparison is void; say so, and never let the healthy
half imply the other one is fine.

**Overseas vantage points must be discovered at runtime** by filtering `DescribeSiteMonitorISPCityList`
(`--ipv4 true --view-all true`) on the `Country` field. **The response uses flat dotted keys** (`Country.en`,
`Country.zh_CN`, `CityName.zh_CN`, `IspName.en`, `Region.en`) and a bare `Country` holding the numeric country
**code** (e.g. `629`). Reading the bare key as a nested object yields the code, so every point silently
classifies as overseas and the domestic group comes back empty — assert the domestic group is really China
before creating any paid task. Official docs publish no example overseas city/ISP
codes, so any hardcoded code would be a guess. If none is found → `NOT_DETECTED` for the overseas half
(error type **E**), and the overall verdict must carry the coverage qualifier.

**Cross-region divergence — the actual diagnostic payload.** Always report the pair, never just the halves:

| Mainland | Overseas | Likely causes to investigate (in order) |
|----------|----------|------------------------------------------|
| ok | fail | Incomplete certificate chain served to overseas clients (they validate strictly) — **outside C2's scope**, so investigate it manually rather than expecting a C2 verdict; scheduler overseas-acceleration line not effective; instance region mismatch (international-edition instance in `ap-southeast-1` but DNS points at mainland Anti-DDoS); overseas back-to-origin timeout |
| fail | ok | ICP filing not completed → mainland interception page; mainland-line DNS anomaly (correlate with C1 `WARN_POINT_INCONSISTENT`); business targets mainland users but runs on an international-edition instance |
| fail (5xx) | fail (5xx) | Back-to-origin failure: origin ACL not allowing Anti-DDoS back-to-origin ranges, wrong origin port/protocol, or origin down. Remediation is to allow the Anti-DDoS back-to-origin ranges on the origin; the report's Recommended Actions section carries the help-doc link |
| fail (conn/timeout) | fail (conn/timeout) | Site down, forwarding rule not effective, or DNS globally broken (correlate with C1) |
| `PARTIAL` | `PARTIAL` | Regional ISP issues or probe-point flakiness — re-probe just the failing points before concluding |
| ok | `NOT_DETECTED` | Say plainly that overseas health is unknown. **Never** write "overseas normal". |

**Latency sub-signals** (advisory, include in the evidence table): `HTTPDNSTime` > 500ms → resolution is slow
(often a long CNAME chain or an authoritative-server geography problem); high `SSLConnectTime` with normal
`tcpConnectTime` → handshake cost, e.g. a large/incomplete chain; high `TotalTime` with normal connect times →
origin or back-to-origin slowness.

**Local fallback**: with `ProbeMode=local`, C4 is one `curl` from one egress. Report it as
`LOCAL_SINGLE_EGRESS` and set the mainland-vs-overseas comparison to `NOT_DETECTED`.

---

## Coverage

Per check, `coverage = effectively-probed items / in-scope items`, one decimal place.

- In-scope items: **C1 = only the branch-4 domains** (a layer-7 rule exists *and* `Cname` is non-empty).
  Branch 1–3 domains are not C1-in-scope — they have nothing to compare — so putting them in the denominator
  would understate real coverage and hide the config prerequisite. Report them separately as a branch
  distribution, e.g. `C1 applicable 12 / 40 (branches: 1->3, 2->1, 3->24, 4->12)`.
  C3 = every layer-7 domain **minus** the `NOT_APPLICABLE_NO_IP_BASIS` and `NOT_APPLICABLE_NO_CONFIG_BASELINE`
  ones (wildcards expanded per the user's Step 2 choice, or excluded and listed);
  **C2 = only the domains that have a certificate bound** (`CertName` or `UserCertName` non-empty) — domains
  with nothing bound (`NOT_APPLICABLE_NO_CERT_BOUND`) and domains whose expiry this account cannot supply
  (`NOT_APPLICABLE_NO_CAS_DATA`) both stay out of the denominator, exactly like C1's branches 1–3; C4 = domains × {mainland, overseas} — a missing overseas point halves that domain's C4 coverage.
- Anything unprobed for any reason is a coverage gap and goes into the Not-Detected List with its reason.
- Any check below 100% forces the qualified overall wording (`..., with N items not detected`).
- Verify the arithmetic before writing it down. `6/11` is `54.5%`, not `100%`.

## Forbidden conclusions

- Reporting `PASS` / "healthy" / "not exposed" for anything that was never probed.
- Producing a C3 verdict for a target the Step 1.5 gate could not resolve in this account, or any C1 verdict
  beyond the precondition branch (`NOT_APPLICABLE_NO_WEB_RULE` / `NOT_APPLICABLE_SCHEDULER_ONLY`) — with no
  config baseline there is nothing to compare against, so any such verdict is invented.
- Emitting any `FAIL_*` for C1 when the baseline is missing: no rule (branch 1), scheduler-only DNS
  (branch 2), or an empty `Cname` because no Anti-DDoS IP is associated (branch 3). "Not finished
  configuring" and "configured wrong" have different remediations and different owners.
- Omitting the customer-facing prompt that belongs to a `NOT_APPLICABLE_*` C1 verdict. The label alone tells
  the customer nothing to do.
- Skipping C2 / C3 / C4 because C1 came back `NOT_APPLICABLE_*`.
- Reporting `FAIL_DIRECT_TO_ORIGIN` when the landing IPs were never proven to be this domain's origins, and
  reporting any `FAIL_*` at all when the landing IP matches nothing this account knows — that is
  `NOT_APPLICABLE_NO_IP_BASIS`.
- Calling another rule's CNAME "this domain's CNAME". `classify_hop` answers *is this an Anti-DDoS CNAME of
  this account*; it does not answer *whose*. The detail must not upgrade one into the other.
- Recording `NOT_DETECTED` where the account simply has no basis (`NOT_APPLICABLE_*`), or `NOT_APPLICABLE_*`
  where the basis exists but the probe failed (`NOT_DETECTED`). They have different fixes and different owners.
- Concluding "not in this account" after searching only one region, or by exact string match only. Wildcard
  coverage (`*.parent` covering `www.parent`) and scheduler-CNAME onboarding are both legitimate membership
  paths; missing them produces a false refusal.
- Treating an observed CNAME chain as the "expected" one just because no config exists for the domain.
- Averaging away per-point disagreement; a majority PASS with a minority origin-landing is still a finding.
- Substituting a configured value (`Cname`, `CertName`, origin IP) for an observed one.
- Treating `CertExpireTime` from `DescribeWebRules` as an expiry date.
- Judging anything beyond the bound certificate's expiry under C2: served-certificate validity, CN/SAN hostname
  coverage, chain completeness, and https/certificate configuration consistency are all out of scope. Answering
  them here re-widens a scope the customer deliberately narrowed.
- Reporting C2 as `PASS` / "certificate healthy" when `cas` returned no data or no `EndDate`. That is
  `NOT_DETECTED`, and it is the most likely C2 outcome whenever the `yundun-cert` read permission is missing.
- Inventing an expiry date, or borrowing another certificate's date, when the bound name matched no `cas` record.
- Judging probe success by `TotalTime >= 0` or by a `status` field.
- Deciding success/failure from an `errorMessage` string — that field is not documented for `ProbeLog`.
- Hardcoding overseas city/ISP codes.
- Concluding `FAIL_CNAME_MISMATCH` for a domain that correctly points at a scheduler CNAME.
- Concluding `FAIL_NOT_FIRST_LAYER` for `RuleType` 2/3/8 schedulers without also stating it is by design.
- Asserting "Anti-DDoS is behind the CDN / WAF / GA" when the CNAME chain merely terminated at that front
  layer. Its back-to-origin configuration is not in public DNS, so that claim is unproven — report
  "not the first layer, and whether Anti-DDoS sits behind it is undeterminable from DNS".
- Justifying the first-hop-only C1 comparison with "Anti-DDoS CNAMEs sit behind GSLB" without having measured
  per-resolver differences. The defensible reason is that the config APIs cannot enumerate the IP set behind
  an Anti-DDoS CNAME.
- Copying a "reserved ports 80/443" style region-specific assumption into the judgment — outside mainland
  China those ports are legal, and assuming otherwise causes under-detection.
