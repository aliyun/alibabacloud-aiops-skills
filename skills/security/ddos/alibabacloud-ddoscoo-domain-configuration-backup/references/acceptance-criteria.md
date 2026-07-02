# Acceptance Criteria: alibabacloud-ddoscoo-domain-configuration-backup

**Scenario**: Full export and import of DDoS Pro domain-level (Layer 7 website) configurations
**Purpose**: Skill acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product -- ddoscoo

All CLI commands use the `aliyun ddoscoo` product name (all lowercase).

#### [OK] CORRECT
```bash
aliyun ddoscoo describe-web-rules --domain 'example.com' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

#### [BAD] INCORRECT
```bash
aliyun ddos describe-web-rules       # Wrong product name (ddos != ddoscoo)
aliyun DDoSCoo describe-web-rules    # Wrong case
```

### 2. Plugin Mode (Default) and OpenAPI Edge Case

All commands use kebab-case plugin mode as the **default and primary form**. A small set of unregistered APIs may temporarily fall back to the OpenAPI route as an edge case when the installed plugin doesn't recognize them.

#### [OK] CORRECT -- Plugin mode for all APIs (default)
```bash
aliyun ddoscoo describe-web-rules --domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-l7-rs-policy --domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-web-cache-configs --domains '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-cname-reuses --domains '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-web-cc-protect-switch --domains '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-web-precise-access-rule --domains '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-web-area-block-configs --domains '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-gm-cert-list --domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-domain-security-profile --domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-l7cc-cookie --domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-l7-mutual-auth-conf --domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

> **Edge case -- plugin doesn't recognize the action** (currently the case on `aliyun-cli-ddoscoo` 0.x for the GM/Cookie/MutualAuth/DomainSecurityProfile family): if a kebab-case call errors with `unknown command` or `'<Action>' is not a valid api`, fall back to the OpenAPI route. Use **PascalCase** action and parameters; do NOT pass `--version` (the core CLI uses its built-in default; an explicit `--version` is rejected as `unchecked version`). Switch back to plugin-mode kebab-case once a future plugin release declares these actions.
>
> ```bash
> aliyun --auto-plugin-install false ddoscoo DescribeGmCertList --force --Domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
> aliyun --auto-plugin-install false ddoscoo DescribeDomainSecurityProfile --force --Domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
> aliyun --auto-plugin-install false ddoscoo DescribeL7CCCookie --force --Domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
> aliyun --auto-plugin-install false ddoscoo DescribeL7MutualAuthConf --force --Domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
> ```

#### [BAD] INCORRECT -- Forcing OpenAPI fallback for APIs that already work in plugin mode
```bash
# These APIs are registered in plugin metadata; using --auto-plugin-install false bypasses the plugin unnecessarily.
# Use kebab-case plugin form instead.
```

### 3. Parameter Naming -- `--domain` vs `--domains`

#### [OK] CORRECT -- Singular `--domain`
```bash
aliyun ddoscoo describe-web-rules --domain '<D>'           # singular
aliyun ddoscoo describe-l7-rs-policy --domain '<D>'        # singular
aliyun ddoscoo describe-headers --domain '<D>'             # singular
aliyun ddoscoo describe-web-cc-rules-v2 --domain '<D>'     # singular
aliyun ddoscoo describe-cdn-linkage-rules --domain '<D>'   # singular
aliyun ddoscoo describe-l7-global-rule --domain '<D>'      # singular
```

#### [OK] CORRECT -- Plural `--domains`
```bash
aliyun ddoscoo describe-web-cache-configs --domains '<D>'           # plural
aliyun ddoscoo describe-cname-reuses --domains '<D>'                # plural
aliyun ddoscoo describe-web-cc-protect-switch --domains '<D>'       # plural
aliyun ddoscoo describe-web-precise-access-rule --domains '<D>'     # plural
aliyun ddoscoo describe-web-area-block-configs --domains '<D>'      # plural
```

#### [BAD] INCORRECT
```bash
aliyun ddoscoo describe-web-rules --domains '<D>'    # Should be --domain
aliyun ddoscoo describe-headers --domains '<D>'      # Should be --domain
```

### 4. Indexed Parameters (Edge case OpenAPI fallback only)

When the OpenAPI fallback edge case applies, array parameters must use the indexed format, not JSON arrays. In normal kebab-case plugin mode, simply pass the value directly.

#### [OK] CORRECT -- Plugin mode (no indexed format needed)
```bash
aliyun ddoscoo describe-gm-cert-list --domain 'example.com' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-domain-security-profile --domain 'example.com' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

> **Edge case (OpenAPI fallback only)** -- if you must use the OpenAPI route, use the indexed format:
>
> ```bash
> aliyun --auto-plugin-install false ddoscoo DescribeGmCertList --force --Domain 'example.com'
> ```

#### [BAD] INCORRECT -- JSON array on the OpenAPI route

If you fall back to the OpenAPI route, do **not** wrap the value in a JSON array (`'["example.com"]'`). Use the indexed form instead. (Plugin-mode kebab-case calls don't need indexed form.)

### 5. `--user-agent` Flag

#### [OK] CORRECT -- Every command includes --user-agent
```bash
aliyun ddoscoo describe-web-rules --domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun ddoscoo describe-gm-cert-list --domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

#### [BAD] INCORRECT -- Missing --user-agent
```bash
aliyun ddoscoo describe-web-rules --domain '<D>' --region cn-hangzhou  # Missing --user-agent
```

### 6. GM Certificate ID Source

#### [OK] CORRECT -- SM2 cert ID from describe-gm-cert-list
```bash
# Export: get SM2 cert ID from describe-gm-cert-list
aliyun ddoscoo describe-gm-cert-list --domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
# Take CertId where DomainMatchCert=true -> write to YAML gm_cert.cert_id

# Import: bind using SM2 cert ID
aliyun ddoscoo config-gm-cert --domain '<D>' --cert-id '21678226-cn-hangzhou' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

> **Edge case (OpenAPI fallback)** -- if `aliyun-cli-ddoscoo` 0.x doesn't recognize these actions:
>
> ```bash
> aliyun --auto-plugin-install false ddoscoo DescribeGmCertList --force --Domain '<D>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
> aliyun --auto-plugin-install false ddoscoo ConfigGmCert --force --Domain '<D>' --CertId '21678226-cn-hangzhou' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
> ```

#### [BAD] INCORRECT -- Using RSA cert ID from describe-web-rules for GM cert
```bash
# describe-web-rules returns RSA cert ID in GmCert.CertId, NOT SM2
# Using this ID for config-gm-cert will fail with NoMatchCert error
```

### 7. CC Rules -- smartcc_ Filter

#### [OK] CORRECT -- Filter out system-generated smartcc_ rules
```
Export: keep only rules where Owner=manual or Name does NOT start with "smartcc_"
```

#### [BAD] INCORRECT -- Including smartcc_ rules in export
```
Export: keep all rules including smartcc_* (these are AI-managed, cannot be manually replayed)
```

### 8. Global Protection Rules -- Non-Default Only

#### [OK] CORRECT -- Export only non-default rules
```
Export: keep rules where Action != ActionDefault OR Enabled = 0
```

#### [BAD] INCORRECT -- Export all rules including defaults
```
Export: keep all 200+ rules (most are system defaults that auto-apply on domain creation)
```

### 9. YAML Schema Version

#### [OK] CORRECT -- v2.0 four-section structure
```yaml
schema_version: "2.0"
domains:
  - proxy: { ... }
    client: { ... }
    server: { ... }
    security: { ... }
```

#### [BAD] INCORRECT -- v1.0 flat structure
```yaml
schema_version: "1.0"
domains:
  - real_servers: [...]
    proxy_types: [...]
    https: { ... }
```

### 10. Pagination Parameters

#### [OK] CORRECT
```bash
aliyun ddoscoo describe-domain-resource --instance-ids '<ID>' --page-number 1 --page-size 10  # max 10
aliyun ddoscoo describe-instances --page-number 1 --page-size 50                              # max 50
aliyun ddoscoo describe-cdn-linkage-rules --domain '<D>' --page-number 1 --page-size 10
```

#### [BAD] INCORRECT
```bash
aliyun ddoscoo describe-domain-resource --instance-ids '<ID>' --page-size 50  # InvalidPageSize (max 10)
```
