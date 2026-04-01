# DeleteWorkflowDefinition

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/DeleteWorkflowDefinition/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Delete Workflow

**aliyun CLI**:
```bash
aliyun dataworks-public DeleteWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Id {{workflow_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import DeleteWorkflowDefinitionRequest

request = DeleteWorkflowDefinitionRequest(
    project_id={{project_id}},
    id='{{workflow_id}}'
)
client.delete_workflow_definition(request)
```
