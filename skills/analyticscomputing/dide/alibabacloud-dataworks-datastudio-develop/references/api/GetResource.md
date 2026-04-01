# GetResource

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/GetResource/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Get File Resource Details

**aliyun CLI**:
```bash
aliyun dataworks-public GetResource \
  --ProjectId {{project_id}} \
  --Id {{resource_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetResourceRequest

request = GetResourceRequest(
    project_id={{project_id}},
    id='{{resource_id}}'
)
response = client.get_resource(request)
print(response.body.spec)
```
