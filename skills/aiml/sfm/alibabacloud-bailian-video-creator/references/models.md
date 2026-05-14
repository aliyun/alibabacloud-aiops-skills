# DashScope Video Model List

## Video Understanding Model

| Model | Description | Input Limit | Frame Rate |
|-------|-------------|-------------|------------|
| qwen3.5-plus | Multimodal video content analysis | Recommended ≤5 minutes | Configurable (fps parameter) |

## Text-to-Video Model

| Model | Description | Max Duration | Resolution |
|-------|-------------|--------------|------------|
| wan2.6-t2v | Multi-shot video generation | 10 sec | 1280*720 |

## Image-to-Video Model

| Model | Description | Max Duration | Resolution |
|-------|-------------|--------------|------------|
| wan2.6-i2v-flash | Image + audio to video | 10 sec | 720P |

## Reference-to-Video Model

| Model | Description | Max Duration | Resolution |
|-------|-------------|--------------|------------|
| wan2.6-r2v-flash | Multi-reference material multi-character video | 10 sec | 1280*720 |

## Video Editing Model

| Model | Description | Input Limit |
|-------|-------------|-------------|
| wanx2.1-vace-plus | Video repainting / region edit | ≤50MB, ≤5 sec |

## Model Selection Guide

### Video Understanding (qwen3.5-plus)
- Use cases: Video content analysis, video Q&A, video summarization
- Features: Supports uploading video URL, configurable frame extraction rate
- Usage tips:
  - Higher fps = more accurate analysis, but slower
  - For long videos, reduce fps or process in segments
  - Supports custom analysis questions

### Text-to-Video (wan2.6-t2v)
- Use cases: MV production, story shorts, creative ads
- Features: Supports multi-shot transitions, automatic shot design
- Prompt tips: Clearly describe each shot's content and timing

### Image-to-Video (wan2.6-i2v-flash)
- Use cases: Image animation, character lip-sync
- Features: Supports audio-driven, preserves image subject features
- Prompt tips: Describe desired motion and atmosphere

### Reference-to-Video (wan2.6-r2v-flash)
- Use cases: Multi-character interaction, complex scenes
- Features: Supports multiple reference materials, precise character appearance control
- Prompt tips: Use Character1, Character2 etc. to reference materials

### Video Editing (wanx2.1-vace-plus)
- Use cases: Video style transfer, local modification
- Features: Preserves original video motion structure, supports fine-grained editing
- Control condition selection:
  - posebodyface: Preserve facial expressions and body movements
  - posebody: Preserve body movements only
  - depth: Preserve composition and contours (most commonly used)
  - scribble: Preserve line art edges

## Model Limitations

| Limitation | Value |
|------------|-------|
| Max video duration | 10 sec |
| Input video size | ≤50MB |
| Input video duration | ≤5 sec |
| Resolution | Max 1280*720 |

## Changelog

- 2026-03-10 17:35: Added qwen3.5-plus video understanding model
- 2026-03-10: Updated wan2.6 series model info
- 2026-03-10: Added wan2.6-r2v-flash reference-to-video model
