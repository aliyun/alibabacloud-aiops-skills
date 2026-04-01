# GetProject

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/GetProject/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Get Project Information (retrieve projectIdentifier via projectId)

**aliyun CLI**:
```bash
# Retrieve project details by projectId (numeric); ProjectName is the projectIdentifier
aliyun dataworks-public GetProject \
  --Id {{project_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Note**: `GetProject` only accepts the numeric `--Id` parameter; reverse lookup by projectIdentifier is not supported.

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetProjectRequest

request = GetProjectRequest(
    id={{project_id}}
)
response = client.get_project(request)
# ProjectName in the response is the projectIdentifier
```
