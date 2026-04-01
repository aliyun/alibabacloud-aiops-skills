# MoveFunction

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/MoveFunction/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Move Function to Target Path

**aliyun CLI**:
```bash
aliyun dataworks-public MoveFunction \
  --ProjectId {{project_id}} \
  --Id {{function_id}} \
  --Path {{target_path}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import MoveFunctionRequest

request = MoveFunctionRequest(
    project_id={{project_id}},
    id='{{function_id}}',
    path='{{target_path}}'
)
client.move_function(request)
```
