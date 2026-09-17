# CORS Rules: Semantics, Preflight, Expose-Headers, Standard Template

Reference for attributing browser/mini-program direct-upload failures to
OSS CORS configuration. Sources (verified):
- Configure CORS rules (console semantics, one `*` wildcard per origin):
  https://help.aliyun.com/zh/oss/user-guide/configure-cross-origin-resource-sharing
- OSS cross-origin FAQ ("No 'Access-Control-Allow-Origin'" handling):
  https://help.aliyun.com/zh/oss/faqs-about-security-and-compliance/
- PostObject (form upload spec, form fields, policy):
  https://help.aliyun.com/zh/oss/developer-reference/postobject
- Client direct upload architecture (server issues policy/signature,
  client posts the form):
  https://help.aliyun.com/zh/oss/user-guide/uploading-objects-to-oss-directly-from-clients/

## 1. Rule semantics (what each field means)

| Field | Meaning | Direct-upload pitfall |
|---|---|---|
| Allowed Origins | Which page origins may issue cross-origin requests. Scheme + host (+optional port); each entry may contain **at most one** `*` wildcard; multiple entries are line-separated | Missing the scheme (`https://app.com` vs `http://app.com` are different origins); `*.example.com` does NOT match the bare `example.com`; dev/test/prod origins all missing |
| Allowed Methods | HTTP methods allowed: GET / PUT / POST / DELETE / HEAD | Browser upload uses POST (PostObject) or PUT (signed PUT); omitting the actual method fails the preflight |
| Allowed Headers | Request headers the browser may send; `*` recommended | Custom headers (e.g. `x-oss-*`, `Cache-Control`) not covered -> preflight rejected |
| Expose Headers | Response headers JavaScript is allowed to read | Browsers hide all non-simple response headers from JS unless listed. `ETag` (upload confirmation / resumable upload) and `x-oss-request-id` (troubleshooting) must be listed. "Please set the etag of expose-headers" targets exactly this |
| Max Age (seconds) | How long the browser may cache the **preflight (OPTIONS)** result | After changing rules, browsers keep using the cached OPTIONS answer until it expires -- the top cause of "CORS config not working". Clear cache or test in private mode |
| Return Vary: Origin | Add `Vary: Origin` to responses | Enable when responses pass through CDN/proxy caches, so different Origins do not share one cached CORS response |

Rule matching: OSS evaluates rules in order; the request Origin must match
an Allowed Origin entry (case-insensitive, wildcard-aware) and the method
must be in Allowed Methods. If NO rule matches, OSS returns the response
without CORS headers and the **browser** blocks the request (the request
itself may still reach OSS).

## 2. Preflight (OPTIONS) mechanics

- Simple requests (plain GET/HEAD, some POSTs without custom headers) go
  straight through; anything else (PUT, POST with custom headers, signed
  uploads) triggers a preflight OPTIONS first.
- The preflight response (`Access-Control-Allow-Origin`,
  `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`) is
  cached by the browser for MaxAgeSeconds.
- Diagnosis order for "still blocked after configuring CORS":
  1. Does GetBucketCors show a rule matching the exact Origin (scheme
     included)? -- run `scripts/oss_cors_diagnosis.py --origin <origin>`
  2. Does the actual OPTIONS response carry the headers? (DevTools
     Network panel; check for duplicate CORS headers from CDN)
  3. Stale preflight cache? -> clear cache / private mode.
  4. CDN/proxy in front of OSS stripping or overriding CORS headers? ->
     configure CORS on the CDN side too and enable Return Vary: Origin.

## 3. Standard CORS template (text output only -- never applied by this skill)

For browser/mini-program direct upload, the standard rule (adjust the
origin; avoid bare `*` in production):

```
Allowed Origins   : https://your-app.example.com        (one per line; at most one * wildcard)
Allowed Methods   : GET, PUT, POST, HEAD
Allowed Headers   : *
Expose Headers    : ETag
                    x-oss-request-id
Max Age (Seconds) : 600
Return Vary: Origin: enabled (recommended when behind CDN)
```

Equivalent PutBucketCors XML body (for the USER to apply manually; this
skill MUST NOT execute it):

```xml
<CORSConfiguration>
  <CORSRule>
    <AllowedOrigin>https://your-app.example.com</AllowedOrigin>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedMethod>PUT</AllowedMethod>
    <AllowedMethod>POST</AllowedMethod>
    <AllowedMethod>HEAD</AllowedMethod>
    <AllowedHeader>*</AllowedHeader>
    <ExposeHeader>ETag</ExposeHeader>
    <ExposeHeader>x-oss-request-id</ExposeHeader>
    <MaxAgeSeconds>600</MaxAgeSeconds>
  </CORSRule>
</CORSConfiguration>
```

Apply paths (manual): OSS console -> Bucket -> Data Security -> CORS
(Cross-Origin Resource Sharing) -> Create Rule; or PutBucketCors API
(requires oss:PutBucketCors -- NOT granted to this read-only skill).

## 4. "CORS not configured" state

GetBucketCors on a bucket with no rule returns 404
`NoSuchCORSConfiguration`. This is a **configuration state**, not an API
error: report "the bucket has no CORS rule configured" and output the
standard template above. Any cross-origin browser request to such a
bucket is blocked by the browser's same-origin policy (no
`Access-Control-Allow-Origin` ever returned).

## 5. Official quotas, wildcard validity, error codes, form limits

Sources (verified):
- Quota / wildcard validity / Vary: Origin / CDN / best practices:
  https://help.aliyun.com/zh/oss/user-guide/configure-cross-origin-resource-sharing
- Error-code articles: 0003-00000601, 0003-00000602, 0034-00000006,
  0034-00000101, 0034-00000102 (same user-guide path pattern)
- Form upload limits: https://help.aliyun.com/zh/oss/user-guide/form-upload
- HTTP 400 summary (CORSRuleBeyondLimit / form-field 4KB / EntityTooLarge):
  https://help.aliyun.com/zh/oss/user-guide/http-400-error-code

### 5.1 Rule-count quota (conflicting official statements -- quote both)

- Current user guide: each Bucket supports **up to 20 CORS rules**.
- Error-code doc 0034-00000006 and the HTTP 400 summary
  (CORSRuleBeyondLimit): **10 rules** per Bucket.
- Report both numbers and note the discrepancy; advise users to keep
  <= 10 rules to stay safe under either statement (merge similar
  origins into one rule with multiple AllowedOrigin lines).

### 5.2 AllowedOrigin wildcard validity

- Format `scheme://host[:port]`; **at most one `*`** per origin line.
- VALID: `https://*.example.com`, `http://localhost:*`.
- INVALID: `https://*` (bare wildcard host), `https://*.example.*`
  (two wildcards). PutBucketCors rejects these (0034-00000009).
- AllowedHeader supports `*`; **ExposeHeader does NOT support `*`**
  (no wildcard at all; 0034-00000013) -- list each header explicitly.

### 5.3 Error-code attribution map

| Code | Meaning | Attribution |
|---|---|---|
| 0003-00000601 | OPTIONS rejected: bucket has NO CORS config | Missing rule -> template output (section 3) |
| 0003-00000602 | OPTIONS rejected: rule exists but method/origin not allowed | Rule mismatch -> run script with `--origin` |
| 0034-00000101 | OPTIONS missing `Origin` header (400) | Client/proxy side: the request did not carry Origin; NOT a bucket-config problem |
| 0034-00000102 | OPTIONS missing `Access-Control-Request-Method` (400) | Client/proxy side, same as above |
| 0034-00000006 | PutBucketCors: too many CORSRule nodes | Quota (section 5.1); user-side manual fix |

0034-00000101/102 typically indicate a hand-crafted request or an
intermediary stripping preflight headers -- route to the requester, do
not change bucket rules for them.

### 5.4 Temporary permissive rule for isolation (manual operation only)

Official FAQ troubleshooting step: create ONE temporary rule -- Origin
`*`, all methods, AllowedHeader `*`, ExposeHeader `ETag` and
`x-oss-request-id`, MaxAgeSeconds `0`, Return Vary: Origin enabled.
If the failure disappears, the original rules do not match; delete the
temporary rule afterwards. This skill only PRINTS this template.

### 5.5 CORS behind CDN acceleration

Two official integration modes when the bucket is CDN-accelerated:
1. Configure CORS rules on the CDN side (CDN returns the CORS headers);
2. CDN passes through the origin CORS headers (then OSS-side rules must
   be correct).
OSS-side CORS only takes effect for requests hitting the OSS origin
domain directly, or via CDN in pass-through mode. Duplicate headers
from both layers break the browser check.

### 5.6 PostObject form hard limits

- Object size via form upload: **<= 5 GB**; larger files need multipart
  upload (PostObject supports no multipart / resumable path).
- Every form field EXCEPT `file`: **<= 4 KB** (400 `FieldItemTooLong`).
  Official dual caliber: the HTTP-400 error-code doc says the other form
  fields must not exceed 4 KB, while the PostObject API doc's error table
  says the field key <= 8 KB and the field value <= 2 MB. Plan against the
  stricter 4 KB limit to be safe.
- Exactly ONE `file` form field per request (400
  `IncorrectNumberOfFilesInPOSTRequest` on multiple); it must be the LAST
  field (official wording, translated: "the `file` field must be the last form field"). Note: `InvalidArgument` in the PostObject
  context is a DIFFERENT error — it means the `OSSAccessKeyId` / `policy` /
  `Signature` fields were not all provided together (once any one of the
  three is present, the other two become mandatory).
- Guard against EntityTooLarge by adding a `content-length-range`
  condition to the Post Policy (server-side policy generation).

### 5.7 PostObject signature-version field names (error family 0002-000007xx)

| Version | AccessKey ID field | Signature field |
|---|---|---|
| V1 | `OSSAccessKeyId` | `Signature` |
| V2 / V4 | `x-oss-access-key-id` | `x-oss-signature` |
| S3-compatible V4 | `AWSAccessKeyId` | `x-amz-signature` |

- `policy` (Base64-encoded JSON) is mandatory (0002-00000702).
- V4 credential scope: `AKID/date/region/oss/aliyun_v4_request`, date
  format `%Y%m%d` (0002-00000708/709/710).
- Mismatch between signature field and declared version causes
  SignatureDoesNotMatch (0002-00000705): recompute HMAC from the exact
  Base64 policy string that was sent.

### 5.7.1 PostObject policy `expiration` — UTC anti-pattern (EC 0006-00000213)

OSS parses the PostObject policy `expiration` field as an **ISO8601 GMT/UTC**
instant with a trailing `Z` (official example `2023-02-19T13:19:00.000Z`);
if the server receives the request later than that instant the policy is
expired and OSS returns `AccessDenied` with EC `0006-00000213`
(https://help.aliyun.com/zh/oss/user-guide/0006-00000213).

**Anti-pattern (do NOT do this):** blaming the failure on "the customer
filled Beijing time into `expiration`". Beijing time is UTC+8, so a
Beijing-time value parses as an instant **8h LATER** — it does **not**
expire early and is **not** the root cause of EC 0006-00000213.

**Real root causes to investigate instead:**
1. The validity window is too short — the client holds the policy, or
   network delay means it arrives already expired;
2. The client caches and reuses a stale policy past expiry instead of
   re-issuing a fresh one per upload session;
3. The policy-issuing server's clock is skewed behind standard time.

**Official fix:** ensure the `expiration` value is well-formed AND send the
PostObject request before it expires. `oss_cors_diagnosis.py
--policy-expiration <value>` runs this check offline (no network, no write)
and classifies the value as `valid` / `expired` / `invalid_format`.

### 5.8 Security best practices (official)

- Do not use Origin `*` in production unless the bucket is fully
  public; list exact site domains.
- Restrict methods to what the business needs (read-only: GET, HEAD).
- Prefer explicit AllowedHeader lists over `*` for authenticated
  API-style calls; never use `*` there.
