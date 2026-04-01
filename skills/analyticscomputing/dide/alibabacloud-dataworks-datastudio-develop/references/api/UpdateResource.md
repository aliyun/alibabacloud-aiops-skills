# UpdateResource

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/UpdateResource/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Update File Resource Information (Incremental Update)

**aliyun CLI**:
```bash
aliyun dataworks-public UpdateResource \
  --ProjectId {{project_id}} \
  --Id {{resource_id}} \
  --Spec "$(cat /tmp/res.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import UpdateResourceRequest

request = UpdateResourceRequest(
    project_id={{project_id}},
    id='{{resource_id}}',
    spec=spec
)
client.update_resource(request)
```
