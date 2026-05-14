# DashScope Video API Reference

## API Endpoints

### Beijing Region
```
https://dashscope.aliyuncs.com/api/v1
```

### Virginia Region
```
https://dashscope-us.aliyuncs.com/api/v1
```

### Singapore Region
```
https://dashscope-intl.aliyuncs.com/api/v1
```

---

## Video Understanding

**Model**: `qwen3.5-plus`

**Function**: Analyze video content, supports uploading video URL with configurable frame extraction rate

**Request example (Python SDK)**:
```python
import dashscope
import os

dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

messages = [
    {"role": "user",
        "content": [
            # fps controls video frame extraction rate, extracts one frame every 1/fps seconds
            {"video": "https://example.com/video.mp4", "fps": 2},
            {"text": "What is the content of this video?"}
        ]
    }
]

response = dashscope.MultiModalConversation.call(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    model='qwen3.5-plus',
    messages=messages
)

print(response.output.choices[0].message.content[0]["text"])
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| video | string | Yes | Video URL (MP4 format) |
| fps | int | No | Frame extraction rate, default 2 (one frame every 0.5 seconds) |
| text | string | Yes | Analysis question or instruction |

**Notes**:
- Video must be a publicly accessible URL
- Recommended video duration: no longer than 5 minutes
- Higher fps = more frames extracted = more accurate analysis, but slower

---

## Text-to-Video

**Model**: `wan2.6-t2v`

**Request example**:
```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.6-t2v",
    "input": {
        "prompt": "A vision of future technology and nature in harmonious coexistence..."
    },
    "parameters": {
        "size": "1280*720",
        "shot_type": "multi",
        "duration": 10,
        "prompt_extend": true,
        "watermark": true,
        "seed": 12345
    }
}'
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | Yes | Video description text |
| size | string | No | Resolution, default "1280*720" |
| shot_type | string | No | "multi" for multi-shot mode |
| duration | int | No | Video duration (seconds) |
| prompt_extend | boolean | No | Smart prompt rewriting |
| watermark | boolean | No | Whether to add watermark |
| seed | int | No | Random seed |

**Official documentation**: https://help.aliyun.com/zh/model-studio/text-to-video-api-reference

---

## Image-to-Video

**Model**: `wan2.6-i2v-flash`

**Request example**:
```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.6-i2v-flash",
    "input": {
        "prompt": "An urban fantasy art scene...",
        "img_url": "https://example.com/image.png",
        "audio_url": "https://example.com/audio.mp3"
    },
    "parameters": {
        "resolution": "720P",
        "duration": 10,
        "prompt_extend": true,
        "watermark": false,
        "seed": 12345
    }
}'
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | Yes | Video description text |
| img_url | string | Yes | Reference image URL |
| audio_url | string | No | Audio URL |
| resolution | string | No | Resolution, default "720P" |
| duration | int | No | Video duration (seconds) |
| prompt_extend | boolean | No | Smart prompt rewriting |
| watermark | boolean | No | Whether to add watermark |

**Official documentation**: https://help.aliyun.com/zh/model-studio/image-to-video-api-reference

---

## Reference-to-Video

**Model**: `wan2.6-r2v-flash`

**Request example**:
```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.6-r2v-flash",
    "input": {
        "prompt": "Character2 is sitting on a chair by the window...",
        "reference_urls": [
            "https://example.com/role1.mp4",
            "https://example.com/role2.mp4",
            "https://example.com/object.png",
            "https://example.com/background.png"
        ]
    },
    "parameters": {
        "size": "1280*720",
        "duration": 10,
        "audio": true,
        "shot_type": "multi",
        "watermark": true
    }
}'
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | Yes | Video description, use Character1, Character2 etc. to reference materials |
| reference_urls | array | Yes | List of reference materials (video/image) |
| size | string | No | Resolution |
| duration | int | No | Video duration (seconds) |
| audio | boolean | No | Whether to generate audio |
| shot_type | string | No | "multi" for multi-shot mode |
| watermark | boolean | No | Whether to add watermark |

---

## Video Editing (Video Repainting)

**Model**: `wanx2.1-vace-plus`

**Request example**:
```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wanx2.1-vace-plus",
    "input": {
        "function": "video_repainting",
        "prompt": "The video shows a black steampunk-style car...",
        "video_url": "https://example.com/input.mp4"
    },
    "parameters": {
        "prompt_extend": false,
        "control_condition": "depth"
    }
}'
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| function | string | Yes | Fixed as "video_repainting" |
| prompt | string | Yes | Description of the repainted video |
| video_url | string | Yes | Input video URL (MP4, ≤50MB, ≤5 seconds) |
| control_condition | string | Yes | Feature extraction method |
| prompt_extend | boolean | No | Recommended to disable for video repainting |

**control_condition options**:
- `posebodyface`: Extract facial expressions and body movements
- `posebody`: Extract body movements only
- `depth`: Extract composition and motion contours (default)
- `scribble`: Extract line art structure

**Official documentation**: https://help.aliyun.com/zh/model-studio/wanx-vace-api-reference

---

## Video Region Edit

**Model**: `wanx2.1-vace-plus`

**Request example**:
```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wanx2.1-vace-plus",
    "input": {
        "function": "video_edit",
        "prompt": "The video shows a Parisian-style French cafe...",
        "video_url": "https://example.com/input.mp4",
        "mask_image_url": "https://example.com/mask.png",
        "mask_frame_id": 1
    },
    "parameters": {
        "prompt_extend": false,
        "mask_type": "tracking",
        "expand_ratio": 0.05
    }
}'
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| function | string | Yes | Fixed as "video_edit" |
| prompt | string | Yes | Description of the edited video |
| video_url | string | Yes | Original video URL |
| mask_image_url | string | No | Mask image URL (or mask_video_url, choose one) |
| mask_frame_id | int | No | Video frame index for the mask |
| mask_type | string | No | tracking (follow motion) or fixed (fixed position) |
| expand_ratio | float | No | Mask expansion ratio [0.0, 1.0] |

---

## Task Query

All video generation tasks are asynchronous. After creating a task, you need to poll the status.

**Query endpoint**:
```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY"
```

**Response example**:
```json
{
    "request_id": "xxx",
    "output": {
        "task_id": "xxx",
        "task_status": "SUCCEEDED",
        "video_url": "https://...",
        "submit_time": "2026-03-10 16:00:00",
        "end_time": "2026-03-10 16:02:00"
    }
}
```

**Task statuses**:
- `PENDING`: Task waiting
- `RUNNING`: Task executing
- `SUCCEEDED`: Task succeeded
- `FAILED`: Task failed
- `CANCELLED`: Task cancelled
