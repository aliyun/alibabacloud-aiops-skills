# 错误排查场景

当用户遇到错误码、异常、报错信息时，按本指南执行。

## 触发条件

- "报错了：InvalidParameter.InstanceId"
- "连接失败：Connection refused"
- "为什么提示 AuthenticationFailed？"
- "SQL 报错：error code 1045"
- "这个错误是什么意思？"

## 核心原则

1. **Agent 提取关键信息**：错误码、错误含义、解决步骤
2. **提供可执行的排查步骤**，不只是抛出文档链接
3. **结合实例状态**，给出针对性建议

---

## 错误类型分类

| 错误类型 | 示例 | 处理方式 |
|---------|------|---------|
| **CLI/API 错误** | InvalidParameter, Forbidden.RAM, InstanceNotFound | 速查表一 |
| **连接错误** | Connection refused, Timeout, Retry exhausted | 速查表二 |
| **SQL 错误** | Error 1045, 1146, 1064, 3024 | 速查表三 |
| **性能/限流** | Quota exceeded, Too many connections | 速查表四 |

---

## 速查表一：CLI/API 错误码

| 错误码 | 含义 | 可能原因 | 解决方法 |
|--------|------|---------|---------|
| `InvalidParameter.InstanceId` | 实例ID无效 | ID格式错误、不存在、已释放 | 检查格式（应为 ld-xxx），用 `get-lindorm-instance --instance-id <id>` 确认是否存在 |
| `InstanceNotFound` | 实例不存在 | ID错误、已释放 | 用 `get-lindorm-instance --instance-id <id>` 确认 |
| `InstanceStatusInvalid` | 实例状态不支持操作 | 实例非运行中 | 等待实例变为 ACTIVATION |
| `InstanceLocked` | 实例被锁定 | 欠费、安全原因、运维中 | 检查账户余额、联系技术支持 |
| `QuotaExceeded` | 配额不足 | 超过地域配额限制 | 提交工单申请提额 |
| `Instance.IsNotValid` | 实例ID格式合法但不存在 | ID错误、已释放 | 通过 `get-instance-summary` 确认 |
| `InvalidAccessKeyId.NotFound` | AccessKey不存在 | AK ID错误 | 检查 AK 配置 |
| `SignatureDoesNotMatch` | 签名错误 | AK Secret错误 | 验证 Secret 正确性 |
| `Forbidden.RAM` | RAM权限不足 | 缺少Lindorm权限 | 添加 `AliyunLindormReadOnlyAccess` 权限 |
| `UnauthorizedOperation` | 未授权操作 | 缺少特定操作权限 | 联系主账号授权 |
| `Throttling.User` | 用户级别限流 | 请求频率过高 | 降低频率、添加重试机制 |
| `Throttling.System` | 系统级别限流 | 系统负载高 | 稍后重试 |

---

## 速查表二：连接错误

### 网络错误

| 错误信息 | 原因 | 排查步骤 |
|---------|------|---------|
| `Connection refused` | 端口不通 | 1. 检查白名单 2. 检查安全组 3. telnet 测试端口 |
| `Connection timeout` | 网络不可达 | 1. 确认网络类型（VPC/公网）2. 检查路由 3. ping 测试 |
| `Unknown host` | DNS解析失败 | 检查连接地址拼写 |
| `Network is unreachable` | 网络不通 | 确认 VPC 配置、检查跨 VPC/跨地域访问 |

### 认证错误（SQL层面）

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| `Authentication failed` (Error 1045) | 用户名/密码错误 | 检查密码，遗忘请去控制台重置 |
| `Access denied` (Error 1227) | 权限不足 | 检查用户权限配置 |

### HBase 客户端错误（官方连接报错）

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| `Retry exhausted when update config from seedserver` | 连接地址或端口错误（官方：HBase兼容端口为30020） | 确认端口正确（端口见 SKILL.md →「端口号速查表」），检查网络 |
| `Failed to connect to jdbc:lindorm:table:url=****` | SQL连接失败（⚠️ Avatica 协议仅存量维护） | 确认端口正确，建议迁移到 MySQL 协议 |
| `DoNotRetryIOException: Detect inefficient query` | 全表扫描被拦截（官方：WHERE条件列无索引） | 见 sql-usage-notes.md →「低效查询拦截」 |

> 官方连接排查顺序：白名单 → 安全组 → 网络类型匹配 → 公网/专线

### 时序引擎错误

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| `TSDB error: table not found` | 表不存在 | 检查表名 |
| `TSDB error: invalid timestamp` | 时间戳格式错误 | 使用毫秒级时间戳 |
| `Write limit exceeded` | 写入限流 | 降低写入频率、扩容 |

---

## 速查表三：SQL 错误码（官方参考）

以下为官方文档中的 MySQL 兼容错误码和 Lindorm 扩展错误码，完整列表见 https://help.aliyun.com/zh/lindorm/developer-reference/common-error-codes-reference

### 常见 MySQL 兼容错误码

| 错误码 | 含义 | 官方处理建议 |
|--------|------|------------|
| 1040 | 连接数过多（单节点） | 重新审视连接使用方式；2.7.0.0前上限1000，2.7.0.0+上限4000 |
| 1045 | 认证失败 | 确认认证信息是否正确 |
| 1049 | 未知 Database | 指定正确的 Database 名称 |
| 1050 | 表已存在 | 使用其他表名或 IF NOT EXISTS |
| 1054 | 未知列名 | 确认 SQL 中的列名是否实际存在 |
| 1064 | SQL语法错误 | 参考 SQL 语法文档校正 |
| 1146 | 表不存在 | 检查表名是否输入有误 |

### 常见 Lindorm 扩展错误码

| 错误码 | 含义 | 官方处理建议 |
|--------|------|------------|
| 3024 | 查询超时 | 重试；若仍超时联系技术支持 |
| 8005 | 表不存在 | 检查表名 |
| 8008 | 超出资源限制 | 查询：缩小时间范围/增加WHERE；写入：限制TPS |
| 9001 | 不支持的语法 | 对照SQL语法文档，避免使用不支持的语法 |
| 9003 | 认证方法不适用于旧版本用户 | 参考MySQL协议兼容文档，指定支持的认证方法 |

---

## 速查表四：监控指标异常

| 指标异常 | 可能原因 | 排查建议 | V2 注意 |
|---------|---------|---------|--------|
| `cpu_idle < 10%` | CPU使用率过高 | 查询慢查询日志、考虑扩容 | — |
| `mem_used_percent > 90%` | 内存紧张 | 检查缓存配置、扩容 | ⚠️ V2返回空，需用 `1 - mem_free/mem_total` 计算 |
| `storage_used_percent > 85%` | 存储空间不足 | 清理数据或扩容 | ⚠️ V2需用 `get-lindorm-v2-storage-usage` API |
| `read_rt_p99 > 1000ms` | 查询延迟高 | 分析慢查询、创建索引 | ⚠️ V2返回空 |
| `write_rt_p99 > 500ms` | 写入延迟高 | 检查写入模式、考虑扩容 | ⚠️ V2返回空 |

---

## 常见错误处理示例

### 示例：InvalidParameter.InstanceId

```
【错误分析】InvalidParameter.InstanceId

【错误含义】实例 ID 参数无效

【可能原因】
1. 实例 ID 格式不正确（应为 ld-xxx）
2. 实例不存在或已释放

【排查步骤】
步骤 1：验证 ID 格式 — 确认以 ld- 开头
步骤 2：确认是否存在 — aliyun hitsdb get-lindorm-instance --instance-id <id>
（API 自动定位地域，无需指定 --region）

【官方文档】https://help.aliyun.com/zh/lindorm/developer-reference/common-error-codes-reference
```

### 示例：认证失败（Error 1045）

```
【错误分析】Access denied / Authentication failed (Error 1045)

【错误含义】用户名或密码不正确

【排查步骤】
步骤 1：确认密码正确（如遗忘请去控制台重置）
步骤 2：检查 RAM 权限 — 确保包含 AliyunLindormReadOnlyAccess
步骤 3：验证修复 — aliyun hitsdb get-instance-summary

【常见错误】
❌ 使用子账号但未授权 Lindorm 权限
❌ 实例 ID 格式错误或实例不存在
```

---

## 官方文档

- **错误码参考**：https://help.aliyun.com/zh/lindorm/developer-reference/common-error-codes-reference
- **连接报错与解决**：https://help.aliyun.com/zh/lindorm/support/lindorm-connection-errors-and-solutions
- **连接问题与解决**：https://help.aliyun.com/zh/lindorm/support/lindorm-connection-issues-and-solutions
- **SQL FAQ**：https://help.aliyun.com/zh/lindorm/developer-reference/sql-faq
- **技术支持**：通过阿里云工单系统提交

---

## 关联场景

- 连接问题 → `connection-troubleshoot.md`
- 性能问题 → `monitoring-guide.md`
- SQL 使用 → `sql-usage-notes.md`