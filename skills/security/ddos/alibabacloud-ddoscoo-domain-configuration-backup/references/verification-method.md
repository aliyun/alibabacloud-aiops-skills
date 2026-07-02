# Verification Method

After import completes, perform the following verification steps for each target domain.

## Step 1: Basic Configuration Verification

```bash
aliyun ddoscoo describe-web-rules --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>
```

Compare the following key fields between the YAML and the API response:

| YAML Path | API Field | Match Rule |
|-----------|-----------|------------|
| `server.real_servers[].address` | `WebRules[0].RealServers[].RealServer` | Exact match |
| `proxy.protocols` | `WebRules[0].ProxyTypes[].{ProxyType,ProxyPorts}` | Set match (ignore order) |
| `proxy.ssl_cert.cert_name` | `WebRules[0].CertName` | Exact match |
| `proxy.tls.ssl_protocols` | `WebRules[0].SslProtocols` | Exact match |
| `proxy.tls.ssl13_enabled` | `WebRules[0].Ssl13Enabled` | Exact match |
| `proxy.tls.ssl_ciphers` | `WebRules[0].SslCiphers` | Exact match |
| `proxy.ocsp_enabled` | `WebRules[0].OcspEnabled` | Exact match |
| `proxy.http2` | `WebRules[0].Http2Enable` | bool -> 0/1 |
| `proxy.http2https` | `WebRules[0].Http2HttpsEnable` | bool -> 0/1 |
| `server.https2http` | `WebRules[0].Https2HttpEnable` | bool -> 0/1 |
| `security.ip_blackwhite.black_list` | `WebRules[0].BlackList` | Set match |
| `security.ip_blackwhite.white_list` | `WebRules[0].WhiteList` | Set match (empty array may not be returned) |

## Step 2: Back-to-Origin Policy Verification

```bash
aliyun ddoscoo describe-l7-rs-policy --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>
```

| YAML Path | API Field |
|-----------|-----------|
| `server.proxy_mode` | `ProxyMode` |
| `server.upstream_retry` | `UpstreamRetry` |
| `server.attributes[].weight` | `Attributes[].Attribute.Weight` |
| `server.attributes[].connect_timeout` | `Attributes[].Attribute.ConnectTimeout` |
| `server.attributes[].read_timeout` | `Attributes[].Attribute.ReadTimeout` |
| `server.attributes[].send_timeout` | `Attributes[].Attribute.SendTimeout` |

## Step 3: Security Policy Verification

```bash
# CC protection
aliyun ddoscoo describe-web-cc-protect-switch --domains '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>

# Region blocking
aliyun ddoscoo describe-web-area-block-configs --domains '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>

# Global protection
aliyun ddoscoo describe-domain-security-profile --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>
```

> **Edge case -- plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddoscoo` 0.x): if `describe-domain-security-profile` errors with `unknown command` or with `is not a valid api`, fall back to the OpenAPI route per [acceptance-criteria.md](acceptance-criteria.md) Section 2 ("Plugin Mode (Default) vs OpenAPI Fallback"). Remember to keep the same `--user-agent` template (`AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>`).

| YAML Path | API Field |
|-----------|-----------|
| `security.cc.global_switch` | `ProtectSwitchList[0].CcGlobalSwitch` |
| `security.cc.enable` | `ProtectSwitchList[0].CcEnable` |
| `security.cc.template` | `ProtectSwitchList[0].CcTemplate` |
| `security.ai_protect.mode` | `ProtectSwitchList[0].AiMode` |
| `security.ai_protect.template` | `ProtectSwitchList[0].AiTemplate` |
| `security.ai_protect.rule_enable` | `ProtectSwitchList[0].AiRuleEnable` |
| `security.area_block.enabled` | `ProtectSwitchList[0].RegionBlockEnable` |
| `security.area_block.regions` | `AreaBlockConfigs[0].RegionList[] where Block=1` (set match) |
| `security.global_protection.enabled` | `Result[0].GlobalEnable` |
| `security.global_protection.mode` | `Result[0].GlobalMode` |

## Step 4: GM Certificate Verification (only for domains with gm_enable=1)

```bash
aliyun ddoscoo describe-gm-cert-list --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>
```

> **Edge case -- plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddoscoo` 0.x): if the call above errors with `unknown command` or with `is not a valid api`, fall back to the OpenAPI route per [acceptance-criteria.md](acceptance-criteria.md) Section 2 / Section 6. Remember to keep the same `--user-agent` template.

| YAML Path | API Field |
|-----------|-----------|
| `proxy.gm_cert.cert_id` | `GmCertList[] where DomainMatchCert=true -> CertId` |
| `proxy.gm_cert.gm_enable` | `describe-web-rules -> GmCert.GmEnable` |
| `proxy.gm_cert.gm_only` | `describe-web-rules -> GmCert.GmOnly` |

## Discrepancy Handling

When any field does not match:

1. Record the discrepancy to `./import-mismatch-{timestamp}.yaml`, including: domain, field path, YAML value, and actual API value
2. Output a `file://` link to the user
3. The user decides whether to roll back (using the auto-generated `rollback-{timestamp}.yaml` created before import)
