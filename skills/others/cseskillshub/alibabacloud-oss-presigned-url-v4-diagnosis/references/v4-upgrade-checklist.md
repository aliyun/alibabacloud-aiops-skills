# V4 Upgrade Compatibility Checklist

Guidance for migrating from V1 to V4 signing. The full, per-language SDK
steps live in the official guide:
https://help.aliyun.com/zh/oss/developer-reference/guidelines-for-upgrading-v1-signatures-to-v4-signatures

## V1 Retirement Policy (official)

- From 2025-03-01, V1 signing is gradually no longer opened to new customer accounts (new uids).
- From 2025-09-01, V1 stops updates and maintenance and is no longer opened to newly created buckets.
- Existing usage continues during the transition, but V4 is the recommended target for all new development.

Source: the official V1-to-V4 upgrade guide linked above (verified 2026-08).

## Checklist Before Switching

1. **Identify the current signature version.**
   - URL signing V1: query contains `OSSAccessKeyId` + `Expires` + `Signature`.
   - URL signing V4: query contains `x-oss-credential` + `x-oss-date` + `x-oss-expires` + `x-oss-signature`.
   - Header V1: `Authorization` starts with `OSS `.
   - Header V4: `Authorization` starts with `OSS4-HMAC-SHA256`.
2. **Upgrade the SDK/ossutil** to a version that supports signature version 4 and enable V4 in the client configuration (per-language steps in the official upgrade guide).
3. **Set the region explicitly.** V4 embeds the region in the credential scope (`AccessKeyId/date/region/oss/aliyun_v4_request`); it must match the bucket's actual region. A wrong region typically surfaces as `AuthorizationHeaderMalformed`.
4. **STS scenarios:** keep passing the security token (`x-oss-security-token` in URLs; SecurityToken in SDKs).
5. **Regenerate circulating presigned URLs** as V4 after the upgrade; discard old V1 links.
6. **Do not keep a silent V1 fallback** that downgrades signing on error; failures should stay visible so misconfiguration is caught.

## Compatibility Notes (ticket-based)

- Presigned-URL consumers (downloaders/uploaders) need no change: they just follow the URL; only the generator side must be upgraded.
- A presigned URL remains bound to the HTTP method used at signing after the upgrade; keep separate URLs for upload vs download.
- Maximum validity: 604800 seconds (7 days) for a long-term AccessKey; 43200 seconds (12 hours) for an STS temporary credential. V4 expiry counts from `x-oss-date`, so store and compare times in UTC.
- Recommended baseline for all new requests: V4 header signature per https://help.aliyun.com/zh/oss/developer-reference/recommend-to-use-signature-version-4
