# RenameFunction

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/RenameFunction/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Rename Function

**aliyun CLI**:
```bash
aliyun dataworks-public RenameFunction \
  --ProjectId {{project_id}} \
  --Id {{function_id}} \
  --Name {{new_name}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import RenameFunctionRequest

request = RenameFunctionRequest(
    project_id={{project_id}},
    id='{{function_id}}',
    name='{{new_name}}'
)
client.rename_function(request)
```
