# PDS Image Editing Guide

> **Hard rule: ALL image editing MUST be done via `aliyun pds image-process` below. You MUST NOT download the image and process it locally with PIL, Pillow, OpenCV, ImageMagick, or any other Python/library/CLI tool. Local processing bypasses server-side ICC color-space management, EXIF orientation handling, and PDS revision tracking. Even if the visual result looks correct, local processing is a FAILURE.**

**Scenario**: You have a source image's `drive_id` plus absolute path or `file_id` (and optionally `revision_id`) and want to edit it and optionally save the result back to PDS.

Editing is done in **one CLI call** — `aliyun pds image-process`. The command renders the `x-pds-process` parameter (operation assembly, base64 encoding, `pds://` schema, save-as) and validates every parameter locally, then calls the Process API. You do **not** build `x-pds-process` by hand or run any Python script.

---

## Command

```bash
aliyun pds image-process \
  --drive-id <SOURCE_DRIVE_ID> \
  --path <SOURCE_PATH> \
  [--revision-id <SOURCE_REVISION_ID>] \
  --operations "<op1>" "<op2>" ... \
  [--save-as true \
     --target-drive-id <ID> \
     --target-path <FILE_OR_PARENT_PATH> \
     [--target-revision-id <ID>] \
     --file-name <NAME>] \
  [--dry-run true]
```

| Flag | Description |
|------|-------------|
| `--drive-id` + `--path` / `--file-id` | Source image. Provide exactly one path/ID unless `--dry-run`; paths are resolved internally. |
| `--revision-id` | Source revision (optional; latest is used if omitted). |
| `--operations` | One or more operations, executed left to right. Pass each as a separate quoted argument. Do **not** add the `image/` prefix — it is handled for you. |
| `--save-as` | Persist the edited image to PDS. Requires the `--target-*` flags below. Save-as always uses the current profile's domain (domains are isolated). |
| `--target-drive-id` | Save-as target drive. |
| `--target-path` / `--target-file-id` | Target file (overwrite) **or** existing parent folder (new file), by path or ID. |
| `--target-revision-id` | Set only when overwriting an existing file. |
| `--file-name` | Saved file name. |
| `--dry-run` | Print the generated `x-pds-process` without calling the API. Path options are rejected in this mode because resolving them requires API calls; use IDs/revisions for dry-run. |

**On success (executed)** returns the saved file: `{ "drive_id": ..., "file_id": ..., "revision_id": ... }`.

> Tip: to get the source `revision_id` and image dimensions, use `aliyun pds get-file --drive-id <id> --path "/…/source.png"` (or `--file-id <id>` when already known). The response includes `image_media_metadata.width/height`, and `--path` resolves internally without a separate `resolve-path` call.

### Use paths in the same call

Pass the source as `--path` and an existing save-as parent folder as `--target-path`; `image-process` resolves both internally. Use `get-file --path` first only when dimensions or metadata are needed for operation planning. If the save-as parent folder does not exist, create it once with `resolve-path --create-missing`, then pass the returned ID.

Do **not** resolve the target *file* itself before save-as — it doesn't exist yet, so that lookup is wasted (and errors). Only pass `--target-file-id` = an existing file's id (plus `--target-revision-id`) when you intend to **overwrite** that file.

---

## Watermark shortcut (recommended)

Instead of manually building the watermark operation in `--operations`, use these shortcut parameters:

```bash
aliyun pds image-process \
  --drive-id 1020 --path "/Photos/source.png" \
  --watermark-path "/Assets/watermark.png" \
  [--watermark-drive-id <ID>] \
  [--watermark-revision-id <ID>] \
  [--watermark-position center|nw|north|ne|west|east|sw|south|se] \
  --save-as true --target-drive-id 1020 --target-path "/Photos/Edited" \
  --file-name watermarked.png
```

| Flag | Description |
|------|-------------|
| `--watermark-path` / `--watermark-file-id` | Watermark image, by path or ID. Provide one for image watermark. |
| `--watermark-drive-id` | Watermark image drive ID (defaults to source `--drive-id`). |
| `--watermark-revision-id` | Watermark image revision ID (auto-fetched if omitted). |
| `--watermark-position` | Watermark position: `center` (default), `nw`, `north`, `ne`, `west`, `east`, `sw`, `south`, `se`. |

The CLI automatically:
1. Fetches the watermark image's revision ID if not provided.
2. Builds the complete `pds://domains/{domain}/drives/{drive}/files/{file}/revisions/{revision}` schema.
3. Base64-encodes the schema.
4. Appends the watermark operation to `--operations`.

**Example:**
```bash
aliyun pds image-process \
  --drive-id 1020 --file-id <SOURCE_FILE_ID> \
  --watermark-file-id <WATERMARK_FILE_ID> \
  --watermark-position center \
  --save-as true --target-drive-id 1020 --target-file-id <PARENT_FOLDER_ID> \
  --file-name watermarked.png
```

---

## Operations quick reference

Compose `--operations` from the operations below. **The CLI validates ranges, enums, required params and coordinates**, so you don't need to memorize limits — an invalid value fails fast with a clear message. Base64 for text/prompt/watermark is handled automatically: **pass raw text** (a raw value must not contain a comma).

| Operation | Syntax | Notes |
|-----------|--------|-------|
| resize | `resize,w_200` / `resize,h_200` / `resize,l_200` / `resize,p_50` | `m_` mode: `lfit`(default)/`mfit`/`fill`/`pad`/`fixed`. Enlarging needs `limit_0`. `pad` uses `color_RRGGBB`. |
| crop | `crop,x_,y_,w_,h_` | `g_` origin: nw/north/ne/west/center/east/sw/south/se/face/auto. |
| quality | `quality,q_80` (relative) / `quality,Q_90` (absolute) | JPG/WebP only. |
| format | `format,png` | jpg/jpeg/png/webp/bmp/gif/tiff/heic/avif. |
| auto-orient | `auto-orient,1` | 0 keep / 1 auto-rotate by EXIF. |
| rotate | `rotate,90` | Clockwise degrees 0–360. |
| flip | `flip,0` / `flip,1` / `flip,2` | **0 = vertical, 1 = horizontal**, 2 = both (counter-intuitive). |
| circle | `circle,r_100` | Radius 1–4096. |
| rounded-corners | `rounded-corners,r_30` | Radius 1–4096. No GIF. |
| indexcrop | `indexcrop,x_100,i_0` | Slice by `x_` or `y_`, pick index `i_`. |
| blur | `blur,r_10,s_10` | r,s 1–50 (required). `g_face`/`g_faces`. |
| bright | `bright,50` | −100..100. |
| contrast | `contrast,50` | −100..100. |
| sharpen | `sharpen,100` | 50–399. |
| interlace | `interlace,1` | JPG only. |
| watermark | `watermark,text_hello,g_se,size_30` or `watermark,image_<full_pds_schema>` | Text watermark: pass raw text. Image watermark: pass the **full** `pds://` schema (see below). CLI base64-encodes both. Position `g_`, opacity `t_0..100`, ratio `p_1..100`. |
| segment | `segment` (auto) / `segment,prompt_kitten` / `segment,points_(x_,y_)` / `segment,boxes_(x_,y_,w_,h_)` | Extract subject; background becomes transparent (save as `.png`). Pass raw prompt text. |
| remove | `remove,points_(x_,y_)` / `remove,boxes_(x_,y_,w_,h_)` | Remove region; AI fills background. |

Combine freely — operations run left to right, e.g. `"crop,x_50,y_50,w_200,h_200" "resize,w_100" "sharpen,90"`.

---

## Examples

**Resize + sharpen + quality, then save-as (overwrite-safe new file):**
```bash
aliyun pds image-process \
  --drive-id 1020 --file-id <SRC_FILE_ID> \
  --operations "resize,w_400" "sharpen,80" "quality,Q_85" \
  --save-as true --target-drive-id 1020 --target-file-id <PARENT_FOLDER_ID> \
  --file-name test_combo.jpg
```

**Text-based segmentation ("person"), save as PNG:**
```bash
aliyun pds image-process \
  --drive-id 1020 --file-id <SRC_FILE_ID> \
  --operations "segment,prompt_person" \
  --save-as true --target-drive-id 1020 --target-file-id <PARENT_FOLDER_ID> \
  --file-name test_segment.png
```

**Remove a rectangular area:**
```bash
aliyun pds image-process \
  --drive-id 1020 --file-id <SRC_FILE_ID> \
  --operations "remove,boxes_(x_0,y_0,w_50,h_50)" \
  --save-as true --target-drive-id 1020 --target-file-id <PARENT_FOLDER_ID> \
  --file-name removed.jpg
```

**Preview the generated parameter only:**
```bash
aliyun pds image-process --operations "resize,w_200" "rotate,45" --dry-run true
# -> { "x_pds_process": "image/resize,w_200/rotate,45" }
```

**Text watermark (via operations):**
```bash
aliyun pds image-process \
  --drive-id 1020 --file-id <SRC_FILE_ID> \
  --operations "watermark,text_hello,g_se,size_30" \
  --save-as true --target-drive-id 1020 --target-file-id <PARENT_FOLDER_ID> \
  --file-name text_watermarked.png
```

---

## Error handling

| HTTP | Code | Meaning | Fix |
|------|------|---------|-----|
| 400 | InvalidParameter.xxx | Bad parameter | Read the CLI validation message; fix the operation. |
| 400 | OperationNotSupport | Feature not enabled | Ask PDS support to enable image editing. |
| 403 | ForbiddenNoPermission.xxx | No permission | Need `DownloadFile` on the source (and watermark) image, `CreateFile` on the save-as target. |

Local validation errors from `image-process` (e.g. `flip value "3" must be one of 0/1/2`) mean the request was **not** sent — just correct the operation and retry.

---

## Limits
- Image size ≤ 20 MB; formats: jpg, jpeg, bmp, png, heic, webp, tiff, avif.
- Save-as never modifies the source file — it always creates/updates the target.
