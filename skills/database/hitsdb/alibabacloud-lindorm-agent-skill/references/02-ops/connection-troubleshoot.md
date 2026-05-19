# 连接问题排查场景

当用户反馈"无法连接 Lindorm 实例"、"连接超时"等问题时，按本指南执行排查。

## 触发条件

用户的典型表达：
- "连不上实例"
- "连接超时"
- "无法访问 Lindorm"
- "白名单配置对吗？"
- "为什么连接被拒绝？"

## 排查原则

连接问题排查采用**分层排查**策略：实例状态 → 白名单 → 网络配置，逐层定位问题。

输出格式：**问题定位 → 根因分析 → 解决方案**

## 执行流程

### 步骤 1：检查实例状态

**目的**：确认实例是否正常运行。

**执行命令**：

```bash
aliyun hitsdb get-lindorm-instance \
    --instance-id <instance-id>
```

**检查要点**：

| 实例状态 | 含义 | 能否连接 | 解决方案 |
|---------|------|:--------:|----------|
| `ACTIVATION` | 运行中 | ✅ 可以 | 继续排查其他项 |
| `CREATING` | 创建中 | ❌ 等待 | 等待实例创建完成（通常 10-30 分钟） |
| `MAINTAINING` | 维护中 | ⚠️ 可能中断 | 等待维护完成或联系技术支持 |
| `STOPPED` | 已停止 | ❌ 需要启动 | 启动实例后再连接 |
| `DELETED` | 已释放 | ❌ 无法恢复 | 实例已释放，无法连接 |
| `CLASS_CHANGING` | 变配中 | ⚠️ 可能中断 | 等待变配完成 |

**输出示例**：

```
【步骤 1：实例状态检查】

✅ 实例状态正常
- 实例 ID：ld-uf6l5kr48wqm6rf1h
- 状态：ACTIVATION（运行中）
- 创建时间：2025-01-15 10:30:00

继续排查白名单配置...
```

如果状态异常：

```
【步骤 1：实例状态检查】

❌ 实例状态异常
- 实例 ID：ld-uf6l5kr48wqm6rf1h
- 状态：CREATING（创建中）

【根因】实例尚未创建完成，无法连接

【解决方案】
- 等待 10-30 分钟，实例创建完成后自动变为 ACTIVATION 状态
- 可通过 get_instance 命令持续检查状态
```

---

### 步骤 2：检查白名单配置

**目的**：确认客户端 IP 是否在白名单中。

**执行命令**：

```bash
aliyun hitsdb get-instance-ip-white-list \
    --instance-id <instance-id>
```

**检查要点**：

- 白名单中是否包含客户端 IP？
- 白名单格式是否正确？
  - 单个 IP：`192.168.1.100`
  - IP 段：`192.168.1.0/24`
  - 公网访问：`0.0.0.0/0`（⚠️ 不推荐，安全风险高）
- 内网访问需要：同 VPC 或 VPC 网段在白名单中

**输出示例**：

```
【步骤 2：白名单检查】

当前白名单配置：
- 10.0.0.0/8（内网 VPC 网段）
- 172.16.1.100（特定 IP）

【检查结果】
- 您的客户端 IP：192.168.1.50
- ❌ 未在白名单中

【根因】客户端 IP 不在白名单中，连接被拒绝

【解决方案】
1. 方案一：将客户端 IP 加入白名单
   
   📍 精确路径：
   1. 登录 [Lindorm 控制台](https://lindorm.console.aliyun.com/)
   2. 在实例列表页，单击**目标实例ID**
   3. 在左侧导航栏，单击**访问控制** → **白名单**
   4. 点击"修改"添加客户端 IP：
      - 单个 IP：192.168.1.50
      - IP 段：192.168.1.0/24

2. 方案二：使用同 VPC 内的 ECS 访问
   - 确保 ECS 与 Lindorm 在同一 VPC
   - 白名单配置为 VPC 网段（如 10.0.0.0/8）

如需更多细节，可参考官方白名单配置指南：
https://help.aliyun.com/zh/lindorm/getting-started/configure-a-whitelist

需要帮您查看网络配置吗？
```

---

### 步骤 3：检查网络配置

**目的**：确认网络类型和访问方式是否匹配。

**执行命令**：

```bash
aliyun hitsdb get-lindorm-instance \
    --instance-id <instance-id>
```

**检查要点**：

从实例详情中提取网络配置：
- `NetworkType`：网络类型（`vpc`）
- `VpcId`：VPC ID
- `VswitchId`：交换机 ID

**网络类型与访问方式**：

| 网络类型 | 访问方式 | 要求 | 连接地址特征 |
|---------|---------|------|---------------|
| `vpc` | **内网访问** | 客户端在同 VPC 内 | V1: `-vpc.lindorm.rds.aliyuncs.com`；V2: `-vpc.lindorm.aliyuncs.com`（INTRANET） |
| `vpc` | **公网访问** | 已开通公网地址 + 白名单包含公网 IP | V1: `-pub.lindorm.rds.aliyuncs.com`；V2: `-pub.lindorm.aliyuncs.com`（INTERNET） |

**输出示例**：

```
【步骤 3：网络配置检查】

网络配置：
- 网络类型：VPC
- VPC ID：vpc-uf6xxxxx
- 交换机 ID：vsw-uf6xxxxx

【访问方式判断】
- 您的客户端：公网 IP（182.92.xxx.xxx）
- 实例配置：VPC 内网

【根因】实例为 VPC 内网访问，客户端在公网，无法直连

【解决方案】
1. 方案一：使用同 VPC 内的 ECS 访问
   - 在同 VPC 内创建 ECS 实例
   - 通过 ECS 内网 IP 访问 Lindorm

2. 方案二：开通公网连接地址（推荐公网用户使用）
   
   📍 精确路径：
   1. 控制台：https://lindorm.console.aliyun.com/
   2. 点击实例 ID "ld-xxx"
   3. 左侧菜单：**配置与管理** → **数据库连接**
   4. 找到对应引擎，点击**申请公网连接地址**
   5. 等待公网地址生成（通常 1-3 分钟）
   6. **配置与管理** → **访问控制** → **白名单** → 添加客户端公网 IP

   > ⚠️ 开通公网地址不等于绑定 EIP。Lindorm 的公网访问是通过"申请公网连接地址"实现的，无需绑定 EIP。

3. 方案三：配置 VPN/专线连接
   - 通过 VPN 或专线将客户端网络与 VPC 打通

如需更多细节，可参考官方连接指南：
https://help.aliyun.com/zh/lindorm/getting-started/connect-to-an-instance
```

---

### 步骤 4：网络连通性测试（高级排查）

**目的**：使用网络工具（ping、telnet）验证网络连通性。

**⚠️ 前提条件**：前三步检查均正常，但仍无法连接。

#### 4.1 使用 ping 测试网络可达性（参考性）

**⚠️ 注意**：ping 测试仅供参考，**ping 不通不代表无法连接**。

**适用场景**：初步判断网络层连通性，但 Lindorm 可能禁用 ICMP 响应。

**操作步骤**：
```bash
# 从客户端机器执行
ping <lindorm-host>

# 示例
ping lindorm-xxx.lindorm.rds.aliyuncs.com
```

**结果判断**：

| 结果 | 含义 | 后续操作 |
|-----|------|----------|
| ✅ 正常响应 | 网络层可达 | 继续检查端口（步骤 4.2） |
| ❌ Request timeout | ICMP 被禁用或网络不通 | **继续用 telnet 测试端口，不要直接判定为网络不通** |
| ❌ Unknown host | DNS 解析失败 | 检查 DNS 配置或使用 IP 直接连接 |

**重要提示**：
- 云产品通常禁用 ICMP（ping）响应以提高安全性
- **ping 不通时，优先使用 `telnet/nc` 或客户端直接连接测试**
- 只有当 telnet 也失败时，才判定为网络连通性问题

**完整排查指南**：
- 官方文档：[使用 ping 命令检查连接](https://help.aliyun.com/zh/lindorm/support/run-the-ping-command-to-check-the-connection-between-an-ecs-instance-and-a-lindorm-instance)

#### 4.2 使用 telnet 测试端口连通性

**适用场景**：ping 通但仍无法连接，需要测试具体端口是否开放。

**操作步骤**：
```bash
# 测试宽表引擎 HBase API 端口
telnet <lindorm-host> 30020

# 测试宽表引擎 MySQL 协议端口（推荐）
telnet <lindorm-host> 33060

# 测试时序引擎端口
telnet <lindorm-host> 8242

# 测试搜索引擎端口
telnet <lindorm-host> 30070
```

**常用端口**：

端口请以 `SKILL.md` →「代码生成规范 / 端口号速查表」为准。

**结果判断**：

```bash
# ✅ 端口连通（正常）
Trying <ip>...
Connected to <host>.
Escape character is '^]'.

# ❌ 端口不通（异常）
Trying <ip>...
telnet: connect to address <ip>: Connection refused
```

**常见问题**：
- 端口不通 → 检查安全组规则是否开放对应端口
- 端口连通但连接失败 → 检查认证信息（用户名/密码/AccessKey）

**完整排查指南**：
- 官方文档：[使用 telnet 命令检查端口连通性](https://help.aliyun.com/zh/lindorm/support/run-the-telnet-command-to-check-the-connectivity-of-the-service-ports-of-lindorm)

#### 4.3 安全组规则检查

**适用场景**：ping 或 telnet 不通，需要检查 ECS 安全组。

**检查要点**：
1. ECS 出方向规则：允许访问 Lindorm IP 和端口
2. Lindorm 白名单：包含 ECS 的 IP

**配置示例**：
```
ECS 安全组出方向规则：
- 协议：TCP
- 端口范围：根据所用引擎/协议放通（端口见 SKILL.md →「代码生成规范 / 端口号速查表」）
- 目标：Lindorm 实例 IP 或 0.0.0.0/0

Lindorm 白名单：
- 添加 ECS 私网 IP 或 VPC 网段
```

---

## 常见问题与解决方案

### 问题 1：连接超时

**可能原因**：
1. 实例状态非 ACTIVATION
2. 网络不通（VPC/白名单问题）
3. 端口未开放或防火墙拦截

**排查步骤**：
1. 检查实例状态（步骤 1）
2. 检查白名单配置（步骤 2）
3. 检查网络配置（步骤 3）
4. 确认使用正确的连接地址和端口

---

### 问题 2：认证失败

**可能原因**：
1. 用户名或密码错误
2. AccessKey 无权限

**排查步骤**：
1. 确认用户名密码正确（Lindorm 控制台 → 账号管理）
2. 确认 AccessKey 有 Lindorm 操作权限（RAM 控制台 → 权限管理）

---

### 问题 3：公网无法访问

**可能原因**：
1. 未开通公网访问（未申请公网连接地址）
2. 白名单未包含公网 IP

**排查步骤**：
1. 确认实例已开通公网连接地址（Lindorm 控制台 → 配置与管理 → 数据库连接 → 查看是否有公网地址）
2. 确认白名单包含公网 IP（步骤 2）

---

### 问题 4：内网无法访问

**可能原因**：
1. 不在同一 VPC
2. 未配置 VPC 访问白名单

**排查步骤**：
1. 确认客户端在同 VPC 内（步骤 3）
2. 确认白名单包含 VPC 网段（步骤 2）

---

## 常见连接错误及解决方案

Agent 在遇到连接错误时，应该查询官方文档获取详细的解决方案：

**⭐ 重点文档**：
- **Lindorm 连接问题及解决方案**：https://help.aliyun.com/zh/lindorm/support/lindorm-connection-issues-and-solutions
- **Lindorm 连接错误及解决方案**：https://help.aliyun.com/zh/lindorm/support/lindorm-connection-errors-and-solutions

**常见错误类型**：

| 错误类型 | 示例错误信息 | 参考文档 |
|---------|------------|---------|
| **连接超时** | Connection timeout, SocketTimeoutException | 上述文档 + ping/telnet 排查 |
| **连接被拒绝** | Connection refused | 检查端口、安全组、白名单 |
| **认证失败** | Authentication failed | 检查用户名密码、AccessKey |
| **网络不可达** | Network is unreachable | 检查 VPC、路由表 |
| **DNS 解析失败** | Unknown host | 检查 DNS 配置 |

**特殊场景**：
- **Spark 访问连接超时**：https://help.aliyun.com/zh/lindorm/support/cause-analysis-of-connection-timout-problem-in-sparkonmc-access-to

---

## 连接地址获取

Lindorm 不同引擎有不同的连接地址。**务必根据客户端所在环境选择对应的地址**：

### 确认客户端环境

| 客户端位置 | 应使用的地址 | 地址特征 |
|-----------|-------------|----------|
| 阿里云 ECS（同 VPC） | 内网地址 | V1: `-vpc.lindorm.rds.aliyuncs.com`；V2: `-vpc.lindorm.aliyuncs.com`（Type=INTRANET） |
| 本地电脑 / 公网服务器 | 公网地址 | V1: `-pub.lindorm.rds.aliyuncs.com`；V2: `-pub.lindorm.aliyuncs.com`（Type=INTERNET） |
| 阿里云 ECS（跨 VPC） | 公网地址或云企业网 | 需额外配置网络打通 |

> ⚠️ **常见错误**：从公网环境使用 VPC 内网地址，导致连接超时。必须确认客户端所处环境后选择对应地址。

### 获取连接地址

**方法 1：阿里云控制台**

📍 精确路径：
1. 控制台：https://lindorm.console.aliyun.com/
2. 点击实例 ID "ld-xxx"
3. 左侧菜单：**配置与管理** → **数据库连接**
4. 查看各引擎的内网/公网连接地址
5. 如果没有公网地址，点击**申请公网连接地址**

> ⚠️ 开通公网地址不等于绑定 EIP。Lindorm 的公网访问是通过"申请公网连接地址"实现的，无需绑定 EIP。

**方法 2：通过 API 获取**

```bash
# V1/V2 通用：查询引擎连接端点
aliyun hitsdb get-lindorm-instance-engine-list --instance-id ld-xxx

# V2 专属：查询实例详情（含 ConnectAddressList）
aliyun hitsdb get-lindorm-v2-instance-details --instance-id ld-xxx
```

**`get-lindorm-instance-engine-list`（V1/V2 通用）**：
返回 `NetInfoList`，通过 `NetType` 判断网络类型：
- `NetType: "0"` → 公网地址（`-pub`）
- `NetType: "2"` → VPC 内网地址（`-vpc`）

**`get-lindorm-v2-instance-details`（仅 V2）**：
返回 `ConnectAddressList`，通过 `Type` 判断网络类型：
- `Type: INTERNET` → 公网地址（`-pub`）
- `Type: INTRANET` → VPC 内网地址（`-vpc`）

> 如果两个 API 返回中都没有公网地址（无 `NetType: "0"` 且无 `Type: INTERNET`），说明尚未开通公网，需在控制台申请。

### 开通公网访问

**前提**：需要从公网（本地电脑等）连接 Lindorm。

📍 操作路径：
1. 登录 [Lindorm 控制台](https://lindorm.console.aliyun.com/)
2. 在实例列表页，单击**目标实例ID**
3. 在左侧导航栏，单击**数据库连接**
4. 切换至目标引擎页签，单击右上角**开通公网地址**
5. 等待地址生成（1-3 分钟）
6. 在左侧导航栏，单击**访问控制** → **白名单** → 添加客户端公网 IP

> 💡 查看自己公网 IP：`curl ifconfig.me`

---

## 快速诊断命令

一键执行完整排查：

```bash
# 1. 检查实例状态
aliyun hitsdb get-lindorm-instance --instance-id ld-xxx

# 2. 检查白名单
aliyun hitsdb get-instance-ip-white-list --instance-id ld-xxx
```

---

## 完整排查清单

**基础检查（使用 API）**：

| 检查项 | 命令 | 期望结果 |
|--------|------|----------|
| **实例状态** | `aliyun hitsdb get-lindorm-instance --instance-id <id>` | `InstanceStatus = ACTIVATION` |
| **白名单配置** | `aliyun hitsdb get-instance-ip-white-list --instance-id <id>` | 包含客户端 IP 或 VPC 网段 |
| **网络类型** | `aliyun hitsdb get-lindorm-instance --instance-id <id>` | `NetworkType = vpc` |
| **VPC 匹配** | `aliyun hitsdb get-lindorm-instance --instance-id <id>` | 客户端与实例在同 VPC（内网访问） |
| **公网地址** | 控制台或 API 查看 | 已开通公网连接地址（非 EIP） |

**网络连通性测试（高级排查）**：

| 检查项 | 命令 | 期望结果 |
|--------|------|----------|
| **网络可达性** | `ping <host>` | 正常响应 |
| **端口连通性** | `telnet <host> <port>` | Connected |
| **DNS 解析** | `nslookup <host>` | 正确解析到 IP |
| **安全组规则** | 控制台查看 | 允许访问对应端口 |

---

## 官方文档索引（供 Agent 参考）

Agent 在处理连接问题时，**强烈建议**查询以下官方文档获取最新信息：

| 文档 | 链接 | 用途 |
|------|------|------|
| **Lindorm 连接问题及解决方案** | [点击查看](https://help.aliyun.com/zh/lindorm/support/lindorm-connection-issues-and-solutions) | ⭐ 常见连接问题汇总 |
| **Lindorm 连接错误及解决方案** | [点击查看](https://help.aliyun.com/zh/lindorm/support/lindorm-connection-errors-and-solutions) | ⭐ 连接错误码解释 |
| **使用 ping 命令检查连接** | [点击查看](https://help.aliyun.com/zh/lindorm/support/run-the-ping-command-to-check-the-connection-between-an-ecs-instance-and-a-lindorm-instance) | ⭐ 网络可达性测试 |
| **使用 telnet 命令检查端口** | [点击查看](https://help.aliyun.com/zh/lindorm/support/run-the-telnet-command-to-check-the-connectivity-of-the-service-ports-of-lindorm) | ⭐ 端口连通性测试 |
| **Spark 连接超时问题** | [点击查看](https://help.aliyun.com/zh/lindorm/support/cause-analysis-of-connection-timout-problem-in-sparkonmc-access-to) | Spark 特定场景 |

**⭐ 重点文档**：前 4 个文档是连接问题排查的核心参考，Agent 在处理连接问题时应该优先查询。

---

## 输出格式

连接问题诊断报告采用固定结构：

```
【连接问题诊断报告】实例 ld-uf6l5kr48wqm6rf1h

【问题定位】白名单配置问题

【根因分析】
- 实例状态：✅ ACTIVATION（运行中）
- 白名单配置：❌ 客户端 IP 未在白名单中
  - 当前白名单：10.0.0.0/8, 172.16.1.100
  - 客户端 IP：192.168.1.50
- 网络配置：✅ VPC 配置正常
- 网络测试：
  - ping：✅ 通
  - telnet 30020：❌ 连接被拒绝（白名单限制）

【解决方案】
1. 将客户端 IP 加入白名单：
   
   📍 精确路径：
   1. 控制台：https://lindorm.console.aliyun.com/
   2. 点击实例 ID "ld-xxx"
   3. 安全设置 → IP 白名单 → 修改
   4. 添加 IP：192.168.1.50 或 192.168.1.0/24

2. 或使用同 VPC 内的 ECS 访问

📚 完整故障排查指南：
- 连接问题汇总：https://help.aliyun.com/zh/lindorm/support/lindorm-connection-issues-and-solutions
- 连接错误解决：https://help.aliyun.com/zh/lindorm/support/lindorm-connection-errors-and-solutions

按上述方案修改后，请重试连接。如仍有问题，请提供错误日志。
```

---

## 缺参处理

### 缺 instance-id

**追问策略**：先 `list_instances` 让用户选择实例。

---

## 错误处理

| 错误 | 原因 | 引导用户 |
|------|------|----------|
| **实例不存在** | 实例 ID 错误或已释放 | 建议先 `list_instances` 确认实例 ID |
| **权限不足** | Access Key 无 Lindorm 权限 | 提示需要 `AliyunLindormReadOnlyAccess` 权限 |
