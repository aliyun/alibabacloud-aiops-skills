# ListNodeDependencies

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListNodeDependencies/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### List Node Dependencies

**aliyun CLI**:
```bash
aliyun dataworks-public ListNodeDependencies \
  --ProjectId {{project_id}} \
  --Id {{node_id}} \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListNodeDependenciesRequest

request = ListNodeDependenciesRequest(
    project_id={{project_id}},
    id='{{node_id}}',
    page_number=1,
    page_size=100
)
response = client.list_node_dependencies(request)
```
