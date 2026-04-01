# MoveNode

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/MoveNode/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Move Node Path

**aliyun CLI**:
```bash
aliyun dataworks-public MoveNode \
  --ProjectId {{project_id}} \
  --Id {{node_id}} \
  --Path {{target_path}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import MoveNodeRequest

request = MoveNodeRequest(
    project_id={{project_id}},
    id='{{node_id}}',
    path='{{target_path}}'
)
client.move_node(request)
```
