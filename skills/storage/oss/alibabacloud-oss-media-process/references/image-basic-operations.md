# Basic Operations Parameter Reference

Detailed parameter specifications for basic image processing operations. The script accepts operations in the format `name:key=value,key=value`. Multiple operations can be passed as separate `--operations` arguments and will be chained in order.

## Table of Contents

- [resize — Image Scaling](#resize--image-scaling)
- [crop — Image Cropping](#crop--image-cropping)
- [rotate — Image Rotation](#rotate--image-rotation)
- [flip — Image Flip](#flip--image-flip)
- [quality — Quality Adjustment](#quality--quality-adjustment)
- [format — Format Conversion](#format--format-conversion)
- [watermark — Text or Image Watermark](#watermark--text-or-image-watermark)
- [blur — Blur Effect](#blur--blur-effect)
- [sharpen — Sharpen Effect](#sharpen--sharpen-effect)
- [bright — Brightness Adjustment](#bright--brightness-adjustment)
- [contrast — Contrast Adjustment](#contrast--contrast-adjustment)
- [auto-orient — Auto Orientation](#auto-orient--auto-orientation)
- [circle — Inscribed Circle Crop](#circle--inscribed-circle-crop)
- [rounded-corners — Rounded Corners](#rounded-corners--rounded-corners)
- [interlace — Progressive Display](#interlace--progressive-display)
- [info — Image Metadata](#info--image-metadata)
- [average-hue — Dominant Color](#average-hue--dominant-color)
- [Chaining Operations](#chaining-operations)

---

## resize — Image Scaling

Scale the image by specifying width, height, percentage, or scaling mode.

| Parameter | Type | Description |
|-----------|------|-------------|
| `w` | int | Target width in pixels |
| `h` | int | Target height in pixels |
| `l` | int | Specify the longer side in pixels |
| `s` | int | Specify the shorter side in pixels |
| `p` | int (1-1000) | Scale by percentage. 50 = half size, 200 = double size |
| `mode` | string | Scaling mode (see below) |
| `limit` | 0 or 1 | Whether to limit scaling to original size. **Only `p` (percentage) can upscale without `limit`. For `w`, `h`, `l`, `s` upscaling, you MUST set `limit=0`.** 1 = limit (default). 0 = allow upscaling. |
| `color` | string | Padding color in hex (used with `pad` mode, e.g., `FFFFFF`) |

**Scaling modes (`mode`):**

| Value | Description |
|-------|-------------|
| `lfit` | (Default) Proportionally scale so the image fits within w x h |
| `mfit` | Proportionally scale so the image covers w x h (may exceed) |
| `fill` | Proportionally scale then center-crop to exactly w x h |
| `pad` | Proportionally scale to fit within w x h, then pad with `color` |
| `fixed` | Force resize to exactly w x h (may distort) |

**Examples:**

```
resize:w=400,h=300
resize:w=800,mode=lfit
resize:l=1024
resize:p=50
resize:p=200                    # Proportional upscale, no limit needed
resize:w=800,h=600,limit=0      # Fixed-size upscale, limit=0 is required
resize:w=200,h=200,mode=pad,color=F5F5F5
```

---

## crop — Image Cropping

Crop a region from the image.

| Parameter | Type | Description |
|-----------|------|-------------|
| `w` | int | Crop width in pixels |
| `h` | int | Crop height in pixels |
| `x` | int | Horizontal offset from the origin point |
| `y` | int | Vertical offset from the origin point |
| `g` | string | Gravity / anchor point (see below) |
| `p` | int (1-200) | Zoom ratio for `g=face` mode only. 100 = original size. **Only works with `g=face`** |

**Gravity values (`g`):**

| Value | Position |
|-------|----------|
| `nw` | Top-left (default) |
| `north` | Top-center |
| `ne` | Top-right |
| `west` | Center-left |
| `center` | Center |
| `east` | Center-right |
| `sw` | Bottom-left |
| `south` | Bottom-center |
| `se` | Bottom-right |
| `auto` | **Smart crop** — AI-recommended crop region (ignores w/h/p) |
| `face` | **Face crop** — center on largest face (supports `p` zoom) |

> **注意**: OSS 官方 API 要求使用全称 (`north`, `west`, `center`, `east`, `south`)。`process.py` 同时接受缩写 (`n`, `w`, `c`, `e`, `s`) 并自动转换为全称。

> **Smart crop (`g=auto`, `g=face`)**: Requires IMM project binding. Does not support anonymous access.

**Examples:**

```
crop:w=200,h=200,g=c
crop:w=300,h=300,x=50,y=50
crop:w=100,h=100,g=se
crop:g=auto                      # Smart AI-recommended crop
crop:g=face,w=200,h=200          # Face-centered crop with fixed size
crop:g=face,p=150                # Face-centered crop, 1.5x zoom
```

---

## indexcrop — Indexed Slice

Split the image along the x or y axis into equal-sized blocks, then return one block by index. `x` and `y` are mutually exclusive (if both specified, `y` takes precedence).

| Parameter | Type | Description |
|-----------|------|-------------|
| `x` | int | Split along x-axis; size of each block in pixels (range: [1, image width]) |
| `y` | int | Split along y-axis; size of each block in pixels (range: [1, image height]) |
| `i` | int | Block index to return (0-based). If index exceeds block count, returns original image |

**Examples:**

```
indexcrop:x=100,i=0
indexcrop:y=200,i=1
```

---

## rotate — Image Rotation

Rotate the image clockwise by a specified angle.

| Parameter | Type | Description |
|-----------|------|-------------|
| `angle` | int (0-360) | Rotation angle in degrees (clockwise) |
| `degree` | int (0-360) | Alias for `angle`, same meaning |

**Examples:**

```
rotate:angle=90
rotate:angle=180
rotate:angle=45
```

---

## flip — Image Flip

Flip the image horizontally, vertically, or both.

| Parameter | Type | Description |
|-----------|------|-------------|
| `v` | int (0-2) | Flip direction: `0` = vertical flip, `1` = horizontal flip, `2` = both directions |

**Examples:**

```
flip:v=0
flip:v=1
flip:v=2
```

---

## quality — Quality Adjustment

Adjust the compression quality. Applicable to JPG and WebP formats.

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | int (1-100) | Relative quality percentage |

**Examples:**

```
quality:q=80
quality:q=50
```

---

## format — Format Conversion

Convert the image to a different format.

| Parameter | Type | Description |
|-----------|------|-------------|
| `target` | string | Target format: `jpg`, `jpeg`, `png`, `webp`, `bmp`, `gif`, `avif`, `tiff`, `heic` |

**Examples:**

```
format:target=webp
format:target=png
format:target=avif
```

---

## watermark — Text or Image Watermark

Add a text or image watermark to the image. Use `text` for text watermarks, or `image` for image watermarks. Chain multiple `watermark` operations to overlay multiple watermarks.

### Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `opacity` | int (0-100) | Transparency, 100 = fully opaque |
| `g` | string | Position: `nw`, `north`, `ne`, `west`, `center`, `east`, `sw`, `south`, `se` (缩写 `n`/`w`/`c`/`e`/`s` 会自动转换) |
| `x` | int | Horizontal offset from the anchor point |
| `y` | int | Vertical offset from the anchor point |
| `tile` | int (0-1) | Tiling mode: `0` = single watermark (default), `1` = tiled across entire image. **Works for both text and image watermarks.** |

### Text Watermark Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | string | Watermark text content (plain text, auto Base64-encoded) |
| `size` | int | Font size in pixels |
| `color` | string | Font color in hex without `#` (e.g., `FFFFFF`) |
| `type` | string | Font name (Base64 encoded). If omitted, a default font (wqy-microhei) is used |
| `shadow` | string | Text shadow effect (JSON string, auto Base64-encoded). Format: `{"Enable":true,"Color":"#000000","Opacity":50,"Size":10,"Distance":5,"Angle":15}` |

### Image Watermark Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `image` | string | OSS object key of the watermark image (plain path, auto Base64-encoded) |
| `rw` | int (1-1000) | Watermark image width scaling percentage (relative to original watermark size) |
| `rh` | int (1-1000) | Watermark image height scaling percentage (relative to original watermark size) |
| `aw` | int (>0) | Absolute watermark width in pixels (auto-scales for different source image sizes) |
| `ah` | int (>0) | Absolute watermark height in pixels (auto-scales for different source image sizes) |
| `preprocess` | string | **Preprocess the watermark image** before applying. Chain sub-operations with `+` (e.g., `resize,P_30+rotate,90`). Supported sub-ops: resize, crop, indexcrop, rounded-corners, rotate. The script automatically combines the path with preprocess instruction and Base64-encodes. |

> **Scaling vs Auto-size**: Use `rw`/`rh` for percentage-based scaling. Use `aw`/`ah` for absolute pixel dimensions that auto-adjust based on source image size. `aw`/`ah` take priority over `rw`/`rh`.
>
> **Preprocess**: Uses `+` to chain sub-operations. Each sub-op uses basic operation syntax (e.g., `resize,P_30`, `rotate,90`).
>
> **Multi-watermark**: Chain multiple `watermark` operations to overlay text + image or multiple image watermarks (e.g., `"watermark:text=Copyright" "watermark:image=logo.png,opacity=50,g=se"`).

**Examples:**

```
watermark:text=Copyright 2024,size=24,color=FFFFFF,opacity=60,g=se,x=10,y=10
watermark:text=SAMPLE,size=48,color=FF0000,opacity=30,g=c
watermark:text=DRAFT,size=36,opacity=15,tile=1                    # Tiled text watermark
watermark:image=assets/logo.png,opacity=50,g=se,x=10,y=10
watermark:image=watermarks/draft.png,opacity=20,tile=1              # Tiled image watermark
watermark:image=logo.png,rw=20,rh=20                                # 20% of original size
watermark:image=logo.png,aw=200,ah=100                              # Fixed 200x100 pixels
watermark:image=panda.png,preprocess=resize,P_30,opacity=90,g=se    # 30% scale watermark
watermark:image=logo.png,preprocess=resize,w_100+rotate,90,opacity=80  # resize + rotate
```

---

## blur — Blur Effect

Apply a Gaussian blur to the image.

| Parameter | Type | Description |
|-----------|------|-------------|
| `r` | int (1-50) | Blur radius |
| `s` | int (1-50) | Standard deviation (sigma) |
| `g` | string | **Face blur mode**: `face` (blur largest face), `faces` (blur all faces) |
| `p` | int (1-200) | Zoom ratio for face blur. **Only works with `g=face` or `g=faces`** |

> **Face blur (`g=face`, `g=faces`)**: Requires IMM project binding. Does not support anonymous access.

**Examples:**

```
blur:r=5,s=3
blur:r=10,s=8
blur:g=face,r=25,s=50              # Blur largest face
blur:g=faces,r=25,s=50             # Blur all faces
blur:g=face,p=200,r=25,s=50        # Blur largest face, 2x zoom
```

---

## sharpen — Sharpen Effect

Sharpen the image.

| Parameter | Type | Description |
|-----------|------|-------------|
| `v` | int (50-399) | Sharpening value |

**Examples:**

```
sharpen:v=100
sharpen:v=200
```

---

## bright — Brightness Adjustment

Adjust the image brightness.

| Parameter | Type | Description |
|-----------|------|-------------|
| `v` | int (-100 to 100) | Brightness value. Positive = brighter, negative = darker |

**Examples:**

```
bright:v=20
bright:v=-30
```

---

## contrast — Contrast Adjustment

Adjust the image contrast.

| Parameter | Type | Description |
|-----------|------|-------------|
| `v` | int (-100 to 100) | Contrast value. Positive = more contrast, negative = less |

**Examples:**

```
contrast:v=30
contrast:v=-20
```

---

## auto-orient — Auto Orientation

Automatically rotate the image based on EXIF orientation data.

| Parameter | Type | Description |
|-----------|------|-------------|
| `v` | int | 0=keep original direction, 1=auto-rotate (default when omitted: 1) |

**Example:**

```
auto-orient
auto-orient:v=1
auto-orient:v=0
```

---

## circle — Inscribed Circle Crop

Crop the image to an inscribed circle. The output format must support transparency (e.g., PNG).

| Parameter | Type | Description |
|-----------|------|-------------|
| `r` | int | Circle radius in pixels |

**Example:**

```
circle:r=100
```

---

## rounded-corners — Rounded Corners

Apply rounded corners to the image. The output format must support transparency (e.g., PNG).

| Parameter | Type | Description |
|-----------|------|-------------|
| `r` | int | Corner radius in pixels |

**Example:**

```
rounded-corners:r=20
rounded-corners:r=50
```

---

## interlace — Progressive Display

Enable or disable progressive/interlaced rendering for JPEG images.

| Parameter | Type | Description |
|-----------|------|-------------|
| `mode` | 0 or 1 | 0 = disable, 1 = enable progressive display |

**Example:**

```
interlace:mode=1
```

---

## info — Image Metadata

Retrieve image metadata (dimensions, format, file size, etc.). Returns a JSON object with the image properties. No parameters required.

**Example:**

```
info
```

**Sample response data:**

```json
{
  "FileSize": {"value": "1024000"},
  "Format": {"value": "jpg"},
  "ImageHeight": {"value": "1200"},
  "ImageWidth": {"value": "1600"}
}
```

---

## average-hue — Dominant Color

Retrieve the dominant (average) color of the image as a hex value. No parameters required.

**Example:**

```
average-hue
```

**Sample response data:**

```json
{
  "RGB": "0x5c783a"
}
```

---

## Chaining Operations

Multiple basic image operations are processed in order. Pass each basic operation as a separate `--operations` argument:

```bash
python scripts/process.py \
  --bucket my-bucket --region cn-hangzhou \
  --source photo.jpg \
  --operations "resize:w=800" "quality:q=80" "format:target=webp"
```

This generates the OSS process string: `image/resize,w_800/quality,Q_80/format,webp`

Basic operations are applied sequentially — order matters. For example, resize before crop produces different results than crop before resize.

### Chaining Rules

- **Basic operations** can be freely chained with each other.
- **`info`** and **`average-hue`** are standalone read-only metadata operations and must be used alone.
- **`blindwatermark-embed`** can follow basic operations but must be the last operation in the chain (e.g., `resize:w=800` then `blindwatermark-embed:content=Test`).
- **`blindwatermark-extract`** must be used alone — no chaining.
- **AI detection operations** (`faces`, `bodies`, `cars`, `codes`, `labels`, `score`) must be used alone — they cannot be chained with basic, metadata, or watermark operations.

---

> Parameter specifications in this document are derived from the [Alibaba Cloud OSS Image Processing documentation](https://help.aliyun.com/zh/oss/user-guide/overview-China-site) and are reproduced here for quick reference.
