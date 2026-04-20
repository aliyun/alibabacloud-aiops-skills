# RAM 权限策略列表

本 Skill 涉及的所有 API 及对应的 RAM 权限要求。

> **策略名称说明**：Lindorm 官方系统策略为 `AliyunLindormReadOnlyAccess`（只读）、`AliyunLindormFullAccess`（完全）、`AliyunLindormDevelopAccess`（开发者）。

## Lindorm API 权限

| API Action | 权限策略 | 说明 |
|------------|---------|------|
| `DescribeRegions` | `AliyunLindormReadOnlyAccess` | 查询地域列表 |
| `GetLindormInstanceList` | `AliyunLindormReadOnlyAccess` | 查询实例列表 |
| `GetLindormInstance` | `AliyunLindormReadOnlyAccess` | 查询实例详情 |
| `GetLindormV2InstanceDetails` | `AliyunLindormReadOnlyAccess` | 查询 V2 实例详情 |
| `GetLindormInstanceEngineList` | `AliyunLindormReadOnlyAccess` | 查询实例引擎列表 |
| `GetLindormFsUsedDetail` | `AliyunLindormReadOnlyAccess` | 查询存储详情（V1） |
| `GetLindormV2StorageUsage` | `AliyunLindormReadOnlyAccess` | 查询存储详情（V2） |
| `GetInstanceIpWhiteList` | `AliyunLindormReadOnlyAccess` | 查询 IP 白名单 |

## 云监控 API 权限

| API Action | 权限策略 | 说明 |
|------------|---------|------|
| `DescribeMetricMetaList` | `AliyunCloudMonitorReadOnlyAccess` | 查询监控指标列表 |
| `DescribeMetricLast` | `AliyunCloudMonitorReadOnlyAccess` | 查询最新监控数据 |
| `DescribeMetricData` | `AliyunCloudMonitorReadOnlyAccess` | 查询历史监控数据 |

## 系统权限策略

### 只读权限（推荐）

> 本 Skill 为只读操作场景，仅需以下权限。

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hitsdb:DescribeRegions",
        "hitsdb:GetLindormInstanceList",
        "hitsdb:GetLindormInstance",
        "hitsdb:GetLindormV2InstanceDetails",
        "hitsdb:GetLindormInstanceEngineList",
        "hitsdb:GetLindormFsUsedDetail",
        "hitsdb:GetLindormV2StorageUsage",
        "hitsdb:GetInstanceIpWhiteList"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricMetaList",
        "cms:DescribeMetricLast",
        "cms:DescribeMetricData"
      ],
      "Resource": "*"
    }
  ],
  "Version": "1"
}
```

> ℹ️ **关于写操作权限**：本 Skill 不执行任何写操作。如用户确实需要创建/修改/删除实例等写操作，请直接授予官方系统策略 `AliyunLindormFullAccess`。

## 权限配置步骤

### 通过 RAM 控制台配置

1. 登录 [RAM 控制台](https://ram.console.aliyun.com/)
2. 创建 RAM 用户或使用现有用户
3. 在用户详情页，点击"添加权限"
4. 选择权限策略：
   - 只读：`AliyunLindormReadOnlyAccess` + `AliyunCloudMonitorReadOnlyAccess`
   - 完全：`AliyunLindormFullAccess`
5. 确认授权

### 通过 CLI 配置

```bash
# 创建 RAM 用户
aliyun ram create-user --user-name lindorm-operator

# 添加只读权限
aliyun ram attach-policy-to-user \
  --user-name lindorm-operator \
  --policy-name AliyunLindormReadOnlyAccess \
  --policy-type System

aliyun ram attach-policy-to-user \
  --user-name lindorm-operator \
  --policy-name AliyunCloudMonitorReadOnlyAccess \
  --policy-type System
```

## 权限验证

执行以下命令验证权限是否配置正确：

```bash
# 测试 Lindorm 权限
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai

# 测试云监控权限
aliyun cms describe-metric-meta-list --namespace acs_lindorm
```

如果返回 `Forbidden.RAM` 错误，说明权限不足，需按上述步骤添加权限。

## 权限不足时的处理流程

1. 检查当前用户权限：在 RAM 控制台查看用户授权策略
2. 确认需要的权限：参考上述 API 权限列表
3. 申请权限：联系主账号管理员添加对应权限策略
4. 验证权限：重新执行测试命令确认权限生效