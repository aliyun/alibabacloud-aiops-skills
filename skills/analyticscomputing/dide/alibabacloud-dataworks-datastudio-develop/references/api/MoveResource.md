# move-resource

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/MoveResource/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Move File Resource to Target Directory

**aliyun CLI**:
```bash
aliyun dataworks-public move-resource \
  --project-id {{project_id}} \
  --id {{resource_id}} \
  --path {{target_path}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import MoveResourceRequest

request = MoveResourceRequest(
    project_id={{project_id}},
    id='{{resource_id}}',
    path='{{target_path}}'
)
client.move_resource(request)
```
