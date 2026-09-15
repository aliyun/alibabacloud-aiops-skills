# OSS Transfer Error Code Catalog

Error-code semantics in this catalog follow the official Alibaba Cloud OSS
documentation (verified 2026-08). Root-cause directions and troubleshooting
steps are distilled from 472 real support tickets in the transfer scenario.

## Official documentation sources

| Source | URL |
| --- | --- |
| HTTP 403 error codes | https://help.aliyun.com/zh/oss/user-guide/http-403-error-code |
| HTTP 400 error codes | https://help.aliyun.com/zh/oss/user-guide/http-400-error-code |
| HTTP 404 error codes | https://help.aliyun.com/zh/oss/user-guide/http-status-code-404 |
| HTTP 503 error codes | https://help.aliyun.com/zh/oss/user-guide/http-status-code-503 |
| Error response parsing | https://help.aliyun.com/zh/oss/user-guide/overview-14 |
| Signature FAQ | https://help.aliyun.com/en/oss/developer-reference/faq-24 |
| Common errors | https://help.aliyun.com/en/oss/user-guide/common-errors |
| PutBucket error codes (BucketAlreadyExists) | https://help.aliyun.com/zh/oss/developer-reference/putbucket |
| Usage limits (5 GB single-request / 48.8 TB multipart, global bucket names) | https://help.aliyun.com/zh/oss/product-overview/limits |
| Authorization syntax and elements (action levels, condition keys) | https://help.aliyun.com/zh/oss/user-guide/authorization-syntax-and-elements |
| EC 0003-00000001 (AccessDenied: credential or permission) | https://help.aliyun.com/zh/oss/user-guide/0003-00000001 |
| EC 0003-00000905 (AccessDenied: RAM permission missing) | https://help.aliyun.com/zh/oss/user-guide/0003-00000905 |
| EC 0003-00001403 (AccessDenied: endpoint region mismatch) | https://help.aliyun.com/zh/oss/user-guide/0003-00001403 |
| EC 0003-00000801 (UserDisable: account disabled) | https://help.aliyun.com/zh/oss/user-guide/0003-00000801 |
| EC 0003-00000908 (bucket banned by security policy) | https://help.aliyun.com/zh/oss/user-guide/0003-00000908 |
| EC 0002-00000904 (InvalidAccessKeyId: AK IP-scope restriction) | https://help.aliyun.com/zh/oss/user-guide/0002-00000904 |
| EC 0017-00000244 (NoSuchUpload: bad/expired UploadId) | https://help.aliyun.com/zh/oss/user-guide/0017-00000244 |
| EC 0007-00000203 (CallbackFailed: callback URL unreachable/non-200) | https://help.aliyun.com/zh/oss/user-guide/0007-00000203 |
| EC 0007-00000202 (callback server processing > 5 s timeout) | https://help.aliyun.com/zh/oss/user-guide/0007-00000202 |
| EC 0015-00000001 (InvalidBucketName: bucket name violates naming rules) | https://help.aliyun.com/zh/oss/user-guide/0015-00000001 |
| EC 0015-00000101 (NoSuchBucket: bucket does not exist) | https://help.aliyun.com/zh/oss/user-guide/0015-00000101 |

The machine-readable copy of this catalog is embedded as a Python constant in
`scripts/_error_catalog.py` (no standalone data files). Always trust the
script output over manual recall.

## Category legend

| Category | Label | Typical side |
| --- | --- | --- |
| permission | permission / RAM / Bucket Policy / ACL | client |
| credential | credential and signature | client |
| network | client network environment | client / both |
| usage | tool / SDK / API usage | client |
| limit | file or object limits | client |
| server | server side / throttling | server |

## HTTP 403 family

### AccessDenied (403, permission)
Root-cause directions (official EC cross-references: 0003-00000001 credential/permission aggregate, 0003-00000905 RAM permission missing, 0003-00001403 endpoint region mismatch):
- RAM user/role lacks the oss action on this bucket or object (top ticket cluster: RAM/BucketPolicy/ACL); note that PutObject with x-oss-tagging additionally requires oss:PutObjectTagging, and ossbrowser login additionally requires oss:GetBucketInfo (official EC 0003-00000905 / 0003-00000001)
- Bucket Policy or object ACL explicitly denies the request
- AccessKey-bound network policy (IP whitelist) does not cover the real source IP (public vs VPC, CEN forwarding IP; IPv4 and IPv6 are separate addresses, real ticket case: IPv6 source not listed)
- RAM/STS policy attaches a directory-prefix condition (oss:Prefix) or a directory-level resource to a Bucket-level action such as ListMultipartUploads - Bucket-level actions must be authorized on the bucket-level resource (authorization syntax and elements doc)
- Policy uses an unsupported condition key (e.g. acs:Referer is not in the official condition-key list); Referer restriction is only available as Bucket-level hotlink protection (real ticket case: STS SessionPolicy per-object Referer control denied)
- Endpoint region mismatch: bucket accessed through the endpoint of another region (official EC 0003-00001403; the error body carries the correct `<Endpoint>` to switch to)
- Hotlink protection (Referer whitelist) rejects the request Referer
- Archive/ColdArchive object not restored, or archive direct-read not enabled
- Bucket belongs to another account (cross-account operation without authorization)

### AccessForbidden (403, permission)
- Operation targets a bucket not owned by the current account
- Request violates an access-control rule attached to the bucket
- CORS rejection on browser/PostObject access: if the error body carries EC 0003-00000602, the bucket's CORS rule is missing the request Origin/method - continue with alibabacloud-oss-browser-upload-cors-diagnosis instead of this generic permission track

### SignatureDoesNotMatch (403, credential)
- Wrong or rotated AccessKey Secret paired with the AccessKey ID
- Signature string built incorrectly (header ordering, Content-Type/MD5 mismatch, wrong canonical resource)
- Non-ASCII characters in x-oss-meta user metadata break the signature computation (real ticket case)
- Outdated SDK with a known signature bug; or V1 signature disabled for the bucket region while client still signs V1
- Clock drift between client and server exceeding the allowed skew
- Object name/path contains special characters (e.g. double slashes //) and the tool's path-encoding behavior diverges from the server-side signature computation (real ticket case: path encoding differs between ossutil versions); compare the StringToSign in the error body with the client's and retry another tool version
- Knowledge boundary: this knowledge is held by three skills - this entry is the general credential/signature track; signature failures inside a multipart flow continue with alibabacloud-oss-multipart-upload-diagnosis, and presigned-URL signature errors continue with alibabacloud-oss-presigned-url-v4-diagnosis

### InvalidAccessKeyId (403, credential)
- AccessKey ID does not exist (deleted, or copied with extra/missing characters)
- AccessKey is disabled in the RAM console
- Credential belongs to a different account than the bucket owner
- AK-bound network restriction (IP whitelist) does not cover the real source IP, e.g. CEN / forwarding-router source IPs (real ticket case observed this surfacing as InvalidAccessKeyId; official EC 0002-00000904 covers the same restriction surfacing as a disabled AccessKeyId)

### SecurityTokenExpired (403, credential)
- STS temporary credential expired during a long-running upload/download (ticket case: hundreds-of-MB direct upload outliving the token)
- Client cached the STS token and never refreshed it before expiry

### RequestTimeTooSkewed (403, credential)
- Client system clock differs from server time by more than 15 minutes

### InvalidObjectState (403, limit)
- Operation not allowed for the object's storage class (ticket case: archive object read before restore)

### UserDisable (403, permission)
- The calling account is disabled; official EC 0003-00000801 lists three causes: overdue payment, account disabled for security reasons, or OSS service not activated (observed in real tickets as the EC numeric code)
- Overdue payment: settle the outstanding balance in the Billing console; security ban: follow the official security-violation handling guide; OSS not activated: activate OSS in the console

### BucketDisable (403, permission)
- The bucket is banned by a security policy due to detected malicious behavior (official EC 0003-00000908); normal access is blocked until resolved
- Verify whether the bucket hosts violating content or malicious behavior, then open a support ticket to appeal/unblock (observed in real tickets as the EC numeric code)

## HTTP 400 family

### RequestTimeout (400, network)
- Client network unstable or bandwidth-limited; the connection or transfer did not finish inside the timeout (top ticket cluster after permission)
- Multipart part size too large for the available bandwidth; no timeout/retry tuning on the client
- Unnecessary use of the global-accelerate endpoint for a domestic same-region path, adding latency (real ticket case)
- Cross-border or long-distance network path with high loss

### ConnectionTimeout (400, network)
- TCP connection to the OSS endpoint could not be established in time (client network, firewall, proxy)
- DNS resolution failure or slow resolution of the OSS domain
- Client-side connect timeout configured too short for an unstable link

### EntityTooLarge (400, limit)
- PostObject form policy (Post Policy content-length-range) caps the allowed body smaller than the file (ticket case: 20 KB image rejected)
- Single-request upload methods (PutObject simple upload, PostObject form upload, AppendObject) cap at 5 GB per request; for larger files use multipart/resumable upload, which supports up to 48.8 TB per file (official usage-limits doc)

### InvalidArgument (400, usage)
- A request parameter is malformed or out of range (e.g. invalid partNumber, expires, or header value)
- Tool/SDK invoked with incompatible options for the operation (tool-usage ticket cluster)

### InvalidBucketName (400, usage)
Official EC 0015-00000001 - the bucket name violates the OSS naming rules:
only lowercase letters, digits and hyphens (-); must start and end with a
lowercase letter or digit; length 3-63 characters.
- Bucket name contains characters that are NEVER valid in OSS - a dot (.),
  underscore (_), uppercase letter or other symbol - so the bucket cannot
  exist under any account or region (real-ticket pattern: a dot-style name
  or a full domain carried over from another S3-compatible store is used as
  the bucket name)
- SDK misuse: the Endpoint parameter was set to the bucket-prefixed domain
  (e.g. `https://your-bucket.oss-cn-hangzhou.aliyuncs.com`) instead of the
  regional endpoint, so the SDK parses the endpoint's bucket label as the
  bucket name (official doc example)
- Diagnosis SOP: extract the bucket name actually used (from the Host
  header - the first label of `bucket.oss-region.aliyuncs.com` - or the SDK
  config), validate it against the rules, and rename it if it contains a
  dot/underscore/uppercase; OSS bucket names cannot contain dots, so the fix
  is renaming, not looking up. Distinguish from NoSuchBucket (EC
  0015-00000101): an INVALID name can never exist; a VALID name may simply
  not have been created. A security-scanner probe with a malformed non-OSS
  Host can also trigger this code and needs no action.

### InvalidPart (400, usage)
- One or more parts listed in CompleteMultipartUpload do not exist, or their
  ETags do not match the ETags recorded at upload time (a part re-uploaded
  with different content, or the UploadId of two upload sessions mixed up)
- The complete list was assembled from a stale local resumable-upload
  checkpoint while the actual parts on the server had changed (real-ticket
  pattern); rebuild the list from ListParts output and retry the complete
  call. Deeper multipart-flow diagnosis: alibabacloud-oss-multipart-upload-diagnosis

### PartOutOfBounds (400, usage)
- The partNumber parameter is outside the allowed range 1-10000 (each
  multipart upload accepts at most 10000 parts); raise the part size if the
  file needs more than 10000 parts. Deeper multipart-flow diagnosis:
  alibabacloud-oss-multipart-upload-diagnosis

### InvalidPartOrder (400, usage)
- The part list in CompleteMultipartUpload is not sorted by partNumber
  ascending (the complete request requires ascending order); build the list
  from ListParts output, which is already ordered. Deeper multipart-flow
  diagnosis: alibabacloud-oss-multipart-upload-diagnosis

## HTTP 404 family

### NoSuchKey (404, usage)
- Object key does not exist: typo, wrong case, or wrong path prefix
- Multipart upload never called the complete step, so the object was never assembled (ticket case: only fragments visible)
- Static-site access to a directory without a configured default index object

### NoSuchBucket (404, usage)
Official EC 0015-00000101 - the bucket does not exist. Distinguish before
troubleshooting:
- Bucket name is legal but the bucket does not exist: misspelled, deleted,
  or created by/for another account
- Bucket name itself is ILLEGAL (contains a dot, underscore, uppercase
  letter, or is not 3-63 chars of lowercase letters/digits/hyphens): such a
  bucket can NEVER exist - if the error body shows EC 0015-00000001 /
  InvalidBucketName instead, the fix is renaming the bucket, not looking it
  up (see the InvalidBucketName entry)
- "Not visible" vs "not existing": a bucket that DOES exist can still
  surface as not-found when the calling credential lacks permission to see
  it (e.g. an unauthorized RAM user, or a cross-account access without
  authorization) - verify with the bucket owner's credential (re-run
  GetBucketInfo/ListBuckets) before concluding the bucket is gone
- Request sent to the wrong region endpoint for an existing bucket
- STS flow misuse: the SDK endpoint used to obtain temporary credentials
  was set to the OSS domain instead of the STS domain (e.g.
  `sts.cn-hangzhou.aliyuncs.com`), so bucket resolution failed (official doc
  example)

### NoSuchUpload (404, usage)
- The multipart UploadId does not exist, was mistyped, or has expired: the upload was already aborted or already completed (official EC 0017-00000244; also returned when AbortMultipartUpload/CompleteMultipartUpload targets a finished UploadId)
- Fix: re-run InitiateMultipartUpload to obtain a fresh UploadId; a resumable checkpoint from a previous session must be discarded when the UploadId no longer resolves (real ticket case)

## HTTP 409 family

### BucketAlreadyExists (409, usage)
- Bucket names are globally unique across all accounts and regions; the name is already created by another account (real ticket case: a typo in the bucket name hit another account's bucket, so uploads returned 403 and the create failed)
- Re-creating a same-name bucket shortly after deletion: OSS requires waiting several hours (usually 4-8 hours) before the name can be created again

## Throttling and server family

### SlowDown (503, server)
- Request rate (QPS) exceeded the throttling limit for the bucket/prefix
- Hot prefix: too many requests concentrated on keys sharing one prefix

### TooManyRequests (removed 2026-08-26)
- Removed: the official OSS 429 doc (https://help.aliyun.com/zh/oss/user-guide/429-error) lists QpsLimitExceeded only and does NOT document a TooManyRequests error code, so this entry had no official source. HTTP 429 input now degrades to the status-only fallback anchored on SlowDown (the catalog's throttling code).

### InternalError (500, server)
- Transient server-side failure inside OSS

### ServiceUnavailable (503, server)
- Service temporarily unavailable, or public-network traffic degraded (e.g. bucket moved into the DDoS sandbox: public access degraded while internal access stays normal)

## HTTP 203 family

### CallbackFailed (203, usage)
- The upload succeeded but the callback step failed: OSS POSTed to callbackUrl and did not receive `200 OK` (official EC 0007-00000203) - callback server not started, callbackUrl missing from the callback parameters, or network between OSS and the callback server blocked (e.g. firewall)
- Callback server processing exceeded the 5-second limit (official EC 0007-00000202); make the callback handler asynchronous and return within 5 seconds
- Verify the callback endpoint independently (e.g. curl/Postman POST returns HTTP/1.1 200 OK) and confirm the URL is publicly reachable (real ticket case)

## HTTP status to code mapping (status-only input)

| Status | Candidate codes |
| --- | --- |
| 203 | CallbackFailed |
| 400 | RequestTimeout, ConnectionTimeout, EntityTooLarge, InvalidArgument, InvalidBucketName, InvalidPart, PartOutOfBounds, InvalidPartOrder |
| 403 | AccessDenied, SignatureDoesNotMatch, InvalidAccessKeyId, SecurityTokenExpired, AccessForbidden, InvalidObjectState, RequestTimeTooSkewed, UserDisable, BucketDisable |
| 404 | NoSuchKey, NoSuchBucket, NoSuchUpload |
| 409 | BucketAlreadyExists |
| 429 | SlowDown (status-only fallback; official 429 code is QpsLimitExceeded, no TooManyRequests in OSS docs) |
| 499 | RequestTimeout, ConnectionTimeout (not an official OSS status; nginx-style proxies/clients emit it when the client closes the connection early, observed in real tickets) |
| 500 | InternalError |
| 503 | SlowDown, ServiceUnavailable |

## Client-term synonyms and routing layers (input forms the script accepts)

The matching ladder accepts more than symbolic codes (all embedded in
`scripts/_error_catalog.py`):

- **Client-term synonyms** (SDK stack-trace names -> catalog code):  `ETIMEDOUT`, `SocketTimeout`, `SocketException`, `RequestError`,
  `net::ERR_EMPTY_RESPONSE`, `connection timed out`, plus the non-English
  equivalents of connection-timeout / request-error / request-timeout;
  connection-reset family `ConnectionReset` / `ConnectionResetError` /
  `ConnectionRefused` / `BrokenPipeError` / `ClientError`; DNS family
  `getaddrinfo failed` / `NameResolutionError` / the non-English phrase for
  domain-resolution failure; read-side `ReadTimeout`.
- **EC numeric aliases**: `0015-00000001` -> InvalidBucketName,
  `0015-00000101` -> NoSuchBucket (the official error body carries both the
  symbolic Code and the numeric EC field).
- **Family words**: a bare family word for "timeout" (non-English)
  cannot decide request- vs connection-timeout, so it yields BOTH candidates
  as a degraded list.
- **Symptom keywords** (`--question` wording, ticket-verified non-English
  phrasings, keys embedded in the code layer): large-file upload breaks
  (large file / big video + a failure verb) -> EntityTooLarge + network
  candidates; mid-transfer breaks (dies halfway / always breaks / never
  finishes) -> network family; bucket-domain unreachable while the plain
  endpoint works (bucket domain / domain unreachable) -> DNS family; generic
  upload-failed / download-failed -> the top ticket-cluster candidates.
  The layer degrades to DEGRADED candidate lists and asks for the error
  body - it never concludes on symptom wording alone.
- **Out-of-domain guards**: customer wording that marks a NON-OSS product
  (SSH / MySQL / Redis / MongoDB / PostgreSQL / RDS / CDN / k8s / docker,
  or an ECS host-level curl probe) with no OSS context anchor produces NO
  OSS diagnosis (FAIL with a boundary note); an OSS anchor (`oss`, `bucket`,
  `ossutil`, `aliyuncs`, ...) anywhere keeps the case in scope.

## Non-transfer EC codes: one-hop referrals

When the input carries an EC numeric code owned by a sibling skill, the
script attaches an `ec_code_referral` block instead of silently absorbing
it:

| EC code | Owning skill |
| --- | --- |
| 0003-00000005 | alibabacloud-oss-direct-access-link-diagnosis (private-object direct-access link / platform ban) |
| 0003-00000201 | alibabacloud-oss-cross-account-auth-diagnosis (explicit RAM Deny) |
| 0003-00000602 | alibabacloud-oss-browser-upload-cors-diagnosis (CORS rule missing the request Origin/method) |
| 0024-00000008 | alibabacloud-oss-transfer-acceleration-diagnosis (transfer acceleration not enabled) |

> Note on 0024-00000008: first-hand measured behavior, NOT present in the
> official 0024 EC family (officially uncatalogued; `search "0024-00000008"`
> returns no doc). The owning skill alibabacloud-oss-transfer-acceleration-diagnosis
> carries the RequestId-level probe evidence and the TAC-2 boundary statement.
> This skill only routes the code onward in one hop and does not claim it as an
> official error code.

## RequestId-only input

A RequestId alone cannot locate the root cause from the client side; the
run stays `STATUS: FAIL` asking for the full error response body, plus a
`request_id_guidance` block listing per-client-type paths (Java SDK logging,
oss2 exception details, ossutil log level, browser devtools Network panel,
capture layer for other tools) to recover that body. Server-side log
lookup by RequestId is a support-only capability and stays out of this
zero-cloud-API skill - keep the RequestId for ticket escalation.
