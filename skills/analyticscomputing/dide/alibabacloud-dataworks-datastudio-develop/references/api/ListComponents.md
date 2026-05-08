# list-components

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListComponents/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### List Components

**aliyun CLI**:
```bash
aliyun dataworks-public list-components \
  --project-id {{project_id}} \
  --page-number 1 \
  --page-size 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListComponentsRequest

request = ListComponentsRequest(
    project_id={{project_id}},
    page_number=1,
    page_size=100
)
response = client.list_components(request)
```
