# Multipart Upload Playbook

Diagnosis playbook for OSS large-file upload problems: stuck / interrupted /
failed multipart uploads, parameter sanity, and fragment (unfinished-part)
identification. Everything here is achievable from the **customer side**
(Request IDs, client logs, ossutil output, bucket metadata); this skill's
scripts cover the control-plane evidence automatically.

---

## 1. Official limits (verified against official documentation)

Source: https://help.aliyun.com/zh/oss/user-guide/multipart-upload (2026-08-27)

| Item | Limit |
|---|---|
| Single object size via multipart upload | <= 48.8 TB |
| Number of parts | 1 .. 10,000 |
| Single part size | 100 KB .. 5 GB (only the LAST part may be smaller than 100 KB) |

Source: https://help.aliyun.com/zh/oss/user-guide/simple-upload (2026-08-27)

| Item | Limit |
|---|---|
| Simple upload (PutObject) | <= 5 GB per request |

Rules of thumb derived from the limits (implemented as pure functions in
`scripts/multipart_upload_diagnosis.py`):

- File <= 5 GB: prefer simple upload (PutObject); multipart adds no benefit
  and can leave fragments.
- File > 5 GB: multipart required; size parts so the part count stays well
  below 10,000 (target ~1000 parts: part size ~= file size / 1000, clamped
  to [1 MB, 5 GB]).
- Concurrency: scale with bandwidth and device load; more workers than parts
  is pointless, and excessive concurrency causes client-side congestion.

## 2. Anatomy of a multipart upload (what to look for)

| Step | API | Meaning |
|---|---|---|
| Initiate | `InitiateMultipartUpload` | Returns the `uploadId`; no data transferred |
| Transfer | `UploadPart` | The actual data transfer; one request per part |
| Complete | `CompleteMultipartUpload` | Assembles parts into the final object; the object only becomes visible after this succeeds |
| Abort | `AbortMultipartUpload` | Cancels the event and deletes the uploaded parts |

Key semantics:

- **Parts alone are invisible.** The object list shows nothing until
  CompleteMultipartUpload succeeds. "The upload returned 200 but the file is
  missing" almost always means the complete step was never called (client
  code path ended early, exception swallowed, browser tab closed, etc.).
- **The complete request is tiny.** CompleteMultipartUpload only sends the
  part-listing XML (a few hundred bytes) — a slow complete request usually
  indicates a client-side problem building the part list, not OSS.
- **A vanished uploadId** (`NoSuchUpload`) means the event was already
  completed or aborted; re-initiate to start over.

## 3. Attribution decision tree: server-side vs client-side vs network

```
Upload stuck / slow / failed
│
├─ HTTP 4xx received? ────────────────► CLIENT-SIDE (permission/parameter)
│    · 403 AccessDenied → RAM permission / bucket policy / expired STS token
│    · 400 InvalidArgument / MalformedXML → part size / part number / body XML
│    · 400 InvalidPart / InvalidPartOrder on CompleteMultipartUpload → the
│      part list is invalid: a partNumber outside 1..10000, a non-ascending
│      part order, or an ETag that does not match the UploadPart response
│      ETag of that part (official InvalidPart troubleshooting doc); fix by
│      re-listing the actually uploaded parts (ListParts) and submitting
│      their exact ETags in ascending partNumber order
│    · FileAlreadyExists → request header x-oss-forbid-overwrite
│      (single-request semantics, see §6) → defer to
│      alibabacloud-oss-transfer-error-code-diagnosis
│
├─ HTTP 5xx received? ────────────────► SERVER-SIDE
│    · retry with exponential backoff; transient 5xx clears quickly;
│      persistent 5xx plus the Request IDs is ticket material
│
├─ No response at all (timeout / connection reset / "stuck at 0%")?
│    · No Request ID obtainable (client logs show no x-oss-request-id)
│      → CLIENT-SIDE or NETWORK: the request never reached OSS. Check local
│      DNS, proxies/firewalls, security groups, egress bandwidth, and
│      client-side read timeouts on the source file handle.
│    · Request IDs present but parts never complete → NETWORK transfer
│      dominates: compare total elapsed time with OSS processing time
│      (bucket access logs / monitoring); a large gap means bandwidth,
│      not OSS.
│
├─ Upload interrupted mid-way? ───────► CLIENT-SIDE or NETWORK
│    · OSS never aborts an upload on its own; interruption comes from a
│      client crash/timeout or a network reset
│    · the leftover parts become fragments (§5)
│
└─ Upload "finished" but capacity occupied / bucket looks empty?
     · FRAGMENT case → run the diagnosis entry script (ListMultipartUploads)
       and follow fragment-cleanup-guide.md
```

## 4. Client-side evidence collection (self-check checklist)

No internal log channel is needed; all of the following are observable from
the customer side:

1. **Request ID self-check.** Every OSS response (accepted or rejected)
   carries `x-oss-request-id`. Collect the Request IDs of the failing or
   stuck requests from the SDK exception object or from ossutil output
   (`Response: ... RequestId: 6AD2...`). A request that produced no Request
   ID at all never reached OSS — that alone attributes the stall to the
   client or the network.
2. **Client logs / SDK errors.** Java SDK `Unable to execute HTTP request:
   ... Read timed out` with RequestId `Unknown` means the request did not
   reach the server — point at local network, proxy, security groups, or
   endpoint selection, not at OSS. Repeated connection timeouts on one part
   suggest that part size is too big for an unstable link — reduce part
   size and enable retries/resume instead.
3. **ossutil output reading.** `ossutil cp localfile oss://bucket/key
   --part-size 10485760 --parallel 5 --loglevel info` prints per-request
   log lines (progress bar is shown by default; suppress with
   `--no-progress`, silence with global `-q`); a stalled transfer shows
   which part number is stuck in the loglevel output.
   **Checkpoint / resume behavior differs by ossutil version:**
   - ossutil **1.x**: files >= `--bigfile-threshold` (default 100 MB)
     automatically enable breakpoint resume and auto-create
     `.ossutil_checkpoint`; re-running the same command resumes.
   - ossutil **2.x** (current GA 2.4.0): breakpoint resume is **NOT**
     enabled unless you explicitly pass `--checkpoint-dir <dir>`;
     without it, a re-run starts from scratch and may create duplicate
     fragments. Always specify `--checkpoint-dir` for large files.
   Recommended 2.x combination for >100 MB files:
   `ossutil cp <file> oss://<bucket>/<key> -j 10 --parallel 10 --checkpoint-dir /path/to/ckpt`
   **ossutil 2.x `-j/--job` caveat** (official `cp.md:24`): default is 3
   (multi-file concurrency), but it only takes effect when combined with
   `-f`/`--update`/`--size-only`/`--ignore-existing`; without one of those
   flags `-j` is silently ignored. `--parallel` (single-file part
   concurrency) has no such precondition. `--bigfile-threshold` default is
   104857600 (100 MB) — files below it use simple upload, not multipart.
4. **Client environment checks.** Confirm there is no proxy/CDN/firewall in
   the path rewriting request headers (proxied `x-oss-*`, `content-type`,
   `content-md5` header changes break signatures), that the endpoint region
   matches the bucket, and that the machine's egress bandwidth actually
   supports the target throughput.
5. **Speed quantification (stuck/slow only).** Measure
   `file_size / elapsed_time` (MB/s) on the client. If the measured speed
   matches the client's bandwidth ceiling, the bottleneck is the link; OSS
   server-side processing time for uploads is typically small — when total
   time greatly exceeds server time, the network transfer dominates.
   > **Scope boundary (per-part speed data):** OSS does not expose per-part
   > transfer speed through any public control-plane API. Quantifying actual
   > per-part throughput requires the customer to have enabled bucket access
   > logging (SLS / real-time log delivery) beforehand; this skill cannot
   > retroactively obtain speed data that was never logged. When logs are
   > unavailable, attribution relies on client-side elapsed-time measurement
   > and Request ID presence/absence alone.

## 5. Fragment identification and impact

- `InitiateMultipartUpload` happened but there is no matching
  `CompleteMultipartUpload` → the upload was interrupted or abandoned; the
  uploaded parts remain as fragments that keep consuming capacity and
  incurring storage fees until completed or aborted (see
  [fragment-cleanup-guide.md](fragment-cleanup-guide.md)).
- Several different uploadIds for the same key → repeated client retries
  kept creating new events; the old ones all left fragments. Deduplicate by
  resuming one event and aborting the rest (manually).
- The diagnosis entry script enumerates unfinished uploads (key, uploadId,
  initiated time, age) via the read-only ListMultipartUploads — it never
  deletes anything.

## 6. Boundary notes (single-request upload errors handled elsewhere)

- **Integrity verification (official position)**: the ETag of an object
  created by multipart upload is NOT the MD5 of the file content (only
  objects created by PutObject carry the content MD5 as ETag), so comparing
  a multipart object's ETag against the local file MD5 is not a valid
  integrity check. The official method is to send the file's Content-MD5
  header (base64 of the raw 128-bit MD5, not of the hex string) at upload
  time: OSS rejects the upload when it does not match (source:
  help.aliyun.com MD5 consistency FAQ, verified 2026-08).
- **EntityTooLarge**: uploading > 5 GB with simple PutObject fails with
  EntityTooLarge — the fix is switching to multipart upload; the error-code
  semantics themselves belong to
  alibabacloud-oss-transfer-error-code-diagnosis.
- **FileAlreadyExists (EC 0026-00000002)**: this is NOT a bucket-level
  "no overwrite" configuration — it is triggered by the request-level
  header `x-oss-forbid-overwrite: true`; removing that header from the
  calling code restores overwrite behavior. On **versioning-enabled
  buckets** the header is ineffective: overwrite always succeeds by
  creating a new version (official `x-oss-forbid-overwrite` request-header
  semantics).
- **SignatureDoesNotMatch / transfer-acceleration error codes**: single
  request transfer-code semantics belong to
  alibabacloud-oss-transfer-error-code-diagnosis, not this skill.

## 7. Anti-patterns

1. **Choosing a sub-100KB part size "to be safe"** — the 10,000-part ceiling
   is hit at only ~1 GB of data, and tiny parts multiply per-request
   overhead; use the recommendation from the diagnosis script instead.
2. **Using multipart for a <= 5 GB file** — simple upload (PutObject) is
   simpler and leaves no fragment risk; multipart only pays off above 5 GB.
3. **Assuming a 200 response means success** — without
   CompleteMultipartUpload the object does not exist; only parts
   (fragments) were created.
4. **Concluding a stuck upload "timed out on the server"** — OSS never
   abandons an upload on its own; stalls are client-side or network-side,
   and the leftover parts remain as billable fragments until completed or
   aborted.
5. **Blindly aborting after a failure** — AbortMultipartUpload deletes all
   already-uploaded parts; if the transfer may still be wanted, prefer
   breakpoint resume (ossutil: re-run with `--checkpoint-dir <dir>`
   (2.x requires explicit flag; 1.x auto-enables for >= 100 MB) /
   SDK `resumable_upload`) so completed parts are reused.
6. **Retrying with a vanished uploadId** — `NoSuchUpload` means the event
   was completed or aborted; re-initiate a new multipart upload instead.
7. **Looking for a bucket-level switch when FileAlreadyExists appears** —
   it is a request-level header, not a bucket configuration (see §6).
