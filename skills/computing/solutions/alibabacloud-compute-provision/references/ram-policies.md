# RAM 权限清单

## 本 Skill 所需权限（required_permissions）

以下按产品分组列出本 Skill 执行所需的全部 RAM 权限。每条权限标注类型（读 / 写）和用途。

如果开放更多权限，Skill 可能通过 search_and_format 找到合适的 API 进行调用，用以完成任务。

### ECS（Elastic Compute Service）

| 权限 | 类型 | 用途 |
|------|------|------|
| `ecs:DescribeRegions` | 读 | 查询可用地域列表 |
| `ecs:DescribeZones` | 读 | 查询地域下可用区列表 |
| `ecs:DescribeInstanceTypes` | 读 | 查询实例规格列表（vCPU、内存、GPU 等） |
| `ecs:DescribeInstanceTypeFamilies` | 读 | 查询实例规格族信息 |
| `ecs:DescribeRecommendInstanceType` | 读 | 获取推荐实例规格 |
| `ecs:DescribeAvailableResource` | 读 | 查询可用区库存与可售规格 |
| `ecs:DescribeImages` | 读 | 查询可用镜像列表 |
| `ecs:DescribePrice` | 读 | 查询实例价格（成本估算） |
| `ecs:DescribeInstances` | 读 | 查询已创建的实例信息 |
| `ecs:DescribeInvocations` | 读 | 查询 Cloud Assistant 命令执行状态 |
| `ecs:DescribeInvocationResults` | 读 | 查询 Cloud Assistant 命令执行结果 |
| `ecs:RunInstances` | 写 | 创建 ECS 实例 |
| `ecs:DeleteInstances` | 写 | 释放 ECS 实例 |
| `ecs:RunCommand` | 写 | 通过 Cloud Assistant 在实例上执行脚本 |
| `ecs:CreateSecurityGroup` | 写 | 创建安全组 |
| `ecs:AuthorizeSecurityGroup` | 写 | 配置安全组入方向规则 |
| `ecs:AuthorizeSecurityGroupEgress` | 写 | 配置安全组出方向规则 |
| `ecs:DeleteSecurityGroup` | 写 | 删除安全组（资源清理） |

### VPC（Virtual Private Cloud）

| 权限 | 类型 | 用途 |
|------|------|------|
| `vpc:DescribeVpcs` | 读 | 查询已有 VPC 列表 |
| `vpc:DescribeVSwitches` | 读 | 查询已有交换机列表 |
| `vpc:CreateVpc` | 写 | 创建 VPC |
| `vpc:DeleteVpc` | 写 | 删除 VPC（资源清理） |
| `vpc:CreateVSwitch` | 写 | 创建交换机 |
| `vpc:DeleteVSwitch` | 写 | 删除交换机（资源清理） |

### FC（Function Compute）

| 权限                             | 类型 | 用途 |
|--------------------------------|------|------|
| `fc:GetFunction`               | 读 | 查询函数详情 |
| `fc:ListFunctions`           | 读 | 列出已有函数 |
| `fc:CreateFunction`          | 写 | 创建函数 |
| `fc:DeleteFunction`          | 写 | 删除函数（资源清理） |
| `fc:InvokeFunction`          | 写 | 调用函数执行任务 |
| `fc:PutAsyncInvokeConfig`    | 写 | 配置异步调用参数 |
| `fc:DeleteAsyncInvokeConfig` | 写 | 删除异步调用配置（资源清理） |
| `fc:GetAsyncTask`            | 读 | 查询异步任务执行状态与结果 |

### STS（Security Token Service）

| 权限 | 类型 | 用途 |
|------|------|------|
| `sts:GetCallerIdentity` | 读 | 获取当前调用者身份（用于构建 FC 端点地址） |

### ACK（Container Service for Kubernetes）

| 权限 | 类型 | 用途 |
|------|------|------|
| `cs:DescribeRegions` | 读 | 查询 ACK 可用地域 |
| `cs:DescribeClustersV1` | 读 | 查询集群列表 |
| `cs:DescribeClusterDetail` | 读 | 查询集群详情与状态 |
| `cs:DescribeClusterNodePools` | 读 | 查询集群节点池列表 |
| `cs:DescribeClusterUserKubeconfig` | 读 | 获取集群 kubeconfig（用于 kubectl 操作） |
| `cs:CreateCluster` | 写 | 创建 ACK 集群 |
| `cs:DeleteCluster` | 写 | 删除 ACK 集群（资源清理） |
| `cs:CreateClusterNodePool` | 写 | 创建集群节点池 |

### PAI-DLC（Platform for AI — Deep Learning Containers）

| 权限 | 类型 | 用途 |
|------|------|------|
| `paidlc:ListEcsSpecs` | 读 | 查询 DLC 可用实例规格列表 |
| `paidlc:ListJobs` | 读 | 查询训练任务列表 |
| `paidlc:GetJob` | 读 | 查询训练任务详情与状态 |
| `paidlc:GetPodLogs` | 读 | 获取训练 Pod 日志 |
| `paidlc:GetPodEvents` | 读 | 获取训练 Pod 事件（诊断用） |
| `paidlc:CreateJob` | 写 | 创建训练任务 |
| `paidlc:DeleteJob` | 写 | 删除训练任务 |
| `paidlc:StopJob` | 写 | 停止运行中的训练任务 |

### PAI-Workspace

| 权限 | 类型 | 用途 |
|------|------|------|
| `paiworkspace:ListWorkspaces` | 读 | 查询已有工作空间列表 |
| `paiworkspace:ListImages` | 读 | 查询可用镜像列表（DLC 镜像） |
| `paiworkspace:CreateWorkspace` | 写 | 创建工作空间 |
