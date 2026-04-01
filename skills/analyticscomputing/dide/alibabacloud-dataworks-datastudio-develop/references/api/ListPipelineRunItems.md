# ListPipelineRunItems

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListPipelineRunItems/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### List Pipeline Run Items

**aliyun CLI**:
```bash
aliyun dataworks-public ListPipelineRunItems \
  --ProjectId {{project_id}} \
  --PipelineRunId {{pipeline_run_id}} \
  --PageNumber 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListPipelineRunItemsRequest

response = client.list_pipeline_run_items(ListPipelineRunItemsRequest(
    project_id={{project_id}},
    pipeline_run_id='{{pipeline_run_id}}',
    page_number=1,
    page_size=50
))
for item in response.body.paging_info.pipeline_run_items:
    m = item.to_map()
    print(f"{m['Name']}: {m.get('Status', 'N/A')}")
```
