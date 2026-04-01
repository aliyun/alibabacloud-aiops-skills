# CreateFunction

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/CreateFunction/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Idempotency Note

This API does not support `ClientToken`. If the call times out or returns a network error, **do not blindly retry**. First check whether the function was created by calling `ListFunctions` and searching by name. Only retry if the function does not exist. Always record the `RequestId` from the response for traceability.

### Create Function

**aliyun CLI**:
```bash
# Build spec JSON (replace placeholders in spec.json with actual values, embed function definition content)
aliyun dataworks-public CreateFunction \
  --ProjectId {{project_id}} \
  --Spec "$(cat /tmp/func.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreateFunctionRequest

request = CreateFunctionRequest(
    project_id={{project_id}},
    spec=spec
)
response = client.create_function(request)
print(f"FunctionId: {response.body.id}")
```
