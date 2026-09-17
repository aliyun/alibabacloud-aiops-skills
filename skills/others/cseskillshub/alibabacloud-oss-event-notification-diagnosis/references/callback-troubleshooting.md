# Upload Callback (CallbackFailed) Troubleshooting

Reference for OSS upload-callback failure attribution. Mechanism facts in
the "Mechanism facts" table below are verified against the official
documentation:

- https://help.aliyun.com/zh/oss/upload-callbacks-6 (upload callback errors and exclusion)
- https://help.aliyun.com/zh/oss/developer-reference/callback (callback mechanism)

Items marked `[measured / SDK-sourced]` or `[ticket-sourced]` are NOT from
official documentation but from live testing, oss2 SDK behaviour, or
support-ticket analysis.

## Mechanism facts (official, verified)

| Fact | Value |
|------|-------|
| Supported APIs | PutObject, PostObject, CompleteMultipartUpload |
| Callback delivery | OSS POSTs to the `callbackUrl` after storing the object |
| Response time limit | **5 seconds, fixed, not configurable**; OSS disconnects after 5 s and reports timeout |
| Success contract | callback server must return HTTP **200** with a **JSON** body (`Content-Type: application/json`). **Dual-position note**: the newer developer-reference/callback.md:297 additionally accepts an XML response body when `Content-Type: application/xml` is set explicitly; three other official docs state JSON is mandatory. Default to JSON; if the customer's server can only emit XML, have it set that Content-Type header explicitly. |
| Failure contract | any non-200 response OR non-JSON body is treated as callback failure |
| Result semantics | upload succeeds + callback fails -> HTTP **203** with `ErrorCode: CallbackFailed`; the object IS stored |
| Callback parameters | `callbackUrl` (required), `callbackBody` (required), `callbackHost` / `callbackBodyType` (optional), carried via `x-oss-callback` header or `callback` query/form field as Base64(JSON) |
| HTTPS/SNI | OSS does NOT send SNI by default; servers relying on SNI need `callbackSNI=true`, otherwise the TLS handshake fails (surfaces as 502) |
| Source IPs | OSS callback source IPs are NOT fixed - IP allowlists cannot solve connectivity; verify the callback signature instead [ticket-sourced: no official doc states source IPs are fixed or variable; the signature-verification advice IS official: callback.md:286-289] |
| Custom variables | declared via `x-oss-callback-var`, keys must start with `x:` **and use only lowercase letters** (official constraint); <=10 variables and <=512 bytes total recommended [the numeric limits are ticket-sourced heuristic, not official] |
| Bucket-level policy | an optional bucket-level callback policy (GetBucketCallbackPolicy) can supply callback parameters; request-level parameters override it [override priority is oss2-SDK-behaviour-sourced, not officially documented]; 404 BucketCallbackPolicyNotExist simply means no policy is configured [live-measured] |
| Callback region availability | Callback is available in **22 regions only** (official: developer-reference/callback.md usage-limits / region-restriction): cn-hangzhou, cn-shanghai, cn-qingdao, cn-beijing, cn-zhangjiakou, cn-huhehaote, cn-wulanchabu, cn-shenzhen, cn-heyuan, cn-guangzhou, cn-chengdu, cn-hongkong, us-west-1 (Silicon Valley), us-east-1 (Virginia), ap-northeast-1 (Tokyo), ap-southeast-1 (Singapore), ap-southeast-3 (Kuala Lumpur), ap-southeast-5 (Jakarta), ap-southeast-6 (Manila), eu-central-1 (Frankfurt), eu-west-1 (London), me-east-1 (Dubai). Callback failure in an unsupported region would be misattributed to the server without this check. |
| callbackUrl IPv6 restriction | `callbackUrl` **does NOT support IPv6 addresses or domains resolving to IPv6** (official: callback.md callbackUrl row) - this is a real 502/connectivity root cause |
| No automatic retry | **Callback failure is NOT retried automatically** by OSS; each upload attempt triggers at most one callback delivery |
| London SNI exception | The **UK (London) region always sends SNI regardless of the callbackSNI parameter** (official: callback.md callbackSNI note box) |
| Debug endpoint | OSS provides a public demo callback server `http://oss-demo.aliyuncs.com:23450` for client-side debugging (signature verification only) |

## Attribution tree (what the error message tells you)

| Observed error | Root cause class | Direction |
|----------------|------------------|-----------|
| `InvalidArgument: The callback configuration is not json format.` | malformed callback parameter | client side: rebuild Base64(CallbackJson) with properly escaped quotes; custom variables need the `x:` prefix |
| `CallbackFailed: Response body is not valid json format.` | non-JSON response body | callback server: return JSON only; strip UTF-8 BOM (ef bb bf); avoid leaking stack traces on exceptions |
| `CallbackFailed: Error status : -1 ... reply timeout, cost:5000ms` or `can not connect to your callbackUrl` | 5-second timeout or unreachable server | callback server: answer within 5 s (move heavy work async); verify DNS/port reachability from the public network |
| `CallbackFailed: Error status : 502.` | web service not listening / wrong callbackUrl / TLS-SNI handshake failure / broken network path | callback server: confirm the process listens on the callbackUrl port; set `callbackSNI=true` for HTTPS; test with `curl -v`; prefer same-region ECS hosting |
| `CallbackFailed: Too many callback requests` | OSS is processing too many concurrent callback requests - server-side throttling | **NOT a customer-server problem**; advise retry later; if sustained, reduce upload burst rate or contact support |
| `CallbackFailed: Get image info failed` | OSS could not retrieve image info (the object may have failed upload or been deleted before the callback fired) | verify the object exists and was uploaded successfully; this is NOT a callback-server error |
| `CallbackFailed: Error Status : 400.User server return too long content-length value` | callback server response did not carry Content-Length AND the body exceeded 1 MB | callback server MUST include a `Content-Length` header and keep the response body <= 1 MB |
| `CallbackFailed: Error status : 400/404/403...` | callback server returned a non-200 status | callback server: fix the handling logic and return exactly 200 + JSON on success |

## Common pitfalls from real support tickets

- **HTTPS + SNI**: a very frequent 502 root cause - the customer changed
  certificate hosting (e.g. moved to a shared/virtual-hosted certificate)
  and OSS stopped reaching the server because no SNI was sent. Fix:
  `callbackSNI=true` or switch to HTTP while debugging.
- **Intermittent timeout only in far regions**: cross-region network delay
  pushes an already-slow handler past the 5-second limit; async handling
  fixes it.
- **URL assembly bug**: an environment variable with a trailing slash
  producing `https://host//path` makes the callback server answer 400.
- **Slow uploads with callback enabled**: total upload latency includes
  the callback round-trip; a slow callback server makes uploads feel slow
  even when OSS itself responds fast.

## Verification steps (user side, read-only for this skill)

1. Reproduce the upload and capture the exact OSS error response
   (ErrorCode / Message / RequestId).
2. `curl -v -d "object=test" <callbackUrl>` from a public network to
   prove the server answers 200 + JSON within 5 s.
3. For HTTPS, confirm the certificate chain and whether the server needs
   SNI; retry with `callbackSNI=true`.
4. Check the callback server logs for received requests and returned
   status codes.

## Official parameter limits and 0007 error-code family

Verified against the dedicated error-code articles
(`https://help.aliyun.com/zh/oss/user-guide/0007-<code>`):

| Limit / rule | Value | Error code |
|---|---|---|
| `x-oss-callback` total length | <= 5 KB after Base64 | 0007-00000001 |
| Encoding | the parameter MUST be Base64(JSON) | 0007-00000002 |
| Decoded content | must be valid JSON; escape quotes inside callbackBody | 0007-00000003 |
| `callbackUrl` validity | well-formed URL; positive integer port; URL-encode Chinese characters; HTTPS supported | 0007-00000004 |
| `callbackUrl` count | at most **5 URLs**, semicolon-separated; OSS tries them in order until the first succeeds | 0007-00000005 |
| `callbackUrl` resolution | must resolve to a **public** IP | 0007-00000007 |
| Internal targets | internal IPs (e.g. 127.0.0.1) are rejected | 0007-00000008 |
| `callbackHost` | valid domain/IP string; auto-derived from callbackUrl when absent | 0007-00000009 |
| `callbackBody` | must be a non-empty STRING (arrays rejected), e.g. `bucket=${bucket}&object=${object}` | 0007-00000010/011 |
| `callbackBodyType` | exactly `application/x-www-form-urlencoded` or `application/json` | 0007-00000012/013 |
| `callbackSNI` | boolean only (`true`/`false`) | 0007-00000014 |
| `callbackStage` | string naming a valid callback-timing identifier | 0007-00000015/016 |
| `callbackFailureAction` | string; feature in invitation-only beta | 0007-00000017 |

Attribution note: 0007-00000001..017 are all REJECTED REQUESTS (4xx
before upload) caused by malformed callback parameters - attribute them
to the CLIENT request construction, not to the callback server. This is
the counterpart of CallbackFailed (203), where the upload succeeded but
the server-side callback delivery failed.
