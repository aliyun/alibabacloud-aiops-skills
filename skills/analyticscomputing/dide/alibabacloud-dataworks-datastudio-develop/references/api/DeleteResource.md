# DeleteResource

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/DeleteResource/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Delete File Resource

**aliyun CLI**:
```bash
aliyun dataworks-public DeleteResource \
  --ProjectId {{project_id}} \
  --Id {{resource_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import DeleteResourceRequest

request = DeleteResourceRequest(
    project_id={{project_id}},
    id='{{resource_id}}'
)
client.delete_resource(request)
```
