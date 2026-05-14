# DashScope Model List

## Text-to-Image Models

| Model Name | Description | Recommended Scenario |
|-----------|-------------|---------------------|
| `qwen-image-2.0-pro` | Qwen text-to-image pro version | High-quality image generation, supports complex scenes |
| `qwen-image-2.0` | Qwen text-to-image standard version | General image generation tasks |

**Supported Sizes**:
- `1024*1024` - Square
- `720*1280` - Portrait
- `1280*720` - Landscape
- `1440*720` - Widescreen
- `720*1440` - Tall portrait

---

## Image Editing Models

| Model Name | Description | Features |
|-----------|-------------|----------|
| `qwen-image-2.0-pro` | Qwen image editing | Supports 1-3 input images, 1-6 output images |
| `qwen-image-edit-max` | Qwen image editing enhanced | More precise editing control |
| `qwen-image-edit-plus` | Qwen image editing pro | Advanced editing features |

**Input**: 1-3 reference images
**Output**: 1-6 images (controlled via `n` parameter)

---

## Wanx Models

| Model Name | Description | Features |
|-----------|-------------|----------|
| `wan2.7-image-pro` | Wanx 2.7 pro version | Text-to-image supports 4K, editing/series up to 2K |
| `wan2.7-image` | Wanx 2.7 standard version | Faster generation, all scenarios up to 2K |

**Supported Sizes**:
- `1K` - Approx. 1024*1024
- `2K` - Approx. 2048*2048 (default)
- `4K` - Approx. 4096*4096 (pro text-to-image only)

**Supported Scenarios**:
- Text-to-image, image editing, multi-image reference, image series generation

---

## Image Understanding Models

| Model Name | Description | Recommended Scenario |
|-----------|-------------|---------------------|
| `qwen3.5-plus` | Qwen 3.5 enhanced | General image understanding, Q&A |
| `qwen-vl-max` | Qwen visual understanding max | Complex visual tasks |
| `qwen-vl-plus` | Qwen visual understanding plus | General visual tasks |

**Supported Features**:
- Image content description
- Image Q&A
- OCR text recognition
- Chart analysis
- Video understanding

---

## Model Selection Guide

### Text-to-Image
- **High quality**: `qwen-image-2.0-pro`
- **Fast generation**: `qwen-image-2.0`

### Image Editing
- **Complex editing**: `qwen-image-edit-max`
- **General editing**: `qwen-image-2.0-pro`

### Image Understanding
- **Complex analysis**: `qwen-vl-max` or `qwen3.5-plus`
- **General Q&A**: `qwen-vl-plus`

---

## Region Availability

| Region | Available Models | API Key |
|--------|-----------------|---------|
| Beijing (China) | All models | China mainland API Key |
| Singapore | Partial models | Singapore API Key |
| Virginia (US) | Partial models | US API Key |

**Note**: API Keys are not interchangeable between regions. Apply separately for each region.
