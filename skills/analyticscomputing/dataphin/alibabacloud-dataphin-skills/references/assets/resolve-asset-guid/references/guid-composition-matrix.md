# 资产 GUID 构成矩阵（按类型拼接规则 · 段语义 · 实测样例）

> 证据标记：`[研发规则]` = 研发给出的服务端枚举 / 拼接规则（权威口径）；`[规则确认]` = 业务方明确指定且有实测样本印证的规则；`[实测]` = POC V6.3 真机返回值；`[autotest]` = `dataphin-ai-autotest` 用例模板 / healing 经验取证；`[待实测]` = 有规则但尚无真机样本印证，**必须回读校验后才可交付**。

## 0.1 大小写规范（最容易拼错、且表面上看不出来）

| 部位 | 规则 | 依据 |
|---|---|---|
| 逻辑表（`dp_table.`）的板块名与表名 | **全部转小写** | `[研发规则]` |
| 物理表类（引擎前缀）的**项目名** | **恒转小写** | `[研发规则]` + `[实测]`：项目 `Nonstructured_data` 在 GUID 里为 `nonstructured_data` |
| 物理表类的**表名** | 看引擎是否区分大小写：不区分 → **转小写**；区分 → **原样保留**（逐引擎见 §1.2 表） | `[研发规则]` |
| 数据源表（`dp_ds_table.`）的 schema 与表名 | **全部转小写** | `[研发规则]` |
| 指标 / API / 报表类 | 末段是数字或 UUID，不涉大小写（`dp_index.` 的环境段固定小写 `dev`/`prod`） | `[研发规则]` + `[实测]` |

> ★ **“区分大小写的引擎”只影响表名，不影响项目名** —— 项目名无论何种引擎都转小写。
> 当前 POC 实测样本全落在**不区分大小写**的引擎上（odps / dp_table / dp_ds_table），因此“区分大小写引擎保留原样表名”这一条属 `[待实测]`：首次遇到 Hologres / StarRocks / Doris / ADB for PG / SelectDB / OushuDB 表时，**先拼原样表名回读，不中再试小写，并把结果回填到 §5 样本表**。

## 0. 第一步永远是分两类

| 类别 | 判据 | 处理路径 |
|---|---|---|
| **A 可拼接（结构型）** | GUID 各段都是「人能说出来的名字」：租户 ID、板块名、项目名、数据源 ID、schema、表名、字段名 | 按 §1 公式拼 → **必须回读校验** |
| **B 必须查（含内部 ID）** | GUID 含库表自增/逻辑 ID、UUID（`logicIndexId` / `logicId` / `apiId` / `componentUuid`） | **不要试图拼**，直接走搜索接口取返回里的 `Guid` |

| 资产类型 | GUID 前缀 | `AssetType` | 类别 |
|---|---|---|---|
| Dataphin 逻辑表（维度/事实/汇总逻辑表、逻辑表视图） | `dp_table.` | `TABLE` | **A** |
| Dataphin 项目内物理表 / 物理视图 / 物化视图 | **引擎前缀**（20 种，见 §1.2 表；MaxCompute = `odps.`） | `TABLE` | **A** |
| Dataphin 实时元表 | `stream_table.` | `TABLE` | **A** |
| Dataphin 镜像表 | `mirror_table.` | `TABLE` | **A** |
| Dataphin 标签表 | `label_table.` | `TABLE` | **A** |
| 数据源表（单层 schema、全域表） | `dp_ds_table.`（5 段） | `TABLE` | **A** |
| **DataWorks 采集表**（数据源表的独立特例） | `dp_ds_table.`（**7 段**，见 §1.3.1） | `TABLE` | A（公式固定；两个中段是 DataWorks 内部 ID，拿不到时转反查） |
| 字段（列） | 表 GUID + `.字段名` | `COLUMN` | **A** |
| 技术指标 · 自定义指标 | `cust_index.` | `INDEX` / SubType `CUSTOM_INDEX` | A（由所属字段 GUID 派生） |
| 技术指标 · 规范建模（派生）指标 | `dp_index.` | `INDEX` / SubType `INDEX` | **B** |
| 业务指标 | `biz_index.` | `BIZ_INDEX` | **B** |
| 数据服务 API | `dp_api.` | `API` | **B** |
| 仪表板 / 图表 | `qbi_page_` / `qbi_component_` | `PAGE` / `COMPONENT` | **B** |

> ★ **不要把“前缀”等同于“资产类型”**：`TABLE` 这一个 `AssetType` 下就有 20+ 种前缀（逻辑表 / 15 种计算引擎 / 实时元表 / 镜像表 / 标签表 / 数据源表两种段式）。先分“表是哪一种表、跑在哪个引擎上”，再选公式。

---

## 1. 逐类型公式

### 1.1 Dataphin 逻辑表 → `dp_table.`

```
dp_table.<tenantId>.<bizUnitName 小写>.<tableName 小写>
```

- 实测样例：`dp_table.300023201.ld_fashion.dim_lk_cus` `[实测]`
  —— 该表 `BizUnitName = LD_Fashion`（→ 段取 `ld_fashion`）、`ProjectName = fashion_cdm`。
- 其它实测样例：`dp_table.300023201.ld_mfg_fin.dim_basic_item`、`dp_table.300023201.ld_train.fct_li_claim_settle_di`
- ★ **DEV 环境的板块段也带 `_dev`**（实测同一张表）：PROD `dp_table.300023201.ld_fashion.dim_lk_cus` / DEV `dp_table.300023201.ld_fashion_dev.dim_lk_cus`（`BizUnitName` 在 DEV 返回的就是 `LD_Fashion_dev`）`[实测]`。
- **板块名与表名均转小写** `[研发规则]`（逻辑表对应枚举 `LOGICAL("logical", "dp_table", false)`，`false` = 不区分大小写）。

> ★ **第三段是「数据板块名」，不是项目名**。逻辑表挂在数据板块（BizUnit）下，同一板块的表可能分布在多个项目里；拿项目名去拼是本类型最高频错误。板块名在界面上常见形如 `LD_Fashion`，GUID 里**统一小写**。

### 1.2 Dataphin 项目内对象 → `<引擎前缀>.<tenantId>.<projectName 小写>.<对象名>`

公式（`[研发规则]`）：**前缀 + tenantId + 小写项目名 + 表名**，表名大小写按下表 `区分大小写` 列处理。物理表 / 物理视图 / 物化视图 / 实时元表 / 镜像表 / 标签表 **共用这一公式，只换前缀**。

#### 引擎 → 前缀 → 大小写对照表（服务端枚举全量，`[研发规则]`）

| 引擎 / 对象类型 | GUID 前缀 | 表名区分大小写 | 表名处理 |
|---|---|---|---|
| 逻辑表（logical） | `dp_table` | 否 | 转小写 |
| MaxCompute | `odps` | 否 | 转小写 |
| TDH Hadoop | `tdh_hadoop` | 否 | 转小写 |
| Hadoop | `hadoop` | 否 | 转小写 |
| AWS EMR | `aws_emr` | 否 | 转小写 |
| ADB for PG / AnalyticDB for PG | `adb_for_pg` | **是** | **原样** |
| StarRocks | `starrocks` | **是** | **原样** |
| Hologres | `hologres` | **是** | **原样** |
| ArgoDB | `argodb` | 否 | 转小写 |
| Lindorm | `lindorm_engine` | 否 | 转小写 |
| GaussDB | `gaussdb` | 否 | 转小写 |
| Databricks | `databricks` | 否 | 转小写 |
| SelectDB | `selectdb` | **是** | **原样** |
| Doris | `doris` | **是** | **原样** |
| OushuDB | `oushudb` | **是** | **原样** |
| EMR Spark Serverless | `emr_spark_serverless` | 否 | 转小写 |
| 实时元表（stream） | `stream_table` | 否 | 转小写 |
| 镜像表（mirror） | `mirror_table` | 否 | 转小写 |
| 标签表（label） | `label_table` | 否 | 转小写 |

> `ADB_FOR_PG` 与 `ANALYTICDB_FOR_PG` 两个枚举值**共用同一前缀** `adb_for_pg`。

#### 实测样例 `[实测]`

| 对象类型 | 实测样例 |
|---|---|
| 物理表（MaxCompute） | `odps.300023201.train_dev.ads_ec_order_yearly_trend`、`odps.300023201.ods_cw_dev.zs_external_table_48` |
| 物理视图 | `odps.300023201.demo_log_cdm.qd_feature_v_max_tv` |
| 物化视图 | `odps.300023201.train_zhaoyue_dev.autotest_mv_perm_20260720225925_w184` |
| 实时元表 | `stream_table.300023201.train_dev.holo_events`、`stream_table.300023201.unstructured_data_knowledge_base.meta_table_noauth` |
| 镜像表 | `mirror_table.300023201.vvp_poc.buyer_summary_mirror` |

四条关键结论：

1. **前缀由项目的计算引擎决定，不是固定 `odps`**。先弄清目标项目跑在哪个引擎上，再查上表取前缀；不确定时用 `list-tables --catalog <项目名>` 取任意一张表的 `Guid` 照抄前缀。
2. **表 / 物理视图 / 物化视图 同构**：三者共用引擎前缀与同一公式，不需要区分。
3. **实时元表 / 镜像表 / 标签表是枚举里的独立项**（`stream_table` / `mirror_table` / `label_table`），段式与物理表完全一致。拿 `odps.` 去拼必然查不到。
4. **项目名恒转小写（已实测：`Nonstructured_data` → GUID 段 `nonstructured_data`）；`_dev` 后缀要“查”不要“拼”**：
   DEV_PROD 模式项目在 DEV 侧的**实名**就带 `_dev`（实测同一张表：PROD `odps.300023201.fashion_cdm.dim_marriott_customer_tmp` / DEV `odps.300023201.fashion_cdm_dev.dim_marriott_customer_tmp`），
   正确做法是**取目标环境下 `ListProjects` / `ListTables` 返回的 `Name` 再转小写**；拿 PROD 名自己补 `_dev` 是错的 —— BASIC 模式项目根本没有 DEV 变体（实测 `Nonstructured_data`，`ModeEnum=BASIC`），强行补后缀必然查不到 `[实测]` `[autotest]`。

> **同一业务下逻辑表用板块名、物理表用项目名**（实测对照）：`dp_table.300023201.ld_train.fct_li_claim_settle_di` 与 `odps.300023201.train_dev.ads_ec_order_yearly_trend` 同属 train 业务，第三段一个是板块 `ld_train`、一个是项目 `train_dev`，**不能互代**。

### 1.3 数据源表 → `dp_ds_table.`

```
dp_ds_table.<tenantId>.<dataSourceId>.<逻辑 schema 小写>.<tableName 小写>
```

- **段均转小写** `[研发规则]`（不看数据源本身是否区分大小写，与 §1.2 的引擎大小写开关无关）。
- 实测样例 `[实测]`：
  - MySQL：`dp_ds_table.300023201.7375744037241779648.dataphin03.site_access`
  - Doris：`dp_ds_table.300023201.7429119042721440256.public.doris_customers`
  - StarRocks：`dp_ds_table.300023201.7311626611751680256.load_test.orders100`
  - 其它：`dp_ds_table.300023201.7271828728219470528.default.ods_orders`
- 段义：`dataSourceId` = Dataphin 数据源 ID（19 位）；`schema` = 数据源侧 schema / 库名（MySQL 即库名，PG 类常为 `public`）。
- ★ **`dataSourceId` 分环境**：同一数据源在 DEV / PROD 各有独立 ID（实测 `mysql_dlink_1010` → PROD `7375744037241779648` / DEV `7375744037594101184`），所以**环境选错等于 GUID 错** `[实测]`。
- ★ **“库名+表名”不唯一**：实测 `dataphin03.store_sales_detail` 同时挂在两个数据源（`7321185713616091392` / `7375744037241779648`）下，定位时必须指定数据源 `[实测]`。

> 反向也成立：拿到一个 `dp_ds_table.` GUID 时，`DatasourceId` 与 schema 直接躺在 GUID 里，与 `Data.DatasourceId` / `AssetFullName` 一致 `[实测]`。

### 1.3.1 DataWorks 采集表 → `dp_ds_table.` 的 7 段特例（独立类型，不按普通数据源表处理）

```
dp_ds_table.<tenantId>.<dataSourceId>.<DataWorks 空间 id>.<DataWorks 数据源 id>.<逻辑 Schema>.<tableName>
```

★ **DataWorks 采集表是数据源表里的特殊存在，段式固定为 7 段**，与 §1.3 的 5 段普通数据源表**不通用** —— 识别出是 DataWorks 采集表就直接用本段公式，不要套 §1.3。`[规则确认]`

- 实测样例 `[实测]`：`dp_ds_table.300023201.7474436468417527616.1284283.982048.system.all_type`
  （同数据源下另有 `….1284283.982048.system.orders` / `….system.liyi_orders` 等，中段稳定）
- 段义：`1284283` = DataWorks 空间 id；`982048` = 该空间内 DataWorks 侧数据源 id；`system` = 逻辑 Schema。
- **判定特征**：`dp_ds_table.` 开头、段数 > 5，且 `dataSourceId` 后紧跟两个纯数字段。

> **段值来源（公式确定，但两个中段取不到时需绕）**：`DataWorks 空间 id` 与 `DataWorks 数据源 id` 是 DataWorks 侧的内部 ID，Dataphin 界面与 OpenAPI 都拿不到。优先级：① 向用户索取这两个 ID → 按公式拼；② **用户确认目标表与模板表同数据源同 schema 后**，照抄其中段；③ 两者都没有 → 走 §3 反查（`list-tables` 取真实 `Guid`）。
>
> ★ **照抄有前提，不是默认动作**：“表名相似”（如 `all_type` 与 `all_type0123`）**不构成同源证据**。未经用户确认就把另一张表的中段搬过来，等于编造了一个可复制的错误 GUID（实测样本池 24 张表里就有 6 个数据源、5 种 schema 路径）。

### 1.4 字段（列） → 表 GUID + `.字段名`

```
<表 GUID>.<columnName>
```

- 实测样例：`dp_table.300023201.ld_fashion.dim_employee.employee_id`、`dp_table.300023201.ld_dummy.dws_guoshou_customer2.order_cnt_cm` `[实测]`
- 字段名**按 `get-table-columns` 返回原样**取，不要自行改大小写。
- 表 GUID 必须先自校验通过，再追加字段名；字段是否存在用表详情的 `Columns[]`（`IncludeColumns: true`）核对。

### 1.5 技术指标 · 派生指标 → `dp_index.`（**必须查**）

```
dp_index.<tenantId>.<dev|prod>.<logicIndexId>
```

- 实测样例：`dp_index.300023201.prod.82746513` `[实测]`；另 `dp_index.300162425.prod.144661` `[autotest]`
- 公式口径：`dp_index + tenantId + dev|prod + indexId` `[研发规则]`
- `logicIndexId` 是内部逻辑 ID，无从拼装 → 用 `list-catalog-assets --asset-type INDEX` 搜。
- ★ **第三段是环境段**（`dev` / `prod`，小写）：同一指标 DEV / PROD 各一条 GUID。autotest 真实踩坑：搜索命中的是 DEV 端 GUID，而下游详情/血缘接口按 PROD 查 → 恒返回 `data: null` `[autotest]`。取到 GUID 后，后续所有接口的环境必须与 GUID 的环境段一致。

### 1.6 技术指标 · 自定义指标 → `cust_index.`（由字段 GUID 派生）

```
cust_index.<所属字段 GUID 去掉其前缀后的全部内容>
= cust_index.<tenantId>.<项目/板块/数据源段…>.<tableName>.<columnName>
```

派生规则（autotest 生产用法）：把该字段 GUID 的前缀替换成 `cust_index.` `[autotest]`

```
colGuid.replace(/^(odps|dp_table|dp_ds_table)\./, 'cust_index.')
```

- 实测样例：`cust_index.300023201.ranzhou_test_project.lfs_tab10_03.id` `[实测]`
  —— 即字段 GUID `odps.300023201.ranzhou_test_project.lfs_tab10_03.id` 把前缀换成 `cust_index.`，**逐段对得上**，前缀替换规则已实测成立。
- 判定归属：自定义指标的 `AssetFullName` = `<所属表名>.<字段名>`；`cust_index.` GUID 中段自带项目（或板块 / datasourceId+schema）`[实测]`

### 1.7 业务指标 → `biz_index.`（**必须查**）

```
biz_index.<tenantId>.<logicId>
```

- 实测样例：`biz_index.300023201.9477256`、`biz_index.300023201.9305017` `[实测]`
- `logicId` 为内部 ID → 用 `get-biz-metric-by-name` 按指标英文名直取 `Data.Guid`。
- 该命令两个契约坑 `[实测]`：业务参数必须包在 `BizMetricByNameQuery` 里；`draft` **必填**（`false` 已发布态 / `true` 草稿态）。

### 1.8 数据服务 API → `dp_api.`（**必须查**）

```
dp_api.<tenantId>.<apiId>
```

- 实测样例：`dp_api.300023201.10383` `[实测]`；公式口径 `dp_api + tenantId + apiId` `[研发规则]`
- 末段是 API 的数字 ID（非 19 位 snowflake，实测为短数字），拿不到就只能查。
- 取法：`list-catalog-assets --asset-type API`；拿到详情后 `ApiId` 可与 GUID 末段互相印证。

### 1.9 仪表板 / 图表 → `qbi_page_` / `qbi_component_`（**必须查**）

```
qbi_page_<tenantId>_<BI 数据源 id>_<pageId（UUID）>
qbi_component_<tenantId>_<BI 数据源 id>_<pageId>_<componentUuid>
```

- 实测样例：`qbi_page_300023201_7321528197764389376_498f84a6-9beb-4aab-a511-d20e862b8f9b` `[实测]`
- 公式口径：`qbi_page + tenantId + 数据源id + 报表id`，**报表类用下划线分隔，其余所有类型都用点分隔** `[研发规则]`
- ★ 按点号切段会把这类 GUID 切错；而 `报表id` **本身是带连字符的 UUID**，按 `_` 切也切不出它的内部结构。
- 取法：仪表板走 `list-catalog-assets --asset-type PAGE`；图表 GUID 只能从仪表板详情的 `Columns[]` 里取（`IncludeColumns: true`，图表列表复用了 `Columns` 字段）`[实测]`。图表**不可枚举**（`list-catalog-assets --asset-type COMPONENT` 返 `TotalCount=0`）`[实测]`。

---

## 2. 通用段义速查

| 段 | 取值 | 来源命令 | 注意 |
|---|---|---|---|
| `tenantId` | 数字租户 ID | 会话已有的 `OpTenantId` | 19 位 snowflake 一律**字符串**传参；GUID 里原样拼 |
| 前缀（项目内对象） | 由**项目计算引擎**或对象类型定（共 19 个取值） | 查 §1.2 对照表；不确定时照抄同项目任意一张表的 `Guid`（`list-tables`） | 注意 `stream_table` / `mirror_table` / `label_table` 也在同一枚举里 |
| `bizUnitName` | 数据板块名 | `list-biz-units` | **转小写**（`LD_Fashion` → `ld_fashion`） |
| `projectName` | 项目名 | `list-projects`（`--mode` 事实必填，`BASIC` / `DEV_PROD` 两个不交集结果集各查一次） | **恒转小写**；DEV 项目名本身就带 `_dev`，不要手工加 |
| `dataSourceId` | 数据源 ID（19 位） | `list-data-source-with-config`（`--page` 必传） | 字符串；GUID 里原样拼 |
| `schema` | 数据源侧逻辑 schema / 库名 | 已有 `dp_ds_table.` GUID 时可直接从中段取；否则从 `list-tables` 命中项的 `Guid` 反推 | **转小写**；MySQL 即库名，PG 类常为 `public` |
| DataWorks 中段 | 空间 id + DataWorks 侧数据源 id + 逻辑 Schema | **无 Dataphin 接口可取** → 照抄同数据源已有表 GUID 或直接反查 | 判定特征：`dp_ds_table.` 且段数 > 5 |
| `env` 段 | `dev` / `prod`（仅 `dp_index.`） | 搜索命中项自带 | 固定小写；与后续接口环境保持一致 |
| `tableName` | 表名 / 对象名 | `list-tables` / `get-table-columns` | 物理表类按 §1.2 引擎开关决定小写或原样；逻辑表 / 数据源表均转小写 |
| `columnName` | 字段名 | `get-table-columns` | 跟随所属表 GUID 的大小写口径，不确定时两种写法各回读一次 |

---

## 3. 反查（拼不出 / 校验不过时的权威路径）

| 目标 | 命令 | 覆盖范围 |
|---|---|---|
| 表（含未上架） | `list-tables --catalog <项目名或数据板块名> --keyword <表名>` | **资产清单**全量（含未上架）；`--catalog` **必填**，不填报 400 `MissingCatalog` `[实测]` |
| 任意类型（仅已上架） | `list-catalog-assets --asset-type TABLE\|INDEX\|BIZ_INDEX\|API\|PAGE --query-mode EXACT_MATCH\|ASSET_SEARCH` | **资产目录已上架**资产；未上架资产搜不到 `[实测]` |
| 业务指标 | `get-biz-metric-by-name --biz-metric-name <名> --draft false` | 直接返回 `Data.Guid` |
| 图表 | `get-catalog-asset-details --guid <仪表板 GUID> --include-columns` | `Columns[].Guid` 即图表 GUID |

> 反查命中多条时（同名表 DEV/PROD 各一条、`_org` 后缀表另算 `[实测]`），**必须按板块/项目/数据源/环境逐条比对后再选**，不能取第一条。

---

## 4. 校验规则与已知坑

### 4.0 每一段都得有来源，且经用户确认

拼接前必须以表单 / 问答形式与用户逐段确认取值（表单模板见 [`segment-resolution.md`](segment-resolution.md) §0）。段值来源只能是：**用户提供** / **接口查得** / **用户确认同源后照抄**。

四条绝对禁止：**禁止从名称形态推断资产类型**（类型一律直接问用户）；禁止用表名相似外推段值；禁止把照抄当默认路径；任何一段未确认时禁止输出 GUID 全文。

> 实测反例：`dws_ai_ready_insight` 同时存在于 MaxCompute 项目与 Doris 数据源；`load_test.orders` 同时存在于两个 StarRocks 数据源（`7311626611751680256` “数据库sql测试” / `7341324071512086400` “数据服务API行级权限_数据源”）。光看限定名既定不了类型、也定不了归属。

### 4.1 GUID 错了不会报错（最危险的一条）

- `GetCatalogAssetDetails` 查不存在的 GUID：**不报错**，只是负载为空 `[实测]`
- `GetAssetAttributes` 查不存在的 GUID：`Success=true` 且结果里**不含**该 GUID，不报错 `[实测]`

→ 所以「命令成功返回」不能作为 GUID 正确的判据。判据必须是：**返回体里真的有这个资产，且 `AssetName` / `AssetFullName` / `AssetType` 与用户描述一致**。

### 4.2 交给写类 skill 前必须校验

未校验的 GUID 一旦流入写类 skill（如 `manage-asset-attributes` 的覆盖写属性、`manage-standard-mapping` 建映射），错误不会在写入时暴露，只会表现为「写了但界面上看不到」，且覆盖写不可自动回滚。

### 4.3 其它坑

| 坑 | 说明 |
|---|---|
| 用“表名相似”外推段值 | 名字相近不是同数据源 / 同空间 / 同 schema 的证据；每段必须逐段确认（§4.0） |
| 反查不可用时仍然“先拼一个” | 凭证/权限受限时拼与查会同时失效，应转为向用户索取段值，交付时标注「未经回读校验」 |
| 默认物理表前缀就是 `odps.` | `odps` 只是 **MaxCompute** 的前缀，共 19 个取值（见 §1.2）；Hologres = `hologres`、StarRocks = `starrocks`、Doris = `doris`… `[研发规则]` |
| 拿 `odps.` 拼实时元表 / 镜像表 / 标签表 | 三者在同一枚举里有独立前缀 `stream_table` / `mirror_table` / `label_table` `[研发规则]` |
| 大小写不归一 | 逻辑表（板块+表名）、数据源表（schema+表名）、**所有引擎的项目名** 均转小写；只有**区分大小写引擎的表名**保留原样 `[研发规则]` |
| 假定 `dp_ds_table.` 永远 5 段 | DataWorks 采集表是独立特例，固定 7 段（多出 DataWorks 空间 id + DataWorks 数据源 id），不能套普通数据源表公式 `[规则确认]` `[实测]` |
| 报表类按点号切段 | 只有报表（`qbi_page_` / `qbi_component_`）用下划线，其余全部用点 `[研发规则]` |
| `$_$VALID` / `$_$INVALID` 后缀 | 这是**落标映射 / 发布对象的对象 ID**（如 `dp_table.300875554.ld_biz_export.dim_dim04$_$VALID`），**不是资产 GUID**，不要拿去查资产详情 `[autotest]` |
| `SumTableGuid` | 技术指标上实测恒为 `null`，不能用它拿所属表 GUID `[实测]` |
| DEV / PROD 双份 | 同名表在 DEV / PROD 各有独立资产与 GUID；带 `_org` 后缀的表是另一个资产 `[实测]` |
| 大整数 ID | `tenantId` / `dataSourceId` 等 19 位 ID 在 JSON / 命令行里一律**字符串**，避免精度丢失 |
| 未采集的外部数据源表 | 元数据未采集时 `list-tables` / `get-table-columns` 查不到，也就不存在资产 GUID —— 应先确认元数据采集已完成，而不是继续换写法拼 |

---

## 5. 实测样本对照表（POC，租户 300023201）

下表样本均为真机取出并逐段对照过公式。**遇到新类型先比对本表，不要凭“类型相似”外推前缀**。

| # | 类型 | 实测 GUID | 对应公式 |
|---|---|---|---|
| 1 | 维度逻辑表 | `dp_table.300023201.ld_fashion.dim_employee` | §1.1 |
| 2 | 汇总逻辑表 | `dp_table.300023201.ld_fashion.dws_channel_type_df` | §1.1 |
| 3 | 事实逻辑表 | `dp_table.300023201.ld_train.fct_li_claim_settle_di` | §1.1 |
| 4 | MySQL 数据源表 | `dp_ds_table.300023201.7375744037241779648.dataphin03.site_access` | §1.3 |
| 5 | 物理表 | `odps.300023201.train_dev.ads_ec_order_yearly_trend`、`odps.300023201.ods_cw_dev.zs_external_table_48` | §1.2 |
| 6 | 实时元表 | `stream_table.300023201.unstructured_data_knowledge_base.meta_table_noauth`、`stream_table.300023201.train_dev.holo_events` | §1.2 |
| 7 | 物理视图 | `odps.300023201.demo_log_cdm.qd_feature_v_max_tv` | §1.2 |
| 8 | 物化视图 | `odps.300023201.train_zhaoyue_dev.autotest_mv_perm_20260720225925_w184` | §1.2 |
| 9 | 镜像表 | `mirror_table.300023201.vvp_poc.buyer_summary_mirror` | §1.2 |
| 10 | DataWorks 采集表（7 段特例） | `dp_ds_table.300023201.7474436468417527616.1284283.982048.system.all_type` | §1.3.1 |
| 11 | 业务指标 | `biz_index.300023201.9477256` | §1.7 |
| 12 | 自定义指标 | `cust_index.300023201.ranzhou_test_project.lfs_tab10_03.id` | §1.6 |
| 13 | 规范建模指标 | `dp_index.300023201.prod.82746513` | §1.5 |
| 14 | 数据服务 API | `dp_api.300023201.10383` | §1.8 |
| 15 | 仪表板 | `qbi_page_300023201_7321528197764389376_498f84a6-9beb-4aab-a511-d20e862b8f9b` | §1.9 |
| 16 | 物理表（项目名含大写，验证小写规则） | `odps.300023201.nonstructured_data.dws_ai_ready_insight`（项目原名 `Nonstructured_data`，BASIC 模式） | §1.2 |
| 17 | MySQL 数据源表（验证 dsId 分环境） | PROD `dp_ds_table.300023201.7375744037241779648.dataphin03.store_sales_detail` / DEV `….7375744037594101184.…` | §1.3 |
| 18 | 物理表（DEV_PROD 模式双环境对照） | PROD `odps.300023201.fashion_cdm.dim_marriott_customer_tmp` / DEV `odps.300023201.fashion_cdm_dev.dim_marriott_customer_tmp` | §1.2 |
| 19 | 逻辑表（DEV 板块段带 `_dev`） | PROD `dp_table.300023201.ld_fashion.dim_lk_cus` / DEV `dp_table.300023201.ld_fashion_dev.dim_lk_cus` | §1.1 |
| 20 | 数据源表（同 schema 同表名跳两个数据源，定位必须用户选） | `dp_ds_table.300023201.7311626611751680256.load_test.orders` 与 `dp_ds_table.300023201.7341324071512086400.load_test.orders` | §1.3 |
| 21 | 逻辑表（板块名与项目名无字面关联） | `dp_table.300023201.ld_sfc_train.dim_investor`（板块 `LD_SFC_train`，**所属项目却是 `test_set_sql`**） | §1.1 |
| 22 | 数据源表（**仅 DEV 存在**，PROD 无；反证环境不得默认 PROD） | `dp_ds_table.300023201.7453104072938256768.performance_schema.innodb_redo_log_files`（数据源 `zh_bank_source`／编码 `ds_zh_bank_source_dev`，MySQL 系统库已被采集 112 张表） | §1.3 |
