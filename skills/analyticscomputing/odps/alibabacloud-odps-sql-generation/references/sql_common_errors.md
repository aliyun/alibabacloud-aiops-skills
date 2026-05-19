# MaxCompute SQL 错误恢复手册

SQL 执行失败后的决策参考。错误消息已自解释、用户无需任何动作的错误此处不展开。

## 自动重试策略

| 类别 | 重试动作 | 最大次数 |
|------|---------|---------|
| 编译期错误（改 SQL 类） | 改 SQL 后重试 | 3 |
| 运行时错误（可 SET 参数类） | 改 SQL 或 SET 参数 | 3 |
| 同错误连续 3 次失败 | 停止并上报原始错误文本 | — |

> **DML 写入幂等性提醒**：自动重试默认仅安全用于 SELECT、编译期错误、以及 `INSERT OVERWRITE` 这类幂等写入。`INSERT INTO` / `MERGE` / `UPDATE` / `DELETE` **不能盲目重试**——同一作业可能已部分提交，重试会重复写入或与上次结果冲突。重试这类语句前必须先确认 instance 状态（成功/失败/未提交）。

## 如何匹配条目

错误码前缀定位大类：`0130xxx` 编译 / `0123xxx` 运行 / `0140xxx` Sandbox / `1850xxx` MCQA。

`ODPS-0130071` 和 `ODPS-0010000` 是 **wrapper**（同码含多种子场景），必须用消息关键词分流，见下文。

## 专用语义错误码

| 错误码 | 含义 | 修复要点 |
|--------|------|---------|
| ODPS-0130131 | Table not found | 检查表名拼写、project/schema 前缀、查询者 ACL |
| ODPS-0130121 | Invalid argument type | 对照函数签名 `CAST` 输入到正确类型 |
| ODPS-0130141 | Illegal implicit type cast | 显式 `CAST(col AS ...)`（**注意**：`Partition not found` 不是这个码，是 0130071） |
| ODPS-0130241 | Illegal union operation | UNION 列数/类型一致；显式 `CAST` 各分支到统一类型（隐式类型提升常失败：BIGINT vs DECIMAL、STRING vs BIGINT） |
| ODPS-0130252 | Cartesian product is not allowed | 加 ON 条件；或 `/*+ MAPJOIN(small_table) */`；兜底 `SET odps.sql.allow.cartesian=true;` |
| ODPS-0140081 | Unsupported join type | MAPJOIN 不支持的 OUTER 配置；改换 JOIN 类型或去 MAPJOIN Hint |
| ODPS-0130013 | Authorization exception / Access Denied | 表/列 ACL 不足，联系 owner 授权 |
| ODPS-0130161 | Syntax error 或 SQL 规模超限（消息含 `DFA count`）| 修语法；规模超限见下节"SQL 规模超限"|

### ODPS-0130071 是通用语义异常 wrapper（覆盖大量子场景）

**不要试图穷举 0130071 的子场景**——它是 MaxCompute 兜底语义错误码，所有没有专用错误码的语义异常都用它。

正确流程：
1. 先比对上面"专用语义错误码"表 → 命中则按那条修复
2. 错误码确为 0130071 → 按消息关键词查下文"高频子场景"

---

## 编译期错误

### SQL 规模超限（三个同根错误码）

触发阶段不同，修复方向一致：

| 错误码 | 消息特征 | 触发阶段 |
|--------|---------|---------|
| ODPS-0130161 | `Parse fail ... DFA count` | 解析期 |
| ODPS-0130071 | `compile fail ... AST node count` | 语义期 |
| ODPS-0010000 | `The Size of Plan is too large` | 执行计划期（>1MB 拒收） |

**修复**（只能降 SQL 复杂度，无 SET 开关）：
- 拆 CTE 或多条 `INSERT OVERWRITE` 串联，用中间表
- 减 JOIN 层数；利用分区裁剪缩小叶子扫描规模
- 单 SELECT 建议 ≤ 5 个窗口函数（软上限）；UNION ALL ≤ 256 张

### ODPS-0010000 wrapper：Plan 过大 vs worker OOM（消息分流）

错误码 0010000 复用于两种性质相反的场景，必须按消息文本判断：

| 消息关键词 | 子场景 | 修复方向 |
|-----------|--------|---------|
| `The Size of Plan is too large` | **编译期** 执行计划过大被拒（>1MB） | 拆 SQL，参考上一节"SQL 规模超限" |
| `worker out of memory` / `sigkill(oom)`（无 `sqltask` 字样） | **运行期** worker 进程 OOM | 先识别失败 task 类型（mapper/reducer/joiner），按对应参数调内存：`odps.sql.mapper.memory` / `odps.sql.reducer.memory` / `odps.sql.joiner.memory`（单位 MB，常见 4096-8192）；同时查算子热点和数据倾斜 |
| `sqltask` + OOM | 编译/规划期 SQL 任务进程 OOM | 减分区扫描、拆 SQL、减元数据查询；**不是算子内存问题**，调 stage memory 无效 |

**修复顺序建议（worker OOM）**：
1. 看 logview / instance summary，识别失败的 task 类型与具体算子（HashJoin / SortMerge / WindowAgg / UDF）
2. 查倾斜：DistinctValueCounts、JOIN key 分布、单 task input bytes 是否远高于平均
3. 倾斜先按倾斜处理（SKEWJOIN hint / 加随机后缀 / 拆热点 key），再考虑加内存
4. 上述都不奏效，**且数据量本身就大** → 调对应阶段内存或拆 SQL
5. **易误判**：看到 `Size of Plan` 字样不要调 stage 内存（根因是编译期计划大小）；HashJoin/窗口算子膨胀有时光加内存解决不了，得先治倾斜

### ODPS-0130071 高频子场景

| 消息关键词 | 场景 | 修复 |
|-----------|------|------|
| `compile fail ... AST node count` | SQL 规模超限（语义期）| 拆 CTE / 多条 INSERT 串联 |
| `recursive-cte ... exceed max iterate number %d` | 递归 CTE 超迭代 | `SET odps.sql.rcte.max.iterate.num=100;`（默认 10，硬上限 100，更大值被截断）；否则改写多次 JOIN |
| `partition not found:<spec>` | 分区不存在 | 检查分区值格式（`'YYYYMMDD'` vs `'YYYY-MM-DD'`），`SHOW PARTITIONS <table>` 确认 |
| `column %s cannot be resolved` | 列名解析失败 | **大小写敏感**，`DESC <table>` 确认列名；编辑距离接近时编译器会给 "Did you mean %s?" |
| `expect equality expression for join condition` | 非等值 JOIN（无 mapjoin hint）| 改写为等值 JOIN，或 `/*+ MAPJOIN(small_table) */` |
| `function sum cannot match any overloaded functions with (BOOLEAN)` | `SUM(布尔表达式)` | 改 `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` 或 `COUNT_IF(...)` |
| `expression is not in GROUP BY` | 非聚合列未在 GROUP BY | **优先**：把列加入 GROUP BY，或换成确定性聚合（`MAX`/`MIN`/`SUM`）；仅在"任意代表值都可接受"时才用 `ANY_VALUE(col)`（**结果非确定**，每次执行可能取不同值）|
| `INSERT INTO HASH CLUSTERED table` | Hash 聚簇表不支持 INSERT INTO | 改 `INSERT OVERWRITE` |
| `invalid partition value` | 动态分区值含非法字符 | 仅允许字母/数字/空格 + `_@$#.!:-`；≤255 字节；无中文；运行期不允许 NULL（"首字符必须字母"非通用约束，部分场景可放宽，遇报错按官方文档版本核对） |
| `function date_format is not supported in current mode` | DATE_FORMAT 类型/模式限制 | TIMESTAMP 输入 → `SET odps.sql.type.system.odps2=true;`；其他类型 → `SET odps.sql.hive.compatible=true;`；推荐改 TO_CHAR |
| `function or view '<name>' cannot be resolved` | 函数/视图名错（如 IFNULL）| 检查拼写；`IFNULL` 不存在，用 `NVL` 或 `COALESCE` |
| `Result of a union cannot be a map table` | UNION + MAPJOIN 组合限制 | 改写 SQL，避免 UNION 内 MAPJOIN |
| `DDL does not support explain` | EXPLAIN 接 DDL 语句 | 去掉 EXPLAIN |
| 其他 `Semantic analysis exception` | 数百种细分场景 | 按消息文本结合上下文判断 |

### ODPS-0130252 笛卡尔积不允许

几个约定俗成的 rewrite pattern：

| 场景 | 改写策略 |
|------|---------|
| `CROSS JOIN + AVG/SUM 子查询` | 窗口函数 `AVG(x) OVER()` 替代 |
| `FROM a, b` 无 ON | 显式 `JOIN ... ON` |
| 非等值 JOIN（业务必须 CROSS 类语义）| 加 `/*+ MAPJOIN(small_table) */` |
| 全组合打标（**慎用**）| Dummy key：两侧 `SELECT *, 1 AS jk`，JOIN ON jk=jk |

> Dummy key 全组合是 **N×M 笛卡尔积**，结果集会爆炸式增长。**只在以下条件全满足时使用**：(1) 业务明确需要全组合；(2) 两侧基数都很小且可控；(3) 用户接受存储/计算成本；(4) 配合 `/*+ MAPJOIN(small) */` 把小表广播。否则用窗口函数 / 分组聚合 / 半笛卡尔（带筛选条件的 JOIN）替代。

兜底（慎用）：`SET odps.sql.allow.cartesian=true;`

### ODPS-0123091 脏值 CAST 失败

加 `CAST()` **无效**——CAST 本身就是报错处。数据里有脏值。

**修复（按优先级）**：
1. 预过滤：`WHERE col RLIKE '^-?[0-9]+$'` 后再 CAST —— 显式控制脏值如何处理（剔除/标记/单独表）
2. 上游审计：把脏值写入审计表 / 加日志，不要静默吞噬
3. 兜底：`SET odps.function.strictmode=false;` 或 `SET odps.sql.udf.strict.mode=false;`（公有云常见前者，不同环境参数名可能不同）。**这个开关不是"忽略整行"**——它让无效 CAST 转成 `NULL` 通过，**整行其他列照常输出**。所以下游必须能区分"业务 NULL"和"CAST 失败 NULL"，否则会造成数据质量问题

---

## 运行时错误

### ODPS-0123065 Join exception

两种触发路径，错误文本不直接区分：

| 路径 | 识别 | 修复 |
|------|------|------|
| 用户显式 `/*+ MAPJOIN(...) */` Hint 超阈值 | SQL 里能看到 Hint | 去掉 Hint，让 CBO 决定 |
| CBO 自动 MAPJOIN（无 Hint） | 错误文本含 `small table exceeds when auto map join applied` | `SET odps.optimizer.auto.mapjoin.threshold=<较小字节>;`（默认 128MB = 134217728），或设 0 禁用自动 MAPJOIN |

调大 MAPJOIN 内存：`SET odps.sql.mapjoin.memory.max=<N>;`（单位 MB，常见 1024-4096）。同时检查 JOIN key 是否严重倾斜。

### ODPS-0123131 User defined function exception

UDF 抛异常 / 输入数据使 UDF 出错。

**修复**：
- 对照 UDF 签名检查输入列类型
- UDF 内部加 try/catch 兜底，避免脏值导致整个作业失败
- 上游加 `WHERE` 预过滤脏值
- 优化 UDF 代码（可能要 UDF 作者修）

### ODPS-0123144 UDF 超时

错误文本含 `kInstanceMonitorTimeout` + `usually caused by bad udf performance`。根因是 UDF 操作太慢（死循环/复杂算法/外部调用）。

**修复（按推荐顺序）**：
1. **先定位慢点**：看 logview UDF profiling，识别是死循环 / 复杂算法 / 外部调用 / 还是个别坏数据卡住
2. 上游加 `WHERE` 预过滤异常输入（坏数据是常见根因，比 timeout 调大见效快）
3. `SET odps.sql.executionengine.batch.rowcount=32;`（减小单批处理量，缓解 batch 内坏数据连锁）
4. 优化 UDF 代码（根治：去除外部慢调用、加缓存、改算法）
5. **临时**放宽 timeout：`SET odps.sql.udf.timeout=3600;`（范围 0-3600s，默认 600；`odps.function.timeout` 是旧 alias）—— 仅在前面措施都不奏效且需赶时间产出时使用

### ODPS-1850001 MCQA 查询加速模式限制

| 场景 | 处理 |
|------|------|
| UDF 触发回退 | `SET odps.mcqa.disable=true;` |
| DML（INSERT/UPDATE/DELETE） | MCQA 只支持 DDL/DQL，必须关 MCQA |
| 其他限制 | 直接关 MCQA 重试 |

### ODPS-0140171 Sandbox violation / archive 加载失败

三种不同性质错误共用这个错误码，**不能一刀切**：

| 消息关键词 | 本质 | 修复 |
|-----------|------|------|
| `permission denied to read archive resource` / `not allow symlink in archive files` | Hive Bridge Sandbox 的 **Java archive 加载限制**（保护第三方 Java 代码加载，不是数据 ACL）| 仅当场景是外部表 + TextFile + LazySimpleSerDe 时，可试 `SET odps.ext.hive.lazy.simple.serde.native=true;`——切 native 读取器绕过 Hive Bridge。其他格式不适用 |
| `PanguPermission` / `permission denied for volume` | **Volume 数据访问权限**（数据 ACL）| 必须走授权（`GRANT Read ON VOLUME ...`），**不能 SET 绕过** |
| 非外部表 `Access Denied` | 表/列 ACL | 联系 owner 授权 |

**重要**：`odps.ext.hive.lazy.simple.serde.native=true` **不是 ACL 绕过 flag**，只是切换读取代码路径。Sandbox 保护的是 Java 代码加载安全，对"数据层面权限拒绝"无效。

### UDF 注册 / 调用问题

按错误根因分两类：

**(A) 注册侧问题（jar / 注解 / 类签名 / 环境）—— 修 UDF 本身，不动调用 SQL**

| 错误关键词 | 修复方向 |
|-----------|---------|
| `cannot be loaded from any resources` | 检查 `CREATE FUNCTION ... USING '<jar>'` 资源是否上传 |
| `does not match annotation` | UDF 类的 `@Resolve` 注解与实际签名一致 |
| `UnsatisfiedLinkError` | Java 版本 / native 库不匹配 |
| `Invalid function class ... static evaluate method` | UDF 类签名错（缺 `evaluate` 方法或参数类型不对）|

**(B) 调用侧问题（参数类型不匹配）—— 改 SQL 的输入类型**

| 错误关键词 | 修复方向 |
|-----------|---------|
| `Wrong arguments UDTF ... initialize returned failed` | UDTF 输入参数类型不符；调用 SQL 里显式 `CAST(col AS <expected>)` |
| `cannot match any overloaded functions with (...)` | 调用类型与 UDF 签名所有重载都不匹配；按签名 CAST 输入 |
