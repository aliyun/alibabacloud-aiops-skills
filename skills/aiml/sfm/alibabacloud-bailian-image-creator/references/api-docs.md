# DashScope API Documentation

## MultiModalConversation API

### Text-to-Image / Image Editing

**Endpoint**: `MultiModalConversation.call()`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_key` | string | Yes | DashScope API Key |
| `model` | string | Yes | Model name, e.g., `qwen-image-2.0-pro` |
| `messages` | list | Yes | Conversation message list |
| `result_format` | string | No | Return format, 'message' or 'completion' |
| `stream` | boolean | No | Whether to stream output, default False |
| `watermark` | boolean | No | Whether to add watermark, default False |
| `prompt_extend` | boolean | No | Whether to auto-optimize prompts, default False |
| `negative_prompt` | string | No | Negative prompt |
| `size` | string | No | Image size, e.g., '1024*1024' |
| `n` | integer | No | Number of generated images, 1-6 |

**Message Format**:

```python
messages = [
    {
        "role": "user",
        "content": [
            {"text": "Text content"},
            {"image": "Image URL or file:// local path"}
        ]
    }
]
```

---

## ImageGeneration API (Wanx)

**Endpoint**: `ImageGeneration.call()`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Model name, `wan2.7-image-pro` or `wan2.7-image` |
| `api_key` | string | Yes | DashScope API Key |
| `messages` | list | Yes | Message list, uses Message objects |
| `watermark` | boolean | No | Whether to add watermark |
| `n` | integer | No | Number of generated images (normal 1-4, series 1-12) |
| `enable_sequential` | boolean | No | Whether to enable series mode for coherent image sets |
| `thinking_mode` | boolean | No | Whether to enable thinking mode, default true |
| `size` | string | No | Image size: '1K', '2K' (default), '4K' (pro text-to-image only) |
| `color_palette` | string | No | Color style control |

**Message Object**:

```python
from dashscope.api_entities.dashscope_response import Message

message = Message(
    role="user",
    content=[
        {"text": "Text description"},
        {"image": "Image URL"}
    ]
)
```

---

## OpenAI Compatible Mode (Image Understanding)

**Endpoint**: `client.chat.completions.create()`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Model name, e.g., `qwen3.5-plus` |
| `messages` | list | Yes | Conversation message list |

**Message Format**:

```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": "Image URL"}
            },
            {"type": "text", "text": "Question text"}
        ]
    }
]
```

---

## Response Formats

### Qwen Series Success Response (200)

```python
{
    "output": {
        "choices": [
            {
                "message": {
                    "content": [
                        {"image": "Generated image URL"}
                    ]
                }
            }
        ]
    },
    "status_code": 200
}
```

### Wanx Series Success Response (200)

```python
{
    "output": {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "image", "image": "Generated image URL"}
                    ]
                }
            }
        ]
    },
    "status_code": 200
}
```

**Note**: Wanx response `content` items include a `"type": "image"` field. Use `content_item.get("type") == "image"` to check.

### Error Response

```python
{
    "status_code": "4xx/5xx",
    "code": "Error code",
    "message": "Error message"
}
```
