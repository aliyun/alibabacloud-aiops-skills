# DeleteComponent

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/DeleteComponent/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Delete Component

**aliyun CLI**:
```bash
aliyun dataworks-public DeleteComponent \
  --ProjectId {{project_id}} \
  --Id {{component_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import DeleteComponentRequest

request = DeleteComponentRequest(
    project_id={{project_id}},
    id='{{component_id}}'
)
client.delete_component(request)
```
