# Troubleshooting Playbook

Four diagnosis tracks aligned with the root-cause clustering of 472 real
support tickets in the OSS transfer scenario (472 scenario hits; 154 tickets
mention 403):

| Track | Ticket count | Share |
| --- | --- | --- |
| Permission / RAM / Bucket Policy / ACL | 196 | dominant |
| Client network | 87 | high |
| Credential and signature | 57 | medium |
| Tool / SDK / API usage (multipart, resumable transfer) | 49 | medium |
| Custom domain / CNAME | 25 | low |
| CORS | 13 | low |
| Hotlink protection (Referer) | 9 | low |
| Object missing / endpoint / server side / size / storage class | <=6 each | rare but kept |

Low-frequency codes (SignatureDoesNotMatch, RequestTimeout, EntityTooLarge,
SlowDown) appear rarely in tickets but are retained as first-class catalog
entries because they are deterministic to diagnose.

## Track 1 - Permission (AccessDenied, AccessForbidden, InvalidObjectState)

Conclusion from tickets: most 403s are authorization problems, not network
problems. Check in this order:
1. Parse the EC code and RecommendDoc in the error response body (error-response parsing doc) to locate the exact denial reason.
2. Confirm the RAM identity's policy grants the exact oss action on the bucket/object resource ARN.
3. Check Bucket Policy, bucket ACL and object ACL for explicit denies.
4. Check AccessKey network-policy IP whitelist against the real request source IP (public vs VPC vs CEN forwarding IP; IPv4 and IPv6 are separate addresses - a policy listing only IPv4 ranges still denies IPv6 requests, real ticket case).
5. Verify the endpoint region matches the bucket region.
6. If Referer hotlink protection is enabled, verify the request Referer is whitelisted.
7. If the object is Archive/ColdArchive, restore it (or enable archive direct-read) before reading.
8. If the denied action is Bucket-level (e.g. ListMultipartUploads), authorize it on the bucket-level resource ARN without oss:Prefix directory conditions (authorization syntax and elements doc lists each action's level).
9. If the denial mentions an STS SessionPolicy, verify the policy uses only officially supported condition keys; acs:Referer is not supported - move Referer control to Bucket-level hotlink protection.

Policy evaluation semantics (official authorization model):
- RAM policy and Bucket Policy are evaluated independently and a single explicit Deny in either one rejects the request (Deny wins over Allow). Both layers must grant the action for it to succeed.
- Enabling Block Public Access (account-level or bucket-level) overrides any ACL/Bucket Policy that allows public (anonymous) access - public reads start failing with AccessDenied even if the bucket ACL is public-read. Check this switch when public access "suddenly" breaks.

## Track 2 - Credential and signature (SignatureDoesNotMatch, InvalidAccessKeyId, SecurityTokenExpired, RequestTimeTooSkewed)

Conclusion from tickets: signature failures cluster around rotated secrets,
non-ASCII metadata, and expired STS tokens during long transfers.
1. Verify the AccessKey ID/Secret pair is current and enabled (re-issue after rotation).
2. Upgrade the SDK to the latest version and retry (known signature bugs in old versions).
3. Ensure x-oss-meta values are ASCII only; remove non-ASCII metadata and retry.
4. Check the bucket region's signature-version requirement (some regions disable V1; use V4 signing).
5. Synchronize the client clock (NTP) and retry; skew beyond 15 minutes is rejected.
6. For STS: refresh the token before retrying; for long transfers, refresh proactively near expiry or raise the role's max session duration.
7. Compare the StringToSign returned in the error body with the one the client computed; if they diverge on the path, the object key contains special characters (e.g. double slashes //) whose encoding differs between tool versions - retry with another tool/SDK version (real ticket case: ossutil 2.x vs 1.0 path encoding).

## Track 3 - Client network (RequestTimeout, ConnectionTimeout)

Conclusion from tickets: timeout-family errors are client-network problems
unless a same-region control test proves otherwise.
1. Retry with smaller multipart parts (e.g. 1-10 MB) and enable SDK timeout/retry settings.
2. Test from another network (e.g. an ECS in the same region as the bucket, using the internal endpoint) to isolate client vs server side.
3. Verify the endpoint choice: plain regional endpoint for same-region traffic; the global-accelerate endpoint only for cross-border acceleration (misuse caused real SocketTimeout tickets).
4. Check local firewall/proxy for connection resets or long idle timeouts.
5. Enable resumable/multipart transfer so retries do not restart from zero.
6. The `-internal` endpoint (`oss-<region>-internal.aliyuncs.com`) is reachable only from the Alibaba Cloud internal network of the same region (e.g. same-region ECS); from the public internet it times out / fails to connect. This is expected behavior, not an outage - switch to the public endpoint outside the VPC (endpoint deep dive belongs to alibabacloud-oss-endpoint-internal-diagnosis).

Network optimization / transfer acceleration advice (attached automatically
by the script for network-category errors):
- Prefer the plain regional endpoint for same-region traffic; reserve the oss-accelerate endpoint for cross-border transfers.
- Enable multipart upload with tuned part size plus SDK timeout and retry settings.
- For cross-region or cross-border transfers, evaluate OSS Transfer Acceleration instead of ad-hoc global-accelerate domains.
- Run the same operation from an ECS in the bucket region via the internal endpoint to separate client-network issues from server-side ones.

## Track 4 - Tool usage and limits (InvalidArgument, InvalidBucketName, NoSuchBucket, InvalidPart, PartOutOfBounds, InvalidPartOrder, NoSuchKey, EntityTooLarge, BucketAlreadyExists)

Conclusion from tickets: multipart misuse (parts uploaded but never
completed) and form-policy size caps are the recurring causes.
1. Read the ArgumentName/ArgumentValue fields in the error body to identify the offending parameter; correct it per the API reference.
2. If fragments/parts are visible but the object is missing, complete or abort the dangling multipart upload and re-upload properly.
3. For PostObject EntityTooLarge, inspect the Post Policy content-length-range condition and raise the upper bound (ticket case: a 20 KB image rejected by a tight cap).
4. For files over 5 GB, switch from single-request upload to Multipart Upload (single file up to 48.8 TB; simple/form/append uploads cap at 5 GB per request per the official usage-limits doc).
5. Compare the exact object key (keys are case-sensitive) and confirm the bucket name and endpoint region.
6. For BucketAlreadyExists (409 on create): bucket names are globally unique - confirm the name is not a typo hitting another account's bucket; pick a different name, or wait several hours (usually 4-8) after deleting a same-name bucket before recreating.
7. Bucket-name legality first (InvalidBucketName / EC 0015-00000001 vs NoSuchBucket / EC 0015-00000101): extract the bucket name actually used (Host header first label, or SDK config) and validate it - lowercase letters/digits/hyphens only, lowercase-letter-or-digit start and end, 3-63 chars. A name containing a dot or underscore is illegal and can never exist: the fix is renaming, not looking up. Only a VALID name that cannot be found points to misspelling/deletion - and distinguish "bucket truly absent" from "no permission to see it" by re-running GetBucketInfo/ListBuckets with the bucket owner's credential before concluding deletion.
8. Multipart completeness family (InvalidPart / PartOutOfBounds / InvalidPartOrder): rebuild the complete list from ListParts output (server-side truth, already ascending), keep partNumber within 1-10000 (raise part size if more parts would be needed), and re-upload any ETag-mismatched part; deeper multipart-flow diagnosis (checkpoints, part numbering) belongs to alibabacloud-oss-multipart-upload-diagnosis.

Tool selection notes (official docs, for GUI-tool download/upload 404 or hangs):
- If a GUI tool reports files missing/404 that exist in the console, verify the exact keys via console or API first - tool-side data desync is a known cause (real ticket case).
- The official docs recommend upgrading from ossbrowser 1.0 to ossbrowser 2.0, and recommend ossutil for public-network transfers over 10 GB or very large batches (ossbrowser 1.0 usage-limits doc).
- Downloads via tools still incur request fees and outbound traffic fees per normal OSS billing (billing deep dives belong to alibabacloud-oss-billing-diagnosis).

## Server-side codes (SlowDown, InternalError, ServiceUnavailable)

These are not client bugs; do not blame the user's configuration first:
1. Apply exponential backoff with jitter and retry; respect Retry-After if present.
2. Spread object keys across multiple prefixes to raise aggregate throughput (hot-prefix throttling).
3. Reduce client concurrency or add a local cache for hot objects.
4. If the bucket recently received attack traffic, public-network degradation may be sandbox-related and is outside this skill's scope - stop the diagnosis and refer the case to human support.

## RequestId-only tickets (no error code yet)

Real tickets frequently arrive with only a RequestId ("upload failed, here
is the requestid, please diagnose"). A RequestId alone cannot locate the
root cause from the client side; the diagnosis stays open until the full
error response body (Code, Message, RequestId, EC, RecommendDoc) is
recovered. The client type decides where to look for it:

| Client type | How to recover the error body |
| --- | --- |
| Java SDK | Enable OSS SDK logging (com.aliyun.oss logger config), or catch OSSException/ClientException in code and print the full response body with the error Code |
| Python SDK (oss2) | Wrap the call in try/except and print the oss2 exception details; oss2 exceptions carry status, request_id and the error code |
| ossutil | Re-run the failing command with a higher log level and read the error block (error code, request id, EC fields) |
| Browser/JS | Devtools Network panel: click the failing OSS request and read the response body (Code/Message/EC); CORS-blocked bodies must be read from the console response preview |
| Other tools/proxies | Capture the raw HTTP response body via the tool's own error dump or a capture layer |

Once the recovered body carries the Code or numeric EC field, re-run the
entry script with it. Keep the RequestId for support-ticket escalation:
server-side log lookup by RequestId is a support-only capability and stays
out of this zero-cloud-API skill. The entry script attaches this guidance
automatically as the `request_id_guidance` block whenever only a
`--request-id` is available.
