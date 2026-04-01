# ListNodes

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListNodes/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### List Nodes

**aliyun CLI**:
```bash
aliyun dataworks-public ListNodes \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListNodesRequest

request = ListNodesRequest(
    project_id={{project_id}},
    scene='DATAWORKS_PROJECT',
    page_number=1,
    page_size=100
)
response = client.list_nodes(request)
for node in response.body.paging_info.nodes:
    print(f"{node.id}: {node.name}")
```
