# API Reference

## API Response Structures

**Alibaba Cloud API response structures are inconsistent — pay attention when using jq:**

| API | jq Path | Structure |
|-----|---------|-----------|
| `AIWorkSpace ListWorkspaces` | `.Workspaces[]` | single-level |
| `AIWorkSpace ListImages` | `.Images[]` | single-level |
| `eas DescribeMachineSpec` | `.InstanceMetas[]` | single-level |
| `eas list-gateway` | `.Gateways[]` | single-level |
| `eas ListResources` | `.Resources[]` | single-level |
| `eas DescribeService` | `.Service` | single object |
| `eas describe-service-event` | `.Events[]` | single-level |
| `vpc DescribeVpcs` | `.Vpcs.Vpc[]` | ⚠️ nested (two-level) |
| `vpc DescribeVSwitches` | `.VSwitches.VSwitch[]` | ⚠️ nested (two-level) |
| `ecs DescribeSecurityGroups` | `.SecurityGroups.SecurityGroup[]` | ⚠️ nested (two-level) |
| `nlb ListLoadBalancers` | `.LoadBalancers[]` | single-level |

## jq Examples

```bash
aliyun aiworkspace list-workspaces --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | jq -r '.Workspaces[] | "\(.WorkspaceId)\t\(.WorkspaceName)"'
aliyun eas list-gateway --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | jq -r '.Gateways[] | "\(.GatewayId)\t\(.GatewayName)"'
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | jq -r '.Vpcs.Vpc[] | "\(.VpcId)\t\(.VpcName)"'
```

## CLI Command Reference

### Parameter Naming Rules

| Command type | Parameter | Example |
|--------------|-----------|---------|
| List / create | `--region` | `ListServices`, `CreateService` |
| Target a single service | `--cluster-id` | `DescribeService`, `DeleteService` |

### Common Commands

```bash
aliyun aiworkspace list-workspaces --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
aliyun aiworkspace list-images --verbose true --labels 'system.official=true,system.supported.eas=true' --page-size 100 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
aliyun eas describe-machine-spec --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
aliyun eas list-resources --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
aliyun eas list-gateway --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
aliyun eas describe-gateway --cluster-id cn-hangzhou --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
aliyun eas create-service --region cn-hangzhou --body "$(cat service.json)" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
aliyun eas describe-service --cluster-id cn-hangzhou --service-name my_service --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
```

## Permission List

See [RAM Policies](ram-policies.md).

## Common GPU Instance Types

| Instance type | GPU | CPU | Memory | Use case |
|---------------|-----|-----|--------|----------|
| `ecs.gn6i-c4g1.xlarge` | 1× T4 | 4 | 16Gi | Small model inference |
| `ecs.gn6i-c8g1.2xlarge` | 1× T4 | 8 | 32Gi | Medium model |
| `ecs.gn7-c12g1.12xlarge` | 4× A10 | 12 | 192Gi | Large model inference |
