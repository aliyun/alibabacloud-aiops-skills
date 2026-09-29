# Related Commands: WAF Certificate Status Check (read-only)

All commands are read-only. Two API generations plus CAS are involved:

- **WAF 3.0** — `waf-openapi` plugin default version `2021-10-01` (no `--api-version` needed).
- **WAF 2.0** — MUST add `--api-version 2019-09-10`. Never use global `--version` or `--force` to
  switch versions (`--force` bypasses the plugin and sends a real RPC request).
- The plugin renames the API parameter `RegionId` to the flag `--biz-region-id`, and `InstanceId` to
  `--instance-id`. Writing `--region-id` / `--RegionId` fails.
- WAF `RegionId` is only valid as `cn-hangzhou` (Chinese mainland) or `ap-southeast-1` (international).
  A stated mainland region (`cn-beijing` / `cn-shanghai` / `cn-shenzhen` / `cn-guangzhou` / …) is
  normalized to `cn-hangzhou`; a stated international region (`ap-*` / `us-*` / `eu-*` / …) to
  `ap-southeast-1` — a deterministic mapping, not a guess. Only a missing / unrecognizable region blocks.
- Append `--cli-dry-run` to print the target Endpoint and request without sending it (zero-risk check).
- Every API command MUST carry `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"` (both values per the Observability section in SKILL.md).

## Phase 1 — Instance and generation

```bash
# WAF 3.0 instance
aliyun waf-openapi describe-instance --biz-region-id <region>
# → InstanceId, Details.Edition

# WAF 2.0 instance (note --api-version)
aliyun waf-openapi describe-instance-info --api-version 2019-09-10 --biz-region-id <region>
# → InstanceInfo.InstanceId
```

## Phase 2 — Enumerate onboarded domains

```bash
# WAF 3.0: paged CNAME-access domain list
aliyun waf-openapi describe-domains --biz-region-id <region> --instance-id <instance_id> \
  --page-number 1 --page-size 50
# → TotalCount, Domains[]{Domain, Status(1=normal), ...}
#   Single domain: add --domain <domain>

# WAF 2.0: full domain name list
aliyun waf-openapi describe-domain-names --api-version 2019-09-10 --biz-region-id <region> \
  --instance-id <instance_id>
# → DomainNames[]
```

## Phase 3 — Certificate bindings and expiry

```bash
# WAF 3.0: per-domain listen config (certificate ID, HTTPS ports, SM2)
aliyun waf-openapi describe-domain-detail --biz-region-id <region> --instance-id <instance_id> \
  --domain <domain>
# → Listen.HttpsPorts[], Listen.CertId, Listen.SM2Enabled, Listen.SM2CertId, Listen.TLSVersion
#   NO expiry date here — resolve CertId in CAS below.

# WAF 3.0 → CAS: resolve the expiry (CertFilter=true is MANDATORY; never fetch cert/key content)
#   CAS region: cn-hangzhou for a Chinese-mainland WAF, ap-southeast-1 for an international WAF.
aliyun cas get-user-certificate-detail --cert-id <numeric_cert_id> --cert-filter true \
  --region cn-hangzhou
# → EndDate (YYYY-MM-DD), Expired (true/false), Common, Sans, Name, Issuer, StartDate
#   CertId may carry a region suffix (e.g. 123-cn-hangzhou for SM2) — pass the numeric prefix.

# WAF 2.0: per-domain bound certificates, expiry included (no CAS call needed)
aliyun waf-openapi describe-certificates --api-version 2019-09-10 --biz-region-id <region> \
  --instance-id <instance_id> --domain <domain>
# → Certificates[]{IsUsing(true=current), CertificateId, CertificateName, CommonName, Sans[],
#                  EndTime(Unix ms, UTC)}
```

## Key response fields to read

| Field | From | Meaning |
|-------|------|---------|
| `InstanceId` | DescribeInstance (3.0) | WAF 3.0 instance ID |
| `InstanceInfo.InstanceId` | DescribeInstanceInfo (2.0) | WAF 2.0 instance ID |
| `TotalCount` / `Domains[].Domain` | DescribeDomains (3.0) | domain inventory + paging |
| `DomainNames[]` | DescribeDomainNames (2.0) | domain inventory |
| `Listen.HttpsPorts` | DescribeDomainDetail (3.0) | empty → HTTP-only, nothing expires |
| `Listen.CertId` / `Listen.SM2CertId` | DescribeDomainDetail (3.0) | certificate reference (resolve in CAS) |
| `EndDate` / `Expired` | CAS GetUserCertificateDetail | WAF 3.0 certificate expiry |
| `Certificates[].IsUsing` | DescribeCertificates (2.0) | which certificate currently serves the domain |
| `Certificates[].EndTime` | DescribeCertificates (2.0) | WAF 2.0 expiry (Unix ms) |

## Official documentation

| Topic | Link |
|-------|------|
| DescribeDomains (3.0) | https://api.aliyun.com/document/waf-openapi/2021-10-01/DescribeDomains |
| DescribeDomainDetail (3.0) | https://api.aliyun.com/document/waf-openapi/2021-10-01/DescribeDomainDetail |
| DescribeDomainNames (2.0) | https://api.aliyun.com/document/waf-openapi/2019-09-10/DescribeDomainNames |
| DescribeCertificates (2.0) | https://api.aliyun.com/document/waf-openapi/2019-09-10/DescribeCertificates |
| GetUserCertificateDetail (CAS) | https://api.aliyun.com/document/cas/2020-04-07/GetUserCertificateDetail |
| WAF 3.0 CNAME onboarding & HTTPS cert | https://help.aliyun.com/zh/waf/web-application-firewall-3-0/add-a-domain-name-to-waf-in-cname-record-mode |
| WAF 2.0 add a domain | https://help.aliyun.com/zh/waf/web-application-firewall-2-0/user-guide/add-a-domain-name-to-waf |
| Upload / sync / share SSL certificate | https://help.aliyun.com/zh/ssl-certificate/upload-an-ssl-certificate |
| SSL certificate renewal | https://help.aliyun.com/zh/ssl-certificate/ssl-official-certificate-renewal |
| Deploy SSL certificate to cloud products | https://help.aliyun.com/zh/ssl-certificate/deploy-ssl-certificates-to-alibaba-cloud-services |
| Certificate hosting (auto-renewal) | https://help.aliyun.com/zh/ssl-certificate/enable-certificate-hosting |
