# Domain Verify — API Commands

## Domain Verify Reference

### get-instance-detail — Query Instance Details (New API, Preferred)

```bash
aliyun cas get-instance-detail --profile $CERT_PROFILE --region $CERT_REGION --instance-id "{{instance_id}}" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

**Verification-related fields:**

| Field | Description |
|-------|-------------|
| `Status` / `CertificateStatus` | Certificate overall status |
| `ValidationMethod` | DNS / HTTP |
| `DnsHost` / `ValidationDomain` / `Host` | DNS host record (full or relative) |
| `DnsValue` / `ValidationValue` / `TxtValue` / `Value` | DNS TXT record value |
| `FilePath` / `ValidationPath` | HTTP verification file path |
| `FileContent` | HTTP verification file content |

### get-task-attribute — Query Application Task Status

```bash
aliyun cas get-task-attribute --profile $CERT_PROFILE --region $CERT_REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id} \
  --task-id "{{instance_id}}" --task-type "ApplyCertificate"
```

### alidns add-domain-record — Auto-Add DNS TXT Record

```bash
aliyun alidns add-domain-record --profile $CERT_PROFILE --region $CERT_REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id} \
  --domain-name "example.com" --rr "_acme-challenge" --type "TXT" --value "{{txt_value}}"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain-name` | Yes | Root domain, e.g. `example.com` |
| `--rr` | Yes | Host record relative part, e.g. `_acme-challenge` |
| `--type` | Yes | Fixed `TXT` |
| `--value` | Yes | TXT record value |

### Status Reference

| Value | Meaning | Action |
|-------|---------|--------|
| `issued` | Issued, verification passed | Done |
| `checking` / `DOMAIN_VERIFY` | Awaiting domain verification | Continue verification |
| `pending` | Under review | Wait |
| `failed` | Verification/application failed | Check error details |
| `expired` | Expired | Re-apply |

### DNS Record Split Rules

If API returns full hostname (`_acme-challenge.example.com`):
- `RR` = `_acme-challenge`, `DomainName` = `example.com`

If API returns only RR (`_acme-challenge`):
- Use directly as `RR`, with user's domain as `DomainName`

### Common Error Codes

| Error | Cause | Fix |
|-------|-------|-----|
| `InvalidInstanceId.NotFound` | Instance does not exist | Check InstanceId |
| `DomainNotExist` | Domain not on Alibaba Cloud DNS | Use manual DNS guidance |
| `DomainRecordDuplicate` | Record already exists | Query/delete old record, or reuse |
| `Throttling` | Rate limited | Reduce polling frequency |

### DNS Auto-Add (Alibaba Cloud DNS)

Check existence first:
```bash
aliyun alidns describe-domain-records --profile $CERT_PROFILE --region $CERT_REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id} \
  --domain-name "{{domain}}" --rr-key-word "{{rr}}" --type-key-word "TXT"
```

Add (if not exists):
```bash
aliyun alidns add-domain-record --profile $CERT_PROFILE --region $CERT_REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id} \
  --domain-name "{{domain}}" --rr "{{rr}}" --type "TXT" --value "{{txt_value}}"
```

> `RR` is host record relative to domain. E.g. `_acme-challenge.example.com` → `RR=_acme-challenge`, `DomainName=example.com`.

### HTTP Verification

Guide user to create file at web server root:
- Path: `{{validation_path}}` (from `FilePath`)
- Content: `{{validation_value}}` (from `FileContent`)

Auto-upload via SSH:
```bash
echo "{{validation_value}}" > /tmp/{{file_name}}
scp /tmp/{{file_name}} {{user}}@{{server}}:{{web_root}}{{validation_path}}

# [MUST] SSRF guard — build this URL ONLY from the get-instance-detail response:
# {{domain}} must equal the instance's validated domain, and {{validation_path}} must equal
# the API-returned FilePath. Never fetch arbitrary user-supplied URLs or domains.
curl -s --connect-timeout 10 --max-time 30 "http://{{domain}}{{validation_path}}"
```

---

