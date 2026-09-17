# Custom Domain Binding Guide

Binding a custom domain to an OSS bucket lets users access objects through
`https://<your-domain>/<key>` instead of the OSS default domain (removing
the default-domain forced-download policy for renderable text types).
Binding is ALWAYS a manual user operation; this skill only checks the
binding state via `ListBucketCname` and attributes failures.

## 1. Binding steps (manual, in the OSS console)

1. OSS console -> target bucket -> Transport Configuration -> Bind Custom
   Domain: enter the domain (e.g. `img.example.com`).
2. Add a DNS **CNAME** record pointing the host to the bucket's external
   endpoint: `img.example.com -> <bucket>.oss-<region>.aliyuncs.com`.
   Do NOT use an A record, and do not keep a conflicting record for the
   same host.
3. If the console asks for ownership verification, add the displayed TXT
   record (commonly `_dnsauth.<your-subdomain>`) and retry.
4. For HTTPS access, host/upload a certificate that covers exactly the
   bound domain (a wildcard certificate covers its subdomains only).

## 2. ICP filing requirement

- Buckets located in **mainland China** (`cn-*` regions except Hong Kong):
  a bound custom domain MUST hold a valid ICP filing; the console rejects
  unfiled domains at binding time.
- **Regionless-attribute buckets** (`oss-rg-china-mainland` /
  `rg-china-mainland`): data is stored in mainland China
  (document_detail/2248436.html:7), so ICP filing IS required — these
  locations do NOT match the `cn-*` pattern but are mainland for ICP
  purposes (B-2 fix, 2026-09-03).
- Regions **outside the mainland** (Hong Kong, Singapore, ...): ICP filing
  is not enforced for the bound domain.
- "The domain IS filed but binding says it is not" — common causes:
  1. The filing record has not synced to the validation database yet
     (new filings or recent transfers need time to propagate).
  2. The filing belongs to a different domain spelling (subdomain vs
     root domain mismatch).
  3. The filing was cancelled/expired at the MIIT registry.
  Verify the filing status for the exact domain, wait for sync, retry.

## 3. Binding-failure attribution table

| Symptom | Likely cause | Next check |
|---|---|---|
| Binding rejected: "not filed" | ICP filing missing / not synced (mainland bucket) | Section 2 above |
| Binding rejected: domain occupied | The domain is already bound to another bucket or another Alibaba Cloud product/account | Find and unbind the old binding first |
| Bound but DNS does not resolve | CNAME record missing / conflicting A record / TTL not expired | `dig <domain>` and compare with the bucket endpoint |
| Bound but access 404 | CNAME points to the wrong bucket endpoint; object path wrong | Confirm endpoint region matches the bucket |
| HTTPS error | Certificate does not cover the bound domain, or is expired | Certificate CN/SAN vs bound domain |
| Status flaps between "effective" and "pending" | DNS record inconsistent across resolvers | Check for duplicate/conflicting records |

## 4. Evidence the diagnosis script produces

- `cnames.count = 0` -> **no custom domain is bound**: access works only
  over the default domain; relay the binding steps above.
- `--domain` not present in the bound cname list -> binding has not taken
  effect; route through the attribution table.
- `--domain` present in the list -> binding is effective; a remaining
  access failure is DNS / certificate / object level, not binding.
