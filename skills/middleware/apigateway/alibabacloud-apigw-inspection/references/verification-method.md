# Inspection Verification Method

## Verification Objective

Confirm that the gateway instance inspection workflow has been executed successfully and valid monitoring metric data has been retrieved.

## Verification Steps

### Step 1: Verify Instance Query Success

**Verification Command:**

For Cloud-Native API Gateway/AI Gateway:
```bash
aliyun apig list-gateways --region ${region_id} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

For API Gateway:
```bash
aliyun cloudapi describe-instances --api-version 2016-07-14 --region ${region_id} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

**Success Criteria:**
- Returns HTTP 200 status code
- Response contains instance information (InstanceId, InstanceName, etc.)
- Instance status is running normally

### Step 2: Verify Monitoring Metric Query Success

**Verification Command:**

For Cloud-Native API Gateway/AI Gateway:
```bash
aliyun cms describe-metric-data \
--namespace acs_cnapigateway \
--region ${region} \
--api-version 2019-01-01 \
--metric-name EnvoyCpuUsageRate \
--period 60 \
--start-time ${start-time} \
--end-time ${end-time} \
--dimensions '[{"instanceId": "${instanceId}"}]' \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

For API Gateway:
```bash
aliyun cloudapi describe-instance-drop-packet \
--start-time ${start-time} \
--end-time ${end-time} \
--instance-id ${instanceId} \
--sbc-name Maximum \
--api-version 2016-07-14 \
--region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

**Success Criteria:**
- Returns HTTP 200 status code
- Response contains `Datapoints` field
- `Datapoints` array is non-empty and contains time series data points

### Step 3: Verify Inspection Report Generation

**Verification Content:**
- Inspection report includes all required sections (basic information, inspection results overview, detailed analysis, risk assessment, optimization recommendations, conclusion)
- All metric data comes from actual API responses, not fabricated
- Risk level determination conforms to threshold standards

**Success Criteria:**
- Report structure is complete
- Data is consistent with query results
- Risk determination logic is correct

## Common Issue Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Instance query returns empty | Region error or instance ID does not exist | Check RegionId and InstanceId |
| Monitoring data is empty | Incorrect time range | Check start-time and end-time format |
| API Gateway does not support inspection | Shared instances are not supported | Only dedicated instances (VPC_DEDICATED) support inspection |
