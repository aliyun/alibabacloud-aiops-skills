# UpdateComponent

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/UpdateComponent/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Update Component

**aliyun CLI**:
```bash
aliyun dataworks-public UpdateComponent \
  --ProjectId {{project_id}} \
  --Id {{component_id}} \
  --Spec "$(cat /tmp/component.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import UpdateComponentRequest

request = UpdateComponentRequest(
    project_id={{project_id}},
    id='{{component_id}}',
    spec=spec
)
client.update_component(request)
```
