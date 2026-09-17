# Diagnosis Tree: Routing Browser Direct-Upload / CORS Errors

Read-only routing guide. For every branch, first run
`scripts/oss_cors_diagnosis.py --bucket <name> [--origin <origin>]` and
ground the conclusion in its report; never conclude from the error text
alone.

## Root: what does the user report?

### Branch A — Browser console: "No 'Access-Control-Allow-Origin'" / CORS blocked

1. Run the diagnosis script with the page's Origin (`--origin`).
2. Report says `CORS not configured` (NoSuchCORSConfiguration) → root
   cause confirmed: the bucket has no CORS rule. Output the standard
   template from [cors-rules.md](cors-rules.md) section 3 as manual
   guidance; never apply it.
3. Report says no rule matches the Origin → check, in order:
   - Scheme present and correct (`https://` vs `http://`)?
   - Subdomain coverage (`*.example.com` ≠ `example.com`)?
   - Port included when the page runs on a non-standard port?
   - Multiple environments (dev/test/prod) each need their own origin.
4. Report says a rule MATCHES but the browser still blocks → preflight
   cache or intermediary: clear browser cache / test private mode; check
   for a CDN/proxy stripping or duplicating CORS headers (duplicate
   `Access-Control-Allow-Origin` headers also fail the browser check);
   enable Return Vary: Origin behind caches.

### Branch B — Preflight OPTIONS fails / upload 403 only from browser

1. Browser direct-upload 403 has TWO independent layers; attribute both:
   - **CORS layer** (browser blocks before/after sending): no matching
     rule → no CORS headers → the browser shows a CORS error even if OSS
     would have allowed the request. Covered by Branch A.
   - **Auth layer** (OSS rejects): the request lacks a valid signature.
     Private buckets require signed requests: PostObject policy +
     Signature form fields, or STS temporary credentials
     (+ `x-oss-security-token`). CORS alone never grants access.
2. Mini programs: many platforms do not enforce browser CORS but still
   require valid signing; if a mini program upload fails with 403 while
   a web page shows CORS errors, fix the signing first (Branch D) and
   the CORS rule second.
3. If the 403 body carries an OSS error code unrelated to CORS/signing
   (server-side SDK transfer errors, throttle codes, etc.), this is
   outside scope — defer to
   alibabacloud-oss-transfer-error-code-diagnosis.
4. OSS error-code attribution for preflight failures (see
   [cors-rules.md](cors-rules.md) section 5.3):
   - `0003-00000601` — OPTIONS rejected because the bucket has no CORS
     config; attribute to missing rule, output the standard template.
   - `0003-00000602` — rules exist but the request method/origin is not
     allowed; re-run the script with the exact `--origin` and report the
     mismatched field.
   - `0034-00000101` / `0034-00000102` — OPTIONS missing the `Origin` or
     `Access-Control-Request-Method` header (400): attribute to the
     CLIENT/proxy crafting the preflight, not to bucket rules.

### Branch C — "CORS config not working" (rules exist, failure persists)

1. Run the script; if `matched_rule_index` is not null:
   - Stale preflight cache (MaxAgeSeconds) → clear cache / private mode;
     this is the most common cause (corroborated by ticket patterns:
     works after clearing cache).
   - CDN/proxy in front of OSS → configure CORS headers on the CDN side
     too; enable Return Vary: Origin.
2. If expose-headers gap is reported (ETag / x-oss-request-id missing):
   the upload may actually SUCCEED while JS reports failure because it
   cannot read ETag — advise adding them to Expose Headers per the
   template (manual operation).
3. Never conclude "OSS bug" without evidence; list what was checked.

### Branch D — PostObject form direct-upload errors

1. `AccessDenied / policy expired` (EC 0006-00000213):
   - Policy `expiration` is **UTC**. Do NOT attribute to "filled Beijing
     time" — Beijing-time values parse as 8h LATER, they do not expire
     early. Real causes: (a) validity window too short (client holds the
     policy or network delay); (b) client reuses a stale cached policy
     past expiry; (c) the policy-issuing server clock skewed backward.
   - Official format (help.aliyun.com EC 0006-00000213): `expiration` is
     an ISO8601 **GMT** timestamp with a trailing `Z`, e.g.
     `2023-02-19T13:19:00.000Z`; if the server receives the request later
     than that instant, the policy is expired. Official fix: make sure the
     `expiration` value is well-formed AND send the PostObject request
     before it expires
     (https://help.aliyun.com/zh/oss/user-guide/0006-00000213).
   - Offline check: pass the customer's value via
     `--policy-expiration <ISO8601-Z>` to `oss_cors_diagnosis.py`; the
     report's `policy_expiration_check` classifies it as `valid` /
     `expired` / `invalid_format` against the current UTC time and
     restates this anti-pattern in `recommendations` and `NEXT_ACTION`
     (never writes anything).
2. `InvalidAccessKeyId / SignatureDoesNotMatch` on PostObject:
   - policy Base64 and Signature computed from the SAME policy string?
   - signing with STS credentials but `x-oss-security-token` form field
     missing?
   - form fields submitted but not covered by policy `conditions`?
3. Form structure errors:
   - the file field MUST be named `file` and be the LAST field;
   - POST multipart/form-data to the bucket root (`https://<bucket>.<endpoint>`),
     not PUT to an object URL;
   - custom callback variables: each is its OWN form field with the `x:`
     prefix (NOT the `x-oss-callback-var` header used by PutObject /
     CompleteMultipartUpload). Empty callback values trace back to empty
     or missing `x:` fields — capture the request body to verify.
4. Policy spec details: see the PostObject doc
   (https://help.aliyun.com/zh/oss/developer-reference/postobject) and
   the client direct-upload guide
   (https://help.aliyun.com/zh/oss/user-guide/uploading-objects-to-oss-directly-from-clients/).

### Branch E — NoSuchBucket / degraded report

1. Bucket names are global and lowercase; verify spelling and the owning
   account (the report's ListBuckets fallback checks the caller's own
   account).
2. Report `STATUS: DEGRADED` → relay the recorded errors and
   `NEXT_ACTION` honestly; the standard templates in the report remain
   valid for manual application once access is restored. Never invent
   CORS rules for a bucket that could not be read.
