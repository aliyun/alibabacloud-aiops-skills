# ListWorkflowDefinitions

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListWorkflowDefinitions/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### List Workflows

**aliyun CLI**:
```bash
aliyun dataworks-public ListWorkflowDefinitions \
  --ProjectId {{project_id}} \
  --Type CycleWorkflow \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListWorkflowDefinitionsRequest

request = ListWorkflowDefinitionsRequest(
    project_id={{project_id}},
    type='CycleWorkflow',
    page_number=1,
    page_size=100
)
response = client.list_workflow_definitions(request)
```

## File Resource Operations
