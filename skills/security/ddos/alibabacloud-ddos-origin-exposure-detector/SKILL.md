---
name: alibabacloud-ddos-origin-exposure-detector
description: |
  Alibaba Cloud Anti-DDoS Proxy (ddoscoo) origin-server IP exposure risk detector.
  Detects whether a website protected by Anti-DDoS Proxy still has its origin IP exposed to
  direct attack, across two scenarios: (S1) a protected domain whose public DNS still resolves
  to the origin IP, bypassing protection;
  (S2) the origin IP is directly reachable from the public Internet. Reads protected domains /
  CNAME / origin IPs via ddoscoo (DescribeWebRules / DescribeNetworkRules). Two probe methods:
  (1) cloud probe via Cms one-off site monitor (CreateInstantSiteMonitor + DescribeSiteMonitorLog);
  (2) local dig / curl / nc, used when cloud probe is unavailable. Binary verdict.
  Triggers: "源站IP暴露", "源站暴露检测", "高防被绕过", "流量绕过高防", "origin IP exposure",
  "DDoS origin detection", "ddos-origin-exposure", "检测源站", "探测源站", "网络分析与监控探测源站",
  "Call DescribeWebRules", "DescribeWebRules", "DescribeNetworkRules", "CreateInstantSiteMonitor",
  "DescribeSiteMonitorLog", "get protected domains", "probe origin server", "site monitor probe origin".
---

# Anti-DDoS Proxy Origin Cloud IP Exposure Risk Detection

Detects whether a website that has onboarded **Alibaba Cloud Anti-DDoS Proxy (`ddoscoo`)** still has its **origin server IP exposed on the public Internet and directly attackable by bypassing Anti-DDoS**.

This skill is distilled from real support tickets: many customers "onboarded Anti-DDoS but the origin still gets bandwidth-saturated / black-holed", with the root cause being an exposed origin IP whose traffic bypasses Anti-DDoS.

## Detection Scenarios (two classes, binary verdict, no grading)

| ID | Scenario | Judgment essence |
|------|------|---------|
| S1 | Domain DNS not pointing to Anti-DDoS (DNS layer) | For a protected domain configured in Anti-DDoS, if the public DNS resolution result intersects the origin IP set, traffic bypasses all intermediate protection layers and reaches the origin directly. **The judgment only looks at "does the resolved IP hit the origin IP", with no need to identify the Anti-DDoS/scheduler CNAME** — a resolution landing on the origin IP means exposure; landing on any non-origin address (Anti-DDoS IP, scheduler CNAME, WAF, CDN, etc.) means it went through an intermediate layer. This naturally covers ordinary Anti-DDoS, traffic scheduler, using the Anti-DDoS IP directly as an A record, and all such cases. Only validates domains already configured in Anti-DDoS; does not actively enumerate subdomains. |
| S2 | Origin directly reachable from the public Internet (network layer) | Probe the origin IP + business port directly from multiple public locations; if directly reachable, it is treated as exposure (regardless of whether the origin is an Alibaba Cloud asset). Probe method depends on onboarding type: **domain onboarding** uses HTTP probing (bind the Host header, inspect status code); **layer-4 port onboarding** uses TCP probing. |

> S1 was originally two scenarios (A1/A2); since their judgment signal is identical ("does the resolution result hit the origin IP"), they were merged into a single DNS-layer check.
> **S1 and S2 are independent**: S1 checks "does the current DNS bypass Anti-DDoS", S2 checks "is the origin locked down against the public Internet". Even if DNS points correctly (S1 miss), if the origin has no access control and is directly reachable (S2 hit), an attacker can still obtain the origin IP via historical resolution / certificate transparency and bypass Anti-DDoS. So both must be checked.

**Only two possible verdicts:**
- "**Exposure risk found**" + matched scenarios (S1 / S2, one or both) + affected domains / origin IPs + recommended actions
- "**No exposure risk detected for now**"

## Architecture (products and APIs involved)

`Anti-DDoS Proxy (ddoscoo) DescribeInstances + DescribeWebRules + DescribeNetworkRules` -> **choose one of two probe methods**: `CloudMonitor (Cms) CreateInstantSiteMonitor -> DescribeSiteMonitorLog` (cloud probe, recommended) **or** local `dig / curl / nc` (local probe).

> **[MUST] Disclosure**: Before this skill runs for real, you MUST clearly tell the user which product APIs will be called and their purpose, let the user choose the probe method, and only proceed after the user acknowledges.
>
> **1. Read Anti-DDoS configuration (always used, read-only)**
> - **Anti-DDoS Proxy (ddoscoo)** `DescribeInstances`: read-only, confirm whether the account has any new BGP Anti-DDoS instances (stop early if none).
> - **Anti-DDoS Proxy (ddoscoo)** `DescribeWebRules`: read-only, get layer-7 domain onboarding protected domains, Anti-DDoS CNAME, origins (IP or domain), and protocol/ports.
> - **Anti-DDoS Proxy (ddoscoo)** `DescribeNetworkRules`: read-only, get layer-4 port-onboarding forwarding rules (forward port, origin IP, protocol). These form the data basis for S1/S2.
>
> **2. Probe method (user chooses one)**
> - **Method 1 — Cloud probe (recommended)**: use **CloudMonitor (Cms)** `CreateInstantSiteMonitor` to create a one-off probe task and `DescribeSiteMonitorLog` to read per-probe-point details, performing DNS resolution (S1) and direct HTTP/TCP probing of origin IP:port (S2) from multiple public probe points. **Pros**: multi-region multi-ISP perspective, closer to real public access; **Prerequisite**: the site-monitor service must be activated (**pay-as-you-go, incurs cost**); if not activated, the API fails.
> - **Method 2 — Local machine probe**: use the **local machine** running this skill to run `dig` (DNS resolution, S1), `curl` (HTTP direct connect with Host header bound, S2 layer-7), `nc`/`curl` (TCP connectivity, S2 layer-4). **Pros**: zero cost, no service activation needed; **Limitation**: single network egress perspective only, may be affected by local network/firewall.
> - **Auto fallback**: if the user picks Method 1 but `CreateInstantSiteMonitor` fails because **the service is not activated** (API unreachable), **automatically fall back to Method 2 local probe** and inform the user "cloud probe service not activated, automatically switched to local probe".
>
> Note: all of the above are read-only queries or one-off side-effect-free probes (public probing / local probing); no customer configuration is modified and no persistent monitoring task is created.
>
> **Local tools (common to both methods)**: when the origin is a domain (RsType=1), resolve it to an IP locally with `dig +short` before probing (avoids consuming cloud probes and avoids resolving too many IPs that complicate probing).

---

## RAM Policy

The RAM permissions required by the APIs this skill uses are listed in `references/ram-policies.md`. The core ones are:
`yundun-ddoscoo:DescribeInstances`, `yundun-ddoscoo:DescribeWebRules`, `yundun-ddoscoo:DescribeNetworkRules`, `cms:CreateInstantSiteMonitor`, `cms:DescribeSiteMonitorLog`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, domain names, origin IPs,
> probe agent selection, etc.) MUST be confirmed with the user. Do NOT assume or use default
> values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `ProbeMode` | Required | Probe method: `cloud` (cloud probe, recommended, requires the site-monitor service activated, pay-as-you-go) / `local` (local dig/curl/nc probe, zero-cost single egress). If `cloud` is chosen but the service is not activated, auto fall back to `local` | `cloud` (needs user confirmation) |
| `Domain` | Optional | Business domain to check (if empty, check all configured domains under the instance) | empty (all domains) |
| `InstanceIds` | Optional | Anti-DDoS instance ID, to narrow the DescribeWebRules query scope | empty (all instances) |
| `RegionId` | Required | ddoscoo China mainland is fixed to `cn-hangzhou`, outside China mainland is `ap-southeast-1` | needs user confirmation |
| `AgentGroup` | Optional | CloudMonitor probe point type: `PC` (fixed line) or `MOBILE` | `PC` |
| `RandomIspCity` | Optional | Number of random probe points (system-picked, mutually exclusive with IspCities) | `3` |
| `IspCities` | Optional | **Explicit probe points** (city + ISP), JSONArray: `[{"city":"546","isp":"465","type":"IDC"}]`; look up city/isp codes with `DescribeSiteMonitorISPCityList`. Setting this disables RandomIspCity | empty (uses RandomIspCity) |

---

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ddoscoo describe-web-rules --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

---

## Core Workflow

> 🚨 **Absolute execution order: Step 0 disclosure → user confirms (or default applied) → Step 0.5 env pre-checks → Step 1 instance query. ANY `aliyun` command before Step 0 completes invalidates the session — restart from scratch.**
>
> **IMPORTANT: Parameter Confirmation** — Before executing any command, you MUST confirm `RegionId`, the target `Domain`/`InstanceIds`, and other parameters with the user; do not silently use defaults.

> **[MUST] Step 0 is a non-bypassable hard gate**: you must NOT run any `aliyun` CLI command or API call (including `describe-instances`, and **also including environment pre-checks** like `aliyun version`, `aliyun configure list/get`, `aliyun plugin list/update`) until you have output the Step 0 disclosure (APIs to be called + probe-method options with cost/perspective + requested confirmation of `RegionId`/`ProbeMode`). If the user gives no reply or replies without selecting, apply the Step 0 default (cloud probe) and state it explicitly — but the disclosure text must still be produced first. **Even if the user prompt explicitly names a specific tool or API (e.g., "Use Cms to probe origin server", "Use dig to check DNS resolution", "Call DescribeWebRules to get protected domains", "Invoke CreateInstantSiteMonitor", "Use nslookup/telnet/HTTP..."), you MUST still produce the full Step 0 disclosure BEFORE executing any command.** Do NOT interpret a tool-named prompt or an "environment check" intent as implicit consent to skip Step 0; the disclosure text is always output first. Skipping Step 0 invalidates the entire detection and must be restarted.

**Step 0 — Disclose API purpose, choose probe method, and confirm parameters**
1. Explain to the user which product APIs will be called (see "Disclosure" above), and confirm `RegionId` (mainland `cn-hangzhou` / non-mainland `ap-southeast-1`) and the detection scope.
2. **Let the user choose the probe method** (recorded as `ProbeMode`):
   - **Method 1 — Cloud probe (recommended, default)**: multiple public probe points, broader perspective; **requires the site-monitor service activated, pay-as-you-go incurs cost**.
   - **Method 2 — Local machine probe**: use local `dig`/`curl`/`nc`, zero cost, no service activation; single network egress perspective only.
   - Clearly state: if Method 1 is chosen but the service is not activated, causing `CreateInstantSiteMonitor` to fail, it will **automatically fall back to local probe**.
   - **[MUST] Default when the user does not answer**: if the user gives no explicit probe-method choice (empty reply, or proceeds without selecting), default to **Method 1 (cloud probe)** and tell the user: "No probe method selected; defaulting to cloud probe (multi-location perspective, pay-as-you-go). Reply `local` to switch to local probing." Do **not** silently pick local probing when the user has not confirmed.

**Step 0.5 — Environment pre-checks (MUST run ONLY after Step 0 disclosure is complete and acknowledged)**

> Run these checks now. If any fails, pause and ask the user to fix before continuing to Step 1.

1. **CLI version**: `aliyun version` — must be >= 3.3.3. If not: `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"` or `aliyun upgrade` (CLI >= 3.3.5). See `references/cli-installation-guide.md`.
2. **Plugin auto-install**: `aliyun configure set --auto-plugin-install true`, then `aliyun plugin update`.
3. **Credentials**: `aliyun configure list` — confirm a valid profile (AK/STS/OAuth). **NEVER** read/echo/print AK/SK values; **NEVER** ask the user to input credentials in conversation. If no valid profile: stop, ask user to configure credentials outside this session, then re-run.

**Step 1 — Instance existence check (early-stop gate)**
First confirm whether the account has any new BGP Anti-DDoS instances.

```bash
aliyun ddoscoo describe-instances \
  --region cn-hangzhou \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
# [MUST] describe-instances --page-size range is 1~50; describe-web-rules/describe-network-rules cap at 10 (over 10 raises InvalidPageSize). When there are many instances, paginate with --page-number to fetch all.
```

- **`Instances` empty / `TotalCount=0`** → **stop detection immediately** and output: "**No Anti-DDoS instance found**: no new BGP Anti-DDoS instance was found under `<RegionId>` for this account; there is nothing to detect. Please confirm the RegionId (mainland `cn-hangzhou` / non-mainland `ap-southeast-1`) is correct, or whether the account has activated Anti-DDoS Proxy." Do not proceed to later steps.
- **Instances exist** → record the `InstanceId` list (**only used in Step 2 for the per-instance layer-4 `describe-network-rules` query**; the layer-7 `describe-web-rules` is queried region-wide and does not use an instance filter), then proceed to Step 2 to read forwarding configuration.

**Step 2 — Read forwarding configuration (shared data basis for S1/S2, layer-7 + layer-4)**

*(2a) Layer-7 domain onboarding* — `DescribeWebRules` returns, for each protected domain: the Anti-DDoS CNAME `Cname`, origins `RealServers[]` (with `RsType`: 0=IP, 1=domain + `RealServer` value), and protocol/ports `ProxyTypes[]` (`ProxyType`=http/https/websocket… + `ProxyPorts[]`).

```bash
# [MUST] Query region-wide and fetch all: read TotalCount from page 1, then paginate by TotalCount to fetch every page
aliyun ddoscoo describe-web-rules \
  --region cn-hangzhou \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
# Only add --domain "www.example.com" when narrowing to a single domain
```

> **[MUST] Layer-7 domains MUST be fetched in full region-wide; NEVER filter with `--instance-ids`**:
> - **Do not filter `describe-web-rules` with `--instance-ids`** — in practice this filter causes **massive under-collection** (an account had 35 real domains in a region, but per-instance querying with `--instance-ids` returned only 7, missing 80%). `describe-web-rules` already **returns all website rules in the region**, so querying by region without an instance filter is what is complete. The goal is "all exposure surface in the whole region", so there is no need — and no reason — to split by instance.
> - **[MUST] Fetch-completeness check**: read `TotalCount` from the page-1 response, compute the number of pages needed (`ceil(TotalCount/10)`), fetch every page with `--page-number N`, and finally **verify the cumulative fetched WebRules count == TotalCount**. If they differ, you must re-fetch or warn. **Never proceed after fetching only page 1** (`--page-size` cap is 10; fetching one page misses all subsequent domains when TotalCount>10).

*(2b) Layer-4 port onboarding* — for each `InstanceId`, call `DescribeNetworkRules` to get port forwarding rules: `FrontendPort` (forward port), `BackendPort` (origin port), `Protocol` (tcp/udp), `RealServers` (origin IP list), `IsAutoCreate` (**the hard flag indicating whether it was auto-generated by website onboarding**, see exclusion note below).

```bash
aliyun ddoscoo describe-network-rules \
  --region cn-hangzhou \
  --instance-id "ddoscoo-cn-xxxxxxxx" \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
# [MUST] --page-size cap is 10; read TotalCount on page 1, paginate by ceil(TotalCount/10) with --page-number N to fetch all, and verify cumulative fetched count == TotalCount; re-fetch if mismatch
```

> **[MUST] Exclude "website-onboarding auto-generated" layer-4 rules (otherwise you get false probes/verdicts)**: when configuring **layer-7 website business**, Anti-DDoS **auto-generates same-port layer-4 TCP forwarding rules** based on the website's server ports (in the console such a rule has an **exclamation-mark icon** next to "forward protocol", cannot be manually edited/deleted, and disappears automatically when the website config is unbound). The `RealServers` of these auto-generated rules are **Anti-DDoS internal layer-7 forwarding/back-to-origin cluster IPs, not the user's real origin IP**; doing S2 layer-4 probing against them is both meaningless and **produces false positives** (you probe the Anti-DDoS cluster, not the origin).
> - **Identification (preferred: hard flag)**: each rule returned by `DescribeNetworkRules` includes an **`IsAutoCreate`** field (corresponding to the console's exclamation mark). **`IsAutoCreate=true` means it is a website-onboarding auto-generated rule** — the only auto-creation source of a layer-4 rule is layer-7 website onboarding, so this field can directly and reliably decide it; prefer it.
> - **Fallback criterion (when `IsAutoCreate` is missing/unavailable)**: if a layer-4 rule's `Protocol`+`FrontendPort` matches the server port used by some `DescribeWebRules` domain **under the same instance** → it is an auto-generated rule for that website (same instance + same protocol + port must be unique; once a website occupies a port, the corresponding layer-4 rule is auto-generated and the user cannot manually create a same-port rule, so a port collision is sufficient to decide; this criterion is region-independent). **Note: do NOT use "reserved ports 80/443/8080/8443/53" to decide** — that restriction only applies to China mainland (ICP filing regulation); **outside China mainland (ap-southeast-1) layer-4 Anti-DDoS can legally configure 80/443**, and excluding by that would wrongly delete real detection targets and cause under-detection.
> - **Handling**: **remove** the identified "website auto-generated layer-4 rules" from the S2 layer-4 probe list (their exposure risk is already covered by the corresponding layer-7 domain's S1/S2), and list them separately in the report noting "the following layer-4 rules are auto-generated by layer-7 website onboarding; the origins are Anti-DDoS forwarding cluster IPs, not user origins, and are excluded from layer-4 probing". The only rules that truly need S2 layer-4 probing are **user-manually-created non-website ports** (e.g. custom 8081/8082/9000/9999) forwarding rules.

- **Both layer-7 and layer-4 rules empty** → output: "An Anti-DDoS instance exists but no forwarding rule (layer-7 domain / layer-4 port) is configured; nothing to detect." Stop.

**Build a checklist for each detection object**, recording: `identifier (domain OR instance+port)`, `onboarding type`, `Anti-DDoS CNAME (layer-7 only)`, `origin list (value + RsType)`, `business port`.
- **Onboarding type**: from DescribeWebRules → **domain onboarding (layer-7)**; from DescribeNetworkRules → **port onboarding (layer-4)**.
- **[MUST] Port expansion rule (avoid HTTPS/multi-port under-detection)**: for each layer-7 domain, expand **every** entry of `ProxyTypes[]` × **every** port of `ProxyPorts[]` into a configuration item (a single domain can have HTTP:80 + HTTPS:443 + custom 9090 simultaneously — you MUST NOT pick only the first port). For each layer-4 rule, expand every `FrontendPort` × every `RealServer` in `RealServers` into a configuration item. **Probe dedup rule**: because WebSocket (ws) and HTTP share the same TCP port and initial HTTP handshake (ws:// is an Upgrade from HTTP), entries that map to the same `(origin_ip, port, protocol)` but differ only in ProxyType (e.g. `websocket:80` vs `http:80`) MAY be deduplicated for probing — one HTTP probe covers both. The S2 probe target count = unique `(target_id, origin_ip, port, protocol)` tuples after dedup; Coverage counts every original configuration item sharing that IP:port as "covered" by one probe result. Skipping any **distinct port** (not ProxyType) causes coverage < 100%.
- **Origin normalization**: if a layer-7 origin has `RsType=1` (domain), first resolve it to IP with **local `dig +short <origin-domain>`** (do not use cloud probe to resolve, to avoid resolving too many IPs that complicate probing); layer-4 `RealServers` are usually already IPs, and if they are domains, resolve them locally too.
- **Wildcard domain identification and handling**: if a domain returned by DescribeWebRules starts with `*.` (e.g. `*.example.com`), flag it as a **wildcard domain**. Wildcard domains cannot be used directly in S1 (DNS probing) or S2 (HTTP origin probing) and need separate handling.
  **If there is no wildcard domain in the current scope** → go straight through the generic flow, no extra handling needed.
  **If a wildcard domain exists** → pause, explain the situation to the user, and offer three options:
  1. **User provides a subdomain list**: ask the user to give some actually-used subdomains under the wildcard (not all required, e.g. `www.example.com`, `api.example.com`); add these to the checklist and run the generic S1+S2 flow.
  2. **Probe with common prefixes**: generate a subdomain list by concatenating preset common prefixes (`www`, `mail`, `api`, `m`, `static`, `cdn`) with the wildcard parent domain. **You MUST explicitly tell the user which subdomains will be probed** (e.g. "the following subdomains will be probed: www.example.com, mail.example.com, api.example.com, m.example.com, static.example.com, cdn.example.com") and only proceed after user confirmation. Note in the report "wildcard `*.example.com` cannot exhaustively enumerate all subdomains; the following is a common-prefix sample".
  3. **Skip the wildcard**: do not probe the wildcard at all; only check the exact domains already configured in the current scope. Note in the report "wildcard `*.example.com` skipped, not included in detection".

> **Probe point selection (region and count controllable)**: all `CreateInstantSiteMonitor` probes (DNS/HTTP/TCP) can specify probe points:
> - **Count only**: `--random-isp-city N` (system picks N random points, default 3).
> - **Explicit region/ISP**: `--isp-cities '[{"city":"546","isp":"465","type":"IDC"}]'` (city=city ID, isp=ISP ID, type=IDC/LASTMILE). Mutually exclusive; setting isp-cities disables random-isp-city.
> - **Probe point type**: `--agent-group PC` (fixed line, default) or `MOBILE`.
> - **Get city/isp codes**: first confirm with the user whether a specific region is needed; if so, call `aliyun cms describe-site-monitor-isp-city-list --view-all true --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}` to look up codes. Judging "is the origin exposed" usually only needs 3~5 random multi-ISP points; explicit isp-cities is only needed to verify access from a specific region.

> **Batching and quota (important)**: an instance may have dozens to hundreds of rules. Batching and throttling rules:
> - **Batching**: recommend ≤10 detection objects per batch; confirm scope with the user first to avoid an accidental full scan.
> - **Call interval**: keep about **1.5s** between adjacent `CreateInstantSiteMonitor` calls (avoid triggering the CloudMonitor one-off probe quota throttling).
> - **[MUST] Throttling backoff retry**: on throttling errors, follow **Type C** of the Cloud Probe Error Handling Decision Tree (backoff 2s/4s/8s, max 3 retries, then list-as-failed; **never** skip remaining items).
> - **Slow down when throttled**: once throttling hits, **double** the call interval for the rest of the batch (1.5s → 3s), and sleep 5s before the next batch.

---

**Step 3 — S1: DNS resolution check (judges "does the resolved IP hit the origin IP", layer-7 domain objects only)**

> **Applicability**: S1 only makes sense for **layer-7 domain onboarding** objects; layer-4 port onboarding has no domain resolution concept, so skip S1 and go straight to S2. **[MUST] Skipping S1 must NOT cause S2 to be skipped**: for a layer-4 object you skip only the S1 DNS check, but you must still run the Step 4 S2 probe (TCP/UDP) for it. Do not treat "no S1 for layer-4" as "no cloud probe at all for layer-4".
> **Judgment core**: only compare whether "the IP the domain finally resolves to" intersects the "origin IP", **with no need to identify the Anti-DDoS/scheduler CNAME or Anti-DDoS IP**. Intersection = bypass protection to origin = exposure; no intersection = went through some intermediate layer (Anti-DDoS/scheduler/WAF/CDN) = not exposed. This logic naturally covers ordinary Anti-DDoS, traffic scheduler, using the Anti-DDoS IP directly as an A record, and all such cases.

> **[MUST] Strict field isolation (avoid confusion)**: the following three data classes are **semantically completely different and must never impersonate each other**; both the detection data structure and the report display must keep **three independent columns**:
> 1. **Config field: Anti-DDoS CNAME** (from the `Cname` returned by `DescribeWebRules`) — the CNAME address Anti-DDoS **assigned to the domain**, config info, not the actual DNS resolution result.
> 2. **Config field: origin IP set** (from `RealServers[].RealServer`; when `RsType=1`, the IP normalized via local `dig +short <origin-domain>`) — the **origin address**, not the resolution result of the "business domain" itself.
> 3. **Probe result: the IP the domain actually resolves to on the public Internet** (obtained by running a cloud probe DNS task **against the business domain itself** or local `dig +short <business-domain>`) — **only this column can be used for the S1 verdict**.
>
> **Forbidden**: filling class 1 (`Cname` config) or class 2 (origin IP, IP normalized from origin domain) into the class-3 "DNS resolution result" column to impersonate the actual resolution. If the business domain dig returns empty, record class 3 explicitly as "no resolution"; **do not** substitute the Anti-DDoS CNAME or origin IP. When judging, only read class 3.
>
> **Report display rule**: the report must show at least 4 columns per domain — `business domain`, `origin IP (RsType note)`, `Anti-DDoS CNAME config`, `actual resolution result IP` — and the verdict column must directly correspond to "actual resolution result IP ∩ origin IP".

> **Wildcard S1 probing**: per the user's Step 2 choice:
> - Option 1 or 2 (user-provided subdomains / common prefixes): run the generic S1 flow below for each expanded subdomain. **Additionally**: you may run local `dig '*.example.com' +short` (quote `*` in shell) to look up the wildcard fallback record's resolved IP as an auxiliary reference (cloud probe API support for `*.` format is uncertain; if it raises `IllegalAddress`, skip).
> - Option 3 (skip wildcard): do nothing, skip directly.

For each layer-7 domain, do DNS resolution, read the actual resolved IP, and pick the probe method by `ProbeMode`:

**(Method 1) Cloud probe**: launch a **DNS-type** one-off probe, then use **`DescribeSiteMonitorLog`** (note: not SiteMonitorData) to get **per-probe-point details**.

```bash
# 3a. Create the DNS probe task, record the returned TaskId
aliyun cms create-instant-site-monitor \
  --address "www.example.com" \
  --task-type "DNS" \
  --task-name "ddos-dns-check-www-example" \
  --random-isp-city 3 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
# [MUST] The returned TaskId is at CreateResultList[0].TaskId (not Data.TaskId)
```

> **[MUST] Auto fallback on service not activated**: classify per **Type A** of the Cloud Probe Error Handling Decision Tree — inform the user "cloud probe service not activated, automatically switched to local probe" and use **Method 2 local probe** for this and all subsequent domains/origins.

```bash
# 3b. Poll for detail logs (including the IP each probe point resolved to). Probing has execution latency:
#     query every 5s, up to 6 times; keep waiting while Data is empty.
aliyun cms describe-site-monitor-log \
  --task-ids "<TaskId>" \
  --metric-name "ProbeLog" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
# [MUST] Result-parsing gotchas:
#  1) --task-ids takes ONE TaskId at a time, query them one by one (CLI parsing of comma-separated multiple IDs is unstable and raises invalid character)
#  2) The per-probe-point data is in the returned Data field (a JSON string, needs second parse; not Datapoints)
#  3) The resolved IP field (e.g. ips) may have a trailing comma ("1.2.3.4,"); after split, strip and filter empty strings
```

**(Method 2) Local probe**: directly use local `dig` to resolve the domain and read the final resolved IP.

```bash
dig +short www.example.com          # Get the final resolved A-record IP (may go through multiple CNAME layers)
```

**Verdict (per domain, identical for both methods)**: intersect the domain's **final resolved IP set** with the **domain's origin IP set**
- **Non-empty intersection** (any probe point / local resolution hits an origin IP) → **S1 hit** (traffic bypasses protection to origin), record domain + hit origin IP.
- **Empty intersection** (all resolution results land on non-origin addresses: Anti-DDoS IP, scheduler/WAF/CDN addresses, etc.) → **S1 miss** (went through some intermediate protection layer).

> **Note**: the verdict does not care what CNAMEs are traversed, nor does it enumerate "legitimate pointing targets"; it only checks whether the final IP lands on an origin IP. When cloud probe and local dig agree, the conclusion is more reliable.

---

**Step 4 — S2: origin direct-connect probe (judges "is the origin directly reachable from the public Internet")**

> **[MUST] S2 is unconditional — never skip based on S1 results**: regardless of whether S1 found DNS resolution (all "miss", all "hit", mixed, or S1 skipped for layer-4), you MUST probe every S2 target from Step 2. "No DNS resolution" does NOT mean "origin unreachable" — attackers can obtain origin IPs via historical records/certificate transparency, making S2 mandatory even when S1 shows nothing.

> **[MUST] S2 verdict rules (read before probing)**: (a) **HTTP**: HIT only when `HTTPResponseCode` ∈ 2xx/3xx. 4xx/5xx (**including 401/403/404/409/429/500/502/503/504**) count as **not-exposed / uncertain**, never HIT — explicitly write "HTTP <code>, classified as not-exposed per S2 verdict rule" in the report. (b) **TCP**: HIT only when cloud-probe `errorCode` is empty **AND** `tcpConnectTime` has a real value (or local `nc -zv` returns "succeeded"); do NOT judge HIT by `TotalTime>=0` or `status!="error"`. (c) **HTTPS ports** (443 / any 443-like): use `--task-type HTTP` with `--address "https://<origin-ip>:<port>"`; the `TaskType` enum **does not** support `HTTPS` and raises `TaskType does not exists`. (d) When `ProbeMode=cloud`, cloud probe MUST be attempted first for EVERY expanded S2 target — only degrade to local per the Cloud Probe Error Handling Decision Tree.

For each normalized **origin IP + business port** from Step 1, **first pick the probe protocol (HTTP/TCP) by onboarding type, then pick the execution method (cloud/local) by `ProbeMode`**:

> **[MUST] Pre-filter the layer-4 probe list**: before layer-4 S2 probing, you must have completed the "exclude website-onboarding auto-generated layer-4 rules" filtering from Step 2 — probe **only user-manually-created non-website-port** layer-4 rules; never probe auto-generated rules (whose RealServers are Anti-DDoS forwarding cluster IPs).

> **[MUST] No subjective filtering of probe targets (avoids incomplete coverage + false "not exposed")**: after removing `IsAutoCreate=true` rules, **every origin IP:port of every remaining user-manual rule must be probed one by one with the chosen method**, none skipped. **Never** subjectively skip an origin IP because it "looks like a public/test/reserved IP" (e.g. `1.1.1.1`/`2.2.2.2`/`1.1.1.2`). **🚫 Forbidden skip reasons**: do NOT use `ProxyStatus=off` / `ProxyEnable=0` / IP-range judgment / "time constraints" / "seems already covered" as reasons to skip any S2 target — the ONLY valid exclusion for layer-4 rules is `IsAutoCreate=true`. Never do only local while skipping cloud probe — a third-party detection once subjectively filtered out 6 origins this way, ending with only 50% coverage, and wrongly described the unprobed targets as "not exposed". If a target genuinely cannot be probed (e.g. no IPv6 capability), it can only be marked "not detected" and **explicitly listed in the report's failed-items list (with IP:port + reason)**; **never** describe it as "not exposed / miss". Whether to clean up these suspected test configs is the customer's decision; the detector must not pre-judge for the customer and omit probing.

> **Wildcard S2 probing**: a wildcard (`*.example.com`) cannot be used directly as an HTTP Host header. Per the user's Step 2 choice: options 1/2 use each expanded subdomain as the Host for HTTP direct-connect to the origin IP one by one; option 3 skips the wildcard's S2 probing.

### Method 1 — Cloud probe

> **[MUST] S2 must attempt cloud probe first when ProbeMode=cloud**: whether or not S1 ran, every S2 target (layer-7 HTTP and layer-4 TCP/UDP) must first be probed via `CreateInstantSiteMonitor`. Only degrade to local probe (Method 2) after the service is confirmed not activated, or after the plugin-parse remediation ladder below has been exhausted. Do not skip cloud probe and go straight to local `nc`/`curl` while ProbeMode=cloud.

**(a) Domain onboarding (layer-7): HTTP probe + bind Host header, inspect status code**

> **[MUST] Correct way to probe HTTPS**: the `TaskType` of `CreateInstantSiteMonitor` **only supports `HTTP/PING/TCP/UDP/DNS`**; writing `HTTPS` raises `InvalidQueryParameter: TaskType does not exists` (verified in practice). The correct way to probe HTTPS business ports like 443 is `--task-type HTTP` + `--address "https://<origin-ip>:443"` (the `https://` URL prefix makes the probe do the TLS handshake); **do not** write `--task-type HTTPS`.

```bash
# HTTP ports use the http:// prefix; HTTPS ports (e.g. 443) use the https:// prefix; task-type is always HTTP
aliyun cms create-instant-site-monitor \
  --address "http://<origin-ip>:<port>" \
  --task-type "HTTP" \
  --task-name "ddos-origin-http-example" \
  --random-isp-city 3 \
  --options-json '{"header":"Host: www.example.com","time_out":5000}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
```

> **[MUST] Correct HTTP options-json (gotchas)**:
> - **Binding the Host header MUST use the `header` field**, format `"header":"Host: <business-domain>"`. The CMS HTTP probe options-json **has no `host` key**; writing `{"host":"..."}` will not bind the Host, causing the origin's Host-based routing to mis-verdict/miss. Separate multiple headers with `\n`.
> - **CLI escaping**: wrap the whole options-json JSON in **single quotes** (`'{"header":"Host: x","time_out":5000}'`); do not use double quotes + backslashes (easily re-parsed by the shell). Under a healthy CLI/plugin this submits fine (reaching the auth/business response). **If it still errors with `invalid character 'r' looking for beginning of value`, it is most likely an `aliyun-cli-cms` plugin version bug** — follow the "handle cloud-probe failures by error type" remediation ladder below; do NOT immediately treat it as a skill syntax error or immediately fall back to local.

**(b) Port onboarding (layer-4): pick TCP or UDP probe by the `Protocol` field**

> **[MUST] TCP/UDP address format (gotcha)**: the `--address` of a TCP/UDP probe **takes the origin IP only, no port**; the port is passed via `--options-json '{"port":<port>}'`. Writing `--address "ip:port"` raises `InvalidQueryParameter: illegal port`.

When Protocol=tcp, use a TCP probe:
```bash
aliyun cms create-instant-site-monitor \
  --address "<origin-ip>" \
  --task-type "TCP" \
  --task-name "ddos-origin-tcp-example" \
  --random-isp-city 3 \
  --options-json '{"port":<port>,"time_out":5000}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
```

When Protocol=udp, use a UDP probe:
```bash
aliyun cms create-instant-site-monitor \
  --address "<origin-ip>" \
  --task-type "UDP" \
  --task-name "ddos-origin-udp-example" \
  --random-isp-city 3 \
  --options-json '{"port":<port>,"time_out":5000}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
```

Get detail logs to judge:
```bash
aliyun cms describe-site-monitor-log \
  --task-ids "<TaskId>" \
  --metric-name "ProbeLog" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddos-origin-exposure-detector/{session-id}
```

> **[MUST] Cloud-probe detail "reachable/failed" verdict fields (avoid TCP false positives, judge strictly by these)**: `ProbeLog`'s `Data` is a JSON string; the per-probe-point verdict must only rely on the following **decisive fields**:
> - **TCP probe**: `errorCode` empty **and** `tcpConnectTime` has a real handshake time → **reachable (S2 hit)**; `errorCode` non-empty (commonly `611`), or the response contains `i/o timeout`/`connection refused`/`no suitable address found` → **failed (miss)**.
> - **HTTP probe**: inspect `HTTPResponseCode`, landing in **2xx/3xx** → hit; `0`/empty/4xx/5xx → miss.
> - **[MUST] NEVER use `TotalTime>=0` or `status!="error"` to judge "reachable"**: on failure `TotalTime` is still filled with the exhausted timeout duration (e.g. `5000.5`), and the TCP probe's `status` is always an empty string with no `"error"` enum at all — using these two conditions would make **every TCP probe that got a log be wrongly judged OPEN** (a third-party detection had 100% false positives this way; must avoid).


> **[MUST] On any cloud-probe error, classify it and act per the "Cloud Probe Error Handling Decision Tree" section below** (Type A service-not-activated → fall back to local; Type B plugin-parse error → remediation ladder then local; Type C throttling → backoff retry then list-as-failed; unknown → local fallback + note). Do not fall back to local unconditionally, and do not silently skip the item.

### Method 2 — Local probe

**(a) Domain onboarding (layer-7): `curl` direct-connect to the origin IP and bind Host with `--resolve` (equivalent to the cloud probe's Host header), inspect status code**
```bash
# HTTP (port 80 etc.)
curl -sS -o /dev/null -w '%{http_code}\n' --connect-timeout 5 --max-time 8 \
  --resolve "www.example.com:<port>:<origin-ip>" "http://www.example.com:<port>/"
# HTTPS (port 443 etc.): when the origin uses a self-signed / mismatched cert, add -k to judge connectivity + status code only
curl -sS -k -o /dev/null -w '%{http_code}\n' --connect-timeout 5 --max-time 8 \
  --resolve "www.example.com:<port>:<origin-ip>" "https://www.example.com:<port>/"
```

**(b) Port onboarding (layer-4): pick TCP or UDP local probe by the `Protocol` field**

Protocol=tcp:
```bash
nc -z -w 5 <origin-ip> <port> && echo "TCP OPEN" || echo "TCP CLOSED/FILTERED"
# Alternative: curl -sS -v --connect-timeout 5 "telnet://<origin-ip>:<port>" 2>&1 | grep -i connected
```

Protocol=udp:
```bash
nc -zu -w 5 <origin-ip> <port> && echo "UDP OPEN/NO-REJECT" || echo "UDP CLOSED/FILTERED"
# -u means UDP mode; note UDP has no handshake, "OPEN" only means no ICMP port unreachable was received
```

> **[MUST] IPv6 origin handling (cloud probe does not support IPv6 targets for now)**: if an origin `RealServer` is an IPv6 address (like `2400:...`), **cloud probe `CreateInstantSiteMonitor` cannot probe it** — confirmed by repeated testing: its probe backend **forces the IPv4 stack**, so even using `--isp-cities` to specify probe points with `IPV6ProbeCount>0` and probing a known publicly-reachable IPv6 (e.g. Alibaba public DNS `2400:3200::1`) still always raises `dial tcp4: address ...: no suitable address found` (TCP) or `ip resolved ... is not valid` (PING). The probe points returned by `describe-site-monitor-isp-city-list --ipv6 true` only mean "the probe machine has an IPv6 NIC", but the one-off probe execution does not resolve/connect IPv6 targets, so the IspCities approach is ineffective for IPv6 targets — **do not try to probe IPv6 via cloud probe again**.
> - **Handling order**: ① when the local machine has an IPv6 egress, probe with `nc -6 <ipv6> <port>` (or `curl -6`); reachable = S2 hit; ② when the local machine has no IPv6 egress, **mark "not detected" directly and list it in the not-detected list** (reason: "cloud probe does not support IPv6 targets, local has no IPv6 egress"; suggest re-testing later with `nc -6` on a machine that has an IPv6 egress).
> - **[MUST] Not detected ≠ not exposed**: when an IPv6 origin is marked not detected, it must never be counted as "not exposed / no risk"; coverage must deduct these items and this must be stated explicitly in the conclusion.

### Verdict (per origin IP:port, identical for both methods)
- **Domain onboarding (HTTP)**: any probe point / local direct-connect to the origin returns a **2xx / 3xx status code** → **S2 hit** (origin directly reachable at business level, real exposure). Returns 4xx/5xx or connection failure → treat as **not exposed / uncertain** (the origin may be only partly open or protected by WAF/auth), do not verdict S2, but may note "suspected partially reachable" in the report.
  > **[MUST] Never classify a 4xx/5xx status code as an S2 hit.** Only 2xx/3xx (e.g. 200, 201, 301, 302) count as a hit. 4xx/5xx codes — including **403, 409, 429, 500, 502, 503** — are **not exposed / uncertain**, never a hit. Example: if a probe returns HTTP 409, record in the report "HTTP 409 is a 4xx, classified as not-exposed/uncertain per the verdict rule, NOT an exposure hit"; do not report it as S2 hit.
- **Port onboarding (TCP)**: any probe point / local **TCP handshake succeeds (connected)** → **S2 hit**. All fail → S2 miss.
- **Port onboarding (UDP)**: any probe point / local probe **received no ICMP port unreachable (port not rejected)** → **S2 hit**. All return port unreachable / clearly closed → S2 miss. Note: UDP has no handshake, so "reachable" only means the port was not explicitly rejected; reliability is lower than TCP, note "UDP probe conclusion is for reference; confirm with the business" in the report.

> **Local probe limitation**: local is a single network egress perspective only, and may produce false negatives due to local network policy / origin regional access control (local unreachable does not mean unreachable from the whole public Internet). For a broader perspective, prefer activating and using the cloud probe method.

---

**Step 5 — Summary output (binary verdict)**

> **[MUST] Output file location (write-then-verify)**: all output files (e.g. `report.md`, `action-log.md`, `protected_domains.json`, intermediate JSON) must land in the session's `outputs/` dir; scripts/artifacts in `ran_scripts/`. Steps (do not skip):
> 1. Resolve + echo: `OUT_DIR="${OUTPUTS_DIR:-./outputs}"`, `RS_DIR="${RAN_SCRIPTS_DIR:-./ran_scripts}"`, then `echo "OUT_DIR=$OUT_DIR RS_DIR=$RS_DIR"` so the target paths are visible — never write only to the agent's working-dir root (not collected by the caller).
> 2. Create + write: `mkdir -p "$OUT_DIR" "$RS_DIR"` then write directly into these paths (e.g. `cp report.md "$OUT_DIR/"`).
> 3. Verify: `ls -la "$OUT_DIR/" "$RS_DIR/"` — confirm each expected file exists with non-zero size. If an expected file is absent from `$OUT_DIR` (commonly because it was written to the working-dir root), locate the stray file (e.g. `ls -la ./report.md`) and `cp` it into `$OUT_DIR`/`$RS_DIR`, then re-run `ls` until confirmed — do not give the final answer before verification passes.

> **[MUST] Verdict + display rules**: **Verdict** — S1/S2 any hit → `Exposure risk found` (list matched scenario, affected domains/origin IP:port, evidence, and remediation help-doc per scenario→doc mapping in `references/verification-method.md`); neither hits → `No exposure risk detected for now` (use the qualified wording per the Finalize checklist when coverage < 100%). **Display** — expand counts per instance (instance ID → frontend:backend port → protocol → origin IP), totals must match the expanded detail; list all cloud-probe creation failures (after 3 backoff retries) and local-probe timeouts in the Not-Detected List; state local-vs-cloud egress difference in the note and prefer cloud-probe for conflicts; quote every domain **character-for-character** from `DescribeWebRules`. See the **Report Template** section below for structure, Finalize checklist, and coverage-conditioned wording.

---

## Cloud Probe Error Handling Decision Tree

> Centralized error-classification for **any** failure from `CreateInstantSiteMonitor` or `DescribeSiteMonitorLog`. On error, classify by the error text and act; never silently skip an item, and never fall back to local unconditionally.

| Type | Error signature | Action |
|------|-----------------|--------|
| **A — service not activated** | `not activated` / `service not opened` / `Forbidden` clearly pointing to site-monitor/network-analysis activation | Inform the user "cloud probe service not activated, automatically switched to local probe"; switch **all subsequent** probes to Method 2 (local); continue detection. |
| **B — plugin parse error** | `invalid character 'r' looking for beginning of value` / other `--options-json` JSON parse errors | This is an `aliyun-cli-cms` plugin input-parsing bug, NOT a JSON syntax error. Run the remediation ladder in order, continue with cloud probe as soon as one succeeds. Only fall back to local after **all three** fail, and warn in the report. |
| **C — throttling** | `Throttling` / `QuotaExceeded` / `RequestLimitExceeded` / `ServiceUnavailable` | Exponential backoff retry 2s / 4s / 8s, **max 3 retries**; also raise the call interval 1.5s→3s for the rest of the batch. After 3 failures, mark the item "creation failed - throttled" and list it in the report. **Do NOT skip remaining items.** |
| **D — service internal error** | `InternalError` / `SDK.ServerError` / `HttpCode 500` / `502` / `503` on the cloud-probe API itself | Retry once after 3s; if it still fails, treat as service temporarily unavailable and **auto-fall-back to local probe** for that item (same as Type A), noting "cloud probe internal error, fell back to local" in the report. Do NOT abandon the item, and do NOT jump straight to `curl`/`nc` without recording the fallback reason. |
| **Unknown** | anything not matching A/B/C/D | Log the raw error, attempt local fallback for that item, and note the unknown error explicitly in the report (do not present it as "not exposed"). |

> **[MUST] Never copy help-text placeholders as real flags**: strings like `--task-xxxxxxx`, `--task-yyy`, `<value>`, `[options]` that appear in `aliyun ... help` output or error hints are **placeholders, not real parameters**. The real flags are `--task-type`, `--task-name`, `--task-ids`, `--address`, `--options-json` (or PascalCase in RPC mode). Never pass a placeholder verbatim.

**Type B remediation ladder (in order):**
1. **Update the plugin**: `aliyun plugin update --name cms` (`plugin update` only supports the singular `--name`; `--names` raises invalid flag; to reinstall use `aliyun plugin install --names cms`), then retry the original command.
2. **Generic RPC mode** (most reliable bypass, verified): invoke the same API through the generic OpenAPI channel instead of the plugin's hyphenated subcommand parser, using PascalCase parameters (`--version 2019-01-01`, `--TaskType`, `--TaskName`, `--Address`, `--RandomIspCity`, `--OptionsJson`, plus `--user-agent`). Preserves the full multi-region perspective. Exact template in `references/acceptance-criteria.md`.
3. **Temp-file input**: `echo '{"port":<port>,"time_out":5000}' > /tmp/opt.json`, then `--options-json "$(cat /tmp/opt.json)"`.

> **IPv6 origins are a separate limitation (not a probe error)**: cloud probe does not support IPv6 targets at all (see "IPv6 origin handling" in Step 4). Handle via local `nc -6`, or mark "not detected" when there is no IPv6 egress — never as "not exposed".

## Report Template (Step 5 output structure)

> **[MUST] STOP before writing report.md** — re-read this entire Finalize checklist right now. Do not write the report from memory; verify every item below against your draft before saving the file.
>
> **[MUST]** The final `report.md` (written to the outputs directory per Step 5) must follow the exact section structure defined in `references/verification-method.md` ("Report Template" section): Verdict, Scope & Config, S1 table, S2 table, Not-Detected List, per-stage Coverage, Recommended Actions, and the closing Note.
>
> **[MUST] Finalize checklist — verify ALL of the following BEFORE returning `report.md`. If any item fails, fix and re-check:**
> 1. **Verdict** contains exactly one of: `Exposure risk found` **or** `No exposure risk detected for now` (with the qualified wording rule below).
> 2. **S1 table** has exactly 4 columns in this order: `Business Domain | Origin IP (RsType) | Anti-DDoS CNAME Config | Actual Resolution Result IP`. The three IP/CNAME columns must remain independent — the Anti-DDoS CNAME config column MUST be present even when empty (write `-`), do not collapse or reorder columns.
> 3. **S2 table** has: `Onboarding | Origin IP:Port | Protocol | Probe (cloud/local) | Status/Result | Verdict`.
> 4. **Not-Detected List** section is present. If nothing to list, write `None`; never omit the section entirely.
> 5. **Coverage** section shows S1 and S2 on separate lines: `S1: probed X / total Y (Z%)` and `S2: probed A / total B (C%)`. Compute Z% and C% as `probed / total × 100`, rounded to one decimal; verify the arithmetic. **Correct examples**: `5/5 (100%)`, `6/11 (54.5%)`, `1/11 (9.1%)`. **Wrong examples (NEVER output these)**: `1/11 (100%)` ← wrong math, `11/1 (10%)` ← inverted fraction, `5/5 (10%)` ← wrong percentage.
> 6. **Closing Note** ends verbatim with the ticket URL preserved character-for-character: `... you may submit an Alibaba Cloud ticket: https://selfservice.console.aliyun.com/ticket/createIndex`. **Never paraphrase the sentence and never omit or shorten the URL** — the raw URL string must appear in the final file.
> 7. **[MUST] Data integrity — no fabrication, no substitution**: every domain / origin IP / CNAME / port / status-code / RsType in the report must be **copied character-for-character** from the raw `DescribeWebRules` / `DescribeNetworkRules` / `DescribeSiteMonitorLog` response JSON. Never summarize, abbreviate, rename, or fabricate a value (e.g. do NOT rewrite `secure.qq.com` as `jiafei1.qq.com`, do NOT fill unknown origins with placeholders like `1.1.1.1`/`0.0.0.0`, do NOT invent HTTP status codes). If a value is unknown, write `-` or `unknown` and mark the item in the Not-Detected List. If any fabricated/substituted field is detected during self-review, the report is invalid and MUST be regenerated from the raw API responses. **Spot-check**: after writing `report.md`, grep 3 random CNAME/IP values from the raw API response JSON and confirm they appear character-for-character in the report; any mismatch → regenerate the affected table from raw data.
> 8. **📢 [MUST] Chat-reply template — copy from `report.md`, do NOT recompute**: the final chat summary MUST be assembled by literally copy-pasting from the already-written `report.md`. Use this exact template: `Verdict: <copy from report.md> | S1 Coverage: <copy exact string, e.g. 5/5 (100.0%)> | S2 Coverage: <copy exact string> | Not-Detected: <copy list or None>`. Do NOT perform any arithmetic in chat (never write `1/11 (100%)`, `5/5 (10%)`, `11/1 (10%)`); if chat numbers differ from `report.md`, the chat reply is invalid and must be regenerated.
>
> **[MUST] Coverage-conditioned verdict wording**: if either S1 or S2 coverage is < 100% (any target not effectively probed for any reason — IPv6, plugin failure after remediation, throttling exhausted, etc.), the Verdict MUST use the qualified form: `No exposure risk found among probed items, with N items not detected (see Not-Detected List).` Do **NOT** output a clean `No exposure risk detected for now` when coverage < 100%. Also do NOT report a bare `Exposure risk found` if any hit item is coverage-uncertain — spell out which items are HIT and which are not-detected.

---

## Success Verification Method

See `references/verification-method.md` (includes verification commands and criteria for each step).

## Cleanup

One-off probe tasks (CreateInstantSiteMonitor) end automatically after execution; **no persistent resource cleanup is needed**. This skill is read-only + one-off probes throughout; it does not create site-monitor instances or modify Anti-DDoS configuration.

## Best Practices

1. **First confirm instance existence with `DescribeInstances`**: if none, output "No Anti-DDoS instance found" and stop; do not output "No exposure risk detected for now" (the two are semantically different).
2. Use `DescribeWebRules` for layer-7 (domain/CNAME/origin/port/RsType) and `DescribeNetworkRules` for layer-4 (port/origin/protocol); merge both into the detection checklist.
3. **Fetching probe results MUST use `DescribeSiteMonitorLog` (includes per-probe-point resolved IP, HTTP status code); do NOT use `DescribeSiteMonitorData` — it only returns aggregate availability, without the resolved IP and status code, so it cannot support a verdict.**
4. **Handle cloud-probe failures per the Cloud Probe Error Handling Decision Tree** (Type A service-not-activated → local fallback; Type B plugin parse bug → remediation ladder then local; Type C throttling → backoff then list-as-failed). Never fall back to local unconditionally; on final local fallback, warn that IPv6 origins cannot be probed (mark not detected).
5. **Local HTTP probing must bind Host with `curl --resolve <domain>:<port>:<origin-ip>`** (equivalent to the cloud probe options-json `header:"Host: ..."` field), otherwise the origin's Host-based routing mis-returns 4xx and causes a miss; add `-k` for HTTPS origins with mismatched certs to judge connectivity + status code only.
6. **Probing has execution latency**: after creating a task, poll for logs (recommend every 5s, up to 6 times); keep waiting while `Data` is empty, to avoid fetching too early and getting an empty result.
7. **Pick probe method by onboarding type and protocol**: domain onboarding (layer-7) uses HTTP probing + bound Host header, inspect 2xx/3xx; port onboarding (layer-4) by the `Protocol` field: tcp uses TCP probing (inspect handshake), udp uses UDP probing (inspect whether port unreachable is received). UDP reliability is lower than TCP; note this in the report.
8. **When the origin is a domain (RsType=1), resolve it to an IP with local `dig +short` first** before probing; do not resolve via cloud probe (avoid resolving too many IPs that complicate probing).
9. An origin may have multiple `RealServer`s; probe each one; any directly reachable means S2 hit.
10. **Batch multi-domain/multi-origin processing** (≤10 per batch), control the `CreateInstantSiteMonitor` call rhythm (**baseline 1.5s each**); on throttling, follow **Type C** of the Cloud Probe Error Handling Decision Tree.
11. **Region + probe points**: use `cn-hangzhou` for China mainland instances, `ap-southeast-1` for outside China mainland (do not mix); recommend `--random-isp-city 3` to cover multiple ISPs and reduce single-point misjudgment.
12. **The S1 verdict only compares "does the resolved IP hit the origin IP"**, with no need to identify the Anti-DDoS/scheduler CNAME or Anti-DDoS IP — a resolution landing on the origin IP is exposure, otherwise it went through an intermediate layer. This logic naturally covers ordinary Anti-DDoS, traffic scheduler, using the Anti-DDoS IP directly as an A record, and all such cases.
13. Never persist customer AK/SK, never print credentials.
14. **[MUST] CLI syntax traps (verified; violating them errors out or causes misses)**: (a) the `ddoscoo` series `--page-size` cap is **10** (>10 raises `InvalidPageSize`), paginate to fetch all; (b) the `CreateInstantSiteMonitor` HTTP probe Host header goes in `--options-json '{"header":"Host: <domain>","time_out":5000}'`, there is **no** `host` key; (c) TCP/UDP probe `--address` **takes the IP only** (no port), the port goes in `--options-json '{"port":<port>}'`, writing `ip:port` raises `illegal port`; (d) the created task's TaskId is at `CreateResultList[0].TaskId`, not `Data.TaskId`.
15. **[MUST] DescribeSiteMonitorLog parsing points**: query one `task-id` at a time (comma-separated multiple IDs are unreliable, raise `invalid character`); the returned `Data` is a **JSON string** needing a second parse; the DNS result `ips` field may have a **trailing comma**, so strip and filter empty values after split. **IPv6 origins**: cloud probe `CreateInstantSiteMonitor` **does not support IPv6 targets** — in practice the probe backend forces the IPv4 stack, so even specifying probe points with `IPV6ProbeCount>0` via `--isp-cities` to probe a known-reachable IPv6 still always raises `dial tcp4: no suitable address found`; the `--ipv6 true` probe pool only means the probe has an IPv6 NIC, the probe logic does not recognize IPv6 targets, so the IspCities approach is ineffective for IPv6. IPv6 origins can only fall back to local `nc -6`; mark "not detected" when there is no IPv6 egress (must not count as not exposed).
16. **[MUST] Distinguish "website auto-generated" from "user-manually-created" layer-4 rules**: layer-7 website onboarding auto-generates same-port layer-4 TCP rules by server port (console shows an exclamation mark, not editable); their `RealServers` are **Anti-DDoS forwarding cluster IPs, not the user origin**, and probing them at layer-4 causes false positives, so they must be excluded; **the preferred criterion is the `IsAutoCreate` field returned by `DescribeNetworkRules` — `IsAutoCreate=true` means an auto-generated rule** (the only auto-creation source of a layer-4 rule is layer-7 website onboarding); when `IsAutoCreate` is unavailable, fall back: a layer-4 rule whose `Protocol`+`FrontendPort` matches some website server port under the same instance is auto-generated. **Never decide by "reserved ports 80/443/8080/8443/53"** — outside China mainland, layer-4 Anti-DDoS can legally configure 80/443, and deciding by that causes under-detection. Only probe user-manually-created non-website-port rules at S2 layer-4; list the excluded auto-generated rules separately in the report.
17. **[MUST] Coverage, verdict, and CLI safety**: verdict fields — TCP HIT = `errorCode` empty AND `tcpConnectTime` real; HTTP HIT = 2xx/3xx (see Step 4 S2 verdict rules); never judge HIT by `TotalTime>=0` or `status!="error"`. Coverage — after removing `IsAutoCreate=true`, every remaining origin IP:port must be probed one by one; never skip because a target "looks like a public/test IP"; unprobable targets (e.g. IPv6) are "not detected" and listed separately, never "not exposed"; coverage < 100% must be stated in the conclusion. CLI safety — `aliyun plugin update` only supports the singular `--name`; on `--options-json` plugin parse error, generic RPC (PascalCase `--OptionsJson`) is the verified reliable bypass and keeps the multi-region cloud-probe perspective.
18. **[MUST] Config fetch must be complete + TotalCount check (avoid massive under-collection / under-reporting)**: (a) **never filter `describe-web-rules` with `--instance-ids`** — in practice this under-collects (35 real domains in a region, per-instance with instance-ids returned only 7, missing 80%); query **by region without an instance filter**; (b) `describe-web-rules`/`describe-network-rules` **must read `TotalCount` on page 1, paginate by `ceil(TotalCount/10)` to fetch all, and verify cumulative fetched count == TotalCount**; never fetch only page 1 (page-size cap 10; when TotalCount>10, one page must miss). An under-collected domain **directly causes its exposure surface to be under-reported** (e.g. a real S2-exposed domain never probed because it was not collected) — the most serious detection defect; must be prevented. Also: HTTPS port probing must use `--task-type HTTP` + `--address "https://<ip>:<port>"` (`TaskType` does not support `HTTPS`, raises `TaskType does not exists`).

## Dependencies

The optional reference scripts under `scripts/` require: **Python** >= 3.7 (standard library only — `argparse`, `json`, `math`, `os`, `re`, `subprocess`, `sys`, `time`; no third-party pip packages, so no `requirements.txt`); **Aliyun CLI** >= 3.3.3 with the `ddoscoo` and `cms` plugins installed (the scripts shell out to `aliyun`) and valid credentials configured; **System tools** `dig` (local origin-domain normalization) and, for local IPv6 probing, `nc` with `-6` support.

## Scripts (reference scripts, optional, for determinism and reproducibility)

`scripts/` provides three reference scripts that codify the deterministic, easy-to-get-wrong steps (paged fetching, task construction, log parsing). **Verdict layering**: the scripts only do deterministic fetch/construct/parse; `DNS` and `TCP/UDP` yield deterministic verdicts, but **the `HTTP` exposure verdict is not decided by the script** (it is marked `NEED_AGENT_REVIEW` and emits risk signals for the agent to review — because of interference like "wildcard-reply server / Alibaba Cloud IP block page / probe points skewed to Alibaba Cloud", judging by status code alone would produce false positives). Scripts are optional (the Core Workflow can also be run by hand), but recommended to avoid under-collection/construction errors. All scripts take the session-id via an environment variable: `SKILL_SESSION_ID=<session-id> python3 scripts/xxx.py ...`.

1. **`scripts/fetch_config.py`** — full config fetch (fixes under-collection). Region-wide paged fetch of `describe-instances`/`describe-web-rules`/`describe-network-rules`, **disables `--instance-ids` filtering of web-rules**, does the `TotalCount` completeness check (warns on mismatch), normalizes domain-type origins (local `dig`), splits layer-4 rules by `IsAutoCreate`, and flags wildcard domains and IPv6 origins. Run: `SKILL_SESSION_ID=<sid> python3 scripts/fetch_config.py --regions cn-hangzhou,ap-southeast-1 --out raw-config.json`
2. **`scripts/create_probes.py`** — batch-create cloud probe tasks (fixes construction errors). Codifies HTTPS→`--task-type HTTP`+`https://` prefix, TCP/UDP port into `options-json`, Host header via the `header` field, 1.5s interval, throttling backoff; **forces non-Alibaba-Cloud ISP (Telecom/Unicom/Mobile) probe points** to avoid isp=465 under-reporting Alibaba Cloud ECS origins. Input `tasks.json` (contains `s1_dns`/`s2_http`/`s2_l4`, IPv4 only). Run: `SKILL_SESSION_ID=<sid> python3 scripts/create_probes.py --tasks tasks.json --out taskids.json`
3. **`scripts/parse_probe_log.py`** — parse probe logs (verdict layering). Second-parse the `Data` JSON, strip DNS `ips` trailing commas; `TCP/UDP` yield deterministic HIT/MISS by `errorCode`+`tcpConnectTime` (**disables TotalTime/status**); `HTTP` only emits per-point `http_code` + risk signals (`signal_aliyun_block_page`, `signal_probe_isp_all_alibaba`) and marks `NEED_AGENT_REVIEW` for the agent to review against the SKILL rules. Run: `SKILL_SESSION_ID=<sid> python3 scripts/parse_probe_log.py --taskids taskids.json --out probe-evidence.json`

## Reference Links

| Reference | Contents |
|-----------|----------|
| `references/ram-policies.md` | Required RAM permissions list |
| `references/related-commands.md` | Full CLI command table |
| `references/verification-method.md` | Per-step verification commands and criteria, risk->action mapping |
| `references/acceptance-criteria.md` | Correct/incorrect CLI usage reference |
| `references/cli-installation-guide.md` | Aliyun CLI installation guide |
