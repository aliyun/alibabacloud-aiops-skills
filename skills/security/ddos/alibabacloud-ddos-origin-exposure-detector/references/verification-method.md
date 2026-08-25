# Verification Method — ddos-origin-exposure-detector

## Verification Commands and Decision Criteria for Each Step

### Step 1 Verification: Anti-DDoS Configuration Read Succeeded
```bash
aliyun ddoscoo describe-web-rules --region cn-hangzhou --domain "www.example.com"
```
- Success criteria: Returns a `WebRules` array, where each entry contains `Domain`, `Cname`, `RealServers[].RealServer`, `RealServers[].RsType`, `ProxyTypes[]`.
- Normalization: `RsType=1` (domain-type origin server) → resolve to an IP with local `dig +short <origin domain>`.
- Access type: `ProxyTypes` contains http/https → domain access (Layer 7); only tcp/udp → port access (Layer 4).
- Troubleshooting: An empty array means the domain is not onboarded to Anti-DDoS; for permission errors see ram-policies.md.

### Step 2 Verification: S1 DNS Resolution Check (use SiteMonitorLog for details)

> **[MUST] Data source constraint**: The "resolved IP" used for the S1 decision must come from an independent probe **against the business domain itself** — either the return value of the cloud site-monitor DNS task `DescribeSiteMonitorLog`, or the output of local `dig +short <business domain>`. It is **strictly forbidden** to treat the `Cname` field of `DescribeWebRules` (the Anti-DDoS CNAME configuration) or the normalized IP from `RealServers[].RealServer` (the origin IP) as the "resolved IP" and feed it into the decision or report. When the business domain has no resolution record, explicitly mark it as "No resolution"; do not substitute anything for it.
> **Report display**: At least four columns — `Business Domain` / `Origin IP (RsType note)` / `Anti-DDoS CNAME configuration` / `Actual resolved IP`, with the decision column directly corresponding to "actual resolved IP ∩ origin IP".

```bash
# Create a DNS site-monitor probe
aliyun cms create-instant-site-monitor --address "www.example.com" --task-type "DNS" --task-name "ddos-dns-check" --random-isp-city 3
# Poll for per-probe-point details (once every 5s, up to 6 times; keep waiting if Data is empty)
aliyun cms describe-site-monitor-log --task-ids "<TaskId>" --metric-name "ProbeLog"
```
- Success criteria: CreateInstantSiteMonitor returns `Success=true` and contains a TaskId; the `Data` of DescribeSiteMonitorLog returns per-probe-point logs (including the resolved IP).
- Decision: If the final IP resolved by any probe point hits this domain's origin IP (resolved IP ∩ origin IP ≠ empty) → S1 matched; if all resolution results fall on non-origin addresses (Anti-DDoS / scheduler / WAF / CDN) → not matched. There is no need to identify the Anti-DDoS CNAME / Anti-DDoS IP; this naturally covers scenarios such as standard Anti-DDoS, traffic scheduler, and using the Anti-DDoS IP directly as an A record.
- Note: **Do not use `describe-site-monitor-data`**, it only returns aggregated availability rates and cannot obtain the resolved IP.

### Step 3 Verification: S2 Direct Origin Probe (by access type)
```bash
# Domain access (Layer 7): HTTP + Host header ([MUST] use the header field of options-json, not a host key)
aliyun cms create-instant-site-monitor --address "http://<origin-ip>:<port>" --task-type "HTTP" --task-name "ddos-origin-http" --random-isp-city 3 --options-json '{"header":"Host: www.example.com","time_out":5000}'
# Port access (Layer 4)-TCP: [MUST] --address only takes the IP (no port); the port goes in the port field of options-json
aliyun cms create-instant-site-monitor --address "<origin-ip>" --task-type "TCP" --task-name "ddos-origin-tcp" --random-isp-city 3 --options-json '{"port":<port>,"time_out":5000}'
# Port access (Layer 4)-UDP: same as above, IP-only + port
aliyun cms create-instant-site-monitor --address "<origin-ip>" --task-type "UDP" --task-name "ddos-origin-udp" --random-isp-city 3 --options-json '{"port":<port>,"time_out":5000}'
# Fetch details ([MUST] TaskId is at CreateResultList[0].TaskId; query only one task-id at a time, comma-separated multiple IDs are unreliable)
aliyun cms describe-site-monitor-log --task-ids "<TaskId>" --metric-name "ProbeLog"
```
- Decision (domain access HTTP): Any probe point returns **2xx/3xx** on direct connection → S2 matched (real exposure); returns 4xx/5xx or fails → do not judge as S2, may annotate as "suspected partially reachable".
- Decision (port access TCP): Any probe point completes the TCP handshake successfully → S2 matched; all fail → not matched.
- Decision (port access UDP): A probe point does not receive ICMP port unreachable (treated as reachable) → S2 matched; explicitly unreachable → not matched. UDP has no handshake, so the conclusion has lower confidence than TCP.

## Scenario -> Recommended Action Mapping (with official help docs)

| Matched Scenario | Decision Signal | Recommended Action | Alibaba Cloud Help Doc |
|---------|---------|---------|--------------|
| S1 DNS not pointing to Anti-DDoS | Probe point resolves to the origin IP, not pointing to the Anti-DDoS CNAME | Switch the domain CNAME to the Anti-DDoS CNAME (`*.aliyunddos*.com`); lower the TTL first before switching; delete leftover A records | Defend a website against DDoS attacks (onboarding + switching DNS/CNAME): https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/getting-started/protect-website-services ; Best practices for onboarding configuration: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/best-practices-for-adding-a-service-to-an-anti-ddos-pro-or-anti-ddos-premium-instance |
| S2 origin directly reachable from the public internet | HTTP direct connection returns 2xx/3xx or TCP handshake succeeds | Configure access control on the origin, allowing only the Anti-DDoS back-to-origin IP ranges to access the business port; apply the same configuration for cross-cloud/cross-account origins; replace the origin IP if necessary | Solution for origin IP exposure: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/handle-exposure-of-the-origin-ip-address ; How to set up origin protection after onboarding to DDoS Anti-DDoS (back-to-origin IP whitelist): https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/configure-acls-for-the-origin-server |

> Help doc links may change as the Alibaba Cloud documentation structure is adjusted; if a link is broken, you can search "DDoS Anti-DDoS origin protection / origin IP exposure" in the Alibaba Cloud Help Center https://help.aliyun.com to get the latest documentation.

## Final Conclusion Output Format

Risk found (must include official help doc links for reducing the risk + a ticket consultation note):
```
[Verdict] Exposure risk found
[Matched Scenarios]
  - S1 DNS not pointing to Anti-DDoS: www.example.com probe points resolve to origin 47.x.x.x, not pointing to the Anti-DDoS CNAME
  - S2 origin directly reachable: domain access, cloud site-monitor directly connects to 47.x.x.x:443 from 3 nodes and returns 200
[Recommended Actions] ... (see the table above)
[Reference Docs (risk remediation)]
  - Solution for origin IP exposure: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/handle-exposure-of-the-origin-ip-address
  - How to set up origin protection after onboarding to DDoS Anti-DDoS: https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/use-cases/configure-acls-for-the-origin-server
  (Please provide the corresponding links according to the actually matched scenarios, see the mapping table above)
[Note] The above is an automated detection result. If you have questions about the verdict, you can submit an Alibaba Cloud ticket for consultation: https://selfservice.console.aliyun.com/ticket/createIndex
```

No risk (also include a ticket consultation note):
```
[Verdict] No exposure risk detected for now
(All configured domains point to the Anti-DDoS CNAME, and the origin IP cannot be directly connected from the public internet)
[Note] This detection is based on the current configuration and probe perspective (cloud site-monitor/local). If you have questions about the verdict, you can submit an Alibaba Cloud ticket for consultation: https://selfservice.console.aliyun.com/ticket/createIndex
```

## Report Template (report.md structure)

The final `report.md` (written to the outputs directory per SKILL.md Step 5) must contain the following sections. Do not omit or paraphrase the ticket URL.

```markdown
# Anti-DDoS Proxy Origin Exposure Detection Report

## 1. Verdict
Exposure risk found  |  No exposure risk detected for now
(if any item was not effectively probed: "No exposure risk found among probed items, with N items not detected")

## 2. Scope & Config (per instance, expanded)
- Instance <id> / Region ... : layer-7 domains N, layer-4 manual rules M (auto-created X excluded)

## 3. S1 — DNS resolution check (layer-7 only)
| Business Domain | Origin IP (RsType) | Anti-DDoS CNAME Config | Actual Resolution Result IP | Verdict |
(three config/probe columns kept strictly separate; empty resolution = "no resolution", never substituted)

## 4. S2 — Origin direct-connect
| Onboarding | Origin IP:Port | Protocol | Probe (cloud/local) | Status/Result | Verdict |
(HTTP 2xx/3xx = HIT; 4xx/5xx = not exposed/uncertain, never HIT)

## 5. Not-Detected List (items NOT effectively probed — separate from hit/miss)
| Origin IP:Port / Domain | Reason | Suggested follow-up |

## 6. Coverage (computed per stage, never mixed)
- S1: probed X / total Y (Z%)
- S2: probed X / total Y (Z%)

## 7. Recommended Actions & Reference Docs
(per matched scenario, see the mapping table above)

## Note
This is an automated detection result. If you have doubts about the conclusion, you may submit an Alibaba Cloud ticket: https://selfservice.console.aliyun.com/ticket/createIndex
```
