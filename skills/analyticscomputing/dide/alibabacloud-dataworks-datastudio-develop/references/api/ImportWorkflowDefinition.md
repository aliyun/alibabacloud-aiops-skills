# ImportWorkflowDefinition

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ImportWorkflowDefinition/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Import Workflow (including internal child nodes)

**aliyun CLI**:
```bash
# spec contains the workflow definition and all child node definitions
aliyun dataworks-public ImportWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Spec "$(cat /tmp/wf_with_nodes.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ImportWorkflowDefinitionRequest

request = ImportWorkflowDefinitionRequest(
    project_id={{project_id}},
    spec=spec
)
response = client.import_workflow_definition(request)
```
