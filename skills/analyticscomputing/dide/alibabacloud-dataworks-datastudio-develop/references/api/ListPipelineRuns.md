# ListPipelineRuns

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListPipelineRuns/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### List Pipeline Run History

**aliyun CLI**:
```bash
aliyun dataworks-public ListPipelineRuns \
  --ProjectId {{project_id}} \
  --PageNumber 1 \
  --PageSize 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListPipelineRunsRequest

response = client.list_pipeline_runs(ListPipelineRunsRequest(
    project_id={{project_id}},
    page_number=1,
    page_size=20
))
for run in response.body.paging_info.pipeline_runs:
    m = run.to_map()
    print(f"{m['Id']} [{m['Status']}]")
```
