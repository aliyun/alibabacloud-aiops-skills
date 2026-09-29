# Scenario Description: WAF Domain Certificate Status Check

The source-of-truth document for this skill's scenario. Records what problem the scenario solves, the
workflow it decomposes into, and where each piece of domain knowledge came from, so that later
iterations can trace every ruling back to its origin.

## 1. Problem Statement

A customer has onboarded domains to Alibaba Cloud WAF (CNAME access) with HTTPS listeners. Each HTTPS
domain is served by an SSL certificate that silently approaches its expiry date. When a certificate
expires, browsers and API clients start showing trust errors and the HTTPS service is effectively
interrupted — an outage caused purely by an unnoticed date.

The customer asks things like:

- "Which of my WAF domain certificates are expired or about to expire?"
- "Give me a certificate expiry audit across all onboarded domains."
- "I renewed the certificate in CAS — did it actually reach WAF?"
- "I want a periodic certificate health check so HTTPS never breaks silently."

The skill answers exactly one question: **for every onboarded domain, which certificate is bound, when
does it expire, and which certificates need renewal now.** It is a read-only inventory and expiry
classification — it never renews, uploads, deploys, or re-binds anything.

## 2. Architecture / Objects Involved

```
WAF instance (3.0: DescribeInstance / 2.0: DescribeInstanceInfo)
    └── onboarded domains (CNAME access)
            └── listen config per domain
                    ├── WAF 3.0: Listen.CertId / Listen.SM2CertId  → resolves in CAS
                    │       └── CAS certificate (EndDate / Expired / Common / Sans)
                    └── WAF 2.0: Certificates[] bound to the domain
                            └── IsUsing=true certificate (EndTime, Unix ms)
```

Cloud objects touched: WAF instance, onboarded domain (listen config), SSL certificate (WAF 3.0: in
the Certificate Management Service / CAS, referenced by CertId; WAF 2.0: certificate metadata
returned directly by WAF, including expiry).

Key cross-service fact: **WAF 3.0's DescribeDomainDetail returns the certificate ID but no expiry
date** — the validity period lives in CAS and must be resolved with `GetUserCertificateDetail`
(`CertFilter=true`). WAF 2.0's `DescribeCertificates` is self-contained (`EndTime`, `IsUsing`).

## 3. Workflow Decomposition

The scenario decomposes into five phases; each phase maps to read-only APIs only.

**Phase 1 — Identify the instance and the WAF generation**
1.1 Query the WAF 3.0 instance (`DescribeInstance`) and/or the WAF 2.0 instance
    (`DescribeInstanceInfo`, `--api-version 2019-09-10`).
1.2 If both generations exist, ask the customer which to check (or run both and label rows).

**Phase 2 — Enumerate onboarded domains**
2.1 WAF 3.0: page through `DescribeDomains` until `TotalCount` is covered.
2.2 WAF 2.0: `DescribeDomainNames` returns the full list.
2.3 Single-domain check: WAF 3.0 `DescribeDomains --domain <d>` / `DescribeDomainDetail --domain <d>`;
    WAF 2.0 `DescribeCertificates --domain <d>`.

**Phase 3 — Collect certificate bindings and expiry**
3.1 WAF 3.0: `DescribeDomainDetail` per domain → `Listen.HttpsPorts`, `Listen.CertId`,
    `Listen.SM2Enabled` / `Listen.SM2CertId`.
3.2 WAF 3.0: CAS `GetUserCertificateDetail --cert-id <numeric id> --cert-filter true` → `EndDate`,
    `Expired`, `Common`, `Sans`, `Name`. CertId may carry a region suffix (`123-cn-hangzhou`) —
    pass the numeric prefix.
3.3 WAF 2.0: `DescribeCertificates` per domain → `Certificates[]` with `IsUsing`, `CertificateId`,
    `CommonName`, `Sans`, `EndTime` (Unix ms, UTC).

**Phase 4 — Classify every domain**
4.1 `expired` — expiry before today (or CAS `Expired=true`).
4.2 `expiring` — within the warn window (default 30 days).
4.3 `healthy` — beyond the window.
4.4 `no-cert-bound` — HTTPS listening on but no certificate bound (actionable finding).
4.5 `https-not-enabled` — HTTP-only listener, nothing to expire.
4.6 `expiry-not-retrieved` — binding or expiry could not be resolved (manual review, never "healthy").

**Phase 5 — Report and guidance**
5.1 Summary table sorted expired → expiring (ascending days left) → rest.
5.2 Renewal guidance as console paths only (CAS renew / upload / deploy-to-cloud-product, or the WAF
    domain edit page), plus the certificate-hosting suggestion with its preconditions.
5.3 After the customer renews: re-run the check to verify the new expiry reached WAF.

## 4. Information Sources

| Knowledge | Source |
|-----------|--------|
| WAF 3.0 API parameters / responses | https://api.aliyun.com/document/waf-openapi/2021-10-01/DescribeDomains , .../DescribeDomainDetail (verified via the public metadata endpoint) |
| WAF 2.0 API parameters / responses | https://api.aliyun.com/document/waf-openapi/2019-09-10/DescribeDomainNames , .../DescribeCertificates |
| CAS certificate detail API | https://api.aliyun.com/document/cas/2020-04-07/GetUserCertificateDetail |
| WAF 3.0 CNAME onboarding & HTTPS certificate configuration | https://help.aliyun.com/zh/waf/web-application-firewall-3-0/add-a-domain-name-to-waf-in-cname-record-mode |
| WAF 2.0 domain onboarding | https://help.aliyun.com/zh/waf/web-application-firewall-2-0/user-guide/add-a-domain-name-to-waf |
| Certificate upload / renewal / hosting / deployment | https://help.aliyun.com/zh/ssl-certificate/upload-an-ssl-certificate , .../ssl-official-certificate-renewal , .../enable-certificate-hosting , .../deploy-ssl-certificates-to-alibaba-cloud-services |
| Certificate-chain completeness, self-signed certificates not supported by WAF, renew ~30 days ahead, cross-account certificates must be re-uploaded/shared, WAF-side cert must match the CAS region | Domain knowledge distilled from Alibaba Cloud WAF certificate support practice |
| RAM action names | `ramActions` field of the public metadata endpoint (e.g. `yundun-cert:GetUserCertificateDetail`, `yundun-waf:DescribeDomains`) |

## 5. Out of Scope

- Why one specific request was blocked (block-reason lookup skill).
- Protection rule effectiveness (rule effectiveness skill).
- TLS handshake / certificate-chain / browser-trust troubleshooting beyond reporting expiry status.
- Cloud-product-access domains (CLB / ALB / MSE / FC): their certificates are managed by those products.
- Executing renewal, upload, deployment, or re-binding — console paths only.
