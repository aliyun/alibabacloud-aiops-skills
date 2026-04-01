# UpdateFunction

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/UpdateFunction/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Update UDF Function Information (Incremental Update)

**aliyun CLI**:
```bash
aliyun dataworks-public UpdateFunction \
  --ProjectId {{project_id}} \
  --Id {{function_id}} \
  --Spec "$(cat /tmp/func.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import UpdateFunctionRequest

request = UpdateFunctionRequest(
    project_id={{project_id}},
    id='{{function_id}}',
    spec=spec
)
client.update_function(request)
```
