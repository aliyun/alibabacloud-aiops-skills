# OSS Endpoint Rules: Region Mapping, Internal/Public Selection, Traffic Cost

All content here is read-only diagnostic knowledge. This skill never changes
any bucket configuration.

## 1. Endpoint forms

| Form | Pattern | Reachability | Typical use |
|---|---|---|---|
| Public endpoint | `oss-<region>.aliyuncs.com` | Internet + Alibaba Cloud network | Clients outside Alibaba Cloud, or cross-region access |
| Internal endpoint | `oss-<region>-internal.aliyuncs.com` | Alibaba Cloud network of the SAME region only (classic network / VPC) | Same-region ECS, containers, Function Compute - free of public network traffic cost |
| Dual-stack endpoint | `<region>.oss.aliyuncs.com` (note: reversed layout vs the public form) | Internet, IPv4 + IPv6 | IPv6 clients; per the official regions-and-endpoints table only SOME regions provide it (most mainland-China regions; e.g. Japan/Korea/Singapore do not; regionless-attribute buckets have none) |
| Transfer acceleration | `oss-accelerate.aliyuncs.com` / `oss-accelerate-overseas.aliyuncs.com` | Internet, global edge optimization | Cross-region / cross-border optimization; billed separately, must be enabled on the bucket |
| Custom domain (CNAME) | any well-formed FQDN that is NOT `*.aliyuncs.com` and NOT a raw IP (e.g. `img.example.com`) | Served through the bucket's own region endpoint underneath | Customer branding; must be CNAME'd to the bucket public endpoint AND bound on the bucket (see sec.3.3). The script classifies this form `cname` |

Regionless-attribute buckets (`rg-china-mainland`) expose ONLY the public
endpoint `oss-rg-china-mainland.aliyuncs.com` - no internal, no dual-stack
(official regions-and-endpoints table).

CAPABILITY PRECHECK for regionless-attribute buckets (G-8, official
region-attribute-of-buckets capability matrix - "x" = NOT supported): a
regionless bucket does NOT support internal access, **transfer acceleration**,
**real-time log query**, resource groups, requester-pays, bucket
tags, OSS accelerator, Inventory, IMM, ZIP decompression, event
notification, OSS-HDFS, OSS ON CloudBox, RTMP push, SelectObject, or data
indexing; log shipping works only to the SAME bucket. So before
recommending transfer acceleration (sec.3) or real-time-log traffic correlation
(sec.4) for a `oss-rg-china-mainland` bucket, note those two paths are NOT
executable on it - the public endpoint is the only access form.

Region examples: `cn-hangzhou`, `cn-shanghai`, `cn-beijing`,
`cn-hongkong`, `ap-southeast-1`, `us-east-1`.

## 2. Region-to-endpoint mapping rule

A bucket's region is fixed at creation time and reported by GetBucketInfo as
`location` (e.g. `oss-cn-shanghai`), together with the AUTHORITATIVE
`extranet_endpoint` / `intranet_endpoint` authoritative values. Resolve the
endpoint in this priority order (B-7):

1. **Use the GetBucketInfo `extranet_endpoint` / `intranet_endpoint`
   authoritative value whenever present** - it is correct for EVERY cloud,
   including finance
   cloud, and always wins over any template.
2. Only when that authoritative value is absent, fall back to the `<location>` template -
   VALID ONLY for ordinary public-cloud regions:
   - public: `https://<location>.aliyuncs.com` -> `oss-cn-shanghai.aliyuncs.com`
   - internal: `https://<location>-internal.aliyuncs.com` -> `oss-cn-shanghai-internal.aliyuncs.com`
3. **Finance-cloud regions MUST NOT use the template** - they follow a
   separate official naming that the template cannot reproduce. Per the
   official finance-cloud tables (regions-and-endpoints * Finance Cloud):
   `cn-hangzhou-finance` -> extranet `oss-cn-hzfinance.aliyuncs.com`;
   `cn-shenzhen-finance-1` -> `oss-cn-szfinance.aliyuncs.com`;
   `cn-shanghai-finance-1` -> `oss-cn-shanghai-finance-1-pub.aliyuncs.com`;
   `cn-beijing-finance-1` -> `oss-cn-beijing-finance-1-pub.aliyuncs.com`.
   Finance cloud defaults to INTERNAL-only access; the extranet Endpoint is
   needed only for access from outside the finance-cloud environment. Always
   consult the official table (source:
   help.aliyun.com/zh/oss/user-guide/regions-and-endpoints * Finance Cloud).

OSS enforces this strictly: accessing a bucket through another region's
endpoint fails with an AccessDenied-class error (official EC 0003-00001403:
"The bucket you are attempting to access must be addressed using the
specified endpoint. Please send all future requests to this endpoint." -
the error body's `<Endpoint>` element carries the **correct** endpoint to
switch to, i.e. the endpoint of the bucket's actual region). The region can
never be "re-pointed" - the client must change its endpoint (source:
help.aliyun.com/zh/oss/user-guide/0003-00001403).

NOTE (D-10, measured 2026-09-07, 3 buckets x cross-region ListObjects):
the phrasing "The bucket you access does not belong to you" is a DIFFERENT
error (EC 0003-00000001) that occurs when accessing another account's bucket
through the CORRECT endpoint - it is NOT a variant of the cross-region error.
Do not conflate the two: 0003-00001403 = wrong region (fix: switch endpoint);
0003-00000001 = wrong account (fix: verify bucket ownership).

## 3. Internal vs public endpoint selection

Decision order:

1. Client runs on Alibaba Cloud (ECS / container / serverless) in the SAME
   region as the bucket -> use the **internal endpoint**. No public network
   traffic cost, lower latency, no public bandwidth consumed.
2. Client runs on Alibaba Cloud in ANOTHER region -> use the public endpoint
   (or transfer acceleration when cross-border latency matters); internal
   endpoints do not resolve across regions.
3. Client runs outside Alibaba Cloud (office, other clouds) -> use the
   **public endpoint**. Internal endpoints fail DNS from the Internet with
   "no such host" - that failure is expected behavior, not a fault.
4. Custom domain bound to the bucket -> the domain inherits the bucket's
   region; endpoint-region rules still apply to SDK/CLI access.

### 3.1 Same-region ECS security-group rules for OSS access

An ECS that only talks to OSS (no public IP needed) still needs egress
allowed toward the OSS endpoints:

- OSS is reached over HTTP (port 80) / HTTPS (port 443); allow outbound
  80/443 toward the OSS endpoints (source:
  help.aliyun.com/zh/ecs/user-guide/security-groups-for-different-use-cases
  and the OSS reverse-proxy doc below).
- OSS public IPs are NOT fixed and cannot be whitelisted by IP; the
  recommended options are to allow by the OSS domain, or put an ECS reverse
  proxy in front of OSS and whitelist the proxy IP (source:
  help.aliyun.com/zh/oss/user-guide/access-oss-through-ecs-reverse-proxy).
- Same-region ECS using the internal endpoint stays inside the Alibaba
  Cloud network (no public egress), which is the minimal-exposure choice.

### 3.2 Access OSS by bucket domain, never by raw IP

- OSS public endpoint IPs are shared infrastructure serving many accounts'
  buckets; a raw-IP URL (e.g. `http://<oss-ip>/<bucket>/<key>`) does not
  reliably address YOUR bucket and may resolve to another account's
  resources. Always use the bucket domain `<bucket>.<endpoint>`.
- OSS requires the virtual-hosted style (bucket name in the host); access
  must go through the three-level bucket domain: except for the GetService
  (ListBuckets) API, every request must use `BucketName.Endpoint` (e.g.
  `https://example-bucket.oss-cn-hangzhou.aliyuncs.com`); a second-level
  host like `oss-cn-hangzhou.aliyuncs.com/<bucket>/...` is rejected
  (official EC 0003-00001401; source:
  help.aliyun.com/zh/oss/user-guide/access-oss-via-bucket-domain-name and
  the "SecondLevelDomainForbidden" troubleshooting doc).
- Security self-check finding "file reachable via an OSS IP" -> first verify
  via GetBucketInfo / the bucket ACL whether the object belongs to the
  caller's bucket; set the bucket/object to private so reads require
  authentication (manual guidance only; this skill never changes ACLs).

### 3.3 Custom domain (CNAME) troubleshooting path

> SCRIPT COVERAGE (E1): this path is no longer reference-only. `classify_endpoint()`
> now returns `kind="cname"` for a well-formed non-`aliyuncs.com`, non-IP FQDN,
> and `oss_endpoint_diagnosis.py` runs the flow end-to-end: an OS-level DNS
> probe (`resolve_cname_target`) + read-only `ListCname` (`oss:ListCname`) feed
> `evaluate_cname()`, which emits a `CUSTOM_DOMAIN_CNAME_*` verdict
> (NOT_RESOLVED / NOT_BOUND / DISABLED / PENDING / MISRESOLVED / OK / UNKNOWN)
> and projects the 7 steps below into `recommendations`. The verdict list is the
> runtime contract; this section is its knowledge source.

A custom domain bound to a bucket is served through the bucket's own region
endpoint, so endpoint-region rules still apply underneath. When a custom
domain fails but the OSS domain works (or vice versa), check in this order
(source: help.aliyun.com/zh/oss/user-guide/access-buckets-via-custom-domain-names):

1. The CNAME record at the DNS provider really points the custom domain to
   the bucket's public endpoint (`<bucket>.oss-<region>.aliyuncs.com`).
2. The custom domain is bound on the bucket in the OSS console (Bucket ->
   Transmission Management -> Domain Names); an unbound domain returns 403 /
   no bucket resolution even with a correct CNAME.
3. HTTPS on the custom domain requires an SSL certificate hosted by OSS for
   that domain; without it, HTTPS fails while HTTP may still work.
4. Cross-region or overseas clients still pay public-egress traffic and are
   subject to the same region rules; the CNAME does not change billing.
5. If the user's tool accepts only an "endpoint" field, entering the custom
   domain there works only when the SDK is set to CNAME mode
   (`is_cname=True` / equivalent); otherwise the SDK rebuilds a bucket
   domain that bypasses the custom domain and the request misroutes.
6. CNAME dedicated domain (official best practice): instead of pointing the
   custom domain's CNAME at the standard bucket endpoint, OSS provides a
   dedicated intermediate domain of the form
   `<BucketName>.<Region>.<dedicated-suffix>` that serves ONLY as the CNAME
   target (it cannot be accessed directly). It decouples the custom
   domain's resolution chain from `aliyuncs.com`, keeping access stable
   when the standard endpoint has resolution anomalies or is blocked
   (source: help.aliyun.com/zh/oss/user-guide/dedicated-cname-domain-best-practices).
7. ICP filing: for buckets in mainland-China regions, a custom domain must
   have completed ICP filing before it can be bound (official precondition
   in the dedicated-CNAME and custom-domain docs).

### 3.4 Bucket Policy VPC condition semantics

Bucket Policy supports restricting access by network origin via condition
keys such as `acs:SourceVpc` (and IP-based keys like `acs:SourceIp`)
(source: help.aliyun.com/zh/oss/user-guide/authorization-syntax-and-elements
and the bucket-policy examples):

- A policy that Allows only when `acs:SourceVpc` equals specific VPC IDs
  denies every request that does not arrive through one of those VPCs -
  including same-region ECS behind a NAT gateway with a public egress IP,
  which arrives with a public source IP instead of a VPC identity.
- Deny entries are evaluated with deny-priority: one explicit Deny (in
  Bucket Policy or RAM policy) rejects the request even if another policy
  allows it.
- A request through the public endpoint never carries a VPC identity, so
  VPC-condition policies are enforced in combination with the endpoint
  choice: internal/VPC access and public access can get different verdicts
  from the same policy set.
- Diagnosis tip: when access works from the internal endpoint but fails
  from the public endpoint (or from one VPC but not another), read the
  bucket's Bucket Policy for `acs:SourceVpc` / `acs:SourceIp` conditions
  before blaming the endpoint itself (read-only inspection; this skill
  never edits policies).

## 4. Public network traffic cost attribution

- Public network traffic cost is generated ONLY by egress through the public
  endpoint (downloads / reads from the Internet side). Same-region internal
  traffic is free of that charge.
- Ingress (uploads) is free, and internal-network egress of the same region
  is free; only public egress (internet outbound traffic) is billed, with
  off-peak / peak unit prices (source: OSS pricing page,
  aliyun.com/price/detail/oss).
- Requests that reach OSS through the internal endpoint from same-region
  Alibaba Cloud services (e.g. console-side operations) do not generate
  public network traffic cost. For "which request is billing me" questions,
  correlate the real-time log (endpoint / network-type fields distinguish
  internal vs public requests) with the bill items; note hourly billing
  data trails real time.
- OSS real-time log query itself does not create traffic charges. Under the
  pay-by-feature LogStore mode it is FREE while BOTH hold:
  retention <= 7 days AND the daily compressed write traffic OR index traffic
  <= **900 GB** (~ 900 million records/day at 1 KB per access log). Exceeding
  either makes SLS charge storage + index-traffic fees. The real-time-query
  Shard quota is free up to **16*31 shard*days/month**; beyond that SLS charges
  separately. A dedicated LogStore's read traffic, external-network traffic,
  data transformation and delivery are billed at standard rates (G-7; source:
  help.aliyun.com/zh/sls/usage-notes-of-oss-access-log/).
- Common root causes of unexpected public network traffic cost:
  - same-region ECS configured with the public endpoint instead of the
    internal endpoint (configuration error, the top scenario);
  - third-party services or office clients pulling through the public
    endpoint (expected behavior - explain the charging rule);
  - CDN back-to-origin hitting the public endpoint. Official rule
    (help.aliyun.com/zh/cdn/product-overview/billing-of-oss-content-acceleration):
    the CDN-side back-to-origin traffic (CDN node fetching from OSS) is NOT
    billed; what OSS bills is the "OSS outbound-to-CDN traffic". It is
    recognized as the DISCOUNTED "CDN back-to-origin outbound traffic" ONLY
    when the console origin type is set to "OSS Domain"; if the origin type is
    mis-set to "Origin (source-station) Domain", OSS recognizes it
    as "Internet outbound traffic" and the discount is lost. When BOTH the CDN back-to-origin
    node and the OSS bucket are outside mainland China, the OSS->CDN traffic is
    FREE (G-5). NOTE (B-10): the official doc says NOTHING about third-party
    CDN (e.g. Tencent Cloud CDN); the idea that a non-Alibaba CDN pulling
    through the public endpoint is billed as standard public egress is a
    reasonable INFERENCE, not an official statement - do not cite it as
    official.
- Public-read bucket ACL exposes unsigned URLs to anyone; unexpected
  download traffic often traces back to a public-read ACL plus leaked
  object URLs - check the ACL as part of traffic attribution (read-only;
  changing the ACL is manual guidance).
- This skill explains WHY the traffic is generated via which endpoint. For
  bill deductions, resource packs (a storage pack does NOT cover traffic),
  and pricing questions, defer to alibabacloud-oss-billing-diagnosis.
- **Per-bucket traffic attribution** (batch2 billing --bucket-usage referral):
  when the diagnosis identifies public-network traffic cost but the user needs
  to know WHICH bucket generates the most outbound traffic, refer to
  `alibabacloud-oss-billing-diagnosis --bucket-usage` which provides
  NetOut/CdnOut per-bucket breakdown data. This skill only diagnoses the
  endpoint-level cause (public vs internal path); billing provides the
  per-resource attribution.

## 5. Validation recipe (mirrors scripts/oss_endpoint_diagnosis.py)

1. Parse the user's endpoint string: classify public / internal /
   accelerate / dualstack / cname / invalid; extract its region.
2. Fetch the bucket's `location`, `intranet_endpoint`, `extranet_endpoint`
   via GetBucketInfo (fall back to ListBuckets location lookup on failure).
3. Compare the endpoint's region with the bucket location:
   matched / mismatch / unknown.
4. Emit the recommendation per section 3 and attribute the traffic cost per
   section 4.

## 6. Internal boundary declaration: cross-skill keyword collision (deferred)

This section records a scoping decision so the next iteration does not
re-litigate it (E7).

- **Known issue:** this skill's measured routing precision is low (~33%) and
  roughly two-thirds of its ticket hits are actually traffic-billing or
  client-tool questions that are double-counted with the billing and
  client-tools pools. The dominant cause is **cross-skill keyword collision**
  ("traffic / fee / public-network" pull billing traffic here; "ossutil / ossbrowser / cannot-connect"
  pull client-tool traffic here), not a missing in-domain branch.
- **Decision (this round):** word-list disambiguation is **NOT** done here.
  It must be bound to the platform's dynamic evaluation (the trigger/routing
  judge), because static description edits cannot be validated against real
  routing behaviour offline and risk lowering recall for genuine endpoint
  tickets. The `description` frontmatter is therefore intentionally left
  unchanged this round.
- **Already built and hardened as runtime guidance (defer referrals):** the script and
  this reference route the colliding intents outward at runtime instead of
  answering them in-domain:
  - traffic cost / deduction / resource pack / per-bucket attribution ->
    `alibabacloud-oss-billing-diagnosis` (`--bucket-usage` for NetOut/CdnOut).
  - ossutil / ossbrowser / SDK client behaviour, probe, concurrency ->
    `alibabacloud-oss-client-tools-diagnosis`.
  - error-code / EC-number semantics -> `alibabacloud-oss-transfer-error-code-diagnosis`.
  - custom-domain downstream (static site / preview / hotlink / CDN origin) ->
    `alibabacloud-oss-static-website-diagnosis`,
    `alibabacloud-oss-direct-access-link-diagnosis`,
    `alibabacloud-oss-cdn-origin-config-diagnosis`.
- **Revisit trigger:** after the platform dynamic-evaluation first round, use
  the real routing confusion matrix (not offline guessing) to decide whether a
  description/word-list disambiguation is warranted.
