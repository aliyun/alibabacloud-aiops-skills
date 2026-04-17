# RAM permission policies

This skill needs the following RAM permissions for Alibaba Cloud services. Prefer a least-privilege RAM role or user for the application.

## Permission overview

| Service | Permission | Purpose | Scripts |
|------|------|------|---------|
| **DashScope API** | `AliyunDashScopeFullAccess` or custom policy | Call AI APIs (video, TTS, image) | All scripts |
| **OSS** | `AliyunOSSFullAccess` or bucket-scoped | Upload media and issue signed URLs | live_portrait.py, animate_anyone.py, image_to_video.py, portrait_animate.py |
| **LingMou** | `AliyunLingMouFullAccess` or custom policy | Digital-human template video | avatar_video.py |

## Details

### 1. DashScope API

**Service**: DashScope (Model Studio)  
**Regions**: cn-beijing (Beijing) / ap-southeast-1 (Singapore)  
**Example policy**:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dashscope:CallModel",
        "dashscope:GetTask",
        "dashscope:ListTasks"
      ],
      "Resource": "*"
    }
  ]
}
```

**Model APIs used**:
- `liveportrait` — LivePortrait talking head
- `liveportrait-detect` — portrait detection
- `emo-v1` — EMO talking head
- `emo-detect-v1` — EMO detection
- `animate-anyone-gen2` — AnimateAnyone video
- `animate-anyone-detect-gen2` — AA image detection
- `animate-anyone-template-gen2` — AA motion template
- `wan2.x-t2i` — Wan text-to-image
- `wan2.x-i2v` — Wan image-to-video
- `qwen3-tts-*` — Qwen real-time TTS

**Env**: `DASHSCOPE_API_KEY`

### 2. OSS

**Service**: Object Storage Service  
**Region**: cn-beijing or others  
**Example policy**:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:PutObject",
        "oss:GetObject",
        "oss:ListObjects"
      ],
      "Resource": [
        "acs:oss:*:*:your-bucket-name/human-avatar/*"
      ]
    }
  ]
}
```

**Usage**:
- Upload local images, audio, video to OSS
- Generate signed URLs for DashScope
- Example prefix: `human-avatar/`

**Env**:
- `ALIBABA_CLOUD_ACCESS_KEY_ID`
- `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
- `OSS_BUCKET`
- `OSS_ENDPOINT` (e.g. `oss-cn-beijing.aliyuncs.com`)

### 3. LingMou

**Service**: LingMou digital human  
**Region**: cn-beijing  
**Example policy**:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lingmou:ListBroadcastTemplates",
        "lingmou:GetBroadcastTemplate",
        "lingmou:CreateBroadcastVideoFromTemplate",
        "lingmou:ListBroadcastVideosById",
        "lingmou:ListPublicBroadcastSceneTemplates",
        "lingmou:CopyBroadcastSceneFromTemplate"
      ],
      "Resource": "*"
    }
  ]
}
```

**Usage**:
- List and inspect broadcast templates
- Create digital-human videos from templates
- Poll video job status
- Copy public templates

**Env**:
- `ALIBABA_CLOUD_ACCESS_KEY_ID`
- `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
- `LINGMOU_ENDPOINT` — optional, default `lingmou.cn-beijing.aliyuncs.com`
- `LINGMOU_REGION` — optional, default `cn-beijing`

## Minimal combined policy example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dashscope:CallModel",
        "dashscope:GetTask",
        "dashscope:ListTasks"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:PutObject",
        "oss:GetObject"
      ],
      "Resource": "acs:oss:*:*:your-bucket-name/human-avatar/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lingmou:ListBroadcastTemplates",
        "lingmou:GetBroadcastTemplate",
        "lingmou:CreateBroadcastVideoFromTemplate",
        "lingmou:ListBroadcastVideosById",
        "lingmou:ListPublicBroadcastSceneTemplates",
        "lingmou:CopyBroadcastSceneFromTemplate"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Security**:
> - Replace `your-bucket-name` with your real bucket name
> - Rotate AccessKeys regularly
> - Prefer RAM roles over root account keys
> - Grant only actions you need

## Checklist before deploy

- [ ] DashScope API key created and set in env
- [ ] OSS bucket exists and the key can write
- [ ] (Optional) LingMou enabled and permissions set
- [ ] All required env vars set
- [ ] Using RAM user/role, not root account

## Related docs

- [RAM overview](https://help.aliyun.com/zh/ram/product-overview/what-is-ram)
- [DashScope RAM](https://help.aliyun.com/zh/model-studio/ram-permission)
- [OSS authorization](https://help.aliyun.com/zh/oss/user-guide/authorization)
- [LingMou permissions](https://help.aliyun.com/zh/model-studio/lingmou)
