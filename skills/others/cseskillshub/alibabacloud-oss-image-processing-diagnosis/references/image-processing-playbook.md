# Image Processing Diagnosis Playbook

Client-side playbook for OSS image processing (IMG) failures. Every step
uses customer-visible channels only: read-only GET probes with
`x-oss-process`, HTTP response header interpretation, and source self-check.
The skill scripts automate this SOP; this document explains the reasoning
tree behind their verdicts.

## Symptom routing

| Symptom reported by the client | First branch to check |
|---|---|
| 400 BadRequest on a processing URL ("This image format is not supported.") | Three-step source SOP below |
| Output equals the original / style seems ignored | Style existence + parameter syntax |
| 403 on direct access while style URLs work | Original-image protection |
| Browser downloads the image instead of previewing | Default-domain forced download |
| 404 on the processing URL | Object key missing (NoSuchKey) |
| Watermark absent from the output | Watermark parameter syntax + source format support |

## Three-step source SOP (400 "image format not supported")

Trigger: a processing GET returns `400 BadRequest`, message "This image
format is not supported." (customer-visible EC `0040-00000005` in the error
body).

### Step 1: check the declared Content-Type (mime type)

HeadObject (or a plain GET) reveals the declared `Content-Type`. Officially
supported source formats: JPG, PNG, BMP, GIF, WebP, TIFF, HEIC, AVIF.

| Declared type | Conclusion | Action |
|---|---|---|
| `video/*` (e.g. video/mp4) | Not processable by design | Image processing never applies to video; advise a media processing service |
| `application/*`, `text/*`, other non-image | Not processable by design | Wrong service / wrong object; the file type cannot be processed as an image |
| `image/jpeg`, `image/png`, ... | Needs deeper verification | Continue with step 2 |

### Step 2: check the object size

From HeadObject `Content-Length`:

| Size | Judgment | Action |
|---|---|---|
| Over 20 MB | Exceeds the official source limit | Shrink the source or request a quota increase via a support ticket |
| Trivially small (a few bytes) | Strong signal of placeholder/corrupted content | Continue with step 3 to inspect the bytes |
| Reasonable (>= 1 KB) | Size is fine; content may still be wrong | Continue with step 3 |

### Step 3: verify the magic-number bytes

Fetch the leading bytes of the ORIGINAL object with a range GET
(`Range: bytes=0-15`, no `x-oss-process`), then compare the head bytes
against the magic-number table. This step decides whether the stored bytes
are really an image of the declared type.

Magic-number table:

| Format | Leading bytes (hex) | Readable form |
|---|---|---|
| PNG | `89 50 4E 47 0D 0A 1A 0A` | `\x89PNG....` |
| JPEG | `FF D8 FF` | `\xff\xd8\xff...` |
| GIF | `47 49 46 38` | `GIF8...` |
| WebP | `52 49 46 46 .. .. .. .. 57 45 42 50` | `RIFF....WEBP` |
| BMP | `42 4D` | `BM...` |
| TIFF | `49 49 2A 00` or `4D 4D 00 2A` | `II*\x00` / `MM\x00*` |
| HEIC | `ftyp` at offset 4, brand `heic/heix/hevc/mif1` | `....ftypheic` |
| AVIF | `ftyp` at offset 4, brand `avif/avis` | `....ftypavif` |

Verdict matrix:

| Magic finding | Root cause | Advice |
|---|---|---|
| A single printable character or all-zero bytes (e.g. content is literally `1`) | The upload code stored a placeholder instead of image bytes | Fix the upload code and re-upload the real image |
| Magic matches a different format than declared (e.g. declared PNG, magic is JPEG) | The file was renamed or uploaded with a wrong Content-Type | Re-upload with the correct Content-Type |
| Magic correct but processing still fails | Content corrupted / truncated | Re-upload the original image |
| No magic match | Not binary image data at all | Re-upload a valid image |

## "Processing not effective" attribution tree

When the client says the processing does not take effect, walk this tree in
order (each branch is verifiable with the skill's read-only probes):

1. **Parameter syntax invalid** - validate `x-oss-process` offline first
   (see params-limits.md). Unknown actions or out-of-range values make the
   request fail or produce the original unchanged.
2. **Source not a supported format** - the three-step SOP above; a 400
   "image format not supported" from the render probe confirms it.
3. **Source beyond limits** - over 20 MB, or beyond the pixel limits
   (rotate sources max 4096 px per side; other operations max 30000 px per
   side and 250 MP total; see params-limits.md).
4. **Style not saved / deleted** - for `style/<name>` URLs: the style must
   exist in the bucket (max 50 per bucket). If it was never saved, the
   rendering cannot apply it. Recreating a style is manual console work -
   this skill is read-only and never creates styles.
5. **Original-image protection 403** - when protection is enabled, direct
   access to the original object is denied (403 AccessDenied) while
   style-based access keeps working. This is configuration behavior: the
   bucket owner deliberately protected originals. If the client needs
   direct original access, they must disable the protection in the console
   (manual guidance only). Official details
   (https://help.aliyun.com/zh/oss/user-guide/protect-source-images):
   - Up to 10 protection rules, each a prefix and/or suffix; a file is
     protected when it matches ANY rule; the case-insensitive option
     applies per rule. The protected-extension list can be set to `*`
     (protects everything).
   - Protection applies to ANONYMOUS access only - signed URLs can still
     fetch the original. So "403 anonymous but signed access works" is
     expected behavior, not a bug.
   - Known pattern: "anonymous 403 directly, but 200 via CDN" - the CDN
     origin-fetches with credentials against a private bucket, bypassing
     the anonymous-only protection.
   - Four custom style separators exist (`-`, `_`, `/`, `!`); with a
     separator set, `.../ObjectName!StyleName` replaces the
     `?x-oss-process=style/<name>` form.
   - The per-rule protection feature is in public beta; enabling it
     requires a support request.
6. **Object missing** - 404 NoSuchKey: the key was mistyped, deleted, or
   never uploaded.
7. **CDN parameter filtering in front of the bucket** - when processed URLs
   (`?x-oss-process=...` or `!style`) are served through a CDN domain, the
   CDN "ignore parameters" / parameter-filtering feature can drop the
   processing parameters from the cache key or from the origin request, so
   different variants cross-contaminate each other or styles silently stop
   applying. See the dedicated section below; this is CDN-side
   configuration, not an OSS IMG fault.

## Resize semantics: lfit never enlarges by default

`resize` returns the ORIGINAL resolution whenever the target exceeds the
source - the output is min(target, source) - because the default switch is
`limit_1`. This is the actual root cause of the live ticket pattern
"resize,w_1500,h_1125 still outputs the original 1504x1120" (ticket
0001ZS5JB6): nothing failed; resize simply does not enlarge by default.
To allow enlarging, add `limit_0` explicitly
(`image/resize,w_1500,h_1125,limit_0`). Animated (dynamic) sources
support downscaling only - enlarging a dynamic image is not supported.

## Quality, compression and animation semantics

- **OSS never compresses images by default**: uploaded bytes are stored
  as-is; any compression requires an explicit `x-oss-process` action
  (quality / format) or an IMM pipeline. "My uploaded image was not
  compressed" is expected storage behavior, not a processing fault, and
  video files never accept image-processing parameters at all.
- **quality applies to lossy formats only**: `q` is the RELATIVE quality
  (a percent of the source quality; e.g. source 80% + q_90 -> 72%), `Q`
  is the ABSOLUTE quality (never raises quality above the source), range
  [1,100]. Effective on JPG and WebP sources only (on WebP, q behaves
  like Q); PNG and other lossless formats are UNAFFECTED - "quality,q_90
  has no effect on my PNG" (ticket 000G2RJ98G) is expected behavior, not
  a bug.
- **Animated GIF flattening**: only resize, crop and watermark keep a GIF
  animated; **rotate is NOT supported on GIF and silently flattens it to a
  static GIF** (official rotate doc: "GIF images do not support the rotate
  parameter. If a rotate operation is performed on an animated GIF, it
  becomes a static GIF."); other actions (quality, format,
  blur, ...) also extract a single frame - applying absolute-quality
  compression or format conversion to an animated GIF returns a STATIC
  image. Keep the original format for animated sources.
- **Dynamic WebP whitelist**: processing dynamic (animated) WebP sources
  fails with `BadWebPImage` unless the account has the animated-WebP
  whitelist - file a support ticket to enable it (tickets 000G2RFMKG
  family). WebP animations also do not support auto-orient.
- **IMG QPS / throughput quotas**: 50 QPS / 20 MB/s by default in
  cn-hangzhou, cn-shanghai, cn-beijing, cn-zhangjiakou and cn-shenzhen;
  5 QPS / 2 MB/s elsewhere; raising them requires a support ticket
  (see the quotas table in params-limits.md).

## Default-domain forced download (preview fails)

Symptom: the image URL opens fine but the browser downloads the file
instead of displaying it; processing itself succeeded (HTTP 200).

Cause: **only for buckets created AFTER 2019-09-30 15:00** (official
EC 0048-00000105 condition), OSS adds `Content-Disposition: attachment`
AND `x-oss-force-download: true` when objects whose Content-Type matches
one of these 12 MIME types are accessed through the OSS default domain
(`<bucket>.oss-<region>.aliyuncs.com`):

> image/jpeg, image/gif, image/tiff, image/png, image/webp,
> image/svg+xml, image/bmp, image/x-ms-bmp, image/x-cmu-raster,
> image/exr, image/x-icon, image/heic

Browsers download instead of rendering inline. The `x-oss-force-download:
true` header is a stronger/more reliable indicator than
`Content-Disposition` alone. This is security-policy behavior, not an
error - the customer-visible EC in access logs for such responses is
`0048-00000105`. Buckets created BEFORE 2019-09-30 15:00 are NOT subject
to this rule - do not attribute their preview failure to forced download.

Resolution options (manual guidance):
1. Bind a custom domain (CNAME) to the bucket - custom-domain access does
   not force download (recommended).
2. Serve the bucket through CDN with the custom domain.
3. For signed URLs, add `response-content-disposition=inline` to override
   the disposition per request.

Verification note: a signed SDK probe does not always surface the
`attachment` header (the probe against the eval object returned an empty
Content-Disposition); attribute the forced download from the browser-visible
behavior plus this documented default-domain rule, not from the SDK probe
alone.

## Watermark not applied

Check in order:
1. Parameter syntax - `image/watermark,...` with the correct key-value
   pairs: text watermarks need the URL-safe-Base64-encoded `text_` value
   (the `t_` key is TRANSPARENCY, range [0,100], default 100 - NOT the
   text content); the font name goes in `type_` (also Base64-encoded,
   default wqy-zenhei = `d3F5LXplbmhlaQ`); `color_` is plain RGB hex
   (NOT Base64, default 000000); image watermarks need the URL-safe-
   Base64 `image_` object reference.
2. Source format support - dynamic GIF sources support only resize, crop
   and watermark (rotate is NOT supported on GIF - it silently becomes
   static); other unsupported sources reject the whole request (400).
3. Order of operations - processing runs in parameter order; a watermark
   placed before a full-frame crop can be cropped away.
4. Cached results at a CDN in front of the bucket - CDN may serve a stale
   variant; this is a knowledge-level note only (this skill does not test
   CDN domains).

## CDN in front: parameter filtering cross-contamination (ticket cluster)

Symptom (live ticket cluster, three same-family tickets): processed image
URLs return the WRONG variant (one style's output served for another), or
style-based URLs suddenly return the original after a CDN configuration
change, while probing the OSS bucket directly returns the correct variant.

Root cause: the bucket is served through a CDN domain whose "ignore
parameters" feature is enabled. With it enabled, CDN edge nodes
treat URLs that differ only in query parameters as the SAME cache key, so
`?x-oss-process=image/resize,w_100` and `...w_500` (and the no-parameter
original) collide and whichever variant was cached first is served for all
of them - cross-contamination. Deleting a CDN "keep only these parameters"
rule that included the processing parameter has the same effect: the
processing parameter no longer reaches OSS, so styles stop applying.

Attribution method (read-only): fetch the same processed URL directly
against the OSS default endpoint (`<bucket>.oss-<region>.aliyuncs.com`) and
against the CDN domain. OSS-direct correct + CDN wrong => CDN parameter
filtering, not an OSS IMG problem.

Resolution (manual guidance - the fix lives in the CDN console, this skill
never changes CDN configuration):
1. Disable "ignore parameters" for the domain, or configure the parameter
   rules so `x-oss-process` is preserved and passed to the origin
   (https://help.aliyun.com/zh/cdn/user-guide/ignore-parameters).
2. Purge the stale edge cache afterwards: per the same official doc, edge
   nodes do NOT refresh automatically after the parameter configuration
   changes - submit a URL/directory refresh (RefreshObjectCaches) so the
   new configuration takes effect.
3. If processing parameters are used purely as cache-busting variables
   elsewhere, consider the reverse trade-off and keep only `x-oss-process`.

Boundary: CDN cache/parameter configuration itself is out of scope for this
skill; state the attribution result and defer the actual configuration
change to the CDN product guidance.

## Out of scope

Video processing, IMM intelligent media, CDN domain testing, billing of
processing fees - state the boundary and defer to the appropriate product
documentation or sibling skills.
