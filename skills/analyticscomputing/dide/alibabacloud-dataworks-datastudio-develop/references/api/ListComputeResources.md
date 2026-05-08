# list-compute-resources

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/ListComputeResources/api.json

Query the list of compute resources bound to the project. Use this API to discover compute engine bindings (EMR Serverless Spark, Hologres, StarRocks, etc.) that may not appear in `list-data-sources`.

**aliyun CLI**:
```bash
aliyun dataworks-public list-compute-resources \
  --project-id {{project_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Key parameters**:
- `--project-id` (Required) — DataWorks workspace ID
- `--EnvType` (Optional) — `Dev` or `Prod`
- `--Types.1`, `--Types.2`, ... (Optional) — Filter by compute resource type

**Response fields of interest**:
- `ComputeResourceList[].Name` — Compute resource name (can be used as `datasource.name`)
- `ComputeResourceList[].Type` — Compute engine type (e.g., `EMR_Serverless`, `Hologres`, `StarRocks`)
- `ComputeResourceList[].EnvType` — Environment type (`Dev` / `Prod`)
