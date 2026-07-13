---
name: alibabacloud-mse-nacos-inspection
description: >
  Perform batch inspection on Alibaba Cloud MSE Nacos instances, checking configuration count usage, connection count usage, QPS usage, and TPS usage. Supports two modes: inspecting a specified list of instance IDs, or inspecting all Nacos instances in a region by region. Triggers when the user needs to perform health inspection, capacity assessment, or usage check on MSE Registration & Configuration Center instances, or when the user mentions "inspect nacos", "check nacos instance usage", "nacos capacity inspection", "MSE registry inspection", "nacos inspection", "check nacos config count", "nacos connection count over limit", "nacos QPS/TPS usage", "inspect all nacos in a region", "inspect nacos instances in cn-hangzhou", "check nacos usage across all regions"
---

# MSE Nacos Instance Batch Inspection

Perform usage inspection on a specified set of Alibaba Cloud MSE Nacos instances, covering configuration count usage, connection count usage, QPS usage, and TPS usage, and output alert recommendations based on thresholds. Supports two inspection modes: inspecting a specified list of instance IDs, or automatically discovering and inspecting all Nacos instances in a region.

## Pre-check: Aliyun CLI >= 3.3.3 required

> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once
for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**

Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag
and should be excluded

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-mse-nacos-inspection/{session-id}
```

## Prerequisites

### CLI Tools (Required)

- **aliyun-cli**: Alibaba Cloud CLI tool for querying MSE instance details
  - Installation guide: https://help.aliyun.com/document_detail/139508.html
  - Requires `aliyun configure` to be set up with AccessKey and default Region
- **curl**: Used for executing Prometheus HTTP API query requests

### Alibaba Cloud Credentials

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile.

## Required RAM Permissions

This skill involves read-only operations only and requires the following minimum RAM permissions:

### Custom Policy (Recommended)
```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mse:QueryClusterDetail",
        "mse:ListClusters"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "arms:ListPrometheusInstances",
        "arms:GetPrometheusInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

**Permission Usage:**
- `mse:QueryClusterDetail` - Query MSE instance details (ClusterName, MseVersion, etc.)
- `mse:ListClusters` - List all MSE instances in a region (used in region-based inspection mode)
- `arms:ListPrometheusInstances` - List Prometheus instances to obtain cloud product Prometheus instance IDs.
- `arms:GetPrometheusInstance` - Get Prometheus HTTP API public and internal addresses

For the full permission policy, see `references/ram-policies.md`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Workflow

### Step 1: Collect Inspection Information

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDr blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

Before starting the inspection, proactively confirm the following information with the user (if already provided, use directly):

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|----------|
| Inspection Mode | Required | Mode A: Specify instance ID list; Mode B: Inspect by region | None |
| Instance ID List | Required for Mode A | Specific MSE instance IDs (e.g., `mse-cn-xxx1, mse-cn-xxx2`) | None |
| Region | Required | Region of the instances or target region for region-based inspection (e.g., `cn-hangzhou`) | None |
| Inspection Time Range | Optional | Time range for monitoring metric queries | Last 1 hour |

1. **Inspection Mode** — Confirm which mode the user wants to use:
   - **Mode A: Specify Instance List** — The user provides specific instance IDs (e.g., `mse-cn-xxx1, mse-cn-xxx2`) along with the region for each instance
   - **Mode B: Inspect by Region** — The user provides one or more regions (e.g., `cn-hangzhou`, `cn-shanghai`), and the system automatically discovers and inspects all Nacos instances in those regions
2. **Inspection Time Range** — For example, "last 1 hour", "last 30 minutes", etc. Default is last 1 hour

Decision criteria: If the user provides specific instance IDs, use Mode A; if the user only mentions a region without specifying instance IDs (e.g., "inspect all nacos instances in cn-hangzhou"), use Mode B.

### Step 2: Get the List of Instances to Inspect

#### Mode A: User Has Specified Instance IDs

Use the instance ID list provided by the user directly, proceed to Step 3 to query details for each instance.

#### Mode B: Auto-discover All Instances by Region

For each region specified by the user, list all MSE instances in that region via paginated queries.

```bash
aliyun mse list-clusters --page-num ${PageNum} --page-size ${PageSize} --biz-region-id ${regionId} --region ${regionId} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mse-nacos-inspection/{session-id}
```

**Pagination Logic:**
1. Initial `PageNum` = 1, `PageSize` = 10
2. Execute the query and extract the instance list from the response
3. Extract `InstanceId`, `ClusterName`, `MseVersion` and other fields from each instance record.
4. If the number of instances returned on the current page equals `PageSize`, increment `PageNum` by 1 and query the next page.
5. If the current page returns an empty instance list or fewer instances than `PageSize`, all instances have been retrieved; stop paginating

**Important**: The `list-clusters` response already includes `ClusterName` and `MseVersion` fields. Therefore, for successfully listed instances in Mode B, **there is no need to call `query-cluster-detail` separately** — you can use the field values from the list response directly, skip Step 3, and proceed to Step 4 to query Prometheus metrics. If list-clusters returns an empty list, the inspection should be paused while simultaneously asking the customer if the region is correct.

### Step 3: Query Instance Details (Mode A Only)

For each Nacos instance to be inspected in Mode A, execute the following command to get `ClusterName` and `MseVersion`:

```bash
aliyun mse query-cluster-detail --instance-id ${instanceId} --region ${regionId} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mse-nacos-inspection/{session-id}
```

Extract the following fields from the response:
- `ClusterName` — Used as `service_cluster_id` in subsequent Prometheus queries
- `MseVersion` — Used to determine the instance version type

**MseVersion Version Mapping:**

| MseVersion Value | Instance Edition | Metrics to Query |
|------------------|------------------|------------------|
| `mse_pro` | Professional | Config count usage + Connection count usage + QPS usage + TPS usage |
| `mse_platinum` | Enterprise | Config count usage + Connection count usage + QPS usage + TPS usage |
| `mse_serverless` | Serverless | Config count usage only |
| `mse_dev` | Developer | No query (skip) |
| `mse_basic` | Basic | No query (skip) |

**Important**: If an instance is Developer or Basic edition, mark it as "N/A" in the inspection results and skip the Prometheus query.

### Step 4: Query Prometheus Monitoring Metrics

#### 4.0 Get Prometheus HTTP API Address

Use the ARMS OpenAPI to get the HTTP API address of the cloud product Prometheus instance in the specified region. The API returns two addresses:
- **HttpApiInterUrl** (public address) — Used by default
- **HttpApiIntraUrl** (internal address) — Used as fallback when public access is unavailable

**Get instance list (extract ClusterId):**
```bash
aliyun arms list-prometheus-instances \
  --biz-region-id ${regionId} \
  --cluster-type cloud-product-prometheus \
  --show-global-view false \
  --api-version 2019-08-08 \
  --region ${regionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mse-nacos-inspection/{session-id}
```

**Get instance details (extract API address):**
```bash
aliyun arms get-prometheus-instance \
  --biz-region-id ${regionId} \
  --cluster-id ${clusterId} \
  --api-version 2019-08-08 \
  --region ${regionId} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mse-nacos-inspection/{session-id}
```

#### 4.0.1 Construct Query URL

Replace the ClusterId (second-to-last path segment) in the obtained URL path with the fixed value `cloud-product-regcenter`:
```
Original: {base}/api/v1/prometheus/{path1}/{path2}/{ClusterId}/{region}
Replaced: {base}/api/v1/prometheus/{path1}/{path2}/cloud-product-regcenter/{region}
```

#### 4.0.2 Execute Range Query

Use curl to execute query_range. The PromQL must be URL-encoded. Use Unix timestamps in seconds:
```bash
ENCODED_PROMQL=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "${PROMQL}")
curl -s "${PROMETHEUS_URL}/api/v1/query_range?query=${ENCODED_PROMQL}&start=${START_TIMESTAMP}&end=${END_TIMESTAMP}&step=${STEP}&timeout=10000" --max-time 120
```

Recommended step parameter: use `15s` for inspection time range <= 1 hour, `60s` for within 1 day.

---

For each instance, query the following metrics based on its edition type. Replace `$clusterName` in all PromQL queries with the `ClusterName` value obtained in Step 2 (Mode B) or Step 3 (Mode A) for that instance.

**For complete PromQL queries, refer to `references/promql-queries.md`.**

#### 4.1 Configuration Count Usage

- Professional (mse_pro): Query `references/promql-queries.md` §4.1 Professional
- Enterprise (mse_platinum): Query `references/promql-queries.md` §4.1 Enterprise
- Serverless (mse_serverless): Query `references/promql-queries.md` §4.1 Serverless

#### 4.2 Connection Count Usage (Professional and Enterprise only)

- Professional (mse_pro): Query `references/promql-queries.md` §4.2 Professional
- Enterprise (mse_platinum): Query `references/promql-queries.md` §4.2 Enterprise

#### 4.3 QPS Usage (Professional and Enterprise only)

- Professional (mse_pro): Query `references/promql-queries.md` §4.3 Professional
- Enterprise (mse_platinum): Query `references/promql-queries.md` §4.3 Enterprise

#### 4.4 TPS Usage (Professional and Enterprise only)

- Professional (mse_pro): Query `references/promql-queries.md` §4.4 Professional
- Enterprise (mse_platinum): Query `references/promql-queries.md` §4.4 Enterprise

---

### Step 5: Analyze and Output Inspection Results

#### 5.1 Parse Metric Data

For each instance and each metric, extract the **maximum value** from the time series data returned by the range query as the basis for inspection judgment.

#### 5.2 Alert Threshold Determination

| Metric | Alert Threshold | Alert Action |
|--------|----------------|--------------|
| Configuration count usage | > 0.8 (80%) | Alert user to monitor configuration count quota and adjust in time |
| Connection count usage | > 1 (100%) | Alert user to monitor instance capacity and upgrade in time |
| QPS usage | > 1 (100%) | Alert user to monitor instance capacity and upgrade in time |
| TPS usage | > 1 (100%) | Alert user to monitor instance capacity and upgrade in time |

#### 5.3 Output Format

Summarize the inspection results in a Markdown table in the session, and also generate a `.md` inspection report file.

**Session Output Example:**

```
## MSE Nacos Inspection Results

Inspection Period: 2024-01-01 10:00 ~ 2024-01-01 11:00
Number of Instances Inspected: 3

| Instance ID | Edition | Config Count Usage | Connection Count Usage | QPS Usage | TPS Usage | Status |
|-------------|---------|-------------------|----------------------|-----------|-----------|--------|
| mse-cn-xxx1 | Professional | 45% | 60% | 30% | 20% | Normal |
| mse-cn-xxx2 | Enterprise | 85% | 50% | 40% | 25% | ⚠️ Config count usage over threshold |
| mse-cn-xxx3 | Serverless | 30% | - | - | - | Normal |

### Alert Details

⚠️ **mse-cn-xxx2 (Enterprise)**
- Configuration count usage reached 85%, exceeding the 80% threshold
- Recommendation: Please adjust the configuration count quota in time
- Reference: https://help.aliyun.com/zh/mse/product-overview/mse-quotas-and-limits
```

#### 5.4 Reference Documentation

Include the following reference documentation links in alert messages:

- **Configuration count quota adjustment**: https://help.aliyun.com/zh/mse/product-overview/mse-quotas-and-limits
- **Developer and Professional edition instance specifications**: https://help.aliyun.com/zh/mse/product-overview/estimate-developer-edition-instances-and-professional-edition-instances
- **Enterprise edition instance specifications**: https://help.aliyun.com/zh/mse/product-overview/nacos-platinum-edition-capacity-description

## Success Verification

After the inspection is complete, follow the steps in `references/verification-method.md` to verify the correctness of the results.

Key verification points:
- All four usage metrics have been queried for each instance (or marked as "N/A" / "No data")
- Instances exceeding thresholds include alert details and recommendations
- Inspection report file has been generated

## Cleanup

This skill performs **read-only operations only** — it does not create, modify, or delete any cloud resources; no cleanup is needed.

Local `.md` inspection report files generated during the inspection are managed by the user.

## Error Handling

- **No instances in region**: If `list-clusters` returns an empty list for a region, inform the user that there are no MSE Nacos instances in that region and continue inspecting other regions
- **Pagination query failure**: If a page query fails during `list-clusters` pagination, record the successfully retrieved instance list, continue inspecting the retrieved instances, and note the pagination interruption in the report
- **Instance does not exist or query failure**: If `query-cluster-detail` returns an error, record the reason for the failure, continue inspecting the remaining instances, and note it in the final inspection report
- **Insufficient permissions**: If AccessDenied or NoPermission is returned, prompt the user to add the corresponding RAM permissions
- **Prometheus query returns no data**: If a metric query returns empty results, mark it as "No data" in the inspection results and suggest the user confirm whether the instance is running normally
- **Partial instance inspection failure**: Does not affect the inspection of other instances; mark failed instances and reasons in the final summary
- **Prometheus instance does not exist**: If `list-prometheus-instances` returns an empty list, inform the user that no cloud product Prometheus instance has been created in that region and suggest enabling it in the ARMS console
- **API address is empty**: If both HttpApiInterUrl and HttpApiIntraUrl are empty, the instance may not be fully initialized; if the public address is empty but the internal address exists, use the internal address
- **PromQL syntax error**: If Prometheus returns a query error (e.g., `errorType: "bad_data"`), display the error message and suggest checking the PromQL syntax
- **Query timeout**: If a timeout error is returned, suggest narrowing the query time range or simplifying the PromQL statement

## Notes

- This skill performs read-only operations only; no cloud resources will be modified
- Prometheus queries are executed via the public address (HttpApiInterUrl) by default; no VPC internal network is required; if public access is unavailable, it will automatically fall back to the internal address (HttpApiIntraUrl)
- Recommended query step parameter: use `15s` for inspection time range <= 1 hour, `60s` for within 1 day
- For batch inspection of a large number of instances (>10), it is recommended to execute in batches to avoid API rate limiting
- When inspecting by region, ListClusters defaults to 10 items per page and will automatically paginate until all instances are retrieved
- Developer and Basic edition instances do not support Prometheus monitoring and will be marked as "N/A" in the inspection results
- Timestamps use Unix seconds (not milliseconds)

## Reference Links

| File | Description |
|------|-------------|
| `references/promql-queries.md` | All PromQL queries (config count / connection count / QPS / TPS) |
| `references/ram-policies.md` | RAM permission policy details |
| `references/related-commands.md` | Related CLI command list |
| `references/verification-method.md` | Verification steps and methods |
| `references/cli-installation-guide.md` | CLI installation guide |
