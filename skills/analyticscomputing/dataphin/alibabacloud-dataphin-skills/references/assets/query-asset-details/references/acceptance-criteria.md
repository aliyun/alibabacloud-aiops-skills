# 验收标准

## 正确模式

### 1. 产品名 / 命令格式
- 使用 `dataphin-public`（非旧 `dataphin` 二进制）
- 插件模式命令为 kebab-case：`get-catalog-asset-details` / `get-asset-attributes` / `get-table-lineages` / `get-table-column-lineages` / `get-quality-watch-by-object-id` / `list-quality-rules` / `list-quality-rule-tasks`
- Action 名用 CLI 命令的 PascalCase（`ListQualityRules`），**不用 `PagedQuery*` 旧裸名**
- 命令未收录时改走 OpenAPI SDK 兜底（API 版本 `2023-06-30`，RPC 风格），且按 SKILL.md §8 末尾的对照表放对参数位置

### 2. 板块① 属性 / 字段 / 使用说明
- `Success=true`；`Columns[]` 条数与界面一致
- **两个开关都已传 `true`（`IncludeColumns` + `IncludeDetailedAttributes`）**——后者不传时 `ReadCount` / `CollectionCount` / `SimpleNodeInfos` / `AssetTags` / `MaintainUser*` 恒为 `null`
- **术语已对齐界面原文**（查 [`ui-field-mapping.md`](ui-field-mapping.md)）：`SimpleNodeInfos` 报为「**产出任务**」（**不是「调度节点」**）、`ReadCount` 报为「**浏览量**」、`CollectionCount` 报为「**收藏数**」
- **热度/产出任务为 `null` 时已先查开关**：确认 `IncludeDetailedAttributes: true` 已传，未把 `null` 当 0 报出（实测该开关不传时 `ReadCount`/`CollectionCount`/`SimpleNodeInfos` 恒 `null`）
- **字段级四列已逐列输出**：关联标准（`Standards`）/ 数据分类（`ClassifyName`）/ 数据分级（`LevelShortName`）有值就给，质量分（`QualityScore`）给 `-` 并注明无 OpenAPI——**未因为抽查到的列为 `null` 就整列省略**
- `Directories[].DirectoryChain` 存在，按 `Level` 升序，末节点为叶子（其 `DirectoryId` == 外层 `DirectoryId`）
- 空描述已兼容 `null`（`TopicDescription`）与 `""`（`DirectoryDescription`）
- `GetAssetAttributes`：传 `AttributeCodeList` 时仅返回指定属性；不存在 GUID 不报错且不出现在结果中（**须核对返回的 GUID 集**）

### 3. 板块② 数据预览
- 执行前已向用户展示「引擎 / 表 / 完整 SQL / 分区」并取得明确同意（HITL）
- SQL 为纯 `SELECT`，带行数上限，无分号拼接多语句
- 表名为全限定名（`<project|schema>.<table>`）
- 分区表（`IsPartitionTable=true`）已按 `PartitionKey` 钉分区值，且分区值来自 `SHOW PARTITIONS` 实取而非猜测
- LIMIT 方言与引擎匹配（Oracle `ROWNUM` / SQL Server `TOP` / DB2 `FETCH FIRST`）
- `DATABASE_SQL` 已同时传 `--data-source-id`（字符串）与 `--data-source-schema`
- 取结果用 `--sub-task-id 0`；结果为空时已按 `data-preview-sql.md` §7 顺序排查后才下结论

### 4. 板块③ 血缘
- **已先跟用户确认血缘范围：「直接上下游（1 跳）」还是「全链路」**，以及方向（仅上游 / 仅下游 / 双向），**未自己默认**
- 选「全链路」时：已做 **BFS 递归**（非单次调用）、已设深度上限并在输出里告知、已做边/节点去重与环检测、节点过多时已停下来问是否继续
- 选「直接上下游」时：输出里**明确写了是直接（1 跳）上下游**，未暗示/声称是全部血缘
- `--need-upstream` / `--need-downstream` **两个接口都显式传值**，不依赖默认
- 空结果已排除"表血缘默认 false"这一误因后才判定"无血缘"
- 需要排查断链时已开 `--need-not-exist-object true`
- **未去找 `depth` / `level` / `hop` 类入参**（接口根本没有）

### 5. 板块④ 质量概况
- **输出里未出现「监控对象」「watch」「watchId」「watchTaskId」「监控任务」等内部词**；改用「这张表下共配置了 N 条质量规则（生效 M 条）」与「最近一次质量校验」表述
- 未配时输出「**这张表下还没有配置质量规则**」（**不是「未配置监控对象/质量监控」**）
- **已确认自己读的是正确的响应负载键**：`List*` → `PageResult.<XxxList>`；`GetQualityWatchByObjectId` → `QualityWatchInfo`；`GetQualityWatchTask` → `WatchTaskInfo`。**不是 `Data`**
- 字段名以实测为准：`Id` / `Type` / `TableInfo` / `Strength` / `TestRun*` / `ValidateSuccess`，不抬 SDK v1.0 文档的 `watchId` / `table` / `validateResult`
- `WatchType` 与资产 `SubType` 匹配（`TABLE` / `DATASOURCE_TABLE` / `REALTIME_LOGICAL_TABLE` / `INDEX` / `DATASOURCE`）
- `TABLE` 类型直接传资产 GUID 作为 `WatchObjectId`
- 用 `list-quality-watches` 兼底时，已用 `TableInfo.Id` 精确匹配目标 GUID 并核对 `TableInfo.Env`（同名表会有 DEV/PROD 多个 watch），**未取第一条**
- 空结果已先排除“读错负载键”与“`WatchObjectId` 形态错”，才判定为未配质量监控
- `list-quality-rules` 已传 `--watch-id`
- 描述当前质量状况优先用 `GetQualityWatchTask.RuleCountInfo`，逐条明细用 `ValidateSuccess` + `BizDate`，**未用 `TestRun*` 试跑字段**
- 已区分 `Status`（任务是否跑完）与 `ValidateSuccess`（数据是否通过），**未拿 `Status=SUCCESS` 当校验通过**
- 已区分 `RuleCount` / `EnabledRuleCount` / `FinishedRuleCount` 三个不同的分母，汇报时口径明确
- 输出中「平台事实」与「自算通过率」分开呈现，自算项已标注口径（分母、排除项、是否加权、业务日期、分区）
- 已如实告知「平台口径的表级质量分无 OpenAPI，需到界面查看」，**且未拿 `Columns[].QualityScore` 充当字段级质量分**（实测恒为 null）

### 6. 参数确认
- 所有用户自定义参数（租户、GUID、板块范围、**血缘范围与方向**、预览行数与分区）执行前需用户确认
- 用户未点名要全部板块时，先问要哪几块（预览耗资源、血缘可能巨大）
- 不硬编码 tenant-id / GUID / DataSourceId / ProjectId

### 7. 资产类型分流（5 类资产）
- **已先根据 `AssetType` + `SubType` 划定板块范围**，未对不支持的板块硬调接口
- 不支持的板块已直接说明「该资产类型无此板块」（业务指标无预览/血缘/质量；API 与仪表板只有属性 + 专属板块）

**技术指标（INDEX）**
- 已从 `AssetFullName` 拆出「表名.字段名」并拼出表 GUID（`dp_index` 用 BizUnitName，`cust_index` 用 DatasourceId+schema）
- **已回读校验两项**：表 GUID 返回非空 + `Columns[]` 中存在该字段
- **未使用 `SumTableGuid`**（实测恒为 null）
- 字段血缘已按 `Input/OutputColumnName == 字段名` 客户端过滤，**多条入向血缘已全部列出**
- 字段质量已按 `ValidateObject.Type == "COLUMN" && ValidateObject.Name == 字段名` 过滤
- 所属表未配 watch 时已直接输出「所属表未配置质量监控」，未继续空转

**业务指标（BIZ_INDEX）**
- `GetBizMetricByName` 已用 **`BizMetricByNameQuery`** 包裹且 **传了 `draft`**
- 已输出 `MetricDefinition`（口径）、`RelatedBizMetrics[]`（含 `RelationType` 与 `ListStatus`）、`AssociatedTechMetrics[]`
- 使用说明**优先取 `OperateInstructionContent`（纯文本）**，未去解析富文本 `Instruction`

**数据服务 API**
- `Id` 取自资产详情的 `ApiId`，未自行猜测
- 已输出四块：基本信息 / `RequestParamList[]` + `PublicParamList[]` / `ResponseParamList[]` + `ResultSample` / 运行配置
- **已如实告知错误码 OpenAPI 未提供**，未用 HTTP 状态码或自编错误码充数
- `Sql` 默认只汇总，未经用户请求不贴全文

**仪表板（PAGE）**
- 已传 `IncludeColumns: true`，从 `Columns[]` 取图表列表
- 已校验 `len(Columns) == ChartCount`
- **已说明图表信息只到名称粒度**（无类型/数据集/字段），未把 `DataType`/`Standards` 等恒 null 字段当有效信息

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant / GUID / DataSourceId
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 凭 `Success=true` 断定 GUID 有效（不存在也返回 true）
- ❌ 凭 `Code=OK` + `Data=null` 断定"该资产没配质量监控"或"未授权"（**先确认负载键是不是 `PageResult` / 具名键**）
- ❌ 凭 SDK v1.0 文档猜字段名（`watchId` / `table` / `validateResult` 实际不存在）
- ❌ 同名表直接取 `list-quality-watches` 的第一条 watch
- ❌ 拿 `Status=SUCCESS` 当成校验通过
- ❌ 拿 `Columns[].QualityScore` 当字段级质量分（实测死字段）
- ❌ **拿字段英文名直译成中文标签**（`SimpleNodeInfos` → 「调度节点」、`ReadCount` → 「阅读数」、`CollectionCount` → 「收藏次数」）
- ❌ **漏传 `IncludeDetailedAttributes` 拿到 `null` 后当 0 汇报**
- ❌ **把 `Standards` / `ClassifyName` / `LevelShortName` 跟 `QualityScore` 一起砍掉不输出**
- ❌ **拿一次血缘调用（1 跳）的结果当「全部上下游」汇报**，或未先问用户要直接还是全链路
- ❌ **质量输出透出「监控对象」「watchId」等内部词**
- ❌ 单次 `GuidList` 超 50 条
- ❌ 把自算规则通过率当作平台质量分报给用户
- ❌ 用试跑结果（`TestRunRuleValidateResult`）代表当前质量状况
- ❌ 表血缘不传 `--need-upstream/--need-downstream` 就断言"无血缘"
- ❌ 未经用户确认直接提交预览查询
- ❌ 预览 SQL 含非 SELECT 语句，或分区表不带分区谓词
- ❌ 19 位大整数 ID 用数值类型传（尾数截断）
- ❌ 默认拉取 `get-ad-hoc-task-log` 全文
- ❌ 不分资产类型就四板块全跑（业务指标/API/仪表板 硬调预览与血缘）
- ❌ 技术指标未回读校验就直接用拼出的表 GUID，或依赖 `SumTableGuid`
- ❌ 技术指标把**全表**血缘/全表规则当成该指标的（必须过滤到对应字段）
- ❌ `GetBizMetricByName` 顶层平铺传参或漏传 `draft`
- ❌ 把仪表板 `Columns[]` 的 `DataType`/`Standards`/`QualityScore` 当成有效图表信息
