# EMO API (DashScope)

Official docs:
- EMO detect: `https://help.aliyun.com/zh/model-studio/emo-detect-api`
- EMO generate: `https://help.aliyun.com/zh/model-studio/emo-api`

## Auth and region

- Auth: `Authorization: Bearer $DASHSCOPE_API_KEY`
- Region: **Beijing** (`dashscope.aliyuncs.com`)
- Set header: `X-DashScope-Async: enable`

## 1) Portrait detection (required first)

`POST https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/face-detect`

Body:

```json
{
  "model": "emo-detect-v1",
  "input": {"image_url": "https://.../portrait.png"},
  "parameters": {"ratio": "1:1"}
}
```

Key success fields:

- `output.check_pass`
- `output.face_bbox`
- `output.ext_bbox`

## 2) Submit video generation

`POST https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/video-synthesis`

Body:

```json
{
  "model": "emo-v1",
  "input": {
    "image_url": "https://.../portrait.png",
    "audio_url": "https://.../speech.mp3",
    "face_bbox": [302,286,610,593],
    "ext_bbox": [71,9,840,778]
  },
  "parameters": {"style_level": "normal"}
}
```

Returns: `output.task_id`

## 3) Poll task

`GET https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}`

States: `PENDING` → `RUNNING` → `SUCCEEDED` / `FAILED`

On success:

- `output.results.video_url`

## Limits

- Image: min edge ≥ 400, max edge ≤ 7000
- Audio: wav/mp3, ≤ 15MB, ≤ 60 seconds
- URLs must be public http/https
