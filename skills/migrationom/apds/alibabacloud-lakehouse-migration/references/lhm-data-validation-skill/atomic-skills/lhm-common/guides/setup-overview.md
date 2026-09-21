## LHM 配置引导

请按以下顺序完成配置，我会逐步引导你。每一步完成后我会自动保存，中途退出也不会丢失已填内容。

### Step 1: API 凭证

你需要阿里云 AccessKey 来调用 LHM 服务。

**获取方式：**
1. 登录 [阿里云 AccessKey 管理页面](https://ram.console.aliyun.com/manage/ak)
2. 创建 AccessKey（强烈建议使用 RAM 子账号，避免使用主账号 AK）
3. 确保该 AK 有 LHM（湖仓迁移中心）的操作权限

准备好后，告诉我你的 AK ID 和 Region 选择（杭州/新加坡）。

> 杭州和新加坡的区别：LHM 的中心节点区域，一般选择与数据集群相同的地域。

### Step 2: DataWorks 资源组

资源组提供校验任务的计算资源（CU），是数据校验的基础设施。

**操作步骤：**
1. 开通 DataWorks 服务：进入 [DataWorks 控制台](https://dataworks.console.aliyun.com/welcome)
2. 创建 Serverless 资源组：进入 [资源组管理](https://dataworks.console.aliyun.com/resource/list)
3. 网络配置：在资源组详情的"网络设置" → "数据调度 & 数据集成"中绑定待校验集群的 VPC 网络
4. CU 配额：在"配额管理"中设置 CU 上限（建议 20-50，防止对集群负载过大）

> 建议单独创建资源组用于迁移校验，不要与生产业务共用。

完成后告诉我资源组 ID 和名称。详见 `guides/resource-group-config.md`。

### Step 3: 绑定资源组到 LHM

将创建好的 DataWorks 资源组绑定到湖仓迁移中心。

**操作步骤：**
1. 进入 [LHM 资源组与服务代理管理](https://apds.console.aliyun.com/lake-house/resource-agent)
2. 点击「绑定资源组」
3. 选择刚创建的 Serverless 资源组

> 当前仅支持绑定一个资源组。

### Step 4: 服务代理（Agent）

服务代理是部署在 ECS 上的客户端程序，负责连接数据源进行即席查询和元数据探查。

**ECS 要求：**
- x86 架构
- CentOS 7.9/7.6 64位 或 Alibaba Cloud Linux 2/3 64位
- 最小 2C4G，建议 4C8G
- 必须与源端和目标端数据源网络打通（最优方案：同 VPC 同交换机）
- 一般无需开通公网

**操作步骤：**
1. 开通 [私网连接服务](https://www.aliyun.com/product/network/privatelink)
2. 准备 ECS 实例（建议与目标数据库同地域同可用区）
3. 确保 RAM 权限：需要 `ecs:DescribeInvocations`、`ecs:DescribeCloudAssistantStatus`、`ecs:RunCommand`
4. 在 [LHM 服务代理管理](https://apds.console.aliyun.com/lake-house/resource-agent) 点击「申请 License」
5. 点击「服务代理安装」，选择 ECS 实例，等待自动部署
6. 确认代理状态为"在线"

> 通过私网连接打通网络会在账号下创建反向终端节点，可能产生费用，使用完需手动释放。
> 自动部署目前仅支持阿里云 ECS。

完成后告诉我 Agent 名称和 ECS 实例 ID。详见 `guides/agent-config.md`。

### Step 5: 数据源

在 LHM 控制台添加需要校验的源端和目标端数据源。

**操作步骤：**
1. 进入 [LHM 数据源管理](https://apds.console.aliyun.com/lake-house/datasource-manage)
2. 点击新建，分别添加源端和目标端数据源
3. 记录每个数据源的 ID 和名称

**支持的数据源类型：**
Hive、MaxCompute、ClickHouse、Hologres、Synapse、Databricks、StarRocks、Doris、Redshift、MySQL、Athena

完成后告诉我每个数据源的：别名（你起一个好记的名字）、ds_id、ds_name、ds_type。详见 `guides/data-source-config.md`。

### Step 6: 验证

所有配置完成后，我会自动运行前置检查，确认：
- API 凭证有效且 LHM 服务可达
- 资源组已绑定且状态正常
- 服务代理在线
- 数据源已在配置文件中定义（连通性验证待接入 API）

如果有任何问题，我会告诉你具体哪一步需要修复。
