# 数据预览 SQL 方言与 OperatorType 映射

> 板块 ② 数据预览专用。核心两件事：**选对 OperatorType**、**写对 LIMIT 方言**。
> 预览会起真实计算任务，执行前必须 HITL 确认（引擎 / 表 / SQL / 分区）。

## 1. 资产类型 → OperatorType

由 `GetCatalogAssetDetails` 的 `SubType` + `DataSourceName` 推导：

| 资产 / 数据源 | OperatorType | 必填参数 |
|---|---|---|
| 项目内 Dataphin 表（GUID 前缀 `odps.`） | `MaxCompute_SQL` | `--project-id` |
| MySQL / PostgreSQL / Oracle / SQL Server / 达梦 / GaussDB 等关系库 | **`DATABASE_SQL`** | `--project-id` + `--data-source-id` + **`--data-source-schema`** |
| Hologres | `HOLOGRES_SQL` | `--project-id`（+ 数据源） |
| StarRocks | `STARROCKS_SQL` | `--project-id`（+ 数据源） |
| Hive | `Hive_SQL` / `Hive_SQL_23X` / `COMMON_HIVE_SQL` | `--project-id` |
| Impala | `IMPALA_SQL` | `--project-id` |
| ArgoDB | `ARGODB_SQL` | `--project-id` |
| ADB for PG / MySQL | `ADB_FOR_PG` / `ONE_SERVICE_SQL_ADB_FOR_MYSQL` | `--project-id` |
| Presto 等需 Catalog 的 | `DATABASE_SQL` | + `--data-source-catalog` |

要点：

- **关系库统统走 `DATABASE_SQL`**，不要按数据库名去猜 `MYSQL_SQL` 这种不存在的枚举。
- `DATABASE_SQL` 只传 `--data-source-id` 不够，**必须同时传 `--data-source-schema`**。
- `--data-source-id` 是 19 位大整数，**字符串传**，否则尾数会被截断。
- OperatorType 大小写敏感，且**不能用数值枚举**（数值枚举只在 `create-batch-task --task-type` 用）。

## 2. 取前 N 行的方言

**不要一律写 `LIMIT 50`。**

| 引擎 | 预览 SQL |
|---|---|
| MaxCompute / Hive / Impala / StarRocks / Doris / MySQL / PostgreSQL / Hologres / Greenplum / ClickHouse / ADB | `SELECT * FROM <库>.<表> LIMIT 50` |
| **Oracle** | `SELECT * FROM <schema>.<表> WHERE ROWNUM <= 50` |
| **SQL Server** | `SELECT TOP 50 * FROM <schema>.<表>` |
| **DB2** | `SELECT * FROM <schema>.<表> FETCH FIRST 50 ROWS ONLY` |
| Oracle 12c+ 也可 | `SELECT * FROM <schema>.<表> FETCH FIRST 50 ROWS ONLY` |

> Oracle 的 `ROWNUM` 不能和 `ORDER BY` 直接连用（先截断再排序，结果不是"最大的 50 条"）。需要排序取前 N 时套子查询：
> `SELECT * FROM (SELECT * FROM t ORDER BY c DESC) WHERE ROWNUM <= 50`

## 3. 表名必须全限定

一律 `<project|schema>.<table>`——`GetCatalogAssetDetails` 的 `AssetFullName` 直接给了这个值。

裸表名的危害：可能解析到其他同名空表，**查出 0 行但任务状态仍为成功**，极易误判"表无数据"。

## 4. 分区表处理（必做）

`IsPartitionTable=true` 时**必须**按 `PartitionKey` 钉一个分区值：

```sql
-- 1) 先取真实分区值，不要猜
SHOW PARTITIONS <project>.<table>;              -- MaxCompute / Hive

-- 2) 再带分区谓词预览
SELECT * FROM <project>.<table> WHERE ds = '20260806' LIMIT 50;
```

不带分区谓词的后果：

- **MaxCompute**：全表扫描保护直接拦，报错退出。
- **Hive / 大表关系库**：查询长时间挂住，白烧资源。

多级分区（`PartitionKey` 含多个键）时每一级都要钉，只钉一级仍可能触发大范围扫描。

## 5. SELECT-only 守卫（硬约束）

预览 SQL **只允许 `SELECT`**。提交前逐条自检：

- ✗ 不得出现 `INSERT` / `UPDATE` / `DELETE` / `DROP` / `ALTER` / `TRUNCATE` / `MERGE` / `CREATE`
- ✗ 不得用分号拼多条语句（会被拆成并行子任务，顺序不保证）
- ✗ 不得因"顺手"把用户的建表/改数需求塞进预览——那属于 `execute-ad-hoc-task`，需用户单独确认授权
- ✓ 必须带行数上限（默认 50）

## 6. 取结果

```bash
sleep 5   # 结果可能延迟几秒才上传
aliyun dataphin-public get-ad-hoc-task-result ... --task-id "$TASK_ID" --sub-task-id 0
```

- **`--sub-task-id` 从 0 开始**（不是 1）。
- **两个接口的负载键都是 `ExecuteResult`**（实测）：提交返回 `ExecuteResult.{TaskId, SubTaskCount}`；取结果返回 `ExecuteResult.{TaskId, ScheduleTaskId, Result}`。
- **任务未完成时 `Result` 是空串 `""`，而不是报错**（实测需轮询 3~4 次 × 5s）。**必须轮询**，不能拿第一次的空串当“表没数据”。
- MaxCompute / Hive 结果：`[[列名...],[行...]]`，未命名列为 `_c0`/`_c1`；空值渲染为字符串 `"\\N"`（不是 `null`），统计空值时要一并当空处理。
- `DATABASE_SQL` 结果：首行多一段 `COLUMN_TYPE:[{"name":...,"type":...}]` 元数据，之后才是 `[headers, rows...]`。
- **`SHOW PARTITIONS` 的结果不是多行**（实测）：全部分区被塞进**单个单元格**、用 `\n` 分隔，形如 `[["DS=20230319\nDS=20230320\n..."]]`。要用正则（如 `DS=(\d+)`）抽取再排序取最新，不能按行读。
- **预览 Dataphin 逻辑表可直接用 `<板块名>.<表名>`**（实测：`MaxCompute_SQL` + `ProjectId`，`SELECT * FROM LD_Fashion.dim_employee` 正常返回）——即 `AssetFullName` 直接可用作表名，无需去找物理表名。
- **默认不要拉 `get-ad-hoc-task-log` 全文**（单次可达上万字符，白吃上下文）。仅当结果为空/报错时才拉，且带 `--cli-query 'LogInfo.TaskStatus'` 只取状态；要看报错正文再取 `LogInfo.Content` 并 `tail` 尾部。

## 7. 结果为空 / 行数少于预期时的排查顺序

按这个顺序排，不要一上来就说"表没数据"：

1. `Result` 是不是还是空串（任务未完成）——**先轮询够次数**
2. 分区值是否真实存在（`SHOW PARTITIONS` 核对）——**钉一个不存在的分区不报错，只返回 0 行**
3. 表名是否用了全限定名
4. 任务状态是否真的 `SUCCESS`（可能还在 `WAIT_RESOURCE`）
5. 以上都排除后，才是该分区本身数据少/为空

> **返回行数 < LIMIT 是有效信息**，不是错误（实测：`LIMIT 50` 只返 5 行 → 该分区真实只有 5 条）。展示时应明确写出“实际返回 N 行”。

## 8. 与其他板块交叉校验（预览的隐藏价值）

预览拿到的分区清单能反过来验证其他板块的结论，实测出过真问题：

- **质量规则在校验一个不存在的分区**：质量任务 `ValidatePartition=ds='20260807'`，但 `SHOW PARTITIONS` 最新只到 `20260806` → 强规则异常的真因是**上游没产出当日分区**，而不是字段值有问题。报质量异常时应同时核对分区是否存在。
- **字段血缘看着全通、实际数据全空**：字段血缘显示 104 列从上游直传，但预览发现 105 列中 98 列全为 `\N` → **血缘只证明“映射关系存在”，不证明“数据真的流过来了”**。

所以：四个板块一起跑才能交叉定位问题，单看任何一个都可能得出误导结论。
