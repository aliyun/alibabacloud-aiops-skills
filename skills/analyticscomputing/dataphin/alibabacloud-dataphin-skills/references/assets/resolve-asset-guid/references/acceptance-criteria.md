# 验收标准（resolve-asset-guid）

## 0. 交付门槛（全部为硬条件）

- [ ] **开场两个必问已问**：① 资产类型由用户明确回答（**不是**从限定名形态 / 前后缀 / 反查结果推得）；② 该类型的必要信息清单已摊给用户、缺项已逐项索取
- [ ] **已向用户输出段值确认表**，每段标明取值与来源（用户提供 / 接口查得 / 用户确认同源后照抄），且全部为 `✅ 已确认` 后才拼接
- [ ] **无任何一段是“表名相似/同前缀”外推而来**；照抄模板表中段前已由用户确认同数据源同 schema
- [ ] **提问与列候选用业务语言**：直接问“数据源/项目/板块是哪一个”并列名称（数据源附编码），**未用 A/B 标号或 19 位 ID 让用户选**
- [ ] 接口不可用（凭证/权限/网关）时已**告知用户并转为索取段值**，未用推断填补中段
- [ ] Step 0 资产类型已明确（类型 + 必要时 SubType），**未靠猜**；用户描述含糊时已追问
- [ ] Step 1 选路正确：含内部 ID 的类型（`dp_index.` / `biz_index.` / `dp_api.` / `qbi_page_` / `qbi_component_`）**没有**尝试拼接
- [ ] 归属对象与环境（DEV/PROD）已与用户确认，未默认取 PROD、未把项目名当板块名
- [ ] 大小写已归一：板块名 / 项目名 / 数据源 schema 均转小写；表名仅在“区分大小写引擎的物理表”上保留原样
- [ ] Step 3 回读校验已执行且四项全过（存在 / 类型一致 / 名称归属一致 / 字段级列存在）
- [ ] 交付内容含五项：GUID 全文 + **段值确认表** + 资产类型 + 校验证据 + 下游参数用法
- [ ] 有段未确认、或回读未通过时**没有产出 GUID 全文**，而是交确认表 + 缺口说明；因凭证/权限无法回读时已显式标注「未经回读校验」

## 1. 分类型校验要点

| 类型 | 必须核对 |
|---|---|
| `dp_table.` | 第三段 == `BizUnitName` 小写（不是项目名）；回读 `AssetFullName` 的板块段与之一致 |
| 项目内物理对象（引擎前缀） | 前缀取自 `guid-composition-matrix.md` §1.2 对照表（或同项目现有表 GUID），不得一律套 `odps.`；第三段 == `list-projects` 的 `Name` **转小写**（无手工 `_dev`）；表名按该引擎的大小写开关处理；物理视图 / 物化视图与物理表同公式 |
| `stream_table.` / `mirror_table.` / `label_table.` | 确认未误用 `odps.` 或引擎前缀；段式 = 小写项目名 + 小写对象名 |
| `dp_ds_table.`（5 段） | `dataSourceId` 与 `Data.DatasourceId` 一致；schema 与表名**均小写**，schema 取自同数据源已有表 GUID 或接口返回 |
| `dp_ds_table.`（7 段，DataWorks 采集表） | 已识别为**独立特例**并用 7 段公式（未套 5 段普通数据源表）；DataWorks 空间 id / 数据源 id 来自用户提供、照抄同数据源已有表中段或反查，**未靠猜** |
| 字段（COLUMN） | 表 GUID 先独立校验通过；`Columns[]` 中存在同名列（大小写一致） |
| `dp_index.` | 环境段（`dev`/`prod`）与后续接口所用环境一致 |
| `cust_index.` | 由所属字段 GUID 前缀替换得到，且 `AssetFullName` == `<所属表名>.<字段名>` |
| `biz_index.` | 由 `get-biz-metric-by-name` 直取（`BizMetricByNameQuery` 包裹 + `draft` 必填），不自拼 |
| `dp_api.` / `qbi_page_` | 由 `list-catalog-assets` 取；`ApiId` / 页面标识与 GUID 末段互相印证；BI 族注意下划线分隔且 `pageId` 为 UUID |

## 2. 正确模式

- ✅ 命中多条时按板块/项目/数据源 + 环境逐条比对后再选
- ✅ 未上架资产改用 `list-tables`（资产清单），不在 `list-catalog-assets` 上反复重试
- ✅ 只读命令一律带 `--cli-query` 裁剪输出
- ✅ 19 位 ID（`OpTenantId` / `DataSourceId`）按字符串传参
- ✅ 每个 `aliyun` API 命令携带 `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"`（session-id 继承父 skill）

## 3. 错误模式

- ❌ **从名称形态推断资产类型**（看 `LD_xxx.表` 当逻辑表、看 `a.b` 当 schema.表、看 `dim_`/`dws_`/`_tmp` 推类型）
- ❌ 拿反查结果替用户断定“这是哪一类资产”或“你要的就是这条”（命中多条必须列候选让用户选）
- ❌ 拿 19 位 ID / A、B 标号当选项让用户选（用户无法从 ID 判断是哪个数据源）
- ❌ 把「命令返回 `Code: OK` / `Success=true`」当作 GUID 有效（GUID 不存在时接口不报错）
- ❌ 用“表名相似”把另一张表的中段整段搬过来，包装成“照抄模板”
- ❌ 反查与回读都被权限卡死时，仍输出一条看起来很确定的 GUID
- ❌ 逻辑表用项目名拼第三段；MaxCompute 项目名手工加 `_dev`
- ❌ 把项目内对象的前缀一律当成 `odps.`（共 19 个取值；实时元表 = `stream_table.`、镜像表 = `mirror_table.`、标签表 = `label_table.`）
- ❌ 大小写不归一（板块名 / 项目名 / schema / 非区分大小写引擎的表名 都必须转小写）
- ❌ 把 DataWorks 采集表当普通数据源表拼成 5 段（它是独立特例，固定 7 段）
- ❌ 按 `.` 切 `qbi_page_` / `qbi_component_` GUID
- ❌ 把 `$_$VALID` / `$_$INVALID` 后缀的落标/发布对象 ID 当资产 GUID
- ❌ 用恒为 `null` 的 `SumTableGuid` 取所属表 GUID
- ❌ 未校验就把 GUID 交给写类 skill（覆盖写不可自动回滚）
- ❌ 搜不到就换写法反复重试，而不先判断「未上架」还是「元数据未采集」
