# create-pipeline-run

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/CreatePipelineRun/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Idempotency Note

This API does not support `ClientToken`. If the call times out or returns a network error, **do not blindly retry**. First check whether a pipeline run was already created by calling `list-pipeline-runs` and filtering by the target object. Only retry if no matching active pipeline run exists. Always record the `RequestId` from the response for traceability.

> ## ⚠️ `--object-ids` Format — Common Mistake
>
> The CLI plugin (`aliyun dataworks-public ...`) accepts `--object-ids` as **space-separated bare values** — verified against `aliyun dataworks-public create-pipeline-run --help`, which prints `format: --object-ids value1 value2 value3`. Do NOT wrap it in JSON brackets.
>
> | ✅ CORRECT | ❌ WRONG |
> |---|---|
> | `--object-ids 7567482277219412494` (bare ID) | `--object-ids '["7567482277219412494"]'` (JSON array string) — CLI sends the literal text `["7567482277219412494"]` as the ID and the API replies `未找到发布对象: [["7567482277219412494"]]` |
> | `--object-ids id1 id2 id3` (space-separated; **only `id1` and its children deploy** — pass extra IDs as separate calls) | `--object-ids [7567482277219412494]` (unquoted brackets — shell glob hazard, also wrong) |
>
> The IDs are strings on the wire even when they look numeric; pass them unquoted at the shell, the CLI handles the rest. The Python SDK takes a real Python list (`object_ids=['ID']`) — the JSON-array confusion only ever applied to the SDK style and was incorrectly back-ported into CLI docs.

### Create Pipeline Run (Publish / Deploy)

**aliyun CLI**:
```bash
aliyun dataworks-public create-pipeline-run \
  --project-id {{project_id}} \
  --type Online \
  --object-ids {{object_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
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
