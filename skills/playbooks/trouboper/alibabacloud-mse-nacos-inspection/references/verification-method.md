# Verification Method — MSE Nacos Inspection

## Verification Steps

### 1. Verify CLI Environment

```bash
# Confirm CLI version >= 3.3.3
aliyun version

# Confirm credentials are configured and valid
aliyun configure list
```

Expected results:
- `aliyun version` output >= 3.3.3
- `aliyun configure list` shows a valid profile (AK/STS/OAuth)

### 2. Verify MSE Instance Query Permission

```bash
# Mode B: List instances by region
aliyun mse list-clusters --page-num 1 --page-size 1 --biz-region-id cn-hangzhou --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mse-nacos-inspection/{session-id}

# Mode A: Query details of a specified instance (replace ${instanceId} with actual instance ID)
aliyun mse query-cluster-detail --instance-id ${instanceId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mse-nacos-inspection/{session-id}
```

Expected result: Returns MSE instance list or details, including `InstanceId`, `ClusterName`, `MseVersion` fields.

### 3. Verify ARMS Prometheus Permission

```bash
aliyun arms list-prometheus-instances \
  --biz-region-id cn-hangzhou \
  --cluster-type cloud-product-prometheus \
  --show-global-view false \
  --api-version 2019-08-08 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mse-nacos-inspection/{session-id}
```

Expected result: Returns Prometheus instance list, including `ClusterId` field.

### 4. Verify Prometheus HTTP API Reachability

```bash
# Get Prometheus instance details
aliyun arms get-prometheus-instance \
  --biz-region-id cn-hangzhou \
  --cluster-id ${clusterId} \
  --api-version 2019-08-08 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-mse-nacos-inspection/{session-id}
```

Expected result: Returns details including `HttpApiInterUrl` (public) and/or `HttpApiIntraUrl` (internal).

Use curl to test API reachability:
```bash
curl -s "${PROMETHEUS_URL}/api/v1/query_range?query=up&start=$(date +%s -d '5 minutes ago')&end=$(date +%s)&step=60s&timeout=10000" --max-time 120
```

Expected result: Returns JSON data with `status` field as `"success"`.

### 5. Verify Inspection Result Output

After the inspection is complete, check whether the output includes:
- [ ] Markdown-formatted inspection result table
- [ ] Configuration count usage, connection count usage, QPS usage, and TPS usage for each instance
- [ ] Alert details and recommendations for instances exceeding thresholds
- [ ] Developer/Basic edition instances marked as "N/A"
- [ ] Reference documentation links
