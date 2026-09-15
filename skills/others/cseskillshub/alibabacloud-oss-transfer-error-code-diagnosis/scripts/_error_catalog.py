#!/usr/bin/env python3
# SECURITY: read-only knowledge module; only loaded by the entry script after
# SKILL.md confirmation; operates purely on user-supplied error descriptions.
"""Official OSS transfer error-code catalog (embedded constant, no data files).

Distilled from the official Alibaba Cloud OSS documentation (HTTP-status
error-code references, verified 2026-08) and root-cause clusters of 472
real support tickets (permissions 196 / client network 87 / credential and
signature 57 / tool and API usage 49 / custom domain 25 / CORS 13 /
hotlink 9). Root-cause directions and troubleshooting steps reflect the
ticket clustering; error-code semantics follow the official docs:

  - HTTP 403: https://help.aliyun.com/zh/oss/user-guide/http-403-error-code
  - HTTP 400: https://help.aliyun.com/zh/oss/user-guide/http-400-error-code
  - HTTP 404: https://help.aliyun.com/zh/oss/user-guide/http-status-code-404
  - HTTP 503: https://help.aliyun.com/zh/oss/user-guide/http-status-code-503
  - Error response parsing: https://help.aliyun.com/zh/oss/user-guide/overview-14
  - Signature FAQ: https://help.aliyun.com/en/oss/developer-reference/faq-24
  - Common errors: https://help.aliyun.com/en/oss/user-guide/common-errors
  - PutBucket error codes (BucketAlreadyExists): https://help.aliyun.com/zh/oss/developer-reference/putbucket
  - Usage limits (5 GB single-request / 48.8 TB multipart, global bucket names): https://help.aliyun.com/zh/oss/product-overview/limits
  - Authorization syntax and elements (action levels, condition keys): https://help.aliyun.com/zh/oss/user-guide/authorization-syntax-and-elements

Categories: permission / credential / network / usage / limit / server.
side: 'client' = fix on the requester side, 'server' = retry/backoff or
escalate, 'both' = needs evidence to decide.
"""

DOC_403 = "https://help.aliyun.com/zh/oss/user-guide/http-403-error-code"
DOC_400 = "https://help.aliyun.com/zh/oss/user-guide/http-400-error-code"
DOC_404 = "https://help.aliyun.com/zh/oss/user-guide/http-status-code-404"
DOC_503 = "https://help.aliyun.com/zh/oss/user-guide/http-status-code-503"
DOC_PARSE = "https://help.aliyun.com/zh/oss/user-guide/overview-14"
DOC_SIGN = "https://help.aliyun.com/en/oss/developer-reference/faq-24"
DOC_COMMON = "https://help.aliyun.com/en/oss/user-guide/common-errors"
DOC_PUTBUCKET = "https://help.aliyun.com/zh/oss/developer-reference/putbucket"
DOC_LIMITS = "https://help.aliyun.com/zh/oss/product-overview/limits"
DOC_AUTH = "https://help.aliyun.com/zh/oss/user-guide/authorization-syntax-and-elements"
DOC_EC_0003_0001 = "https://help.aliyun.com/zh/oss/user-guide/0003-00000001"
DOC_EC_0003_0905 = "https://help.aliyun.com/zh/oss/user-guide/0003-00000905"
DOC_EC_0003_1403 = "https://help.aliyun.com/zh/oss/user-guide/0003-00001403"
DOC_EC_0003_0801 = "https://help.aliyun.com/zh/oss/user-guide/0003-00000801"
DOC_EC_0003_0908 = "https://help.aliyun.com/zh/oss/user-guide/0003-00000908"
DOC_EC_0002_0904 = "https://help.aliyun.com/zh/oss/user-guide/0002-00000904"
DOC_EC_0017_0244 = "https://help.aliyun.com/zh/oss/user-guide/0017-00000244"
DOC_EC_0007_0203 = "https://help.aliyun.com/zh/oss/user-guide/0007-00000203"
DOC_EC_0007_0202 = "https://help.aliyun.com/zh/oss/user-guide/0007-00000202"
DOC_EC_0015_0001 = "https://help.aliyun.com/zh/oss/user-guide/0015-00000001"
DOC_EC_0015_0101 = "https://help.aliyun.com/zh/oss/user-guide/0015-00000101"

ERROR_CATALOG = {
    "AccessDenied": {
        "code": "AccessDenied",
        "http_status": 403,
        "category": "permission",
        "side": "client",
        "root_cause_directions": [
            "RAM user/role lacks the oss action on this bucket or object (top ticket cluster: RAM/BucketPolicy/ACL); PutObject with x-oss-tagging additionally requires oss:PutObjectTagging, and ossbrowser login additionally requires oss:GetBucketInfo (official EC 0003-00000905 / 0003-00000001)",
            "Bucket Policy or object ACL explicitly denies the request",
            "AccessKey-bound network policy (IP whitelist) does not cover the real source IP (public vs VPC, CEN forwarding IP; IPv4 and IPv6 are separate addresses, real ticket case: IPv6 source not listed)",
            "RAM/STS policy attaches a directory-prefix condition (oss:Prefix) or a directory-level resource to a Bucket-level action such as ListMultipartUploads - Bucket-level actions must be authorized on the bucket-level resource (see authorization syntax and elements doc)",
            "Policy uses an unsupported condition key (e.g. acs:Referer is not in the official condition-key list); Referer restriction is only available as Bucket-level hotlink protection (real ticket case: STS SessionPolicy per-object Referer control denied)",
            "Endpoint region mismatch: bucket accessed through the endpoint of another region (official EC 0003-00001403; the error body carries the correct <Endpoint> to switch to)",
            "Hotlink protection (Referer whitelist) rejects the request Referer",
            "Archive/ColdArchive object not restored, or archive direct-read not enabled",
            "Bucket belongs to another account (cross-account operation without authorization)",
        ],
        "troubleshooting_steps": [
            "Parse the EC code and RecommendDoc in the error response body to locate the exact denial reason (see error-response parsing doc)",
            "Confirm the RAM identity's policy grants the exact oss action on this bucket/object resource ARN",
            "Check Bucket Policy, bucket ACL and object ACL for explicit denies",
            "Check AccessKey network-policy IP whitelist against the real request source IP (public/VPC/CEN; check both IPv4 and IPv6)",
            "Authorize Bucket-level actions (e.g. ListMultipartUploads) on the bucket-level resource ARN only, without oss:Prefix directory conditions",
            "If the denial mentions SessionPolicy, verify the policy uses only officially supported condition keys; move Referer control to Bucket-level hotlink protection",
            "Verify the endpoint region matches the bucket region",
            "If Referer hotlink protection is enabled, verify the request Referer is whitelisted",
            "If the object is Archive/ColdArchive, restore it (or enable archive direct-read) before reading",
        ],
        "official_doc_ref": DOC_403,
    },
    "AccessForbidden": {
        "code": "AccessForbidden",
        "http_status": 403,
        "category": "permission",
        "side": "client",
        "root_cause_directions": [
            "Operation targets a bucket not owned by the current account (e.g. configuring CORS on another account's bucket)",
            "Request violates an access-control rule attached to the bucket",
            "Browser/PostObject CORS rejection: when the error body carries official EC 0003-00000602 the bucket's CORS rule is missing the request Origin/method - this is the browser-upload CORS domain, continue with alibabacloud-oss-browser-upload-cors-diagnosis instead of this generic permission track",
        ],
        "troubleshooting_steps": [
            "Confirm the bucket owner account matches the account of the calling credential",
            "For cross-account scenarios, ask the bucket owner to grant authorization via Bucket Policy or RAM",
            "Parse the EC code in the response body for the exact forbidden reason; EC 0003-00000602 (CORS Origin/method not allowed) routes to alibabacloud-oss-browser-upload-cors-diagnosis",
        ],
        "official_doc_ref": DOC_403,
    },
    "SignatureDoesNotMatch": {
        "code": "SignatureDoesNotMatch",
        "http_status": 403,
        "category": "credential",
        "side": "client",
        "root_cause_directions": [
            "Wrong or rotated AccessKey Secret paired with the AccessKey ID",
            "Signature string built incorrectly (header ordering, Content-Type/MD5 mismatch, wrong canonical resource)",
            "Non-ASCII characters in x-oss-meta user metadata break the signature computation (real ticket case)",
            "Outdated SDK with a known signature bug; or V1 signature disabled for the bucket region while client still signs V1",
            "Clock drift between client and server exceeding the allowed skew",
            "Object name/path contains special characters (e.g. double slashes //) and the tool's path-encoding behavior diverges from the server-side signature computation (real ticket case: path encoding differs between ossutil versions)",
        ],
        "troubleshooting_steps": [
            "Verify the AccessKey ID/Secret pair is current and enabled (re-issue after rotation)",
            "Upgrade the SDK to the latest version and retry",
            "Ensure x-oss-meta values are ASCII-only; remove non-ASCII metadata and retry",
            "Check the bucket region's signature-version requirement (some regions disable V1; use V4 signing)",
            "Synchronize the client clock (NTP) and retry",
            "Compare the StringToSign returned in the error body with the one the client computed; if they diverge on the path, retry with another tool/SDK version that encodes the object key differently (e.g. ossutil 1.0 vs 2.x)",
            "Knowledge boundary: SignatureDoesNotMatch knowledge is held by three skills - this entry is the general credential/signature track; signature failures inside a multipart flow continue with alibabacloud-oss-multipart-upload-diagnosis, and presigned-URL signature errors continue with alibabacloud-oss-presigned-url-v4-diagnosis",
        ],
        "official_doc_ref": DOC_SIGN,
    },
    "InvalidAccessKeyId": {
        "code": "InvalidAccessKeyId",
        "http_status": 403,
        "category": "credential",
        "side": "client",
        "root_cause_directions": [
            "AccessKey ID does not exist (deleted, or copied with extra/missing characters)",
            "AccessKey is disabled in the RAM console",
            "Credential belongs to a different account than the bucket owner",
            "AK-bound network restriction (IP whitelist) does not cover the real source IP, e.g. CEN / forwarding-router source IPs - real ticket case observed this surfacing as InvalidAccessKeyId; official EC 0002-00000904 covers the same restriction surfacing as a disabled AccessKeyId",
        ],
        "troubleshooting_steps": [
            "Open the RAM console and confirm the AccessKey ID exists and is enabled",
            "Re-copy the AccessKey ID exactly (no spaces/newlines)",
            "Confirm the credential's account owns or is authorized on the target bucket",
            "Check the AK-bound network restriction (IP whitelist) against the real request source IP, including CEN / forwarding-router egress IPs",
        ],
        "official_doc_ref": DOC_403,
    },
    "SecurityTokenExpired": {
        "code": "SecurityTokenExpired",
        "http_status": 403,
        "category": "credential",
        "side": "client",
        "root_cause_directions": [
            "STS temporary credential expired during a long-running upload/download (ticket case: hundreds-of-MB direct upload outliving the token)",
            "Client cached the STS token and never refreshed it before expiry",
        ],
        "troubleshooting_steps": [
            "Refresh the STS token (AssumeRole) before retrying the operation",
            "For long transfers, shorten token usage window or refresh proactively near expiry",
            "Increase the STS role's MaxSessionDuration if transfers legitimately need more time",
        ],
        "official_doc_ref": DOC_403,
    },
    "RequestTimeTooSkewed": {
        "code": "RequestTimeTooSkewed",
        "http_status": 403,
        "category": "credential",
        "side": "client",
        "root_cause_directions": [
            "Client system clock differs from server time by more than 15 minutes",
        ],
        "troubleshooting_steps": [
            "Check the machine clock and synchronize with NTP",
            "Retry the request after clock correction",
        ],
        "official_doc_ref": DOC_PARSE,
    },
    "RequestTimeout": {
        "code": "RequestTimeout",
        "http_status": 400,
        "category": "network",
        "side": "both",
        "root_cause_directions": [
            "Client network unstable or bandwidth-limited; the connection or transfer did not finish inside the timeout (top ticket cluster after permission)",
            "Multipart part size too large for the available bandwidth; no timeout/retry tuning on the client",
            "Unnecessary use of the global-accelerate endpoint for a domestic same-region path, adding latency (real ticket case)",
            "Cross-border or long-distance network path with high loss",
        ],
        "troubleshooting_steps": [
            "Retry with smaller multipart parts (e.g. 1-10 MB) and enable SDK timeout/retry settings",
            "Test from another network (e.g. an ECS in the same region as the bucket) to isolate client vs server side",
            "Verify the endpoint choice: plain regional endpoint for same-region traffic; oss-accelerate only for cross-border acceleration",
            "Check local firewall/proxy for connection resets or long idle timeouts",
            "Enable resumable/multipart upload so retries do not restart from zero",
        ],
        "official_doc_ref": DOC_400,
    },
    "ConnectionTimeout": {
        "code": "ConnectionTimeout",
        "http_status": 400,
        "category": "network",
        "side": "client",
        "root_cause_directions": [
            "TCP connection to the OSS endpoint could not be established in time (client network, firewall, proxy)",
            "DNS resolution failure or slow resolution of the OSS domain",
            "Client-side connect timeout configured too short for an unstable link",
        ],
        "troubleshooting_steps": [
            "Verify DNS resolution and basic reachability of the endpoint domain from the client machine",
            "Check firewall/security-group/proxy rules between client and the OSS endpoint",
            "Raise the client connect timeout and add retries with backoff",
            "From an ECS in the bucket region, use the internal endpoint to confirm the server side is healthy",
        ],
        "official_doc_ref": DOC_400,
    },
    "EntityTooLarge": {
        "code": "EntityTooLarge",
        "http_status": 400,
        "category": "limit",
        "side": "client",
        "root_cause_directions": [
            "PostObject form policy (Post Policy content-length-range) caps the allowed body smaller than the file (ticket case: 20 KB image rejected)",
            "Single-request upload methods (PutObject simple upload, PostObject form upload, AppendObject) cap at 5 GB per request; for larger files use multipart/resumable upload, which supports up to 48.8 TB per file (official usage-limits doc)",
        ],
        "troubleshooting_steps": [
            "For PostObject, inspect the Post Policy content-length-range condition and raise the upper bound",
            "For files over 5 GB, switch from PutObject to Multipart Upload (single file up to 48.8 TB)",
            "Confirm the client actually sends the declared Content-Length (proxy truncation can also trigger size errors)",
        ],
        "official_doc_ref": DOC_LIMITS,
    },
    "InvalidArgument": {
        "code": "InvalidArgument",
        "http_status": 400,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "A request parameter is malformed or out of range (e.g. invalid partNumber, expires, or header value)",
            "Tool/SDK invoked with incompatible options for the operation (tool-usage ticket cluster)",
        ],
        "troubleshooting_steps": [
            "Read the ArgumentName/ArgumentValue fields in the error body to identify the offending parameter",
            "Correct the parameter per the API reference and retry",
            "If a tool (ossutil/SDK) produced the request, upgrade it and re-check the flags",
        ],
        "official_doc_ref": DOC_400,
    },
    "InvalidBucketName": {
        "code": "InvalidBucketName",
        "http_status": 400,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "Bucket name violates the OSS naming rules: only lowercase letters, digits and hyphens (-); must start and end with a lowercase letter or digit; length 3-63 characters (official EC 0015-00000001)",
            "Bucket name contains characters that are NEVER valid in OSS - a dot (.), underscore (_), uppercase letter or other symbol - so the bucket cannot exist under any account or region; real-ticket pattern: a dot-style name or a full domain carried over from another S3-compatible store is used as the bucket name",
            "SDK misuse: the Endpoint parameter was set to the bucket-prefixed domain (e.g. https://your-bucket.oss-cn-hangzhou.aliyuncs.com) instead of the regional endpoint, so the SDK parses the endpoint's bucket label as the bucket name (official doc example)",
            "Cloud-API error-code form: the same problem surfaces in the error body as the numeric EC 0015-00000001 - treat the numeric form and the symbolic code InvalidBucketName as one diagnosis",
        ],
        "troubleshooting_steps": [
            "Extract the bucket name actually used - from the Host header (the first label of bucket.oss-region.aliyuncs.com) or from the SDK configuration - and validate it against the rules: lowercase letters/digits/hyphens only, lowercase-letter-or-digit start and end, 3-63 characters",
            "If the name contains a dot, underscore, uppercase letter or any other invalid character: OSS bucket names cannot contain dots - rename the bucket per the rules and re-run the access test; do NOT go looking for the bucket first (a name like that can never exist)",
            "For SDK users, pass the regional endpoint (e.g. https://oss-cn-hangzhou.aliyuncs.com) as the Endpoint parameter and the bucket name separately, never the bucket-prefixed domain as the Endpoint",
            "After correcting the name, verify via the OSS console or a fresh request that the error is gone; an unrelated security-scanner probe with a malformed Host (non-OSS endpoint format) can also trigger this code and needs no action",
        ],
        "official_doc_ref": DOC_EC_0015_0001,
    },
    "InvalidPart": {
        "code": "InvalidPart",
        "http_status": 400,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "One or more parts listed in CompleteMultipartUpload do not exist, or their ETags do not match the ETags recorded at upload time (a part was re-uploaded with different content, or the UploadId of two upload sessions was mixed up)",
            "The complete list was assembled from a stale local resumable-upload checkpoint while the actual parts on the server had changed (real-ticket pattern)",
        ],
        "troubleshooting_steps": [
            "Re-list the uploaded parts for the UploadId (ListParts) and rebuild the complete list from the server-side part list, not from a local checkpoint/cache",
            "Re-upload any missing or ETag-mismatched part, then retry CompleteMultipartUpload",
            "For deeper multipart-flow diagnosis (checkpoint handling, part numbering, ordering), continue with alibabacloud-oss-multipart-upload-diagnosis",
        ],
        "official_doc_ref": DOC_400,
    },
    "PartOutOfBounds": {
        "code": "PartOutOfBounds",
        "http_status": 400,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "The partNumber parameter is outside the allowed range 1-10000 (each multipart upload accepts at most 10000 parts)",
        ],
        "troubleshooting_steps": [
            "Check that partNumber in the request is an integer within 1-10000",
            "If the file needs more than 10000 parts at the current part size, raise the part size (at least ceil(fileSize/10000)) and restart the multipart upload",
            "For deeper multipart-flow diagnosis, continue with alibabacloud-oss-multipart-upload-diagnosis",
        ],
        "official_doc_ref": DOC_400,
    },
    "InvalidPartOrder": {
        "code": "InvalidPartOrder",
        "http_status": 400,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "The part list in CompleteMultipartUpload is not sorted by partNumber ascending (the complete request requires parts in ascending part-number order)",
        ],
        "troubleshooting_steps": [
            "Sort the part list by partNumber ascending and resend CompleteMultipartUpload",
            "Build the list from the ListParts output, which is already in ascending order",
            "For deeper multipart-flow diagnosis, continue with alibabacloud-oss-multipart-upload-diagnosis",
        ],
        "official_doc_ref": DOC_400,
    },
    "NoSuchKey": {
        "code": "NoSuchKey",
        "http_status": 404,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "Object key does not exist: typo, wrong case, or wrong path prefix",
            "Multipart upload never called CompleteMultipartUpload, so the object was never assembled (ticket case: only fragments visible)",
            "Static-site access to a directory without a configured default index object",
        ],
        "troubleshooting_steps": [
            "List the bucket prefix and compare the exact key (keys are case-sensitive)",
            "If fragments/parts are visible, complete or abort the dangling multipart upload and re-upload properly",
            "For website access, configure the default index object or request the full object key",
        ],
        "official_doc_ref": DOC_404,
    },
    "NoSuchBucket": {
        "code": "NoSuchBucket",
        "http_status": 404,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "Bucket name is legal but the bucket does not exist: misspelled, deleted, or created by/for another account (official EC 0015-00000101)",
            "Bucket name itself is ILLEGAL (contains a dot, underscore, uppercase letter, or is not 3-63 chars of lowercase letters/digits/hyphens): such a bucket can NEVER exist - if the error body instead shows EC 0015-00000001 / InvalidBucketName, the fix is renaming the bucket, not looking it up (distinguish the two EC codes before troubleshooting)",
            "'Not visible' vs 'not existing': a bucket that DOES exist can still surface as not-found when the calling credential lacks permission to see it (e.g. an unauthorized RAM user, or a cross-account access without authorization) - verify with the bucket owner's credential before concluding the bucket is gone",
            "Request sent to the wrong region endpoint for an existing bucket",
            "STS flow misuse: the SDK endpoint used to obtain temporary credentials was set to the OSS domain instead of the STS domain, so bucket resolution failed (official doc example)",
        ],
        "troubleshooting_steps": [
            "First validate the bucket name itself: lowercase letters/digits/hyphens only, lowercase-letter-or-digit start and end, 3-63 characters; a name containing '.' or '_' is illegal and must be renamed (see InvalidBucketName / EC 0015-00000001)",
            "Distinguish 'bucket truly absent' from 'no permission to see it': re-run GetBucketInfo/ListBuckets with the bucket owner's credential; only conclude misspelling/deletion after the owner's credential also cannot see the bucket",
            "Confirm the exact bucket name spelling in the OSS console",
            "Confirm the endpoint region matches the bucket's region",
            "For STS temporary-credential flows, verify the AssumeRole endpoint uses the STS domain (e.g. sts.cn-hangzhou.aliyuncs.com), not the OSS domain",
        ],
        "official_doc_ref": DOC_EC_0015_0101,
    },
    "SlowDown": {
        "code": "SlowDown",
        "http_status": 503,
        "category": "server",
        "side": "server",
        "root_cause_directions": [
            "Request rate (QPS) exceeded the throttling limit for the bucket/prefix",
            "Hot prefix: too many requests concentrated on keys sharing one prefix",
        ],
        "troubleshooting_steps": [
            "Apply exponential backoff with jitter and retry",
            "Spread object keys across multiple prefixes to raise aggregate throughput",
            "Reduce client concurrency or add a local cache for hot objects",
        ],
        "official_doc_ref": DOC_503,
    },
    "InvalidObjectState": {
        "code": "InvalidObjectState",
        "http_status": 403,
        "category": "limit",
        "side": "client",
        "root_cause_directions": [
            "Operation not allowed for the object's storage class (ticket case: archive object read before restore)",
        ],
        "troubleshooting_steps": [
            "Check the object's storage class; restore Archive/ColdArchive objects before reading",
            "Or enable archive direct-read on the bucket where supported",
            "Wait for the restore to complete, then retry",
        ],
        "official_doc_ref": DOC_403,
    },
    "InternalError": {
        "code": "InternalError",
        "http_status": 500,
        "category": "server",
        "side": "server",
        "root_cause_directions": [
            "Transient server-side failure inside OSS",
        ],
        "troubleshooting_steps": [
            "Retry with exponential backoff (the error is transient by definition)",
            "If persistent, record the RequestId and escalate via a support ticket",
        ],
        "official_doc_ref": DOC_COMMON,
    },
    "BucketAlreadyExists": {
        "code": "BucketAlreadyExists",
        "http_status": 409,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "Bucket names are globally unique across all accounts and regions; the name is already created by another account (real ticket case: a typo in the bucket name hit another account's bucket, so uploads returned 403 and the create failed)",
            "Re-creating a same-name bucket shortly after deletion: OSS requires waiting several hours (usually 4-8 hours) before the name can be created again",
        ],
        "troubleshooting_steps": [
            "Confirm the exact intended bucket name in the OSS console (a one-letter typo can hit another account's bucket)",
            "If the name is occupied by another account, pick a different name - it cannot be created or deleted cross-account",
            "If you recently deleted a same-name bucket yourself, wait several hours (usually 4-8 hours) and recreate",
        ],
        "official_doc_ref": DOC_PUTBUCKET,
    },
    "ServiceUnavailable": {
        "code": "ServiceUnavailable",
        "http_status": 503,
        "category": "server",
        "side": "server",
        "root_cause_directions": [
            "Service temporarily unavailable, or public-network traffic degraded (e.g. bucket moved into the DDoS sandbox: public access degraded while internal access stays normal)",
        ],
        "troubleshooting_steps": [
            "Retry with backoff for transient occurrences",
            "If the bucket recently received attack traffic, sandbox degradation is expected and is handled outside this skill's scope - escalate to support",
            "Record the RequestId for the support ticket",
        ],
        "official_doc_ref": DOC_503,
    },
    "UserDisable": {
        "code": "UserDisable",
        "http_status": 403,
        "category": "permission",
        "side": "client",
        "root_cause_directions": [
            "The calling account is disabled; official EC 0003-00000801 lists three causes: overdue payment, account disabled for security reasons, or OSS service not activated (observed in real tickets as the EC numeric code)",
        ],
        "troubleshooting_steps": [
            "Check the account for overdue payment in the Billing console and settle the outstanding balance",
            "If the account was disabled for security reasons, follow the official security-violation handling guide",
            "If OSS was never activated, activate the OSS service in the console",
        ],
        "official_doc_ref": DOC_EC_0003_0801,
    },
    "BucketDisable": {
        "code": "BucketDisable",
        "http_status": 403,
        "category": "permission",
        "side": "both",
        "root_cause_directions": [
            "The bucket is banned by a security policy due to detected malicious behavior (official EC 0003-00000908); normal access is blocked until resolved (observed in real tickets as the EC numeric code)",
        ],
        "troubleshooting_steps": [
            "Verify whether the bucket hosts violating content or malicious behavior",
            "Open a support ticket to appeal and request unblocking",
        ],
        "official_doc_ref": DOC_EC_0003_0908,
    },
    "NoSuchUpload": {
        "code": "NoSuchUpload",
        "http_status": 404,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "The multipart UploadId does not exist, was mistyped, or has expired: the upload was already aborted or already completed (official EC 0017-00000244; also returned when AbortMultipartUpload/CompleteMultipartUpload targets a finished UploadId)",
        ],
        "troubleshooting_steps": [
            "Re-run InitiateMultipartUpload to obtain a fresh UploadId and restart the multipart flow",
            "Discard the stale resumable checkpoint when the UploadId no longer resolves (real ticket case)",
            "Treat CompleteMultipartUpload returning 200 as the success criterion before reusing any UploadId",
        ],
        "official_doc_ref": DOC_EC_0017_0244,
    },
    "CallbackFailed": {
        "code": "CallbackFailed",
        "http_status": 203,
        "category": "usage",
        "side": "client",
        "root_cause_directions": [
            "The upload succeeded but the callback step failed: OSS POSTed to callbackUrl and did not receive 200 OK (official EC 0007-00000203) - callback server not started, callbackUrl missing from the callback parameters, or network between OSS and the callback server blocked (e.g. firewall)",
            "Callback server processing exceeded the 5-second limit (official EC 0007-00000202)",
        ],
        "troubleshooting_steps": [
            "Verify the callback endpoint independently (e.g. curl/Postman POST returns HTTP/1.1 200 OK) and confirm the URL is publicly reachable",
            "Ensure callbackUrl is set in the callback parameters and points to a public address",
            "Make the callback handler asynchronous so it returns within 5 seconds",
        ],
        "official_doc_ref": DOC_EC_0007_0203,
    },
}

# HTTP status -> codes that commonly map to it (used when only the status is known).
# 429 note: the official OSS 429 doc (help.aliyun.com/zh/oss/user-guide/429-error,
# verified 2026-08-26) lists QpsLimitExceeded only and does NOT document a
# TooManyRequests error code; the former TooManyRequests catalog entry had no
# official source and was removed. 429 input therefore degrades to the
# status-only fallback anchored on SlowDown, the catalog's throttling code.
# 499 note: not an official OSS status; it is emitted by nginx-style
# proxies/clients when the client closed the connection early (client-side
# cancel or timeout in front of OSS). Measured on real tickets, so route it
# to the network-family codes instead of failing.
STATUS_TO_CODES = {
    203: ["CallbackFailed"],
    400: ["RequestTimeout", "ConnectionTimeout", "EntityTooLarge",
           "InvalidArgument", "InvalidBucketName", "InvalidPart",
           "PartOutOfBounds", "InvalidPartOrder"],
    409: ["BucketAlreadyExists"],
    403: ["AccessDenied", "SignatureDoesNotMatch", "InvalidAccessKeyId",
           "SecurityTokenExpired", "AccessForbidden", "InvalidObjectState",
           "RequestTimeTooSkewed", "UserDisable", "BucketDisable"],
    404: ["NoSuchKey", "NoSuchBucket", "NoSuchUpload"],
    429: ["SlowDown"],
    499: ["RequestTimeout", "ConnectionTimeout"],
    500: ["InternalError"],
    503: ["SlowDown", "ServiceUnavailable"],
}

# Client-side terminology -> canonical catalog code (lowercase keys).
# Real tickets report the client/tool error string instead of the OSS error
# code; these synonyms route them to the matching network-family entry so
# the diagnosis hits instead of failing.
CLIENT_TERM_SYNONYMS = {
    "sockettimeout": "ConnectionTimeout",
    "socket timeout": "ConnectionTimeout",
    "sockettimeoutexception": "ConnectionTimeout",
    "etimedout": "ConnectionTimeout",
    "net::err_empty_response": "ConnectionTimeout",
    # SDK exception wrapper names pasted verbatim from stack traces
    # (ticket 0001ZRGGE6: oss2 RequestError wrapping connect/write timeout).
    "requesterror": "ConnectionTimeout",
    "socketexception": "ConnectionTimeout",
    "connection timed out": "ConnectionTimeout",
    # Chinese natural-language forms of the same client-side timeouts
    # (ticket-verified phrasings; route like the English synonyms).
    "\u8fde\u63a5\u8d85\u65f6": "ConnectionTimeout",
    "\u8bf7\u6c42\u9519\u8bef": "ConnectionTimeout",
    "\u8bf7\u6c42\u8d85\u65f6": "RequestTimeout",
    # EC numeric-code aliases: the official error body carries both the
    # symbolic Code and the numeric EC field; these two EC codes own the
    # bucket-naming family (official pages verified 2026-09-02) and route
    # straight to the full SOP instead of degrading to status-only lists.
    "0015-00000001": "InvalidBucketName",
    "0015-00000101": "NoSuchBucket",
    # connection-reset / broken-pipe family (SDK stack-trace forms observed
    # in the client-network ticket cluster, 87/month).
    "connectionreset": "ConnectionTimeout",
    "connection reset": "ConnectionTimeout",
    "connectionreseterror": "ConnectionTimeout",
    "connectionrefused": "ConnectionTimeout",
    "connection refused": "ConnectionTimeout",
    "brokenpipeerror": "ConnectionTimeout",
    "broken pipe": "ConnectionTimeout",
    "readtimeout": "RequestTimeout",
    "read timeout": "RequestTimeout",
    "clienterror": "ConnectionTimeout",
    # DNS-resolution family (stack-trace forms; the ConnectionTimeout entry
    # already carries the DNS root-cause direction).
    "getaddrinfo failed": "ConnectionTimeout",
    "getaddrinfo": "ConnectionTimeout",
    "nameresolutionerror": "ConnectionTimeout",
    "name or service not known": "ConnectionTimeout",
    "\u57df\u540d\u89e3\u6790\u5931\u8d25": "ConnectionTimeout",
    "\u65e0\u6cd5\u89e3\u6790\u57df\u540d": "ConnectionTimeout",
}

# Chinese natural-language family word: the bare timeout word (\u8d85\u65f6)
# alone cannot decide request-timeout vs connection-timeout, so it yields BOTH
# candidates as a degraded family list instead of failing (ticket phrasing was
# "how to solve the Germany timeout problem" - the bare word was previously
# unroutable).
CLIENT_TERM_FAMILIES = {
    "\u8d85\u65f6": ["RequestTimeout", "ConnectionTimeout"],
}

# Symptom keywords (lowercase substring; Chinese ticket phrasings, verified
# against the transfer-scenario first-question set) -> candidate catalog
# codes. Layer purpose: customers usually describe the SYMPTOM only (in the
# 42-question transfer set only 7 questions carry error text); when no error
# code / status can be extracted, these keys keep the case routable as a
# DEGRADED candidate list instead of FAIL. Subject discrimination: generic
# action words (upload / download) are never keys on their own - every key
# pairs an action or size marker with a failure symptom. Out-of-domain wording
# is handled by DOMAIN_TRANSFER_GUARDS before this layer (entry script).
SYMPTOM_KEYWORDS = {
    # large-file + upload failure -> limit + network candidates
    "\u5927\u6587\u4ef6": ["EntityTooLarge", "RequestTimeout", "ConnectionTimeout"],
    "\u5927\u70b9\u7684": ["EntityTooLarge", "RequestTimeout", "ConnectionTimeout"],
    "\u5927\u89c6\u9891": ["EntityTooLarge", "RequestTimeout", "ConnectionTimeout"],
    "\u6587\u4ef6\u592a\u5927": ["EntityTooLarge", "RequestTimeout", "ConnectionTimeout"],
    # mid-transfer break -> network family
    "\u5230\u4e00\u534a": ["RequestTimeout", "ConnectionTimeout"],
    "\u4e00\u534a\u5c31": ["RequestTimeout", "ConnectionTimeout"],
    "\u603b\u662f\u65ad": ["RequestTimeout", "ConnectionTimeout"],
    "\u8001\u662f\u65ad": ["RequestTimeout", "ConnectionTimeout"],
    "\u7ecf\u5e38\u65ad": ["RequestTimeout", "ConnectionTimeout"],
    "\u603b\u662f\u5931\u8d25": ["RequestTimeout", "ConnectionTimeout"],
    "\u8001\u662f\u5931\u8d25": ["RequestTimeout", "ConnectionTimeout"],
    "\u4f20\u4e0d\u5b8c": ["RequestTimeout", "ConnectionTimeout"],
    "copy \u4e0d\u5b8c": ["RequestTimeout", "ConnectionTimeout"],
    "copy\u4e0d\u5b8c": ["RequestTimeout", "ConnectionTimeout"],
    # bucket-domain unreachable while the plain endpoint works -> DNS family
    "bucket \u57df\u540d": ["ConnectionTimeout"],
    "bucket\u57df\u540d": ["ConnectionTimeout"],
    "\u6876\u57df\u540d": ["ConnectionTimeout"],
    "\u57df\u540d\u8bbf\u95ee\u4e0d\u5230": ["ConnectionTimeout"],
    "\u57df\u540d\u4e0d\u901a": ["ConnectionTimeout"],
    # generic upload failure -> top ticket clusters (permission/network/limit)
    "\u4e0a\u4f20\u5931\u8d25": ["AccessDenied", "RequestTimeout", "ConnectionTimeout",
                "EntityTooLarge"],
    "\u4e0a\u4f20\u4e0d\u6210\u529f": ["AccessDenied", "RequestTimeout", "ConnectionTimeout",
                   "EntityTooLarge"],
    "\u4f20\u4e0d\u4e0a\u53bb": ["AccessDenied", "RequestTimeout", "ConnectionTimeout",
                "EntityTooLarge"],
    "\u4f20\u4e0d\u4e0a": ["AccessDenied", "RequestTimeout", "ConnectionTimeout",
              "EntityTooLarge"],
    # generic download failure -> usage + permission + network candidates
    "\u4e0b\u8f7d\u5931\u8d25": ["NoSuchKey", "AccessDenied", "RequestTimeout",
                "ConnectionTimeout"],
    "\u4e0b\u8f7d\u4e0d\u6210\u529f": ["NoSuchKey", "AccessDenied", "RequestTimeout",
                   "ConnectionTimeout"],
    "\u4e0b\u4e0d\u4e0b\u6765": ["NoSuchKey", "AccessDenied", "RequestTimeout",
                "ConnectionTimeout"],
    "\u4e0b\u8f7d\u4e0d\u4e0b\u6765": ["NoSuchKey", "AccessDenied", "RequestTimeout",
                   "ConnectionTimeout"],
}

# Out-of-domain transfer guards (presigned-skill guard pattern): wording
# that marks the failing subject as a NON-OSS product produces NO OSS
# diagnosis here. Each guard is a tuple of word groups; EVERY group must
# contribute at least one word present in the (lowercased) text. Guards
# apply only when the wording carries NO OSS context anchor (checked by
# the caller) - an OSS problem mentioned alongside stays in scope.
DOMAIN_TRANSFER_GUARDS = (
    (("ssh",),),                  # SSH connectivity is not an OSS transfer
    (("mysql", "mariadb"),),      # MySQL family connectivity
    (("redis",),),
    (("mongodb",),),
    (("postgres", "postgresql"),),
    (("rds",),),                  # managed database
    (("cdn",),),                  # CDN domain -> cdn-origin-config skill
    (("k8s", "kubernetes"),),
    (("ecs",), ("curl",)),        # host-level curl probe on ECS, no OSS target
)

# OSS context anchors: any of these (lowercased substring) keeps the case
# in scope even when a guard word appears (e.g. a ticket saying "curl-probing
# the OSS endpoint from ECS returns 403" stays diagnosable).
OSS_CONTEXT_ANCHORS = (
    "oss", "\u5bf9\u8c61\u5b58\u50a8", "bucket", "\u6876", "oss-cn", "oss-accelerate",
    "ossutil", "osscmd", "ossbrowser", "oss2", "aliyuncs",
    "accesskey", "aksk", "sts",
)

# Known non-transfer EC numeric codes -> owning sibling skill. Surfaced as a
# referral block so a wrong-door input reaches the right skill in one hop
# instead of a blind "give me the error body" loop.
EC_CODE_REFERRALS = {
    "0003-00000005": "alibabacloud-oss-direct-access-link-diagnosis (private-object direct-access link / platform ban)",
    "0003-00000201": "alibabacloud-oss-cross-account-auth-diagnosis (explicit RAM Deny)",
    "0003-00000602": "alibabacloud-oss-browser-upload-cors-diagnosis (CORS rule missing the request Origin/method)",
    # 0024-00000008: first-hand measured behavior, NOT in the official 0024 EC
    # family (officially uncatalogued). Owned + annotated (RequestId-level probe
    # evidence, TAC-2 boundary statement) by transfer-acceleration-diagnosis;
    # this skill only routes it onward, never claims it as an official code.
    "0024-00000008": "alibabacloud-oss-transfer-acceleration-diagnosis (transfer acceleration not enabled)",
}

# RequestId-only guidance (client-side layer only; server-side log lookup
# by RequestId is a support-only capability and stays out of this
# zero-cloud-API skill). Distilled from the reqId diagnosis playbook: with
# only a RequestId the root cause cannot be located from the client side;
# the actionable path is to recover the FULL error response body around the
# RequestId, and the client type decides where to look for it.
REQUEST_ID_GUIDANCE = {
    "note": "A RequestId alone cannot locate the root cause from the client side; the full error response body (Code, Message, RequestId, EC, RecommendDoc) around this RequestId is required.",
    "client_type_paths": [
        "Java SDK: enable OSS SDK logging (com.aliyun.oss logger config) or catch OSSException/ClientException in code and print the full response body with the error Code",
        "Python SDK (oss2): wrap the call in try/except and print the oss2 exception details; oss2 exceptions carry status, request_id and the error code",
        "ossutil: re-run the failing command with a higher log level and read the error block; the tool prints the error code, request id and EC fields",
        "Browser/JS: open the devtools Network panel, click the failing OSS request and read the response body (Code/Message/EC); CORS-blocked bodies must be read from the console response preview",
        "Other tools/proxies: capture the raw HTTP response body of the failing request via the tool's own error dump or a capture layer",
    ],
    "ec_hint": "Once the recovered body carries the Code or numeric EC field, re-run this skill with it; keep the RequestId for support-ticket escalation.",
    "doc_ref": DOC_PARSE,
}

CATEGORY_LABELS = {
    "permission": "permission / RAM / Bucket Policy / ACL",
    "credential": "credential & signature",
    "network": "client network environment",
    "usage": "tool / SDK / API usage",
    "limit": "file or object limits",
    "server": "server side / throttling",
}

# Transfer-acceleration / network-optimization suggestions attached when the
# category is network (or the operation times out) — distilled from tickets.
NETWORK_OPTIMIZATION_SUGGESTIONS = [
    "Prefer the plain regional endpoint for same-region traffic; reserve the oss-accelerate endpoint for cross-border transfers",
    "Enable multipart upload with tuned part size plus SDK timeout and retry settings",
    "For cross-region or cross-border transfers, evaluate OSS Transfer Acceleration instead of ad-hoc global-accelerate domains",
    "Run the same operation from an ECS in the bucket region via the internal endpoint to separate client-network issues from server-side ones",
]

# --- Inline boundary assertions: TooManyRequests removal (2026-08-26) -------
# The official OSS 429 doc lists QpsLimitExceeded only; TooManyRequests has no
# official source, so the entry was removed. After removal:
#   * TooManyRequests no longer matches the catalog (exact or fuzzy);
#   * HTTP 429 input still degrades through the status-only fallback
#     (candidates anchored on SlowDown), never crashes or hits an unmapped key.
assert "TooManyRequests" not in ERROR_CATALOG
assert "TooManyRequests" not in {c for codes in STATUS_TO_CODES.values() for c in codes}
assert STATUS_TO_CODES.get(429) == ["SlowDown"]
assert all(c in ERROR_CATALOG for c in STATUS_TO_CODES[429])
# Client-term synonyms and the 499 route must all resolve to catalog codes.
assert all(c in ERROR_CATALOG for c in CLIENT_TERM_SYNONYMS.values())
assert all(c in ERROR_CATALOG for c in STATUS_TO_CODES[499])
assert CLIENT_TERM_SYNONYMS["etimedout"] == "ConnectionTimeout"
# Chinese / SDK-wrapper synonyms must resolve to catalog codes too.
assert CLIENT_TERM_SYNONYMS["requesterror"] == "ConnectionTimeout"
assert CLIENT_TERM_SYNONYMS["\u8fde\u63a5\u8d85\u65f6"] == "ConnectionTimeout"
assert CLIENT_TERM_SYNONYMS["\u8bf7\u6c42\u8d85\u65f6"] == "RequestTimeout"
# New official codes added 2026-08-27 (knowledge-completeness backfill): every
# status-mapped code must resolve in the catalog.
assert all(c in ERROR_CATALOG for codes in STATUS_TO_CODES.values() for c in codes)

# --- Inline boundary assertions: bucket-name family + routing layers (2026-09) --
# Bucket-naming EC family (official pages verified 2026-09-02): both EC
# numeric aliases and the symbolic codes must exist and stay cross-linked.
assert "InvalidBucketName" in ERROR_CATALOG
assert "NoSuchBucket" in ERROR_CATALOG
assert CLIENT_TERM_SYNONYMS["0015-00000001"] == "InvalidBucketName"   # normal
assert CLIENT_TERM_SYNONYMS["0015-00000101"] == "NoSuchBucket"        # normal
assert "InvalidBucketName" in STATUS_TO_CODES[400]                    # boundary: status map
assert ERROR_CATALOG["InvalidBucketName"]["official_doc_ref"].endswith("0015-00000001")
assert ERROR_CATALOG["NoSuchBucket"]["official_doc_ref"].endswith("0015-00000101")
# The two SOPs must carry the mutual-distinction knowledge (bucket-name
# illegal vs bucket absent).
_ns_dir = " ".join(ERROR_CATALOG["NoSuchBucket"]["root_cause_directions"])
assert "0015-00000001" in _ns_dir and "0015-00000101" in _ns_dir
assert any("dot" in d or "'.'" in d for d in ERROR_CATALOG["InvalidBucketName"]["troubleshooting_steps"])
# Multipart completeness family (added 2026-09): all three codes live in the
# 400 status map and carry the multipart-skill referral step.
for _mp in ("InvalidPart", "PartOutOfBounds", "InvalidPartOrder"):
    assert _mp in ERROR_CATALOG and _mp in STATUS_TO_CODES[400]
    assert any("multipart-upload-diagnosis" in s
               for s in ERROR_CATALOG[_mp]["troubleshooting_steps"])
# Synonym families added 2026-09: reset/DNS/EC aliases must resolve.
for _key in ("connectionreset", "connectionreseterror", "connectionrefused",
             "brokenpipeerror", "readtimeout", "clienterror",
             "getaddrinfo failed", "nameresolutionerror", "\u57df\u540d\u89e3\u6790\u5931\u8d25"):
    assert CLIENT_TERM_SYNONYMS[_key] in ERROR_CATALOG          # normal
assert CLIENT_TERM_SYNONYMS["readtimeout"] == "RequestTimeout"  # boundary: read side
assert all(c in ERROR_CATALOG for c in CLIENT_TERM_FAMILIES["\u8d85\u65f6"])  # family resolves
# Symptom layer: every key maps to catalog codes only.
for _codes in SYMPTOM_KEYWORDS.values():
    assert _codes and all(c in ERROR_CATALOG for c in _codes)
assert SYMPTOM_KEYWORDS["\u5927\u6587\u4ef6"] == ["EntityTooLarge", "RequestTimeout", "ConnectionTimeout"]
# Guards: single-word guards hit; the AND-group guard needs both words.
assert any(all(w in "\u670d\u52a1\u5668 ssh \u8fde\u63a5\u8d85\u65f6" for w in g) for guard in DOMAIN_TRANSFER_GUARDS for g in [guard[0]] if len(guard) == 1)  # normal: ssh
assert any("mysql" in g for guard in DOMAIN_TRANSFER_GUARDS for g in guard)   # normal: mysql group
# EC referrals: targets are full skill names, never bare codes.
for _ec, _target in EC_CODE_REFERRALS.items():
    assert _ec not in CLIENT_TERM_SYNONYMS                       # referral codes are not aliases
    assert _target.startswith("alibabacloud-oss-")              # normal
assert set(EC_CODE_REFERRALS) == {"0003-00000005", "0003-00000201",
                                  "0003-00000602", "0024-00000008"}  # 0024-00000008 = first-hand measured, officially uncatalogued (referral only)
# RequestId guidance block sanity (client-side layer only).
assert len(REQUEST_ID_GUIDANCE["client_type_paths"]) >= 5
assert REQUEST_ID_GUIDANCE["doc_ref"].startswith("https://help.aliyun.com")
# AccessForbidden CORS distinction (official EC 0003-00000602).
_af_dir = " ".join(ERROR_CATALOG["AccessForbidden"]["root_cause_directions"])
assert "0003-00000602" in _af_dir and "browser-upload-cors" in _af_dir
# SignatureDoesNotMatch three-holder boundary note.
_sdm_steps = " ".join(ERROR_CATALOG["SignatureDoesNotMatch"]["troubleshooting_steps"])
assert "multipart-upload-diagnosis" in _sdm_steps and "presigned-url-v4" in _sdm_steps
