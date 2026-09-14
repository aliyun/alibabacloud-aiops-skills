# 质量概况可行性结论：能拿到什么、拿不到什么

> 回答"这张表质量分是多少"之前**必须**先读本文。
> **结论（已用真实数据验证）：平台的表级质量分，OpenAPI 拿不到。** 但"质量概况"能拿得比预想的全——`GetQualityWatchTask` 的 `RuleCountInfo` 就是界面质量概况的数据源。

> **★ 措辞硬要求：给用户的输出里不得出现「监控对象」「watch」「watchId」「watchTaskId」「监控任务」。**
> 界面页签叫「质量概况」，页面上没有「监控对象」这个概念——它是 OpenAPI 侧的实现对象（`QualityWatch`）。
> 汇报一律说「**这张表下共配置了 N 条质量规则（生效 M 条）**」；未配时说「**这张表下还没有配置质量规则**」。
> 完整措辞对照见 [`ui-field-mapping.md`](ui-field-mapping.md) §6。

## 1. 结论表

| 想要的 | 能拿到？ | 来源 |
|---|---|---|
| 这张表下有没有配质量规则 | ✅ | `GetQualityWatchByObjectId`（`watchObjectId` **直接传资产 GUID**） |
| 规则总数 / 生效规则数 | ✅ | watch 的 `RuleCount` / `EnabledRuleCount` |
| 规则清单（名称/状态/模板/校验条件/绑定调度） | ✅ | `ListQualityRules`（`WatchId` 必填） |
| **强/弱/校验规则的 总数·已完成·异常·通过 计数** | ✅ **★ 最接近界面「质量概况」** | `GetQualityWatchTask` → **`RuleCountInfo`** |
| 每条规则的真实执行是否通过 | ✅ | `ListQualityRuleTasks` → **`ValidateSuccess`**(bool) |
| **表级平台质量分** | ❌ | 无任何 OpenAPI（全字段扫描 0 命中） |
| 计分方式 / 质量分权重 | ❌ | OpenAPI 连写都不支持，自然读不到 |
| **字段级 `Columns[].QualityScore`** | ❌ **实测不回填** | 字段存在但恒为 `null`，见 §2.3 |
| 规则通过率 | ⚠️ 自算 | 由 `RuleCountInfo` 或 `ValidateSuccess` 推导，**≠ 平台质量分** |

## 2. 为什么表级质量分拿不到（证据）

### 2.1 真实响应里没有任何分数字段

对已配置 8 条规则的真实表跑完整链路后，对 `ListQualityWatches` / `ListQualityRules` / `ListQualityRuleTasks` / `GetQualityWatchTask` 的返回体做 `score|weight|grade` 递归扫描：**命中 0 个**。

规则对象（`QualityRuleList[]`）的完整键集（实测）：

```
Id, Name, Description, Status, Strength, TemplateId, TemplateName, TemplateType,
TemplateScope, CatalogList, ValidateObject, ValidateConditionList, FormPropertyList,
AttributeWithValueList, ScheduleBindList, EnableErrorArchive, WatchId,
TestRunRuleTaskId, TestRunRuleTaskStatus, TestRunRuleValidateResult,
Creator, CreatorName, CreateTime, Modifier, ModifierName, ModifyTime
```

规则任务对象（`QualityRuleTaskList[]`）的完整键集（实测）：

```
Id, WatchId, WatchTaskId, RuleId, TemplateId, Status, StartTime, EndTime,
ValidatePartition, ValidateObjectType, ValidateObjectName, ValidateSuccess,
BizDate, BizDateFormat, Creator, CreateTime, Modifier, ModifyTime
```

两者都只有"状态/是否通过"，没有分数。

### 2.2 计分规则本身就在 OpenAPI 之外

`configure-quality-rule` skill 已确认：**归档模式、归档位置、计分方式、质量分权重四项 OpenAPI 不可配**，创建规则后由后端填默认值（计分方式=「质量校验状态」、权重=1）。计分口径不进 OpenAPI，按该口径算的分数自然也没有出口。

### 2.3 `Columns[].QualityScore` 是个死字段（实测结论，勿再指望）

`GetCatalogAssetDetails`（`IncludeColumns: true`）的 `Columns[]` 里有 `QualityScore` 字段，但**实测不回填**：

```jsonc
// dp_table.300023201.ld_fashion.dim_employee —— 该表确有 8 条质量规则、
// 其中 employee_id 字段就挂着规则并且当天校验未通过
{
  "Guid": "dp_table.300023201.ld_fashion.dim_employee.employee_id",
  "Name": "employee_id", "DisplayName": "employee_主键",
  "Standards": [{"Id": 120350, "Name": "id", "Code": "hr_person_id"}],
  "QualityScore": null          // ← 有规则、有异常，依然是 null
}
```

105 个字段**全部为 `null`**。**这次是有效证据**（质量模块可读 + 该表确有规则 + 该字段确有异常），所以结论是：**该版本 `QualityScore` 不回填，不能用它做字段级质量分**。

补充扭转面：又对 **60 张表**（含分区表/逻辑表/数据源表，列数 2~125）逐张扫描 `Columns[]`，`QualityScore` 非空列数**仍为 0**；同一批表里 `ClassifyName` / `LevelShortName` 非空列数高达 99，`Standards` 也有多张表命中。

> **★ 所以不能拿“`QualityScore` 是死字段”类推到其他三项字段级信息上。**
> `Standards`（关联标准）/ `ClassifyName`（数据分类）/ `LevelShortName`（数据分级）**都是活字段，必须逐列输出**；
> 只有「质量分」这一列写 `-` 并注明无 OpenAPI。详见 [`asset-type-matrix.md`](asset-type-matrix.md) §1.1。

## 3. ★ 最大的坑：响应体不在 `Data` 键下，只读 `Data` 会把自己骗了

**质量模块（及 `ListTables` 等）的业务负载在 `PageResult` / 具名键下，不在 `Data` 下。**

| Action | 负载键 | 列表键 |
|---|---|---|
| `ListQualityWatches` | `PageResult` | `QualityWatchList` |
| `ListQualityRules` | `PageResult` | `QualityRuleList` |
| `ListQualityRuleTasks` | `PageResult` | `QualityRuleTaskList` |
| `ListQualityTemplates` | `PageResult` | `QualityTemplateList` |
| `GetQualityWatchByObjectId` | **`QualityWatchInfo`** | — |
| `GetQualityWatchTask` | **`WatchTaskInfo`** | — |
| `GetCatalogAssetDetails` / `GetAssetAttributes` | `Data` | — |

> **踩坑实录**：探针只取 `body["Data"]`，于是质量模块所有接口都"返回 `Code=OK` + `Data=null`"。据此一路推理出「该 AK 未授权质量模块」，还编了一套用 `ListQualityTemplates` 做阳性对照的诊断法——**全是错的**。换 AK 后打印完整响应体才发现 `PageResult.TotalCount=96`，数据一直都在。
>
> **规则：拿到空结果的第一反应必须是 `print(list(body.keys()))`，确认自己读的是不是正确的负载键**，再谈"没数据 / 没配置 / 没授权"。

## 4. 真实字段名与 SDK v1.0 文档不一致（以实测为准）

| SDK v1.0 文档写的 | 实际返回 |
|---|---|
| `watchId` | **`Id`** |
| `watchType` | **`Type`** |
| `watchStatus` | **`Status`** |
| `table` | **`TableInfo`** |
| `datasource` | **`DataSourceInfo`** |
| `ruleStrength` | **`Strength`** |
| `tryRunRuleTaskId/Status/ValidateResult` | **`TestRunRuleTaskId/Status/ValidateResult`** |
| `validateResult`（规则任务） | **`ValidateSuccess`**（bool） |
| `ruleCounts` | **`RuleCountInfo`** |

`TableInfo` 里还带着一堆有用的东西（实测）：`Id`（= 资产 GUID）、`Catalog`、`Name`、`Type`（如 `LOGIC_DIM_TABLE`）、`Env`、`Owner`、`ProjectId/ProjectName`、`BizUnitId/BizUnitName`、`DataSourceType/DataSourceId`、`IsPartitionTable`。

## 5. 实测契约（POC V6.3 独立部署，直调 OpenAPI）

| 现象 | 实测报文 | 结论 |
|---|---|---|
| `GetQualityWatchByObjectId` 业务参数放 body | `Missing required argument: WatchType` | `WatchType`/`WatchObjectId` 是 **query 位参数**（参与签名） |
| `GetQualityWatchByObjectId(TABLE, 资产GUID)` | ✅ 返回 `QualityWatchInfo.Id=3925946` | **TABLE 类型的 `watchObjectId` 就是资产 GUID**，无需另找内部 ID |
| `ListQualityRules` 不传 watchId | `DPN.Bus.ParamsValidateError: watchId is null!` | `WatchId` **事实必填**（文档标可选） |
| 直调 `PagedQueryQualityWatches` | `Unknown API: PopSDKPagedQueryQualityWatches` | `PagedQuery*` 是 v1.0 旧裸名；真实 Action = CLI kebab 命令的 PascalCase |
| `GetTableLineages` 不传 `FilterQuery` | `DPN.Commons.InternalError` | `FilterQuery` 事实必传 |
| `SearchCatalogTable` | `Unknown API: PopSDKSearchCatalogTable` | 此部署无该 Action（也不需要——GUID 直接可用） |
| 同名表的多个 watch | keyword 搜 `dim_employee` 命中 4 个 | **DEV/PROD、`_org` 后缀表各自独立 watch**，必须用 `TableInfo.Id` 精确匹配目标 GUID，不能取第一条 |

## 6. 实测案例：`dp_table.300023201.ld_fashion.dim_employee`（POC，2026-08-07）

| 步骤 | 结果 |
|---|---|
| `GetQualityWatchByObjectId(TABLE, 该 GUID)` | ✅ `QualityWatchInfo.Id=3925946`，`LatestWatchTaskId=7825649` |
| watch 概况 | `Name=LD_Fashion.dim_employee`，`Status=ENABLE`，`Env=PROD`，`RuleCount=8`，`EnabledRuleCount=3`，质量负责人 `SuperAdmin` |
| `ListQualityRules(WatchId=3925946)` | ✅ 8 条：3 条 `ENABLE`（模板 100 字段空值校验 ×3）、5 条 `DISABLE`（含模板 200/300/1100） |
| `GetQualityWatchTask(7825649).RuleCountInfo` | 强规则 `total=1, finished=1, error=1, success=0`；弱规则与校验规则全 0 |
| `ListQualityRuleTasks(WatchTaskId=7825649)` | 1 条：`RuleId=4642836`（"告警test"），校验对象 `employee_id`（COLUMN），分区 `ds='20260807'`，`Status=SUCCESS`，**`ValidateSuccess=false`** |
| 分数字段扫描 | **0 命中** |
| `Columns[].QualityScore` | 105 个字段全 `null`（该表明明有规则且有异常）→ 死字段 |

**该表质量概况（可直接交付的口径，注意里面没有「监控对象」「watchId」）**：

```text
质量概况（LD_Fashion.dim_employee，PROD，业务日期 20260807）
├─ 平台事实
│   ├─ 这张表下共配置了 8 条质量规则（生效 3 条，禁用 5 条）
│   ├─ 最近一次质量校验：Status=SUCCESS
│   ├─ 强规则：1 条已执行，异常 1、通过 0
│   └─ 异常明细：规则「告警test」（模板100 字段空值校验）
│        校验对象 employee_id，分区 ds='20260807'，ValidateSuccess=false
├─ 自算指标（非平台质量分）
│   └─ 规则通过率 = 通过 0 / 已完成 1 = 0%
│      口径：取最近一次质量校验的强规则计数；未执行规则已排除；未做强弱加权
└─ 说明：平台口径的「表级质量分」无 OpenAPI，需到 Dataphin 界面查看
```

> 注意"规则数 8"与"强规则已执行 1"的落差：8 条里只有 3 条生效，且当次监控任务只跑出 1 条规则任务。**汇报时必须把分母讲清楚**，否则容易被理解成"8 条规则只过了 0 条"。

## 7. 推荐的「质量概况」输出口径

平台事实与自算指标必须分开写，不能混成一个数：

1. **优先用 `GetQualityWatchTask.RuleCountInfo`**——它按 强/弱/校验 三类各给 `TotalRuleCount / FinishedRuleCount / ErrorRuleCount / SuccessRuleCount`，是界面质量概况的同源数据，比自己遍历规则任务更准。
2. **分母写清楚**——`RuleCount`（配了多少）、`EnabledRuleCount`（生效多少）、`FinishedRuleCount`（本次跑完多少）是三个不同的数，别混用。
3. **不擅自加权**——平台默认计分方式是「质量校验状态」、权重 1；要按强弱加权必须标明是自定义口径。
4. **带上业务日期与分区**——质量结果按 `BizDate` 分天、按 `ValidatePartition` 分区，不写这两个的通过率没有意义。
5. **一句话免责**——明确"此为规则通过率，非平台质量分"。
6. **不透出内部对象名**——「监控对象」`watch` `watchId` `watchTaskId`「监控任务」均不进给用户的输出；统一说「这张表下的质量规则」与「最近一次质量校验」。

## 8. 如果确实需要平台口径的表级质量分

1. **界面查看**（当前唯一能拿到平台口径分数的方式）。
2. **自算 + 对齐口径**：向用户确认各规则的计分方式与权重（界面可见），再按平台公式复算——能逼近，但仍非平台产出值。
3. **提需求**：质量模块补一个"按监控对象/资产查质量分"的只读 OpenAPI，并把 `Columns[].QualityScore` 这个已存在但不回填的字段补上。这是本板块唯一的真实能力缺口。
