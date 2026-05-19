# 连接信息获取场景

当用户询问"怎么连接实例"、"连接地址是什么"、"需要什么 SDK"时，按本指南执行。

## 触发条件

用户的典型表达：
- "怎么连接 ld-xxx？"
- "给我连接地址"
- "用 Java 怎么连接？"
- "时序引擎的端口是多少？"
- "给我一个连接示例"

## 核心原则

**Agent 是解决方案提供者**，而不是指路者：
2. **Agent 提取关键信息**并整理成完整答案（代码示例、依赖配置、参数说明）
3. **用户无需离开对话**就能得到可执行的连接代码
4. 连接地址从 API 无法获取时，**明确告知控制台精确路径**（精确到按钮位置）
5. 文档链接作为补充参考，用户如需深入了解可查看


---

## 执行流程

### 阶段一：获取实例基本信息

执行以下命令获取实例的架构版本、连接端点和网络配置：

```bash
# 1. 获取实例详情（判断 V1/V2 架构）
aliyun hitsdb get-lindorm-instance \
    --instance-id <instance-id>

# 2. 获取各引擎连接端点
aliyun hitsdb get-lindorm-instance-engine-list \
    --instance-id <instance-id>
```

**需要提取的关键信息**：

| 信息项 | 来源字段 | 说明 |
|--------|----------|------|
| 架构版本 | `ServiceType` | `lindorm_v2*` = V2 新架构, `lindorm` = V1 老架构 |
| 连接地址 | `NetInfoList`（V1/V2 均使用此字段） | 各引擎的域名和端口 |
| 网络类型 | `NetType` | `"0"` = 公网可用, `"2"` = 仅 VPC 内网（字符串类型，V1/V2 相同） |
| 引擎版本 | `EngineList` | 各引擎的版本号 |

> **注意**：`get-lindorm-instance-engine-list` 对 V1 和 V2 都返回 `NetInfoList` + `NetType`。另一个 V2 专属 API `get-lindorm-v2-instance-details` 返回 `ConnectAddressList` + `Type=INTRANET/INTERNET`，见阶段二。

**端点域名格式**：

域名格式见 [sql-client-guide.md](sql-client-guide.md)，含V1/V2 ServiceType判断逻辑和完整示例

---

### 阶段二：确认连接条件

在提供连接代码前，必须确认以下两项：

#### 1. 公网访问检查

**方式一：通过 `get-lindorm-instance-engine-list`（V1/V2 通用）**

检查 `NetInfoList` 中的 `NetType` 字段（字符串类型）：
- `"0"`: 公网可用
- `"2"`: 仅 VPC 内网

**方式二：通过 `get-lindorm-v2-instance-details`（仅 V2）**

检查 `ConnectAddressList` 中的 `Type` 字段：
- `INTERNET`: 公网可用
- `INTRANET`: 仅 VPC 内网

**如果只有 VPC 内网地址（NetType="2" 或 Type=INTRANET）**：
> ⚠️ 当前实例 SQL 端口仅支持 VPC 内网访问。从本地电脑连接需要：
> 1. 登录 [Lindorm 控制台](https://lindorm.console.aliyun.com/)
> 2. 点击实例 ID → **数据库连接** → **引擎** 页签
> 3. 点击右上角 **「开通公网地址」**
> 4. 配置白名单（您的本地 IP 地址）
>
> 或者，您可以在阿里云 ECS（与 Lindorm 同 VPC）上执行连接和操作。

#### 2. 密码获取与确认

**V2 实例**：
```bash
aliyun hitsdb get-lindorm-v2-instance-details \
    --instance-id <instance-id>
```
提取 `InitialRootPassword` 字段，用户名为 `root`。

> ⚠️ **密码获取/确认流程：**
> 1. **首次连接**：使用 `InitialRootPassword`
> 2. **连接失败/密码错误**：停止执行，**必须询问用户**当前密码
> 3. **执行变更操作**（如创建表、修改配置）：**必须获得用户明确授权**

**V1 实例**：
- **默认用户名**：`root`
- **默认密码**：`root`
- **如果忘记密码**：通过集群管理系统修改
  - 路径：[Lindorm 控制台](https://lindorm.console.aliyun.com/) → 实例 ID → **数据库连接** → **宽表引擎** → **Lindorm Insight** → **用户管理**
  - 修改密码后需要**重启引擎**才能生效

---

### 阶段三：提供连接信息

整理阶段一、二获取的信息，直接给用户完整的连接方案：

```
实例 ld-xxx 已开通以下引擎：
- 宽表引擎（版本 2.8.6，V2 新架构）
- 时序引擎（版本 2.7.15）

【连接地址】（已通过 API 获取）
- 内网（VPC）：ld-xxx-proxy-lindorm-vpc.lindorm.aliyuncs.com:33060
- 公网：ld-xxx-proxy-lindorm-pub.lindorm.aliyuncs.com:33060

> ⚠️ 从公网（本地电脑等）连接时，必须使用公网地址（`-pub`），不能用内网地址（`-vpc`），否则连接超时。

【SQL 连接凭证】
- 用户名：root
- 密码：（V2 实例已通过 get-lindorm-v2-instance-details 获取 InitialRootPassword；
         V1 实例请在控制台 Lindorm Insight → 用户管理 中查看）
```

**连通性验证**（MySQL 命令行）：

```bash
mysql -h <连接地址> -P 33060 -u root -p \
  --get-server-public-key --ssl-mode=DISABLED
```

连接成功后提示用户：
> 连接已验证成功。需要建表、写入数据的完整示例吗？可以告诉我您使用的引擎类型，我为您提供完整代码。

**各引擎端口速查**：

| 引擎 | 协议 | 端口 |
|------|------|------|
| 宽表引擎 | MySQL 协议（推荐） | 33060 |
| 宽表引擎 | HBase API | 30020 |
| 时序引擎 | HTTP SQL API | 8242 |
| 搜索引擎 | Elasticsearch API | 30070 |
| 流引擎 | MySQL 协议 | 33060 |

**各引擎连接方式总览**（Agent 根据用户需求路由到正确的文档）：

| 引擎 | 连接方式 | 推荐 | 官方文档 |
|------|---------|------|----------|
| 宽表引擎 | MySQL 协议 SQL | ⭐ 推荐 | [Java JDBC](https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-java-jdbc-interface)、[Python](https://help.aliyun.com/zh/lindorm/user-guide/python-based-application-development-1)、多语言见 [sql-client-guide.md](sql-client-guide.md) |
| 宽表引擎 | HBase API | 常用 | [Java](https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-java-to-connect-to-and-use-the-wide-table-engine)、[非Java](https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-a-non-java-language-to-connect-to-and-use-the-wide-table-engine)，代码示例见 [quick-start-guide.md 场景F](quick-start-guide.md#场景-f宽表引擎-hbase-api-快速开始) |
| 宽表引擎 | Cassandra CQL | 存量 | [Java Driver](https://help.aliyun.com/zh/lindorm/user-guide/use-a-cassandra-client-driver-for-java-to-connect-to-and-use-the-wide-table-engine)、[非Java](https://help.aliyun.com/zh/lindorm/user-guide/use-a-multi-language-cassandra-client-driver-to-connect-to-and-use-the-wide-table-engine) |
| 宽表引擎 | S3 协议 | 存量 | [Java](https://help.aliyun.com/zh/lindorm/user-guide/connect-and-use-the-wide-table-engine-with-the-s3)、[非Java](https://help.aliyun.com/zh/lindorm/user-guide/connect-via-s3-non-java-api-and-use-the-wide-table) |
| 时序引擎 | JDBC Driver | ⭐ 推荐 | [JDBC Driver](https://help.aliyun.com/zh/lindorm/user-guide/use-the-jdbc-driver-for-lindorm-to-connect-to-and-use-lindormtsdb) |
| 时序引擎 | HTTP SQL API | 轻量 | [HTTP API](https://help.aliyun.com/zh/lindorm/user-guide/http-sql-api-user-guide) |
| 搜索引擎 | Elasticsearch API | ⭐ 推荐 | [Java REST Client](https://help.aliyun.com/zh/lindorm/user-guide/java-low-level-rest-client) |
| 向量引擎 | Elasticsearch API | ⭐ 推荐 | 复用搜索引擎端口 30070，[向量开发指南](https://help.aliyun.com/zh/lindorm/user-guide/foundation) |
| 流引擎 | MySQL 协议 ETL SQL | ⭐ 推荐 | [实时ETL](https://help.aliyun.com/zh/lindorm/user-guide/real-time-etl) |
| 流引擎 | Kafka 客户端 | 数据接入 | [Kafka写入](https://help.aliyun.com/zh/lindorm/use-an-open-source-apache-kafka-client-to-write-data-to-the-lindorm-streaming-engine) |
| LindormDFS | HDFS Shell / 客户端 | - | [底层文件访问概览](https://help.aliyun.com/zh/lindorm/user-guide/lindormdfs)、[运维指南](https://help.aliyun.com/zh/lindorm/user-guide/lindormdfs-user-guide/) |
| 计算引擎 | JDBC / JAR / Python | - | [JDBC访问](https://help.aliyun.com/zh/lindorm/user-guide/use-sql-to-connect-to-ldps)、[JAR作业](https://help.aliyun.com/zh/lindorm/user-guide/jar-job-development-practice) |

> **LindormDFS 和计算引擎** Skill 不提供代码示例，如用户询问请引导至上述官方文档或[连接总览](https://help.aliyun.com/zh/lindorm/getting-started/connect-to-an-instance)。

---

### 阶段四：白名单检查

**Agent 主动检查白名单**：

```bash
aliyun hitsdb get-instance-ip-white-list \
    --instance-id <instance-id>
```

**分析后给出明确建议**：

```
【白名单检查】

当前白名单配置：10.0.0.0/8

【分析】
- 如果您的客户端 IP 在 10.0.0.0/8 网段内 → ✅ 可以直接连接
- 如果您的客户端 IP 不在白名单中 → ❌ 需要添加

【添加白名单】（精确步骤）
1. 登录 [Lindorm 控制台](https://lindorm.console.aliyun.com/) → 在实例列表页，单击**目标实例ID** → 在左侧导航栏，单击**访问控制** → **白名单**
2. 点击"创建分组白名单"或修改已有分组
3. 添加客户端 IP（内网环境填 VPC IP，公网环境填公网 IP）
   - 单个 IP：192.168.1.100
   - IP 段：192.168.1.0/24
4. 点击"确定"保存

> 💡 查看自己公网 IP：`curl ifconfig.me`

【安全提示】
- ⚠️ 不建议使用 0.0.0.0/0（允许所有 IP），存在安全风险
- ✅ 建议只添加必要的 IP 或 VPC 网段

需要我帮您排查连接问题吗？
```

---

## 下一步引导

连接验证成功后，根据用户需求引导：

- **建表/写入/查询** → 参考 [quick-start-guide.md](quick-start-guide.md)（含宽表、时序、搜索、向量、流引擎完整示例）
- **连接失败排查** → 参考 [connection-troubleshoot.md](../02-ops/connection-troubleshoot.md)
- **用户权限管理** → 参考 [user-permission.md](../02-ops/user-permission.md)
