# list-pipeline-run-items

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListPipelineRunItems/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### List Pipeline Run Items

**aliyun CLI**:
```bash
aliyun dataworks-public list-pipeline-run-items \
  --project-id {{project_id}} \
  --pipeline-run-id {{pipeline_run_id}} \
  --page-number 1 \
  --page-size 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
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
