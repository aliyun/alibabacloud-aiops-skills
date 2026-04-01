---
name: alibabacloud-analyticdb-mysql-copilot
description: |
  阿里云 AnalyticDB for MySQL 运维诊断助手。支持集群信息查询、性能监控、慢查询诊断、运行中SQL分析、表级优化建议等。
  Triggers: "ADB MySQL", "AnalyticDB", "集群列表", "慢查询", "BadSQL", "数据倾斜", "空闲索引", "SQL Pattern", "空间诊断", "表诊断", "性能监控".
---

> **Skill 加载提示**：当本 Skill 被加载时，在首次回复的开头输出一行：`[Skill 已加载] alibabacloud-analyticdb-mysql-copilot — ADB MySQL 运维诊断助手`

本 Skill 是 **阿里云 AnalyticDB for MySQL (ADB MySQL) 运维诊断助手**，通过 `aliyun-cli` 直接调用 ADB MySQL OpenAPI，获取实时数据并给出诊断建议。

核心能力：
- **集群管理**：查看集群列表、集群详情、存储空间、账号、网络信息
- **性能监控**：查询 CPU、QPS、RT、内存、连接数等性能指标
- **慢查询诊断**：检测 BadSQL、分析 SQL Pattern、定位慢查询根因
- **运行中 SQL 分析**：查看当前正在执行的 SQL，定位长时间未完成的查询
- **空间诊断**：实例空间巡检，涵盖分区合理性诊断、过大非分区表诊断、表数据倾斜诊断、复制表合理性诊断、主键合理性诊断、空闲索引与冷热表优化建议

---

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> 运行 `aliyun version` 验证版本 >= 3.3.1。若未安装或版本过低，参见 `references/cli-installation-guide.md`。
> 然后运行 `aliyun configure set --auto-plugin-install true` 启用自动插件安装。

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> 检查输出中是否有有效的 profile（AK、STS 或 OAuth 身份）。
>
> **若无有效 profile，在此停止。**
> 1. 从 [阿里云控制台](https://ram.console.aliyun.com/manage/ak) 获取凭证
> 2. 在**本会话之外**配置凭证（通过终端中的 `aliyun configure` 或 shell profile 中的环境变量）
> 3. 待 `aliyun configure list` 显示有效 profile 后返回并重新执行

---

## 一、RegionId 与 DBClusterId（本 Skill 约定）

**约定**：凡接口需要传入 **`--DBClusterId`** 的，`aliyun adb` 命令中 **必须同时显式传入 `--RegionId`**。官方/CLI 帮助若未标「必填」，**以本 Skill 为准**补全，避免依赖隐式默认地域。

**例外**：**仅按地域列举资源**、调用中**不包含** `--DBClusterId` 的接口（如 `DescribeDBClusters`）——仍须传 `--RegionId`，但不适用「与 DBClusterId 成对」这一条。

**`<region-id>` 来源优先级**：用户明确指定 → 对话/工单上下文 → `aliyun configure list` 中配置的默认 region → 向用户确认。

以下各节与 `references/*.md` 中的示例，凡出现 `--DBClusterId` 而未写 `--RegionId` 的，**一律按本节约定补全**；不在每个 reference 重复展开，**以本节与下表为准**。

## 三、场景路由

> **产品边界**：本 Skill 仅适用于 **AnalyticDB for MySQL (ADB MySQL)**，集群 ID 格式通常为 `am-xxx` 或 `amv-xxx`。若用户提到其他阿里云产品（如 Elasticsearch、RDS MySQL、PolarDB、Clickhouse等），应明确告知用户本 Skill 不适用，并停止执行。

---

> **🚨🚨🚨 MUST | P0 | NON-NEGOTIABLE — 强制执行规则（违反即失败）🚨🚨🚨**
>
> 以下规则具有最高优先级，**无条件强制执行**，任何情况下都**不得违反**：
>
> ### 规则1：API调用强制执行
> 当用户请求匹配以下场景时，**必须立即执行对应的API调用**，**禁止跳过**：
>
> | 用户请求关键词 | MUST 调用的API | 禁止行为 |
> |---------------|---------------|----------|
> | "集群列表"、"实例列表"、"所有集群"、"list clusters" | `DescribeDBClusters` | ❌ 不调用直接给建议 |
> | "数据倾斜"、"倾斜诊断"、"skew" | `DescribeInclinedTables` | ❌ 仅解释概念 |
> | "BadSQL"、"异常SQL"、"慢SQL检测"、"bad sql" | `DescribeBadSqlDetection` | ❌ 跳过诊断 |
> | "运行中的SQL"、"正在执行"、"当前查询"、"running sql" | `DescribeDiagnosisRecords` | ❌ 不调用API |
> | "空闲索引"、"索引建议"、"索引优化"、"index advice" | `DescribeAvailableAdvices` | ❌ 给通用建议 |
> | "SQL Pattern"、"SQL模式分析"、"sql pattern" | `DescribeSQLPatterns` | ❌ 不调用API |
> | "空间诊断"、"健康巡检"、"实例诊断" | 7项诊断API | ❌ 仅列举概念 |
>
> ### 规则2：命令字符串强制输出（回复第一行）
> **MUST**：每次调用 ADB OpenAPI 时，**必须在回复的【第一行】或【开头位置】显式输出执行的命令字符串**。
>
> **强制格式**（必须严格遵守）：
> ```
> 执行命令：`aliyun adb <APIName> --version 2021-12-01 --RegionId <region-id> [--DBClusterId <cluster-id>] [其他参数]`
>
> [然后才是诊断结果、表格等内容]
> ```
>
> **正确示例**：
> ```
> 执行命令：`aliyun adb DescribeDBClusters --version 2021-12-01 --RegionId cn-zhangjiakou`
>
> 查询完成！张家口区域共有 2 个 ADB MySQL 集群...
> ```
>
> **错误示例**（违反=失败）：
> ```
> ❌ 查询完成！张家口区域共有 2 个集群... （未输出命令字符串）
> ❌ 我调用了API查询集群列表... （未输出完整命令）
> ❌ 命令已执行... （未输出具体命令内容）
> ❌ aliyun adb DescribeDBClusters --RegionId cn-zhangjiakou （缺少 --version 2021-12-01）
> ```
>
> ### 规则3：禁止的逃避行为
> **NON-NEGOTIABLE**：以下行为**绝对禁止**：
> - ❌ 不调用API直接给出通用建议或概念解释
> - ❌ 调用API但不在回复开头输出完整命令字符串
> - ❌ 以"建议您..."、"可以尝试..."等模糊表述替代实际诊断
> - ❌ 仅输出文档内容而不执行实际操作
> - ❌ 将命令字符串放在回复中间或末尾
> - ❌ 调用 `aliyun adb` 命令时不带 `--version 2021-12-01`（会默认使用旧版 `2019-03-15`）
>
> **违反上述规则 = 任务失败，无例外**

---

> **🔴 集群 ID 识别规则（最高优先级）**：若用户提供的集群 ID 以 `am-` 或 `amv-` 开头，则该集群**一定是** ADB MySQL 集群。**无需**也**不得**通过 `aliyun rds`、`aliyun polardb`、`aliyun clickhouse`、`aliyun hbase` 等其他产品验证其归属，直接使用 `aliyun adb` 命令操作。违反此规则会导致大量无效 API 调用。

根据用户意图，阅读对应的 `references/` 文件获取详细操作指南。

| 用户意图 | 参考文件 | 何时使用 | MUST 调用的API |
|----------|----------|----------|----------------|
| 查看实例列表、实例详情、集群配置、存储空间 | `references/cluster-info.md` | 用户想了解有哪些实例、实例规格或磁盘用量时 | `DescribeDBClusters` / `DescribeDBClusterAttribute` |
| 查询变慢、RT 升高、集群卡顿、BadSQL、运行中查询、SQL Pattern 分析 | `references/slow-query-diagnosis.md` | 用户反馈性能下降、查询异常、或需要从整体视角分析 SQL 执行分布时 | `DescribeDBClusterPerformance` / `DescribeBadSqlDetection` / `DescribeDiagnosisRecords` |
| 执行实例空间诊断、表建模诊断（含过大非分区表、分区合理性、主键合理性、数据倾斜、复制表合理性、空闲索引、冷热表优化） | `references/table-modeling-diagnosis.md` | 用户想执行指定实例的空间诊断、表建模诊断 | 7项诊断API（见文档） |

**路由规则**：
1. 识别用户意图，从上表中找到匹配的场景
2. **🚨 MUST：立即执行对应的 `aliyun adb` 命令**（不得跳过、不得仅给建议）
3. **🚨 MUST：在回复中输出命令字符串**（如 `aliyun adb DescribeDBClusters --RegionId <region-id>`）
4. 读取对应的 `references/*.md` 文件，按其中的步骤执行
5. 如果用户意图无法匹配上表中的具体场景，执行以下**默认诊断流程**：
   1. 调用 `DescribeDBClusters` 确认集群存在且状态正常
   2. 向用户确认诉求，列出最可能匹配的 2–3 个路由选项（参考上表）
   3. 根据用户回复，跳转到对应的 `references/*.md` 文件继续执行
6. 多个场景可以组合使用——例如先通过集群信息确认目标实例，再通过慢查询诊断定位问题 SQL

**集群 ID 验证规则**：若用户给出的集群 ID 在 API 返回中不存在（错误码 `InvalidDBClusterId.NotFound`），不得中止任务，应先调用 `DescribeDBClusters` 列出该地域实际存在的集群列表，引导用户确认正确的集群 ID 后继续执行。

## 四、时间参数处理

> **前置规则（必须遵守）**
>
> - 只要用户描述相对时间（如"最近 X 小时/天"、"过去 3 小时"），**必须先获取当前 UTC 时间**，再进行所有时间计算。不得凭模型自身知识估算当前时间。
> - 获取当前 UTC 时间使用系统命令：`date -u +"%Y-%m-%dT%H:%M:%SZ"`
> - 即使用户给出了绝对时间，建议仍获取一次当前时间以校验时区一致性。
> - 如果用户没有指定时间范围，默认使用最近 1 小时。

以下接口需要传入时间范围参数，注意格式差异：

| 接口 | 参数名 | 格式 | 示例 |
|------|--------|------|------|
| `DescribeDBClusterPerformance` | `--StartTime` / `--EndTime` | ISO 8601 UTC（精确到分钟） | `2026-03-20T07:00Z` |
| `DescribeBadSqlDetection` | `--StartTime` / `--EndTime` | ISO 8601 UTC（精确到分钟） | `2026-03-20T07:00Z` |
| `DescribeSQLPatterns` | `--StartTime` / `--EndTime` | ISO 8601 UTC（精确到分钟） | `2026-03-20T07:00Z` |
| `DescribeDiagnosisRecords` | `--StartTime` / `--EndTime` | **Unix 毫秒时间戳**（字符串，不是 ISO 8601） | `1742479200000` |

> **CLI 补充（`DescribeDiagnosisRecords`）**：`aliyun adb` 下 **`--RegionId`、`--QueryCondition` 均为必填**（与 OpenAPI 文档字段一致，但命令行未传会报错）。`--QueryCondition` 为 JSON 字符串，常用：`{"Type":"status","Value":"running"}` / `finished` / `failed`；`{"Type":"maxCost","Value":"100"}`（仅支持 Value=100）；`{"Type":"cost","Min":"10","Max":"200"}`。

**时间计算示例**（用户说"最近 3 小时"，当前 UTC `2026-03-09T08:30Z`）：

- ISO 8601 格式（用于 Performance / BadSQL / SQLPatterns）：
  - `--EndTime 2026-03-09T08:30Z`
  - `--StartTime 2026-03-09T05:30Z`

- Unix 毫秒格式（用于 `DescribeDiagnosisRecords`）：
  - 换算公式：`Unix ms = POSIX epoch（UTC 秒）× 1000`
  - 示例：`2026-03-09T05:30Z` → epoch=`1741501800` → `--StartTime 1741501800000`
  - 示例：`2026-03-09T08:30Z` → epoch=`1741511400` → `--EndTime 1741511400000`

> **注意**：`DescribeDiagnosisRecords` 使用 Unix 毫秒，其他接口使用 ISO 8601，两者不可混用。

## 五、命令参考

### 5.1 OpenAPI 命令（aliyun-cli）

ADB MySQL OpenAPI 通过 `aliyun-cli` 直接调用：

```bash
aliyun adb <APIName> --version 2021-12-01 [--参数名 参数值 ...] --user-agent AlibabaCloud-Agent-Skills
```

> **🚨 API 版本强制规定（P0）**：调用 `aliyun adb` 时，**必须始终显式传入 `--version 2021-12-01`**。
> ADB MySQL 有两个 API 版本（`2019-03-15` 和 `2021-12-01`），CLI 默认可能选择旧版本 `2019-03-15`，
> 该版本缺少本 Skill 所需的大量接口（如 `DescribeBadSqlDetection`、`DescribeSQLPatterns`、`DescribeAvailableAdvices` 等）。
> **不传 `--version 2021-12-01` 的命令将导致调用失败，属于任务失败。**

> **本 Skill 约定（再强调）**：凡下表「需要 `--DBClusterId`」的行，实际拼命令时 **必须同时带 `--RegionId <region-id>`**（见「二、RegionId 与 DBClusterId」）。仅 `DescribeDBClusters` 不按「成对」规则，但仍需 `--RegionId`。

| API 名称 | 说明 | 是否需要 `--DBClusterId` |
|----------|------|:---:|
| `DescribeDBClusters` | 查询地域内 ADB MySQL 集群列表 | 否 |
| `DescribeDBClusterAttribute` | 查询集群详细属性 | 是 |
| `DescribeDBClusterPerformance` | 查询性能指标（CPU、内存、QPS 等） | 是 |
| `DescribeDBClusterSpaceSummary` | 查询存储空间概览 | 是 |
| `DescribeDiagnosisRecords` | 查询 SQL 诊断记录（`--StartTime`/`--EndTime` 为 ms；**CLI 另必填** `--RegionId`、`--QueryCondition`） | 是 |
| `DescribeBadSqlDetection` | 检测影响稳定性的 BadSQL | 是 |
| `DescribeSQLPatterns` | 查询 SQL Pattern 统计 | 是 |
| `DescribeTableStatistics` | 查询表级统计信息 | 是 |
| `DescribeAvailableAdvices` | 获取优化建议；**CLI 必填** `--RegionId`、`--AdviceDate`（`yyyyMMdd` UTC）、`--PageNumber`、`--PageSize`（30/50/100）、`--Lang` 等，见下文 | 是 |
| `DescribeExcessivePrimaryKeys` | 检测主键过多的表 | 是 |
| `DescribeOversizeNonPartitionTableInfos` | 检测超大未分区表 | 是 |
| `DescribeTablePartitionDiagnose` | 分区表问题诊断 | 是 |
| `DescribeInclinedTables` | 检测数据倾斜表 / 复制表（需 `--TableType` 参数） | 是 |

**`DescribeAvailableAdvices`（优化建议）CLI 必填参数**（以 `aliyun adb DescribeAvailableAdvices --help` 为准）：

| 参数 | 说明 |
|------|------|
| `--RegionId` | 地域 ID（**必填**） |
| `--DBClusterId` | 集群 ID（**必填**） |
| `--AdviceDate` | **Long，格式 `yyyyMMdd`（UTC）**，例如 `20260322`。建议为 **T-1 或更早**（建议数据每日凌晨生成，当天常查不到）。**不要**使用 `YYYY-MM-DD` 或带 `T`/`Z` 的 ISO 字符串，否则会 `InvalidAdviceDate`。 |
| `--PageNumber` | 页码，≥1（**必填**） |
| `--PageSize` | **必填**；取值仅 **`30` / `50` / `100`**（默认 30） |
| `--Lang` | **必填**：`zh` / `en` / `ja` / `zh-tw` |
| `--AdviceType` | 可选：`INDEX`（索引）或 `TIERING`（冷热） |

示例：

```bash
aliyun adb DescribeAvailableAdvices --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id> \
  --AdviceDate 20260322 --AdviceType INDEX --PageNumber 1 --PageSize 30 --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills
```

### 5.3 常用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--RegionId` | 地域 ID（凡带 `--DBClusterId` 时本 Skill 要求必传） | — |
| `--DBClusterId` | ADB MySQL 集群 ID（如 `amv-xxx`） | 必填 |
| `--StartTime` | 起始时间（ISO 8601 UTC 或 ms 时间戳，视接口而定） | — |
| `--EndTime` | 结束时间（同上） | — |
| `--QueryCondition` | SQL 过滤条件（JSON），如 `'{"Type":"status","Value":"running"}'` | — |
| `--Lang` | 语言：`zh` / `en` / `ja` / `zh-tw` | `zh` |
| `--Order` | 排序字段（JSON），如 `'[{"Field":"StartTime","Type":"desc"}]'` | — |
| `--PageNumber` | 页码 | `1` |
| `--PageSize` | 每页条数 | `30` |

> **性能指标 Key**：使用 `DescribeDBClusterPerformance` 时通过 `--Key` 指定，常用值包括 `AnalyticDB_CPU`（CPU使用率）、`AnalyticDB_QPS`（每秒查询数）、`AnalyticDB_QueryRT`（查询响应时间）、`AnalyticDB_Connections`（连接数）等。完整列表可通过 `aliyun adb DescribeDBClusterPerformance --help` 查看。

### 5.4 凭证配置

**阿里云 API 凭证**通过 `aliyun configure` 在**本会话之外**配置，CLI 会自动读取。

**凭证状态检查**：

```bash
aliyun configure list
```

若输出中 AccessKeyId 列为空或显示 `<empty>`，说明凭证未配置，应提示用户：
1. 在**本会话之外**通过终端运行 `aliyun configure` 进行配置
2. 或在 shell profile 中配置环境变量
3. 配置完成后返回继续执行

> **🔴 重要规则**：
> - **严禁**在会话中引导用户输入 AK/SK 凭证
> - **严禁**使用 `aliyun configure set --access-key-id` 等显式凭证参数
> - 凭证检查必须是任务的第一步，检查失败时直接报告并终止

支持多种凭证类型：AK、StsToken、RamRoleArn、EcsRamRole 等。详见 [配置凭证文档](https://help.aliyun.com/zh/cli/configure-credentials)。

## 六、RAM Policy

本 Skill 涉及的 RAM 权限列表详见 `references/ram-policies.md`。

> **[MUST] Permission Failure Handling:** 当任何命令或 API 调用在执行过程中因权限错误而失败时，请遵循此流程：
> 1. 阅读 `references/ram-policies.md` 获取本 SKILL 所需的完整权限列表
> 2. 使用 `ram-permission-diagnose` skill 引导用户申请必要的权限
> 3. 暂停并等待用户确认所需权限已授予

## 七、参数确认

> **IMPORTANT: Parameter Confirmation** — 在执行任何命令或 API 调用之前，所有用户可自定义参数（如 RegionId、实例名称、CIDR 块、密码、域名、资源规格等）**必须**与用户确认。**不得**在未经用户明确批准的情况下假设或使用默认值。

| 参数名 | 必填/可选 | 描述 | 默认值 |
|--------|----------|------|--------|
| `RegionId` | 必填 | 阿里云地域 ID | 无（需用户确认） |
| `DBClusterId` | 必填 | ADB MySQL 集群 ID（`am-xxx` 或 `amv-xxx`） | 无（需用户确认） |
| `StartTime` / `EndTime` | 可选 | 时间范围参数 | 最近 1 小时 |

## 八、最佳实践

1. **CLI-First**：优先使用 `aliyun adb` CLI 命令进行诊断
2. **时间校验**：涉及时间范围查询时，必须先获取当前 UTC 时间再计算
3. **命令输出**：每次 API 调用必须在回复开头输出完整命令字符串
4. **错误处理**：集群 ID 不存在时，应引导用户选择正确集群而非直接失败
5. **产品边界**：仅处理 ADB MySQL 集群（ID 前缀 `am-` 或 `amv-`），不混用其他产品 API

## 九、参考链接

| 参考文件 | 内容 |
|----------|------|
| `references/ram-policies.md` | RAM 权限列表 |
| `references/verification-method.md` | 验证方法 |
| `references/cli-installation-guide.md` | Aliyun CLI 安装指南 |
| `references/cluster-info.md` | 集群信息查询详细步骤 |
| `references/slow-query-diagnosis.md` | 慢查询诊断详细步骤 |
| `references/table-modeling-diagnosis.md` | 实例空间诊断流程 |