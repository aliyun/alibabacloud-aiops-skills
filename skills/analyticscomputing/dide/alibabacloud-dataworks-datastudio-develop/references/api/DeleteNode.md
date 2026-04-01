# DeleteNode

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/DeleteNode/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Delete Node

**aliyun CLI**:
```bash
aliyun dataworks-public DeleteNode \
  --ProjectId {{project_id}} \
  --Id {{node_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import DeleteNodeRequest

request = DeleteNodeRequest(
    project_id={{project_id}},
    id='{{node_id}}'
)
client.delete_node(request)
```
