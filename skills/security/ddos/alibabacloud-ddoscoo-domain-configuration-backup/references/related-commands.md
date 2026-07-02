# Related Commands

Complete quick-reference table of all `aliyun ddoscoo` CLI commands used by this skill.

> All commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-domain-configuration-backup/<SESSION_ID>`.

## Export Commands (16 describe APIs)

| # | Command | Parameter Pattern | Description |
|---|---------|-------------------|-------------|
| 1 | `describe-web-rules` | `--domain <D>` | Domain entity + HTTPS/TLS/OCSP/GmCert/IP blacklist & whitelist |
| 2 | `describe-l7-rs-policy` | `--domain <D>` | Back-to-origin policy (load balancing algorithm/timeout/weight) |
| 3 | `describe-l7-us-keepalive` | `--domain <D>` | Persistent connections (forward timeout + back-to-origin keepalive) |
| 4 | `describe-headers` | `--domain <D>` | Back-to-origin headers (custom + embedded switches) |
| 5 | `describe-cname-reuses` | `--domains <D>` | CNAME reuse |
| 6 | `describe-web-cc-protect-switch` | `--domains <D>` | CC/AI protection switches and templates |
| 7 | `describe-web-cc-rules-v2` | `--domain <D>` | Custom CC rules (filter out smartcc_ prefix) |
| 8 | `describe-web-precise-access-rule` | `--domains <D>` | Precise access control ACL |
| 9 | `describe-web-area-block-configs` | `--domains <D>` | Region blocking |
| 10 | `describe-web-cache-configs` | `--domains <D>` | Static page caching (**plural**) |
| 11 | `describe-cdn-linkage-rules` | `--domain <D> --page-number 1 --page-size 10` | CDN linkage scheduling |
| 12 | `aliyun ddoscoo describe-domain-security-profile` !! | `--domain <D>` | Global protection level and switches (falls back to OpenAPI on plugin 0.x -- see export-workflow.md Sec.2.12) |
| 13 | `describe-l7-global-rule` | `--domain <D>` | Global protection rule details |
| 14 | `aliyun ddoscoo describe-l7cc-cookie` !! | `--domain <D>` | Cookie settings (falls back to OpenAPI on plugin 0.x -- see export-workflow.md Sec.2.14) |
| 15 | `aliyun ddoscoo describe-l7-mutual-auth-conf` !! | `--domain <D>` | Mutual authentication mTLS (falls back to OpenAPI on plugin 0.x -- see export-workflow.md Sec.2.15) |
| 16 | `aliyun ddoscoo describe-gm-cert-list` !! | `--domain <D>` | SM2 (GM) certificate list (falls back to OpenAPI on plugin 0.x -- see export-workflow.md Sec.2.16) |

## Auxiliary Query Commands

| Command | Parameters | Description |
|---------|------------|-------------|
| `describe-instances` | `--page-number 1 --page-size 50` | Instance list (paginated) |
| `describe-domains` | No pagination parameters | Full domain list |
| `describe-domain-resource` | `--instance-ids <ID>` or `--domain <D>` | Domain resource details (including instance bindings) |

## Import Commands (4 Phases)

### Phase 1: Domain Entity

| Command | Description |
|---------|-------------|
| `create-domain-resource` | Create new domain (including protocol/port/origin/HttpsExt) |
| `modify-web-rule` | Overwrite existing domain entity configuration |

### Phase 2: HTTPS Certificate

| Command | Parameter Pattern | Description |
|---------|-------------------|-------------|
| `associate-web-cert` | `--cert-identifier` | Associate RSA certificate |
| `aliyun ddoscoo config-gm-cert` !! | `--domain --cert-id` | Bind SM2 (GM) certificate (falls back to OpenAPI on plugin 0.x -- see import-workflow.md) |
| `aliyun ddoscoo config-gm-cert-enable` !! | `--domain --enable` | Enable/disable GM certificate (falls back to OpenAPI on plugin 0.x -- see import-workflow.md) |
| `aliyun ddoscoo config-gm-cert-only` !! | `--domain --enable` | GM-exclusive mode (falls back to OpenAPI on plugin 0.x -- see import-workflow.md) |

### Phase 3: Advanced Configuration

| Command | Description |
|---------|-------------|
| `modify-ocsp-status` | OCSP Stapling switch |
| `modify-tls-config` | TLS version/cipher suites |
| `aliyun ddoscoo config-l7-mutual-authentication` !! | Mutual authentication mTLS (falls back to OpenAPI on plugin 0.x -- see import-workflow.md) |
| `config-l7-us-keepalive` | Persistent connections + forward timeout |
| `modify-headers` | Back-to-origin headers (custom + embedded) |
| `config-l7-rs-policy` | Back-to-origin policy (load balancing algorithm/timeout/weight) |
| `modify-cname-reuse` | CNAME reuse switch |
| `aliyun ddoscoo config-l7cc-cookie-enable` !! | Cookie settings (falls back to OpenAPI on plugin 0.x -- see import-workflow.md) |

### Phase 4: Security Policies

| Command | Description |
|---------|-------------|
| `modify-web-cc-global-switch` | CC global switch |
| `enable-web-cc` / `disable-web-cc` | CC protection master switch |
| `enable-web-cc-rule` / `disable-web-cc-rule` | Custom CC rule switch |
| `config-web-cc-template` | CC template |
| `config-web-cc-rule-v2` | Custom CC rule (ACL) |
| `modify-web-ai-protect-mode` | AI protection level |
| `modify-web-ai-protect-switch` | AI protection switch |
| `modify-web-precise-access-rule` | Precise access control rules |
| `modify-web-precise-access-switch` | Precise access control switch |
| `modify-web-area-block` | Region blocking policy |
| `modify-web-area-block-switch` | Region blocking switch |
| `config-web-ip-set` | IP blacklist & whitelist |
| `modify-web-ip-set-switch` | IP blacklist & whitelist switch |
| `modify-web-cache-switch` | Cache switch |
| `modify-web-cache-mode` | Cache mode |
| `modify-web-cache-custom-rule` | Custom cache rules |
| `create-scheduler-rule` / `modify-scheduler-rule` | CDN linkage scheduling |
| `config-domain-security-profile` | Global protection switches + level |
| `config-l7-global-rule` | Global protection rules (batch) |
