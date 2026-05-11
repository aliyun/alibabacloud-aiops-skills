# IMM Operations Parameter Reference

Detailed parameter specifications for image-intelligent (IMM) operations. These operations are powered by Alibaba Cloud IMM (Intelligent Media Management) and require IMM service activated with the OSS bucket bound to an IMM project.

## Table of Contents

- [blindwatermark-embed — Blind Watermark Embedding](#blindwatermark-embed--blind-watermark-embedding)
- [blindwatermark-extract — Blind Watermark Extraction](#blindwatermark-extract--blind-watermark-extraction)
- [faces — Face Detection](#faces--face-detection)
- [bodies — Body Detection](#bodies--body-detection)
- [cars — Car Detection](#cars--car-detection)
- [codes — QR/Barcode Recognition](#codes--qrbarcode-recognition)
- [labels — Image Labeling](#labels--image-labeling)
- [score — Image Quality Score](#score--image-quality-score)
- [IMM Chaining Rules](#imm-chaining-rules)

---

## blindwatermark-embed — Blind Watermark Embedding

Embed an invisible blind watermark into the image. The watermark text is not visible to the human eye but can be extracted later using `blindwatermark-extract`. This operation requires IMM service activated and bucket bound to an IMM project.

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | string | Watermark text to embed (plain text, auto Base64-encoded) |
| `s` | string | Watermark strength: `low`, `medium`, `high` (default: `low`) |

Higher strength makes the watermark more resistant to image transformations (crop, compression, etc.) but may slightly affect image quality.

`blindwatermark-embed` produces a new image and uses `process_object` with `sys/saveas`. It supports all three output modes (`url`, `download`, `save`). When chained with other operations, it must be the last operation.

**Examples:**

```
blindwatermark-embed:content=Copyright2024,s=high
blindwatermark-embed:content=MyBrand
```

---

## blindwatermark-extract — Blind Watermark Extraction

Extract blind watermark text from a previously watermarked image. This is an asynchronous operation that uses the IMM SDK to create a decode task and poll for results. Requires `--imm-project` or the `ALIBABA_CLOUD_IMM_PROJECT` environment variable.

| Parameter | Type | Description |
|-----------|------|-------------|
| `s` | string | Watermark strength used during embedding: `low`, `medium`, `high` |
| `model` | string | Watermark algorithm model: `FFT`, `FFT_FULL` (optional) |

This operation must be used alone — it cannot be chained with other operations. The result is returned as JSON containing the extracted watermark content and task ID.

**Examples:**

```
blindwatermark-extract:s=high
blindwatermark-extract:s=medium,model=FFT
```

---

## faces — Face Detection

Detect faces in the image and return their locations and attributes. Returns a JSON response. Requires IMM service. No parameters required.

**Example:**

```
faces
```

---

## bodies — Body Detection

Detect human bodies in the image and return their bounding boxes. Returns a JSON response. Requires IMM service. No parameters required.

**Example:**

```
bodies
```

---

## cars — Car Detection

Detect cars in the image and return their bounding boxes. Returns a JSON response. Requires IMM service. No parameters required.

**Example:**

```
cars
```

---

## codes — QR/Barcode Recognition

Recognize QR codes and barcodes in the image. Returns a JSON response with decoded content. Requires IMM service. No parameters required.

**Example:**

```
codes
```

---

## labels — Image Labeling

Generate descriptive labels/tags for the image content. Returns a JSON response with label names and confidence scores. Requires IMM service. No parameters required.

**Example:**

```
labels
```

---

## score — Image Quality Score

Evaluate the aesthetic/technical quality of the image. Returns a JSON response with a quality score. Requires IMM service. No parameters required.

**Example:**

```
score
```

---

## IMM Chaining Rules

- **`blindwatermark-embed`** can follow basic operations but must be the last operation in the chain (e.g., `resize:w=800` then `blindwatermark-embed:content=Test`).
- **`blindwatermark-extract`** must be used alone — no chaining.
- **AI detection operations** (`faces`, `bodies`, `cars`, `codes`, `labels`, `score`) must be used alone — they cannot be chained with basic, metadata, or watermark operations.

---

> Parameter specifications in this document are derived from the [Alibaba Cloud IMM documentation](https://help.aliyun.com/zh/imm/) and are reproduced here for quick reference.
