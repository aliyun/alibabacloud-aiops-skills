# abolish-pipeline-run

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/AbolishPipelineRun/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Cancel Publishing

**aliyun CLI**:
```bash
aliyun dataworks-public abolish-pipeline-run \
  --project-id {{project_id}} \
  --id {{pipeline_run_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import AbolishPipelineRunRequest

client.abolish_pipeline_run(AbolishPipelineRunRequest(
    project_id={{project_id}},
    id='{{pipeline_run_id}}'
))
```
