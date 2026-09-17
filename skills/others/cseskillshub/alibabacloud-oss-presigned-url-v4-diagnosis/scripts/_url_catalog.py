#!/usr/bin/env python3
# SECURITY: read-only knowledge module; only loaded by the entry script after
# SKILL.md confirmation; operates purely on user-supplied URL/error text.
"""Presigned-URL failure-mode catalog (embedded constant, no data files).

Distilled from the official Alibaba Cloud OSS documentation (verified
2026-08) and from support-ticket clustering of presigned-URL failures
(approx. 130 tickets/month in the signature/share-link cluster). Official
sources used for every factual claim:

  - V4 signature in URL (x-oss-credential / x-oss-date / x-oss-expires /
    x-oss-signature; expiry counted from x-oss-date, max 604800 s = 7 days for
    a long-term AccessKey, max 43200 s = 12 hours for an STS temporary
    credential):
    https://help.aliyun.com/zh/oss/developer-reference/add-signatures-to-urls
  - V1 signature in URL (OSSAccessKeyId / Expires / Signature):
    https://help.aliyun.com/zh/oss/add-signatures-to-urls-14
  - V1-to-V4 upgrade guide and the V1 retirement policy (from 2025-03-01
    V1 is gradually closed to new customer accounts/new uids; from
    2025-09-01 V1 stops updates/maintenance and is no longer opened to
    newly created buckets):
    https://help.aliyun.com/zh/oss/developer-reference/guidelines-for-upgrading-v1-signatures-to-v4-signatures
  - V4 header signature recommended format (Authorization with
    OSS4-HMAC-SHA256): https://help.aliyun.com/zh/oss/developer-reference/recommend-to-use-signature-version-4
  - Presigned URL download/preview and expiration behavior:
    https://help.aliyun.com/zh/oss/user-guide/how-to-obtain-the-url-of-a-single-object-or-the-urls-of-multiple-objects
  - Presigned URL upload:
    https://help.aliyun.com/zh/oss/user-guide/upload-files-using-presigned-urls
  - V4 error 0002-00000216 when x-oss-expires is empty:
    https://help.aliyun.com/zh/oss/user-guide/0002-00000216

Ticket-based root-cause clusters (real support cases, anonymized):
  expired link, clock skew beyond the +/-15 minute window, signature
  version forbidden (V1 retired), URL parameter tampering, credential
  rotation/STS expiry, permission change after signing, wrong HTTP method,
  malformed signature parameters.
"""

DOC_V4_URL_SIGN = "https://help.aliyun.com/zh/oss/developer-reference/add-signatures-to-urls"
DOC_V1_URL_SIGN = "https://help.aliyun.com/zh/oss/add-signatures-to-urls-14"
DOC_V4_UPGRADE = "https://help.aliyun.com/zh/oss/developer-reference/guidelines-for-upgrading-v1-signatures-to-v4-signatures"
DOC_V4_HEADER = "https://help.aliyun.com/zh/oss/developer-reference/recommend-to-use-signature-version-4"
DOC_PRESIGNED_DOWNLOAD = "https://help.aliyun.com/zh/oss/user-guide/how-to-obtain-the-url-of-a-single-object-or-the-urls-of-multiple-objects"
DOC_PRESIGNED_UPLOAD = "https://help.aliyun.com/zh/oss/user-guide/upload-files-using-presigned-urls"
DOC_V4_EXPIRES_EMPTY = "https://help.aliyun.com/zh/oss/user-guide/0002-00000216"
DOC_EC_EXPIRED = "https://help.aliyun.com/zh/oss/user-guide/0002-00000069"
DOC_EC_SIGN_MISMATCH = "https://help.aliyun.com/zh/oss/user-guide/0002-00000040"
DOC_EC_TOKEN_IN_URL = "https://help.aliyun.com/zh/oss/user-guide/0002-00000005"
DOC_CUSTOM_DOMAIN_ACCESS = "https://help.aliyun.com/zh/oss/user-guide/access-buckets-via-custom-domain-names"
DOC_CUSTOM_DOMAIN_HTTPS = "https://help.aliyun.com/zh/oss/user-guide/access-oss-by-https-protocol"
DOC_CUSTOM_DOMAIN_SDK = "https://help.aliyun.com/zh/oss/developer-reference/use-custom-domain-names"

# Maximum validity of a presigned URL depends on the credential type used to
# sign it (official V4-in-URL documentation, add-signatures-to-urls):
#   - long-term AccessKey: x-oss-expires max 604800 seconds (7 days);
#   - STS temporary credential: x-oss-expires max 43200 seconds (12 hours).
# For V1 the Expires parameter is an absolute UNIX epoch; for V4 the expiry is
# computed as x-oss-date + x-oss-expires and x-oss-expires must not exceed the
# cap that matches the signing credential. The credential type is detected from
# the URL: a V4 URL carrying x-oss-security-token (or security-token) is
# STS-signed and therefore capped at 43200 seconds.
MAX_PRESIGNED_TTL_SECONDS_LONG_TERM_AK = 604800   # 7 days, long-term AccessKey
MAX_PRESIGNED_TTL_SECONDS_STS = 43200             # 12 hours, STS temporary credential
# Backward-compatible alias: the historical single-cap name now resolves to the
# long-term AccessKey cap (the more permissive of the two).
MAX_PRESIGNED_TTL_SECONDS = MAX_PRESIGNED_TTL_SECONDS_LONG_TERM_AK

# OSS allows at most +/- 15 minutes (900 seconds) clock skew between the
# request timestamp and server time (RequestTimeTooSkewed, EC 0002-00000504).
MAX_CLOCK_SKEW_SECONDS = 900

# Signature URL forms: query-parameter fingerprint per signature version.
SIGNATURE_URL_FORMS = {
    "v1": {
        "label": "V1 presigned URL (OSSAccessKeyId + Expires + Signature)",
        "required_params": ["OSSAccessKeyId", "Expires", "Signature"],
        "expiry_param": "Expires",
        "expiry_meaning": "absolute UNIX epoch seconds",
        "official_doc_ref": DOC_V1_URL_SIGN,
    },
    "v4": {
        "label": "V4 presigned URL (x-oss-credential + x-oss-date + x-oss-expires + x-oss-signature)",
        "required_params": [
            "x-oss-credential", "x-oss-date", "x-oss-expires", "x-oss-signature",
        ],
        "optional_params": ["x-oss-signature-version", "x-oss-additional-headers",
                            "x-oss-security-token"],
        "expiry_param": "x-oss-expires",
        "expiry_meaning": "seconds after x-oss-date (max 604800 = 7 days for a long-term AccessKey; max 43200 = 12 hours for an STS temporary credential)",
        "credential_scope_format": "AccessKeyId/date/region/oss/aliyun_v4_request",
        "official_doc_ref": DOC_V4_URL_SIGN,
    },
    "v2": {
        "label": "Legacy V2 signature (rare; superseded by V4)",
        "required_params": ["OSSAccessKeyId", "Expires", "Signature"],
        "marker_param": "x-oss-signature-version=OSS2",
        "expiry_param": "Expires",
        "expiry_meaning": "absolute UNIX epoch seconds",
        "official_doc_ref": DOC_V1_URL_SIGN,
    },
}

# Failure-mode catalog. side: 'client' = fix on the requester/owner side;
# 'owner' = the bucket/object owner must act (regenerate or re-authorize).
FAILURE_MODES = {
    "expired": {
        "mode": "expired",
        "label": "Presigned URL expired",
        "http_status": 403,
        "side": "owner",
        "root_cause_directions": [
            "The URL validity window has passed: V1 Expires (epoch) or V4 x-oss-date + x-oss-expires is in the past (official EC 0002-00000069)",
            "The link was generated with a short TTL and shared beyond that window",
            "Client clock is far ahead of real time, so a still-valid URL is judged expired locally or the signed timestamp fails server-side checks",
            "Inverse symptom - an expired URL still works: a CDN/proxy in front of the custom domain cached the response or ignores URL parameters when caching, so expiry is not enforced; align the CDN cache TTL with the URL validity window or bypass the CDN to verify",
        ],
        "troubleshooting_steps": [
            "Extract the expiry from the URL (V1: Expires epoch; V4: x-oss-date + x-oss-expires) and compare with the current UTC time",
            "Ask the bucket owner to regenerate the presigned URL with a sufficient TTL (maximum 604800 seconds = 7 days for a long-term AccessKey; maximum 43200 seconds = 12 hours for an STS temporary credential)",
            "Console-generated URLs allow at most 32400 seconds (9 hours) with a 3600-second default; use the SDK or ossutil to customize the TTL up to the 604800-second maximum (long-term AccessKey) or the 43200-second maximum (STS temporary credential)",
            "Store and compare all times in UTC to avoid timezone mistakes",
            "For long-lived sharing, regenerate on demand instead of circulating a static long-lived URL; OSS has no built-in auto-renewal, refresh the URL in application code before or after expiry",
        ],
        "official_doc_ref": DOC_EC_EXPIRED,
    },
    "clock_skew": {
        "mode": "clock_skew",
        "label": "Clock skew beyond the +/-15 minute window",
        "http_status": 403,
        "side": "client",
        "root_cause_directions": [
            "Client device clock differs from the OSS server time by more than 15 minutes (900 seconds), producing RequestTimeTooSkewed (EC 0002-00000504)",
            "A signed request sat in a client retry/network queue so long that the signing timestamp became stale before it reached OSS",
        ],
        "troubleshooting_steps": [
            "Compare the device/system clock with real UTC time; enable automatic time synchronization (NTP)",
            "If the error is intermittent, check weak-network/retry behavior that delays queued requests after signing",
            "Timezone misconfiguration produces hour-scale offsets; a skew of minutes points to clock drift, not timezone",
        ],
        "official_doc_ref": DOC_V4_HEADER,
    },
    "v1_signature_forbidden": {
        "mode": "v1_signature_forbidden",
        "label": "V1 signature no longer allowed - upgrade to V4",
        "http_status": 403,
        "side": "client",
        "root_cause_directions": [
            "The account (new uid) was created after the V1 retirement cut-over and cannot use V1 signing",
            "A newly created bucket no longer accepts V1 signatures (per the official V1 retirement policy)",
            "Client/SDK still signs with V1 while the service requires V4",
            "The SDK version is below the minimum that supports V4 signing, so requests silently fall back to V1 even when V4 was configured; upgrading the SDK is required before V4 takes effect",
            "The AccessKey was created after the V1 cut-over date, and keys created after that date cannot use V1 signatures",
        ],
        "troubleshooting_steps": [
            "Confirm the client currently uses V1 (URL contains OSSAccessKeyId+Expires+Signature, or Authorization starts with 'OSS ')",
            "Upgrade the client/SDK to V4 following the official V1-to-V4 upgrade guide; for SDK clients this is a configuration switch plus region setting, no hand-written signing code",
            "Regenerate any circulating V1 presigned URLs as V4 URLs after the upgrade",
        ],
        "official_doc_ref": DOC_V4_UPGRADE,
    },
    "v4_unavailable_fallback_v1": {
        "mode": "v4_unavailable_fallback_v1",
        "label": "V4 signing unavailable in this environment - fall back to V1",
        "http_status": 403,
        "side": "client",
        "root_cause_directions": [
            "The bucket sits in a special/legacy region where the client's V4 signing is not supported yet, so V4-signed requests fail while V1 still works",
            "An old client tool (e.g. an old ossbrowser build) has no V4 signing support at all and can only sign with V1",
            "The SDK/tool version predates V4 support for that region and cannot be upgraded in the short term",
        ],
        "troubleshooting_steps": [
            "Confirm the failing requests are signed with V4 (URL carries x-oss-credential/x-oss-date/x-oss-expires/x-oss-signature, or Authorization starts with OSS4-HMAC-SHA256) and the bucket region is a special/legacy region",
            "This is the symmetric exception of v1_signature_forbidden: where V4 is unavailable, falling back to V1 signing is the ticket-proven workaround - configure the client to sign V1 for this environment",
            "For ossbrowser: upgrade to the latest version that supports V4; keep the V1 fallback only until the upgrade is possible",
            "Keep the fallback explicit and scoped to the affected region/tool; do not silently downgrade all signing to V1",
        ],
        "official_doc_ref": DOC_V4_UPGRADE,
    },
    "long_term_private_access": {
        "mode": "long_term_private_access",
        "label": "Long-term secure access to private objects (alternatives to static presigned URLs)",
        "http_status": 0,
        "side": "owner",
        "root_cause_directions": [
            "A static presigned URL circulating for long-term sharing conflicts with the maximum TTL (604800 seconds = 7 days for a long-term AccessKey, 43200 seconds = 12 hours for an STS temporary credential) and accumulates leak risk",
            "The bucket/object is private and requesters need durable but controlled access without making it public",
        ],
        "troubleshooting_steps": [
            "Regenerate presigned URLs on demand in application code with a short TTL refreshed before expiry, instead of circulating one static long-lived URL (OSS has no built-in URL auto-renewal)",
            "For web/app end users, consider CDN with private-bucket back-to-origin plus CDN URL authentication, or an application gateway that issues short-lived signed URLs",
            "For programmatic server-to-server access, prefer a RAM user or STS temporary credentials with least-privilege policies over presigned URLs",
            "Never switch the object/bucket ACL to public-read merely to avoid link expiry",
        ],
        "official_doc_ref": DOC_PRESIGNED_DOWNLOAD,
    },
    "parameter_tampered": {
        "mode": "parameter_tampered",
        "label": "Signed URL parameters altered after signing",
        "http_status": 403,
        "side": "client",
        "root_cause_directions": [
            "The URL was edited after signing: object path, expiry value, or any signed query parameter changed, so the signature no longer matches (SignatureDoesNotMatch)",
            "A proxy/CDN/gateway re-encoded or re-ordered query parameters or the object path between signer and OSS",
            "The URL was double-encoded or partially decoded when copied (e.g. %2F handling differs between generator and requester)",
            "A proxy in front of the client added or rewrote request headers after signing: x-oss-* headers, Content-Type and Content-MD5 participate in the signature by default, so any proxy-injected or proxy-modified header of these breaks the signature (cse playbook-signature step 4.3)",
            "Hand-assembled V4 signature (not via SDK): CanonicalRequest construction mistakes are the dominant cause -- the SignedHeaders list omits a header that is actually sent (e.g. content-type), headers are not lowercased and alphabetically sorted, or the canonical path/query is not URI-encoded per the canonical form (cse playbook-signature step 4.4)",
            "Official SignatureDoesNotMatch causes (EC 0002-00000040): a client proxy added/modified headers after signing; CDN converts HEAD to GET when back-to-origin (configure the Ali-Swift-Fwd-Head origin header or use the OSS default domain); CDN injects x-oss-* headers (e.g. x-oss-range-behavior) that must then be included in the signature; the endpoint is a CNAME domain but the client's CNAME switch is off; the signature value contains a plus sign (+) that was not URL-encoded (must be %2B); mini-program clients (e.g. WeChat) attach an extra Content-Type that must also enter the StringToSign",
        ],
        "troubleshooting_steps": [
            "Compare the failing URL character-by-character with the URL the owner generated; any difference besides whitespace breaks the signature",
            "Regenerate the URL and test it immediately without any intermediate rewriting",
            "If a proxy/CDN sits in front of OSS, bypass it and request the OSS endpoint directly to isolate parameter rewriting",
            "Compare the StringToSign returned in the error body with what the client computed to localize the divergence (official EC 0002-00000040 step 3)",
            "URL-encode the signature value (plus sign -> %2B) and enable the CNAME switch when signing against a CNAME endpoint",
            "When hand-signing V4 (not via SDK), verify the four mandatory V4 elements: x-oss-content-sha256, x-oss-date, the SignedHeaders list (lowercase, sorted, complete -- every header it lists must actually be sent and vice versa), and the region inside the credential scope (cse playbook-signature P3 four-element checklist)",
            "Do NOT reverse-engineer the client's construction from the CanonicalRequest echoed by the server: the server-side value is the server's own recomputation of what it received, not a transcript of what the client sent; debug the client-side intermediate values layer by layer instead (StringToSign -> CanonicalRequest -> signed headers, cse playbook-signature step 4.5 / anti-pattern P7)",
        ],
        "official_doc_ref": DOC_EC_SIGN_MISMATCH,
    },
    "credential_invalid": {
        "mode": "credential_invalid",
        "label": "Signing credential changed or invalidated after the URL was issued",
        "http_status": 403,
        "side": "owner",
        "root_cause_directions": [
            "The AccessKey used to sign the URL was rotated, disabled, or deleted after the URL was shared (SignatureDoesNotMatch or InvalidAccessKeyId)",
            "The URL was signed with an STS temporary credential whose security token expired",
            "The AccessKey Secret paired with the AccessKey ID is wrong on the generator side",
            "For STS-signed URLs the security token must ride in the URL as the security-token query parameter (or x-oss-security-token in V4 URLs); placing it only in a request header is rejected for URL-signed requests (official EC 0002-00000005)",
        ],
        "troubleshooting_steps": [
            "Ask the owner whether the signing AccessKey was rotated/disabled since the URL was generated; if yes, regenerate the URL with a current credential",
            "For STS-signed URLs, check that the token lifetime covers the sharing window; otherwise regenerate with a longer-lived STS session or a long-term key within policy",
            "Verify the AccessKey ID/Secret pair on the generator is current and enabled",
            "For STS-signed URLs, confirm the token is carried inside the URL (security-token parameter), not only in an x-oss-security-token header (official EC 0002-00000005)",
        ],
        "official_doc_ref": DOC_EC_TOKEN_IN_URL,
    },
    "permission_changed": {
        "mode": "permission_changed",
        "label": "Authorization changed after the URL was signed",
        "http_status": 403,
        "side": "owner",
        "root_cause_directions": [
            "RAM permission of the signing identity was revoked or narrowed after signing; presigned URLs inherit the signer's permissions",
            "A Bucket Policy deny rule (e.g. source-IP/VPC restriction) blocks the request; presigned URLs do NOT bypass Bucket Policy",
            "The signing identity's AccessKey is bound to a network-policy / IP-whitelist restriction (e.g. the RAM user's AK denies public-internet access): the signature itself is valid, but requests from disallowed networks are rejected, so a valid presigned URL 'does not open' from the public internet (ticket-verified cause U2)",
            "The object ACL/object state changed, or the object/bucket was deleted (then the error is 404 NoSuchKey/NoSuchBucket instead)",
        ],
        "troubleshooting_steps": [
            "Ask the owner whether RAM policies, Bucket Policy, or ACLs changed since the URL was generated",
            "Check whether the request source (public IP vs VPC) matches any Bucket Policy condition",
            "For a valid URL that fails only from certain networks, check the signing AK's network policy / IP whitelist on the RAM side (public-access restriction) in addition to Bucket Policy",
            "Confirm the object still exists and the bucket is in the expected region",
        ],
        "official_doc_ref": DOC_PRESIGNED_DOWNLOAD,
    },
    "method_mismatch": {
        "mode": "method_mismatch",
        "label": "HTTP method differs from the one used at signing",
        "http_status": 403,
        "side": "client",
        "root_cause_directions": [
            "A presigned URL is bound to the HTTP method used when signing; a GET-signed URL requested with PUT (or vice versa) fails signature verification",
            "A tool changed the request method automatically (e.g. redirect-following converted POST to GET)",
        ],
        "troubleshooting_steps": [
            "Confirm the actual request method matches the method used when generating the presigned URL",
            "Generate a separate presigned URL per HTTP method needed (one for upload, one for download)",
        ],
        "official_doc_ref": DOC_PRESIGNED_UPLOAD,
    },
    "sdk_config_misuse": {
        "mode": "sdk_config_misuse",
        "label": "SDK client configuration misuse breaks the signature (pathStyleAccess / CNAME switch)",
        "http_status": 403,
        "side": "client",
        "root_cause_directions": [
            "pathStyleAccess is enabled while the endpoint is a virtual-hosted-style domain (or the reverse mismatch): the SDK then builds a different CanonicalizedResource than the service expects and every request fails SignatureDoesNotMatch even though the AK/SK pair is correct (cse playbook-signature step 4.2)",
            "The client signs against a custom-domain (CNAME) endpoint with the CNAME switch OFF: the SDK splits the CNAME into bucket + default domain and signs the wrong host/path; enable cname=true / is_cname=True so the domain is treated as the endpoint itself",
            "The SDK version predates V4 support and silently falls back to V1 signing while the service requires V4, so requests fail even when V4 was the intended configuration",
        ],
        "troubleshooting_steps": [
            "When the AK/SK pair is verified correct but SignatureDoesNotMatch persists, check the client configuration FIRST (cse playbook-signature step 4.2): the pathStyleAccess setting, the CNAME switch, and the signature-version setting must match the endpoint form actually used",
            "Align the three elements: endpoint form (virtual-host style / path style / custom domain), the corresponding client switch, and the region setting embedded in the V4 credential scope",
            "Upgrade the SDK to a version with V4 support and set the signature version explicitly instead of relying on the silent default",
        ],
        "official_doc_ref": DOC_V4_HEADER,
    },
    "malformed_url": {
        "mode": "malformed_url",
        "label": "Malformed or incomplete signature parameters",
        "http_status": 400,
        "side": "client",
        "root_cause_directions": [
            "A required signature parameter is missing or empty (e.g. empty x-oss-expires produces error 0002-00000216)",
            "Official URL-signature parameter EC family: 0002-00000067 Expires missing, 0002-00000068 Expires empty, 0002-00000070 Expires/x-oss-expires not a valid second-level UNIX timestamp, 0002-00000071 OSSAccessKeyId missing, 0002-00000072 OSSAccessKeyId empty, 0002-00000073 OSSAccessKeyId contains invalid characters, 0002-00000074 Signature missing, 0002-00000075 Signature empty, 0002-00000066 x-oss-signature-version value invalid (V1 needs none, V2 needs OSS2)",
            "x-oss-expires exceeds the maximum allowed for the signing credential: 604800 seconds (7 days) for a long-term AccessKey, or 43200 seconds (12 hours) for an STS temporary credential",
            "x-oss-credential does not follow the format AccessKeyId/date/region/oss/aliyun_v4_request, or the region in the credential scope does not match the bucket region (wrong region typically surfaces as AuthorizationHeaderMalformed)",
            "x-oss-date is not in the basic ISO-8601 form YYYYMMDDTHHmmssZ",
            "URL signature and header signature are mixed in one request: OSS rejects a request that carries both the Signature query parameter and an Authorization header ('Either the Signature query string parameter or the Authorization header should be specified, not both'); a common trigger is using an OSS presigned URL behind CDN private-bucket back-to-origin, which injects its own Authorization header",
        ],
        "troubleshooting_steps": [
            "Validate every signature parameter against the official format before sharing the URL",
            "Keep x-oss-expires within the cap for the signing credential (604800 seconds for a long-term AccessKey; 43200 seconds for an STS temporary credential); split longer sharing into regenerated links",
            "Ensure the region in x-oss-credential equals the bucket's actual region",
            "Prefer SDK-generated URLs over hand-assembled ones; SDKs keep parameter format correct",
            "Keep exactly one authentication mechanism per request: when a CDN with private-bucket back-to-origin fronts the bucket, use CDN URL authentication instead of an OSS presigned URL so no Authorization header is injected",
        ],
        "official_doc_ref": DOC_V4_EXPIRES_EMPTY,
    },
    "custom_domain_presigned": {
        "mode": "custom_domain_presigned",
        "label": "Presigned URL served from a custom domain (CNAME) endpoint",
        "http_status": 0,
        "side": "owner",
        "root_cause_directions": [
            "The share link must be generated with the custom domain itself as the endpoint (the bucket-bound CNAME), not the default '<bucket>.oss-<region>.aliyuncs.com' domain; the signing algorithm and parameters are identical, only the host differs (ticket 0001FRR89N basis)",
            "Both http and https presigned URLs over a custom domain are technically valid; https requires an SSL certificate hosted for that domain on OSS first - without it, only http works (official HTTPS-access doc)",
            "The client/SDK signs against the CNAME endpoint with the CNAME switch OFF, so the endpoint is parsed as a third-level-bucket default domain and the signature mismatches (SignatureDoesNotMatch)",
        ],
        "troubleshooting_steps": [
            "Bind the custom domain to the bucket first (Bucket Settings > Domain Management > Bind Domain) and add the CNAME DNS record, per the official custom-domain access guide",
            "Generate the presigned URL with the custom domain as the endpoint; http presigned URLs work immediately, and an https presigned URL additionally requires hosting an SSL certificate for the domain on OSS",
            "In the SDK, enable the custom-domain option when signing against a CNAME endpoint (e.g. cname=true / is_cname=True in the client configuration) so the domain is treated as the endpoint, not split into bucket + default domain",
            "Keep the URL TTL within the maximum for the signing credential (604800 seconds = 7 days for a long-term AccessKey; 43200 seconds = 12 hours for an STS temporary credential) as with default-domain presigned URLs",
        ],
        "official_doc_ref": DOC_CUSTOM_DOMAIN_ACCESS,
    },
}

# Routing: error code (canonical, case-insensitive) -> candidate failure modes.
ERROR_CODE_ROUTES = {
    "SignatureDoesNotMatch": ["parameter_tampered", "credential_invalid",
                              "method_mismatch", "v1_signature_forbidden"],
    "InvalidAccessKeyId": ["credential_invalid"],
    "SecurityTokenExpired": ["credential_invalid"],
    "RequestTimeTooSkewed": ["clock_skew"],
    "AccessDenied": ["expired", "permission_changed", "credential_invalid",
                     "v1_signature_forbidden"],
    "AuthorizationHeaderMalformed": ["malformed_url"],
    "InvalidArgument": ["malformed_url"],
    "AccessForbidden": ["permission_changed"],
}

# Routing: HTTP status -> candidate failure modes.
STATUS_TO_MODES = {
    403: ["expired", "parameter_tampered", "credential_invalid",
          "permission_changed", "clock_skew", "method_mismatch"],
    400: ["malformed_url", "clock_skew"],
    404: ["permission_changed"],
}

# Routing: symptom keywords (lowercase substring) -> candidate failure modes.
#
# Design rules (eval fix PR-2/PR-3/PR-4/PR-10, ticket-verified):
#   1. No single ambiguous CJK key may own 'expired': the generic '签名' key
#      maps to tampering/credential causes only -- expiry needs an explicit
#      expiry word (过期/失效/expire/...) plus URL/link context.
#   2. 'v4' alone is NOT a routing key: V4-unavailable fallback needs a
#      compound wording (v4 不可用/v4 关闭/...), a special-region or an
#      old-tool marker; generic V4 talk routes to tampering/SDK-config causes.
#   3. 'cdn' is NOT a routing key: CDN back-to-origin wording transfers out
#      via the domain-transfer guards in the entry script (cdn-origin-config
#      skill); only the cache inverse-symptom keys (cache/缓存) remain here.
#   4. Precise compound keys (签名不匹配/签名错误/手动签名/...) outrank
#      generic keys because the entry script iterates longest-key-first.
#
# NOTE on the 'expired' route: the entry script applies subject
# discrimination -- 'expired' only survives when the symptom text carries
# URL/link/signature context; resource-package/plan subjects are excluded
# (they belong to billing diagnosis, not presigned-URL diagnosis).
SYMPTOM_KEYWORDS = {
    "expire": ["expired"],
    "过期": ["expired"],
    "clock": ["clock_skew"],
    "skew": ["clock_skew"],
    "时间": ["clock_skew", "expired"],
    "v1": ["v1_signature_forbidden"],
    "v4 不可用": ["v4_unavailable_fallback_v1"],
    "v4 关闭": ["v4_unavailable_fallback_v1"],
    "v4 不支持": ["v4_unavailable_fallback_v1"],
    "v4 无法": ["v4_unavailable_fallback_v1"],
    "forbidden": ["v1_signature_forbidden", "permission_changed"],
    "tamper": ["parameter_tampered"],
    "modify": ["parameter_tampered"],
    "edit": ["parameter_tampered"],
    "signaturedoesnotmatch": ["parameter_tampered", "credential_invalid",
                              "method_mismatch"],
    "signed url": ["parameter_tampered"],
    "stops working": ["expired"],
    "dies": ["expired"],
    "改动": ["parameter_tampered"],
    "改变": ["parameter_tampered"],
    "rotat": ["credential_invalid"],
    "disabled": ["credential_invalid", "permission_changed"],
    "sts": ["credential_invalid"],
    "token": ["credential_invalid"],
    "permission": ["permission_changed"],
    "policy": ["permission_changed"],
    "acl": ["permission_changed"],
    "method": ["method_mismatch"],
    "put": ["method_mismatch"],
    "upload": ["method_mismatch", "expired"],
    "malformed": ["malformed_url"],
    "x-oss-credential": ["malformed_url"],
    "x-oss-expires": ["malformed_url"],
    "region": ["malformed_url"],
    "authorization": ["malformed_url"],
    "not both": ["malformed_url"],
    "cache": ["expired", "malformed_url"],
    "缓存": ["expired"],
    # Chinese scenario-word routing (ticket-verified phrasings).
    "私有": ["long_term_private_access"],
    "签名": ["parameter_tampered", "credential_invalid"],
    "分享": ["expired", "long_term_private_access"],
    "链接": ["expired"],
    "长期": ["long_term_private_access", "expired"],
    "长期共享": ["long_term_private_access"],
    "失效": ["credential_invalid", "expired"],
    "永久": ["long_term_private_access"],
    # V4-unavailable fallback triggers (special region / old tooling).
    "ossbrowser": ["v4_unavailable_fallback_v1"],
    "特殊区域": ["v4_unavailable_fallback_v1"],
    "回退": ["v4_unavailable_fallback_v1"],
    # Custom-domain (CNAME) presigned URL routing (ticket 0001FRR89N).
    "自定义域名": ["custom_domain_presigned"],
    "cname": ["custom_domain_presigned"],
    "custom domain": ["custom_domain_presigned"],
    "域名": ["custom_domain_presigned"],
    # Chinese synonym layer (ticket-verified phrasings) so Chinese symptom
    # text routes directly instead of degrading to generic candidates.
    "签名不匹配": ["parameter_tampered"],
    "签名错误": ["parameter_tampered", "credential_invalid"],
    "被篡改": ["parameter_tampered"],
    "篡改": ["parameter_tampered"],
    "代理": ["parameter_tampered"],
    "自己拼": ["parameter_tampered"],
    "手动签名": ["parameter_tampered"],
    "signedheaders": ["parameter_tampered"],
    "pathstyle": ["sdk_config_misuse"],
    "sdk 配置": ["sdk_config_misuse"],
    "签名连接": ["permission_changed", "parameter_tampered"],
    "权限": ["permission_changed"],
    "策略": ["permission_changed"],
    "时钟": ["clock_skew"],
    "时钟偏差": ["clock_skew"],
    "时间不对": ["clock_skew"],
    "请求方法": ["method_mismatch"],
    "上传失败": ["method_mismatch", "expired"],
    "凭证": ["credential_invalid"],
    "密钥轮换": ["credential_invalid"],
    "权限变更": ["permission_changed"],
    "地域不匹配": ["malformed_url"],
    "region不对": ["malformed_url"],
    "参数格式": ["malformed_url"],
}

# Intent/endpoint precedence keys (eval fix PR-2 routing-order half): these
# wording families carry the case THEME and are iterated BEFORE all other
# keywords, so a long-term-access request ('改成永久的...一小时就失效') or a
# custom-domain case keeps its thematic first mode instead of being
# outranked by a generic symptom word that happens to sort earlier.
INTENT_PRECEDENCE_KEYS = (
    "永久", "长期共享", "长期", "私有",
    "自定义域名", "域名", "cname", "custom domain",
)

# Out-of-domain transfer guards (eval fix PR-4, ticket-verified): wording
# that marks the case for a sibling skill produces NO candidates here, so
# the entry script FAILs and SKILL.md's Do-NOT-use table routes the customer
# onward. Each guard is a tuple of word groups; EVERY group must have at
# least one word present. Guards only apply without URL/link/signature
# context (a signed-URL problem mentioned alongside stays in scope).
DOMAIN_TRANSFER_GUARDS = (
    # CDN back-to-origin configuration -> cdn-origin-config-diagnosis.
    (("回源",),),
    # traffic abuse / hotlink theft -> security-incident-forensics.
    (("黑产", "盗刷", "盗链", "流量暴涨"),),
    # 'make the bucket public' requests -> permission domain sibling.
    (("开启", "开通"), ("公开", "公共读")),
)

# V4 upgrade compatibility checklist (from the official V1-to-V4 upgrade
# guide; SDK-specific steps are documented per language there).
V4_UPGRADE_CHECKLIST = [
    "Confirm current signature version: V1 URL = OSSAccessKeyId+Expires+Signature; V4 URL = x-oss-credential+x-oss-date+x-oss-expires+x-oss-signature; header V4 Authorization starts with OSS4-HMAC-SHA256",
    "Upgrade SDK/ossutil to a version that supports signature version 4 and enable V4 in the client configuration (SDK-specific steps in the official upgrade guide)",
    "Set the region explicitly: V4 credential scope embeds the region (AccessKeyId/date/region/oss/aliyun_v4_request) and it must match the bucket region",
    "For STS credentials, keep passing the security token (x-oss-security-token in URLs; SecurityToken in SDKs)",
    "V1 retirement policy: since 2025-03-01 V1 is gradually closed to new customer accounts (new uids); since 2025-09-01 V1 stops updates and maintenance and is not opened to newly created buckets",
    "After upgrading, regenerate all circulating presigned URLs as V4 and discard old V1 links",
    "Do not keep a V1 fallback that silently downgrades signing; failures should surface so misconfiguration is visible",
]

# How to recover a broken share link (owner-side actions).
LINK_RECOVERY_GUIDANCE = [
    "Only the bucket/object owner (or an identity with the corresponding permission) can regenerate a presigned URL; recipients cannot repair it",
    "Regenerate the URL with the correct HTTP method, a sufficient TTL (max 604800 seconds = 7 days for a long-term AccessKey; max 43200 seconds = 12 hours for an STS temporary credential), and a current, enabled credential",
    "Re-verify the signer's RAM permission and Bucket Policy before re-sharing",
    "Deliver the new link without intermediate rewriting; verify by opening it once immediately after generation",
]

MODE_KEYS = sorted(FAILURE_MODES.keys())
