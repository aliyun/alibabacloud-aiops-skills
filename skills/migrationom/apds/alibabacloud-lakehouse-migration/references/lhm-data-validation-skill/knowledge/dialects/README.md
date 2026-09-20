# 方言能力档案索引

每个方言一份独立档案，记录该方言在数据校验场景下的能力边界和特殊行为。
任意两个方言搭配时，对比两份档案即可识别潜在差异。

## 核心方言（独立行为，差异最大）

| 文件 | 方言 | 方言族 | 特殊说明 |
|------|------|--------|---------|
| `maxcompute.md` | MaxCompute (ODPS) | — | 非 JDBC，SDK 直连 |
| `hive.md` | Hive | Hive 族 | 大数据 SQL 基准方言 |
| `starrocks.md` | StarRocks | MySQL 族 | 分区语法独特 |
| `postgres.md` | PostgreSQL | PG 族 | PG 族基准，DECIMAL 前导零问题 |
| `redshift.md` | Redshift | PG 族 | SUPER 类型、CRC32 不兼容 |
| `clickhouse.md` | ClickHouse | — | 独立方言，CRC32 返回类型不同 |
| `bigquery.md` | BigQuery | — | 独立方言，无 CRC32 |
| `presto.md` | Presto | Presto 族 | 函数语法与 Hive 差异较大 |

## 衍生方言（继承核心方言，差异较小）

| 文件 | 方言 | 继承自 | 关键差异 |
|------|------|--------|---------|
| `mysql-family.md` | MySQL / ADB MySQL / Doris | MySQL 族 | MySQL 为基准，Doris 继承 StarRocks |
| `pg-family.md` | Hologres / GaussDB / ADBPG | PG 族 | 共享 DECIMAL 前导零问题 |
| `hive-family.md` | Impala / Databricks / EMR Spark | Hive 族 | Impala LENGTH 行为特殊 |
| `presto-family.md` | Amazon Athena | Presto 族 | 基本继承 Presto |
| `azure-synapse.md` | Azure Synapse | — | 独立方言 |

## 使用方式

当用户的数据源对为 A → B 时：
1. 读取 `dialects/A.md` 和 `dialects/B.md`
2. 对比两份档案中的各项能力
3. 识别差异项，给出适配建议

## 档案统一结构

每份档案包含以下 8 个维度：

1. **分区查询语法** — 分区表的查询方式
2. **复杂类型语法** — JSON/STRUCT/ARRAY/MAP 的访问方式
3. **聚合函数** — SUM/AVG/MIN/MAX/COUNT 等的特殊行为
4. **NULL 处理** — NULL 替换函数
5. **DECIMAL 格式化** — 小数转字符串的方式
6. **BOOLEAN 表示** — 布尔值序列化格式
7. **校验算法** — MD5/CRC32/LENGTH 的可用性
8. **已知陷阱** — 该方言在数据校验中的常见问题
