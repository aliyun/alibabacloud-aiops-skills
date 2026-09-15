# x-oss-process Parameters and Official Limits

Official parameter syntax and limits for OSS image processing, verified
against the Alibaba Cloud public documentation on 2026-08-27. Sources:

- Image processing overview & limits:
  https://help.aliyun.com/zh/oss/user-guide/overview-17/
- Operation modes (file URL / SDK / API):
  https://help.aliyun.com/zh/oss/user-guide/img-implementation-modes
- Resize parameter ranges:
  https://help.aliyun.com/zh/oss/user-guide/resize-images-4
- Usage limits summary:
  https://help.aliyun.com/zh/oss/user-guide/limits

## URL syntax

| Form | Meaning |
|---|---|
| `?x-oss-process=image/<action>,<key_value>[/<action>,<key_value>...]` | Inline processing; multiple actions run in order, separated by `/` |
| `?x-oss-process=style/<style-name>` | Apply a saved style (max 50 styles per bucket) |
| `<url>!<style-name>` | Custom-delimiter form of the style URL (delimiter configured on the bucket) |

Example: `https://<bucket>.<endpoint>/<key>?x-oss-process=image/resize,w_300/quality,q_90`

For private objects the processing parameters must be embedded in a signed
GET URL (SDK `sign_url(..., params={'x-oss-process': ...})`); anonymous
file-URL processing only works for public-read objects.

## Action set (official new-version actions)

resize, watermark, crop, quality, format, info, auto-orient, circle,
indexcrop, rounded-corners, blur, rotate, interlace, average-hue, bright,
sharpen, contrast.

## Key parameter ranges used by the offline validator

| Action | Parameter | Range / values (official) |
|---|---|---|
| resize | `w`, `h`, `l` (long edge), `s` (short edge) | [1, 16384], positive integer |
| resize | `p` (percentage) | [1, 1000], positive integer (1-100 shrink, 100-1000 enlarge) |
| resize | `m` (mode) | lfit (default), mfit, fill, pad, fixed |
| resize | `color` (pad fill color) | 6-digit RGB hex, e.g. FF0000 |
| resize | `limit` (enlarge switch) | 0 or 1; default `limit_1`: when the target resolution exceeds the source, the ORIGINAL resolution is returned (resize never enlarges by default); add `limit_0` to allow enlarging |
| resize | `e` (edge priority) | 0 (long edge, default) or 1 (short edge) |
| rotate | bare angle value | [0, 360] degrees, clockwise; the official form is the SINGLE BARE value (`image/rotate,90`, e.g. chained `image/resize,w_300/rotate,90`); the `a_<angle>` key_value form is rejected live with 400 InvalidArgument EC 0040-00000217 (measured 2026-09-07 on bucket test-agentceping: `rotate,90`/`rotate,70` -> 200 while `rotate,a_90`/`rotate,abc`/`rotate,400` -> 400). This mirrors the `format` bare-value rule. **rotate is NOT supported on GIF** (see Dynamic images row below) |
| quality | `q` (relative) / `Q` (absolute) | [1, 100]; `q` = percent of the source quality, `Q` = absolute target that never raises quality above the source; effective on lossy JPG/WebP sources only - PNG and other lossless formats are unaffected. **WebP source: `q` behaves identically to `Q`** (official: adjust-image-quality.md:10 "only JPG sources determine relative quality; for WebP sources q equals Q") |
| format | bare target value | jpg, png, bmp, gif, webp, tiff, heic, avif; the official form is the bare value (`image/format,webp`, e.g. `image/resize,w_100/format,jpg`); the `f_<target>` key_value form is rejected live with 400 InvalidArgument EC 0040-00000206. **Region restriction**: heic and avif targets are supported ONLY in 6 regions (cn-zhangjiakou, cn-shanghai, cn-shenzhen, cn-hangzhou, cn-beijing, ap-southeast-1 Singapore); conversion to heic/avif in other regions will fail. Additional: transparent-channel HEIC cannot be saved as JPG; gif target inherits animation from a GIF source but produces the source format otherwise (official: convert-image-formats-2.md) |
| interlace | value | 0 or 1 |
| sharpen | value | [50, 399] |
| bright / contrast | value | [-100, 100] |
| blur | `r` (radius), `s` (sigma) | [1, 50] each |
| crop / circle / rounded-corners / indexcrop / watermark | pixel-valued keys | positive integers; many keys, shape-checked only |

## Source limits (official)

| Item | Limit |
|---|---|
| Source formats | JPG, PNG, BMP, GIF, WebP, TIFF, HEIC, AVIF only. **Dual-position note on AVIF as source**: the official limits.md includes AVIF in the source-format list, while resize-images-4.md:11 does NOT list AVIF as a supported source - treat AVIF sources as region/feature-dependent and verify with a render probe |
| Dynamic images (e.g. GIF, animated/dynamic WebP) | Only resize, crop and watermark are supported, and only for DOWNSCALING (enlarging a dynamic image is not supported); **rotate is NOT supported on GIF** (official: "GIF images do not support the rotate parameter; performing rotate on an animated GIF turns it into a static GIF"); other actions (quality, format conversion, blur, ...) extract a single frame - applying absolute-quality compression (`Q`) or format conversion to an animated GIF returns a STATIC image; keep the original format for animated sources |
| Source size | <= 20 MB (quota increase via support ticket, up to 200 MB) |
| Source dimensions | rotate operations: each side <= 4096 px; other operations: each side <= 30000 px and total pixels <= 250,000,000 |
| Styles per bucket | max 50 |

## Processing quotas (QPS / throughput)

Default account-level IMG quotas (not bucket-level settings); higher
limits require a support ticket:

| Region | Default QPS | Default processing data size |
|---|---|---|
| cn-hangzhou, cn-shanghai, cn-beijing, cn-zhangjiakou, cn-shenzhen | 50 | 20 MB/s |
| All other regions | 5 | 2 MB/s |

Source: https://help.aliyun.com/zh/oss/user-guide/limits (usage limits,
verified 2026-09-02).

## Output limits (official)

| Item | Limit |
|---|---|
| WebP output | width/height <= 16383 px |
| HEIC output | width/height <= 4096 px |
| AVIF output | width <= 4096 px, total pixels <= 9,437,184 |
| resize output | width/height <= 16384 px, total pixels <= 16,777,216 |

## Error facts measured against real OSS responses

- Processing a non-image source (e.g. a text/plain object) with
  `x-oss-process=image/resize,w_50` returns `400 BadRequest`, message
  "This image format is not supported.", EC `0040-00000005`
  (measured 2026-08-27, bucket test-agentceping, object
  test-assets/sample.txt).
- A processing GET against a missing key returns `404 NoSuchKey`
  (EC `0040-00000024` on the processing path; HeadObject reports
  EC `0026-00000001`), measured 2026-08-27.
- A valid rendering probe on a real JPEG (bucket test-agentceping, object
  test-assets/sample.jpg, `image/resize,w_50`) returns 200 with
  Content-Type image/jpeg and a smaller body, measured 2026-08-27.
- Default-domain browser access of image-type objects (only for buckets
  created AFTER 2019-09-30 15:00, and only for the 12 official MIME types:
  image/jpeg, image/gif, image/tiff, image/png, image/webp, image/svg+xml,
  image/bmp, image/x-ms-bmp, image/x-cmu-raster, image/exr, image/x-icon,
  image/heic) is served with `Content-Disposition: attachment` AND
  `x-oss-force-download: true` (forced download, customer-visible EC
  `0048-00000105` in access logs) - see the playbook for resolution.

## Official IMG error codes and messages

Verified against the official error-response doc
(https://help.aliyun.com/zh/oss/user-guide/common-errors) and FAQ
(https://help.aliyun.com/zh/oss/user-guide/faq-2). IMG errors use an XML
body (`Code` / `Message` / `RequestId` / `HostId`):

| HTTP | Code | Typical meaning |
|---|---|---|
| 400 | InvalidArgument / BadRequest / MissingArgument | bad or missing processing parameter |
| 400 | CutEdgeExceedRange | crop/circle region beyond the source image bounds - NO 0040-* EC field, message "Advance cut's position is out of image.", body carries the bucket HostId (never an endpoint signal) [measured / ticket-sourced, NOT in the official common-errors table] |
| 400 | BadWebPImage | dynamic (animated) WebP source without the account whitelist - file a support ticket to enable the animated-WebP whitelist |
| 400 | ImageTooLarge | source exceeds the size/pixel limits above |
| 400 | WatermarkError | watermark parameter or watermark-object problem |
| 400 | NotImplemented | action not implemented |
| 403 | AccessDenied | ACL / original-image protection / bucket policy |
| 403 | SignatureDoesNotMatch | signed processing URL signature invalid |
| 403 | UserDisable | the ACCOUNT owning the resource is disabled (EC 0003-00000801) - official three causes: **account arrears**, security ban, or OSS not activated; switching endpoints or granting RAM permissions will not fix it |
| 404 | NoSuchKey / NoSuchStyle | object missing / style name does not exist |
| 500 | InternalError | service-side failure; quote the RequestId |

Bound error messages seen in tickets:
- `MemLimitExceeded` - source beyond the pixel limits (30000 px per side /
  250 MP total; rotate: 4096 px per side). Use `image/info` to read the
  real dimensions before concluding.
- `Picture exceed the maximum allowable rotation range` - rotate on a
  source whose side > 4096 px or width*height > 4096*4096.
- `NoSuchStyle` (404) - the `style/<name>` in the URL was never saved or
  was deleted (styles are bucket-scoped, max 50).
- EC `0017-00000288` (400) - the `x-oss-process` parameter value is too
  long (too many chained actions); shorten the processing chain.
- EC `0004-00000801` (503) - IMG CPU concurrency exceeded (throttling);
  reduce image-processing concurrency; higher limits need a support
  request. Attribute to server-side throttling, not to the image itself.
- EC `0040-00000001` (400) - source image exceeds the official size limit
  (official limits.md directly references this EC for "source exceeds size limit").
- EC `0040-00000011` (400) - WebP encoding output exceeds 16383 px
  (official: convert-image-formats-2.md WebP output limit).

## Parameter composition rules (official)

Source: https://help.aliyun.com/zh/oss/user-guide/key-rules-for-image-processing

- Key-value pairs are ORDER-INDEPENDENT; IMG re-sorts them to the
  documented canonical order before processing.
- Duplicate keys: the LATER definition overrides the earlier one.
- Resize orientation: long-edge priority by default (`e=0`); short-edge
  priority with `e=1`.
- URL-safe Base64 (RFC 4648) applies ONLY to watermark parameters (text
  content, text color, text font, image watermark object): replace `+`
  with `-`, `/` with `_`, strip trailing `=`. Never use it inside the
  request signature.

## Persistence (saving processed images)

Source: https://help.aliyun.com/zh/oss/user-guide/save-processed-images

- Requires `oss:PostProcessTask` on the source bucket plus
  `oss:PutBucket` (target bucket) and `oss:PutObject` (target object).
- Source and target buckets may differ but must belong to the SAME
  account and the SAME region.
- Saving the result of a plain file-URL processing request directly to a
  bucket is NOT supported - fetch the processed image locally first, then
  upload (or use the SDK persistence path).
- The saved image ACL inherits the target bucket (no custom ACL).
