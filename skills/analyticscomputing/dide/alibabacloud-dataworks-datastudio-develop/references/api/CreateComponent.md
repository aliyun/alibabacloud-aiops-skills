# create-component

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/CreateComponent/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Idempotency Note

This API does not support `ClientToken`. If the call times out or returns a network error, **do not blindly retry**. First check whether the component was created by calling `list-components` and searching by name. Only retry if the component does not exist. Always record the `RequestId` from the response for traceability.

### Create Component

**aliyun CLI**:
```bash
aliyun dataworks-public create-component \
  --project-id {{project_id}} \
  --spec "$(cat /tmp/component.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
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
