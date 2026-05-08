# get-function

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/GetFunction/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Get Function Details

**aliyun CLI**:
```bash
aliyun dataworks-public get-function \
  --project-id {{project_id}} \
  --id {{function_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetFunctionRequest

request = GetFunctionRequest(
    project_id={{project_id}},
    id='{{function_id}}'
)
response = client.get_function(request)
print(response.body.spec)
```
