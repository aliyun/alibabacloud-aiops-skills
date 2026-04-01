# ListDataSources

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListDataSources/api.json

Query the list of data sources in the project.

**aliyun CLI**:
```bash
aliyun dataworks-public ListDataSources \
  --ProjectId {{project_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListDataSourcesRequest

response = client.list_data_sources(ListDataSourcesRequest(
    project_id={{project_id}}
))
# The response structure depends on the actual SDK version; use .to_map() to inspect
```
