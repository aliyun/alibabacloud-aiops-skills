# Preview-vs-Download Playbook

Attribution guide for "opening an OSS link turns into a download instead
of previewing". The diagnosis entry probes the default domain anonymously
(`--object`) and reports the real status / Content-Type /
Content-Disposition / X-Oss-Force-Download; this playbook explains each
branch.

## 1. Attribution decision tree

| Probe evidence | Root cause | Fix (manual) |
|---|---|---|
| HTTP 403, bucket ACL `private` | Anonymous access is denied by design | Preview via presigned GET URL or public-read object/bucket ACL; the 403 itself does NOT prove a referer misconfiguration |
| HTTP 403, bucket ACL public-read, Block Public Access enabled | The account/bucket-level Block Public Access switch overrides public-read and denies anonymous GET | Disable Block Public Access (or keep it and use presigned URLs) — this is a common "file cannot be opened at all" root cause |
| HTTP 403, bucket NOT private | EC 0003-00000005 class: attribute in the fixed order referer rules -> cause-1 object private ACL -> Block Public Access -> unattributed escalation | Run the bisection (the script does it automatically); see [ec-0003-00000005-bisection.md](ec-0003-00000005-bisection.md) |
| HTTP 200, `x-oss-force-download: true` | OSS itself injected the forced-download headers (0048 error-code family, section 2) | Serve the affected types through a bound custom domain |
| HTTP 200, `Content-Disposition: attachment` | Object uploaded with attachment disposition | Re-upload / update object HTTP headers to `Content-Disposition: inline` |
| HTTP 200, `Content-Type: application/octet-stream` | Content-Type misconfiguration; browser treats unknown binary as download | Set the real MIME type (image/jpeg, application/pdf, video/mp4, ...) |
| HTTP 200, renderable type, still downloads | 0048 forced-download family matches the type + bucket/domain (section 2) | Bind a custom domain; preview those types through it |

## 2. Default-domain forced-download policy (0048 error-code family)

OSS default domains (`<bucket>.oss-<region>.aliyuncs.com` and
`<bucket>.<region>.aliyuncs.com`) are shared hosts. As a security
policy, OSS injects BOTH `x-oss-force-download: true` and
`Content-Disposition: attachment` into responses for the file families
below — the browser then downloads instead of previewing, and setting
`Content-Disposition: inline` on the object does NOT take effect. The
response-header pair is the probe-level proof of this policy.

The full official family (help.aliyun.com user-guide EC pages):

| EC code | Applies to | Cutoff / condition |
|---|---|---|
| 0048-00000001 | `.htm`/`.html` suffix or `text/html` Content-Type | Buckets created after 2017-10-01 00:00 (Beijing time) |
| 0048-00000002 | Same HTML set over transfer-acceleration domains (`oss-accelerate`) | Transfer acceleration enabled after 2020-12-31 00:00 |
| 0048-00000100 ~ 00000105 | The 12 image MIME types (below) over default domains | Buckets created after the 2019-09 cutoffs (earliest 2019-09-23 17:00, latest 2019-09-30 15:00, Beijing time; the exact cutoff is region-batched across EC 100/101/102/103/104/105) |
| 0048-00000106 ~ 00000112 | ALL file types over transfer-acceleration domains | Transfer acceleration ENABLED after one of 7 per-code cutoffs (Beijing time): 106 = 2020-11-17 11:07, 107 = 2021-01-07 12:00, 108 = 2021-01-07 18:00, 109 = 2021-01-08 18:00, 110 = 2021-01-14 12:00, 111 = 2021-01-16 00:00, 112 = 2023-02-01 00:00. The trigger is the transfer-acceleration ENABLEMENT time, NOT the bucket creation date; when the exact batch is unknown, treat the earliest cutoff (2020-11-17 11:07) as the conservative answer (N-5 fix, per-code verified against the official EC pages 2026-09-07; supersedes the former blanket "2020-12 cutoffs" wording mis-copied from the 0048-00000002 row) |
| 0048-00000113 | ALL file types over standard default domains for new users | New users after 2022-10-09 (Beijing time) |
| 0048-00000114 | The image MIME types (12-image family) over standard default domains in 6 specified regions | Buckets created in East China 6 (Fuzhou), North China 6 (Ulanqab), South China 2 (Heyuan), South China 3 (Guangzhou), East China 5 (Nanjing), Central China 1 (Wuhan) from 2025-12-22 10:00:00 (Beijing time) |
| 0048-00000200 ~ 00000203 | `.apk` / `.ipa` installation packages over default PUBLIC domains | Buckets created after 2023-08-15: returns HTTP **400 `ApkDownloadForbidden`** (blocked outright, NOT a forced download) |
| 0048-00000300 / 00000301 | 3xx redirect rules over default PUBLIC domains | Buckets created after 2024-08-05: returns HTTP **400 `ExternalRedirectForbidden`** when a 3xx redirect triggers |

The 12 image MIME types (0048-00000100 family):

```
image/jpeg  image/gif  image/tiff  image/png
image/webp  image/svg+xml  image/bmp  image/x-ms-bmp
image/x-cmu-raster  image/exr  image/x-icon  image/heic
```

Practical consequences (supersedes the earlier blanket claim that
"images preview normally over the default domain" — that only holds for
buckets created BEFORE the 2019-09 cutoffs):

- HTML (`.htm`/`.html` suffix or `text/html` Content-Type) never previews
  over the default domain for post-2017-10 buckets (EC 0048-00000001);
  images (the 12-MIME family) are equally force-downloaded for post-2019-09
  buckets. JS/CSS/JSON are NOT part of the 2017-10 HTML family — they only
  force-download under the ALL-file-types rule for new users after
  2022-10-09 (EC 0048-00000113), so do NOT lump them with the 2017-10 HTML
  cutoff (B-4-class cross-family pollution, corrected 2026-09-03).
- APK/IPA distribution over OSS domains is restricted outright.
- For a reported "image/PDF turns into download", first compare the
  bucket `creation_date` (reported by the diagnosis script) against the
  cutoffs: after the cutoff the ONLY preview path is a bound custom
  domain (see domain-binding-guide.md); before the cutoff, suspect the
  object metadata (Content-Type / Content-Disposition) instead. Exception:
  the 0048-00000106~112 transfer-acceleration family keys off the
  transfer-acceleration ENABLEMENT time (7 per-code cutoffs, 2020-11-17 ~
  2023-02-01), not the bucket creation date.
- PDF is NOT in the 12-MIME image list: a PDF previews over the default
  domain whenever its Content-Type is `application/pdf` and no
  attachment disposition is set; if it downloads, check the metadata.

## 3. Anonymous 403 is a diagnosis branch

A private bucket denies anonymous GET/HEAD with 403 AccessDenied. For
"cannot preview" complaints on private buckets this is expected behavior:
the object is not publicly readable, so the browser cannot fetch it.
Remediation options (user's manual choice):

1. Presigned GET URL with an expiration (sibling presigned-url-v4 skill
   covers signing questions).
2. Object ACL public-read for assets that must be public.
3. Bucket policy granting read to specific principals.

Only when the bucket is NOT private does the EC 0003-00000005
bisection apply: referer rules -> object-level private ACL (cause-1) ->
Block Public Access (official "Problem examples") -> unattributed escalation; see
[ec-0003-00000005-bisection.md](ec-0003-00000005-bisection.md).

## 4. Fix checklist (templates only — never applied by this skill)

1. Verify object Content-Type is the real MIME type.
2. Verify object Content-Disposition is `inline` (or absent).
3. For HTML (post-2017-10) or any type blocked by the 0048 forced-download
   families (including images on post-2019-09 buckets, all file types for
   new users after 2022-10-09, and APK/IPA
   packages): bind a custom domain and serve the object through it.
4. For private buckets: use presigned URLs or public-read ACL.
5. Re-test in a private browser window to bypass local cache.
