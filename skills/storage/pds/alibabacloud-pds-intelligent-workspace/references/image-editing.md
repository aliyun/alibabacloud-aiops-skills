# PDS Image Editing Guide

**Scenario**: Already obtained drive_id, file_id, revision_id, need to perform image editing operations

**Purpose**: Edit images through the Process interface, including scaling, cropping, rotation, segmentation, removal, watermark and other features, and save the results to PDS

---

## Image Editing Capabilities Overview

PDS image editing capabilities are implemented through `x-pds-process=image/xxx`, supporting basic image processing such as scaling, cropping, rotation, as well as AI image processing such as segmentation and removal.

| Parameter | Description | Reference Link                                                                                                                                   |
|------|------|----------------------------------------------------------------------------------------------------------------------------------------|
| resize | Scale image to specified size | [resize documentation](https://help.aliyun.com/zh/oss/user-guide/resize-images-4)       |
| watermark | Add text or image watermark to image | [watermark documentation](https://help.aliyun.com/zh/oss/user-guide/add-watermarks) |
| crop | Crop rectangular image of specified size | [crop documentation](https://help.aliyun.com/zh/oss/user-guide/custom-crop)           |
| quality | Adjust quality of JPEG and WebP format images | [quality documentation](https://help.aliyun.com/zh/oss/user-guide/adjust-image-quality)     |
| format | Convert image format | [format documentation](https://help.aliyun.com/zh/oss/user-guide/convert-image-formats-2)                                                                        |
| auto-orient | Auto-rotate images with rotation parameters | [auto-orient documentation](https://help.aliyun.com/zh/oss/user-guide/auto-rotate-4)                                                              |
| circle | Crop circular image with specified size centered on image | [circle documentation](https://help.aliyun.com/zh/oss/user-guide/circle-crop)                                                                        |
| indexcrop | Slice image by position on x or y axis, then select one image | [indexcrop documentation](https://help.aliyun.com/zh/oss/user-guide/indexed-slice)                                                                  |
| rounded-corners | Crop image into rounded rectangle with specified corner radius | [rounded-corners documentation](https://help.aliyun.com/zh/oss/user-guide/rounded-rectangle-4)                                                      |
| blur | Apply blur effect to image | [blur documentation](https://help.aliyun.com/zh/oss/user-guide/blur)                                                                            |
| rotate | Rotate image clockwise by specified angle | [rotate documentation](https://help.aliyun.com/zh/oss/user-guide/rotate)                                                                        |
| interlace | Adjust JPG images to progressive display | [interlace documentation](https://help.aliyun.com/zh/oss/user-guide/gradual-display)                                                                  |
| bright | Adjust image brightness | [bright documentation](https://help.aliyun.com/zh/oss/user-guide/brightness)                                                                        |
| sharpen | Sharpen image | [sharpen documentation](https://help.aliyun.com/zh/oss/user-guide/sharpen)                                                                      |
| contrast | Adjust image contrast | [contrast documentation](https://help.aliyun.com/zh/oss/user-guide/contrast)                                                                    |
| flip | Flip image | [flip documentation](https://help.aliyun.com/zh/oss/user-guide/flip-image)                                                                            |
| segment | Perform image segmentation | See below                                                                                                                                    |
| remove | Perform image removal | See below                                                                                                                                    |

### Basic Image Processing

Basic image processing capabilities are provided by OSS. For detailed parameters and usage of each feature, please refer to the reference links in the overview table.

For image watermarks in watermark processing, the watermark image's pds_schema format is required, i.e., `pds://domains/{domain_id}/drives/{drive_id}/files/{file_id}/revisions/{revision_id}`, which needs to be URL-safe base64 encoded before use.

### Watermark Processing

#### Image Watermark

| Feature | Parameter Format | Description |
|------|---------|------|
| **Image Watermark** | `image/watermark,image_{base64(pds_schema)}` | Add image watermark, watermark image must exist in PDS |
| **Watermark Position** | `image/watermark,image_{...},g_{position}` | Specify watermark position: nw(top-left), north(top-center), ne(top-right), west(left-center), center(center), east(right-center), sw(bottom-left), south(bottom-center), se(bottom-right) |
| **Watermark Transparency** | `image/watermark,image_{...},t_{transparency}` | Set watermark transparency, 0-100, 100 means completely opaque |
| **Watermark Ratio** | `image/watermark,image_{...},p_{percent}` | Watermark percentage of original image, 1-100 |
| **Watermark Horizontal Offset** | `image/watermark,image_{...},x_{offset}` | Watermark horizontal offset distance, unit: pixels |
| **Watermark Vertical Offset** | `image/watermark,image_{...},y_{offset}` | Watermark vertical offset distance, unit: pixels |
| **Watermark Tiling** | `image/watermark,image_{...},repeat_1` | Tile watermark across entire image |


> **Watermark image pds_schema format**: `pds://domains/{domain_id}/drives/{drive_id}/files/{file_id}/revisions/{revision_id}`
>
> The pds_schema needs to be URL-safe base64 encoded before use.

### AI Image Processing

| Feature | Parameter Format | Description |
|------|---------|------|
| **Auto Segmentation** | `image/segment` | Automatically identify and extract the main subject from the image |
| **Point-based Segmentation** | `image/segment,points_(x_{x},y_{y})` | Extract subject at specified coordinate point, x is distance from left edge (px), y is distance from top edge (px) |
| **Rectangle Segmentation** | `image/segment,boxes_(x_{x},y_{y},w_{w},h_{h})` | Extract rectangular area, x,y are starting coordinates, w is width, h is height |
| **Text-based Segmentation** | `image/segment,prompt_{base64(prompt)}` | Segment based on text description, prompt is text description (e.g., "kitten"), needs base64 encoding |
| **Point-based Removal** | `image/remove,points_(x_{x},y_{y})` | Remove content at specified coordinate point |
| **Rectangle Removal** | `image/remove,boxes_(x_{x},y_{y},w_{w},h_{h})` | Remove rectangular area |

### Feature Combination

Multiple image editing capabilities can be combined, separated by `/`, executed from left to right in order:

**Note**: Only the first operation needs the `image/` prefix, subsequent operations can be written directly without the prefix.

```
image/crop,x_50,y_50,w_200,h_200/resize,w_100/sharpen,90
image/rotate,90/resize,p_150
```

---

## Core Workflow

### Image Editing and Save-as

Save edited image to specified PDS location.

#### Step 1: Construct x-pds-process parameter and save to variable

**Important**: Since x-pds-process parameter contains base64 encoding (which may include special characters like `=`), parameters must be passed using variables to avoid shell parsing errors from direct hardcoding.

```bash
# Generate parameter and save to variable
X_PDS_PROCESS=$(python scripts/render_image_editing_process.py \
  --operations "image/resize,w_200" \
  --saveas \
  --target-domain-id ${TARGET_DOMAIN_ID} \
  --target-drive-id ${TARGET_DRIVE_ID} \
  --target-file-id ${TARGET_FILE_ID} \
  --target-revision-id ${TARGET_REVISION_ID} \
  --file-name "edited_image.jpg")
```

**Save-as Parameter Description**:
- `--saveas`: Enable save-as functionality
- `--target-domain-id`: domain_id of the save-as target (required)
- `--target-drive-id`: drive_id of the save-as target (required)
- `--target-file-id`: target file ID or parent folder ID (required)
- `--target-revision-id`: target version ID (required when overwriting existing file, leave empty when creating new file)
- `--file-name`: saved file name (required)

#### Step 2: Execute save-as request

```bash
aliyun pds process \
  --resource-type file \
  --drive-id ${SOURCE_DRIVE_ID} \
  --file-id ${SOURCE_FILE_ID} \
  --x-pds-process "${X_PDS_PROCESS}" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Response** (HTTP 200):
```json
{
  "drive_id": "drive_id of saved file",
  "file_id": "file_id of saved file",
  "revision_id": "revision_id of saved file version"
}
```

---

## Common Scenario Examples

### Scenario 1: Image Scaling and Save-as

```bash
# Scale to width 200px, height adjusted proportionally, and save-as
python scripts/render_image_editing_process.py \
  --operations "image/resize,w_200" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "resized_image.jpg"

# Scale to height 200px, width adjusted proportionally, and save-as
python scripts/render_image_editing_process.py \
  --operations "image/resize,h_200" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "resized_image.jpg"

# Limit maximum width and height, and save-as
python scripts/render_image_editing_process.py \
  --operations "image/resize,l_200" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "resized_image.jpg"
```

### Scenario 2: Image Rotation and Save-as

```bash
# Rotate 90 degrees and save-as
python scripts/render_image_editing_process.py \
  --operations "image/rotate,90" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "rotated_image.jpg"

# Auto-orient (based on EXIF information) and save-as
python scripts/render_image_editing_process.py \
  --operations "image/auto-orient,1" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "auto_oriented_image.jpg"
```

### Scenario 3: Auto Segmentation and Save-as

```bash
# Automatically identify and extract subject, and save-as
python scripts/render_image_editing_process.py \
  --operations "image/segment" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "segmented_image.png"
```

### Scenario 4: Rectangle Segmentation and Save-as

```bash
# Extract top-left 100x100 area, and save-as
python scripts/render_image_editing_process.py \
  --operations "image/segment,boxes_(x_0,y_0,w_100,h_100)" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "cropped_image.png"
```

### Scenario 5: Text-based Segmentation and Save-as

```bash
# Segment by text description, and save-as
python scripts/render_image_editing_process.py \
  --operations "image/segment,prompt_5bCP5aqr" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "segmented_cat.png"
```

> Note: prompt parameter needs to be base64 encoded first, for example "小猫" (kitten) base64 encoding is "5bCP5aqr"

### Scenario 6: Rectangle Area Removal and Save-as

```bash
# Remove top-left 50x50 area, and save-as
python scripts/render_image_editing_process.py \
  --operations "image/remove,boxes_(x_0,y_0,w_50,h_50)" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "removed_image.jpg"
```

### Scenario 7: Combined Operations and Save-as

```bash
# Scale first then rotate, and save-as
python scripts/render_image_editing_process.py \
  --operations "image/resize,w_200" "rotate,45" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "processed_image.jpg"

# Scale + sharpen + quality adjustment, and save-as
python scripts/render_image_editing_process.py \
  --operations "image/resize,w_200" "sharpen,100" "quality,q_80" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id" \
  --file-name "processed_image.jpg"

```

### Scenario 8: Edit and Save-as

```bash
# Scale image and save-as to specified location
python scripts/render_image_editing_process.py \
  --operations "image/resize,w_200" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "parent_folder_id_123" \
  --file-name "resized_image.jpg"

# Overwrite existing file
python scripts/render_image_editing_process.py \
  --operations "image/resize,w_200" \
  --saveas \
  --target-domain-id "bj31216" \
  --target-drive-id "1020" \
  --target-file-id "existing_file_id_456" \
  --target-revision-id "revision_789" \
  --file-name "resized_image.jpg"
```

---

## Error Handling

| HTTP Status Code | Error Code | Description | Solution |
|------------|--------|------|---------|
| 400 | InvalidParameter.xxx | Invalid parameter | Check parameter format and encoding |
| 400 | OperationNotSupport | Feature not enabled | Contact PDS technical support to enable feature |
| 403 | ForbiddenNoPermission.xxx | No permission | Check AccessToken permissions |

### Common Errors

#### 1. Feature Not Enabled

```json
{
  "code": "OperationNotSupport",
  "message": "This operation is not supported."
}
```

**Solution**: Contact PDS technical support to enable image editing functionality.

#### 2. Insufficient Permissions

```json
{
  "code": "ForbiddenNoPermission.file",
  "message": "No Permission to access resource file"
}
```

**Solution**:
- Ensure current user has `DownloadFile` permission for source image
- Ensure current user has `DownloadFile` permission for watermark image
- Ensure current user has `CreateFile` permission for save-as target location

#### 3. Invalid Parameter (InvalidParameter.XPdsProcess)

```json
{
  "code": "InvalidParameter.XPdsProcess",
  "message": "The input parameter x-pds-process is not valid."
}
```

**Common Causes**:
- Directly hardcoding x-pds-process parameter in command line, special characters like `=` in base64 encoding are incorrectly parsed by shell
- Parameter contains invisible characters (such as line breaks)

**Solution**:
- **Use variable to pass parameter** (recommended):
  ```bash
  X_PDS_PROCESS=$(python scripts/render_image_editing_process.py \
    --operations "image/resize,h_150" \
    --saveas \
    --target-domain-id "bj31216" \
    --target-drive-id "101" \
    --target-file-id "folder_id" \
    --file-name "output.png")
  
  aliyun pds process \
    --resource-type file \
    --drive-id "101" \
    --file-id "source_file_id" \
    --x-pds-process "${X_PDS_PROCESS}" \
    --user-agent AlibabaCloud-Agent-Skills
  ```
- Ensure there are no extra spaces or line breaks in the parameter
- Check if base64 encoding is correct

---

## Best Practices

### 1. Operation Order Optimization

Image editing operations are executed from left to right.合理安排顺序可以提高处理效率:
- Crop first then scale: reduces data volume for subsequent processing
- Rotate first then crop: avoids coordinate changes after rotation

### 2. Coordinate Determination

Before using point-based or rectangle operations, it is recommended to obtain image dimensions first to ensure coordinate values are within valid range.


---

## FAQ

**Q: How to get image dimension information?**

A: You can use `aliyun pds get-file` command to get file information, the returned data includes image width and height information.
```bash
aliyun pds get-file \
  --drive-id <drive_id> \
  --file-id <file_id> \
  --user-agent AlibabaCloud-Agent-Skills
```

response example:
```json
{
  "file_id": "5d79206586bb5dd69fb34c349282718146c55da7",
  "name": "example.jpg",
  "image_media_metadata": 
    {
      "width": 1920,
      "height": 1080
    }
}
```


**Q: What is the difference between segmentation and removal operations?**

A: 
- **Segmentation (segment)**: Extract the main subject from the image, background becomes transparent
- **Removal (remove)**: Remove content from specified area in the image, AI automatically fills the background

**Q: What is the execution order when multiple operations are combined?**

A: Operations are executed from left to right in the order they appear in x-pds-process.


**Q: Will save-as operation modify the source file?**

A: No, save-as operation creates a new file, the source file remains unchanged.

---

## Image Limitations
- **Size Limit**: Only supports images within 20MB
- **Format Limit**: Only supports the following formats
  - jpg, jpeg, bmp, png, heic, webp, tiff, avif

## Permission Requirements
- Need `DownloadFile` permission for the image being edited
- Need `DownloadFile` permission for watermark images
- Need `CreateFile` permission for save-as target location

---
