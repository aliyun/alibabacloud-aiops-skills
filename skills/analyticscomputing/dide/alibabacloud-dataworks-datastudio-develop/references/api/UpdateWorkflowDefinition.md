# update-workflow-definition

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/UpdateWorkflowDefinition/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Update Workflow

**aliyun CLI**:
```bash
aliyun dataworks-public update-workflow-definition \
  --project-id {{project_id}} \
  --id {{workflow_id}} \
  --spec "$(cat /tmp/wf.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
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
