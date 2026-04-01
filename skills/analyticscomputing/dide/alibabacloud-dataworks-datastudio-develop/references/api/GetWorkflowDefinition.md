# GetWorkflowDefinition

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/GetWorkflowDefinition/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Get Workflow Details

**aliyun CLI**:
```bash
aliyun dataworks-public GetWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Id {{workflow_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetWorkflowDefinitionRequest

request = GetWorkflowDefinitionRequest(
    project_id={{project_id}},
    id='{{workflow_id}}'
)
response = client.get_workflow_definition(request)
```
