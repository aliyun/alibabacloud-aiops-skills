# Origin Configuration Checklist (Host / Port / Domain State)

The checklist `origin_config_diagnosis.py` runs for every diagnosis, with
the finding code emitted for each failed item. All items are read-only
checks; fixes are manual guidance only.

## 1. Domain state

| Check | Evidence | Finding |
|---|---|---|
| Domain exists under this account | DescribeCdnDomainDetail | `DOMAIN_NOT_FOUND` on InvalidDomain.NotFound |
| Domain is online | `DomainStatus` | `DOMAIN_NOT_ONLINE` (offline/stopped/configuring domains serve no traffic; back-to-origin symptoms are expected) |
| At least one origin configured | `SourceModels` | `NO_ORIGIN_CONFIGURED` |

A stopped domain is the cheapest explanation for any back-to-origin symptom:
check state first, authorization second.

## 2. Origin content

| Check | Evidence | Finding |
|---|---|---|
| OSS origin matches `<bucket>.oss-<region>.aliyuncs.com` | origin `Content` | `UNRECOGNIZED_OSS_ORIGIN` |
| Non-OSS origin (ipaddr/domain) | origin `Type` | `NON_OSS_ORIGIN` (private-bucket rules not applicable) |
| Origin uses the INTERNAL endpoint (`oss-<region>-internal.aliyuncs.com`) | origin `Content` | `ORIGIN_INTERNAL_ENDPOINT` — internal endpoints serve same-region Alibaba Cloud intranet clients only (official: access-oss-via-bucket-domain-name, "internal access domain" section — intranet VIP segments); public CDN edge nodes cannot route to them, so this origin never works — switch to the public endpoint |
| Origin uses the transfer-ACCELERATION endpoint (`oss-accelerate[-overseas].aliyuncs.com`) | origin `Content` | `ORIGIN_ACCELERATE_ENDPOINT` (info) — official "CDN + transfer acceleration" dual-acceleration architecture (transfer-acceleration best practices: "configure CDN back-to-origin to the transfer-acceleration domain"); the region-consistency check does NOT apply to this endpoint form |
| Origin bucket exists | OSS GetBucketInfo | `ORIGIN_BUCKET_MISSING` on NoSuchBucket |
| Bucket region matches the endpoint in the origin host (public region endpoints only) | `location` vs host | `ORIGIN_REGION_MISMATCH` |

**Billing consequence of the origin TYPE (G-5)** — the `Type` field is not
just a private-bucket-rule switch; it drives the traffic bill. Official rule
(help.aliyun.com/zh/cdn/product-overview/billing-of-oss-content-acceleration):

- Origin type set to **"OSS Domain"** -> OSS recognizes the Alibaba-Cloud-CDN
  back-to-origin traffic as the DISCOUNTED "CDN back-to-origin outbound
  traffic" (cheaper price).
- Origin type mis-set to **"Origin (source-station) Domain"** -> OSS
  recognizes the same traffic as "Internet outbound traffic" (standard public
  egress) and the discount is LOST — a common
  cause of "back-to-origin traffic fee suddenly jumped".
- The CDN-side back-to-origin traffic (CDN node fetching from OSS) is NOT
  billed on the CDN side; OSS bills the "OSS outbound-to-CDN traffic". When
  BOTH the CDN back-to-origin
  node and the bucket are OUTSIDE mainland China, the OSS→CDN traffic is FREE.

So a `NON_OSS_ORIGIN` finding should also flag the billing impact, and
"back-to-origin traffic fee suddenly jumped" questions cross-refer to
alibabacloud-oss-billing-diagnosis and
alibabacloud-oss-endpoint-internal-diagnosis (endpoint-rules.md §4 covers the
same official page from the traffic-cost side).

## 3. Back-to-origin Host header

For an OSS origin, the request `Host` must equal the bucket's virtual-hosted
endpoint host (`<bucket>.oss-<region>.aliyuncs.com`) or a custom domain
bound to that bucket — otherwise OSS cannot route the request and answers
403/404.

**Official auto-set behavior (OSS-domain origins only)**: when the CDN origin
type is set to an OSS domain, CDN automatically enables the default
origin-HOST feature and sets the domain type to "source station domain" — the
back-to-origin Host equals the OSS bucket endpoint WITHOUT any user
configuration (source:
help.aliyun.com/zh/cdn/user-guide/configure-the-default-origin-host,
section "Example 3: origin type is OSS Domain"). For non-OSS origins (domain / IP type)
the feature is OFF by default and the Host falls back to the accelerated
domain, which OSS cannot route.

| Check | Evidence | Finding |
|---|---|---|
| `set_req_host_header` configured (non-OSS origin only) | DescribeCdnDomainConfigs | `ORIGIN_HOST_DEFAULT` when absent AND origin type ≠ OSS domain (CDN then sends the accelerated domain as Host; OSS cannot route it) |
| `set_req_host_header` absent, origin type = OSS domain | DescribeCdnDomainConfigs | `ORIGIN_HOST_AUTO_OK` (info): CDN auto-sets Host to the source station domain per official policy — no action needed |
| Host equals the origin endpoint host | `FunctionArgs.domain_name` | `ORIGIN_HOST_MISMATCH` |

## 4. Origin port and back-to-origin protocol

OSS endpoints serve HTTP on 80 and HTTPS on 443. Any other origin port for
an OSS origin cannot work (`ORIGIN_PORT_SUSPECT`).

**Back-to-origin protocol policy** (official:
help.aliyun.com/zh/cdn/user-guide/configure-the-origin-protocol-policy):

- The feature is OFF by default; with it off, the protocol follows the
  configured origin PORT: port 443 -> HTTPS back-to-origin; port 80 or any
  other port -> HTTP back-to-origin.
- When enabled, the policy is one of **HTTP** (fixed HTTP), **HTTPS**
  (fixed HTTPS), or **Follow** (client HTTP -> origin HTTP, client
  HTTPS -> origin HTTPS).
- Custom origin ports: HTTP/HTTPS port range is **1-65535**; clients can
  only reach CDN on the standard ports 80/443 — custom ports apply to the
  CDN-node-to-origin leg only. (For an OSS origin custom ports are useless:
  OSS serves 80/443 only, hence `ORIGIN_PORT_SUSPECT`.)
- With **HTTPS** back-to-origin, the default origin HOST and the back-to-
  origin **SNI** must both be correct (accelerated domain or origin domain),
  otherwise Bad Request / 502 / back-to-origin failure — relevant when the
  origin hosts multiple HTTPS sites; for a plain OSS bucket origin the
  auto-set source-station Host (§3) is correct.
- Symptom mapping from real tickets: "back-to-origin fails / 502 after
  enabling HTTPS" is usually protocol+Host/SNI; "forced HTTP back-to-origin
  causes a redirect loop" is usually the protocol policy vs the origin's
  HTTP->HTTPS redirect (see
  back-to-origin-troubleshooting).

## 5. Private-bucket attribution

| Fact | Finding | Playbook |
|---|---|---|
| `acl=private`, same account | `PRIVATE_ORIGIN_AUTH_REQUIRED` | origin-auth-playbook Method 1/2 |
| `acl=private`, other account | `PRIVATE_ORIGIN_CROSS_ACCOUNT` | origin-auth-playbook Method 2 (owner side) |
| `acl=public-read*` | `PUBLIC_ORIGIN_NO_AUTH_NEEDED` | look at Host/port/deny policy instead |
| GetBucketInfo denied | `ORIGIN_BUCKET_NOT_READABLE` | degrade `[WARN]`, advise owner-side check |

## Routing summary

- 403 on back-to-origin + private bucket -> section 5 first, then 3.
- 403 on back-to-origin + public bucket + OSS-domain origin -> section 3
  (ORIGIN_HOST_MISMATCH only; ORIGIN_HOST_DEFAULT is NOT a valid finding
  for OSS-domain origins per official auto-set policy), then section 4.
- 403 on back-to-origin + public bucket + non-OSS origin -> section 3/4.
- No response / timeout on back-to-origin -> section 1 (state), then 4
  (port), then 2 (`ORIGIN_INTERNAL_ENDPOINT` — an internal-endpoint origin
  is unreachable for CDN by design).
- HTTPS/protocol-related back-to-origin failures (502, redirect loops after
  protocol changes) -> section 4 protocol policy.
- Back-to-origin 404 with "rewrite back-to-origin path" (URL rewrite) rules
  configured ->
  official rewrite-urls-in-back-to-origin-requests: up to 50 rules per
  domain; rewrite rules may conflict with the "ignore parameters"
  performance feature and with conditional back-to-origin rules (the
  rewritten path diverges from what the origin expects -> 404; official
  triage: temporarily disable the rewrite rules to verify); `enhance break`
  additionally rewrites URL parameters and may conflict with the
  back-to-origin parameter-rewrite feature.
  This skill cannot read rewrite rules (DescribeCdnDomainConfigs is queried
  for set_req_host_header only) — advise manual inspection.
- Symptom "traffic not accelerated" -> check client addressing and the
  accelerated-domain CNAME.
- Terminology guard: OSS **mirror back-to-origin** (an OSS bucket rule that
  pulls missing objects from another origin) is NOT CDN
  back-to-origin; this skill covers the CDN side only — mirror-rule
  questions belong to the OSS data-migration/back-to-origin-rule docs, not
  to the finding codes above.
