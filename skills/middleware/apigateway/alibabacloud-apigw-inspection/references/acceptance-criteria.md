# Acceptance Criteria: alibabacloud-apigw-inspection

**Scenario**: Alibaba Cloud Gateway Instance Inspection
**Purpose**: Skill Test Acceptance Criteria

---

## Correct CLI Command Patterns

### 1. Product Subcommand Validation

#### ✅ Correct
```bash
# Cloud-Native API Gateway/AI Gateway - Use apig product
aliyun apig list-gateways --region cn-hangzhou

# API Gateway - Use cloudapi product
aliyun cloudapi describe-instances --api-version 2016-07-14 --region cn-hangzhou

# Cloud Monitor - Use cms product
aliyun cms describe-metric-data --namespace acs_cnapigateway
```

#### ❌ Incorrect
```bash
# Error: Product name does not exist
aliyun apigateway list-gateways  # Should be apig
aliyun gateway list  # Product name does not exist
```

### 2. Action Subcommand Validation

#### ✅ Correct — Plugin Mode (Required)
```bash
# MUST use plugin mode (lowercase hyphenated format)
aliyun apig list-gateways
aliyun cloudapi describe-instances
aliyun cloudapi describe-instance-drop-packet
aliyun cloudapi describe-instance-drop-connections
aliyun cloudapi describe-instance-slb-connect
aliyun cloudapi describe-instance-traffic
aliyun cloudapi describe-instance-qps
aliyun cms describe-metric-data
```

> **IMPORTANT**: All commands MUST be executed using CLI plugin mode. Traditional API format (PascalCase action names) is NOT allowed.
> If a required plugin is not installed, run `aliyun plugin install --names <plugin-name>` to install it first.

#### ❌ Incorrect
```bash
# Error: Wrong product code (apigateway does not exist, use apig)
aliyun apigateway list-gateways
aliyun apigateway DescribeInstance
# Error: Wrong action name (DescribeInstance is not a valid Apig action, use ListGateways)
aliyun apig DescribeInstance
```

### 3. Parameter Validation

#### ✅ Correct
```bash
# Cloud-Native API Gateway/AI Gateway query
aliyun apig list-gateways --region cn-hangzhou

# API Gateway query (requires --api-version)
aliyun cloudapi describe-instances --api-version 2016-07-14 --region cn-hangzhou

# Cloud Monitor query (complete parameters)
aliyun cms describe-metric-data \
  --namespace acs_cnapigateway \
  --region cn-hangzhou \
  --api-version 2019-01-01 \
  --metric-name EnvoyCpuUsageRate \
  --period 60 \
  --start-time 1704067200000 \
  --end-time 1704153600000 \
  --dimensions '[{"instanceId": "gw-xxxxxxx"}]'

# API Gateway dedicated instance query
aliyun cloudapi describe-instance-drop-packet \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T01:00:00Z \
  --instance-id apigateway-xx-xxxxxxx \
  --sbc-name Maximum \
  --api-version 2016-07-14 \
  --region cn-hangzhou
```

#### ❌ Incorrect
```bash
# Error: Missing required parameters
aliyun cms describe-metric-data --namespace acs_cnapigateway  # Missing metric-name, dimensions, etc.

# Error: Incorrect time format (Cloud Monitor uses millisecond timestamps)
aliyun cms describe-metric-data --start-time "2024-01-01" --end-time "2024-01-02"

# Error: API Gateway time format should use ISO8601 UTC
aliyun cloudapi describe-instance-drop-packet --start-time "1704067200000"

# Error: DescribeMetricList is NOT the same as DescribeMetricData — DO NOT use DescribeMetricList
aliyun cms describe-metric-list --namespace acs_cnapigateway
aliyun cms DescribeMetricList --Namespace acs_cnapigateway
```

---

## Correct Inspection Workflow Patterns

### 1. Instance Type Determination

#### ✅ Correct
```
1. User selects product type (Cloud-Native API Gateway/AI Gateway/API Gateway)
2. Use the corresponding query command based on product type:
   - Cloud-Native API Gateway/AI Gateway:
     aliyun apig list-gateways --region ${region_id} (plugin mode only)
   - API Gateway: aliyun cloudapi describe-instances
3. Do NOT skip the gateway list query. If plugin is not installed, run `aliyun plugin install --names apig` first.
4. Check instance type:
   - API Gateway: Only VPC_DEDICATED (dedicated) type is supported
   - Cloud-Native API Gateway/AI Gateway: Distinguished by gatewayType
```

#### ❌ Incorrect
```
# Error: Inspecting a shared API Gateway instance
# Shared instances (VPC_SHARED) do not support inspection; user should be informed in advance

# Error: Confusing instance ID formats
# API Gateway instance ID: apigateway-xx-xxxxxxx
# Cloud-Native API Gateway/AI Gateway instance ID: gw-xxxxxxx
```

### 2. Monitoring Metric Query

#### ✅ Correct
```
Cloud-Native API Gateway/AI Gateway:
- API: Cms DescribeMetricData (product: Cms, action: DescribeMetricData, version: 2019-01-01)
- CLI: aliyun cms describe-metric-data (NOT describe-metric-list)
- namespace: acs_cnapigateway
- dimensions: [{"instanceId": "xxx"}]
- start-time/end-time: Unix millisecond timestamps
- MUST query ALL metric categories: CPU, memory, connections, network IO, rate limiting, bandwidth

API Gateway dedicated instances:
- MUST use CloudAPI dedicated APIs (product: cloudapi, version: 2016-07-14)
- DO NOT use Cloud Monitor (CMS) for API Gateway dedicated instances
- Required APIs: DescribeInstanceDropPacket, DescribeInstanceDropConnections, DescribeInstanceSlbConnect, DescribeInstanceTraffic, DescribeInstanceQps
- start-time/end-time: ISO8601 UTC format (YYYY-MM-DDThh:mm:ssZ)
- DescribeInstanceTraffic and DescribeInstanceQps MUST each be queried 3 times: RELEASE, PRE, TEST
- Total: 7 API calls (5 base APIs, Traffic × 3, QPS × 3)
```

#### ❌ Incorrect
```
# Error: Using CMS for API Gateway dedicated instances
# Should use cloudapi describe-instance-traffic, NOT cms describe-metric-data/list
aliyun cms describe-metric-list --namespace acs_apigateway_dashboard  # WRONG for API Gateway
aliyun cms DescribeMetricList --Namespace acs_apigateway_dashboard    # WRONG for API Gateway

# Error: Using API Gateway APIs for Cloud-Native API Gateway
# Should use cms describe-metric-data, not cloudapi describe-instance-*

# Error: Mixing time formats
# Cloud Monitor uses millisecond timestamps, API Gateway uses ISO8601 UTC

# Error: Only querying one environment for Traffic/QPS
# Must query RELEASE, PRE, and TEST separately
```

### 3. Inspection Report Generation

#### ✅ Correct
```
Report includes:
- Basic information (product type, instance ID, region, inspection time)
- Inspection results overview (table format)
- Detailed analysis (peak values, trends, and analysis for each metric)
- Risk assessment (high/medium risk items)
- Optimization recommendations (based on actual issues)
- Conclusion
```

#### ❌ Incorrect
```
# Error: Fabricating data
# All data must come from actual API responses

# Error: Providing optimization recommendations when all metrics are normal
# If all metrics are normal, no recommendations are needed
```

---

## Key Threshold Standards

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| CPU Usage | < 70% | 70%-85% | > 85% |
| Memory Usage | < 75% | 75%-90% | > 90% |
| Connections | < 70% of max | 70%-85% | > 85% |
| Network IO | < 70% of bandwidth | 70%-85% | > 85% |
| Rate Limiting | No triggers | > 0 occurrences | Continuously increasing |

---

## Security Checklist

- [ ] No hardcoded AccessKey ID/Secret
- [ ] Use `aliyun configure list` to verify credential status
- [ ] All user-customizable parameters have been confirmed
- [ ] Region is within the available regions for the corresponding product
- [ ] Instance ID format matches the product type
