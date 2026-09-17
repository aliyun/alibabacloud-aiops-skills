# Bypass Detection: Traffic Reaching OSS Directly Instead of CDN

"Traffic bypasses the CDN" means client requests are addressed to the OSS
bucket endpoint (e.g. `<bucket>.oss-<region>.aliyuncs.com`) instead of the
CDN accelerated domain, so every request becomes a direct OSS read: no edge
cache, OSS internet traffic cost, and none of the CDN protections apply.

## Evidence this skill collects (read-only)

| Evidence | Source | Meaning |
|---|---|---|
| Configured origin list | DescribeCdnDomainDetail (`Sources`) | what CDN itself uses on back-to-origin |
| User-reported origin host | `--user-origin-host` argument | the host the user's traffic actually targets |
| Bucket endpoint shape | pattern `<bucket>.oss-<region>.aliyuncs.com` | a direct OSS address, not an accelerated domain |

Decision logic implemented by `origin_config_diagnosis.py`:

1. The reported host matches the OSS endpoint shape **and is not** among the
   CDN-configured origins -> `DIRECT_OSS_ACCESS` (bypass confirmed at the
   addressing level).
2. The reported host matches an OSS endpoint shape **and equals** a
   configured origin -> `DIRECT_OSS_HOST_MATCHES_ORIGIN`: the CDN origin is
   the same bucket, so the bypass is in the client addressing / DNS layer.
3. Any other mismatch between the reported host and the configured origins ->
   `ORIGIN_HOST_MISMATCH` (configuration divergence, investigate).

## Typical root causes (guidance)

- **Hardcoded OSS URLs** in the website/app/SDK: the client points at
  `<bucket>.oss-<region>.aliyuncs.com` instead of the accelerated domain.
  Fix: rewrite the public URLs to the accelerated domain.
- **DNS CNAME missing**: the accelerated domain resolves to the OSS bucket
  (or nowhere) instead of the CDN CNAME. Fix: set the CNAME record of the
  accelerated domain to the CDN-assigned CNAME target (visible in the CDN
  console; the diagnosis report records the `Cname` field).
- **Wrong entry point**: downloads/links shared with the OSS host. Fix:
  regenerate the links with the accelerated domain.

## What this skill deliberately does NOT do

- No active probing or mutation of DNS records.
- No traffic measurement comparison (that belongs to CDN traffic analysis /
  billing diagnosis skills, not this configuration check).
- No rewrite of any client configuration — manual guidance only.

## The reverse bypass: CDN edge cache defeating OSS hotlink protection (G-6)

The mirror image of "traffic bypasses the CDN" is "protection bypasses OSS".
Official rule (help.aliyun.com/zh/oss/user-guide/hotlink-protection ·
CDN cache bypass risk): when an OSS resource is accelerated by CDN, a hotlink
request may hit the CDN EDGE CACHE and be served WITHOUT ever reaching OSS,
so the OSS Referer whitelist/blacklist is NEVER evaluated. A user who
"configured OSS hotlink protection but the theft traffic did not drop" is
almost always in this branch — the OSS rules are correct, they simply are not
in the request path. Official fix: configure the SAME Referer rules at the
CDN layer (multi-layer defense).

Diagnostic hand-off: the Referer rule semantics, the empty-referer/blacklist
attribution and the verdict table belong to
alibabacloud-oss-direct-access-link-diagnosis (references/referer-rules.md,
which carries the matching CDN-cache-bypass note). This skill contributes the
CDN-side view: whether the accelerated domain is configured and whether the
origin is the OSS bucket, i.e. whether an edge cache sits in front of OSS at
all.
