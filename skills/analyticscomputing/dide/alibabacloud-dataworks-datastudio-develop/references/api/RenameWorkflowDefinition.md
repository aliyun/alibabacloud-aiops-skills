# rename-workflow-definition

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/RenameWorkflowDefinition/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Rename Workflow

**aliyun CLI**:
```bash
aliyun dataworks-public rename-workflow-definition \
  --project-id {{project_id}} \
  --id {{workflow_id}} \
  --name {{new_name}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import RenameWorkflowDefinitionRequest

request = RenameWorkflowDefinitionRequest(
    project_id={{project_id}},
    id='{{workflow_id}}',
    name='{{new_name}}'
)
client.rename_workflow_definition(request)
```
