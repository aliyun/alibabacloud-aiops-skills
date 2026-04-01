# DeleteFunction

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/DeleteFunction/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Delete UDF Function

**aliyun CLI**:
```bash
aliyun dataworks-public DeleteFunction \
  --ProjectId {{project_id}} \
  --Id {{function_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import DeleteFunctionRequest

request = DeleteFunctionRequest(
    project_id={{project_id}},
    id='{{function_id}}'
)
client.delete_function(request)
```
