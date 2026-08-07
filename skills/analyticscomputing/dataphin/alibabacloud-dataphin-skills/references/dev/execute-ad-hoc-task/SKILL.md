---
name: execute-ad-hoc-task
description: |
  执行 Dataphin 即席查询任务（临时跑 SQL / 脚本 / 查元信息，不创建持久化任务）。触发场景：执行 SQL / 即席查询 / 临时跑一段代码 / 建表 / 查数据源表 / execute-ad-hoc-task / DATABASE_SQL / MaxCompute_SQL / ad-hoc。关键点：OperatorType 为字符串枚举（MySQL/Oracle/PostgreSQL/SQLServer 统一用 DATABASE_SQL；MaxCompute 用 MaxCompute_SQL）；DATABASE_SQL 必须同时传 --data-source-id 和 --data-source-schema；MaxCompute_SQL 只需 --project-id；参数名是 --code 不是 --script；get-ad-hoc-task-result 的 --sub-task-id 从 0 开始；结果可能延迟几秒才能取到；MaxCompute 结果格式为 [["_c0","_c1",...],[1,2,...]]。触发词：执行 SQL、即席查询、临时跑代码、建表、execute-ad-hoc-task、DATABASE_SQL、MaxCompute_SQL、ad-hoc、查表结构。
---

# 即席查询任务 Skill

## 1. Scenario Description

场景：需要临时执行一段 SQL / 脚本 / 查元信息，不想创建持久化任务，只想一次性运行并获取结果。

本 Skill 覆盖常见 OperatorType 的提交、结果获取、日志排查全流程。

### Architecture

```
用户请求 → 确认参数 → execute-ad-hoc-task 提交任务
  → get-ad-hoc-task-log 查看运行状态
  → get-ad-hoc-task-result 获取执行结果
```

### 涉及 Dataphin OpenAPI

- `ExecuteAdHocTask` — 提交即席查询任务
- `GetAdHocTaskResult` — 获取即席查询结果
- `GetAdHocTaskLog` — 获取即席查询日志
- `ListDataSourceWithConfig` — 查找可用的数据源 ID

## 2. Installation

```bash
# 安装 aliyun CLI（>= 3.4.8）
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 安装 dataphin-public 插件
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证
aliyun dataphin-public --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

### Pre-check: Credentials Required

> **Security Rules:**
> - **NEVER** 读取、回显或打印凭证环境变量（禁止对 AccessKey ID / Secret 做任何输出或日志）
> - **NEVER** 要求用户在本会话或命令行直接输入 AK/SK
> - **NEVER** 使用 `aliyun configure set` 写入字面量凭证
> - **ONLY** 使用 `aliyun configure list` 检查凭证状态
>
> ```bash
> aliyun configure list
> ```
> 检查输出中是否存在有效 profile（AK、STS 或 OAuth 身份）。
>
> **如果没有有效 profile，请在此停止。**
> 1. 从 [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak) 获取凭证
> 2. 在会话外配置（终端执行 `aliyun configure`，或在 shell profile 中设置环境变量）
> 3. 重新运行 `aliyun configure list` 确认有效后再继续

### Pre-check: Aliyun CLI plugin update required

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
>
> 执行前确认 CLI 与插件版本：
> ```bash
> aliyun version
> aliyun plugin list
> ```

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

本 skill 最小权限见 [../../ram-policies.md](../../ram-policies.md)。

## 6. IMPORTANT: Parameter Confirmation

执行即席查询前，**任何未由用户显式提供的参数都必须主动询问用户**，禁止猜测或假设默认值（除 `--env` 可默认 PROD 外）。

### 必须获取的参数

| 参数 | 说明 | 是否必须询问 |
|------|------|-------------|
| `--env` | DEV 或 PROD；若用户未指定，可默认 PROD，但需告知用户 | 可选确认 |
| `--tenant-id` | 租户 ID；优先从 profile 读取，若 profile 未配置则必须询问 | 条件必须 |
| `--project-id` | 项目 ID；优先从 profile 读取，若 profile 未配置则必须询问 | 条件必须 |
| `--operator-type` | 任务类型，**必须询问用户** | **必须** |
| `--code` | 要执行的脚本/SQL，**必须询问用户** | **必须** |
| `--data-source-id` | 数据源 ID；当 `--operator-type` 为 DATABASE_SQL 时必须询问 | 条件必须 |
| `--data-source-schema` | Schema/库名；当 `--operator-type` 为 DATABASE_SQL 时必须询问 | 条件必须 |

### 询问模板

当用户说"执行 SQL"但未给出具体信息时，按以下顺序追问：

1. **环境确认**："请在 DEV 还是 PROD 环境执行？（默认 PROD）"
2. **项目确认**："请提供项目 ID 或项目名。"
3. **任务类型**："请指定任务类型，例如 MaxCompute_SQL、DATABASE_SQL（PostgreSQL/MySQL/Oracle/SQLServer）、HOLOGRES_SQL、Shell 等。"
4. **执行代码**："请提供要执行的 SQL 或脚本内容。"
5. **数据源**（仅数据库类需要）："请提供数据源 ID 和 Schema/库名。"

### 参数获取完成后再执行

> **在所有必填参数确认完整之前，禁止调用 `execute-ad-hoc-task`。**

## 7. 完整命令链

```bash
TENANT_ID=<tenant-id>
PROJECT_ID=<project-id>
ENV=PROD
USER_AGENT="AlibabaCloud-Agent-Skills/execute-ad-hoc-task/{session-id}"

# 1) 查找数据源（仅 DATABASE_SQL / HOLOGRES_SQL 等需要）
aliyun dataphin-public list-data-source-with-config --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --page 1 --page-size 20 \
  --user-agent "$USER_AGENT" --format json \
  | jq '.PageResult.DataSourceList[] | {
       Name: .ProdDataSourceInfo.Name,
       Type: .ProdDataSourceInfo.Type,
       ProdId: .ProdDataSourceInfo.Id,
       DevId: .DevDataSourceInfo.Id
     }'

# 2) 提交即席查询任务
# --- MaxCompute_SQL 示例 ---
aliyun dataphin-public execute-ad-hoc-task --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --operator-type MaxCompute_SQL \
  --code "SELECT 1, 2, 3, 4" \
  --user-agent "$USER_AGENT" --format json \
  | jq '.ExecuteResult | {TaskId, SubTaskCount}'

# --- DATABASE_SQL（PostgreSQL）示例 ---
aliyun dataphin-public execute-ad-hoc-task --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --operator-type DATABASE_SQL \
  --data-source-id "<data-source-id-string>" \
  --data-source-schema public \
  --code "SELECT 1, 2, 3, 4" \
  --user-agent "$USER_AGENT" --format json \
  | jq '.ExecuteResult | {TaskId, SubTaskCount}'

TASK_ID=<上一步返回的 TaskId>

# 3) 等待并取结果（默认路径：直接拿结果，不要默认拉日志——日志正文常达上万字符，白白吃上下文）
sleep 5
aliyun dataphin-public get-ad-hoc-task-result --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --task-id $TASK_ID --sub-task-id 0 \
  --user-agent "$USER_AGENT" --format json \
  | jq -r '.ExecuteResult.Result'

# 4) 仅在结果为空 / 报错 / 需确认运行状态时才拉日志，且只取状态字段
aliyun dataphin-public get-ad-hoc-task-log --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --task-id $TASK_ID --sub-task-id 0 --offset 0 \
  --cli-query 'LogInfo.TaskStatus' \
  --user-agent "$USER_AGENT" --format json
# 需要看报错正文时再取 Content（建议配合 tail 只看尾部）：
#   ... --cli-query 'LogInfo.Content' --format json | tail -c 2000
```

## 8. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/execute-ad-hoc-task/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 9. OperatorType 与必填参数

> `execute-ad-hoc-task` 使用**字符串枚举**（如 `MaxCompute_SQL`、`DATABASE_SQL`）。
> MySQL / Oracle / PostgreSQL / SQLServer 等关系型数据库统一使用 **DATABASE_SQL**。
> 💡 **术语**：ODPS（Open Data Processing Service）是 MaxCompute 的旧名称，`MaxCompute_SQL` 对应旧称 `ODPS_SQL`。

| OperatorType（字符串） | DataSourceId | 说明 |
|---|---|---|
| `MaxCompute_SQL` | ✗ | 使用项目绑定的 MaxCompute 计算源，仅需 `--project-id` |
| `Hive_SQL` / `Hive_SQL_23X` / `COMMON_HIVE_SQL` | ✗ | Hive 计算源 |
| `HOLOGRES_SQL` | ✓ | Hologres 数据源 |
| `STARROCKS_SQL` | ✓ | StarRocks 数据源 |
| `SPARK_SQL` / `SPARK_SQL_ON_MAX_COMPUTE` / `SPARK_SQL_ON_HIVE` | ✗ | Spark SQL |
| `Shell` | ✗ | Shell 脚本 |
| `Python` / `Python37x` / `Python311x` | ✗ | Python 脚本 |
| **`DATABASE_SQL`** | **✓ 必填 + Schema** | **MySQL / Oracle / SQLServer / PostgreSQL 等关系型数据库，需同时传 `--data-source-schema`** |

### DataSourceId / Schema / Catalog 规则

| 场景 | 必填参数 |
|---|---|
| MaxCompute_SQL / Shell / Python 等非 DB 类 | 仅 `--project-id` |
| Hive / OneService / Hologres / StarRocks 等 | 仅 `--project-id`（由项目计算源决定） |
| MySQL / Oracle / SQLServer / PostgreSQL 等 | `--data-source-id` + `--data-source-schema` |
| Presto 等 | `--data-source-id` + `--data-source-catalog` |

## 10. 结果获取与格式

### 获取结果命令

```bash
aliyun dataphin-public get-ad-hoc-task-result \
  --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --task-id $TASK_ID --sub-task-id 0 \
  --user-agent "$USER_AGENT" --format json
```

### 常见结果格式

**MaxCompute_SQL / Hive 类**：
```text
[["_c0","_c1","_c2","_c3"],[1,2,3,4]]
```
- 第一行为列名（未命名列默认 `_c0`, `_c1`...）
- 第二行起为数据行

**DATABASE_SQL（PostgreSQL）**：
```text
COLUMN_TYPE:[{"name":"?column?","type":"int4"},...]
[["?column?","?column?","?column?","?column?"],[1,2,3,4]]
```
- 首行包含 COLUMN_TYPE 元数据
- 随后为 `[headers, rows...]`

### 结果延迟

`get-ad-hoc-task-result` 在任务刚结束时可能返回空 `Result`（或 `ExecuteResult` 不存在），因为输出数据可能尚未上传到结果服务。建议：
1. 先通过 `get-ad-hoc-task-log` 确认 `TaskStatus: SUCCESS`
2. 再调用 `get-ad-hoc-task-result`，必要时等待 3-10 秒

## 11. 常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| `unknown option '--script'` | CLI 不存在 `--script` 参数 | 使用 `--code` |
| `Missing required argument: data-source-id` | DATABASE_SQL 未传数据源 | 加 `--data-source-id` 和 `--data-source-schema` |
| `InvalidDataSource` / 数据源不存在 | `--data-source-id` 错误或环境不匹配 | 用 `list-data-source-with-config` 确认 |
| `InvalidOperatorType` | OperatorType 拼写错误或用了数值 | 使用字符串枚举，如 `MaxCompute_SQL` |
| `get-ad-hoc-task-result` 返回空 | 任务尚未完成或结果未上传 | 先查日志确认 SUCCESS，再重试 |
| `SubTaskId not found` | `--sub-task-id` 错误 | sub-task-id 从 0 开始 |

## 12. ✗ 不要做

- ✗ 用 `--script` 代替 `--code`
- ✗ DATABASE_SQL 只传 `--data-source-id` 不传 `--data-source-schema`
- ✗ 用数值枚举（如 `5`、`998`）代替字符串 OperatorType
- ✗ `--sub-task-id` 从 1 开始（正确从 0 开始）
- ✗ 任务一提交就立即取结果，不查日志确认状态
- ✗ 未带 `--user-agent` 调用 aliyun API 命令
- ✗ 硬编码真实 tenant-id / project-id / data-source-id

## 13. 相关命令

- `aliyun dataphin-public execute-ad-hoc-task` — 提交即席查询
- `aliyun dataphin-public get-ad-hoc-task-result` — 获取即席查询结果
- `aliyun dataphin-public get-ad-hoc-task-log` — 获取即席查询日志
- `aliyun dataphin-public list-data-source-with-config` — 查找可用的数据源
- `submit-batch-task`（经套件入口路由加载） — 即席查询验证通过后转成持久化任务
---
name: execute-ad-hoc-task
description: |-
  执行即席查询任务（临时跑 SQL / 建表 / 查元信息，不创建持久化任务）。 触发场景：执行 SQL / 即席查询 / 临时跑一段代码 / 建表语句 / 查数据源表 / execute-ad-hoc-task / DATABASE_SQL / MaxCompute_SQL。 OperatorType 为字符串枚举：MySQL/Oracle/PostgreSQL/SQLServer 统一用 DATABASE_SQL；MaxCompute 用 MaxCompute_SQL。 SQL 类需填 DataSourceId，MaxCompute_SQL 不需要。参数名是 --code 不是 --script。 触发词：执行 SQL、即席查询、临时跑代码、建表、execute-ad-hoc-task、DATABASE_SQL、MaxCompute_SQL、ad-hoc、查表结构。
---
# 即席查询任务 skill

## 适用场景

- 临时跑一段 SQL / 脚本验证数据或查元信息
- 不想建持久化任务，只想一次性执行
- **查询 MySQL、Oracle、PostgreSQL、SQLServer 等数据库**：使用 `--operator-type DATABASE_SQL`，必须同时传 `--data-source-id` 和 `--data-source-schema`

## 命令 & 官方文档

- CLI：`aliyun dataphin-public execute-ad-hoc-task --help`
- OpenAPI：[ExecuteAdHocTask](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/ExecuteAdHocTask)

## 顶层参数骨架

```text
--tenant-id <int>              必填 | 租户 ID
--project-id <int>             必填 | 项目 ID（profile 已配置可省略）
--operator-type <string>       必填 | 任务类型（字符串枚举，见下表）
--code <string>                必填 | 任务脚本
--data-source-id <string>      数据库 SQL 类必填 | 数据源 ID
--data-source-catalog <string> 可选 | Presto 等需设置 Catalog 的数据源
--data-source-schema <string>  可选 | Oracle/MySQL 等需设置 Schema 的数据源
--param-list <JSON array>      可选 | 运行参数，${var} 形式注入 Code
```

## OperatorType 枚举

> `execute-ad-hoc-task` 使用**字符串枚举**（如 `MaxCompute_SQL`、`DATABASE_SQL`）。
> MySQL / Oracle / PostgreSQL / SQLServer 等关系型数据库统一使用 **DATABASE_SQL**。
> 💡 **术语**：ODPS（Open Data Processing Service）是 MaxCompute 的旧名称，`MaxCompute_SQL` 对应旧称 `ODPS_SQL`，配置项、文档中仍可能出现 `odps` 字样。

| OperatorType（字符串） | Code 语言 | DataSourceId | 说明 |
|---|---|---|---|
| `MaxCompute_SQL` | MaxCompute SQL | ✗ | 使用项目绑定的 MaxCompute 计算源 |
| `Hive_SQL` | Hive SQL | ✗ | Hive 数据源 |
| `Hive_SQL_23X` | Hive 2.3.x SQL | ✗ | |
| `HIVE_SQL_FUSION_INSIGHT_80X` | FusionInsight 8.x SQL | ✗ | |
| `COMMON_HIVE_SQL` | 通用 Hive SQL | ✗ | |
| `MaxCompute_MR` | MaxCompute MapReduce | ✗ | |
| `SPARK_SQL_ON_MAX_COMPUTE` | Spark SQL on MaxCompute | ✗ | |
| `SPARK_JAR_ON_MAX_COMPUTE` | Spark JAR on MaxCompute | ✗ | |
| `SPARK_SQL_ON_HIVE` | Spark SQL on Hive | ✗ | |
| `Spark_JAR_ON_HIVE` | Spark JAR on Hive | ✗ | |
| `Shell` | Shell 脚本 | ✗ | |
| `PAI_DESIGNER` | PAI Designer | ✗ | |
| `DataX` | DataX 配置 | ✗ | |
| `Merge` | Merge 任务 | ✗ | |
| `Python` | Python 2.7 | ✗ | |
| `Python37x` | Python 3.7 | ✗ | |
| `Perl` | Perl | ✗ | |
| `Python311x` | Python 3.11 | ✗ | |
| `OneService_SQL` | OneService SQL | ✗ | |
| `ONE_SERVICE_SQL_ADB_FOR_PG` | ADB for PG SQL（AnalyticDB for PostgreSQL） | ✗ | |
| `OneService_SQL_Hive11x` | Hive 1.1.x SQL | ✗ | |
| `HOLOGRES_SQL` | Hologres SQL | ✗ | |
| `OneService_SQL_Hive23x` | Hive 2.3.x SQL | ✗ | |
| `Dlink` | Dlink（集成管道） | ✗ | |
| `ONE_SERVICE_SQL_ADB_FOR_MYSQL` | ADB for MySQL SQL（AnalyticDB for MySQL） | ✗ | |
| `ADB_FOR_PG` | ADB for PG SQL（AnalyticDB for PostgreSQL） | ✗ | |
| `Flink_Streaming` | Flink 实时 | ✗ | |
| `Flink_Batch` | Flink 离线 | ✗ | |
| `ONE_SERVICE_SQL_TDH_INCEPTOR` | TDH Inceptor SQL | ✗ | |
| `ARGODB_SQL` | ArgoDB SQL | ✗ | |
| `IMPALA_SQL` | Impala SQL | ✗ | |
| `STARROCKS_SQL` | StarRocks SQL | ✗ | |
| `SPARK_SQL` | Spark SQL | ✗ | |
| `GAUSS_SQL` | Gauss SQL | ✗ | |
| `ONE_SERVICE_SQL_HIVE_CDP` | Hive CDP SQL | ✗ | |
| `ONE_SERVICE_SQL_HIVE_ASIA_INFO_DP_53X` | Hive AsiaInfo DP 5.3.x SQL | ✗ | |
| `HADOOP_MR` | Hadoop MR | ✗ | |
| `CHECK` | 检查任务 | ✗ | |
| `VIRTUAL` | 虚拟节点 | ✗ | |
| **`DATABASE_SQL`** | **通用数据库 SQL** | **✓ 必填 + Schema** | **MySQL / Oracle / SQLServer / PostgreSQL 等关系型数据库，需同时传 `--data-source-schema`** |
| `EXTERNAL_TRIGGER` | 外部触发 | ✗ | |

### DataSourceId / Schema / Catalog 规则

| 场景 | 必填参数 |
|---|---|
| MaxCompute_SQL / Shell / Python 等非 DB 类 | 仅 `--project-id` |
| Hive / OneService / Hologres / StarRocks 等 | 仅 `--project-id` |
| MySQL / Oracle / SQLServer / PostgreSQL 等 | `--data-source-id` + `--data-source-schema` |
| Presto 等 | `--data-source-id` + `--data-source-catalog` |

## 按 OperatorType 的示例

### MaxCompute_SQL

```bash
aliyun dataphin-public execute-ad-hoc-task \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --operator-type MaxCompute_SQL \
  --code "SELECT COUNT(*) FROM my_table WHERE ds='${bizdate}'" \
  --param-list '[{"Key":"bizdate","Value":"20260101"}]'
```

### DATABASE_SQL（MySQL/Oracle/SQLServer/PostgreSQL 等）

```bash
aliyun dataphin-public execute-ad-hoc-task \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --operator-type DATABASE_SQL \
  --data-source-id <mysql-datasource-id> \
  --data-source-schema qbi_test \
  --code "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns WHERE table_schema='qbi_test' AND table_name='company_sales_record' ORDER BY ORDINAL_POSITION"
```

### HOLOGRES_SQL

```bash
aliyun dataphin-public execute-ad-hoc-task \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --operator-type HOLOGRES_SQL \
  --data-source-id <hologres-datasource-id> \
  --code "SELECT current_timestamp"
```

### Shell

```bash
aliyun dataphin-public execute-ad-hoc-task \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --operator-type Shell \
  --code "echo 'Hello World'"
```

## 获取任务结果

```bash
# 查结果
aliyun dataphin-public get-ad-hoc-task-result \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --task-id <从返回的TaskId取> \
  --sub-task-id 1

# 查日志
aliyun dataphin-public get-ad-hoc-task-log \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --task-id <TaskId> \
  --sub-task-id 1 \
  --offset 0
```

## 常见坑

1. **OperatorType 大小写敏感**：必须用原始字符串枚举（如 `MaxCompute_SQL`、`DATABASE_SQL`），不能用数值（如 `5`、`998`），也不能用 kebab-case（如 `max-compute-sql`）——数值枚举仅 `create-batch-task --task-type` 使用
2. **数据库 SQL 必须带 DataSourceId**：`--data-source-id` 为字符串类型（大整数 ID 避免精度丢失），写成 integer 可能被拒或尾数截断
3. **DATABASE_SQL 需额外传 --data-source-schema**：MySQL/Oracle/SQLServer/PostgreSQL 等数据库 SQL 类型，仅传 `--data-source-id` 不够，必须同时传 `--data-source-schema` 指定库名/schema
4. **ParamList 变量不会自动转义**：`${bizdate}` 只会做字符串替换，SQL 里自己处理引号
5. **即席查询结果过大**：部分版本限制返回行数，超出会截断；大查询建议建正式任务
6. **sub-task-id 从 0 开始**：`get-ad-hoc-task-result` 的 `--sub-task-id` 从 0 开始
7. **参数名是 `--code` 不是 `--script`**：CLI 不存在 `--script` 参数，传 `--script` 会报 `error: unknown option '--script'`。正确参数名是 `--code`
8. **多条 SQL 分号提交会被拆成并行子任务，执行顺序不保证**（[Agent 自主发现]）：一次提交 N 条分号分隔的 SQL 返回 `SubTaskCount: N` 并行执行——有依赖顺序的语句（如 `ADD COLUMN` 与其后的 `COMMENT ON COLUMN`）可能乱序报错（`column does not exist`）。有依赖的 DDL 分批串行提交或逐条提交；失败子任务可单独补跑；逐子任务查 `get-ad-hoc-task-log` 确认状态（INIT/WAIT_RESOURCE/SUCCESS/FAILED），不能只看提交成功
9. **`--project-id` 必须当顶层 flag 传，写进 JSON 不生效**（[Agent 自主发现]）：OpenAPI 定义里 `ProjectId` 是 `ExecuteCommand` 对象的必填字段，但 CLI 插件**把该对象整体扁平化了——根本不存在 `--execute-command` 这个 flag**，子字段全变成顶层 flag（`--code` / `--operator-type` / `--project-id` / `--param-list` / `--data-source-*`）。写 `--execute-command '{"ProjectId":...,"Code":...}'` 会报 `Error: --project-id is required`（实测连踩 5 次）。推论：**不要凭 api-meta 推断 CLI 入参形态，以 `--help` 输出的 flag 为准**
10. **不要默认拉 `get-ad-hoc-task-log` 全文（上下文开销）**（[Agent 自主发现]）：实测一轮探查中 task-log 占了工具输出总量的 16%（单次可达 9k+ 字符），而取数只需 `get-ad-hoc-task-result`。默认路径：直接取 result；仅在结果为空/报错/需确认状态时才拉日志，且带 `--cli-query 'LogInfo.TaskStatus'` 只取状态，看报错正文时再取 `LogInfo.Content` 并 `tail` 尾部
11. **采样/探查类 SQL 的表名必须用「项目名.表名」全限定名**（[Agent 自主发现]）：写裸表名（`FROM t_org`）可能解析到其他同名空表，查出 0 行但**任务状态仍为成功**（返回只有表头），极易误判为“表无数据”。正确：`FROM mfg_fin_ods.t_org`；若结果为空先换全限定名重试一次再下结论

## 相关命令

- [submit-batch-task.md](./submit-batch-task.md) — 即席查询验证通过后转成持久化任务
- `aliyun dataphin-public get-ad-hoc-task-result` — 获取即席查询结果
- `aliyun dataphin-public get-ad-hoc-task-log` — 获取即席查询日志
- `aliyun dataphin-public list-data-source-with-config` — 找可用的 DataSourceId
