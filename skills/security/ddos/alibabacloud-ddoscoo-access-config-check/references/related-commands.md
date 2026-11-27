# Related CLI Commands — alibabacloud-ddoscoo-access-config-check

All cloud commands use `aliyun` CLI plugin mode (lowercase, hyphen-separated actions). Every cloud API call
carries the double-quoted UA below. Where `{session-id}` and `{skill-version}` come from, and the rule to STOP
rather than invent them, are defined once in the Observability section of SKILL.md:

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
```

| Product | CLI command | API | Version | Used for |
|---------|-------------|-----|---------|----------|
| ddoscoo | `aliyun ddoscoo describe-instances` | DescribeInstances | 2020-01-01 | Instance existence check + the Anti-DDoS IPs (`Ip`), needed to tell an A record to Anti-DDoS from an A record to the origin |
| ddoscoo | `aliyun ddoscoo describe-web-rules` | DescribeWebRules | 2020-01-01 | Per domain: `Cname` (C1/C3), `CertName` / `UserCertName` / `CertRegion` (C2 — the key that joins to `cas`), `ProxyTypes[]` protocol + ports (C4), `RealServers[]` with `RsType` (C1/C3 comparison values) |
| ddoscoo | `aliyun ddoscoo describe-scheduler-rules` | DescribeSchedulerRules | 2020-01-01 | Traffic-scheduler rules: `RuleName`, `RuleType`, `Cname`, `Rules[]{Type,Value,ValueType,Priority,Status,RestoreDelay,Line}` (C1/C3/C4 scheduler handling) |
| ddoscoo | `aliyun ddoscoo describe-domains` | DescribeDomains | 2020-01-01 | Auxiliary: list of configured protected domains |
| Cms | `aliyun cms describe-site-monitor-isp-city-list` | DescribeSiteMonitorISPCityList | 2019-01-01 | Select mainland + overseas vantage points. **Flat dotted keys**: `Country.en` / `Country.zh_CN` / `CityName.zh_CN` / `IspName.en` / `Region.en` / `Area.en`, plus `City`, `Isp`, `IPV4ProbeCount`. The bare `Country` is the numeric **code** (e.g. `629`), not an object |
| Cms | `aliyun cms create-instant-site-monitor` | CreateInstantSiteMonitor | 2019-01-01 | One-off `DNS` (C1) and `HTTP` (C4) probes |
| Cms | `aliyun cms describe-site-monitor-log` | DescribeSiteMonitorLog | 2019-01-01 | Per-probe-point detail (`--metric-name ProbeLog`). **Primary DNS source for C1/C3**: `DNSRaw` is the whole ordered answer section, pipe-separated (`a.com CNAME b.aliyunddos0018.com TTL 600\|b… A 1.2.3.4 TTL 10\|any: type 41 string (…)\|` — skip the OPT pseudosection), plus `cnames`, `ips` and `dnsServer` per point. **Always pass `--start-time`/`--end-time`**: without a window the service returns only its own recent range, so older tasks come back with empty `Data` and get mis-read as `NOT_DETECTED` |
| cas (**required for C2**) | `aliyun cas list-user-certificate-order` | ListUserCertificateOrder | 2020-04-07 | The bound certificate's expiry (`EndDate`, `Expired`) — C2's only data source |
| cas (**required for C2**) | `aliyun cas get-user-certificate-detail` | GetUserCertificateDetail | 2020-04-07 | Fallback by `CertId` when the list record has no `EndDate`: `EndDate`, `Expired`, `StartDate`, `Name`, `CommonName`, `Sans` |

API references:
[DescribeWebRules](https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/developer-reference/api-ddoscoo-2020-01-01-describewebrules) ·
[DescribeSchedulerRules](https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/developer-reference/api-ddoscoo-2020-01-01-describeschedulerrules) ·
[DescribeCerts](https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/developer-reference/api-ddoscoo-2020-01-01-describecerts) ·
[ddoscoo endpoints](https://help.aliyun.com/zh/anti-ddos/anti-ddos-pro-and-premium/developer-reference/api-ddoscoo-2020-01-01-endpoint) ·
[CreateInstantSiteMonitor](https://help.aliyun.com/zh/cms/cloudmonitor-1-0/developer-reference/api-cms-2019-01-01-createinstantsitemonitor) ·
[DescribeSiteMonitorLog](https://help.aliyun.com/zh/cms/cloudmonitor-1-0/developer-reference/api-cms-2019-01-01-describesitemonitorlog) ·
[DescribeSiteMonitorISPCityList](https://help.aliyun.com/zh/cms/cloudmonitor-1-0/developer-reference/api-cms-2019-01-01-describesitemonitorispcitylist) ·
[GetUserCertificateDetail](https://help.aliyun.com/en/ssl-certificate/developer-reference/api-cas-2020-04-07-getusercertificatedetail)

## Key parameter notes

### ddoscoo describe-web-rules
- `--region`: `cn-hangzhou` = Anti-DDoS Proxy (new BGP / mainland); `ap-southeast-1` = Anti-DDoS Premium
  (outside mainland / international edition). One account may hold both — query each separately.
- `--domain`: narrows to one domain; safe to use.
- **`--instance-ids`: [MUST] never use it to filter.** Verified under-collection (35 real domains in a region,
  per-instance filtering returned 7 — 80% missing). The API already returns all website rules of the region.
- `--page-size` 1–10, `--page-number`: read `TotalCount` on page 1, fetch `ceil(TotalCount/10)` pages, verify
  the cumulative count equals `TotalCount`.
- Returns: `WebRules[].Domain`, `.Cname`, `.CertName`, `.UserCertName`, `.CertRegion`, `.ProxyTypes[]`
  (`ProxyType` + `ProxyPorts[]`), `.RealServers[]` (`RealServer` + `RsType`: 0=IP, 1=domain), `TotalCount`.
- **`CertExpireTime` is documented as *not currently used*** — never read it as an expiry date.

### ddoscoo describe-scheduler-rules
- `--page-size` is **required**; there is no `RegionId` request parameter, but `--region` is still needed for
  endpoint routing.
- Returns `TotalCount`, `SchedulerRules[].{RuleName, RuleType, Cname, Rules[], Param}`.
- `RuleType`: 2 tiered protection / 3 overseas acceleration / 5 CDN interaction / 6 cloud-product interaction / 8 secure acceleration.
- `Rules[].ValueType`: 1 Anti-DDoS IP / 2 cloud resource / 3 acceleration line / 5 CDN domain / 6 cloud product / 8 secure acceleration;
  `Rules[].Status`: 0 inactive / 1 active; `Rules[].Type`: `A` | `CNAME`.
- **No `Domain` field** — rules are domain-agnostic; bind them to domains by observed DNS.

### cms describe-site-monitor-isp-city-list
- `--ipv4 true` / `--ipv6 true`, `--view-all true` (all points; `false` = currently available only),
  `--isp` / `--city` (fuzzy filters).
- Returns `IspCityList.IspCity[]`: `City`, `Isp` (IDs), `CityName.{en,zh_CN}`, `Region.en`,
  `Country.{en,zh_CN}`, `IspName.en`, `IPV4ProbeCount`, `IPV6ProbeCount`, `IPPool`.
- Mainland vs overseas is decided by `Country`; **no overseas city/ISP code is published in the docs, so
  never hardcode one** — filter at runtime and require `IPV4ProbeCount > 0`.
- Mainland real-user ISPs: Telecom `132`, Unicom `232`, Mobile `5`. Alibaba-Cloud-internal points (`isp=465`)
  do not represent user access — avoid them for C4.

### cms create-instant-site-monitor
- `--address`: for `DNS` a bare domain (`www.example.com`); for `HTTP` a full URL
  (`https://www.example.com/` or `http://www.example.com:8080/`); for `TCP`/`UDP` **the IP only, no port**
  (a port in the address raises `illegal port` — the port goes into `--options-json`).
- `--task-type`: `HTTP` / `PING` / `TCP` / `UDP` / `DNS`. **There is no `HTTPS`** — probing 443 means
  `--task-type HTTP` with an `https://` address prefix.
- `--task-name`: 4–100 characters; sanitize to `[a-z0-9-]`.
- `--isp-cities`: JSONArray `[{"city":"357","isp":"132","type":"IDC"}]`; `type` = `IDC` | `LASTMILE`.
  Mutually exclusive with `--random-isp-city` — setting `--isp-cities` disables the random pick.
- `--options-json`: wrap the whole JSON in **single quotes**. HTTP headers go in the `header` key
  (`'{"header":"Host: www.example.com","time_out":5000}'`); **there is no `host` key**. For this skill's C4
  probes the address already is the domain, so only `'{"time_out":5000}'` is needed.
- `--agent-group`: `PC` (fixed line, default) / `MOBILE`.
- Returns `CreateResultList[0].TaskId` — **not** `Data.TaskId`.

### cms describe-site-monitor-log
- `--task-ids`: **one TaskId per call**; comma-separated IDs parse unreliably and raise `invalid character`.
- `--metric-name ProbeLog` (the only supported value). Do **not** use `describe-site-monitor-data` — it
  returns aggregate availability without resolved IPs or status codes.
- `--isp` / `--city` / `--filter` (e.g. `TotalTime>100`) / `--start-time` / `--end-time` / `--length` (1–1440)
  / `--next-token`.
- Returns `Data` as a **JSON string** (parse twice). Documented per-point fields: `HTTPResponseCode`,
  `TotalTime`, `HTTPDNSTime`, `SSLConnectTime`, `tcpConnectTime`, `HTTPConnectTime`, `errorCode` (integer —
  **no `errorMessage` field is documented**), `ips` (may carry a trailing comma), `isp`/`ispCN`/`ispEN`,
  `city`/`cityCN`/`cityEN`, `countryCN`/`countryEN`, `provinceCN`/`provinceEN`, `localDns`, `suourceIp`
  (official spelling), `redirectCount`, `redirectTime`, `timestamp`, `taskId`.
- Probes have execution latency: poll every 5s, up to 6 times, while `Data` is empty.

### cas list-user-certificate-order (required for C2)
- `--current-page`, `--show-size`, plus optional `--order-type`, `--status`, `--keyword`.
- Per certificate: `EndDate`, `StartDate`, `Expired`, name/domain fields. Field spellings vary across
  versions, so read them defensively and report `NOT_DETECTED` rather than guessing.
- `DescribeUserCertificateList` (2018-07-13) is **deprecated** — do not use it.

## Local commands (ProbeMode=local; C1/C3 and the C4 fallback only — C2 never runs locally)

Zero cost, no service activation; the limitation is a single network egress.

### C1 / C3 — resolution and chain walking (`dig`)
```bash
dig +short www.example.com CNAME              # first CNAME hop
dig +short www.example.com A                  # final A records (chain lines may appear too)
dig +short www.example.com AAAA               # IPv6
dig @223.5.5.5 +short www.example.com CNAME   # second resolver view: exposes per-line / split-horizon records
dig +short NS example.com                     # authoritative DNS provider
```
- Walk hop by hop (max 8, with loop detection); compare each hop normalized (lowercase, trailing dot stripped)
  against the expected CNAME set.
- Different final IPs across resolvers on a CDN/GSLB domain is **normal**; a different *first hop* is not.

### C2 — no local command at all
C2 reads the **bound** certificate's expiry from `cas` (see above); this skill does not read the served
certificate, so there is no `openssl` step, no hostname-match check and no chain-depth check. Adding one back
would re-widen a scope the customer deliberately narrowed.

### C4 — single-egress health (`curl`)
```bash
curl -sS -k -o /dev/null --connect-timeout 6 --max-time 12 \
  -w '%{http_code}|%{time_namelookup}|%{time_connect}|%{time_appconnect}|%{time_starttransfer}|%{time_total}\n' \
  "https://www.example.com/"
```
- Success = HTTP code 2xx/3xx. `-k` keeps a TLS problem from aborting the health probe; C2 does not read the
  served certificate, so `-k` cannot mask a C2 finding.
- Label the result `LOCAL_SINGLE_EGRESS` and set the mainland-vs-overseas comparison to `NOT_DETECTED`.

### Origin normalization (comparison values only — this skill never probes origins)
```bash
dig +short <origin-domain>     # RsType=1 domain-type origin -> IPs, for C1/C3 intersection checks
```
