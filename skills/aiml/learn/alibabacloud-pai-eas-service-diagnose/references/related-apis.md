# Related API List

This document lists all APIs and their CLI commands involved in PAI-EAS service diagnosis.

**Table of Contents**

- [EAS Service Diagnosis APIs](#eas-service-diagnosis-apis)
- [Resource Group APIs](#resource-group-apis)
- [Gateway APIs](#gateway-apis)
- [CLI Command Details](#cli-command-details)
- [SDK Invocation Metadata](#sdk-invocation-metadata)

## EAS Service Diagnosis APIs

| API | CLI Command | Description |
|-----|------------|-------------|
| DescribeService | `aliyun eas describe-service --user-agent AlibabaCloud-Agent-Skills` | Query service details |
| DescribeServiceLog | `aliyun eas describe-service-log --user-agent AlibabaCloud-Agent-Skills` | Query service logs |
| DescribeServiceEvent | `aliyun eas describe-service-event --user-agent AlibabaCloud-Agent-Skills` | Query service events |
| DescribeServiceDiagnosis | `aliyun eas describe-service-diagnosis --user-agent AlibabaCloud-Agent-Skills` | Service diagnosis report |
| DescribeServiceInstanceDiagnosis | `aliyun eas describe-service-instance-diagnosis --user-agent AlibabaCloud-Agent-Skills` | Instance diagnosis |
| ListServiceInstances | `aliyun eas list-service-instances --user-agent AlibabaCloud-Agent-Skills` | List instances |
| ListServiceContainers | `aliyun eas list-service-containers --instance-name <instance> --user-agent AlibabaCloud-Agent-Skills` | List containers (requires --instance-name) |
| DescribeServiceEndpoints | `aliyun eas describe-service-endpoints --user-agent AlibabaCloud-Agent-Skills` | Service endpoints |
| ListServices | `aliyun eas list-services --user-agent AlibabaCloud-Agent-Skills` | List services |

## Resource Group APIs

| API | CLI Command | Description |
|-----|------------|-------------|
| DescribeResource | `aliyun eas describe-resource --user-agent AlibabaCloud-Agent-Skills` | Resource group details |
| ListResources | `aliyun eas list-resources --user-agent AlibabaCloud-Agent-Skills` | List resource groups |

## Gateway APIs

| API | CLI Command | Description |
|-----|------------|-------------|
| DescribeGateway | `aliyun eas describe-gateway --user-agent AlibabaCloud-Agent-Skills` | Gateway details |
| ListGateways | `aliyun eas list-gateways --user-agent AlibabaCloud-Agent-Skills` | List gateways |

---

## CLI Command Details

### Service Status Query

```bash
aliyun eas describe-service --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills

aliyun eas list-services --cluster-id $CLUSTER_ID --user-agent AlibabaCloud-Agent-Skills
```

### Log Query

```bash
# Basic query
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE --limit 100 --user-agent AlibabaCloud-Agent-Skills

# Keyword filtering
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --keyword "error" --limit 50 --user-agent AlibabaCloud-Agent-Skills

# Time range
aliyun eas describe-service-log --cluster-id $CLUSTER_ID --service-name $SERVICE \
  --start-time "2026-03-19T00:00:00Z" --end-time "2026-03-19T23:59:59Z" --user-agent AlibabaCloud-Agent-Skills
```

### Event Query

```bash
aliyun eas describe-service-event --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills
```

### Instance Query

```bash
aliyun eas list-service-instances --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills

aliyun eas list-service-containers --cluster-id $CLUSTER_ID --service-name $SERVICE --instance-name $INSTANCE_NAME --user-agent AlibabaCloud-Agent-Skills
```

### Diagnosis API

```bash
aliyun eas describe-service-diagnosis --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills

aliyun eas describe-service-instance-diagnosis --cluster-id $CLUSTER_ID \
  --service-name $SERVICE --instance-id i-xxx --user-agent AlibabaCloud-Agent-Skills
```

### Endpoint Query

```bash
aliyun eas describe-service-endpoints --cluster-id $CLUSTER_ID --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills
```

### Resource Group Query

```bash
aliyun eas describe-resource --cluster-id $CLUSTER_ID --resource-id eas-r-xxx --user-agent AlibabaCloud-Agent-Skills

aliyun eas list-resources --cluster-id $CLUSTER_ID --user-agent AlibabaCloud-Agent-Skills
```

### Gateway Query

```bash
aliyun eas describe-gateway --cluster-id $CLUSTER_ID --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills

aliyun eas list-gateways --cluster-id $CLUSTER_ID --user-agent AlibabaCloud-Agent-Skills
```

---

## SDK Invocation Metadata

If you need to use Python Common SDK instead of CLI, here is the metadata for each API:

| Service | API | popCode | popVersion |
|---------|-----|---------|------------|
| EAS | DescribeService | eas | 2021-07-01 |
| EAS | DescribeServiceLog | eas | 2021-07-01 |
| EAS | DescribeServiceEvent | eas | 2021-07-01 |
| EAS | DescribeServiceDiagnosis | eas | 2021-07-01 |
| EAS | DescribeServiceInstanceDiagnosis | eas | 2021-07-01 |
| EAS | ListServiceInstances | eas | 2021-07-01 |
| EAS | ListServiceContainers | eas | 2021-07-01 |
| EAS | DescribeServiceEndpoints | eas | 2021-07-01 |
| EAS | ListServices | eas | 2021-07-01 |
| EAS | DescribeResource | eas | 2021-07-01 |
| EAS | ListResources | eas | 2021-07-01 |
| EAS | DescribeGateway | eas | 2021-07-01 |
| EAS | ListGateways | eas | 2021-07-01 |
