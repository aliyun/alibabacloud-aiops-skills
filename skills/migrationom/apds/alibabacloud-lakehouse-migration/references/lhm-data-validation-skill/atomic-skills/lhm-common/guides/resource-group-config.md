## 资源组配置指南

### 什么是资源组

DataWorks Serverless 资源组，为 LHM 提供数据迁移、调度、校验等功能的**计算和调度能力**。

资源组提供的 CU（Compute Unit）用于校验任务的比对计算，同时作为网络桥梁打通待校验集群的 VPC。

### 创建步骤

**Step 1: 开通 DataWorks 服务**
1. 进入 [DataWorks 控制台](https://dataworks.console.aliyun.com/welcome)
2. 选择目标地域（建议与待迁移集群相同地域）
3. 选择版本和时长

**Step 2: 创建 Serverless 资源组**
1. 进入 [资源组管理](https://dataworks.console.aliyun.com/resource/list)
2. 点击创建资源组
3. 配置：
   - 资源组名称和备注
   - 选择已打通集群网络的 VPC 和交换机
   - 创建服务关联角色（如未创建）

**Step 3: 配置资源组**
1. 网络配置：绑定额外的 VPC/VSW
2. CU 配额管理：设置上限（建议 <= 50，经验值 20）
3. 运维日志：可在资源组详情页查看作业日志

**Step 4: 绑定到 LHM**
1. 进入 [LHM 资源组与服务代理管理](https://apds.console.aliyun.com/lake-house/resource-agent)
2. 点击「绑定资源组」→ 选择刚创建的资源组

### 注意事项

- 强烈建议**单独创建资源组**用于迁移校验，不要与生产业务共用
- CU 上限设置过高可能导致对源端/目标端集群负载过大
- 选择 VPC/VSW 时必须确保已提前与集群完成网络打通
- 当前仅支持绑定一个资源组

### 状态说明

| 状态 | 含义 | 是否可用 |
|------|------|---------|
| Normal | 正常 | 可用 |
| Stop | 冻结（已到期） | 不可用 |
| Creating | 创建中 | 等待完成 |
| Updating | 更新中（扩容/缩容） | 等待完成 |
| Starting | 启动中 | 等待完成 |
| CreateFailed | 创建失败 | 不可用，需检查错误日志 |
| UpdateFailed | 更新失败 | 不可用，需检查错误日志 |
| Deleted / Deleting | 已删除 / 删除中 | 不可用 |
| Freezed | 冻结 | 不可用，需续费或解冻 |
| Timeout | 操作超时 | 不可用 |

官方文档：https://help.aliyun.com/zh/cmh/lakehouse-migration/user-guide/resource-group-management
