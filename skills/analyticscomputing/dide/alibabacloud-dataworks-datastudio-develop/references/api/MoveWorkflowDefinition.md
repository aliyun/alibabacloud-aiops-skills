# move-workflow-definition

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/MoveWorkflowDefinition/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Move Workflow to Target Path

**aliyun CLI**:
```bash
aliyun dataworks-public move-workflow-definition \
  --project-id {{project_id}} \
  --id {{workflow_id}} \
  --path {{target_path}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import MoveWorkflowDefinitionRequest

request = MoveWorkflowDefinitionRequest(
    project_id={{project_id}},
    id='{{workflow_id}}',
    path='{{target_path}}'
)
client.move_workflow_definition(request)
```
