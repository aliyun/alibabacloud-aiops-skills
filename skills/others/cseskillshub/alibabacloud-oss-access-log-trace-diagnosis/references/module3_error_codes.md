# Module 3: Error Codes and the Honesty Contract

How this skill turns an OSS failure into a conclusion, and — equally important —
how it decides when a conclusion is **not** available.

---

## 1. Where the EC code comes from

Every OSS error response body carries an extended error code next to the classic
error code:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>AccessDenied</Code>
  <Message>Access denied by bucket policy.</Message>
  <RequestId>65A1B2C3D4E5F6G7H8I9J0K1</RequestId>
  <HostId>example-bucket.oss-cn-hangzhou.aliyuncs.com</HostId>
  <EC>0003-00000101</EC>
  <RecommendDoc>https://help.aliyun.com/zh/oss/user-guide/0003-00000101</RecommendDoc>
</Error>
```

Two independent sources feed the diagnosis, and either is sufficient to start:

| Source | Field | How to obtain |
|---|---|---|
| The error response the client received | `EC`, `Code`, `RequestId` | Client SDK exception, or the raw XML above |
| The realtime access log | `ec`, `error_code`, `request_id` | `trace_request.py`, filtered by request ID or by EC |

### Documentation links are verified, never recalled

Each EC code has its own public documentation page, and an error response may
carry a `RecommendDoc` URL directly. This skill handles links in two ways and
neither one relies on memory:

1. The knowledge base carries a link for the codes where one was confirmed; the
   report prints it only when present.
2. For anything else, pass the customer's own wording with `--question`. The
   script verifies it against the official help-center document index at
   runtime and returns up to three candidate documents. **Cite only URLs that
   the lookup returned.** When its note starts with `DEGRADED`, state that
   online official docs could not be verified.

Never fabricate a documentation URL, and never write one down from recall: a
plausible-looking link that 404s is worse than no link.

---

## 2. Verdict classes — what the report is allowed to claim

This is the core discipline of the skill. Every conclusion carries one of three
classes, and the class limits the wording.

| Class | Meaning | Permitted output |
|---|---|---|
| **A** | Provable from the customer's own log plus the customer's own configuration | A single conclusion, with the matching evidence quoted verbatim |
| **B** | Evidence narrows the cause to a few candidates, but confirmation needs something the customer must supply or run | Ranked candidates, each with its own verification step, plus a plain statement of what could not be checked |
| **C** | The decisive evidence is server-side only and is not exposed through any customer-facing API | Escalation: a support-ticket package, plus an explicit statement of what could not be verified |

**Why B and C exist.** The server-side log that carries the string-to-sign, the
canonical request and the precise denial message is not reachable through any
customer-facing API. A signature mismatch therefore cannot be pinpointed from
the customer side. Producing a confident cause anyway would be fabrication, so
the script downgrades the verdict and says what is missing.

**Hard rule:** never upgrade a B or C verdict to A wording because the customer
sounds certain, or because a cause looks plausible. Plausible is not proven.

---

## 3. Error-code table

| EC | Error code | Status | Meaning | Class |
|---|---|---|---|---|
| `0003-00000101` | AccessDenied | 403 | Denied by a bucket policy statement | **A** |
| `0003-00000905` | AccessDenied | 403 | Anonymous request denied | **A** |
| `0003-00000005` | AccessDenied | 403 | No read permission on this object | **A → C** |
| `0003-00000201` | AccessDenied | 403 | Denied by a RAM identity policy | **B** |
| `0003-00000001` | AccessDenied | 403 | Denied by a platform-level security policy | **C** |
| `0003-00000801` | AccessDenied | 403 | Account disabled | **C** |
| `0024-00000008` | AccessDenied | 403 | Feature gated for this access path | **C** |
| `0030-00000006` | NoSuchBucketPolicy | 404 | The bucket has no policy — **not a failure** | **A** |
| `0015-00000101` | NoSuchBucket | 404 | The bucket does not exist | **A** |
| `0015-00000001` | InvalidBucketName | 400 | The bucket name breaks the naming rules | **A** |
| `0026-00000001` | NoSuchKey | 404 | The object does not exist | **A** |
| `0026-00000002` | FileAlreadyExists | 409 | The request asked not to overwrite | **A** |
| `0026-00000004` | StaleFile | 409 | Optimistic-locking conflict on metadata | **B** |
| `0048-00000105` | — | 200 | Forced download instead of inline preview | **A** |
| `0040-00000005` | BadRequest | 400 | Image processing rejected the source format | **B** |
| `0006-00000213` | InvalidPolicyDocument | 403 | Form-upload policy expired | **A** |
| `0002-00000201` | SignatureDoesNotMatch | 403 | Header signature mismatch | **B** |
| `0002-00000040` | SignatureDoesNotMatch | 403 | Presigned-URL signature mismatch | **B** |
| `0002-00000504` | RequestTimeTooSkewed | 403 | Clock skew beyond 15 minutes | **B** |
| — | MirrorFailed | 424 | Mirror back-to-origin got a non-200 from the origin | **B** |
| — | InternalError / ServiceUnavailable | 5xx | Server-side failure | **C** |

---

## 4. Authorization family

### `0003-00000101` — denied by a bucket policy (class A)

The strongest case in this skill, because every input is customer-readable.

Evidence: the policy document, plus the logged `vpc_id`, `client_ip`,
`access_id`, `requester_id`, `extend_information`, `sign_type`, `operation` and
`object`. The engine walks each statement and reports, condition by condition,
whether it matched — see [module4_policy_analysis.md](module4_policy_analysis.md).

Required output shape:

```
Statement #2 (Effect: Deny) applies:
  Action covers the logged operation 'GetObject': yes
  Resource covers 'example-bucket/images/a.png': yes
  Principal: Principal ["*"] covers every caller, including anonymous
  Condition NotIpAddress acs:SourceIp: expected ['203.0.113.0/24'],
            actual '198.51.100.7' -> MET
  Condition StringNotLike acs:SourceVpc: expected ['vpc-*'], actual '-' -> MET
  Every required condition is satisfied, so the Deny takes effect.
```

Two facts that must be stated when relevant:

- A presigned URL does **not** bypass a bucket policy; the policy is evaluated
  before the signature is accepted.
- An explicit Deny outranks every Allow, so adding an Allow elsewhere does not
  fix it.

### `0003-00000905` — anonymous request denied (class A)

The decisive detail: **neither `public-read` nor `public-read-write` grants
anonymous listing.** A public ACL grants anonymous object reads (and writes, for
`public-read-write`); anonymous listing requires a bucket policy statement whose
principal is `*`. Also note that the logged operation name for listing is
`GetBucket`, not `ListObjects`.

Check block-public-access first: when it is on, it overrides both the bucket ACL
and the object ACL, so a public setting will not make anything reachable.

### `0003-00000005` — no read permission on this object (class A, else C)

Exactly two causes. Work them in order and never invent a third:

1. **The object carries its own private ACL** while the bucket is public.
   Verifiable: read the object ACL. Fixable by the customer: set the object ACL
   back to `default` so it inherits the bucket setting. This skill is read-only
   and hands the customer the command instead of running it.
2. **A platform-level block on the object.** Not verifiable through any
   customer-facing API → escalate.

Prohibited wording: "content-security interception", "firewall blocked it",
"security policy rejected it". Those are guesses dressed as findings, and this
error code does not support them.

### `0003-00000201` — denied by a RAM identity policy (class B)

An explicit Deny on the caller's RAM identity policy, or a resource-directory
control policy applied to the account. For object-level operations the log does
not record which of the two produced it.

What the skill can do: scan the caller's identity policies for a Deny statement
(`--ram-user <name>`). What it cannot do: read a resource-directory control
policy from the bucket side. State both.

Never suggest widening the bucket policy here — a Deny outranks it.

### `0003-00000001`, `0003-00000801`, `0024-00000008` — escalate (class C)

The policy content, the account status and the feature gating are not readable
through customer-facing APIs. Escalate with the ticket package. Specifically:
retrying, or re-issuing credentials, changes nothing for `0003-00000001`,
because that denial happens before credentials are evaluated — saying otherwise
sends the customer in circles.

---

## 5. Naming and existence family (all class A)

### `0015-00000001` — invalid bucket name

Decided locally from the host header, no API call needed. Strip the endpoint
suffix from the host and validate the remainder: lowercase letters, digits and
hyphens only, 3 to 63 characters, starting and ending with a letter or digit.

A dot or an underscore makes the name impossible, so the bucket can never exist
— typically a domain name was used where a bucket name was expected.

Keep this distinct from `0015-00000101`: there the name is valid but absent.

Evidence provenance matters: if the name came from the caller rather than from a
logged host header, the script reports it as a strong hint (class B), not as a
proven cause.

### `0015-00000101` — no such bucket

When a bucket does not exist the request fails during routing, which is why
`sign_type`, `access_id` and `owner_id` stay empty in the log. A very small
`response_time` is consistent with that.

A frequent real cause is a region mismatch in the endpoint: the name is correct
but the request went to the wrong region. Read the bucket information to settle
it. If that read fails, existence is undetermined — say so, do not assert that
the bucket is gone.

### `0026-00000001` — no such key

Trace the object's own history with `--object`. Keys are URL encoded in the log,
so matching uses `url_decode(object)`. Three outcomes: a logged removal
operation (report who and when, from `requester_id` / `client_ip` /
`sign_type`), no logged operation at all (never uploaded, removed before
logging was enabled, or outside the window), or a delete marker when versioning
is enabled.

### `0030-00000006` — no such bucket policy

**Not an authorization failure.** A 404 on a policy read simply means no policy
is configured. Reporting this as "permission denied" is the single most common
misdiagnosis in this family.

---

## 6. Request-semantics family

### `0026-00000002` — file already exists (class A)

A request-level control, not a bucket setting: the caller sent the
`x-oss-forbid-overwrite` header. In a versioning-enabled bucket that header has
no effect at all — every write creates a new version.

### `0026-00000004` — stale file (class B)

An optimistic-locking conflict on object metadata or tags. Read `sign_type` and
`sync_request` first: when they identify a service-side task (for example
last-access-time bookkeeping), the conflict is OSS's own, it is retried
automatically, and no customer action is needed. Otherwise scan the same window
for concurrent writes to the same key (`--concurrency`).

### `0048-00000105` — forced download (class A)

The status is **200**: the request succeeded. For buckets created after
2019-09-30 15:00, image access through the default OSS domain receives a
`Content-Disposition: attachment` header. Fixes: bind a custom domain, front the
bucket with a CDN, or append `response-content-disposition=inline`.

### `0040-00000005` — image processing rejected the source (class B)

Three steps, in order:

1. If the content type is not an image type, image processing does not apply —
   close the case. Supported types: `image/jpeg`, `image/png`, `image/webp`,
   `image/gif`, `image/bmp`, `image/tiff`, `image/avif`.
2. If it is an image type, inspect `object_size`. A value below 50 bytes cannot
   be a real image and strongly suggests a placeholder was uploaded instead of
   image bytes.
3. Download the object and check the magic bytes:

| Format | Leading bytes (hex) |
|---|---|
| PNG | `89 50 4E 47 0D 0A 1A 0A` |
| JPEG | `FF D8 FF` |
| GIF | `47 49 46 38` |
| WebP | `52 49 46 46 .. .. .. .. 57 45 42 50` |
| BMP | `42 4D` |

Step 3 needs object read permission, which this skill deliberately does not
request. Hand the customer the command:

```bash
curl -s -o /tmp/check.img "https://<bucket>.oss-<region>.aliyuncs.com/<key>"
ls -l /tmp/check.img
xxd /tmp/check.img | head -2
```

Interpretation: a single ASCII character or all zeros means the upload wrote a
placeholder; magic bytes that disagree with the content type mean a renamed or
mislabelled file; correct magic bytes with truncated content mean an interrupted
upload.

### `0006-00000213` — form-upload policy expired (class A)

A form upload carries the policy as a base64 JSON form field:

```
------boundary
Content-Disposition: form-data; name="policy"

eyJleHBpcmF0aW9uIjoiMjAyNi0wNi0xMVQxNDowMDowMC4wMDBaIiwiY29uZGl0aW9ucyI6W119
------boundary
```

Decoded, `expiration` is compared against the request time. **All OSS time
parameters are UTC.** A Beijing-time value written into `expiration` is parsed
as UTC and therefore expires eight hours *later*, not sooner — so a timezone
mix-up is *not* the cause. The real causes are a window that is too short, a
stale policy being reused, or a signing server whose clock drifts.

Pass the base64 value with `--post-policy` and the script decodes it and
compares.

### MirrorFailed (424) — mirror back-to-origin (class B)

The origin returned something other than 200, so the root cause sits at the
origin rather than in OSS. What this skill can and cannot do here:

- **Can**: confirm from the log that the failing request went through a mirror
  or website path, and report the logged status.
- **Cannot**: read the mirror rule itself. The SDK's website read returns only
  the static-website index and error documents — the back-to-origin rule and
  its origin address are **not exposed**. Claiming an origin address that was
  never read would be fabrication.

So the handover is: read the rule in the console under the bucket's
static-website settings, then request that origin URL directly and report the
status it returns. The conclusion "the origin is failing" is only established
once that direct request has been made.

---

## 7. Signature family (all class B — read this before wording anything)

**The decisive evidence is not available to the customer.** The string-to-sign
and the canonical request exist only in the server-side log. Any claim about
what the client computed is therefore an inference, not a finding.

What the access log *does* establish, and what to do with it:

| Logged field | What it tells you | Branch |
|---|---|---|
| `user_agent` | Official SDK versus hand-rolled signing | SDK: a wrong secret or a misconfigured client is far more likely than an encoding issue. Hand-rolled: ask the customer to print their own string-to-sign |
| `access_id` compared across requests from the same `client_ip` | Whether failing and succeeding requests used the same key | Mixed keys point at credential confusion |
| `host` | Whether a proxy, CDN or custom domain sits in front | An intermediary can rewrite headers that participate in signing |
| `sign_type`, and `OSSAccessKeyId` + `Expires` + `Signature` in `request_uri` | V1 header, V4 header, V1 presigned URL, V4 presigned URL | Decides which intermediate values to ask for |
| `response_time` | Whether the link itself was slow | Relevant to skew, not to a mismatch |

Four ranked candidates, in the order the script emits them:

1. **The AccessKey Secret does not match the AccessKey ID.** Most common. The
   service recognised the key ID (otherwise the error would be an invalid-key
   error) but the computed signature differed.
2. **An intermediary rewrote a signed header.** All `x-oss-*` headers, plus
   `Content-Type` and `Content-MD5`, participate in signing.
3. **Hand-rolled signing omitted a header, or the URL was re-encoded** between
   signing and sending.
4. **An SDK client configuration mismatch** — a path-style setting used against
   a virtual-hosted endpoint, a region that does not match the bucket, or a
   missing temporary security token.

What to ask the customer to print, per signature version:

| Version | Client-side values to collect |
|---|---|
| V1 header / V1 presigned URL | The string to sign: `METHOD\nContent-MD5\nContent-Type\nExpires-or-Date\nCanonicalizedOSSHeaders+CanonicalizedResource`, plus the `Content-Type` and `Content-MD5` actually sent |
| V4 header / V4 presigned URL | The canonical request: `METHOD\nCanonicalURI\nCanonicalQueryString\nCanonicalHeaders\nSignedHeaders\nHex(SHA256(payload))`, plus `x-oss-date`, `x-oss-content-sha256`, the `SignedHeaders` list and the region in the credential scope |

Compare layer by layer; the first differing layer is the cause.

Two traps to avoid in wording:

- Do **not** read URL encoding in the log as proof of an encoding bug. An SDK
  handles encoding itself and the log only shows how the request arrived.
- A wrong region in a V4 signature produces a malformed-authorization error,
  not a signature mismatch.

### `0002-00000504` — request time too skewed (class B)

The allowed skew is 15 minutes, for header signatures and temporary credentials
alike. Two candidates: the device clock runs slow (persistent failures), or the
request was signed and then held in a client or network queue (sporadic
failures, common on flaky mobile networks). A normal `response_time` rules out
link latency. A skew that is an exact multiple of one hour points at a timezone
bug instead of clock drift.

---

## 8. Prohibited conclusions

These are the ways this diagnosis goes wrong. Each one is a fabrication, not a
shortcut.

1. Asserting a cause for a class C code instead of escalating.
2. Upgrading a class B verdict because a cause "looks likely".
3. Inventing a third cause for `0003-00000005`.
4. Reporting `0030-00000006` as a permission failure.
5. Claiming the client built a wrong canonical request based on server-side
   values the customer cannot see.
6. Attributing a mismatch to URL encoding without a client-side comparison.
7. Guessing a bucket's purpose or an object's content from its name. Object
   keys are the customer's own naming and say nothing about the data; drawing
   security conclusions from a path is both wrong and a privacy breach.
8. Presenting a name or a configuration the caller supplied as if it had been
   read from the failing request.
9. Concluding "no problem" from an empty log query: an empty result usually
   means logging was off, the window was wrong, or the region was wrong.
