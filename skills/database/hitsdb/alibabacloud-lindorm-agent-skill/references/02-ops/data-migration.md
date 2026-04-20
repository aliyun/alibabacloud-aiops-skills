# 数据迁移场景

## 触发条件

- "如何从 MySQL 导入数据到 Lindorm？"
- "怎么把 HBase 集群数据迁移过来？"
- "从 Kafka 实时同步数据到 Lindorm 的步骤？"
- "能帮我规划数据迁移方案吗？"

## 核心原则

**⚠️ 安全边界：只读 + 引导，严禁直接执行迁移操作**

迁移涉及源库连接信息（账号密码），直接执行可能泄露敏感信息或导致数据丢失。Agent 只提供方案和步骤，引导用户通过控制台操作。

---

## 官方文档

- LTS（原BDS）服务介绍：https://help.aliyun.com/zh/lindorm/user-guide/bds-introduction
- MySQL/RDS → Lindorm（DTS）：https://help.aliyun.com/zh/dts/user-guide/migrate-data-from-an-apsaradb-rds-for-mysql-instance-to-a-lindorm-instance
- HBase → Lindorm（LTS）：https://help.aliyun.com/zh/lindorm/user-guide/synchronize-full-and-incremental-data
- Lindorm 数据订阅（→ Kafka 导出）：https://help.aliyun.com/zh/lindorm/user-guide/real-time-data-subscription/
- 字段类型映射：https://help.aliyun.com/zh/lindorm/developer-reference/basic-data-types

---

## 迁移方案选择

| 源端 | 推荐方案 | 支持全量+增量 | 关键限制 |
|------|---------|-------------|---------|
| MySQL/RDS | **DTS**（新用户推荐） | ✅ | ⚠️ 不支持自动表结构迁移，需预先在Lindorm手动建表 |
| HBase 1.x/2.x | **LTS** | ✅ | Bulkload写入的数据不会被增量同步 |
| Lindorm → Lindorm | **LTS** | ✅ | 需确保网络连通 |
| Kafka → Lindorm | **LTS 流式通道** | ✅ | — |
| 自建/特殊需求 | 开源工具（Canal/Sqoop/脚本） | 视工具 | Lindorm非完整MySQL，部分工具可能因DDL差异失败 |

> ⚠️ LTS原有的RDS同步功能已于2023年3月10日下线，之后购买的LTS实例不再支持MySQL迁移。新用户请用DTS。

---

## 方案A：DTS 迁移（MySQL/RDS → Lindorm）

### 步骤

1. **进入 DTS 控制台** → https://dts.console.aliyun.com/ → 数据迁移 → 创建任务
2. **配置源库与目标库**：源库类型 MySQL，目标库 Lindorm（需已开通宽表引擎 MySQL 兼容地址）
3. **预先在 Lindorm 手动建表**（⚠️ DTS 不支持自动表结构迁移，参考字段类型映射处理 ENUM→VARCHAR 等类型转换）
4. **预检查**：系统自动检查源库连通性、账号权限、binlog配置（增量迁移需 binlog_format=ROW）
5. **启动迁移**：可在控制台实时查看进度和数据量
6. **验证数据**：在 Lindorm 执行 `SELECT COUNT(*) FROM your_table;` 与源库对比

### 注意事项

- 全量迁移期间请勿修改源库表结构
- 增量同步前提：MySQL 端必须开启 binlog（binlog_format=ROW）
- 建议在业务低峰期执行

---

## 方案B：LTS 迁移（HBase → Lindorm）

### 步骤

1. **开通 LTS 服务**：Lindorm 控制台 → 目标实例 → 数据生态服务 → 开通 LTS
2. **创建迁移任务**：LTS 操作页面 → 导入Lindorm/HBase → 一键迁移 → 创建任务
3. **配置源端与目标端**：源端 HBase 集群（需与 LTS 网络连通），目标端 Lindorm 宽表引擎；选择 ☑️ 表结构迁移 + ☑️ 历史数据迁移 + ☑️ 实时数据复制
4. **监控与验证**：实时查看迁移进度，LTS 数据抽样校验，业务验证后执行流量切换

### 注意事项

- 确保 LTS、源 HBase、目标 Lindorm 三者网络已打通
- 增量同步基于 HBase WAL，Bulkload 写入的数据不会被同步
- 迁移前确认目标实例存储空间充足

---

## 方案C：开源工具迁移

### C-1：Canal（MySQL → Lindorm 实时同步）

解析 MySQL binlog 实时同步到 Lindorm。

1. 部署 Canal Server
2. 配置 Canal 监听 MySQL binlog
3. 使用 Canal Adapter 将数据写入 Lindorm

参考：https://github.com/alibaba/canal

### C-2：Sqoop（Hadoop → Lindorm 批量导入）

> ⚠️ Lindorm 宽表引擎是MySQL兼容而非完整MySQL，Sqoop可能因DDL差异失败。

```bash
# 连接地址根据实例 ServiceType 选择（见 sql-client-guide.md →「连接域名格式」）
# V1/V2 MySQL 协议端口均为 33060
sqoop export \
  --connect jdbc:mysql://<您的连接地址>:<端口>/default \
  --table my_table \
  --export-dir /user/hive/warehouse/my_table \
  --input-fields-terminated-by '\t'
```

### C-3：自定义脚本

适用于数据量小或特殊转换需求。示例：

1. 从源库导出数据（mysqldump、HBase Export）
2. 数据清洗和格式转换
3. 使用 Lindorm SDK 或 MySQL 协议批量写入

Python 示例（MySQL → Lindorm）：

```python
import pymysql

# 1. 读取 MySQL 数据
mysql_conn = pymysql.connect(host='...', user='...', password='...', database='source_db')
cursor = mysql_conn.cursor()
cursor.execute("SELECT * FROM source_table")

# 2. 写入 Lindorm（MySQL 协议）
# 连接地址根据实例 ServiceType 选择（见 sql-client-guide.md）
# V1/V2 MySQL 协议端口均为 33060（域名格式见 sql-client-guide.md）
lindorm_conn = pymysql.connect(
    host='<您的连接地址>',
    port=<端口>,
    user='root',
    password='your-password',
    database='default'
)
lindorm_cursor = lindorm_conn.cursor()

for row in cursor:
    placeholders = ','.join(['%s'] * len(row))
    lindorm_cursor.execute(f"INSERT INTO target_table VALUES ({placeholders})", row)
lindorm_conn.commit()
```

---

## 常见问题

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 连通性检查失败 | 网络不通/白名单未配置 | 确认同一VPC或已配公网；添加源库IP到Lindorm白名单 |
| 表结构不兼容 | MySQL类型无Lindorm对应 | ENUM→VARCHAR；TEXT/BLOB超2MB需拆分；必须有主键 |
| 增量同步断开 | MySQL binlog被清理 | 增大binlog保留时间；重新配置DTS任务 |
| 目标存储不足 | 数据量超预期 | 迁移前确认Lindorm存储空间（建议预留20GB+） |

---

## 关联场景

- 迁移后性能对比 → `monitoring-guide.md`
- 验证数据一致性 → `monitoring-guide.md` 查询写入指标
- 迁移任务监控 → LTS 控制台实时查看（暂无 API 支持）