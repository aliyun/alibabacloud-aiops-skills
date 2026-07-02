# Export Workflow

## Overview

Per-domain basis: for each domain to be exported, execute 16 describe APIs serially (multiple domains can be processed in parallel), then assemble the return values into YAML and write to disk.

> **!! Critical Pitfall: `--domain` vs `--domains` Inconsistency** -- using the wrong form causes `Error: unknown flag`.
>
> **`--domain` (singular)**: `describe-domain-resource` / `describe-web-rules` / `describe-l7-rs-policy` / `describe-l7-us-keepalive` / `describe-headers` / `describe-web-cc-rules-v2` / `describe-cdn-linkage-rules` / `describe-l7-global-rule`
>
> **`--domains` (plural)**: `describe-cname-reuses` / `describe-domain-cc-protect-switch` / `describe-web-cc-protect-switch` / `describe-web-precise-access-rule` / `describe-web-area-block-configs` / `describe-web-cache-configs`
>
> **Mnemonic**: Resources (resource/web-rules/headers/keepalive/policy) use singular; switches/rule collections (cc/precise/area/cache/cname-reuse) use plural.

## Step 1: Determine Domain List

Based on the user's selected scope, build the list of domains to export:

```bash
# Full account / entire instance (returns all domains in one call, CLI does not support pagination)
aliyun ddoscoo describe-domains --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Filter by instance, used when detailed configuration is needed (supports pagination)
aliyun ddoscoo describe-domain-resource --instance-ids '<InstanceId>' --page-number 1 --page-size 10 --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

> `describe-domains` returns the full domain list in one call; the CLI does not support `--page-number` / `--page-size`, so no pagination loop is needed.
> `describe-domain-resource` has a `--page-size` **maximum of 10** (exceeding causes `InvalidPageSize`); when pagination is needed, increment `page-number` until the response is empty.

## Step 2: Call 16 Describe APIs Per Domain

For each domain `<D>`, execute:

### 2.1 Domain Entity (includes HTTPS/TLS/OCSP/Http2 flags/GM Cert/BlackList/WhiteList)

```bash
aliyun ddoscoo describe-web-rules --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Returns `WebRules[0]` containing fields:
- `Domain` / `Cname` / `RealServers[].{RealServer,RsType}` / `ProxyEnabled` / `ProxyTypes[].{ProxyType,ProxyPorts}`
- HTTPS: `CertName` / `CertRegion` / `UserCertName` / `SslProtocols` / `SslCiphers` / `Ssl13Enabled` / `CustomCiphers` / `Tls13CustomCiphers` / `OcspEnabled` / `Http2Enable` / `Http2HttpsEnable` / `Https2HttpEnable`
- GM (SM2): `GmCert.{CertId,GmEnable,GmOnly}` (!! `GmCert.CertId` returns the RSA certificate ID, **not** the SM2 GM certificate ID; the SM2 certificate must be obtained via Step 2.16 `describe-gm-cert-list`. The write actions `config-gm-cert` / `config-gm-cert-enable` / `config-gm-cert-only` rely on the OpenAPI fallback edge case when the plugin doesn't yet declare them)
- WAF: `WafProtectionEnable`
- IP Blacklist/Whitelist: `BlackList` / `WhiteList` (WhiteList is not returned when the array is empty)
- CC Basics: `CcEnabled` / `CcRuleEnabled` / `CcTemplate` (!! `CcEnabled` and `CcRuleEnabled` are synonymous boolean values of `CcEnable` and `CcCustomRuleEnable` returned by `describe-web-cc-protect-switch`; use the integer values from `describe-web-cc-protect-switch` as the authoritative source when exporting)
- Punishment status: `PunishStatus` / `PunishReason`

> **!! InstanceIds is not returned by this API**: `InstanceIds` is returned by `describe-domain-resource` from Step 1, not by `describe-web-rules`. The two APIs also return `RealServers` in different formats:
> - `describe-domain-resource`: flat string array `["1.2.3.4"]` + separate `RsType` field + `HttpsExt` (JSON string)
> - `describe-web-rules`: object array `[{RealServer, RsType}]` + `Http2Enable` / `Http2HttpsEnable` / `Https2HttpEnable` (separate bool fields)
>
> When exporting, merge the return values from both APIs: get `InstanceIds` from `describe-domain-resource`, and get the full configuration fields from `describe-web-rules`.

> **!! IP Whitelist field is returned on demand**: `describe-web-rules` returns both `BlackList` and `WhiteList`, but `WhiteList` only appears in the response when the domain has a whitelist configured (the field is absent when the array is empty). When exporting, check whether the `WhiteList` field exists: use its value if present, otherwise treat it as `[]`.
>
> **!! YAML placement**: Although `BlackList` / `WhiteList` originate from `describe-web-rules` (Step 2.1), they belong under the **`security.ip_blackwhite`** node in YAML (`security.ip_blackwhite.black_list` / `security.ip_blackwhite.white_list`), **not** as top-level domain fields. Make sure to place them under `security.ip_blackwhite` during assembly.

> Note: The `HttpsExt` field is returned by `describe-domain-resource` as a JSON string (e.g., `"{\"Https2http\":0,\"Http2\":0,\"Http2https\":0}"`), but `describe-web-rules` already expands `Http2Enable` / `Http2HttpsEnable` / `Https2HttpEnable` into separate bool fields. During import, these must be reassembled back into the `HttpsExt` JSON.

### 2.2 Back-to-Origin Policy

```bash
aliyun ddoscoo describe-l7-rs-policy --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `ProxyMode` (ip_hash/rr/least_time), `UpstreamRetry`, `Attributes[].{RealServer, Attribute.{Weight,ConnectTimeout,ReadTimeout,SendTimeout,Mode,MaxFails,FailTimeout}}`, `RsAttrRwTimeoutMax`.

> !! This API does **not accept** the `--instance-id` parameter; it relies solely on `--domain` for unique identification.

### 2.3 Keepalive

```bash
aliyun ddoscoo describe-l7-us-keepalive --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `RsKeepalive.{Enabled, KeepaliveTimeout, KeepaliveRequests, DsKeepaliveTimeout}`.

### 2.4 Back-to-Origin Headers

```bash
aliyun ddoscoo describe-headers --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `CustomHeader.Headers` (user-defined key-value pairs) + `EmbeddedHeaders` (system-embedded switches: WL-Proxy-Client-IP / Web-Server-Type / X-Client-IP / X-Forwarded-Proto / X-True-IP).

### 2.5 CNAME Reuse

```bash
aliyun ddoscoo describe-cname-reuses --domains '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `CnameReuses[0].{Cname, Enable}`.

### 2.6 CC/AI Protection Switches and Templates

```bash
aliyun ddoscoo describe-web-cc-protect-switch --domains '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `ProtectSwitchList[0]` contains
- `CcGlobalSwitch` / `CcEnable` / `CcTemplate`
- `CcCustomRuleEnable` / `PreciseRuleEnable` / `RegionBlockEnable` / `BlackWhiteListEnable`
- AI: `AiMode` / `AiTemplate` / `AiRuleEnable`

### 2.7 CC Custom Rules (`--domain` singular)

```bash
aliyun ddoscoo describe-web-cc-rules-v2 --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `WebCCRules[].{Name, Owner, Expires, RuleDetail.{Action, Condition[].{Field,MatchMethod,Content}, RateLimit.{Target,Interval,Threshold,Ttl}, Statistics, StatusCode}}`.

> **!! Smart policy filtering**: Among the rules returned by `describe-web-cc-rules-v2`, those with `Name` starting with `smartcc_` are system-generated intelligent protection policies (produced by AI integration). **These must be filtered out during export** -- only retain user-defined rules where `Owner=manual` or the name does not start with `smartcc_`. Smart policies are automatically managed by the AI protection module and cannot be manually replayed.

### 2.8 Precise Access Control

```bash
aliyun ddoscoo describe-web-precise-access-rule --domains '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `PreciseAccessConfigList[0].RuleList[].{Name, Action, Owner, Expires, ExpirePeriod, ConditionList[].{Field,MatchMethod,Content}}`.

### 2.9 Region Blocking

```bash
aliyun ddoscoo describe-web-area-block-configs --domains '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `AreaBlockConfigs[0].RegionList[].{Region, Block}`. **When exporting, only retain items with `Block=1`** to avoid excessively large YAML files (the default lists 200+ regions worldwide).

### 2.10 Static Page Cache (`--domains` plural)

```bash
aliyun ddoscoo describe-web-cache-configs --domains '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `DomainCacheConfigs[0].{Enable, Mode, CustomRules[]}`.

### 2.11 CDN Linkage Scheduling

```bash
aliyun ddoscoo describe-cdn-linkage-rules --domain '<D>' --page-number 1 --page-size 10 --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `SchedulerRules[0].{CdnLinkageEnable, CdnLinkageRule.{Cname, RuleName, Param.{ParamType, ParamData.{Domain,Cname,AccessQps,UpstreamQps}}, Rules[].{Type,Value,Priority,ValueType}}}`.

> `Rules[].Type`: `A` (IP) or `CNAME` (domain). `ValueType`: `1`=Anti-DDoS IP / `2`=Cloud resource IP / `3`=Accelerated route IP / `5`=CDN linkage / `6`=Cloud product linkage. CDN linkage scenarios always use `Type=CNAME, ValueType=5`.

### 2.12 Global Protection Level and Switches

```bash
# Get the global protection master switch and protection level
aliyun ddoscoo describe-domain-security-profile --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `Result[0].{GlobalEnable, GlobalMode}`.
- `GlobalEnable`: Global protection master switch (true/false)
- `GlobalMode`: Protection level (`hard` / `default` / `weak`)

> **Edge case -- plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddoscoo` 0.x): if the call above errors with `unknown command` or with `is not a valid api` for this action, fall back to the OpenAPI route per the Command Template's edge-case block in [acceptance-criteria.md](acceptance-criteria.md) (Section 2, "Plugin Mode (Default) vs OpenAPI Fallback").

### 2.13 Global Protection Rule Details (`--domain` singular)

```bash
aliyun ddoscoo describe-l7-global-rule --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `GlobalRules[].{RuleId, RuleName, Description, Action, ActionDefault, Enabled}`.

> **Export strategy (non-default only)**: Only export global protection rules that deviate from system defaults (`Action != ActionDefault` or `Enabled=0`). Reason: `RuleId` contains a server-side dynamic hash that is unstable across domain instances; system default rules do not need to be replayed (they are automatically applied when a domain is created). Only user-customized rule differences need to be recorded. Export retains `RuleId` + `Action` + `Enabled`; import replays by `RuleId`.

### 2.14 Cookie Settings

```bash
aliyun ddoscoo describe-l7cc-cookie --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `AliyungfTc` (0/1), `CookieSecure` (0/1), `MaxAgeEnable` (0/1), `MaxAge` (string).

> **Edge case -- plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddoscoo` 0.x): if the call above errors with `unknown command` or with `is not a valid api` for this action, fall back to the OpenAPI route per [acceptance-criteria.md](acceptance-criteria.md) (Section 2).

### 2.15 Mutual Authentication (mTLS) Configuration

```bash
aliyun ddoscoo describe-l7-mutual-auth-conf --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `Enable` (0/1), `CertIssuer`, `CertId`, `Cert`.

> The corresponding write API is `config-l7-mutual-authentication`.
>
> **Edge case -- plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddoscoo` 0.x): if the call above errors with `unknown command` or with `is not a valid api` for this action, fall back to the OpenAPI route per [acceptance-criteria.md](acceptance-criteria.md) (Section 2).

### 2.16 GM (SM2) Certificate List

```bash
aliyun ddoscoo describe-gm-cert-list --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Fields: `GmCertList[].{CertId, CertName, Algorithm, Domain, DomainMatchCert, Issuer, StartDate, EndDate}`.

> **!! The `GmCert.CertId` from `describe-web-rules` is the RSA certificate ID, not the SM2 GM certificate ID**. GM certificates (SM2 algorithm) must be obtained via this API. When exporting:
> - If `GmCertList` is non-empty, take the SM2 certificate `CertId` where `DomainMatchCert=true` and write it to YAML `proxy.gm_cert.cert_id`
> - If multiple matching SM2 certificates exist, take the first one or let the user choose
> - `GmEnable` / `GmOnly` are still obtained from `describe-web-rules`'s `GmCert`
>
> **Edge case -- plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddoscoo` 0.x): if the call above errors with `unknown command` or with `is not a valid api` for this action, fall back to the OpenAPI route per the Command Template's edge-case block in [acceptance-criteria.md](acceptance-criteria.md) (Section 2 / Section 6).

## Step 3: Assemble YAML (v2.0 Four-Section Structure)

Following the schema defined in [yaml-schema.md](yaml-schema.md), merge the above return values into a single YAML tree organized by **proxy / client / server / security** sections. **Key transformation rules**:

1. **proxy.protocols**: `ProxyTypes[].{ProxyType,ProxyPorts}` -> `[{protocol, ports}]`
2. **proxy.ssl_cert / proxy.tls / proxy.gm_cert**: split from `describe-web-rules` fields
3. **proxy.http2 / proxy.http2https**: `Http2Enable`/`Http2HttpsEnable` bool -> 0/1 integer
4. **server.https2http**: `Https2HttpEnable` bool -> 0/1 (HTTP back-to-origin switch, belongs under server not proxy)
5. **client.ds_keepalive_timeout**: from `describe-l7-us-keepalive` -> `RsKeepalive.DsKeepaliveTimeout`
6. **server.keepalive**: `Enabled` / `KeepaliveTimeout` / `KeepaliveRequests` from the same API belong under server
7. **server.headers**: `CustomHeader.Headers` (including traffic marker variables `$ReqClientIP` / `$ReqVar_*`) + `EmbeddedHeaders` merged
8. **server.proxy_mode / server.attributes**: from `describe-l7-rs-policy` (timeouts include ConnectTimeout / ReadTimeout / SendTimeout)
9. **security.ip_blackwhite**: `BlackList`/`WhiteList` originate from `describe-web-rules` but belong under the security section
10. **RegionList filtering**: only retain items with `Block=1`
11. **Empty field omission**: all empty arrays, empty dicts, and switches with `Enable=0` are omitted by default to reduce noise (export with `--include-defaults` flag to retain all fields)
12. **CC rule smartcc_ filtering**: discard all system smart policies where `Name` starts with `smartcc_`; only retain user-created rules
13. **Global protection rules full export**: all rules are recorded without incremental filtering

## Step 4: Write to File

Each domain generates a separate YAML file with the naming convention: `{region}-{domain}-{YYYYMMDD}.yaml`

Example: `cn-hangzhou-api.example.com-20260617.yaml`

Use the `Write` tool to save to disk. Output a `file://` link to the user when complete.

## Error Handling

| Error | Cause | Resolution |
| ----- | ----- | ---------- |
| `Error: unknown flag: --domain` | API uses `--domains` (plural) | See the "`--domain` vs `--domains`" pitfall table at the top of this document |
| `InvalidPageSize` | `--page-size` exceeds API limit | `describe-domain-resource` max 10, `describe-instances` max 50 |
| `Throttling.User` | QPS rate limiting | Add 200ms sleep between domains |
| `domain.NotExists` | Domain has been deleted | Skip the domain and log a warning |
| `Permission denied` | RAM lacks permissions | Trigger the `ram-permission-diagnose` skill |

## Performance Recommendations

- A single API call takes approximately 1.0s on average (including CLI startup + network RTT)
- Exporting a single domain takes approximately 10-16s (16 serial calls)
- For multiple domains, process in batches of 5 domains in parallel (to avoid triggering QPS rate limiting)
- Estimated total time for 100 domains: approximately 4-5 minutes

## Output Example

See [yaml-example.yaml](yaml-example.yaml) for a complete YAML example.
