# AA (AnimateAnyone Gen2) API reference

Official docs:
- Image detection: https://help.aliyun.com/zh/model-studio/animate-anyone-detect-api
- Motion template: https://help.aliyun.com/zh/model-studio/animate-anyone-template-api
- Video generation: https://help.aliyun.com/zh/model-studio/animateanyone-video-generation-api

## Important

- **Region is Beijing**: `dashscope.aliyuncs.com`; API key must be for Beijing.
- Three steps total: Step 1 sync; Steps 2/3 async (poll `task_id`).

---

## Three-step pipeline

```
Step 1: aa-detect     (sync)  → check_pass=true or error
Step 2: aa-template   (async)  → template_id
Step 3: aa-generate   (async)  → video_url
```

---

## Step 1: Image detection (sync)

```
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/aa-detect
```

| Field | Description |
|------|------|
| `model` | `animate-anyone-detect-gen2` |
| `input.image_url` | Public HTTP/HTTPS URL; jpg/jpeg/png/bmp; under 5MB; max edge ≤4096 |

Response:

```json
{
  "output": {
    "check_pass": true,
    "bodystyle": "full"
  }
}
```

(`bodystyle`: `"full"` = full body, `"half"` = half body.)

**Image requirements (to pass)**:
- Single person, front or near-front, no strong profile
- Clear face, no occlusion
- Full body or at least waist-up visible
- Simple background preferred

---

## Step 2: Motion template (async)

```
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/aa-template-generation/
Header: X-DashScope-Async: enable
```

| Field | Description |
|------|------|
| `model` | `animate-anyone-template-gen2` |
| `input.video_url` | Public URL; mp4/avi/mov; H.264/H.265; fps≥24; 2–60s; ≤200MB |

**Video requirements**:
- Full body in frame, single continuous shot, no hard cuts
- First frame facing camera
- Subject visible from first frame

Poll `GET /api/v1/tasks/{task_id}`:

```json
{
  "output": {
    "task_status": "SUCCEEDED",
    "template_id": "AACT.xxx.xxx-xxx.xxx"
  }
}
```

---

## Step 3: Video generation (async)

```
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/video-synthesis/
Header: X-DashScope-Async: enable
```

| Field | Description |
|------|------|
| `model` | `animate-anyone-gen2` |
| `input.image_url` | Image URL that passed Step 1 |
| `input.template_id` | `template_id` from Step 2 |
| `parameters.use_ref_img_bg` | `false` (default, video background) / `true` (image background) |
| `parameters.video_ratio` | `"9:16"` or `"3:4"` (only when `use_ref_img_bg=true`) |

Poll response:

```json
{
  "output": {
    "task_status": "SUCCEEDED",
    "video_url": "https://xxx/output.mp4"
  }
}
```

> ⚠️ `video_url` is valid for **24 hours** after success—download promptly.

---

## Format conversion (ffmpeg)

| Input | Unsupported | Target | Command |
|---------|----------|---------|---------|
| Image | webp, heic, tif, bmp | jpg | `ffmpeg -i input.webp -q:v 2 output.jpg` |
| Video | webm, mkv, flv, wmv | mp4 (H.264) | `ffmpeg -i input.webm -c:v libx264 -crf 22 -c:a aac output.mp4` |
| Video fps under 24 | — | 24 fps | `ffmpeg -i input.mp4 -vf fps=24 -c:v libx264 output.mp4` |

`animate_anyone.py` performs this automatically.

---

## Full examples

```bash
# Local files (convert + OSS)
python scripts/animate_anyone.py \
  --image ./portrait.jpg \
  --video ./dance.webm \
  --download --output result.mp4

# Existing URLs
python scripts/animate_anyone.py \
  --image-url "https://oss.../portrait.jpg?..." \
  --video-url "https://oss.../dance.mp4?..." \
  --download

# Existing template_id (skip Step 2)
python scripts/animate_anyone.py \
  --image ./portrait.jpg \
  --template-id "AACT.xxx.xxx" \
  --download

# Image as background
python scripts/animate_anyone.py \
  --image ./portrait.jpg --video ./dance.mp4 \
  --use-ref-img-bg --video-ratio 9:16 --download
```
