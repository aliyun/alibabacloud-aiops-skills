# YAML Schema (v2.0)

## Top-Level Structure

```yaml
schema_version: "2.0"               # Required, schema version number
exported_at: "2026-06-17T10:00:00+08:00"
exported_from:                       # Metadata, source marker only
  account_uid: "1234567890"
  region: cn-hangzhou
  instance_ids:
    - ddoscoo-cn-5es4t7x52001
domains:                             # Required, domain configuration array
  - <DomainConfig>
```

## DomainConfig Structure

Following the DDoS Pro console layout, split into 4 sections: **proxy (protocols and access)**, **client (client-side settings)**, **server (back-to-origin settings)**, **security (security policies)**.

```yaml
domain: api.example.com              # Required
instance_id_ref: 0                   # Reference to exported_from.instance_ids index
cname: "xxx.aliyunddos1003.com"      # Read-only, ignored during import

# ====================================
# 1. proxy -- Protocols and Access
# ====================================
proxy:
  protocols:                         # Protocol type + port (required)
    - {protocol: http, ports: [80]}
    - {protocol: https, ports: [443]}
    # protocol in {http, https, websocket, websockets}

  ssl_cert:                          # SSL certificate (HTTPS domains only)
    cert_name: "24203010.pem"
    cert_region: cn-hangzhou
    user_cert_name: "jiafei"

  gm_cert:                           # GM (SM2) certificate (optional); write via aliyun ddoscoo config-gm-cert / config-gm-cert-enable / config-gm-cert-only (with OpenAPI fallback when plugin doesn't recognize the action)
    cert_id: ""                      # SM2 GM certificate ID (source: aliyun ddoscoo describe-gm-cert-list, not the RSA certificate ID returned by describe-web-rules)
    gm_enable: 0                     # 0=off 1=on (source: describe-web-rules -> GmCert.GmEnable)
    gm_only: 0                       # 0=off 1=GM exclusive (source: describe-web-rules -> GmCert.GmOnly)

  tls:                               # TLS strategy (HTTPS domains only)
    ssl_protocols: "tls1.2"          # tls1.0|tls1.1|tls1.2|tls1.3
    ssl_ciphers: "default"           # default|all|strong|custom
    ssl13_enabled: false
    custom_ciphers: []
    tls13_custom_ciphers: []

  ocsp_enabled: false                # OCSP Stapling: true|false

  http2https: 0                      # HTTPS force redirect: 0=off 1=on (export source: describe-web-rules.Http2HttpsEnable; import: assembled into HttpsExt.Http2https JSON for create-domain-resource / modify-web-rule)
  http2: 0                           # HTTP2 listener: 0=off 1=on (export source: describe-web-rules.Http2Enable; import: assembled into HttpsExt.Http2 JSON for create-domain-resource / modify-web-rule)

  mutual_auth:                       # Mutual Authentication (mTLS); export: aliyun ddoscoo describe-l7-mutual-auth-conf --domain; import: aliyun ddoscoo config-l7-mutual-authentication (OpenAPI fallback when plugin doesn't recognize the action)
    ca_cert_enable: 0                # 0=off 1=on (API returns Enable)
    cert_issuer: "aliyun"            # Certificate issuer (API returns CertIssuer)
    cert_region: "cn-hangzhou"       # Certificate region (!! Describe API does not return this; used only during import, corresponds to --CertRegion)
    cert_identifier: ""              # Required when ca_cert_enable=1, CA certificate ID (API returns CertId)

# ====================================
# 2. client -- Client-Side Settings
# ====================================
client:
  ds_keepalive_timeout: 120          # Downstream keepalive timeout (seconds); source: describe-l7-us-keepalive -> DsKeepaliveTimeout

  cookie:                            # Cookie settings; source: aliyun ddoscoo describe-l7cc-cookie --domain (OpenAPI fallback when plugin doesn't recognize the action)
    aliyungf_tc: 1                   # Anti-DDoS CC protection Cookie (aliyungf_tc): 0=off 1=on
    cookie_secure: 0                 # Cookie Secure attribute: 0=off 1=on
    max_age_enable: 0                # Cookie Max-Age switch: 0=off 1=on
    max_age: ""                      # Max-Age value (effective when max_age_enable=1)

  cname_reuse:                       # CNAME Reuse
    enabled: 0                       # 0=off 1=on
    cname: ""                        # Required when enabled=1

# ====================================
# 3. server -- Back-to-Origin Settings
# ====================================
server:
  real_servers:                      # Origin server info (required); rs_type is per-origin (describe-web-rules.RealServers[].RsType)
    - {address: "1.1.1.1", rs_type: 0}   # rs_type 0=IP, 1=domain

  proxy_mode: "rr"                   # Back-to-origin load balancing algorithm: ip_hash|rr|least_time
  upstream_retry: 1                  # Back-to-origin retry: 0=no retry 1=retry

  headers:                           # Request header forwarding config + traffic markers (same API)
    custom:                          # Custom headers (including traffic markers, e.g., "$ReqClientIP"/"$ReqVar_*" variables)
      X-Forwarded-ClientSrcIp: "$ReqClientIP"
      http2_client_fingerprint_md5: "$ReqVar_http2_client_fingerprint_md5"
    embedded:                        # System-embedded header switches
      x_forwarded_proto: true
      x_client_ip: true
      x_true_ip: true
      wl_proxy_client_ip: true
      web_server_type: true

  https2http: 0                      # HTTP back-to-origin: 0=off 1=on (export source: describe-web-rules.Https2HttpEnable; import: assembled into HttpsExt.Https2http JSON for create-domain-resource / modify-web-rule)

  attributes:                        # Per-origin-server settings (including timeouts)
    - real_server: "1.1.1.1"
      weight: 100
      connect_timeout: 5             # New connection timeout (seconds)
      read_timeout: 120              # Read connection timeout (seconds)
      send_timeout: 120              # Write connection timeout (seconds)
      mode: "active"                 # active|backup
      max_fails: 3
      fail_timeout: 10

  keepalive:                         # Back-to-origin keepalive
    enabled: true
    keepalive_timeout: 30            # Seconds
    keepalive_requests: 1000

  cache:                             # Static Page Cache
    enabled: 0                       # 0=off 1=on
    mode: "standard"                 # standard|aggressive|bypass
    custom_rules: []

  cdn_linkage:                       # CDN Linkage Scheduling
    enabled: 0
    cname: ""
    rule_name: ""
    param:
      param_type: "cdn"
      param_data:
        domain: ""
        cname: ""
        access_qps: 0
        upstream_qps: 0
    rules:
      - type: "CNAME"               # A=IP address, CNAME=domain
        value: ""
        priority: 50                 # 0-100
        value_type: 5                # 1=Anti-DDoS IP, 2=Cloud resource IP, 3=Accelerated route IP, 5=CDN linkage, 6=Cloud product linkage

# ====================================
# 4. security -- Security Policies
# ====================================
security:
  ai_protect:                        # AI Intelligent Protection
    rule_enable: 1                   # Status: 0=off 1=on
    mode: "defense"                  # Mode: defense|warning
    template: "level60"              # Level: level30|level60|level90

  global_protection:                 # DDoS Global Protection Policy
    enabled: true                    # Status (master switch): true|false (source: DescribeDomainSecurityProfile -> GlobalEnable)
    mode: "hard"                     # Mode: hard|default|weak (source: GlobalMode; write uses config-domain-security-profile --config global_rule_mode)
    rules:                           # Non-default rules only (Action!=ActionDefault or Enabled=0); system default rules are not recorded
      - rule_id: "global_03"
        rule_name: "Simulate Browser Request"    # Read-only
        action: "watch"              # block|challenge|watch
        action_default: "challenge"  # System default action (read-only, used for diff comparison)
        enabled: 1                   # 0=user disabled 1=enabled

  ip_blackwhite:                     # IP Blacklist/Whitelist
    enabled: 1                       # Status: 0=off 1=on (corresponds to API BlackWhiteListEnable -> write as bwlist_enable)
    black_list: ["1.2.3.4"]          # Source: describe-web-rules -> BlackList
    white_list: ["10.0.0.1"]         # Source: describe-web-rules -> WhiteList (field not returned when array is empty, treated as [])

  area_block:                        # Region Blocking
    enabled: 0                       # Status: 0=off 1=on (corresponds to API RegionBlockEnable -> write as RegionblockEnable, note lowercase b)
    regions: []                      # Strategy: only retain items with Block=1, e.g., ["CN-11", "OVERSEAS-RU"]

  cc:                                # CC Protection
    global_switch: "open"            # CC global switch: open|close
    enable: 1                        # CC protection master switch: 0|1
    template: "default"              # Template: default|gf_under_attack|gf_sos_verify|gf_sos_enhance
    custom_rule_enable: 1            # CC custom rule switch (ACL): 0|1
    custom_rules:                    # CC custom rules (excluding smartcc_ prefix)
      - name: "rule1"
        action: "block"              # block|challenge|watch
        owner: "manual"
        expires: 0
        condition:
          - {field: "uri", match_method: "contain", content: "/admin"}
        ratelimit:
          target: "ip"               # ip|session
          interval: 5
          threshold: 10
          ttl: 1800
        statistics: {}               # !! Must be removed when empty {} during import, otherwise InvalidParams is returned
        status_code: {}              # !! Must be removed when empty {} during import, otherwise InvalidParams is returned
    precise_access_enable: 1         # Precise Access Control switch (ACL): 0|1 (corresponds to API PreciseRuleEnable)
    precise_access_rules:            # Precise Access Control rules (ACL)
      - name: "test"
        action: "block"              # accept|block|challenge|watch
        owner: "manual"
        expires: 0
        expire_period: 0
        condition:
          - {field: "uri", match_method: "contain", content: "/admin"}
```

## Known Limitations

All 20 configuration dimensions currently support full bidirectional (export + import) operations with no known functional limitations.

## Field Conventions

### Default Value Omission

To reduce YAML size, the following fields are omitted by default during export (treated as defaults during import):

- `proxy.ssl_cert` -- pure HTTP domains
- `proxy.gm_cert` -- when no GM certificate is present
- `proxy.tls` -- pure HTTP domains
- `proxy.http2https=0` and `proxy.http2=0`
- `client.cname_reuse.enabled=0`
- `server.cache.enabled=0`
- `server.cdn_linkage.enabled=0`
- `security.cc.custom_rules=[]`
- `security.cc.precise_access_rules=[]`
- `security.area_block.regions=[]`

Export with the `--include-defaults` flag to retain all fields.

### Field Mapping (API <-> YAML)

See the field lists in each API section of [export-workflow.md](export-workflow.md) combined with the YAML structure definition in this document for detailed field mappings. For import command field correspondences, see [import-workflow.md](import-workflow.md).

### v1.0 -> v2.0 Migration Guide

| v1.0 Path | v2.0 Path |
| --------- | --------- |
| `real_servers` | `server.real_servers` |
| `proxy_types` | `proxy.protocols` |
| `https.*` | `proxy.ssl_cert` + `proxy.gm_cert` + `proxy.tls` + `proxy.ocsp_enabled` + `proxy.http2` + `proxy.http2https` |
| `https.https_ext.https2http` | `server.https2http` |
| `keepalive.ds_keepalive_timeout` | `client.ds_keepalive_timeout` |
| `keepalive.{enabled,keepalive_timeout,keepalive_requests}` | `server.keepalive` |
| `headers` | `server.headers` |
| `rs_policy` | `server.proxy_mode` + `server.upstream_retry` + `server.attributes` |
| `cname_reuse` | `client.cname_reuse` |
| `security.cc` | `security.cc` |
| `security.ai_protect` | `security.ai_protect` |
| `security.precise_access_enable` + `security.precise_access_rules` | `security.cc.precise_access_enable` + `security.cc.precise_access_rules` |
| `security.ip_blacklist` + `security.ip_whitelist` + `security.ip_blackwhite_enable` | `security.ip_blackwhite.*` |
| `security.area_block` | `security.area_block` |
| `security.global_enable` + `security.global_mode` + `security.global_rules` | `security.global_protection.*` |
| `security.cache` | `server.cache` |
| `security.cdn_linkage` | `server.cdn_linkage` |
