# E-HPC Instant作业技能所需的 RAM 权限策略

E-HPC Instant作业技能所需的 RAM 权限说明。

## 权限列表

| 权限 | 操作类型 | 描述 |
|------|----------|------|
| `ehpc:AddImage` | 写入 | 添加自定义镜像 |
| `ehpc:CreateJob` | 写入 | 创建作业 |
| `ehpc:CreateImageByExecutor` | 写入 | 通过执行器创建镜像 |
| `ehpc:DeleteJobs` | 写入 | 删除作业 |
| `ehpc:DeleteJobRecords` | 写入 | 删除作业记录 |
| `ehpc:DescribeJobMetricData` | 查询 | 查询作业监控数据 |
| `ehpc:DescribeJobMetricLast` | 查询 | 查询作业最新监控指标 |
| `ehpc:DescribeJobResults` | 查询 | 查询作业结果 |
| `ehpc:GetAppVersions` | 查询 | 获取应用版本信息 |
| `ehpc:GetImage` | 查询 | 获取镜像详情 |
| `ehpc:GetJob` | 查询 | 获取作业详情 |
| `ehpc:GetLoginUrlForExecutor` | 查询 | 获取执行器登录 URL |
| `ehpc:GetGlobalResourceLast` | 查询 | 获取全局资源最新状态 |
| `ehpc:GetGlobalResourceStatistic` | 查询 | 获取全局资源统计信息 |
| `ehpc:ListImages` | 查询 | 列出镜像 |
| `ehpc:ListJobExecutors` | 查询 | 列出作业执行器 |
| `ehpc:ListJobs` | 查询 | 列出作业 |
| `ehpc:RemoveImage` | 写入 | 移除镜像 |
| `ehpc:SynchronizeApp` | 写入 | 同步应用 |
| `ehpc:ListRegions` | 查询 | 列出可用地域 |
| `ehpc:ListAvailableFileSystems` | 查询 | 列出可用文件系统 |
| `ecs:DescribeImages` | 查询 | 查询 ECS 镜像列表 |
| `ecs:DescribeSecurityGroups` | 查询 | 查询安全组列表 |
| `vpc:DescribeVpcs` | 查询 | 查询 VPC 列表 |
| `vpc:DescribeVSwitches` | 查询 | 查询交换机列表 |
| `vpc:DescribeEipAddresses` | 查询 | 查询弹性公网 IP 列表 |
| `tag:ListTagKeys` | 查询 | 列出标签键 |
| `tag:ListTagValues` | 查询 | 列出标签值 |
| `cms:QueryMetricList` | 查询 | 查询云监控指标数据 |
| `oss:ListBuckets` | 查询 | 列出 OSS 存储桶 |
| `ram:GetRole` | 查询 | 获取 RAM 角色信息 |

## 最小权限策略

当您仅需要即时作业功能时，使用此策略：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ehpc:AddImage",
        "ehpc:CreateJob",
        "ehpc:CreateImageByExecutor",
        "ehpc:DeleteJobs",
        "ehpc:DeleteJobRecords",
        "ehpc:DescribeJobMetricData",
        "ehpc:DescribeJobMetricLast",
        "ehpc:DescribeJobResults",
        "ehpc:GetAppVersions",
        "ehpc:GetImage",
        "ehpc:GetJob",
        "ehpc:GetLoginUrlForExecutor",
        "ehpc:GetGlobalResourceLast",
        "ehpc:GetGlobalResourceStatistic",
        "ehpc:ListImages",
        "ehpc:ListJobExecutors",
        "ehpc:ListJobs",
        "ehpc:RemoveImage",
        "ehpc:SynchronizeApp",
        "ehpc:ListRegions",
        "ehpc:ListAvailableFileSystems"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeImages",
        "ecs:DescribeSecurityGroups",
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "tag:ListTagKeys",
        "tag:ListTagValues"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "cms:QueryMetricList",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "oss:ListBuckets",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "ram:GetRole",
      "Resource": "*"
    }
  ]
}
```

## 完整权限策略（推荐）

推荐在生产环境中使用，包含额外的查询和监控权限：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ehpc:AddImage",
        "ehpc:CreateJob",
        "ehpc:CreateImageByExecutor",
        "ehpc:DeleteJobs",
        "ehpc:DeleteJobRecords",
        "ehpc:DescribeJobMetricData",
        "ehpc:DescribeJobMetricLast",
        "ehpc:DescribeJobResults",
        "ehpc:GetAppVersions",
        "ehpc:GetImage",
        "ehpc:GetJob",
        "ehpc:GetLoginUrlForExecutor",
        "ehpc:GetGlobalResourceLast",
        "ehpc:GetGlobalResourceStatistic",
        "ehpc:ListImages",
        "ehpc:ListJobExecutors",
        "ehpc:ListJobs",
        "ehpc:RemoveImage",
        "ehpc:SynchronizeApp",
        "ehpc:ListRegions",
        "ehpc:ListAvailableFileSystems"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeImages",
        "ecs:DescribeSecurityGroups",
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "tag:ListTagKeys",
        "tag:ListTagValues"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "cms:QueryMetricList",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "oss:ListBuckets",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "ram:GetRole",
      "Resource": "*"
    }
  ]
}
```

> **注意：** `ehpc:DescribeJobMetricData` 和 `ehpc:DescribeJobMetricLast` 用于查询作业运行时的监控数据，有助于跟踪作业执行进度和资源使用情况。`ehpc:GetGlobalResourceLast` 和 `ehpc:GetGlobalResourceStatistic` 用于查看全局资源的使用状态和统计信息。`ecs:DescribeImages` 和 `ecs:DescribeSecurityGroups` 用于创建作业时选择镜像和安全组。`vpc:DescribeVpcs`、`vpc:DescribeVSwitches` 和 `vpc:DescribeEipAddresses` 用于配置作业的网络环境。`cms:QueryMetricList` 用于查询云监控指标数据。`oss:ListBuckets` 用于列出可用的 OSS 存储桶。`ram:GetRole` 用于获取服务关联角色信息。

## 权限验证命令

附加策略后，验证权限是否正确：

```bash
# 验证 E-HPC 作业列表查询权限
aliyun ehpcinstant ListJobs \
  --region-id cn-hangzhou \
  --PageSize 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill

# 验证 E-HPC 镜像列表查询权限
aliyun ehpcinstant ListImages \
  --region-id cn-hangzhou \
  --PageSize 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

如果所有命令均成功返回数据，则说明权限已正确配置。

## 常见权限错误与排查

### 错误：`Forbidden.RAM` / `NoPermission`

**原因：** RAM 用户没有所需的权限。

**解决方案：**
1. 登录 [RAM 控制台](https://ram.console.aliyun.com/)
2. 找到目标 RAM 用户
3. 点击"添加权限"
4. 选择"自定义策略"并粘贴上述最小权限策略 JSON
5. 或选择系统策略：`AliyunEHPCFullAccess` + `AliyunECSReadOnlyAccess` + `AliyunVPCReadOnlyAccess`（更宽泛的权限）

### 错误：`ehpc:CreateJob` 上的 `Forbidden`

**原因：** 缺少 E-HPC 作业创建权限。

**解决方案：** 确保策略中包含 `ehpc:CreateJob` 操作。

### 错误：`ehpc:ListJobs` 上的 `Forbidden`

**原因：** 缺少 E-HPC 作业查询权限。

**解决方案：** 确保策略中包含 `ehpc:ListJobs` 和 `ehpc:GetJob` 操作。作业管理流程需要这些权限来查询和获取作业状态。

### 错误：`InvalidAccount.NotFound`

**原因：** AccessKey 不正确或账号不存在。

**解决方案：**
- 检查 AccessKey ID 是否正确
- 在 RAM 控制台中验证 AccessKey 是否处于启用状态
- 在当前会话外使用 `aliyun configure` 交互式配置或通过环境变量重新配置凭据

### 使用预定义系统策略

如果自定义策略不方便，可以直接附加以下系统策略：

| 系统策略 | 描述 |
|----------|------|
| `AliyunEHPCFullAccess` | E-HPC 完整权限（包括 CreateJob、ListJobs、ListImages 等） |
| `AliyunECSReadOnlyAccess` | ECS 只读权限（包括 DescribeImages、DescribeSecurityGroups 等） |
| `AliyunVPCReadOnlyAccess` | VPC 只读权限（包括 DescribeVpcs、DescribeVSwitches 等） |

附加方法：
```bash
# 通过 RAM 控制台或 CLI 附加
aliyun ram attach-policy-to-user \
  --policy-type System \
  --policy-name AliyunEHPCFullAccess \
  --user-name <你的RAM用户名> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

> **安全建议：** 在生产环境中，建议使用自定义最小权限策略而非完整访问的系统策略，以遵循最小权限原则。