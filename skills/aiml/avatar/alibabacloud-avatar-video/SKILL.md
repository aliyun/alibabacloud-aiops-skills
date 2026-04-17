---
name: alibabacloud-avatar-video
description: Use Alibaba Cloud DashScope API and LingMou to generate AI video and speech. Seven capabilities — (1) LivePortrait talking-head (image + audio → video, two-step), (2) EMO talking-head, (3) AA/AnimateAnyone full-body animation (three-step), (4) T2I text-to-image (Wan 2.x, default wan2.2-t2i-flash), (5) I2V image-to-video (Wan 2.x, default wan2.7-i2v-flash, supports T2I→I2V pipeline), (6) Qwen TTS (auto model/voice by scene, default qwen3-tts-vd-realtime-2026-01-15), (7) LingMou digital-human template video with random template, public-template copy, and script confirmation. Trigger when the user needs talking-head, portrait, full-body animation, text-to-image, text-to-video, or speech synthesis.
metadata:
  {
    "openclaw": {
      "emoji": "🎭",
      "requires": {
        "bins": ["ffmpeg", "ffprobe"],
        "env": [
          "DASHSCOPE_API_KEY",
          "ALIBABA_CLOUD_ACCESS_KEY_ID",
          "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
          "OSS_BUCKET",
          "OSS_ENDPOINT"
        ]
      }
    }
  }
---

# Human Avatar — Alibaba Cloud AI Video & Speech

## Capabilities overview

| Capability | Script | Model / API | Region | Summary |
|------|------|---------|--------|------|
| **LivePortrait** | `live_portrait.py` | `liveportrait` | cn-beijing | Portrait + audio/video → talking video, two steps |
| **EMO** | `portrait_animate.py` | `emo-v1` | cn-beijing | Portrait + audio → talking head, detect + generate |
| **AA** (AnimateAnyone) | `animate_anyone.py` | `animate-anyone-gen2` | cn-beijing | Full-body animation: detect → motion template → video |
| **T2I** | `text_to_image.py` | `wan2.x-t2i` | Multi-region | Text → image, default wan2.2-t2i-flash |
| **I2V** | `image_to_video.py` | `wan2.x-i2v` | Multi-region | Image → video; T2I→I2V pipeline supported; default wan2.7-i2v-flash |
| **Qwen TTS** | `qwen_tts.py` | `qwen3-tts-*` | cn-beijing / Singapore | Text → speech; auto model/voice by scene |
| **LingMou** | `avatar_video.py` | LingMou SDK | cn-beijing | Template-based digital-human broadcast video |

---

## Quick selection guide

```
Talking head (have audio/video already)     → LivePortrait
Talking head (no audio; synthesize first)   → Qwen TTS → LivePortrait
Full-body dance / motion                    → AA (AnimateAnyone)
Text → image                                → T2I (text_to_image)
Image → video                               → I2V (image_to_video)
Text → video end-to-end                     → T2I → I2V (image_to_video --t2i-prompt)
Enterprise digital human / template news    → LingMou (avatar_video)
```

---

## Environment setup

```bash
pip install requests==2.33.1 dashscope==1.25.15 oss2==2.19.1 numpy==1.26.4
# LingMou additionally:
pip install alibabacloud-lingmou20250527==1.7.0 alibabacloud-tea-openapi==0.4.4
```

```bash
export DASHSCOPE_API_KEY=sk-xxxx               # Beijing-region API key
export ALIBABA_CLOUD_ACCESS_KEY_ID=xxx         # OSS upload
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=xxx
export OSS_BUCKET=your-bucket
export OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
```

> ⚠️ API keys for `cn-beijing` and **Singapore are not interchangeable**; use the key for the correct region.  
> `OSS_ENDPOINT` may include or omit the `https://` prefix; scripts normalize it.

---

## 1. LivePortrait — talking-head video

**When to use**: You have a portrait photo + speech and want a talking-head video quickly.

**Flow**:
```
Step 1: liveportrait-detect (sync)  → pass=true
  ↓
Step 2: liveportrait        (async)  → video_url
```

**Image**: Single person, front-facing portrait, clear face, no occlusion  
**Audio**: wav/mp3, < 15MB, 1s–3min  
**Video input**: Audio extracted automatically (ffmpeg)

```bash
# Image + audio file
python scripts/live_portrait.py \
  --image ./portrait.jpg \
  --audio ./speech.mp3 \
  --template normal --download

# Image + video (extract audio)
python scripts/live_portrait.py \
  --image ./portrait.jpg \
  --video ./speech_video.mp4 \
  --template active --download

# Public URLs
python scripts/live_portrait.py \
  --image-url "https://..." \
  --audio-url "https://..." \
  --mouth-strength 1.2 --download
```

**Motion templates**:
- `normal` (default, moderate motion)
- `calm` (calm; news / storytelling)
- `active` (lively; singing / hosting)

---

## 2. Qwen TTS — text to speech

**When to use**: Generate speech files from text (for LivePortrait, EMO, etc.).

**Default model**: `qwen3-tts-vd-realtime-2026-01-15`

### Auto model selection by scene

| Scene `--scene` | Suggested model | Suggested voice |
|---------------|---------|---------|
| `default` / `brand` | `qwen3-tts-vd-realtime-2026-01-15` | Cherry |
| `news` / `documentary` / `advertising` | `qwen3-tts-instruct-flash-realtime` | Serena / Ethan |
| `audiobook` / `drama` | `qwen3-tts-instruct-flash-realtime` | Cherry / Dylan |
| `customer_service` / `chatbot` / `education` | `qwen3-tts-flash-realtime` | Anna / Ethan |
| `ecommerce` / `short_video` | `qwen3-tts-flash-realtime` | Cherry / Chelsie |

### Available voices

| Voice | Character |
|------|------|
| `Cherry` | Bright, sweet female; ads / audiobooks / dubbing |
| `Serena` | Mature, intellectual female; news / explainers / corporate |
| `Ethan` | Steady, warm male; education / documentary / training |
| `Dylan` | Expressive male; radio drama / game VO |
| `Anna` | Gentle, friendly female; support / assistant / daily |
| `Chelsie` | Young, fresh female; short video / e-commerce |
| `Thomas` | Deep, magnetic male; brand / ads |
| `Luna` | Warm, soft female; meditation / storytelling |

```bash
# Default (qwen3-tts-vd-realtime + Cherry)
python scripts/qwen_tts.py --text "Hello, welcome to Qwen TTS." --download

# Match by scene
python scripts/qwen_tts.py --text "Today's market..." --scene news --download
python scripts/qwen_tts.py --text "Once upon a time..." --scene audiobook --download

# Style via instructions
python scripts/qwen_tts.py \
  --text "Dear students..." \
  --model qwen3-tts-instruct-flash-realtime \
  --instructions "Warm tone, steady pace, suitable for teaching" \
  --download

# List options
python scripts/qwen_tts.py --list-voices
python scripts/qwen_tts.py --list-models
```

---

## 3. T2I — Wan 2.x text-to-image

**When to use**: Generate images from text (optionally feed into I2V).

```bash
# Default model (wan2.2-t2i-flash, fast)
python scripts/text_to_image.py \
  --prompt "A woman in Hanfu in a peach blossom forest, cinematic, 4K, soft light" \
  --size 960*1696 --download

# Higher quality
python scripts/text_to_image.py \
  --prompt "..." --model wan2.2-t2i-plus --size 1280*1280 --download

# Latest (Wan 2.6)
python scripts/text_to_image.py \
  --prompt "..." --model wan2.6-t2i --size 1280*1280 --n 1 --download
```

**Models**:
- `wan2.2-t2i-flash` (default, fast, good for tests)
- `wan2.2-t2i-plus` (higher quality)
- `wan2.6-t2i` (latest; more aspect ratios; sync call)

**Common sizes**: `1280*1280` (1:1) / `960*1696` (9:16) / `1696*960` (16:9)

---

## 4. I2V — Wan 2.x image-to-video

**When to use**: Turn an image into motion video; supports text-to-video via T2I first.

```bash
# Local image → video
python scripts/image_to_video.py \
  --image ./portrait.jpg \
  --prompt "She turns slowly and smiles; dress and petals drift gently" \
  --model wan2.7-i2v \
  --resolution 720P --duration 5 --download

# Pipeline: text → image → video
python scripts/image_to_video.py \
  --t2i-prompt "A woman in Hanfu in a peach blossom forest" \
  --prompt "She turns slowly; petals fall; poetic mood" \
  --download --output result.mp4

# With background music
python scripts/image_to_video.py \
  --image ./portrait.jpg \
  --audio-url "https://..." \
  --prompt "..." --download
```

**Models**:
- `wan2.7-i2v` (default; includes sound; 5s/10s)
- `wan2.5-i2v-preview` (high-quality preview)
- `wan2.2-i2v-plus` (no built-in audio; faster)

---

## 5. AA AnimateAnyone — full-body animation

**When to use**: Full-body photo + reference motion video → dance / motion video.

**Requirements**:
- Image: Single person, full body front, head to toe, aspect ratio 0.5–2.0
- Video: Full body in frame from first frame; mp4/avi/mov; fps ≥ 24; 2–60s

**Three steps**:
```
Step 1: animate-anyone-detect-gen2   (sync)  → check_pass=true
  ↓
Step 2: animate-anyone-template-gen2 (async)  → template_id (~3–5 min)
  ↓
Step 3: animate-anyone-gen2          (async)  → video_url (~3–5 min)
```

```bash
# Local files (auto convert + OSS upload)
python scripts/animate_anyone.py \
  --image ./portrait_fullbody.jpg \
  --video ./dance.mp4 \
  --download --output result.mp4

# Use image as background
python scripts/animate_anyone.py \
  --image ./portrait.jpg --video ./dance.mp4 \
  --use-ref-img-bg --video-ratio 9:16 --download

# Skip Step 2 (existing template_id)
python scripts/animate_anyone.py \
  --image ./portrait.jpg \
  --template-id "AACT.xxx.xxx" --download
```

> Auto conversion: video webm/mkv/flv → mp4; image webp/heic → jpg; if fps is under 24, normalize to 24 fps

---

## 6. EMO — talking head (legacy)

**Note**: Prefer LivePortrait; EMO suits cases that need stricter lip-sync.

```bash
python scripts/portrait_animate.py \
  --image ./portrait.jpg \
  --audio ./speech.mp3 \
  --download
```

---

## 7. LingMou — enterprise template video

**When to use**: Corporate digital-human news, template-based broadcasts, scripted reads with optional character images.

### New workflow (prefer no `template_id`)

- If the user **provides `template_id`**: use that template to generate.
- If **no `template_id`**:
  1. List existing broadcast templates for the account.
  2. If any exist, **pick one at random** for creation.
  3. If none, fetch public templates and **copy up to 3** into the account.
  4. Pick one at random from the copy results and continue.
- **Caveat**: After a public template is copied, the copy may not yet be a fully “ready-to-render” template; some copies are still drafts and may lack clips, assets, or variable bindings—complete them in LingMou.
- If the user only gives an image and “make a talking video” **without a script**: confirm the spoken copy before generating.

### What `scripts/avatar_video.py` supports

- `--list-templates`: list account templates
- `--list-public-templates`: list public templates (SDK 1.7.0+)
- `--copy-public-templates`: copy up to 3 public templates (SDK 1.7.0+)
- Omit `--template-id`: random existing template
- When local templates are empty: auto try public-template copy as fallback
- `--show-template-detail`: template detail and replaceable variables
- Fills input text into template text variables (prefers `text_content` / `test_text`)
- If generation fails right after copying a public template, surfaces a clear error that the template may still need completion (no silent failure)

```bash
# List templates
python scripts/avatar_video.py --list-templates

# Public templates (SDK 1.7.0+)
python scripts/avatar_video.py --list-public-templates

# Copy up to 3 public templates (SDK 1.7.0+)
python scripts/avatar_video.py --copy-public-templates

# No template_id — random existing template
python scripts/avatar_video.py \
  --text "Hello, welcome to today's tech news." \
  --download

# Specific template_id
python scripts/avatar_video.py \
  --template-id "BS1b2WNnRMu4ouRzT4clY9Jhg" \
  --text "Hello, welcome to today's tech news." \
  --download

# Detail for randomly chosen template
python scripts/avatar_video.py \
  --show-template-detail \
  --text "This is a test script for broadcast."
```

### Conversational usage

When the user says things like:
- “Make a talking video from this image”
- “Digital-human broadcast for me”
- “Upload image and make a news read”

Do this:
1. Check whether they already gave copy/script ready to read.
2. If not, ask: **“What is the exact script to read? You can give bullet points and I can turn them into broadcast-ready copy.”**
3. With script in hand, run LingMou: prefer random existing template; if none locally, try public copy.
4. If they uploaded a portrait but the template API does not use it, explain: this path is template-driven; for image-driven talking head, use LivePortrait or EMO.

---

## API reference links

- **LivePortrait**: https://help.aliyun.com/zh/model-studio/liveportrait-api
- **EMO** (emo-detect + emo-v1): [references/emo-api.md](references/emo-api.md)
- **AA** (Animate Anyone): [references/aa-api.md](references/aa-api.md)
- **T2I** (text-to-image v2): https://help.aliyun.com/zh/model-studio/text-to-image-v2-api-reference
- **I2V** (image-to-video): https://help.aliyun.com/zh/model-studio/image-to-video-api-reference/
- **Qwen TTS**: https://help.aliyun.com/zh/model-studio/qwen-tts-realtime
- **LingMou**: [references/lingmou-api.md](references/lingmou-api.md)
- **OSS upload**: [references/oss-upload.md](references/oss-upload.md)
