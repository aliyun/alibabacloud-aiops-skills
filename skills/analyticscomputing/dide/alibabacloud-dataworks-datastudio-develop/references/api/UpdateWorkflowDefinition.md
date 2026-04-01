# UpdateWorkflowDefinition

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/UpdateWorkflowDefinition/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Update Workflow

**aliyun CLI**:
```bash
aliyun dataworks-public UpdateWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Id {{workflow_id}} \
  --Spec "$(cat /tmp/wf.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import UpdateWorkflowDefinitionRequest

request = UpdateWorkflowDefinitionRequest(
    project_id={{project_id}},
    id='{{workflow_id}}',
    spec=spec
)
client.update_workflow_definition(request)
```
