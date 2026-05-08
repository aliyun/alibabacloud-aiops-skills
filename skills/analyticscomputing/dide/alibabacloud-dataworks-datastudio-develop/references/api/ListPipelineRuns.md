# list-pipeline-runs

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListPipelineRuns/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### List Pipeline Run History

**aliyun CLI**:
```bash
aliyun dataworks-public list-pipeline-runs \
  --project-id {{project_id}} \
  --page-number 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
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
