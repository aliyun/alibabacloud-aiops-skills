# CreateWorkflowDefinition

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/CreateWorkflowDefinition/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Idempotency Note

This API does not support `ClientToken`. If the call times out or returns a network error, **do not blindly retry**. First check whether the workflow was created by calling `ListWorkflowDefinitions` and searching by name. Only retry if the workflow does not exist. Always record the `RequestId` from the response for traceability.

### Create Workflow

The workflow spec must include `script.runtime.command: "WORKFLOW"`, otherwise the creation will fail. The correct spec format is as follows:

```json
{
  "version": "2.0.0",
  "kind": "CycleWorkflow",
  "spec": {
    "workflows": [{
      "name": "my_workflow",
      "script": {
        "path": "my_workflow",
        "runtime": {"command": "WORKFLOW"}
      },
      "trigger": {
        "type": "Scheduler",
        "cron": "00 00 02 * * ?",
        "startTime": "1970-01-01 00:00:00",
        "endTime": "9999-01-01 00:00:00",
        "timezone": "Asia/Shanghai"
      }
    }]
  }
}
```

**Prerequisite**: Use build.py to merge the three files (a workflow directory typically only has spec.json + properties, no code file):
```bash
python $SKILL/scripts/build.py ./my_workflow > /tmp/wf.json
```

**aliyun CLI**:
```bash
aliyun dataworks-public CreateWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Spec "$(cat /tmp/wf.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreateWorkflowDefinitionRequest

with open('/tmp/wf.json') as f:
    spec = f.read()

request = CreateWorkflowDefinitionRequest(
    project_id={{project_id}},
    spec=spec
)
response = client.create_workflow_definition(request)
print(f"WorkflowId: {response.body.id}")
```
