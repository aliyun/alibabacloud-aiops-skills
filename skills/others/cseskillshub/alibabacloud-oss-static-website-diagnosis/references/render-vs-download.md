# Render vs Download: Why the Static Website Downloads Instead of Rendering

Attribution reference for the symptom "opening the OSS static website URL
downloads the file / does not render the page". Pairs with the evidence
produced by `scripts/static_website_diagnosis.py` (anonymous default-domain
probe, ACL, custom-domain list).

## 1. The default-domain browser download policy (canonical cause)

For a Bucket created after **2017-10-01 00:00 (Beijing time)**, when a
BROWSER requests an object through the OSS DEFAULT domain —
`<bucket>.<region>.aliyuncs.com` (the extranet endpoint host) — and the
object name ends in `.htm`/`.html` OR its Content-Type is `text/html`, OSS
injects two response headers (`x-oss-force-download: true` and
`Content-Disposition: attachment`), so the browser downloads the page
instead of rendering it in place (EC **0048-00000001**). This policy exists
to curb phishing abuse of the shared default domain.

Official source: the OSS EC note `0048-00000001` (this reference carries NO
document URL on purpose — in a user-facing answer, cite only the URLs returned
by the entry script's `doc_verification.docs`). Official text (translated to English): "For a Bucket created after 2017-10-01
00:00, when a file is accessed through the OSS domain and the file name ends
in htm or html, OR the file's Content-Type is `text/html`, OSS adds two
response headers: x-oss-force-download: true / Content-Disposition:
attachment".

Family discipline (B-4 fix — do NOT conflate the two 0048 families):

- The HTML family (0048-00000001) cutoff is **2017-10-01** and its condition
  is ONLY `.htm`/`.html` suffix or `text/html` Content-Type. CSS and JS
  objects are NOT part of this forced-download set.
- The separate IMAGE family (0048-00000100 ~ 00000105, the 12 image MIME
  types) uses a **2019-09** cutoff. The former "Since September 2019 …
  HTML/CSS/JS" wording wrongly applied the image-family date and types to
  the HTML family; it is corrected here.

Consequences for a static website:

- The HTML object itself is fine and readable; the browser simply refuses to
  render it because the delivery channel (default domain) marks the
  `text/html` response as a download.
- API/SDK/ossutil/curl access is NOT affected — programmatic GETs still
  receive the raw bytes and the real Content-Type. The symptom is therefore
  browser-specific and often surprises users who "curl works but Chrome
  downloads".
- The only supported rendering path for browsers is a CUSTOM DOMAIN bound
  to the bucket via CNAME (see section 4).

Scope note: detailed default-domain link troubleshooting, Referer-based
hotlink protection, and the domain-binding procedure itself belong to
alibabacloud-oss-direct-access-link-diagnosis; this skill only uses the
policy as attribution knowledge for the render-vs-download symptom.

## 2. Hosting not configured

If `GetBucketWebsite` returns `NoSuchWebsiteConfiguration`, no
IndexDocument / ErrorDocument rules exist at all. Every request is served
as a plain object GET — for a browser on the default domain this combines
with the download policy of section 1, so nothing renders and files
download. Fix path (manual): enable static website hosting first, then bind
a custom domain for browser rendering.

## 3. Anonymous access blocked (403)

Static website serving requires ANONYMOUS read. Evidence chain in the
report:

- `bucket_info.acl == private` AND
- `default_domain_probe.status == 403` with OSS code `AccessDenied`
  ("Anonymous user has no right to access this bucket." — measured).

When anonymous read is absent, browsers get 403 before any rendering can
happen. Remediation is a manual WRITE operation, and the official procedure
(hosting-static-websites) has a MANDATORY FIRST STEP that is easy to miss
(G-2):

1. **Close Block Public Access FIRST** — a newly created OSS bucket has
   Block Public Access enabled BY DEFAULT, and that switch
   PREVENTS the bucket from being set to public-read / public-read-write at
   all. Official (hosting-static-websites, translated): "because Block Public
   Access is enabled by default when an OSS Bucket is created, and it prevents
   the Bucket from being set to public-read or public-read-write, you must
   turn this feature off first." Console: Permission Control ->
   Block Public Access -> turn the switch off (type the confirmation
   "I confirm closing Block Public Access"). If you
   skip this step the ACL change in step 2 FAILS and the failure is otherwise
   unexplained. (The sibling skill direct-access
   preview-download-playbook.md §1 already states that Block Public Access
   OVERRIDES public-read and denies anonymous GET.)
2. Then set the bucket ACL to public-read, OR keep the bucket private and
   grant anonymous `oss:GetObject` on the site prefix via a bucket policy.

This skill only advises; it never applies any of these WRITE operations.

## 4. The custom-domain rendering path

To render pages in a browser:

1. Bind a custom domain (e.g. `www.example.com`) to the bucket via CNAME
   (console: Bucket -> Settings -> Domain Names). Manual operation; the
   binding procedure and any certificate / hotlink concerns belong to
   alibabacloud-oss-direct-access-link-diagnosis.
2. Ensure the domain's DNS CNAME record points at the bucket's extranet
   endpoint host.
3. Mainland China regions require the domain to hold a valid ICP filing —
   see filing-requirements.md.
4. Open the site via the custom domain; the download policy of section 1 no
   longer applies.

## 5. Remaining causes after a custom domain is bound

If the page STILL downloads or misbehaves through the custom domain:

- wrong Content-Type on the object (`application/octet-stream` instead of
  `text/html`);
- the homepage rule names an object that does not exist (see
  hosting-config-playbook.md);
- the visitor keeps using an old default-domain URL from cache/bookmarks;
- HTTPS certificate issues on the custom domain (defer to the direct-access
  link skill).

## 6. Decision table (mirrors the script verdict)

| Evidence | Attribution |
|---|---|
| probe 403 + ACL private | anonymous access blocked -> grant read (manual) |
| hosting_state not_configured | enable hosting first (manual) |
| hosting configured + ACL readable + default domain used | default-domain download policy -> bind a custom domain |
| custom domain bound + still downloads | Content-Type / rule / cache checks (section 5) |
