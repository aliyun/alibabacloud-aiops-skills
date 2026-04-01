# CreateComponent

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/CreateComponent/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Idempotency Note

This API does not support `ClientToken`. If the call times out or returns a network error, **do not blindly retry**. First check whether the component was created by calling `ListComponents` and searching by name. Only retry if the component does not exist. Always record the `RequestId` from the response for traceability.

### Create Component

**aliyun CLI**:
```bash
aliyun dataworks-public CreateComponent \
  --ProjectId {{project_id}} \
  --Spec "$(cat /tmp/component.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreateComponentRequest

request = CreateComponentRequest(
    project_id={{project_id}},
    spec=spec
)
response = client.create_component(request)
print(f"ComponentId: {response.body.id}")
```
