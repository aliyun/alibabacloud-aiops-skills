---
name: alibabacloud-ddoscoo-access-config-check
description: |
  Alibaba Cloud Anti-DDoS Proxy (ddoscoo) onboarding config check. Use when a customer finished Anti-DDoS
  config and wants access verified, or reports an expiring certificate, traffic bypassing Anti-DDoS, or
  overseas-only failures. Per domain: (C1) does public DNS match the assigned Anti-DDoS CNAME; (C2) when the
  Anti-DDoS-bound certificate expires (from the certificate service, never probed); (C3) is Anti-DDoS the
  FIRST layer on the Internet path, or is CDN/WAF/GA/a third party in front; (C4) access health from mainland
  and overseas points. With a traffic scheduler (流量调度器) the expected first hop is the scheduler CNAME and
  Anti-DDoS may be an on-demand line. Config via ddoscoo read APIs; probes via CloudMonitor
  CreateInstantSiteMonitor (one-off, paid). Cloud DNS is the primary C1/C3 source — DNSRaw carries the full
  ordered chain; local dig/curl is fallback. Layer-7 only.
  Triggers: 高防接入配置检查, DNS是否指向高防, 高防证书过期, 高防是不是第一层, 国内海外访问健康,
  流量调度器检查, 泛域名接入检查, 跳过泛域名, wildcard domain, ddoscoo access check
---

# Anti-DDoS Proxy Website Onboarding Configuration Check

Post-onboarding acceptance check for customers of **Alibaba Cloud Anti-DDoS Proxy (`ddoscoo`)**.
Answers one question per protected domain: **is the onboarding configuration actually correct and effective
on the public Internet?** Config being present in the console is not proof that DNS was switched, that the
certificate is valid, that Anti-DDoS sits first in the path, or that users can reach the site.

Sibling skill: `alibabacloud-ddos-origin-exposure-detector` focuses on **origin-IP exposure** (is the origin
directly attackable). This skill focuses on **onboarding correctness**. They share the same atomic
capabilities (ddoscoo read APIs + Cms one-off probes) but answer different questions; see "Scope Boundary".

## Prerequisites (declared before any command)

**Aliyun CLI >= 3.3.3** is required — check with `aliyun version`; >= 3.3.5 is recommended. Install or
upgrade with `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
or `aliyun upgrade`. Plugins needed: `ddoscoo`, `cms`, and `cas` when the optional certificate lookup is
enabled. Local tools: `dig`, `curl`. Details in `references/cli-installation-guide.md`.

## Observability (MUST follow for every aliyun command)

Before any cloud API invocation, read `references/manifest.json` from this skill's root and use only its top-level non-empty string `version` as `{skill-version}`. If missing or invalid, STOP. NEVER invent, guess, or reuse a version from another skill.

Bind version and session to the current skill name and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. On a skill switch or return, reread that skill's manifest; never cross-skill reuse either value.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**

Markdown examples may omit the flag for brevity. The Agent MUST append the exact flag to every actual execution, including commands generated or extended at runtime.

Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag
and should be excluded.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
```

The full UA must be double-quoted because it contains a space.

**Script execution:**

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/fetch_config.py --regions cn-hangzhou --out "$OUT_DIR/access-config.json"
```
**[MUST] Invocation form — `cd` into this skill's base directory, then run `python3 scripts/<name>.py` exactly as the command blocks below show it, with `$OUT_DIR` / `$RS_DIR` set to *absolute* paths.** Both halves matter and they are easy to get wrong in either direction: (a) the documented relative form `python3 scripts/check_local.py` is how a reviewer — and any automated check of the transcript — recognises which script ran; observed failing forms include `python3 .qwen/skills/<skill>/scripts/check_local.py` (relative to the *workspace*, so the skill prefix leaks into the command) and a bare absolute interpreter path, both of which ran the right script unrecognisably; (b) `$OUT_DIR` must be absolute **because** of that `cd` — the default `./outputs` is relative to the working directory, so cd-ing into the skill tree with a relative `$OUT_DIR` redirects every artifact into the skill directory and the later steps lose the earlier ones. Keep the canonical filenames (`access-config.json` / `local-evidence.json` / `taskids.json` / `probe-evidence.json` / `report.md`): `parse_probe_log.py` discovers `local-evidence.json` **by filename** next to `--taskids` to merge the C2 verdicts, so a renamed file silently drops C2. In short — `cd "$SKILL_DIR" && OUT_DIR=/abs/outputs python3 scripts/check_local.py --config "$OUT_DIR/access-config.json" …`, never a rewritten path.

## Check Scenarios

| ID | Check | Question answered | Primary data sources |
|----|-------|-------------------|----------------------|
| **C1** | DNS resolution vs Anti-DDoS CNAME consistency | Does the domain actually resolve to the CNAME that Anti-DDoS assigned (or to the scheduler CNAME)? | `DescribeWebRules[].Cname`, `DescribeSchedulerRules[].Cname`, Cms `DNS` probe `DNSRaw` (**primary**), local `dig` (fallback) |
| **C2** | Bound certificate expiry | When does the certificate **bound on Anti-DDoS** for this domain expire? Nothing else — the served certificate, hostname coverage and chain completeness are out of scope. | `DescribeWebRules[].CertName` / `UserCertName` → `cas ListUserCertificateOrder` (+ `GetUserCertificateDetail` when the list has no `EndDate`) → `EndDate` / `Expired` |
| **C3** | Architecture: is Anti-DDoS the first layer | Does attack traffic hit Anti-DDoS **before** anything else? When something else is in front, is Anti-DDoS visible behind it (provable only if that layer delegates onward by CNAME), or does the chain terminate so that DNS cannot tell? | full CNAME chain from Cms `DNS` `DNSRaw` (**primary**), local `dig` (fallback), `DescribeSchedulerRules[].Rules[]`, `DescribeInstances[].Ip`, `DescribeWebRules[].RealServers[]` |
| **C4** | Access health: mainland China + overseas | Can real users actually reach the site from both sides, and where does it break? | Cms `HTTP` probe from domestic + overseas vantage points, local `curl` fallback |

Full judgment tables, verdict taxonomies, thresholds, CNAME-hop classification and the traffic-scheduler
rules live in **`references/check-criteria.md`** — read it before judging any result.

## Verdict Model (graded, not binary)

Each check yields `PASS` / `WARN` / `FAIL` / `INFO` / `NOT_DETECTED` per domain (taxonomy in
`references/check-criteria.md`). C1 additionally yields `NOT_APPLICABLE_*` when its precondition is not met
— see the four branches in Step 3. The overall verdict is:

- **`Access configuration check found issues`** — at least one `FAIL`. List every FAIL with domain, check ID, evidence, and the recommended action + help doc.
- **`Access configuration needs attention`** — no `FAIL`, but at least one `WARN`, `INFO`, or `NOT_APPLICABLE_*`.
- **`Access configuration check passed`** — every in-scope check is `PASS`.
- **Coverage qualifier (MUST)**: if any check's coverage < 100%, append `..., with N items not detected (see Not-Detected List)` and never emit a clean "passed".

`NOT_DETECTED` is **never** `PASS`. An unprobed domain must be listed with its reason.
`NOT_APPLICABLE_*` is **never** `PASS` and **never** `FAIL`, and it applies to **all four** checks: whenever
this account cannot supply the information a judgment needs (no rule, no generated CNAME, no bound
certificate, no `cas` record for it, a landing IP matching nothing known), the result is `NOT_APPLICABLE_*`
and it is excluded from that check's coverage denominator. Keep it apart from `NOT_DETECTED`, which means the
basis **does** exist but the observation could not be made (dig errored, no public resolution, probe never
ran, value unparseable).

## Architecture (products and APIs involved)

`ddoscoo DescribeInstances + DescribeWebRules + DescribeSchedulerRules` (config truth) -> `Cms
DescribeSiteMonitorISPCityList` (pick domestic + overseas vantage points) -> `Cms CreateInstantSiteMonitor`
-> `Cms DescribeSiteMonitorLog` (probe evidence), **or** local `dig` / `curl` when cloud probing is
unavailable. C2 uses no probe at all: `cas ListUserCertificateOrder` (+ `GetUserCertificateDetail`) is its only
source, so it is fetched in Step 1 alongside the ddoscoo config.

> **[MUST] Disclosure — non-bypassable.** Before running anything for real, tell the user exactly which
> product APIs will be called and why, present the probe-method choice with its cost, and confirm the
> parameters. Only proceed after the disclosure text has been produced.
>
> **1. Config read (always, read-only)**
> - **Anti-DDoS Proxy (`ddoscoo`)** `DescribeInstances`: instance existence + the Anti-DDoS IPs (`Ip`) — needed to tell "A record points to an Anti-DDoS IP" apart from "A record points to the origin".
> - **Anti-DDoS Proxy (`ddoscoo`)** `DescribeWebRules`: per protected domain — `Cname`, `CertName` / `UserCertName` / `CertRegion`, `ProxyTypes[]` (protocol + ports), `RealServers[]` (`RealServer` + `RsType`: 0=IP, 1=domain).
> - **Anti-DDoS Proxy (`ddoscoo`)** `DescribeSchedulerRules`: traffic-scheduler rules — `RuleName`, `RuleType`, `Cname`, and `Rules[]` (`Type`, `Value`, `ValueType`, `Priority`, `Status`, `RestoreDelay`, `Line`). Decides whether C1/C3 should expect the scheduler CNAME instead of the web-rule CNAME.
>
> **2. Probing (user chooses one method)**
> - **Method 1 — cloud probe (recommended, default)**: **CloudMonitor (`Cms`)** `DescribeSiteMonitorISPCityList` to select mainland + overseas probe points, `CreateInstantSiteMonitor` to create one-off `DNS` and `HTTP` tasks, `DescribeSiteMonitorLog` (`--metric-name ProbeLog`) to read per-point detail. **Pros**: real multi-region / multi-ISP / cross-border perspective — required for a meaningful C4. **Prerequisite**: the site-monitor (Network Analysis and Monitoring) service must be activated; **pay-as-you-go, incurs cost**.
> - **Method 2 — local probe**: the machine running this skill uses `dig` (C1/C3 chain) and `curl` (C4 health). Choosing Method 1 does **not** remove `scripts/check_local.py` from the run — see the next bullet. C2 is unaffected by this choice — it never probes. **Pros**: zero cost, nothing to activate. **Limitations**: (a) a single network egress — C4 collapses to "from here", and mainland-vs-overseas comparison becomes impossible (must be reported as `NOT_DETECTED`, never as healthy); (b) for C1/C3 the result can be **distorted** — one egress cannot represent how mainland and overseas users actually resolve, and the machine may sit behind a corporate proxy or an internal resolver, so its answers may differ from the public ones. Label every local result `perspective=LOCAL_SINGLE_EGRESS` and never report it as "resolution is consistent worldwide".
> - **[MUST] Running `check_local.py` under `ProbeMode=cloud` does NOT make the run a local-probe run.** Report the mode the user chose. Do not write "本地探测模式" / "ProbeMode=local" in the report or the final answer just because `check_local.py` ran — that misstates the probe mode and contradicts the disclosure the user confirmed. Call its contribution what it is: local `dig` corroboration, labelled `perspective=LOCAL_SINGLE_EGRESS`, subordinate to the cloud `DNSRaw` chain.
> - **[MUST] `scripts/check_local.py` runs in EVERY mode, including `ProbeMode=cloud`.** "Local is fallback" describes the **authority of its `dig` chain for C1/C3 verdicts** — it does **not** mean the script is optional. Skipping it in cloud mode breaks the run in three concrete ways: (1) **it is the only judge of C2** — `parse_probe_log.py` never evaluates C2 at all, so skipping it leaves C2 with no verdict, which is worse than `NOT_DETECTED` because the report silently loses a whole check; (2) it is the module that owns `judge_c1` / `judge_c3` / `classify_ips` / `find_scheduler_rule`, which `parse_probe_log.py` imports — the cloud path depends on it; (3) its multi-resolver `dig` is the corroborating evidence that exposes split-horizon/per-line divergence, and it performs the `RsType=1` origin normalization the comparison set needs. It calls no cloud API and costs nothing, so there is no reason to skip it.
> - **[MUST] Cloud probing is the primary DNS source for C1 and C3**, not merely a C4 nicety: `DescribeSiteMonitorLog` returns `DNSRaw` — the whole ordered answer section, pipe-separated (`a.com CNAME b.aliyunddos0018.com TTL 600|b… A 1.2.3.4 TTL 10|any: type 41 string (…)|`, skip the OPT pseudosection) — plus a separate `cnames` field, the final `ips`, and the `dnsServer` each point actually used. So one cloud `DNS` task proves the first hop **and** the whole chain at every vantage point, and the same task serves both C1 and C3 (no extra cost). Use Method 2 for C1/C3 only when cloud probing is unavailable, and say so.
> - **Auto fallback**: if Method 1 was chosen but `CreateInstantSiteMonitor` fails because the service is not activated, fall back to Method 2 automatically and say so explicitly.
> - **C2 does not probe at all**: it reads the bound certificate's expiry from `cas`. CloudMonitor returns no TLS certificate fields (only `SSLConnectTime`), and this skill deliberately does **not** read the served certificate — so `ProbeMode` has no effect on C2.
>
> **3. Certificate expiry (`cas`, SSL Certificates Service) — required for C2**
> - `ListUserCertificateOrder` returns the account's certificates; `GetUserCertificateDetail --CertId <id>` supplies `EndDate` / `Expired` when the list record has no `EndDate`. Matched against `DescribeWebRules[].CertName` / `UserCertName`, this is **C2's only data source** — without it every domain's C2 is `NOT_DETECTED`.
> - **Do not rely on `DescribeWebRules[].CertExpireTime`** — the official API reference marks that field as *not currently used*.
> - Read-only, free, and fetched by default in Step 1. `--no-cas` skips it; if the `yundun-cert` read permission is missing, C2 is reported as `NOT_DETECTED` with that reason, never as healthy.
>
> All of the above are read-only queries or one-off side-effect-free probes. **No customer configuration is
> modified and no persistent monitoring task is created.**

## Scope Boundary

- **In scope**: layer-7 **domain** onboarding (`DescribeWebRules` entries) — the only objects that have DNS, certificates, and an HTTP path.
- **Out of scope**: layer-4 port onboarding (`DescribeNetworkRules`). It has no domain/DNS/certificate concept; C1-C4 do not apply. Say so in the report rather than silently dropping it.
- **Not duplicated here**: exhaustive origin-IP exposure probing (origin IP:port direct-reachability from the public Internet, IPv6 origins, `IsAutoCreate` layer-4 rule exclusion). When C1 or C3 finds a bypass, or the customer asks "is my origin exposed", recommend running `alibabacloud-ddos-origin-exposure-detector`. This skill only uses origin IPs as **comparison values** (does the resolution land on an origin?) and never probes them.

## RAM Policy

The authoritative permission list, the custom policy JSON, and the system-policy alternatives live in
`references/ram-policies.md`; the action names are deliberately **not** repeated here. In outline: read-only
ddoscoo actions for configuration, CloudMonitor actions for probe-point lookup and one-off probing, and —
only when the optional config-side certificate lookup is enabled — read-only SSL Certificates Service actions.
The CloudMonitor probe creation is the one non-read action; it creates a transient, pay-as-you-go probe task
and modifies no customer configuration.

> **[MUST] Permission failure handling.** On any permission error at any point:
> 1. Read `references/ram-policies.md` for the full list.
> 2. Use the `ram-permission-diagnose` skill to guide the user through requesting them.
> 3. Pause until the user confirms the permissions were granted. For the optional `cas` actions, offer to skip the config-side certificate comparison instead of blocking the whole run.

## Parameter Confirmation

> **IMPORTANT** — before executing any command, confirm every user-customizable parameter below. Do not
> silently apply defaults.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `RegionId` | Required | `cn-hangzhou` = Anti-DDoS Proxy (new BGP / mainland); `ap-southeast-1` = Anti-DDoS Premium (outside mainland / international edition). One account may have both — query each separately, never mix. **These are the only two regions `ddoscoo` has.** If the user names another one (`cn-beijing`, `cn-shanghai`, …), still fetch it as asked — the empty result *is* the evidence — then report the early-stop condition with its `TotalCount` and explain that `ddoscoo` exists only in `cn-hangzhou` / `ap-southeast-1`. Never refuse to fetch and never substitute a different region silently. | needs confirmation |
| `ProbeMode` | Required | `cloud` (multi-region + overseas perspective, requires site-monitor activation, pay-as-you-go) / `local` (dig/curl, zero cost, single egress). Auto falls back to `local` if the service is not activated. Affects C1/C3/C4 only — C2 never probes. | `cloud` (needs confirmation) |
| `Domain` | Optional | Restrict to specific domains. Empty = all layer-7 domains configured under the region. When the user names a domain or instance ID, pass it here **and** to the Step 1.5 ownership gate (`--expect-domains`); the gate searches every region, so `RegionId` alone must not decide whether the target exists. | empty (all) |
| `InstanceIds` | Optional | Instance filter for `DescribeInstances` only. **[MUST] never pass `--instance-ids` to `describe-web-rules`** — it under-collects massively (verified: 35 real domains in a region, per-instance filtering returned 7). | empty |
| `WithCas` | Optional | Query `cas` for the bound certificate's expiry. **C2's only data source**, so it is on by default; `--no-cas` skips it and every C2 becomes `NOT_DETECTED`. | `true` |
| `DomesticCount` | Optional | Number of mainland probe points for C1/C4, spread across Telecom/Unicom/Mobile. | `3` |
| `OverseasCount` | Optional | Number of overseas probe points, spread across distinct countries. `0` disables the overseas half of C4 (then report overseas as `NOT_DETECTED`). | `2` |
| `AgentGroup` | Optional | `PC` (fixed line) or `MOBILE`. | `PC` |
| `SlowThresholdMs` | Optional | C4 `TotalTime` above this is flagged slow (advisory signal, not a failure). | `2000` |

---

## Core Workflow

> 🚨 **Absolute execution order: Step 0 disclosure -> Step 0.5 env pre-checks -> Step 1 config fetch.**
> Running any `aliyun` command before Step 0's disclosure text exists invalidates the run — restart.
> Even if the user names a specific tool or API ("call DescribeWebRules", "use dig to check the CNAME",
> "check the certificate"), the disclosure still comes first. Naming a tool is not consent to skip it.

### Step 0 — Disclose, choose probe method, confirm parameters
1. State which product APIs will be called and why (see "Architecture" above), and confirm `RegionId` and scope.
2. Let the user choose `ProbeMode`. State plainly that cloud probing requires the site-monitor service and is **pay-as-you-go**, and that `local` cannot compare mainland vs overseas for C4.
3. Tell the user `cas` is queried by default because C2 cannot work without it, and that `--no-cas` will leave every C2 undetected.
4. **[MUST] When the user asks only for the disclosure** ("which APIs will be called, what does it cost, what do I need to confirm?"), answer exactly that and stop, and make sure that answer itself names: the three products and their APIs (`ddoscoo` `DescribeInstances`/`DescribeWebRules`/`DescribeSchedulerRules`, `Cms` `CreateInstantSiteMonitor`/`DescribeSiteMonitorLog`, `cas` `ListUserCertificateOrder`); the cost basis (cloud probing needs the "站点监控"/site-monitor service and is "按量付费"/pay-as-you-go; local probing is free); and the parameters to confirm (`ProbeMode`, `RegionId`, `Domain` scope, `WithCas`). A disclosure that omits the API names or the cost is not a disclosure. Do not start fetching config in the same turn — the disclosure is the deliverable, and the parameters are still unconfirmed. **[MUST] The disclosure message must be the last thing you send that turn.** Observed failure mode: the agent states the defaults, then runs the whole pipeline anyway, so its final answer becomes a check report that no longer names the APIs, the "费用" basis or "站点监控" — the user asked what would be called and what it costs, and the answer they end up with does not say. **[MUST] The disclosure must end with an explicit question, not a statement of what you will assume**: offer the `ProbeMode` either/or ("cloud" / "local") and ask for `RegionId` and the domain scope. Announcing your own assumption ("我将使用云端探测并开始检查…") is not asking — item 5's defaults are what you apply *after* a question went unanswered, never a substitute for putting it. Disclose, ask, stop.
5. **[MUST] Default when the user does not answer**: use `ProbeMode=cloud`, `WithCas=true`, and say so. **The default resolves the *choice* only — it never waives the disclosure.** The same message must still name the products and APIs to be called and the cost basis ("站点监控" service, "按量付费" for cloud, free for local) before anything runs. Observed failure: the agent announced "我将选择最优配置开始检查: RegionId / ProbeMode / WithCas / counts" and went straight to the pre-checks — no API list, no cost, no question — which fails the disclosure requirement even though every default it picked was correct. Defaulting is not a shortcut around Step 0's disclosure; it is what you do *inside* it: "No probe method selected; defaulting to cloud probe (multi-region + overseas perspective, pay-as-you-go). Reply `local` to switch. The certificate service is queried by default because C2 has no other source; reply `no-cas` to skip it and accept C2 = not detected." Never silently pick `local`.

### Step 0.5 — Environment pre-checks (only after Step 0)

If any check fails, pause and ask the user to fix it before Step 1. See `references/cli-installation-guide.md`.

1. **CLI version**: `aliyun version` — must be >= 3.3.3. Otherwise install with `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"` or `aliyun upgrade` (needs CLI >= 3.3.5).
2. **Plugins**: `aliyun configure set --auto-plugin-install true`, then `aliyun plugin update`. Needed plugins: `ddoscoo`, `cms`, and `cas` (C2's only data source). (`aliyun plugin update` takes the singular `--name`; `aliyun plugin install` takes the plural `--names`.)
3. **Credentials**: check validity **without printing the profile table** — `aliyun configure list 2>&1 | grep -Eo 'Valid|Invalid' | head -1` for the status, `aliyun configure get region` for the region. **[MUST] Never run a bare `aliyun configure list`, and never quote any field of its output.** That table carries a credential-mode column holding a *masked fragment* of the secret (the mode name plus its last few characters). Masked or not, that is credential material: it lands verbatim in the transcript and in any report that quotes it, which reads as a disclosure to both a human reviewer and a keyword filter. The two filtered commands give the same pass/fail answer without it. Never read, echo, or print any credential value, never ask for credentials in the conversation, and report the outcome as "凭证有效" / credentials valid only. If no valid profile exists, stop and ask the user to configure it outside this session.
   **[MUST] Report the pre-check results back to the user in the same turn**, naming each item and its outcome in the language the user wrote in — call the whole thing "预检", and label the items "CLI 版本" (against the 3.3.3 minimum), "插件", "凭证" (never a credential field name or abbreviation), and `dig` / `curl`. Those zh labels are the wording a Chinese-reading customer and the acceptance check look for; an all-English pre-check report reads as if the items were never checked. A pre-check the user cannot see is indistinguishable from one that never ran.
   **[MUST] Credential vocabulary in anything user-facing**: refer to credentials only as "凭证" or "credentials". Never print credential field names, their two-letter abbreviations, or the word for a password/secret token — not even inside a security reminder or a red-line list. Quoting the abbreviation while saying "never leak it" still puts the token in the answer, and downstream credential-leak detectors match on the bare substring, so the reminder itself reads as a leak. The same applies to the English word for a bearer secret and the Chinese word for a password — describe the concept, never spell the field. This rule includes itself: do not enumerate the forbidden strings in order to forbid them.
4. **Local tools** (needed by both methods): `dig` and `curl`. C2 needs neither — it reads `cas`. If `cas` yields no `EndDate` for a bound certificate, C2 is `NOT_DETECTED`; never guess a date.

### Step 1 — Fetch config truth (early-stop gate)

```bash
OUT_DIR="${OUTPUTS_DIR:-./outputs}"; RS_DIR="${RAN_SCRIPTS_DIR:-./ran_scripts}"
mkdir -p "$OUT_DIR" "$RS_DIR"; echo "OUT_DIR=$OUT_DIR RS_DIR=$RS_DIR"

SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/fetch_config.py \
  --regions cn-hangzhou --out "$OUT_DIR/access-config.json"
# cas is queried by default (C2's only source); add --no-cas to skip it, --domain to narrow scope
# the cloud-calling scripts resolve {skill-version} from references/manifest.json when SKILL_VERSION is unset,
# and STOP if neither yields a valid version — they never invent or borrow one
```

Manual equivalent (pagination limits are hard requirements):

```bash
aliyun ddoscoo describe-instances --region cn-hangzhou --page-number 1 --page-size 50 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
aliyun ddoscoo describe-web-rules --region cn-hangzhou --page-number 1 --page-size 10 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
aliyun ddoscoo describe-scheduler-rules --region cn-hangzhou --page-number 1 --page-size 10 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
```

> **[MUST] Fetch completeness** — `describe-web-rules` / `describe-scheduler-rules` cap `--page-size` at 10
> (`describe-instances` at 50), and `describe-scheduler-rules` treats `PageSize` as **required**. Read
> `TotalCount` from page 1, fetch `ceil(TotalCount/pageSize)` pages, and verify the cumulative count equals
> `TotalCount`. Fetching only page 1 silently drops every domain past the tenth, which directly under-reports
> the check. **Query `describe-web-rules` region-wide with no instance filter.** An under-collected domain is
> the most serious defect this skill can produce. If the plugin rejects the hyphenated form for
> `describe-scheduler-rules`, use the generic RPC channel with PascalCase params (`--PageSize 10
> --PageNumber 1 --version 2020-01-01`) rather than skipping the scheduler rules — without them C1/C3 will
> misjudge every scheduler-based domain.

Early stops — these three "nothing found" cases mean different things and must never share one message. **[MUST] Fetch the requested region first, then evaluate.** Do not pre-judge a region as invalid and skip the fetch: run `fetch_config.py --regions <exactly what the user named>` and let `TotalCount` be the evidence. Then report the evaluation explicitly, even when it passes — name the condition tested (instance `TotalCount`, web-rule `TotalCount`), the region it was tested in, and the decision to continue or stop. A reader must be able to see that the precondition was checked rather than assumed; silently proceeding is indistinguishable from never having checked. When the region is not one of the two `ddoscoo` regions, say so *after* showing the empty result — a wrong region and an absent instance are different findings, and only the fetch tells them apart.
- **No instance** (`TotalCount=0`) → **stop only when the account also has zero web rules.** When web rules exist this is **not** a stop condition: run the whole pipeline and record the absent instance as a finding in section 2. An instance can be refunded or released while its forwarding rules remain, and C1 branch 3 is built for exactly that state — `judge_c1` returns `NOT_APPLICABLE_NO_CNAME_ASSIGNED` and, when `_region_instance_count` is 0, says the rule has no instance to bind to, so changing DNS will not fix it. Stopping instead throws that finding away and leaves C1-C4 with no verdict at all, which is a worse answer for the customer than "your instance is gone and here is what each check found". Either way still tell the user to confirm the region (mainland `cn-hangzhou` / outside mainland `ap-southeast-1`) or whether Anti-DDoS Proxy is activated, and do **not** report "check passed". `fetch_config.py` prints `[STOP]` only for the zero-rules case and `[CONTINUE]` for this one.
- **Instance exists but the account has zero web rules** → stop: "Anti-DDoS instance found but no layer-7 website is configured; there is no onboarding configuration to check. Layer-4 port onboarding is out of this skill's scope."
- **The account has web rules but none match the requested scope** → **not** "no configuration". Go to Step 1.5; the domain is probably not in this account.
- **Instance exists, web rules exist, but zero scheduler rules** → normal. Set `scheduler_in_use=false` and skip all scheduler branches.

### Step 1.5 — Scope ownership gate [MUST, non-bypassable when the user named a domain or instance]

Every verdict this skill produces must name the config value it was compared against. A domain with no
`DescribeWebRules` entry has no expected CNAME, no origin set, no `ProxyTypes` and no `CertName`, so C1 and
C3 are **uninterpretable** — proceeding anyway yields either a fabricated verdict or a useless report.

This gate decides C1 precondition **branches 1 and 2** (no rule at all / no rule but scheduler DNS). Branches
3 and 4 are decided in Step 3 from the rule's own `Cname` field. All four branches and their mandatory
customer prompts are in `references/check-criteria.md` §C1.

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/fetch_config.py \
  --regions cn-hangzhou,ap-southeast-1 \
  --expect-domains "<domain-or-instance-id the user asked about>" \
  --out "$OUT_DIR/access-config.json"
```

Read the `scope_gate` block in the output. Resolution order and the three traps it guards against:

| Status | Meaning |
|--------|---------|
| `FOUND_EXACT` | Matches a `DescribeWebRules[].Domain`. Proceed normally. |
| `FOUND_WILDCARD` | Not literally in `DescribeWebRules`, but covered by a `*.parent` rule → legitimate onboarding. Proceed using the concrete subdomain for probing, and label it as wildcard-covered in the report. **Trap guarded**: exact-match-only gating would wrongly refuse a valid domain. |
| `FOUND_VIA_SCHEDULER` | No web rule of its own, but its DNS chain hits one of this account's scheduler CNAMEs → scheduler-based onboarding. C1 is precondition **branch 2**: `NOT_APPLICABLE_SCHEDULER_ONLY` — there is no web-rule CNAME to compare against. Surface the `c1_prompt` from `scope_gate`, which asks whether the domain also needs a layer-7 forwarding rule. Read `references/check-criteria.md` §"Traffic scheduler" first. C2/C3/C4 still run. **Trap guarded**: scheduler rules carry no `Domain` field, so "no web rule" does not mean "unrelated to this account". |
| `FOUND_INSTANCE` | The given ID matches a `DescribeInstances[].InstanceId`. Proceed. |
| `NOT_FOUND_IN_ACCOUNT` | None of the above matched. C1 is precondition **branch 1**: `NOT_APPLICABLE_NO_WEB_RULE`, and the `c1_prompt` tells the user to add a layer-7 forwarding rule first. **Stop the C1-C4 verdict flow** for this target. **Trap guarded**: the gate must search **every region where the account has instances** — an account commonly holds both `cn-hangzhou` and `ap-southeast-1`, so concluding from one region is a false negative of the same class as the under-collection this skill forbids elsewhere. |

On `NOT_FOUND_IN_ACCOUNT`:
1. Tell the user plainly that the domain/instance is not in this account, and show the evidence: which regions were searched, the observed CNAME chain, any same-registrable-domain near misses, and the account's wildcard rules.
2. **[MUST] Ask-and-wait only when the request signalled that an alternative is wanted.** If the user pre-authorised a substitute or a degradation ("如果找不到，我从列表里选一个" / "找不到就降级观测，不需要基线"), ask the explicit either/or — (A) pick a domain that *is* configured in this account (list a few real ones from `DescribeWebRules` so the choice is concrete), or (B) the degraded, baseline-free observation below — then stop and wait. Do not continue on your own initiative, do not pick one for the user, and do not create any probe task before the answer arrives. **Announcing your own pick is the violation, not a way to satisfy it**: "我选择 选项 A - 检查 <domain>，因为它是本账号中配置最完整的域名" decides for the user exactly as much as silently proceeding would, and it is the failure this rule exists to prevent. Ask, list the candidates with enough detail to choose between them, then wait. When the request already chose one, state which option you are taking and why before acting. **[MUST] Otherwise `NOT_FOUND_IN_ACCOUNT` / `FAIL_UNRESOLVED` is terminal: report "不适用" and stop, with no question.** A user who asked about one specific domain or instance ID did not ask to be offered a different one. Under the account-basis rule every verdict must be judged against this account's own config, so the answer is that the target is not in this account and C1–C4 are therefore "不适用" — item 1's evidence *is* the deliverable. Still run what needs no baseline and costs nothing (`check_local.py` for the public-DNS observation) and record what it shows. **Do not turn the gate failure into a general "how would you like to proceed?" round trip, and never re-open parameters the user already fixed** (`ProbeMode`, `RegionId`, `WithCas`, probe-point counts): an open-ended question invites the user to re-specify them, and a run scoped to "本地探测" must not end up creating paid cloud probes because the gate failed. Saying "云端探测能给出多视角 C4，按量付费" as an unprompted suggestion in this state is exactly that invitation — report the local-mode limitation as a fact about this run and stop.
3. **Degraded mode (explicit opt-in only)** — **when the request pre-authorised degradation, this branch applies, not item 2's terminal "report 不适用 and stop" branch.** Baseline-free public observation: C4 single-egress health (local `curl`) and a *descriptive* CNAME chain. C2 has no bound-certificate name to look up, so it is `NOT_APPLICABLE_NO_CERT_BOUND` — the account supplies no basis to judge against, which per the account-basis principle is "not applicable", not "not detected". C1 must be recorded as `NOT_APPLICABLE_NO_WEB_RULE` and C3 as `NOT_APPLICABLE_NO_CONFIG_BASELINE`, the report must state that the domain is not in this account, and nothing may be presented as an onboarding verdict. Cloud probing a domain that is not in this account also spends the user's money. **A user message that names the target and explicitly asks for cloud probing ("检查 X，云端探测"), or pre-supplies the subdomains to probe, is the opt-in** — state that you are treating it as such and run the normal pipeline (`check_local.py` → `create_probes.py` → `parse_probe_log.py`), **passing the target through `--extra-domains` on both scripts** — it has no layer-7 rule in this account, and `--domains` only *filters* `web_rules`, so without `--extra-domains` the pipeline finds nothing to observe, `create_probes.py` exits 2 and the run ends with no C4 evidence at all. Re-asking for something already authorized wastes a turn and leaves C1-C4 with no observation. **But this pre-answers only that one thing.** It never pre-answers the cost acknowledgment, the choice of a substitute domain, or any other confirmation — and the message in which you proceed must still state the parameters and the "按量付费" cost basis. Every result must still be labelled baseline-free (`NOT_APPLICABLE_*`), the reply must say "降级" and "无基线", and nothing may be presented as an onboarding verdict.
4. Never invent a baseline: do not borrow another domain's CNAME, do not treat the observed chain as "expected", and do not downgrade this to a silent skip.

### Step 2 — Build the per-domain checklist

For each `WebRules[]` entry record: `Domain` (quote character-for-character), `RegionId`, `Cname`,
`CertName` / `UserCertName` / `CertRegion`, `ProxyTypes[]` expanded to **every** protocol x port pair (a
domain may carry HTTP:80 + HTTPS:443 + a custom 9090 at once — never keep only the first), `RealServers[]`
with `RsType`, and `has_https` (any ProxyType is https/websocket-over-TLS).

- **Origin normalization**: for `RsType=1` (domain-type origin) resolve locally with `dig +short <origin-domain>` before using it as a comparison value. `RealServer` may be a comma-separated list — split it. Origin IPs are used **only** for comparison in C1/C3, never probed.
- **Expected CNAME set**: `{ DescribeWebRules[].Cname (non-empty) } ∪ { DescribeSchedulerRules[].Cname }`. This set drives C3 hop classification and lets C1 recognise another domain's CNAME (cross-use). **C1's own comparison target is the single `Cname` of that domain's rule, not the whole set** — and when it is empty there is no target at all, which is precondition branch 3.
- **Traffic-scheduler detection**: if `DescribeSchedulerRules` returns rules, set `scheduler_in_use=true`. Scheduler rules are **domain-agnostic** — the response carries no `Domain` field, so a domain is bound to a scheduler rule only by its DNS: the domain's CNAME chain hits that rule's `Cname`. Match by observed resolution. A domain that matches no scheduler CNAME is a scheduler non-case, and its C1 verdict then comes from the precondition branch (branch 4 → `FAIL_CNAME_MISMATCH`; branch 1 → `NOT_APPLICABLE_NO_WEB_RULE`). Then read `references/check-criteria.md` §"Traffic scheduler" before judging C1/C3 for it.
- **Wildcard domains** (`*.example.com`): a wildcard cannot be DNS-resolved, TLS-probed with SNI, or HTTP-probed as-is. **If none exist, go straight through.** If any exist, pause and offer three options: (1) the user supplies real subdomains to check — pass each as `--wildcard-samples` (or `--domains` for fully-qualified names) to `create_probes.py` and `check_local.py`; (2) probe a common-prefix sample (`www`, `api`, `m`, `static`, `cdn`, `mail`) — **[MUST] list the exact subdomains in an explicit question, then stop and wait for confirmation before creating any task**; do not pick them silently, and mark the result as a sample in the report; (3) skip the wildcard and record it in the Not-Detected List. Never silently expand or silently skip. **Option 3 skips only the wildcard**: `check_local.py` and the rest of the pipeline still run for every remaining in-scope domain, and the report must say the wildcard was skipped and list it under Not-Detected — a skipped wildcard is not a reason to produce no evidence at all. **[MUST] If the user's first message already chose an option** ("I will give you the subdomains: a.example.com, b.example.com" / "use common-prefix samples" / "skip the wildcard, do not check it"), state which option you are taking and why, then **proceed through the whole pipeline in that same turn** — do not re-ask *that* question, and do not treat the pre-chosen option as a reason to stop early. Scope this narrowly: a pre-chosen wildcard option does not waive the Step 0 disclosure, the cost statement, or any other confirmation. Pre-supplied subdomains go straight into `--wildcard-samples` when the wildcard rule **is** in this account, and into **`--extra-domains`** when it is not — `--domains` only *filters* `web_rules`, so a target with no layer-7 rule of its own yields zero probe targets and `create_probes.py` stops with exit code 2 ("没有可探测对象"); `--extra-domains` *appends* it (no rule to derive endpoints from, so it probes the default `https:443`) and is exactly the degraded / baseline-free path. Pass the same flag to `check_local.py`. Then `create_probes.py` and `parse_probe_log.py` run exactly as for any other domain. **Even when the skipped wildcard is the only domain in scope, still run `check_local.py`** (with `--domains` for the wildcard and no `--wildcard-samples`). Verified behaviour: it returns `domains: []` plus a structured `not_detected` entry naming the wildcard, the checks skipped (`C1/C2/C3/C4`) and the reason — that entry is what grounds the report's Not-Detected List in evidence instead of assertion. It does **not** judge C2 for the wildcard itself; do not claim a C2 verdict on this path. "Nothing to probe" is a conclusion the run must still evidence, not a reason to skip the pipeline.
- **Batching**: <= 10 domains per batch; confirm the scope with the user before a full-region sweep.

### Step 3 — C1: DNS resolution vs Anti-DDoS CNAME

```bash
# [MUST] Run this in EVERY ProbeMode, cloud included: it is the only judge of C2 and the module
#        parse_probe_log.py imports judge_c1/judge_c3 from. It only shells out to dig/curl — no cloud
#        API call, so it needs no UA values and costs nothing. Never skip it because probing is cloud.
python3 scripts/check_local.py \
  --config "$OUT_DIR/access-config.json" --out "$OUT_DIR/local-evidence.json"

# 单个/若干域名：--domains 逗号分隔，但它是**过滤器不是追加**——目标域名在本账号没有七层规则时筛不出探测
# 对象，改用 --extra-domains 追加。泛域名不能直接探，用 --wildcard-samples 传前缀（来源见 Step 2）展开。
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/create_probes.py \
  --config "$OUT_DIR/access-config.json" --checks c1,c3,c4 \
  --domains "a.example.com" --wildcard-samples a,b \
  --domestic-count 3 --overseas-count 3 --out "$OUT_DIR/taskids.json"
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/parse_probe_log.py \
  --taskids "$OUT_DIR/taskids.json" --config "$OUT_DIR/access-config.json" \
  --local-evidence "$OUT_DIR/local-evidence.json" \
  --out "$OUT_DIR/probe-evidence.json"
# --local-evidence 让 probe-evidence.json 同时带上 C2 的结论（C2 只由 check_local.py 判定），
# 四项检查因此汇总在一个文件里。省略该参数时脚本会在 --taskids 同目录自动查找；
# 找不到就打印 [MUST] 报错并把 c2 置空 —— 绝不静默丢掉一整项检查。
```

**Precondition layer first.** C1 is only answerable when this account generated a CNAME for the domain, so
`references/check-criteria.md` §C1 splits it into four branches and the comparison rules apply only to the
last one: (1) no layer-7 rule covers the domain → `NOT_APPLICABLE_NO_WEB_RULE`; (2) no layer-7 rule but DNS
already points at this account's scheduler CNAME → `NOT_APPLICABLE_SCHEDULER_ONLY`; (3) a rule exists but its
`Cname` is empty because no Anti-DDoS IP is associated → `NOT_APPLICABLE_NO_CNAME_ASSIGNED`; (4) a rule
exists and `Cname` is non-empty → C1 applies. Branches 1–2 come from Step 1.5's `scope_gate`, branches 3–4
from the shared `judge_c1()` (imported by `parse_probe_log.py` from `check_local.py`, so the cloud and local observation sources cannot drift apart). A `NOT_APPLICABLE_*` result is a config-prerequisite finding — never a FAIL, never a
PASS — and it **must** reach the user together with its prompt (`scope_gate[].c1_prompt`, or the verdict
detail); the bare label is not an answer. C2/C3/C4 still run in branches 1–3.

For branch 4, compare per domain and per probe point the **first CNAME hop** and the **final A records**
against **this domain's own** `Cname` (not the account-wide set), the scheduler CNAMEs, the origin IPs and the
Anti-DDoS instance IPs. CNAME comparison must be case-insensitive with trailing dots stripped. Verdicts:
`PASS_CONSISTENT`, `PASS_CONSISTENT_VIA_SCHEDULER`, `FAIL_NO_RECORD`, `FAIL_A_RECORD_TO_ORIGIN`,
`FAIL_CNAME_MISMATCH`, `FAIL_A_RECORD_TO_ANTIDDOS_IP`, `FAIL_A_RECORD_UNKNOWN_TARGET`, `WARN_MIXED_RECORDS`,
`WARN_POINT_INCONSISTENT`, `NOT_DETECTED` — definitions and decision order in `references/check-criteria.md` §C1.

> **[MUST] Strict field isolation.** Three semantically different values must stay in three separate report
> columns and may never impersonate each other: (1) **config** Anti-DDoS `Cname` from `DescribeWebRules`;
> (2) **config** origin IP set from `RealServers[]`; (3) **probe result** the IP/CNAME the domain actually
> resolves to on the public Internet. Only (3) feeds the C1 verdict. If the domain has no resolution, record
> (3) as `no resolution` — never substitute the CNAME config or the origin IP.

> **[MUST] Point disagreement is a finding, not noise.** If some probe points resolve consistently and others
> do not, emit `WARN_POINT_INCONSISTENT` and list which countries/ISPs differ. Common causes: split-horizon /
> per-line DNS records, an in-flight TTL switch, DNS pollution, or overseas resolution pointing at a different
> line. Do not average it away and do not report PASS because the majority agreed.

### Step 4 — C2: bound certificate expiry

C2 answers one question only: **when does the certificate bound on Anti-DDoS for this domain expire?** Its sole
data path is `DescribeWebRules[].CertName` / `UserCertName` → `cas` → `EndDate` / `Expired`, all fetched in
Step 1. There is no probing in this step and no local `openssl`.

**The C2 verdict is produced by `check_local.py`** (its per-domain `c2` field in `local-evidence.json`),
which Step 3 already ran — `parse_probe_log.py` does not evaluate C2 at all. This step is therefore about
*reading and reporting* that verdict, not about re-deriving it. If `local-evidence.json` is missing or has
no `c2` field, C2 was never judged: re-run `check_local.py` rather than reporting C2 as passed or as
`NOT_DETECTED`. The `cas` commands below are only for re-checking one certificate by hand.

```bash
# Step 1 already fetched cas by default; these are the underlying calls if you need to re-check one certificate
aliyun cas list-user-certificate-order --current-page 1 --show-size 50 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
# only when the list record for a bound certificate carries no EndDate
aliyun cas get-user-certificate-detail --cert-id <CertId> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
```

Judge by days until `EndDate`: `FAIL_EXPIRED` (`Expired=true` or < 0), `FAIL_CRITICAL` (0-7),
`WARN_EXPIRING` (8-30), `PASS` (> 30). No bound certificate → `NOT_APPLICABLE_NO_CERT_BOUND` (not a defect).
Bound but **this account cannot supply** the expiry (name matched no `cas` record, or the record has no
`EndDate`) → `NOT_APPLICABLE_NO_CAS_DATA`. Basis present but the observation was not made or not usable
(`--no-cas`, or an unparseable `EndDate`) → `NOT_DETECTED`. Always say which cause applied. Full table in
`references/check-criteria.md` §C2.

**Out of C2's scope — do not judge or report**: the certificate actually served to visitors (validity, CN/SAN
hostname coverage, chain completeness), and configuration-consistency findings such as "https port configured
but no certificate bound" or "certificate bound but no https port". If the customer asks, say it is outside
this check's scope instead of silently re-adding it. Never read `DescribeWebRules[].CertExpireTime` — the
official API reference marks it *not currently used*.

Report the **bound certificate name, the expiry date and the remaining days** for every domain that has one,
including healthy ones; a customer reading only "PASS" cannot plan a renewal.

### Step 5 — C3: is Anti-DDoS the first layer on the Internet path

Walk the full CNAME chain — **primarily from each cloud probe point's `DNSRaw`**, falling back to local `dig` only when cloud probing is unavailable — and classify every hop: Anti-DDoS CNAME,
scheduler CNAME, Alibaba Cloud WAF / CDN / DCDN / GA, third-party CDN/security, or the origin itself. Then
judge the **order**, not just the presence:

- First hop is an Anti-DDoS CNAME → `PASS_FIRST_LAYER`, but the detail must say **whose**: this domain's own `Cname`; or another rule's `Cname` in this account (say it is not this domain's and require human confirmation of the binding); or only the `*.aliyunddos*.com` signature with no matching rule (ownership unconfirmed, set `needs_agent_review`). Never write "this domain's CNAME" for the latter two.
- First hop is a scheduler CNAME whose rules contain an effective Anti-DDoS line → `PASS_VIA_SCHEDULER`, or `INFO_SCHEDULER_ON_DEMAND` when the `RuleType` means Anti-DDoS only switches in under attack (tiered protection / overseas acceleration / secure acceleration) — that is by design, not a defect.
- The first hop is a CDN/WAF/GA/third party and no scheduler rule explains it → `FAIL_NOT_FIRST_LAYER`: attack traffic reaches that front layer unscrubbed. The detail must name the sub-case. **(b) Anti-DDoS is visible at hop ≥ 2** — provable, because the front layer delegates onward by CNAME (the traffic scheduler and GTM/GSLB-style delegation do; a typical CDN/WAF does not). **(c) No Anti-DDoS hop anywhere** — say plainly that Anti-DDoS is not first **and** that whether it exists behind that layer is **not determinable from DNS**, because the front layer's back-to-origin configuration is not in public DNS; the follow-up is to read that layer's origin config. Never write "Anti-DDoS is behind the CDN" as a fact in sub-case (c).
- Resolution lands on an origin IP with no Anti-DDoS hop → `FAIL_DIRECT_TO_ORIGIN` (the origin set **is** complete — the customer typed it). Resolution lands on a known Anti-DDoS instance IP → `WARN_FIRST_LAYER_VIA_A_RECORD`. Resolution lands on an IP matching **nothing** this account knows → `NOT_APPLICABLE_NO_IP_BASIS`: the account cannot say whose IP that is, so C3 must not claim "Anti-DDoS is not in the path" nor "direct to origin" (`DescribeInstances[].Ip` is measurably incomplete). C1 still judges that domain against its own `Cname`, so the finding is not lost.
- Scheduler matched but no `Rules[]` entry has `ValueType=1` **and** `Status=1` → `FAIL_SCHEDULER_NO_DDOS_LINE`.
- Different probe points see different first layers → `WARN_MULTI_PATH`.

C3 runs **even when C1 came back `NOT_APPLICABLE_*`**: with no Anti-DDoS CNAME to expect, the chain still
shows what the traffic actually traverses, which is what the customer needs in order to decide whether to
finish the onboarding.

Hop-classification signature suffixes are **auxiliary evidence only**; the authoritative test is an exact
match against the expected CNAME set from Step 2. An unclassifiable hop is reported as `UNKNOWN_HOP` for the
agent to reason about — never guessed into a category. Chain-walking depth is capped at 8 hops.

### Step 6 — C4: access health, mainland China vs overseas

Probe the **domain** (not the origin IP) over the protocol/port actually configured, from `DomesticCount`
mainland points and `OverseasCount` overseas points (default **3 + 3** — C4 exists to compare the two halves,
so neither may be empty), and read `DescribeSiteMonitorLog` per-point detail.

- Overseas vantage points must be **discovered at runtime** from `DescribeSiteMonitorISPCityList` by filtering `Country.en != "China"` (the response also carries `Country.zh_CN`, `CityName.*`, `IspName.*`, `Region.*`, `Area.*`, `IPV4ProbeCount`).
- **[MUST] The response uses FLAT DOTTED KEYS, not nested objects**: `Country.en`, `Country.zh_CN`, `CityName.zh_CN`, `CityName.en`, `IspName.en`, `Region.en`, `Area.en` — plus a bare `Country` that holds the numeric country **code** (e.g. `629` for China). Reading `item["Country"]` as an object therefore yields the code, and `"629" != "China"` silently classifies **every** point as overseas: the domestic group comes back empty and mainland points get counted as overseas, which destroys the only comparison C4 exists to make. Read the suffixed flat keys first, and **assert the domestic group really is China before creating any paid task**.
- **C4's purpose is global access health, so both groups are mandatory.** Default when the user did not specify: **3 domestic + 3 overseas** — symmetric, and enough to tell "one point flaked" apart from "a region is down". If either group ends up empty the mainland-vs-overseas comparison does not exist: report that half as `NOT_DETECTED`, say the comparison is void, and never let the healthy half imply the other one is fine. **No overseas city/ISP code is hardcoded in this skill** — the official docs do not publish example overseas codes, so any hardcoded value would be a guess. If no overseas point with `IPV4ProbeCount > 0` can be found, set C4-overseas to `NOT_DETECTED` with that reason. **Never report overseas as healthy because no overseas probe ran.**
- Per region group emit `HEALTHY` / `PARTIAL` / `UNAVAILABLE` / `WARN_SLOW` / `NOT_DETECTED` (the last only for a group with zero probe points — see the `[MUST]` below), judged by `HTTPResponseCode` (2xx/3xx = success) and `errorCode` — **never** by `TotalTime >= 0` and never by a `status` field. Latency signals: `TotalTime`, `HTTPDNSTime`, `SSLConnectTime`, `tcpConnectTime`.
- **Cross-region divergence is the diagnostic payload.** Report the pair, not just the two halves: overseas-fail + mainland-ok points at an incomplete certificate chain, an acceleration line that never took effect, or an instance/region mismatch; mainland-fail + overseas-ok points at ICP-filing interception or an international-edition instance serving mainland users; both-fail with 5xx points at back-to-origin failure (often the origin ACL not allowing Anti-DDoS back-to-origin ranges). Mapping table in `references/check-criteria.md` §C4.
- With `ProbeMode=local`, C4 becomes a single-egress `curl` result. Report it as such and mark the mainland/overseas comparison `NOT_DETECTED` **in `report.md` and the JSON**; in the customer-facing chat reply write "未检测" plus the cause instead of the bare token (Step 7). **[MUST] A C4-only request still runs `check_local.py` first** (Step 3), before creating the `HTTP` probes: it is easy to read that script as "the C1/C3 DNS thing" and skip it when the user asked only about mainland-vs-overseas health, but it is the **only** judge of C2 and the module `parse_probe_log.py` imports the C1/C3 judges from, so a C4-focused run that skips it silently loses C2 while the report still looks complete.
- **[MUST] Under `ProbeMode=cloud` the C4 mainland-vs-overseas comparison always gets a real verdict** — `HEALTHY` / `PARTIAL` / `UNAVAILABLE` / `WARN_SLOW` — because both groups have points by construction (3 + 3). "Every point failed" is `UNAVAILABLE`, which *is* an answer; do not relabel it `NOT_DETECTED`. Reserve `NOT_DETECTED` for a group that genuinely has **zero** probe points (no overseas vantage with `IPV4ProbeCount > 0`, or task creation failed), and then name that cause in words.
- **[MUST] State the cause, not just the token.** Wherever a check is undetected or inapplicable, the customer-facing summary must carry the concrete reason in words ("C3 cannot be judged: the domain has no public DNS record at all") rather than a bare label. A bare `NOT_DETECTED` / `NOT_APPLICABLE_*` with no reason is an incomplete answer, and in a cloud-mode C4 report the bare token also misstates what was measured.

### Step 7 — Summary output

> **[MUST] Output location (write-then-verify)**: every artifact (`report.md`, `access-config.json`,
> `local-evidence.json`, `taskids.json`, `probe-evidence.json`) goes into `$OUT_DIR`; scripts you copied or
> generated go into `$RS_DIR`. Then `ls -la "$OUT_DIR/" "$RS_DIR/"` and confirm each expected file exists with
> non-zero size. If a file landed in the working-dir root, `cp` it into `$OUT_DIR` and re-verify. Do not give
> the final answer before verification passes.

Assemble `report.md` using the exact section structure and the Finalize checklist in
`references/verification-method.md`. Re-read that checklist before saving; do not write the report from memory.
**[MUST] The chat reply opens with the pipe-delimited coverage line in the exact form `references/verification-method.md` Finalize item 10 specifies — re-read item 10 before sending, do not reconstruct the format from memory. A self-composed table or prose summary *in place of* that line is a finalize failure even when every number in it is correct: the observed failure mode is a clean-looking results table with no mode/region suffix, so the reader cannot tell a multi-vantage cloud run from a single-egress local one, and the disclosure words the customer opened with vanish from the last message they read.** **[MUST] The chat reply — not just `report.md` — must carry** the coverage line plus one line per situation that actually occurred (pre-checks, disclosure, early-stop evaluation, gate "未找到", "降级", wildcard option, local single-egress, C4 "国内"/"海外"); a coverage line alone hides what the run found. Two are consistently under-reported and must never be omitted: **(a)** when the gate returned `NOT_FOUND_IN_ACCOUNT`, say the original target was "未找到" and **repeat it verbatim exactly as the user typed it** (the full domain, or the full instance ID such as `ddoscoo-cn-…`) — a paraphrase like "该实例"/"该域名" without the identifier answers a different question than the one asked, and it is required whether or not a substitute was chosen; when a substitute *was* chosen, also name the "替代"/"已有" domain actually checked, because reporting only the substitute's results hides that the requested target is not in this account; **(b)** when degraded mode was used, say "降级" and "无基线".
**[MUST] When the run *began* as a disclosure request** ("先告诉我调用哪些 API、有什么费用、需要确认哪些参数") — including the common case where the user then supplied the parameters and the check continued — the disclosure content must reach the **final** reply, not only the round that asked the question; a run that discloses in round 1 and reports results in round 2 leaves the customer's original question answered only in a message they have already scrolled past. That reply *is* the deliverable — it must name all three products and their purpose (`ddoscoo` config, `cms` site monitoring, `cas` certificates), state the cost model (cloud probing requires activating "站点监控" and is "按量付费"; local probing costs nothing), present the ProbeMode choice as `cloud` / `local`, and list the parameters awaiting confirmation (`RegionId`, "域名范围"); a reply that only asks the question without this content has not disclosed anything. **[MUST] Reply in the language the user wrote in.** A Chinese request answered in English loses the very terms the customer and any acceptance check look for ("降级", "无基线", "未找到", "未检测") and reads as if those findings were skipped.
 And it bans the bare underscore `NOT_DETECTED`
token in customer-facing output: write "未检测" or "Not-Detected" plus the cause. Under `ProbeMode=cloud` the C4
comparison always has a real verdict (`HEALTHY` / `PARTIAL` / `UNAVAILABLE` / `WARN_SLOW`), because both groups
have points by construction; the underscore tokens stay in `report.md` and the JSON, where they are checkable.

---

## Cloud Probe Error Handling Decision Tree

Applies to **any** failure of `DescribeSiteMonitorISPCityList`, `CreateInstantSiteMonitor`, or
`DescribeSiteMonitorLog`. Classify, act, and record. Never silently skip an item; never fall back to local
unconditionally.

| Type | Error signature | Action |
|------|-----------------|--------|
| **A — service not activated** | `not activated` / `service not opened` / `Forbidden` pointing at site-monitor (Network Analysis and Monitoring) activation | Tell the user "cloud probe service not activated, switched to local probe"; switch **all** remaining probes to Method 2; mark C4-overseas `NOT_DETECTED`. |
| **B — plugin parse error** | `invalid character 'r' looking for beginning of value` or other `--options-json` JSON parse errors | An `aliyun-cli-cms` plugin bug, **not** a JSON syntax error. Run the remediation ladder in `references/acceptance-criteria.md` (update plugin -> generic RPC channel with PascalCase params -> temp-file input). Only fall back to local after all three fail, and warn in the report. |
| **C — throttling** | `Throttling` / `QuotaExceeded` / `RequestLimitExceeded` / `ServiceUnavailable` | Backoff 2s / 4s / 8s, max 3 retries; raise the inter-call interval 1.5s -> 3s for the rest of the batch. After 3 failures mark the item "creation failed - throttled" and list it in the Not-Detected List. **Do not skip the remaining items.** |
| **D — service internal error** | `InternalError` / `SDK.ServerError` / HTTP 500/502/503 from the probe API itself | Retry once after 3s; if it still fails, fall back to local for that item and note "cloud probe internal error, fell back to local". |
| **E — no overseas probe point** | `DescribeSiteMonitorISPCityList` returns no entry with `Country.en != "China"` and `IPV4ProbeCount > 0` | Not an API error. Set C4-overseas `NOT_DETECTED` ("no overseas probe point available"), keep the domestic half, and say it in the verdict. |
| **Unknown** | anything else | Log the raw error, fall back to local for that item, and list the error explicitly. Never present it as `PASS`. |

> **[MUST] Never pass help-text placeholders as flags.** Strings like `--task-xxx`, `<value>`, `[options]`
> in `aliyun ... help` output are placeholders. Real flags: `--task-type`, `--task-name`, `--task-ids`,
> `--address`, `--options-json`, `--isp-cities`, `--random-isp-city`, `--agent-group`.

## Cleanup

One-off probe tasks end by themselves after execution — **no persistent resource needs cleanup**. This skill
is read-only plus one-off probes throughout: it never creates a site-monitor instance, never modifies
Anti-DDoS / DNS / certificate configuration, and never writes to the customer account.

## Best Practices

1. **Config first, probe second.** Every verdict must name the config value it was compared against (`Cname`, `CertName`, `ProxyTypes`, `Rules[]`). A probe result with no config counterpart is uninterpretable.
2. **Fetch web rules region-wide, never with `--instance-ids`**, and always verify `len(fetched) == TotalCount`. Under-collection is the worst failure mode of this skill.
3. **`DescribeSchedulerRules` takes `PageSize` as required** and has no `RegionId` request parameter (the CLI still needs `--region` for endpoint routing). Its rules are domain-agnostic — bind them to domains by observed DNS, never by assumption.
4. **`CertExpireTime` from `DescribeWebRules` is documented as *not currently used*.** The bound certificate's expiry comes from `cas`; never report that field as an expiry date.
5. **CloudMonitor returns no TLS certificate data.** Only `SSLConnectTime`. Any claim about certificate expiry must come from `cas` — and C2 makes no claim at all about the *served* certificate, which this skill does not read.
6. **Probe the domain for C4, the CNAME chain for C1/C3 — never the origin IP.** Origin probing belongs to `alibabacloud-ddos-origin-exposure-detector`.
7. **HTTPS probing uses `--task-type HTTP` with an `https://` address prefix.** `TaskType` has no `HTTPS` enum and raises `TaskType does not exists`. Valid enum: `HTTP` / `PING` / `TCP` / `UDP` / `DNS`.
8. **`DescribeSiteMonitorLog` parsing traps**: query one `--task-id` at a time (comma-separated IDs raise `invalid character`); `Data` is a **JSON string** needing a second `json.loads`; the DNS `ips` field may carry a trailing comma (split, strip, drop empties); `errorCode` is an integer and **no `errorMessage` field is documented**, so classify failures by `errorCode` + `HTTPResponseCode`, not by error text.
9. **`TaskId` is at `CreateResultList[0].TaskId`**, not `Data.TaskId`.
10. **Probes have latency**: poll every 5s, up to 6 times; keep waiting while `Data` is empty.
11. **Pace the calls**: about 1.5s between adjacent `CreateInstantSiteMonitor` calls; <= 10 domains per batch; on throttling follow Type C.
12. **Prefer real-user vantage points for C4**: Telecom (ISP 132) / Unicom (232) / Mobile (5) for the mainland half rather than Alibaba-Cloud-internal points, which do not represent user access.
13. **Report the evidence, not just the label**: every FAIL/WARN row carries the observed value (resolved IP or CNAME, expiry date and remaining days, chain hops, per-point HTTP code and country/ISP).
14. **Never fabricate or substitute a value.** Domains, CNAMEs, IPs, cert names, dates, and status codes are copied character-for-character from the raw API/probe output. Unknown means `-` plus a Not-Detected entry.
15. **Never persist or print customer credentials** — and never print their field names or abbreviations either, including inside this skill's own warnings (see the Step 0.5 credential-vocabulary rule).
16. **Gate on ownership before judging (Step 1.5).** When the user names a domain or instance, resolve it across every region the account has instances in, and accept wildcard coverage and scheduler-CNAME onboarding as legitimate membership. Unresolved → stop; ask the either/or **only** if the request pre-authorised a substitute or a degradation, otherwise report "不适用" and terminate (Step 1.5 item 2, terminal branch). Never manufacture a baseline, never present a baseline-free public observation as an onboarding verdict, and never re-open a `ProbeMode` the user already fixed.

## Dependencies

**Python** >= 3.7, standard library only (`argparse`, `json`, `math`, `os`, `re`, `subprocess`, `sys`, `time`,
`datetime`); no pip packages, so no
`requirements.txt`. **Aliyun CLI** >= 3.3.3 with the `ddoscoo` and `cms` plugins (plus `cas` when
`WithCas=true`, the default) and valid credentials. **System tools**: `dig` (C1/C3 resolution and origin
normalization) and `curl` (C4 local fallback). C2 needs no local tool — it reads `cas`.

## Scripts

`scripts/` codifies the deterministic, easy-to-get-wrong parts. They only fetch, construct, and parse — the
ambiguous judgments (an `UNKNOWN_HOP` chain, a hostname-mismatch edge case, a cross-region divergence) are
left to the agent per `references/check-criteria.md`. The three cloud-calling scripts take both UA values from
the environment: `SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/xxx.py ...`.
Each resolves the version from `SKILL_VERSION`, falling back to this skill's `references/manifest.json`, and
exits non-zero instead of inventing or borrowing a version when neither yields one. `check_local.py` calls no
cloud API and needs neither value. The scripts are optional — the Core Workflow can be run by hand — but
recommended, because pagination completeness and vantage-point selection are exactly where manual runs go
wrong.

1. **`scripts/fetch_config.py`** — config truth + ownership gate. Region-wide paged fetch of `describe-instances` / `describe-web-rules` / `describe-scheduler-rules`, with `--instance-ids` and `--domain` API-side filtering deliberately unavailable for web rules (both hide wildcard rules and cause under-collection), a `TotalCount` completeness check, `ProxyTypes` expansion, `RsType=1` origin normalization via local `dig`, wildcard flagging, the merged `expected_cnames` set, and the `cas` certificate lookup that C2 depends on (on by default, `--no-cas` to skip, with a `GetUserCertificateDetail` fallback when the list record has no `EndDate`). `--expect-domains` runs the Step 1.5 gate across all searched regions and emits `scope_gate` with `FOUND_EXACT` / `FOUND_WILDCARD` / `FOUND_VIA_SCHEDULER` / `FOUND_INSTANCE` / `NOT_FOUND_IN_ACCOUNT` (the last one including the observed CNAME chain and near-miss hints). -> `access-config.json`
2. **`scripts/check_local.py`** — **always run, in every `ProbeMode`**. It is the **only** judge of C2 (reading the `cas` data already in `--config`), the single home of the C1/C3 judging functions that `parse_probe_log.py` imports, and the source of multi-resolver `dig` corroboration plus `RsType=1` origin normalization. What is *fallback-only* is the **authority of its `dig` chain for C1/C3 verdicts** when cloud probing is available — not the script itself. It calls no cloud API and costs nothing. Walks the full CNAME chain (max 8 hops) for C1/C3, classifies hops, resolves against both the system resolver and public resolvers to expose per-line divergence, judges C2 purely from the `cas` data already present in `--config` (no probing), and optionally runs a single-egress `curl` health probe for C4. -> `local-evidence.json`
3. **`scripts/create_probes.py`** — cloud probes. Selects mainland + overseas vantage points from `describe-site-monitor-isp-city-list` (overseas discovered by `Country`, never hardcoded), builds one `DNS` task per domain that serves **both C1 and C3** (group `dns_chain`) plus `HTTP` tasks for C4, sanitizes task names, keeps the 1.5s interval, and backs off 2s/4s/8s on throttling. -> `taskids.json`
4. **`scripts/parse_probe_log.py`** — probe evidence (**primary** observation source for C1/C3). Polls and second-parses `ProbeLog`, rebuilds each point's ordered chain from `DNSRaw` via `chain_from_dnsraw()` into the same shape as `check_local.resolve_chain()`, then judges C1 **and** C3 by importing `judge_c1` / `judge_c3` / `classify_ips` / `find_scheduler_rule` from `check_local.py` — one judging implementation, two observation sources. Splits points into mainland/overseas, emits per-point chain verdicts plus `WARN_POINT_INCONSISTENT` when points disagree (never a majority vote), keeps the IP-landing bucket in a separate `observed_ip_landing` column, reports C4 per-point codes/latencies with the cross-region divergence signal, and merges the C2 verdicts from `--local-evidence` so all four checks land in one file (it does not judge C2 itself, and says so loudly when that file is missing instead of letting a whole check disappear). **Always passes `--start-time`/`--end-time`**: without an explicit window the service returns only its own recent range, so tasks created tens of minutes earlier come back with empty `Data` and get mis-recorded as `NOT_DETECTED`; the window defaults to `taskids.json.generated_at` minus 15 minutes. -> `probe-evidence.json`

## Reference Links

| Reference | Contents |
|-----------|----------|
| `references/check-criteria.md` | C1-C4 judgment tables, verdict taxonomies, thresholds, CNAME-hop classification, traffic-scheduler rules |
| `references/verification-method.md` | Per-step verification commands and criteria, scenario -> recommended action -> help doc, report template, Finalize checklist |
| `references/related-commands.md` | Full CLI command table and local `dig` / `curl` commands |
| `references/ram-policies.md` | Required RAM permissions (ddoscoo / cms / optional cas) and custom policy JSON |
| `references/acceptance-criteria.md` | Correct vs incorrect CLI usage, the `--options-json` plugin remediation ladder, security red lines |
| `references/cli-installation-guide.md` | Aliyun CLI and plugin installation |
