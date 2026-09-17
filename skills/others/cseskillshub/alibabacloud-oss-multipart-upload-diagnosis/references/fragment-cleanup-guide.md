# Fragment Cleanup Guide (MANUAL — executed by the user, never by this skill)

**READ-ONLY BOUNDARY**: this skill only LISTS unfinished multipart uploads
(ListMultipartUploads). `AbortMultipartUpload` is a WRITE operation: the
commands below are templates for the **user to review and execute
themselves**. The skill and its Agent never run them.

---

## 1. What fragments are and why they cost money

When a multipart upload is initiated and some parts are uploaded, but the
upload is never completed (`CompleteMultipartUpload`) or aborted
(`AbortMultipartUpload`), the uploaded parts stay in the bucket as
**fragments**. Fragments:

- are invisible in the normal object list (so a bucket can look empty);
- occupy storage capacity and **keep incurring storage fees** until the
  upload is completed or aborted;
- block bucket deletion (a bucket must have no objects AND no fragments
  before it can be deleted; see `alibabacloud-oss-deletion-recovery-diagnosis`
  for the full deletion-blocked-by-fragments decision tree).

Source: https://help.aliyun.com/zh/oss/developer-reference/abortmultipartupload
(2026-08-27) — "uploaded parts that are neither completed nor aborted keep
occupying storage and incurring storage fees" (translated from the official
Chinese documentation).

## 2. Identify fragments (read-only — the skill already does this)

Run the diagnosis entry script; `fragments` in the JSON report lists every
unfinished upload with `key`, `upload_id`, `initiated` (UTC) and
`age_hours`:

```bash
python3 scripts/multipart_upload_diagnosis.py --bucket <bucket> [--prefix <object-prefix>]
```

Alternative manual listings (for the user):

- OSS console: Bucket -> File Management -> Fragment Management — shows
  every unfinished upload event.
- ossutil: `ossutil api list-multipart-uploads --bucket <bucket>`
  (ossutil 2.x) or `ossutil ls oss://<bucket> -m -s` (ossutil 1.x).

## 3. Decide: resume or abort

For each unfinished upload, decide BEFORE deleting anything:

| Situation | Recommendation |
|---|---|
| The file is still wanted and the checkpoint exists | **Resume** (Section 4) — reuses the already-uploaded parts |
| The upload is old / superseded / the source file changed | **Abort** (Section 5) — deletes the parts |
| Unknown | Check `initiated` time and the key; when in doubt, keep it and re-check later — abort is irreversible |

**Abort is irreversible**: it deletes all parts uploaded under that
uploadId. Never abort an upload that another process may still be writing.

## 4. Resume an interrupted upload (breakpoint resume)

- **ossutil**: re-run the same `cp` command with the same checkpoint
  directory; uploaded parts are reused:
  `ossutil cp <local-file> oss://<bucket>/<key> --checkpoint-dir <dir>`
- **SDK (Python oss2)**: `bucket.resumable_upload(key, local_file,
  store=oss2.ResumableStore(root='/tmp'), multipart_threshold=100*1024*1024,
  part_size=..., num_threads=...)` — resumes from the stored checkpoint.
- After a successful resume the old unfinished events disappear on
  completion; any OTHER stale uploadIds for the same key should be aborted
  afterwards.

## 5. Abort / delete fragments (WRITE — user executes)

### Option A — OSS console (simplest)

Bucket -> File Management -> Fragment Management: select the unwanted
fragment entries and delete them. Whole-bucket cleanup is also available
here.

### Option B — ossutil command templates

Per upload event (ossutil 2.x API form):

```bash
ossutil api abort-multipart-upload \
    --bucket <bucket> \
    --key <object-key> \
    --upload-id <uploadId>
```

Batch form (ossutil 1.x, user executes): `rm -m` targets unfinished
multipart uploads (fragments) instead of whole objects:

```bash
# abort every unfinished upload under the prefix (irreversible)
ossutil rm oss://<bucket>/<object-prefix> -m -r -f
# abort every unfinished upload of the whole bucket
ossutil rm oss://<bucket> -m -r -f
```

`-m` selects the multipart-upload (fragment) space, `-r` applies it to all
keys under the prefix, `-f` skips per-item confirmation. Double-check the
bucket/prefix before running: deleted fragments cannot be recovered, and a
still-running upload under the same prefix would be killed.

### Option C — SDK template (Python oss2, user code)

```python
import oss2
auth = oss2.ProviderAuth(...)           # user's own credentials
bucket = oss2.Bucket(auth, "<endpoint>", "<bucket>")
bucket.abort_multipart_upload("<object-key>", "<uploadId>")
```

### Option D — prevent future leftovers: lifecycle rule

Add a lifecycle rule with `AbortIncompleteMultipartUpload` (e.g. abort
uploads unfinished for more than 7 days):

- Console: Bucket -> Basic Settings -> Lifecycle -> Create Rule -> enable
  "Delete unfinished multipart upload parts".
- This is the recommended durable fix for clients that can crash mid-upload.

Official configuration constraints for the AbortMultipartUpload element
(sources: help.aliyun.com lifecycle EC articles 0014-00000027 /
0014-00000034 / 0014-00000071 / 0014-00000072, verified 2026-08):

- The AbortMultipartUpload element is mutually exclusive with a Tag node
  (EC 0014-00000027) and with a Filter/Not node (EC 0014-00000034): a rule
  that aborts fragments cannot carry tag or Not filters — keep it a
  standalone prefix-only rule.
- The element does not support the IsAccessTime condition (EC 0014-00000071).
- Some regions do not support the AbortMultipartUpload element at all
  (EC 0014-00000072); if PutBucketLifecycle returns that error, fall back
  to manual/ossutil cleanup (Options A-C) until the region enables it.

## 6. Verify after cleanup

Re-run the read-only diagnosis to confirm zero unfinished uploads remain:

```bash
python3 scripts/multipart_upload_diagnosis.py --bucket <bucket>
```

`fragments.count == 0` and `STATUS: OK` means no billable fragments remain
(storage usage meters may take some time to reflect the change).
