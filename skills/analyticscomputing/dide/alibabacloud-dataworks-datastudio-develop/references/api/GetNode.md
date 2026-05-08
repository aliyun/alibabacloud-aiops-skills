# get-node

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/GetNode/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Get Node Details

**aliyun CLI**:
```bash
aliyun dataworks-public get-node \
  --project-id {{project_id}} \
  --id {{node_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetNodeRequest

request = GetNodeRequest(
    project_id={{project_id}},
    id='{{node_id}}'
)
response = client.get_node(request)
# response.body.spec contains the full FlowSpec JSON
```
