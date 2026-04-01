# UpdateNode

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/UpdateNode/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Update Node

**Important**: Use incremental updates -- only send `id` + the fields to modify. Do not send unchanged fields like `datasource` or `runtimeResource` (the server may have corrected their values, and sending them back can cause errors).

**aliyun CLI**:
```bash
aliyun dataworks-public UpdateNode \
  --ProjectId {{project_id}} \
  --Id {{node_id}} \
  --Spec "$(cat /tmp/update_spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import UpdateNodeRequest
import json

# Incremental update: only send id and the fields to modify
update_spec = {
    "version": "2.0.0",
    "kind": "Node",
    "spec": {
        "nodes": [{
            "id": "{{node_id}}",
            "script": {
                "content": "new code content"
            }
        }]
    }
}

request = UpdateNodeRequest(
    project_id={{project_id}},
    id='{{node_id}}',
    spec=json.dumps(update_spec, ensure_ascii=False)
)
response = client.update_node(request)
```
