# ExecPipelineRunStage

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ExecPipelineRunStage/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Advance Pipeline Run Stage

**aliyun CLI**:
```bash
aliyun dataworks-public ExecPipelineRunStage \
  --ProjectId {{project_id}} \
  --Id {{pipeline_run_id}} \
  --Code {{stage_code}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ExecPipelineRunStageRequest

# code: stage code, obtained from Stages[].Code in the GetPipelineRun response
# stages must be advanced in order; skipping stages is not allowed
# triggered asynchronously; continue polling to confirm the result
client.exec_pipeline_run_stage(ExecPipelineRunStageRequest(
    project_id={{project_id}},
    id='{{pipeline_run_id}}',
    code='{{stage_code}}'  # e.g., PROD_CHECK, PROD
))
```
