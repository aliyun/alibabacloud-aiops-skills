# Certificate Status Basics

Background knowledge for reading WAF domain certificate status. This skill only **reports status**; it
never fixes a certificate. The concepts below explain what each field means and why a finding matters,
so the report can be interpreted correctly.

## 1. Where the expiry lives (the single most important fact)

| WAF generation | Does the WAF API return the expiry? | Where to read the expiry |
|----------------|-------------------------------------|--------------------------|
| WAF 3.0 (2021-10-01) | **No.** `DescribeDomainDetail` returns `Listen.CertId` only | Resolve `CertId` in **CAS**: `GetUserCertificateDetail` → `EndDate` / `Expired` |
| WAF 2.0 (2019-09-10) | **Yes.** `DescribeCertificates` returns `EndTime` per certificate | Read `Certificates[].EndTime` (Unix ms, UTC) directly |

Consequence: for WAF 3.0, "the domain has a CertId" does **not** mean the expiry is known. If CAS
cannot resolve the CertId (deleted there, or issued under another account), the correct status is
`expiry-not-retrieved` — **never** "healthy" and **never** a guessed date.

## 2. Validity period and the expiry classification

A certificate is valid between `StartDate`/`NotBefore` and `EndDate`/`NotAfter`. Days remaining are
counted from **today** to the expiry date:

- **expired** — expiry is before today (or CAS `Expired=true`). HTTPS with this certificate already
  triggers browser/client trust errors; this is an active incident, reported first.
- **expiring** — within the warn window (default **30 days**). Renewal should start now: buying or
  re-issuing a CA certificate, completing domain validation, and deploying to WAF can take days.
- **healthy** — beyond the window. Still list the expiry date so the customer can plan.

The 30-day window is a default, not a law. Business-critical domains are commonly renewed earlier.

## 3. Binding states that are not about expiry

Two findings are reported even though nothing "expires":

- **no-cert-bound** — the domain has HTTPS listening enabled (`HttpsPorts` non-empty on WAF 3.0) but no
  certificate is bound. HTTPS cannot serve correctly; this is an actionable misconfiguration.
- **https-not-enabled** — the domain listens on HTTP only (no `HttpsPorts`, no certificate). There is
  no certificate to expire; reported as informational, never flagged as a risk.

On WAF 2.0, `DescribeCertificates` returns all certificates associated with the domain; the one with
`IsUsing=true` is the certificate currently serving traffic and is the one to classify. Others are
"available but not in use".

## 4. Certificate types

- **RSA / ECC (international algorithm)** — the common case; `Listen.CertId` on WAF 3.0, or a
  `Certificates[]` entry on WAF 2.0.
- **SM2 (Chinese national cryptography)** — WAF 3.0 only, when `Listen.SM2Enabled=true`. The
  certificate ID is `Listen.SM2CertId` and often carries a region suffix (e.g. `123-cn-hangzhou`);
  pass the numeric prefix to CAS. Report it as an **extra row** for the same domain — never drop it.
  A domain can carry both an RSA/ECC and an SM2 certificate; both expire independently.

## 5. Certificate source and chain (why a certificate may not resolve or may fail)

Domain knowledge that shapes the guidance (this skill reports status; these are the reasons behind a
finding, not things this skill fixes):

- **WAF requires a CA-issued certificate.** Self-signed certificates are not accepted for WAF
  onboarding; if a customer insists on self-signed, WAF is not the right entry point (an API gateway
  or similar would be). This skill never promises a self-signed certificate can be bound.
- **Complete certificate chain.** A certificate must be deployed with its full chain (root +
  intermediate + domain certificate). An incomplete chain shows up as "some browsers/clients OK,
  others fail" or mobile-client errors — a **chain** problem, distinct from an **expiry** problem. If
  the customer's symptom is a trust/handshake error rather than a date, route to a
  certificate-chain/TLS troubleshooting flow; this skill only reports expiry.
- **Cross-account certificates.** CAS resolves only certificates in the **same account** as the WAF
  instance. A certificate bought or uploaded under another account must be shared into, or re-uploaded
  to, this account before it resolves — otherwise the status stays `expiry-not-retrieved`.
- **Region alignment.** The certificate must be available in the CAS region that matches the WAF
  region (`cn-hangzhou` for Chinese mainland, `ap-southeast-1` for international). A mismatch is a
  common reason a CertId does not resolve.

## 6. Renewal and deployment (the customer's action, not this skill's)

The renewal path handed back as console guidance (see the Remediation Table in SKILL.md):

1. Obtain a replacement: renew in CAS (`SSL 证书续费`), or buy/apply for a new CA certificate, or upload
   an existing one (`上传证书`).
2. Deploy it to WAF: either a CAS deployment task (`云产品部署` → WAF), or edit the domain in the WAF
   console (`接入管理` → `CNAME 接入` → `编辑` → update certificate) and select the new certificate.
3. Verify: HTTPS access works, then **re-run this skill** — the domain row must now show the new,
   later expiry. A renewal that never reached WAF is exactly the silent failure this check catches.

**Certificate hosting / auto-renewal** (CAS `证书托管`) can renew and redeploy automatically, but only
under preconditions (typically a certificate bought in Alibaba Cloud with hosting enabled). It is a
suggestion with caveats — this skill never asserts that auto-renewal is active or will succeed
(constraint 9).

## 7. After expiry

Once a certificate expires, HTTPS requests to that domain fail trust validation in browsers and many
API clients — effectively an HTTPS interruption. The old certificate does not "auto-refresh"; a valid
replacement must be deployed. This is why the skill treats `expiring` (not only `expired`) as needing
attention, and why renewing ahead of the expiry date is the whole point of the check.
