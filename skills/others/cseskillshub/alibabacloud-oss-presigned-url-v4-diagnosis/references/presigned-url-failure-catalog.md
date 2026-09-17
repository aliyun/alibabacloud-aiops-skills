# Presigned-URL Failure Catalog

Knowledge base embedded by `scripts/_url_catalog.py` (single source of truth;
this document mirrors it for human reading). All official facts verified
against Alibaba Cloud OSS documentation in 2026-08.

## 1. Signature URL Forms

| Query parameters present | Signature version | Expiry semantics |
| --- | --- | --- |
| `OSSAccessKeyId` + `Expires` + `Signature` | V1 presigned URL | `Expires` is an absolute UNIX epoch (seconds) |
| `x-oss-credential` + `x-oss-date` + `x-oss-expires` + `x-oss-signature` | V4 presigned URL | expiry = `x-oss-date` + `x-oss-expires` (seconds), max 604800 s (7 days) for a long-term AccessKey; STS temporary credentials cap at 43200 s (12 hours) |
| Legacy marker `x-oss-signature-version=OSS2` | V2 (legacy, rare) | `Expires` is an absolute UNIX epoch |

- V4 `x-oss-credential` format: `AccessKeyId/date/region/oss/aliyun_v4_request` (slash-separated, URL-encoded in the query).
- V4 `x-oss-date` format: basic ISO-8601 `YYYYMMDDTHHmmssZ` (UTC).
- Optional V4 URL parameters: `x-oss-signature-version=OSS4-HMAC-SHA256`, `x-oss-additional-headers`, `x-oss-security-token` (STS).
- Sources: V4 in URL — https://help.aliyun.com/zh/oss/developer-reference/add-signatures-to-urls ; V1 in URL — https://help.aliyun.com/zh/oss/add-signatures-to-urls-14

## 2. Hard Limits

| Limit | Value | Source |
| --- | --- | --- |
| Maximum presigned-URL validity | 604800 seconds (7 days) for a long-term AccessKey; STS temporary credentials cap at 43200 seconds (12 hours); V4 counted from `x-oss-date` | official V4-in-URL doc above |
| Maximum clock skew | +/- 15 minutes (900 s); exceeded → `RequestTimeTooSkewed` (EC 0002-00000504) | support-ticket case law + official RequestTimeTooSkewed semantics |
| Empty/missing `x-oss-expires` in V4 | official error 0002-00000216 | https://help.aliyun.com/zh/oss/user-guide/0002-00000216 |
| URL-signature parameter EC family | 0002-00000067 Expires missing / 0002-00000068 Expires empty / 0002-00000070 Expires value not a valid second-level UNIX timestamp / 0002-00000071 OSSAccessKeyId missing / 0002-00000072 OSSAccessKeyId empty / 0002-00000073 OSSAccessKeyId invalid characters / 0002-00000074 Signature missing / 0002-00000075 Signature empty / 0002-00000066 x-oss-signature-version invalid (V1 needs none, V2 needs OSS2) | https://help.aliyun.com/zh/oss/user-guide/0002-00000067 ...0002-00000075, 0002-00000066 |
| STS token placement in URL-signed requests | the security token must be carried in the URL `security-token` parameter, not only in an `x-oss-security-token` header (EC 0002-00000005) | https://help.aliyun.com/zh/oss/user-guide/0002-00000005 |

## 3. Failure Modes (root-cause directions)

| Mode | Typical error signal | Key directions |
| --- | --- | --- |
| `expired` | 403 AccessDenied; expiry timestamp in the past (official EC 0002-00000069; console default TTL 3600 s) | TTL exceeded; short TTL shared too long; client clock far ahead |
| `clock_skew` | 403 RequestTimeTooSkewed | device clock drift; signed request queued in retries before send |
| `v1_signature_forbidden` | V1 rejected per retirement policy | new uid after cut-over; newly created bucket; client still signs V1 |
| `v4_unavailable_fallback_v1` | V4-signed requests fail in a special/legacy region or with an old tool (e.g. old ossbrowser) while V1 works | symmetric exception of `v1_signature_forbidden`: fall back to V1 signing for the affected region/tool, upgrade the tool when possible (ticket-verified workaround) |
| `long_term_private_access` | durable-access design question for private objects, not an error code | on-demand re-signing with short TTL; CDN private back-to-origin + URL auth or a signing gateway; RAM/STS for programmatic access; never make the object public |
| `parameter_tampered` | 403 SignatureDoesNotMatch | URL edited after signing; proxy/CDN rewrote path or params; double-encoding; official EC 0002-00000040 causes: proxy adds headers after signing, CDN converts HEAD→GET or injects x-oss-* headers, CNAME endpoint without the CNAME switch, unencoded plus sign (+→%2B) in the signature, mini-program extra Content-Type; hand-built V4 CanonicalRequest mistakes (SignedHeaders omitted / not lowercase-sorted / missing URI-encoding) — check the four V4 elements x-oss-content-sha256 / x-oss-date / SignedHeaders / region; compare the StringToSign in the error body, but NEVER infer the client-side construction from the server-side canonical string (anti-pattern: compare the client's intermediate signing variables layer by layer instead) |
| `credential_invalid` | 403 SignatureDoesNotMatch / InvalidAccessKeyId / SecurityTokenExpired | AK rotated/disabled after sharing; STS token expired; wrong SK at generation; STS token must be carried in the URL security-token parameter, header-only placement is rejected (EC 0002-00000005) |
| `permission_changed` | 403 AccessDenied despite valid signature | signer's RAM permission revoked; Bucket Policy deny (presigned URLs do NOT bypass policy); object deleted/ACL changed; AK bound to a network policy / IP allow-list that forbids public-internet access — the signature is valid but the request is rejected at the network layer (ticket 0001FSADTN: removing the network-policy restriction restored access) |
| `method_mismatch` | 403 SignatureDoesNotMatch on upload with GET-signed URL | URL bound to the HTTP method used at signing |
| `malformed_url` | 400 / 0002-00000216 / AuthorizationHeaderMalformed | missing/empty params (EC 0002-00000067/068/071/072/074/075, invalid values 0002-00000070/073, bad signature-version 0002-00000066); `x-oss-expires` > 604800 (long-term AK) or > 43200 (STS); bad credential scope; wrong region (→ AuthorizationHeaderMalformed) |
| `custom_domain_presigned` | custom-domain (CNAME) endpoint presigned-URL questions, incl. SignatureDoesNotMatch when the CNAME switch is off | sign with the custom domain as the endpoint (ticket 0001FRR89N); http works immediately, https additionally requires an SSL certificate hosted for the domain on OSS; enable the SDK custom-domain option (cname=true / is_cname=True) when signing against a CNAME endpoint; TTL max 604800 s (long-term AK) as usual, STS-signed CNAME URLs still cap at 43200 s |
| `sdk_config_misuse` | 403 SignatureDoesNotMatch with SDK-generated URLs | `pathStyleAccess` enabled against a virtual-hosted-style endpoint (path-style bucket addressing changes the signed resource); CNAME switch off (`cname=false`) while signing a custom domain; an SDK older than V4 support silently falling back to V1; check the SDK's resolved endpoint and bucket addressing against the signing input (step 4.2 of the five-step signature SOP) |

## 4. Error-Code Routing

| Error code | Candidate modes (in priority order) |
| --- | --- |
| `SignatureDoesNotMatch` | parameter_tampered → credential_invalid → method_mismatch → v1_signature_forbidden |
| `InvalidAccessKeyId` | credential_invalid |
| `SecurityTokenExpired` | credential_invalid |
| `RequestTimeTooSkewed` | clock_skew |
| `AccessDenied` | expired → permission_changed → credential_invalid → v1_signature_forbidden |
| `AuthorizationHeaderMalformed` | malformed_url |
| `InvalidArgument` | malformed_url |
| `AccessForbidden` | permission_changed |

HTTP-status routing: 403 → signature/permission family above; 400 → malformed_url, clock_skew; 404 → permission_changed (object/bucket gone).

Symptom routing notes (eval fix PR-2/PR-3/PR-4):
- Intent precedence: long-term / private / custom-domain wording carries the
case theme and is matched first.
- Remaining keywords match longest-first, so precise compounds (e.g. a
signature-mismatch phrase) outrank generic ones (e.g. a bare signature
word); the generic signature keyword never routes to `expired` on its
own.
- The `expired` route applies subject discrimination: a symptom routes to
signed-URL expiry only when it carries URL/link/signature context;
resource-package/plan subjects (e.g. a Chinese complaint about an expired
resource package / storage plan) are excluded and belong to billing
diagnosis.
- Domain-transfer guards: CDN back-to-origin, traffic-abuse (black-market
upload / scraping / traffic-surge wording) and make-it-public wording
WITHOUT URL context yields NO candidates here — those tickets belong to
cdn-origin-config / security-incident-forensics; with URL/link/signature
context the case stays in scope.
- Chinese scenario keyword families route directly (the keyword table
itself lives in `scripts/_url_catalog.py`): share / link / expired
wording → expiry family; signature-mismatch / tampered / proxy /
hand-signed / signedHeaders wording → `parameter_tampered`; ossbrowser /
special region / v4-unavailable wording → `v4_unavailable_fallback_v1`;
custom domain / cname / domain wording → `custom_domain_presigned`;
pathStyleAccess / SDK-config wording → `sdk_config_misuse`; permission /
policy / network-policy wording → `permission_changed`;
signed-link-changed wording → `permission_changed` + `parameter_tampered`.

## 5. Deterministic Verdicts

The entry script concludes without further questions when the URL parse is definitive:
- expiry timestamp is in the past → `expired` (STATUS: OK);
- expiry parameters are malformed (empty `x-oss-expires`, non-numeric values, `x-oss-expires` > 604800 for a long-term AccessKey or > 43200 for an STS temporary credential, bad `x-oss-date` format) → `malformed_url` (STATUS: OK);
- V4 credential scope is malformed (not 5 slash-separated segments `AccessKeyId/date/region/oss/aliyun_v4_request`) → `malformed_url` (STATUS: OK; report `url_analysis.credential_scope.reason` verbatim) — eval fix PR-1, SKILL.md Example 3 contract.

All other combinations yield ordered candidate lists (STATUS: DEGRADED) and require discriminating evidence before a conclusion.
