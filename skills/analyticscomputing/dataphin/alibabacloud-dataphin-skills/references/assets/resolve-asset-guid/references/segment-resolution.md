# 段值解析手册（每一段从哪个接口拿）

> 目标：把用户说得出的业务信息（"fashion 板块的 dim_lk_cus 表"）补齐成 GUID 所需的全部段值。所有命令均为**只读**。
> 通用变量：`OP_TENANT_ID`（19 位字符串）、`UA="AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/$SESSION_ID skill-version/$SKILL_VERSION"`。
> 独立部署环境下每条命令追加 `--profile dataphin-standalone --skip-secure-verify --op-tenant-id "$OP_TENANT_ID"`（父 skill §4.1 规则）。

## 0. 段值确认表模板（拼接前必须先跟用户逐段核一遍）

按资产类型选一张表，逐段填“取值 / 来源 / 状态”后交用户确认。来源只能是三种之一：**用户提供** / **接口查得（附命令）** / **用户确认同源后照抄**。写不出来源的段，状态就是 `⚠️ 待确认`，不得自行填值。

**逻辑表**：`tenantId` / `bizUnitName`（小写）/ `tableName`（小写）/ 环境 DEV或PROD

**项目内对象（物理表 / 视图 / 物化视图 / 实时元表 / 镜像表 / 标签表）**：`引擎前缀`（由项目计算引擎定）/ `tenantId` / `projectName`（小写）/ `对象名`（大小写看引擎开关）/ 环境

**普通数据源表**：`tenantId` / `dataSourceId` / `逻辑 schema`（小写）/ `tableName`（小写）

**DataWorks 采集表**：`tenantId` / `dataSourceId` / `DataWorks 空间 id` / `DataWorks 数据源 id` / `逻辑 Schema` / `tableName`
—— 其中两个 DataWorks ID **Dataphin 侧无接口可取**，只能用户提供、或在用户确认“与模板表同数据源同 schema”后照抄。

**字段**：`所属表 GUID`（先独立确认+校验）/ `columnName`

**指标 / API / 仪表板**：不拼，直接反查（见 §6）；需确认的只有“名称 + 类型 + 环境”用于搜索定位。

问答话术（可直接用）：

> 拼这个 GUID 需要 N 个段，我目前确定的是…，还差…。你希望怎么补？
> ① 你直接告诉我这几个值；② 我调接口查出候选值，你核对；③ 你先给关键归属（如数据源名），剩下我查。

## 1. 优先问用户，别默认盲搜

进入解析前先把已知信息落到下面这张表上，**缺哪一格补哪一格**；用户能直接说出板块/项目/数据源名时，不要再去枚举全量。

| 资产类型 | 必需段 | 用户通常能直接说出的 |
|---|---|---|
| 逻辑表 | 板块名 + 表名 | 两者都能 |
| 项目内物理对象 | **引擎（定前缀）** + 项目名 + 表名 | 项目名 + 表名；引擎常需反推 |
| 实时元表 / 镜像表 / 标签表 | 项目名 + 表名（前缀固定） | 两者都能 |
| 数据源表 | 数据源（名→ID）+ 逻辑 schema + 表名 | 数据源名 + 表名，schema 常缺 |
| 字段 | 表 GUID + 字段名 | 字段名 |
| 派生指标 / 业务指标 / API / 仪表板 | 名称（用于搜索） | 名称 |

> **先归一大小写再拼**：板块名 / 项目名 / 数据源 schema 一律转小写；表名除“区分大小写引擎的物理表”外也转小写（逐引擎见 [`guid-composition-matrix.md`](guid-composition-matrix.md) §1.2）。

## 1.1 项目跑在哪个引擎上（定物理表前缀）

前缀由项目的计算引擎决定，两条获取路径（优先第一条，最省）：

```bash
# ① 照抄法（推荐）：取同项目任意一张表的 Guid，前缀与段式直接照抄
aliyun dataphin-public list-tables \
  --tenant-id "$OP_TENANT_ID" --catalog "<项目名>" \
  --cli-query 'PageResult.TableList[].{Name:Name,Guid:Guid}' --page-size 5 \
  --user-agent "$UA"

# ② 问用户：“这个项目的计算引擎是什么（MaxCompute / Hologres / StarRocks / Doris / …）？”
#   拿到引擎名后查 guid-composition-matrix.md §1.2 对照表取前缀与大小写开关
```

> 注意：实时元表 / 镜像表 / 标签表的前缀**不看引擎**，固定为 `stream_table` / `mirror_table` / `label_table`。

## 2. 数据板块名（`dp_table.` 第三段）

```bash
aliyun dataphin-public list-biz-units \
  --tenant-id "$OP_TENANT_ID" \
  --cli-query 'BizUnitList[].{Id:Id,Name:Name}' \
  --user-agent "$UA"
```

- 返回的 `Name` 形如 `LD_Fashion` → 拼 GUID 时**转小写**（表名也转小写）。
- 用户给的是项目名而非板块名时：先用 `list-tables --catalog <项目名> --keyword <表名>` 拿到命中项的 `Guid`，直接读出板块段（比继续猜板块名更快更准）。

## 3. 项目名（项目内对象第三段）

```bash
# --mode 事实必填；BASIC 与 DEV_PROD 是两个不交集结果集，要全量必须各查一次
aliyun dataphin-public list-projects \
  --mode DEV_PROD --page-no 1 --page-size 100 \
  --cli-query 'PageResult.ProjectList[].{Id:Id,Name:Name,Mode:Mode}' \
  --user-agent "$UA"
```

- 凭证若通过命令行 `--mode AK` 注入会与业务 `--mode` **同名冲突**（报 `parse failed --mode duplicated`）：此时凭证改用环境变量注入。
- 取 `Name` **转小写**（项目名无论何种引擎都转小写），但**不要**自行加 `_dev` / `_prod`。

## 4. 数据源 ID + schema（`dp_ds_table.` 中段）

```bash
aliyun dataphin-public list-data-source-with-config \
  --tenant-id "$OP_TENANT_ID" \
  --data-source-name "<数据源名>" --page 1 \
  --cli-query 'PageResult.DataSourceList[].{Id:Id,Name:Name,Type:Type}' \
  --user-agent "$UA"
```

- `Id` 即 GUID 里的 `dataSourceId`（19 位，按字符串处理）。
- **用户可能用“名称”或“编码”指代数据源**：`Name` = 显示名（如“数据服务API行级权限_数据源”），`DataSourceCatalog` = 编码（如 `ds_demo`，**DEV 侧为 `ds_demo_dev`**）。两个字段都能搜（`name` 参数对两者都生效，实测）；拿到后**必须映射到 `DataSourceId` 再拼 GUID**，不能把编码当段值填进去 `[实测]`。
- ★ **同一数据源在 DEV / PROD 各有独立 ID**（实测：`mysql_dlink_1010` → PROD `7375744037241779648` / DEV `7375744037594101184`）。因此**环境直接决定第三段取值**，必须先与用户确认环境；返回结构里 `ProdDataSourceConfig` / `DevDataSourceConfig` 各自带一个 `DataSourceId`。
- ★ **“库名 + 表名”不足以定位，必须指定数据源**：实测同一 schema `dataphin03` 下的同名表 `store_sales_detail` 同时挂在**两个不同数据源**（`7321185713616091392` 与 `7375744037241779648`），只给库名会选错。
- **独立部署内部网关的等价调用**（公共云 CLI 不可用时）：Action `SearchDataSourceConfig`，业务参数包在 `DataSourceQuery`（`{"name":"<数据源名>","pageSize":50,"currentPage":1}`）。
  > ⚠️ **切勿把 `OpUserId` 不匹配误判为“接口不可用”**：若请求带的 `OpUserId` 不是 AK 属主，所有元数据/数据源接口会统一报 `Dataphin.OpenAPI.Forbidden: Current user is not the super admin … no permission to assume role of other users`；**去掉 `OpUserId` 后同一把 AK 即可正常调用**（实测验证）。判定“无权限”前必须先排除这一项。
- **schema 与表名均转小写**（数据源表不看引擎大小写开关）。
- **schema 段不要猜**：普通数据源表是单层 schema（共 5 段）。拿不准时拿同数据源下**任意一张已采集表**的 GUID 作为模板，或直接走反查（§6）。
- **DataWorks 采集表是独立特例**（共 7 段，见 [`guid-composition-matrix.md`](guid-composition-matrix.md) §1.3.1）：除 `dataSourceId` 外还需 `DataWorks 空间 id` 与 `DataWorks 数据源 id`，两者 Dataphin 侧无接口可取 → **只能向用户索取**，或在用户确认“与模板表同数据源同 schema”后照抄；**不得因表名相似就沿用另一张表的中段**。

## 5. 表名 / 字段名的权威写法

```bash
# 表：资产清单全量（含未上架），--catalog 必填（项目名或数据板块名）
aliyun dataphin-public list-tables \
  --tenant-id "$OP_TENANT_ID" \
  --catalog "<项目名或数据板块名>" --keyword "<表名>" \
  --cli-query 'PageResult.TableList[].{Name:Name,Guid:Guid,Type:Type,Env:Env}' \
  --user-agent "$UA"

# 字段：确认字段名存在且拿到原样大小写
aliyun dataphin-public get-table-columns \
  --tenant-id "$OP_TENANT_ID" \
  --catalog "<项目名或数据板块名>" --table-name "<表名>" \
  --cli-query 'ColumnList[].{Name:Name,DataType:DataType}' \
  --user-agent "$UA"
```

> **上下文经济性**：这两个命令不带 `--cli-query` 时返回极大（实测单表字段全量约 18k 字符、`list-tables` 不裁剪单次可达 115k 字符）。一律带 `--cli-query` 裁剪。

## 6. 反查兜底（拿到官方 GUID，最省事）

```bash
# 已上架资产：按名称精确 / 关键词模糊
aliyun dataphin-public list-catalog-assets \
  --tenant-id "$OP_TENANT_ID" \
  --asset-type TABLE --query-mode EXACT_MATCH --asset-name "<资产名>" \
  --page-size 20 --user-agent "$UA" --format json

# 业务指标：直取 Guid
aliyun dataphin-public get-biz-metric-by-name \
  --tenant-id "$OP_TENANT_ID" \
  --biz-metric-name "<指标英文名>" --draft false \
  --user-agent "$UA"
```

- `list-catalog-assets` 的 `--asset-type` 取值：`TABLE` / `INDEX` / `BIZ_INDEX` / `API` / `PAGE`；`--query-mode` 取 `EXACT_MATCH`（配 `--asset-name`）或 `ASSET_SEARCH`（配 `--keyword`）。
- **覆盖范围差异是选路关键**：`list-catalog-assets` 只覆盖资产目录**已上架**资产；未上架的表只能靠 `list-tables`。

## 7. 回读校验（唯一放行判据）

```bash
aliyun dataphin-public get-catalog-asset-details \
  --OpTenantId "$OP_TENANT_ID" \
  --GetCatalogAssetDetailsQuery '{"Guid":"<待校验 GUID>","IncludeColumns":true}' \
  --user-agent "$UA"
```

放行需同时满足：

1. 负载非空（`Data` 有值）——GUID 存在；
2. `AssetType`（必要时含 `SubType`）与目标类型一致；
3. `AssetName` / `AssetFullName` 与用户描述的表/字段一致；
4. 字段级 GUID 还需 `Columns[]` 中存在同名列。

> `GetCatalogAssetDetails` 需 6.1+。**6.0 环境降级校验**：用 `list-tables --catalog <…> --keyword <表名>` 精确比对返回的 `Guid` 字符串是否与拼出的完全相等；字段级再用 `get-table-columns` 核对列名。
