# CreatePipelineRun

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/CreatePipelineRun/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Idempotency Note

This API does not support `ClientToken`. If the call times out or returns a network error, **do not blindly retry**. First check whether a pipeline run was already created by calling `ListPipelineRuns` and filtering by the target object. Only retry if no matching active pipeline run exists. Always record the `RequestId` from the response for traceability.

### Create Pipeline Run (Publish / Deploy)

**aliyun CLI**:
```bash
aliyun dataworks-public CreatePipelineRun \
  --ProjectId {{project_id}} \
  --Type Online \
  --ObjectIds "[\"{{object_id}}\"]" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreatePipelineRunRequest

# type: Online (deploy) or Offline (undeploy)
# object_ids: only the first entity and its child entities will be processed
request = CreatePipelineRunRequest(
    project_id={{project_id}},
    type='Online',
    object_ids=['{{object_id}}']
)
response = client.create_pipeline_run(request)
run_id = response.body.id
print(f"PipelineRunId: {run_id}")
```
