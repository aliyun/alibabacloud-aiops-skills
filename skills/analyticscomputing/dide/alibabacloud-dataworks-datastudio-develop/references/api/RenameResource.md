# RenameResource

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/RenameResource/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Rename File Resource

**aliyun CLI**:
```bash
aliyun dataworks-public RenameResource \
  --ProjectId {{project_id}} \
  --Id {{resource_id}} \
  --Name {{new_name}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import RenameResourceRequest

request = RenameResourceRequest(
    project_id={{project_id}},
    id='{{resource_id}}',
    name='{{new_name}}'
)
client.rename_resource(request)
```
