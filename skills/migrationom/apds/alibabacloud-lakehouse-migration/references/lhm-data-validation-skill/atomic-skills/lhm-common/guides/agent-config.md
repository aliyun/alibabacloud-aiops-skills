## 服务代理配置指南

### 什么是服务代理

服务代理（Agent）是部署在 ECS 内网上的客户端程序。LHM 通过它实现：
- 数据源连接测试
- 元数据探查
- 数据校验的即席查询执行

Agent 必须与源端和目标端数据源网络打通，是 LHM 校验链路中不可缺少的组件。

### ECS 配置要求

| 项目 | 要求 |
|------|------|
| 架构 | x86 |
| 操作系统 | CentOS 7.9/7.6 64位 或 Alibaba Cloud Linux 2/3 64位 |
| 规格 | 最小 2C4G，建议 4C8G |
| 系统盘 | 最小 20GiB，建议 40GiB |
| 地域 | 建议与目标数据库同地域同可用区 |
| 公网 | 无需且不建议开通 |

### 网络要求

必须确保 Agent ECS 与源端/目标端数据源的网络完全连通。

| 场景 | 方案 |
|------|------|
| 同 VPC 同交换机（最优） | 无需额外配置 |
| 同 VPC 不同交换机 | 检查路由表和安全组放通策略 |
| 跨 VPC | 通过 VPC 对等连接、私网连接、云企业网等打通 |

### 安装步骤

1. 开通 [私网连接服务](https://www.aliyun.com/product/network/privatelink)
2. 确认 RAM 权限（最小权限集）：
   - `ecs:DescribeInvocations`
   - `ecs:DescribeCloudAssistantStatus`
   - `ecs:RunCommand`
   - 或直接授予 `AliyunECSAssistantFullAccess`
3. 进入 [服务代理管理](https://apds.console.aliyun.com/lake-house/resource-agent)
4. 点击「申请 License」→ 系统自动生成
5. 点击「服务代理安装」→ 填名称 → 选 ECS → 自动部署
6. 确认状态为"在线"

### 排查问题

客户端部署路径：`/home/agent/meta/{代理名称}/`
- 启动日志：`start.log`
- 代理查询日志：`/var/log/agent/meta/{代理名称}/application*.log`

### 状态说明

| 状态 | 含义 | 是否可用 |
|------|------|---------|
| Online | 在线 | 可用 |
| Offline | 离线 | 不可用，检查 ECS 上 Agent 进程 |
| Not_Started | License 已申请，未安装 | 不可用，需执行安装步骤 |
| Started | 已启动，网络未连接 | 不可用，检查网络配置 |
| Installing | 安装中 | 不可用，等待完成 |
| Stopped | 已停止 | 不可用，需重启 Agent |
| Install_Failed | 安装失败 | 不可用，检查 ECS 和日志 |

### 注意事项

- 系统默认使用列表中**第一个在线**的 Agent 进行代理查询
- 私网连接产生的反向终端节点**可能产生费用**，使用完需手动释放
- 自动部署仅支持阿里云创建的 ECS

官方文档：https://help.aliyun.com/zh/cmh/lakehouse-migration/user-guide/service-agent-management
