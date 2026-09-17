# Diagnosis Tree: Routing OSS Endpoint / Access Errors

Read-only routing guide. For every branch, first run
`scripts/oss_endpoint_diagnosis.py --bucket <name> [--endpoint <endpoint>]`
and ground the conclusion in its report; never conclude from the error text
alone.

## Root: what does the user report?

### Branch A - DNS failure: "no such host" / resolution failure

1. Is the endpoint an internal endpoint (`oss-<region>-internal.aliyuncs.com`)?
   - Yes AND the client runs outside the Alibaba Cloud network (office,
     home, other clouds) -> EXPECTED behavior: internal endpoints only
     resolve inside the Alibaba Cloud network of that region. Advise the
     public endpoint `oss-<region>.aliyuncs.com`.
   - Yes AND the client runs on same-region ECS -> check the ECS's DNS
     configuration (custom resolv.conf, DNS proxy); the internal endpoint
     should resolve there. Report as a local DNS issue, not an OSS fault.
2. Is the endpoint malformed (typo, wrong TLD, region misspelled)?
   - Yes -> the diagnosis script classifies it `invalid`; give the correct
     endpoint form rebuilt from the bucket location.
   - NOT malformed but not an `*.aliyuncs.com` host either (a well-formed
     custom domain such as `img.example.com`) -> the script classifies it
     `cname`, not `invalid`; go to Branch H. A raw IP stays `invalid`
     (Branch G / endpoint-rules.md sec.3.2).

### Branch B - "must use specified endpoint" / wrong-region AccessDenied

1. Run the diagnosis script with the user's endpoint. The error body of
   this failure carries an `<EC>` of 0003-00001403 and an `<Endpoint>`
   element naming the correct endpoint - quote it as evidence.
2. `verdict.region_match == mismatch` -> root cause confirmed: endpoint
   region differs from the bucket location. Advise rebuilding the endpoint
   from the bucket location (public or internal per the client's network
   position, see endpoint-rules.md section 3).
3. Report is `DEGRADED` with an AccessDenied error -> distinguish by EC code
   (D-10, measured 2026-09-07):
   - EC 0003-00001403 ("must be addressed using the specified endpoint"):
     wrong-region endpoint; the `<Endpoint>` field names the correct one.
   - EC 0003-00000001 ("The bucket you access does not belong to you"):
     the bucket exists but belongs to another account - verify bucket
     ownership and the caller's UID.
   - Other AccessDenied (no EC or EC 0003-00000201): missing RAM permission;
     check oss:GetBucketInfo / oss:ListObjects grants.
   List the candidates and the evidence needed; do not pick one without data.

### Branch C - 403 AccessDenied without endpoint wording

1. Script report `category=permission`:
   - Caller lacks `oss:GetBucketInfo` -> point to ram-policies.md.
   - Bucket belongs to another account -> verify the UID that owns the
     bucket vs the caller UID in the report's `identity` block.
   - Bucket policy / RAM deny restricting source IP (VPC or public IP
     whitelist) -> the request source IP may fall outside the whitelist;
     this is policy attribution, give manual guidance only. Authoring the
     fine-grained policy itself (e.g. `acs:SourceIp` / VPC conditions per
     the OSS Bucket Policy doc, help.aliyun.com/document_detail/213018.html)
     is a configuration change and stays manual guidance.
2. Never mutate any policy; this skill only explains the cause.

### Branch D - NoSuchBucket (404)

1. Bucket names are lowercase and unique within OSS. Official PutBucket
   naming spec: 3-63 characters of lowercase letters, digits and hyphens,
   starting and ending with a lowercase letter or digit. (The naming spec
   does NOT itself state "globally unique" - global uniqueness is product
   common knowledge, not official doc text, so treat "unique within OSS" as the working
   assumption - B-9.) Verify spelling, case, and the
   account that created it (the report's ListBuckets fallback checks the
   caller's own account).
2. If the bucket was released, the name may no longer resolve - state that
   the bucket does not exist in the caller's account per the report; never
   invent a region for a non-existent bucket.

### Branch E - Network timeout / connection reset against a valid endpoint

1. Classify the endpoint first: an internal endpoint from outside the
   Alibaba Cloud network times out / fails to connect - expected. The
   script reports this as `category=network` (DNS "no such host" and
   connect timeouts are both transport failures: HTTP status -2 with an
   empty code, normalized to the network category).
2. Public endpoint timing out from the Internet -> local network / firewall;
   give guidance only. Transfer acceleration endpoint instability ->
   acceleration is for cross-region optimization; same-region clients
   should use the internal endpoint instead.
3. Cross-region question (e.g. "can my ECS in region A use the internal
   endpoint of a bucket in region B?"): internal endpoints only resolve
   inside the Alibaba Cloud network of THEIR region - cross-region clients
   must use the public endpoint (or CEN/Express Connect for private
   cross-region connectivity).

### Branch F - "Why am I paying public network traffic cost?"

1. Identify which clients read the bucket and through which endpoint.
2. Same-region clients on the public endpoint -> root cause: endpoint
   choice; advise the internal endpoint (endpoint-rules.md section 3/4).
3. Third-party CDN back-to-origin -> billed as standard public egress
   unless Alibaba Cloud CDN with the origin type set to the OSS domain is
   used (endpoint-rules.md section 4).
4. Public-read ACL plus leaked object URLs -> unsigned downloads by
   strangers; attribute with the real-time log / Top IP statistics, advise
   a private ACL and Bucket Policy IP restrictions as manual guidance.
5. Legitimate internet egress -> explain the charging rule (internal /
   ingress traffic is free; only public egress is billed; a storage pack
   does NOT cover traffic); defer deduction / resource-pack questions to
   alibabacloud-oss-billing-diagnosis.

### Branch G - "A file is reachable through a raw OSS IP" (security self-check)

1. The user's "endpoint" here is a raw IP address - the script classifies
   it `invalid`; OSS public endpoint IPs are shared by many accounts'
   buckets, so a raw-IP path does not necessarily belong to the caller
   (endpoint-rules.md section 3.2).
2. Verify ownership with GetBucketInfo on the caller's actual bucket
   domain; if the exposed object belongs to another account, state that
   the caller cannot control it - always access OSS via the bucket domain.
3. If the object belongs to the caller's bucket -> advise private ACL /
   authenticated URLs as manual guidance; never mutate anything.

### Branch H - Custom domain (CNAME) won't open / stuck pending / no such host

Run the script with the custom domain as `--endpoint`; it classifies the value
`cname`, probes DNS and calls read-only `ListCname`, then reports
`cname_diagnosis.verdict`. Ground every conclusion in that verdict and the
sec.3.3 path in endpoint-rules.md - never invent the binding state.

1. `CUSTOM_DOMAIN_CNAME_NOT_RESOLVED` -> the domain does not resolve; this IS
   the customer-side `UnknownHostException` / "no such host". Fix the CNAME
   record at the DNS provider so it points at the bucket's public endpoint
   (`<bucket>.oss-<region>.aliyuncs.com`).
2. `CUSTOM_DOMAIN_CNAME_NOT_BOUND` -> resolves but `ListCname` shows no match:
   bind it in the OSS console (Transmission Management > Domain Names); for
   mainland-China buckets ICP filing is a precondition.
3. `CUSTOM_DOMAIN_CNAME_DISABLED` -> bound but `ListCname` Status is `Disabled`
   (the official enum is only Enabled/Disabled); re-enable it.
4. `CUSTOM_DOMAIN_CNAME_PENDING` -> a non-Enabled status. IMPORTANT: the
   console's "pending verification" state is a CnameToken ownership-verification state, NOT an API
   `Status` value, and such a domain may not surface in `ListCname` until
   verified; complete ownership verification + ICP filing and wait for it to
   clear. Never report a pending domain as healthy.
5. `CUSTOM_DOMAIN_CNAME_MISRESOLVED` -> bound (Enabled) but the resolution
   chain misses the bucket endpoint (often points at a CDN). Re-point the
   CNAME, or use the dedicated CNAME domain (sec.3.3 step 6). If a CDN is
   intentional -> alibabacloud-oss-cdn-origin-config-diagnosis.
6. `CUSTOM_DOMAIN_CNAME_OK` -> binding healthy. If access still fails: check
   the HTTPS certificate (`ListCname` reports certificate presence/status -
   HTTPS fails while HTTP works when no cert is bound, sec.3.3 step 3), the SDK
   CNAME mode (`is_cname=True`, step 5), and Bucket Policy/ACL. Downstream
   fan-out: a webpage that won't open -> alibabacloud-oss-static-website-diagnosis;
   object preview / hotlink protection -> alibabacloud-oss-direct-access-link-diagnosis.
7. `CUSTOM_DOMAIN_CNAME_UNKNOWN` -> DNS probe and/or `ListCname` degraded (e.g.
   missing `oss:ListCname`, or cluster custom-domain feature off per OSS error
   0018-00000002); relay the `[WARN]` and walk sec.3.3 manually.

### Branch I - "Unreachable / slow only from a certain region or ISP" (dial-test)

1. First rule out an endpoint-string problem (Branches A/B) - a wrong
   endpoint is not a network-path problem.
2. If the endpoint is correct but one region/ISP fails (especially 6xx) or is
   slow, this is a reachability question: guide the customer to run a
   **self-service** dial-test (CloudMonitor site monitoring, or `ossutil probe`
   on the affected client) and interpret the result with the dial-test guidance
   module (M4 in the skill's Module Index). This skill NEVER
   runs a dial-test itself.
3. 6xx from one ISP's nodes while others are fine -> ISP hijack/blocking: advise
   transfer acceleration or a different ISP. All nodes fine -> client-side
   (local DNS/firewall). All ISPs in one region abnormal -> escalate to the
   network team.

## Degraded-report discipline

Whenever the script exits with `STATUS: DEGRADED`, the final answer must:
- quote the recorded error `category` / `code` and the `NEXT_ACTION` line;
- state what could NOT be verified (e.g. bucket region unverifiable without
  `oss:GetBucketInfo` permission);
- never fill the gap with guesses.
