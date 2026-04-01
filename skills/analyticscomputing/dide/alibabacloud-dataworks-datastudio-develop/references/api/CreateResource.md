# CreateResource

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/CreateResource/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Idempotency Note

This API does not support `ClientToken`. If the call times out or returns a network error, **do not blindly retry**. First check whether the resource was created by calling `ListResources` and searching by name. Only retry if the resource does not exist. Always record the `RequestId` from the response for traceability.

### Create Resource

**aliyun CLI**:
```bash
# Build spec JSON (replace placeholders in spec.json with actual values, embed resource file content)
aliyun dataworks-public CreateResource \
  --ProjectId {{project_id}} \
  --Spec "$(cat /tmp/res.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreateResourceRequest

request = CreateResourceRequest(
    project_id={{project_id}},
    spec=spec
)
response = client.create_resource(request)
print(f"ResourceId: {response.body.id}")
```
