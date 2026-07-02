# Import Workflow

## Overview

Read YAML file -> schema validation -> dry-run diff -> user confirmation -> 4-phase commit.

## Step 1: File Reading and Schema Validation

```bash
# Read YAML
cat <YAML_PATH>
```

Validation items:
- `schema_version` is compatible (currently supports `2.0`)
- `domains[]` is non-empty
- Each domain must have `domain` / `instance_id_ref` / `server.real_servers` / `proxy.protocols`
- Protocol/port enumeration: `proxy.protocols[].protocol in {http, https, websocket, websockets}`
- HTTPS domains (containing `https` port) must have `proxy.ssl_cert.cert_name` or `proxy.ssl_cert.user_cert_name`

## Step 1.5: Instance Mapping

> **Purpose**: Ensure every instance ID in YAML `exported_from.instance_ids` has a corresponding match in the target environment. If a source instance does not exist in the target environment (e.g., cross-instance recovery, instance renewal with ID change), guide the user to select a target instance.

```bash
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

**Logic**:

1. Read the source instance ID list from YAML `exported_from.instance_ids` (e.g., `["ddoscoo-cn-abc"]`)
2. Compare each against the target environment instances returned by `describe-instances`
3. Build mapping table `instance_mapping = {}`

| Scenario | Handling |
| -------- | -------- |
| Source instance ID exists in target environment | Auto-map: `instance_mapping[sourceID] = sourceID`, no user intervention needed |
| Source instance ID does not exist, target environment has only 1 instance with sufficient capacity | Auto-map to the sole instance, inform user: `"Source instance <sourceID> not found, auto-mapped to <targetID>"` |
| Source instance ID does not exist, target environment has multiple instances | **Use AskUserQuestion** to let the user choose (show instance ID + used domain count / total capacity) |
| Target instance remaining capacity is insufficient for the domains to be imported | **Block execution**, prompt user to scale up or split the import |

**AskUserQuestion Example**:

```
Source instance ddoscoo-cn-abc from YAML does not exist in the target environment.
Please select the target instance to bind the domain to:
[A] ddoscoo-cn-xxx (3/50 domains used, 47 remaining)
[B] ddoscoo-cn-yyy (10/50 domains used, 40 remaining)
```

**Mapping table propagation**: The subsequent Phase 1 `create-domain-resource --instance-ids` and `modify-web-rule --instance-ids` use the mapped instance IDs:

```python
# Pseudocode
target_instance = instance_mapping[yaml_domain['exported_from']['instance_ids'][domain['instance_id_ref']]]
```

## Step 2: Dry-run Diff

For each domain, execute:

```bash
aliyun ddoscoo describe-web-rules --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

Compare YAML against live configuration field by field, generating a tri-color report:

- [NEW] **Green (NEW)**: Current `TotalCount=0`, will be created
- [DIFF] **Yellow (DIFF)**: Exists but with different configuration, list differing fields
- [DESTRUCTIVE] **Red (DESTRUCTIVE)**: Origin server IP / Instance ID / Certificate / Protocol-port changes (requires user confirmation)

Output report example:

```
diff report (3 domains):
  api.example.com    [NEW] NEW
  www.example.com    [DIFF] DIFF: ssl_protocols (tls1.0->tls1.2), cc.template (default->gf_sos_verify)
  pay.example.com    [DESTRUCTIVE] DESTRUCTIVE: real_servers (1.2.3.4 -> 5.6.7.8)
```

## Step 3: AskUserQuestion Confirmation

```
Confirm importing the following changes?
  - New: 1
  - Overwrite: 1
  - Destructive: 1 (pay.example.com origin server change)

[ Execute All / Execute New+Overwrite Only / Cancel ]
```

## Step 4: 4-Phase Commit

Each domain is an independent transaction, executed in the following order. **If a preceding phase fails -> skip subsequent phases for that domain** (Phase 1 must succeed; Phase 2-4 failures are only recorded).

### Phase 1: Domain Entity

> **`<TargetInstanceId>` value**: Use the instance ID mapped by `instance_mapping` established in Step 1.5. That is, `instance_mapping[exported_from.instance_ids[domain.instance_id_ref]]`.

Conflict detection:

```bash
aliyun ddoscoo describe-domain-resource --domain '<D>' --query-domain-pattern exact --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

- `TotalCount=0` -> call `create-domain-resource`
- `TotalCount>0` and policy=skip -> skip
- `TotalCount>0` and policy=overwrite -> call `modify-web-rule`

```bash
# Create (YAML field mapping: proxy.protocols -> ProxyTypes, server.real_servers -> RealServers, proxy.http2/http2https/server.https2http -> HttpsExt)
aliyun ddoscoo create-domain-resource \
  --domain '<D>' \
  --instance-ids '<TargetInstanceId>' \
  --rs-type <0|1> \
  --real-servers '<rs1>' '<rs2>' \
  --proxy-types '[{"ProxyType":"http","ProxyPorts":[80]},{"ProxyType":"https","ProxyPorts":[443]}]' \
  --https-ext '{"Http2":0,"Http2https":0,"Https2http":0}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

```bash
# Overwrite
aliyun ddoscoo modify-web-rule \
  --domain '<D>' \
  --instance-ids '<TargetInstanceId>' \
  --rs-type <0|1> \
  --real-servers '<rs1>' \
  --proxy-types '[{"ProxyType":"http","ProxyPorts":[80]}]' \
  --https-ext '{"Http2":1,"Http2https":1,"Https2http":0}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

### Phase 2: HTTPS Certificate Association (only for domains with https port)

> **YAML path**: `proxy.ssl_cert.cert_name` -> `--cert-identifier`; `proxy.gm_cert` -> GM cert kebab-case actions (with OpenAPI fallback edge case below).

```bash
aliyun ddoscoo associate-web-cert \
  --domain '<D>' \
  --cert-identifier '<CertId>-cn-hangzhou' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

> **Pre-validation**: Before executing `associate-web-cert`, call `aliyun cas list-user-certificate-order --status ISSUE --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>` to confirm the certificate has been issued (Status=ISSUE). Unissued certificate IDs will cause association failure.
>
> **GM (SM2) certificate import**: If the `proxy.gm_cert` section exists in YAML and `gm_enable=1`, use the GM cert actions documented below.
>
> **!! cert_id source note**: The `gm_cert.cert_id` in YAML comes from the SM2 certificate ID returned by `describe-gm-cert-list` during export, **not** the RSA certificate ID returned by `describe-web-rules`. Before importing, call `describe-gm-cert-list` to confirm the SM2 certificate exists in the target environment:
>
> ```bash
> # 0. First query available SM2 certificates in the target environment
> aliyun ddoscoo describe-gm-cert-list --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
> ```
>
> If a certificate matching `gm_cert.cert_id` is found in the list, bind it directly; if no match is found, the SM2 certificate has not been uploaded to the target environment yet -- **skip GM binding and log a warning**.
>
> ```bash
> # 1. Bind GM certificate
> aliyun ddoscoo config-gm-cert --domain '<D>' --cert-id '<gm_cert.cert_id>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
>
> # 2. Enable GM
> aliyun ddoscoo config-gm-cert-enable --domain '<D>' --enable <gm_cert.gm_enable> --region <REGION> --user-agent AlibabaCloud-Agent-Skills
>
> # 3. GM-exclusive mode (optional, execute when gm_only=1)
> aliyun ddoscoo config-gm-cert-only --domain '<D>' --enable <gm_cert.gm_only> --region <REGION> --user-agent AlibabaCloud-Agent-Skills
> ```
>
> **Edge case -- plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddoscoo` 0.x): if any of the four GM actions above (`describe-gm-cert-list` / `config-gm-cert` / `config-gm-cert-enable` / `config-gm-cert-only`) errors with `unknown command` or with `is not a valid api`, fall back to the OpenAPI route per the Command Template's edge-case block in [acceptance-criteria.md](acceptance-criteria.md) (Section 2 / Section 6). On the OpenAPI route, parameters must be PascalCase and `--version` must be omitted (the core CLI uses its built-in default; an explicit `--version` is rejected as `unchecked version`).

### Phase 3: Advanced Configuration (9 items: proxy + client + server)

Execute as needed -- **each item can fail independently**:

```bash
# OCSP (HTTPS only) -- YAML: proxy.ocsp_enabled
aliyun ddoscoo modify-ocsp-status --domain '<D>' --enable <0|1> --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# TLS (HTTPS only) -- YAML: proxy.tls.* -- config JSON keys must be snake_case (verified 2026-06-18)
# !! Note the underscore position in ssl_13_enabled (not ssl13_enabled or Ssl13Enabled)
aliyun ddoscoo modify-tls-config --domain '<D>' \
  --config '{"ssl_protocols":"tls1.2","ssl_13_enabled":false,"ssl_ciphers":"default","custom_ciphers":[],"tls_13_custom_ciphers":[]}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Mutual Authentication (mTLS) -- YAML: proxy.mutual_auth.*
# ca_cert_enable=0 disables mutual auth; when =1, --cert-identifier must be provided
aliyun ddoscoo config-l7-mutual-authentication --domain '<D>' \
  --ca-cert-enable <0|1> --cert-issuer 'aliyun' --cert-region '<CertRegion>' \
  --cert-identifier '<CertId>' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Back-to-origin keepalive + downstream timeout -- YAML: server.keepalive.* + client.ds_keepalive_timeout
# !! --upstream-keepalive JSON keys must be snake_case (enabled/keepalive_timeout/keepalive_requests); PascalCase causes ddos_layer73446 (verified 2026-06-18)
# !! --downstream-keepalive must be a simple integer (e.g., '120'); passing JSON causes ddos_layer73446 (verified 2026-06-18)
aliyun ddoscoo config-l7-us-keepalive --domain '<D>' \
  --upstream-keepalive '{"enabled":true,"keepalive_timeout":30,"keepalive_requests":1000}' \
  --downstream-keepalive '120' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Back-to-origin headers (including traffic markers) -- YAML: server.headers.* -- --custom-headers must be a flat KV map, do not wrap in {Domain, Headers} (verified 2026-06-17)
# !! --embedded-headers key names must strictly match API response format (case-sensitive), e.g., WL-Proxy-Client-IP (not Wl-) (verified 2026-06-18)
aliyun ddoscoo modify-headers --domain '<D>' \
  --custom-headers '{"X-Custom":"value"}' \
  --embedded-headers '{"WL-Proxy-Client-IP":true,"Web-Server-Type":true,"X-Client-IP":true,"X-Forwarded-Proto":true,"X-True-IP":true}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Back-to-origin policy -- YAML: server.proxy_mode + server.upstream_retry + server.attributes
aliyun ddoscoo config-l7-rs-policy --domain '<D>' \
  --policy '{"ProxyMode":"ip_hash","Attributes":[{"RealServer":"1.2.3.4","Attribute":{"Weight":100,"ConnectTimeout":5,"ReadTimeout":120,"SendTimeout":120,"Mode":"active","MaxFails":3,"FailTimeout":10}}]}' \
  --upstream-retry 1 \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# CNAME reuse -- YAML: client.cname_reuse.*
aliyun ddoscoo modify-cname-reuse --domain '<D>' --enable <0|1> \
  --cname '<CnameValue>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Cookie settings (aliyungf_tc) -- YAML: client.cookie.aliyungf_tc
aliyun ddoscoo config-l7cc-cookie-enable --domain '<D>' \
  --enable <0|1> --key 'aliyungf_tc' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Cookie settings (cookie_secure) -- YAML: client.cookie.cookie_secure
aliyun ddoscoo config-l7cc-cookie-enable --domain '<D>' \
  --enable <0|1> --key 'cookie_secure' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

> **Edge case -- plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddoscoo` 0.x for `config-l7-mutual-authentication` and `config-l7cc-cookie-enable`): if either kebab-case call above errors with `unknown command` or with `is not a valid api`, fall back to the OpenAPI route per the Command Template's edge-case block in [acceptance-criteria.md](acceptance-criteria.md) (Section 2). On the OpenAPI route, parameters must be PascalCase and `--version` must be omitted (the core CLI uses its built-in default; an explicit `--version` is rejected as `unchecked version`).

### Phase 4: Security Policies (security section)

```bash
# CC global switch -- YAML: security.cc.global_switch (verified 2026-06-17)
aliyun ddoscoo modify-web-cc-global-switch --domain '<D>' --cc-global-switch open \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# CC protection master switch -- YAML: security.cc.enable (corresponds to CcEnable from describe, verified 2026-06-17)
aliyun ddoscoo enable-web-cc --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
# Use disable-web-cc to turn off

# CC custom rule switch -- YAML: security.cc.custom_rule_enable (corresponds to CcCustomRuleEnable from describe, verified 2026-06-17)
aliyun ddoscoo enable-web-cc-rule --domain '<D>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
# Use disable-web-cc-rule to turn off

# CC template -- YAML: security.cc.template
aliyun ddoscoo config-web-cc-template --domain '<D>' --template <default|gf_under_attack|gf_sos_verify|gf_sos_enhance> \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# CC custom rules -- YAML: security.cc.custom_rules -- must be snake_case (verified 2026-06-17)
# owner/expires/status_code/statistics can all be replayed; but status_code and statistics must be removed when empty {}, otherwise InvalidParams is returned
aliyun ddoscoo config-web-cc-rule-v2 --domain '<D>' \
  --rule-list '[{"name":"cc1","action":"block","owner":"manual","expires":0,"condition":[{"field":"uri","match_method":"contain","content":"/"}],"ratelimit":{"interval":5,"target":"ip","threshold":2,"ttl":6660},"status_code":{"enabled":false,"code":200,"use_ratio":false,"count_threshold":100}}]' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# AI intelligent protection -- YAML: security.ai_protect.* -- config fields are AiTemplate/AiMode (verified 2026-06-17)
aliyun ddoscoo modify-web-ai-protect-mode --domain '<D>' \
  --config '{"AiTemplate":"level60","AiMode":"defense"}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo modify-web-ai-protect-switch --domain '<D>' \
  --config '{"AiRuleEnable":1}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Precise access control rules -- YAML: security.cc.precise_access_rules -- rules must be snake_case, key is condition (not conditionList) (verified 2026-06-17)
# owner/expires/expire_period can all be replayed (verified 2026-06-17)
aliyun ddoscoo modify-web-precise-access-rule --domain '<D>' \
  --rules '[{"name":"rule1","action":"block","owner":"manual","expires":0,"expire_period":0,"condition":[{"field":"uri","match_method":"contain","content":"/admin"}]}]' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Precise access control switch -- YAML: security.cc.precise_access_enable (verified 2026-06-17)
aliyun ddoscoo modify-web-precise-access-switch --domain '<D>' \
  --config '{"PreciseRuleEnable":1}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Region blocking -- YAML: security.area_block.regions
aliyun ddoscoo modify-web-area-block --domain '<D>' --regions 'CN-11' 'OVERSEAS-RU' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Region blocking switch -- YAML: security.area_block.enabled (verified 2026-06-17)
aliyun ddoscoo modify-web-area-block-switch --domain '<D>' \
  --config '{"RegionblockEnable":1}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# Domain-level IP blacklist/whitelist -- YAML: security.ip_blackwhite.{black_list,white_list}
aliyun ddoscoo config-web-ip-set --domain '<D>' \
  --black-list '1.2.3.4' '5.6.7.0/24' \
  --white-list '10.0.0.1' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
# Blacklist/whitelist switch -- YAML: security.ip_blackwhite.enabled
aliyun ddoscoo modify-web-ip-set-switch --domain '<D>' \
  --config '{"bwlist_enable":1}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
# Note: Black/white list combined switch, 0=off 1=on (verified 2026-06-17, BlackEnable/WhiteEnable are deprecated)

# Static page cache -- YAML: server.cache.*
# 1) Switch
aliyun ddoscoo modify-web-cache-switch --domain '<D>' --enable 1 --region <REGION> --user-agent AlibabaCloud-Agent-Skills
# 2) Cache mode (only when exported Mode is non-empty)
aliyun ddoscoo modify-web-cache-mode --domain '<D>' --biz-mode '<standard|aggressive|bypass>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills
# 3) Custom rules (only when exported CustomRules is non-empty; --rules is a JSON array string)
aliyun ddoscoo modify-web-cache-custom-rule --domain '<D>' \
  --rules '[{"Name":"r1","Uri":"/static/","Mode":"standard","CacheTtl":3600}]' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills

# CDN linkage scheduling -- YAML: server.cdn_linkage.* (rule_type=5 indicates CDN linkage)
# Create:
aliyun ddoscoo create-scheduler-rule --rule-name '<RuleName>' --rule-type 5 \
  --rules '[{"Type":"CNAME","Value":"<CdnCname>","Priority":50,"ValueType":5}]' \
  --param '{"ParamType":"cdn","ParamData":{"Domain":"<CdnDomain>","Cname":"<CdnCname>","AccessQps":1000,"UpstreamQps":500}}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
# Edit (if already exists) uses modify-scheduler-rule with the same parameters as create
# Skip this step when YAML server.cdn_linkage.enabled=0
```

#### Global Protection (security.global_protection)

```bash
# Global protection switch and level -- YAML: security.global_protection.enabled + security.global_protection.mode
# global_rule_enable: 0=off 1=on, global_rule_mode: hard|default|weak
aliyun ddoscoo config-domain-security-profile --domain '<D>' \
  --config '{"global_rule_enable":1,"global_rule_mode":"hard"}' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
```

```bash
# Global protection rule details -- YAML: security.global_protection.rules
# Only execute when security.global_protection.rules in YAML is non-empty (i.e., non-default rules exist)
# Export already filtered: only retains items where Action != ActionDefault or Enabled=0
# Note: RuleId contains a server-side dynamic hash; stable within the same instance, may differ across instances
# System default rules do not need replay (automatically applied when domain is created)
#
# !! Server-side payload-size limit: a single --rule-attr array with ~67 items reproducibly returns
#    HTTP 500 InternalError on cn-hangzhou (verified 2026-06-22 against domain-inspect-test profile).
#    Chunks of <= 20 items submitted sequentially succeed. The skill MUST split non-default rules into
#    chunks of at most 20 and call config-l7-global-rule once per chunk; failures of any single chunk
#    must be logged but should not abort the remaining chunks.
aliyun ddoscoo config-l7-global-rule --domain '<D>' \
  --rule-attr '[{"RuleId":"global_03","Action":"watch","Enabled":1},...]' \
  --region <REGION> --user-agent AlibabaCloud-Agent-Skills
# --rule-attr accepts a JSON array; each item requires RuleId + Action + Enabled
# Only replay non-default items recorded in YAML; unrecorded rules retain system defaults
```

## Step 6: Failure Report and Rollback YAML

Record a `phase` x `api` x `result` matrix for each domain, saved to `./import-result-{timestamp}.yaml`:

```yaml
import_result:
  total: 3
  succeeded: 2
  partial: 1
  failed: 0
domains:
  - domain: api.example.com
    status: success
    phases: {phase1: ok, phase2: ok, phase3: ok, phase4: ok}
  - domain: www.example.com
    status: partial
    phases: {phase1: ok, phase2: ok, phase3: failed, phase4: skipped}
    errors:
      - {api: modify-tls-config, code: InvalidParameter, message: "..."}
```

Also generate a rollback YAML (pre-import snapshot) that the user can re-import to roll back: `./rollback-{timestamp}.yaml`.

## Output to User

After execution, output to the user:

- Statistics for success / partial success / failure
- Failure report file:// link
- Rollback YAML file:// link
- Verification command: `aliyun ddoscoo describe-web-rules --domain '<domain>' --region <REGION> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>`, then compare key fields such as `RealServers/ProxyTypes/SslProtocols/CertName/BlackList` against the YAML
