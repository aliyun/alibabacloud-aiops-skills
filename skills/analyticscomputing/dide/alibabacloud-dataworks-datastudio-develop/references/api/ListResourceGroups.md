# ListResourceGroups

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListResourceGroups/api.json

Query the list of resource groups in the project.

**aliyun CLI**:
```bash
aliyun dataworks-public ListResourceGroups \
  --ProjectId {{project_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListResourceGroupsRequest

response = client.list_resource_groups(ListResourceGroupsRequest(
    project_id={{project_id}}
))
# The response structure depends on the actual SDK version; use .to_map() to inspect
```
