# exec-pipeline-run-stage

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ExecPipelineRunStage/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

> ## ⚠️ Parameter Name — Common Mistake
>
> The pipeline-run identifier parameter is **`--id`**, NOT `--pipeline-run-id`.
>
> | ❌ WRONG | ✅ CORRECT |
> |----------|-----------|
> | `aliyun dataworks-public exec-pipeline-run-stage --pipeline-run-id <UUID> --code PROD_CHECK` | `aliyun dataworks-public exec-pipeline-run-stage --id <UUID> --code PROD_CHECK` |
>
> Calling with `--pipeline-run-id` returns `Error: --id is required` and exits non-zero.
>
> **Naming-convention inconsistency to memorize** (the CLI is not uniform across pipeline APIs):
>
> | API | Identifier flag |
> |---|---|
> | `exec-pipeline-run-stage` | `--id` |
> | `get-pipeline-run` | `--id` |
> | `abolish-pipeline-run` | `--id` |
> | `list-pipeline-run-items` | `--pipeline-run-id` |
>
> When in doubt, run `aliyun dataworks-public <command> --help`.

### Advance Pipeline Run Stage

**aliyun CLI**:
```bash
aliyun dataworks-public exec-pipeline-run-stage \
  --project-id {{project_id}} \
  --id {{pipeline_run_id}} \
  --code {{stage_code}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ExecPipelineRunStageRequest

# code: stage code, obtained from Stages[].Code in the get-pipeline-run response
# stages must be advanced in order; skipping stages is not allowed
# triggered asynchronously; continue polling to confirm the result
client.exec_pipeline_run_stage(ExecPipelineRunStageRequest(
    project_id={{project_id}},
    id='{{pipeline_run_id}}',
    code='{{stage_code}}'  # e.g., PROD_CHECK, PROD
))
```
