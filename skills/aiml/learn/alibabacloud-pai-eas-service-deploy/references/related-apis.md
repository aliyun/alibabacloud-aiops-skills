# Related API List

All APIs and CLI commands involved in PAI-EAS service deployment.

## EAS Service APIs

| API | CLI Command | Description |
|-----|------------|-------------|
| CreateService | `aliyun eas create-service` | Create service |
| DescribeService | `aliyun eas describe-service` | Query service details |
| ListServices | `aliyun eas list-services` | List services |
| DescribeServiceEndpoints | `aliyun eas describe-service-endpoints` | Query service endpoint |
| DescribeServiceEvent | `aliyun eas describe-service-event` | Query service events |
| DescribeMachineSpec | `aliyun eas describe-machine-spec` | Query machine specs |
| ListResources | `aliyun eas list-resources` | List resource groups |
| ListGateway | `aliyun eas list-gateway` | List gateways |
| DescribeGateway | `aliyun eas describe-gateway` | Query gateway details |

## AIWorkSpace APIs

| API | CLI Command | Description |
|-----|------------|-------------|
| ListWorkspaces | `aliyun aiworkspace list-workspaces` | List workspaces |
| ListImages | `aliyun aiworkspace list-images` | List images |
| GetImage | `aliyun aiworkspace get-image` | Get image details |
| ListDatasets | `aliyun aiworkspace list-datasets` | List datasets |

## OSS APIs

| API | CLI Command | Description |
|-----|------------|-------------|
| ListBuckets | `ossutil ls` | List buckets |
| GetBucketLocation | `ossutil stat` | Get bucket region |
| ListObjects | `ossutil ls oss://bucket/` | List objects |

## VPC APIs

| API | CLI Command | Description |
|-----|------------|-------------|
| DescribeVpcs | `aliyun vpc describe-vpcs` | Query VPCs |
| DescribeVSwitches | `aliyun vpc describe-vswitches` | Query VSwitches |

## ECS APIs

| API | CLI Command | Description |
|-----|------------|-------------|
| DescribeSecurityGroups | `aliyun ecs describe-security-groups` | Query security groups |

## NLB APIs

| API | CLI Command | Description |
|-----|------------|-------------|
| ListLoadBalancers | `aliyun nlb list-load-balancers` | List load balancers |

---

## CLI Command Details

### EAS Service Operations

```bash
# ⚠️ Do NOT use file:// prefix, use $(cat) to read file content
aliyun eas create-service --region cn-hangzhou --body "$(cat service.json)" --user-agent AlibabaCloud-Agent-Skills

aliyun eas describe-service --cluster-id cn-hangzhou --service-name my-service --user-agent AlibabaCloud-Agent-Skills

aliyun eas list-services --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

aliyun eas describe-machine-spec --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

aliyun eas list-resources --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

aliyun eas list-gateway --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

aliyun eas describe-gateway --cluster-id cn-hangzhou --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills
```

### AIWorkSpace Operations

```bash
aliyun aiworkspace list-workspaces --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

aliyun aiworkspace list-images --verbose true --labels 'system.official=true,system.supported.eas=true' --page-size 50 --user-agent AlibabaCloud-Agent-Skills

aliyun aiworkspace get-image --image-id image-xxx --user-agent AlibabaCloud-Agent-Skills

aliyun aiworkspace list-datasets --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

### OSS Operations

```bash
ossutil ls

ossutil ls oss://bucket-name/path/
```

### VPC Operations

```bash
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

aliyun vpc describe-vswitches --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

### ECS Operations

```bash
aliyun ecs describe-security-groups --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

### NLB Operations

```bash
aliyun nlb list-load-balancers --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

---

## SDK Call Metadata

If you need to use Python Common SDK instead of CLI, here are the API metadata:

| Service | API | popCode | popVersion |
|---------|-----|---------|------------|
| EAS | CreateService | eas | 2021-07-01 |
| EAS | DescribeService | eas | 2021-07-01 |
| EAS | ListServices | eas | 2021-07-01 |
| EAS | DescribeServiceEndpoint | eas | 2021-07-01 |
| EAS | ListServiceEvents | eas | 2021-07-01 |
| EAS | DescribeMachineSpec | eas | 2021-07-01 |
| EAS | ListResources | eas | 2021-07-01 |
| EAS | ListGateway | eas | 2021-07-01 |
| EAS | DescribeGateway | eas | 2021-07-01 |
| NLB | ListLoadBalancers | nlb | 2022-04-30 |
| AIWorkSpace | ListWorkspaces | aiworkspace | 2020-04-20 |
| AIWorkSpace | ListImages | aiworkspace | 2020-04-20 |
| AIWorkSpace | GetImage | aiworkspace | 2020-04-20 |
| AIWorkSpace | ListDatasets | aiworkspace | 2020-04-20 |
| OSS | ListBuckets | oss | 2019-05-17 |
| OSS | GetBucketLocation | oss | 2019-05-17 |
| OSS | ListObjects | oss | 2019-05-17 |
| VPC | DescribeVpcs | vpc | 2016-04-28 |
| VPC | DescribeVSwitches | vpc | 2016-04-28 |
| ECS | DescribeSecurityGroups | ecs | 2014-05-26 |
