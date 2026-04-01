# GetComponent

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/GetComponent/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Get Component Details

**aliyun CLI**:
```bash
aliyun dataworks-public GetComponent \
  --ProjectId {{project_id}} \
  --Id {{component_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetComponentRequest

request = GetComponentRequest(
    project_id={{project_id}},
    id='{{component_id}}'
)
response = client.get_component(request)
print(response.body.spec)
```
