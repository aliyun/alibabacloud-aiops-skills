# RenameNode

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/RenameNode/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Rename Node

**aliyun CLI**:
```bash
aliyun dataworks-public RenameNode \
  --ProjectId {{project_id}} \
  --Id {{node_id}} \
  --Name {{new_name}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import RenameNodeRequest

request = RenameNodeRequest(
    project_id={{project_id}},
    id='{{node_id}}',
    name='{{new_name}}'
)
client.rename_node(request)
```
