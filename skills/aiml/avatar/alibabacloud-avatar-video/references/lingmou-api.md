# LingMou API

Official docs:
- Create broadcast video from template:
  `https://help.aliyun.com/zh/avatar/avatar-application/developer-reference/api-lingmou-2025-05-27-createbroadcastvideofromtemplate`
- Batch query broadcast videos:
  `https://help.aliyun.com/zh/avatar/avatar-application/developer-reference/api-lingmou-2025-05-27-listbroadcastvideosbyid`
- Get broadcast template:
  `https://api.aliyun.com/api/LingMou/2025-05-27/GetBroadcastTemplate`
- List broadcast templates:
  `https://api.aliyun.com/api/LingMou/2025-05-27/ListBroadcastTemplates`

## Auth and region

- Auth: Alibaba Cloud AK/SK (OpenAPI signature)
- Region: `cn-beijing`
- Endpoint: `lingmou.cn-beijing.aliyuncs.com`
- API version: `2025-05-27`

## Verified flow (SDK 1.6.0 in test env)

1. Call `ListBroadcastTemplates` for existing templates.
2. If user did not specify `templateId`, pick one at random.
3. Call `GetBroadcastTemplate` for details and `variables`.
4. Choose a replaceable text variable (prefer `text_content`).
5. Call `CreateBroadcastVideoFromTemplate`.
6. Poll `ListBroadcastVideosById` with returned `id`.
7. When `status=SUCCESS`, read `videoURL`.

## New capabilities (verified with SDK 1.7.0 in venv)

Goals:

1. List public broadcast templates
2. Copy a public template into your account
3. Create video from the copied template

Intended workflow:

- `list broadcast template` first
- If templates exist: pick one at random
- If none: list public templates, copy up to 3, then pick one at random to create video

**Observed behavior**:

- `alibabacloud-lingmou20250527==1.7.0` adds:
  - `list_public_broadcast_scene_templates`
  - `copy_broadcast_scene_from_template`
- Both were called successfully in tests
- **Creating video immediately after copy is not guaranteed**; errors such as `100010031001-400` (“no valid segments”) can occur
- The new `BS...` id may list variables but still lack a complete renderable scene
- **Production strategy**:
  - **Prefer random selection among known-good account templates**
  - **Only when local templates are empty**, use public copy as fallback
  - If generation still fails, tell the user the template may need completion in LingMou

## Python SDK fields

### Version differences

- System Python had `1.6.0` without public-template APIs
- For public-template tests, use your venv’s Python, e.g.:

  ```bash
  .venv-human-avatar/bin/python scripts/avatar_video.py --list-public-templates
  ```

### ListBroadcastTemplates

Response includes:

- `data[].id`
- `data[].name`
- `data[].variables` (often empty or minimal in list response)

Example (test account):

```json
[
  {"id": "BS1vs5wAhH7OvW7btG1M6VxEQ", "name": "boy-01"},
  {"id": "BS1V_mn-IwR6uZTgxuiKoWdPw", "name": "girl-01"},
  {"id": "BS1JqkX1Dm4VGjseLKkPkpmiw", "name": "boy-02"},
  {"id": "BS1bR7OvVfFY2OkNEy591084A", "name": "girl-02"}
]
```

### GetBroadcastTemplate

Python SDK uses `template_id`, not `id`:

```python
req = lm.GetBroadcastTemplateRequest()
req.template_id = "BS1vs5wAhH7OvW7btG1M6VxEQ"
resp = client.get_broadcast_template(req)
```

Example response:

```json
{
  "id": "BS1vs5wAhH7OvW7btG1M6VxEQ",
  "name": "boy-01",
  "variables": [
    {
      "name": "text_content",
      "type": "text"
    }
  ]
}
```

## CreateBroadcastVideoFromTemplate (key payload)

```json
{
  "templateId": "BS1b2WNnRMu4ouRzT4clY9Jhg",
  "name": "Broadcast video test",
  "variables": [
    {
      "name": "text_content",
      "type": "text",
      "properties": {"content": "Script to read aloud"}
    }
  ],
  "videoOptions": {
    "resolution": "720p",
    "fps": 30,
    "watermark": true
  }
}
```

## ListBroadcastVideosById (key fields)

- `data[].status`: `SUCCESS` / `ERROR` / `PROCESSING` / …
- `data[].videoURL`
- `data[].captionURL`

## Variable types

- `text` — text
- `image` — image asset
- `avatar` — digital-human asset
- `voice` — voice asset

## Integration notes

- Do not require user-supplied `template_id` in chat
- If omitted, list templates and pick at random
- If no script was given, confirm script before generating
- If the user insists on “must use my uploaded photo for talking head”, steer to `LivePortrait` or `EMO`; template broadcast is a different path from image-driven lip-sync
