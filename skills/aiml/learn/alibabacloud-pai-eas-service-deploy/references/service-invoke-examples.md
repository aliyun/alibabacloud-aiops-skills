# Service Invocation Examples

PAI-EAS service invocation examples.

---

## Endpoint Formats

| Type | Format | Description |
|------|--------|-------------|
| Public | `http://{service_name}.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/{service_name}` | Public internet access |
| Internal | `http://{service_name}.gw-xxx-vpc.cn-hangzhou.pai-eas.aliyuncs.com/` | VPC internal access (faster and more stable) |

---

## Invocation Methods

### Method 1: HTTP Invocation (curl)

```bash
curl http://xxx.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/my_service \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, please introduce yourself"}'
```

### Method 2: OpenAI SDK Compatible Invocation

For vLLM, SGLang and other OpenAI API compatible images.

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://xxx.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/my_service/v1",
    api_key="xxx"  # Fill in if Token auth is configured, otherwise omit
)

response = client.chat.completions.create(
    model="/model_dir",  # Model mount path
    messages=[{"role": "user", "content": "Hello, please introduce yourself"}],
    max_tokens=100
)

print(response.choices[0].message.content)
```

### Method 3: Python requests

```python
import requests

url = "http://xxx.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/my_service"
headers = {"Content-Type": "application/json"}
data = {"input": "Hello, please introduce yourself"}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

### Method 4: Internal Network Invocation

Use internal endpoint within the same VPC for faster and more stable access:

```bash
curl http://xxx.gw-xxx-vpc.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/my_service \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello"}'
```

---

## Image-specific Endpoints

| Image Type | Endpoint | Description |
|-----------|----------|-------------|
| vLLM | `/v1/chat/completions` | OpenAI compatible API |
| SGLang | `/v1/chat/completions` | OpenAI compatible API |
| ComfyUI | `/prompt` | See image docs |
| SD WebUI | `/sdapi/v1/txt2img` | See image docs |
| Custom | `/` | Depends on implementation |

---

## Authentication

| Gateway Type | Authentication Method |
|-------------|----------------------|
| Shared Gateway | No auth by default, publicly accessible |
| ALB/NLB | Token auth can be configured, add `Authorization: Bearer <token>` header |

---

## vLLM Complete Example

```python
from openai import OpenAI

# Service endpoint
base_url = "http://my-service.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/my_service/v1"

client = OpenAI(
    base_url=base_url,
    api_key="your-token"  # Optional
)

# Chat completion
response = client.chat.completions.create(
    model="/model_dir",  # Model mount path
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Introduce Alibaba Cloud PAI-EAS"}
    ],
    temperature=0.7,
    max_tokens=500
)

print(response.choices[0].message.content)
```

---

## FAQ

**Q: Getting 404 response?**

A: Check service name and endpoint are correct, ensure service status is Running.

**Q: Getting 401 response?**

A: Check if Token auth is configured, add `Authorization: Bearer <token>` header.

**Q: Cannot access internal endpoint?**

A: Ensure the caller and service are in the same VPC.
