# API 参考手册

## API 返回结构

**阿里云 API 返回结构不一致，使用 jq 时需注意**：

| API | jq 路径 | 结构 |
|-----|---------|------|
| `AIWorkSpace ListWorkspaces` | `.Workspaces[]` | 单层 |
| `AIWorkSpace ListImages` | `.Images[]` | 单层 |
| `eas DescribeMachineSpec` | `.InstanceMetas[]` | 单层 |
| `eas list-gateway` | `.Gateways[]` | 单层 |
| `eas ListResources` | `.Resources[]` | 单层 |
| `eas DescribeService` | `.Service` | 单个对象 |
| `eas describe-service-event` | `.Events[]` | 单层 |
| `vpc DescribeVpcs` | `.Vpcs.Vpc[]` | ⚠️ 双层 |
| `vpc DescribeVSwitches` | `.VSwitches.VSwitch[]` | ⚠️ 双层 |
| `ecs DescribeSecurityGroups` | `.SecurityGroups.SecurityGroup[]` | ⚠️ 双层 |
| `nlb ListLoadBalancers` | `.LoadBalancers[]` | 单层 |

## jq 示例

```bash
aliyun aiworkspace list-workspaces --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills | jq -r '.Workspaces[] | "\(.WorkspaceId)\t\(.WorkspaceName)"'
aliyun eas list-gateway --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills | jq -r '.Gateways[] | "\(.GatewayId)\t\(.GatewayName)"'
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills | jq -r '.Vpcs.Vpc[] | "\(.VpcId)\t\(.VpcName)"'
```

## CLI 命令参考

### 参数命名规则

| 命令类型 | 参数名 | 示例 |
|---------|--------|------|
| 列表类/创建类 | `--region` | `ListServices`, `CreateService` |
| 针对单个服务 | `--cluster-id` | `DescribeService`, `DeleteService` |

### 常用命令

```bash
aliyun aiworkspace list-workspaces --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun aiworkspace list-images --verbose true --labels 'system.official=true,system.supported.eas=true' --page-size 100 --user-agent AlibabaCloud-Agent-Skills
aliyun eas describe-machine-spec --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun eas list-resources --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun eas list-gateway --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun eas describe-gateway --cluster-id cn-hangzhou --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills
aliyun eas create-service --region cn-hangzhou --body "$(cat service.json)" --user-agent AlibabaCloud-Agent-Skills
aliyun eas describe-service --cluster-id cn-hangzhou --service-name my_service --user-agent AlibabaCloud-Agent-Skills
```

## 权限列表

详见 [RAM 权限策略](ram-policies.md)

## 常用 GPU 规格

| 规格 | GPU | CPU | 内存 | 适用场景 |
|------|-----|-----|------|---------|
| `ecs.gn6i-c4g1.xlarge` | 1× T4 | 4 | 16Gi | 小模型推理 |
| `ecs.gn6i-c8g1.2xlarge` | 1× T4 | 8 | 32Gi | 中等模型 |
| `ecs.gn7-c12g1.12xlarge` | 4× A10 | 12 | 192Gi | 大模型推理 |
