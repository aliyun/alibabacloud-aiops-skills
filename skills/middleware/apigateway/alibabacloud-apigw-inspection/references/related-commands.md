# Related Commands

## Cloud-Native API Gateway / AI Gateway Commands

**API Mapping**: Product `Apig` | Action `ListGateways` | Version `2019-01-01`

| Product | CLI Command (Plugin Mode) | Description |
|---------|-------------|-------------|
| Cloud-Native API Gateway/AI Gateway | `aliyun apig list-gateways --region ${region_id} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}` | Query gateway list |
| Cloud Monitor | `aliyun cms describe-metric-data` | Query cloud product monitoring data (MUST use DescribeMetricData via plugin mode. DO NOT use DescribeMetricList or DescribeMetricMetaList) |

## API Gateway Commands

> **CRITICAL**: For API Gateway dedicated instances, MUST use `cloudapi` dedicated APIs. DO NOT use Cloud Monitor (CMS).

**API Mapping**: Product `cloudapi` | Version `2016-07-14`

| Product | CLI Command | API Action | Description |
|---------|-------------|------------|-------------|
| API Gateway | `aliyun cloudapi describe-instances --api-version 2016-07-14 --region ${region_id} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}` | DescribeInstances | List API Gateway instances in a specified region |
| API Gateway | `aliyun cloudapi describe-instance-drop-packet` | DescribeInstanceDropPacket | View dropped packet count of dedicated instances |
| API Gateway | `aliyun cloudapi describe-instance-drop-connections` | DescribeInstanceDropConnections | View dropped connection count of dedicated instances |
| API Gateway | `aliyun cloudapi describe-instance-slb-connect` | DescribeInstanceSlbConnect | View SLB connection count of dedicated instances |
| API Gateway | `aliyun cloudapi describe-instance-traffic` | DescribeInstanceTraffic | View traffic information (query RELEASE/PRE/TEST separately) |
| API Gateway | `aliyun cloudapi describe-instance-qps` | DescribeInstanceQps | View QPS data (query RELEASE/PRE/TEST separately) |

## Cloud Monitor Generic Commands

**API Mapping**: Product `Cms` | Action `DescribeMetricData` | Version `2019-01-01`

> **CRITICAL — PROHIBITED APIs:**
> - **DO NOT USE** `DescribeMetricList` (`aliyun cms describe-metric-list`) — returns a different response format and is NOT accepted
> - **DO NOT USE** `DescribeMetricMetaList` (`aliyun cms describe-metric-meta-list`) — DO NOT call this API to discover or list available metrics
> - **ALL metric names are provided in the Supported Metrics tables in SKILL.md. No metric discovery is needed**

| Product | CLI Command | Description |
|---------|-------------|-------------|
| Cloud Monitor | `aliyun cms describe-metric-data --help` | View supported parameters |

## Command Detailed Usage

### Query Cloud-Native API Gateway/AI Gateway Metric Data

```bash
aliyun cms describe-metric-data \
--namespace acs_cnapigateway \
--region ${region} \
--api-version 2019-01-01 \
--metric-name ${metric-name} \
--period 60 \
--start-time ${start-time} \
--end-time ${end-time} \
--dimensions '[{"instanceId": "xxxxxxx"}]' \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

### Query API Gateway Dedicated Instance Metrics

```bash
# Dropped packets
aliyun cloudapi describe-instance-drop-packet \
--start-time ${start-time} \
--end-time ${end-time} \
--instance-id ${instanceId} \
--sbc-name Maximum \
--api-version 2016-07-14 \
--region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

# Dropped connections
aliyun cloudapi describe-instance-drop-connections \
--start-time ${start-time} \
--end-time ${end-time} \
--instance-id ${instanceId} \
--sbc-name Maximum \
--api-version 2016-07-14 \
--region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

# SLB connections
aliyun cloudapi describe-instance-slb-connect \
--start-time ${start-time} \
--end-time ${end-time} \
--instance-id ${instanceId} \
--sbc-name Maximum \
--api-version 2016-07-14 \
--region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

# Traffic information (query RELEASE/PRE/TEST environments separately)
aliyun cloudapi describe-instance-traffic \
--start-time ${start-time} \
--end-time ${end-time} \
--instance-id ${instanceId} \
--stage-name RELEASE \
--api-version 2016-07-14 \
--region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

# QPS data (query RELEASE/PRE/TEST environments separately)
aliyun cloudapi describe-instance-qps \
--start-time ${start-time} \
--end-time ${end-time} \
--instance-id ${instanceId} \
--stage-name RELEASE \
--api-version 2016-07-14 \
--region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```
