# GetPipelineRun

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/GetPipelineRun/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Query Pipeline Run Status

**aliyun CLI**:
```bash
aliyun dataworks-public GetPipelineRun \
  --ProjectId {{project_id}} \
  --Id {{pipeline_run_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetPipelineRunRequest

response = client.get_pipeline_run(GetPipelineRunRequest(
    project_id={{project_id}},
    id='{{pipeline_run_id}}'
))
pipeline = response.body.pipeline.to_map()
print(f"Status: {pipeline['Status']}")
# Status: Init / Running / Success / Fail / Termination / Cancel
for stage in pipeline.get('Stages', []):
    print(f"  {stage['Code']}({stage['Status']}): {stage['Name']}")
```
