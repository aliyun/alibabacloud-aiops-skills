---
name: query-kg
description: |
  知识图谱图数据查询。通过 CLI 原生命令完成：Cypher 图查询（仅 Neo4j 引擎）、邻居节点遍历与关键词/语义混合搜索（引擎无关）。纯查询 Skill，不含任何写操作。查询前必须先确认图谱空间绑定的图引擎（Neo4j / Lindorm）——Lindorm 不支持 Cypher。
  触发场景：知识图谱查询 / Cypher 查询 / 邻居遍历 / 图查询 / 关系路径查询 / 语义搜索 / 知识图谱探索。
---

# 知识图谱图数据查询（query-kg）

## 1. Scenario Description

数据分析师或数据工程师通过阿里云 CLI 对知识图谱进行只读查询，包括 Cypher 图查询语言、邻居节点遍历与关键词/语义混合搜索，用于数据探索、关系路径分析和图谱可视化数据获取。

> **🚨 第一步先确认图引擎（硬前置）**：知识图谱空间创建时绑定一个图引擎，**引擎直接决定可用的查询通道**：
>
> | 引擎 | Cypher（`exec-kg-cypher`） | 邻居遍历（`get-kg-neighbor`） | 语义搜索（`search-kg-by-semantic`） |
> |---|---|---|---|
> | **Neo4j** | ✅ 支持 | ✅ | ✅（V6.2.3+） |
> | **Lindorm 图引擎**（V6.2.3 新增） | ❌ **不支持**，调用固定报 `DPN.Commons.InternalError`（实测） | ✅ 实测通过 | ✅ 实测通过（V6.2.3+） |
>
> Lindorm 的查询语言是 Gremlin，但 **`ExecKgGremlin` OpenAPI 尚未上线**（CLI 插件实测无 `exec-kg-gremlin` 命令）。在 Lindorm 空间上做图查询，请直接走步骤 2/3/4 的引擎无关通道。完整差异矩阵见 [图引擎能力矩阵](../graph-engine-capabilities.md)。
>
> 引擎取得途径：用户告知 / 控制台「知识图谱 → 空间配置」 / 智能工作台右栏图谱空间条目的引擎标签。**OpenAPI 无查空间详情/引擎的接口，不确定时直接问用户，不要默认当作 Neo4j。**

**业务流程：**
```
确认图引擎 → （Neo4j）Cypher 查询探索 / （Lindorm）实体列表 + 语义搜索定位 → 邻居节点遍历 → 结果分析
```

**资源拓扑：**
```
知识图谱空间（Workspace）
└── 图引擎（Neo4j 或 Lindorm，创建时绑定）
    ├── Cypher 查询（只读，**仅 Neo4j**）
    │   ├── MATCH / WHERE / RETURN
    │   ├── 节点属性过滤
    │   └── 路径查询与聚合
    ├── 邻居节点遍历（引擎无关）
    │   ├── 方向控制（DirectionType: In/Out/Both）
    │   ├── 深度控制（Depth）
    │   └── 关系类型过滤（RelationTypes）
    └── 关键词+语义混合搜索（引擎无关，V6.2.3+，**仅实体**）
        ├── QueryText 自然语言查询
        ├── EntityTypeCodes / PropertyCode 过滤
        └── TopK / MinSimilarity 阈值控制
```

**前置条件：**
- 知识图谱空间已存在且 Schema 已发布到图引擎（`manage-kg-schema` Skill 产出）
- 知识数据已写入（`manage-kg-knowledge` Skill 产出）
- OpTenantId（租户 ID）、WorkspaceId（空间 ID）**与该空间的图引擎**已知

> **CLI 原生支持**：KG OpenAPI 已正式发布（CLI `--help` 实测显示 Online version: **v6.1.1**，以 `aliyun dataphin-public exec-kg-cypher --help` 实际输出为准），并注册到 `aliyun-cli-dataphin-public` 插件（**>= 0.7.1**）。本 Skill 全部使用 CLI 原生命令 `exec-kg-cypher` / `get-kg-neighbor`，无需 Python SDK。
>
> **旧环境兜底**：独立部署低于 KG OpenAPI 发布版本（< v6.1.1）的环境未发布 KG OpenAPI，CLI 命令会报 API 不存在——此时可退回 Python Tea SDK `call_api()` 泛化调用，本 Skill 保留封装脚本 `scripts/query-kg.py`（见 [Python SDK 模板](./references/python-sdk-template.md)）。

> **本 Skill 纯只读**：不涉及任何写操作（无 HITL 确认），查询结果不影响图谱数据。

## 2. Installation

**Pre-check: Aliyun CLI >= 3.4.8 required**
> 运行 `aliyun version` 确认版本 >= 3.4.8。未安装或版本过低，请从 https://aliyuncli.alicdn.com 安装/升级（各操作系统一键脚本见 ./references/cli-installation-guide.md）。

**Pre-check: Aliyun CLI plugin update required**
> [MUST] 运行 `aliyun configure set --auto-plugin-install true` 开启插件自动安装。
> [MUST] 运行 `aliyun plugin update` 确保已装插件保持最新（KG 命令要求插件 **>= 0.7.1**）。

```bash
# 安装 aliyun CLI（>= 3.4.8）：https://github.com/aliyun/aliyun-cli
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 开启插件自动安装并更新已装插件
aliyun configure set --auto-plugin-install true
aliyun plugin update

# 安装 dataphin-public 插件（>= 0.7.1，KG 命令自 0.7.x 起注册）
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证：KG 查询命令已注册
aliyun version            # 需 >= 3.4.8
aliyun dataphin-public exec-kg-cypher --help
aliyun dataphin-public get-kg-neighbor --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

### Pre-check: Credentials Required

```bash
# 检查凭证配置
aliyun configure list

# 检查 CLI 版本
aliyun version
# 要求 >= 3.4.8

# 检查 KG 命令已注册（插件 >= 0.7.1）
aliyun dataphin-public exec-kg-cypher --help
```

**凭证不可打印**：任何时候不得将 AccessKey ID/Secret 输出到终端或日志。

## 5. RAM Policy

本 Skill 仅涉及只读 API，最小 RAM 权限：

```json
{
  "Effect": "Allow",
  "Action": [
    "dataphin:ExecKgCypher",
    "dataphin:GetKgNeighbor",
    "dataphin:SearchKgBySemantic"
  ],
  "Resource": "*"
}
```

### Permission Failure Handling

若遇到权限错误（HTTP 403 或 ErrorCode 含 `Forbidden`/`NoPermission`/`Dataphin.KG.NoPermission`），请：
1. 确认 RAM 用户已附加上述策略
2. 确认策略中 Resource 范围覆盖目标租户
3. 确认当前用户在知识图谱空间中具有数据查询权限
4. 联系租户管理员授权

详见 [RAM 策略参考](../../ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation**
> 执行前必须确认以下业务参数：

| 参数 | CLI 标志 | 含义 | 获取方式 | 必填 |
|------|---------|------|---------|------|
| **图引擎** | （不是 CLI 参数） | 空间绑定的引擎：`Neo4j` / `Lindorm` | **向用户确认**（或看工作台右栏引擎标签 / 控制台空间配置） | **是（选命令前置）** |
| OpTenantId | `--op-tenant-id` | 租户 ID | profile 或询问用户 | 是 |
| WorkspaceId | `--workspace-id` | 知识图谱空间 ID | **必须向用户索取**（见下方说明） | 是 |
| ExecCommand | `--exec-command` | Cypher 查询指令 JSON（`{Query, Limit, Params}`） | 用户编写 | exec-kg-cypher（仅 Neo4j） |
| EntityDataId | `--entity-data-id` | 起始实体 DataId | `list-kg-entity` 的 `EntityList[].EntityId`（Neo4j 也可用 Cypher 的 `NodeList[].DataId`） | get-kg-neighbor |
| EntityType | `--entity-type` | 起始实体类型 | `export-kg-schema` 或上游查询结果 | get-kg-neighbor |
| NeighborsQuery | `--neighbors-query` | 遍历指令 JSON（`{Depth, DirectionType, RelationTypes}`） | 用户指定 | get-kg-neighbor（可选） |
| SearchCommand | （见步骤 3） | 搜索指令（`{QueryText, EntityTypeCodes, PropertyCode, TopK, MinSimilarity}`），**字段名是 `SearchCommand` 不是 `SearchKgBySemanticCommand`** | 用户描述转写 | search-kg-by-semantic |

> **图引擎未确认前不要发图查询**：Lindorm 空间上发 Cypher 必报 `DPN.Commons.InternalError`，白费一次调用且易误判为环境故障。

> **WorkspaceId 无自助发现途径**：KG OpenAPI **不提供列出 KG 空间的接口**（全部 18 个 KG 命令中无任何 list-workspace 类命令），WorkspaceId 必须向用户索取（32 位小写 hex 字符串，可在控制台知识图谱空间列表页查到）。不要尝试猜命令或翻 help 探索。

详细 API 入参/出参见 [KG Query API 参数参考](./references/kg-query-api-params.md)。

## 7. Observability

本子 Skill 的 session-id **继承自父 Skill `alibabacloud-dataphin-skills`**，不重新生成。

所有 CLI 命令携带：
```
--user-agent AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}
```

其中 `{SESSION_ID}` 为父 Skill 生成的 32 字符小写十六进制字符串。

## 8. Core Workflow

### 步骤 0：确认图引擎（选命令的分水岭）

开始任何图查询前先确认引擎，再按下表选路径：

| 需求 | Neo4j 空间 | Lindorm 空间 |
|---|---|---|
| 自由图查询 / 多跳路径 / 聚合统计 | 步骤 1（Cypher） | ❌ 无通道——先向用户说明，再用步骤 2/3 组合逼近；确需复杂图计算则引导到控制台图谱视图 |
| 按类型/属性找实体 | `list-kg-entity`（manage-kg-knowledge） | `list-kg-entity` |
| 自然语言/近似词找实体 | 步骤 3（语义搜索） | 步骤 3（语义搜索） |
| 看某实体的关系网络 | 步骤 2（邻居遍历） | 步骤 2（邻居遍历） |

> 在 Lindorm 空间上被要求“用 Cypher 查”时，**直说不支持并给出替代方案**，不要先发一次 Cypher “试试看”。

### 步骤 1：Cypher 图查询（仅 Neo4j 引擎空间）

Cypher 是图数据库查询语言，支持节点/关系模式匹配、属性过滤、路径查询等。

> **❌ Lindorm 空间不要执行本步骤**：`exec-kg-cypher` 在 Lindorm 上固定返回 `DPN.Commons.InternalError`（实测，trace f3781307 连碰 3 次）。该错误**不是**环境故障：改写语句、降低 `Limit`、换标签均无效；把 Gremlin 语句（如 `g.V().hasLabel('Company')`）塞进 `Query` 字段也同样报错。Lindorm 请转步骤 2/3。

> **🚨 节点必须带类型标签，禁止裸 `MATCH (n)`**：无标签查询（如 `MATCH (n) RETURN labels(n), count(*)`）会扫描底层图引擎 Space 全库——实测扫到 100+ 种标签、百万级节点，是性能灾难。测试/POC 环境若多个知识图谱空间共享同一 Space，还会扫到其他空间数据（实际客户部署要求**一个 Space 仅绑定一个知识图谱空间**，按规范部署时无跨空间数据问题）。带标签（如 `MATCH (n:COMPANY)`）时按类型精确命中。所有节点模式（含多跳路径两端）都必须显式指定本空间 Schema 中定义的实体类型标签。

```bash
aliyun dataphin-public exec-kg-cypher \
  --op-tenant-id "{OpTenantId}" \
  --workspace-id "{WorkspaceId}" \
  --exec-command '{
    "Query": "MATCH (n:COMPANY) RETURN n.name, n.industry LIMIT 10",
    "Limit": 100
  }' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}"
```

> `--exec-command` 是 JSON 对象：`Query`（Cypher 语句，必填）、`Limit`（返回上限，默认 100）、`Params`（参数化查询 `[{DataType, Key, Value}]`，可选）。
> 独立部署环境需加 `--endpoint dataphin-openapi.<env>.aliyun.com`（不带 `https://` 前缀）。

**响应处理：**
- `Data.NodeList[]`：匹配到的节点列表（含 `DataId`、`EntityType`、`Properties[]`）
- `Data.EdgeList[]`：匹配到的边列表（含 `RelationId`、`RelationType`、`SourceEntityId`、`TargetEntityId`）
- `Data.RowList[].Columns[].Code/Value`：RETURN 子句返回的标量值（与 Cypher RETURN 列对应）
- `Data.ExecuteCypher`：实际执行的 Cypher 语句

> **⚠️ 实测注意（RETURN n 与 DataId）**：`RETURN n`（返回整节点）时，部分空间/版本下 `DataId` 可能为 `null`、`Properties` 为空——此时无法直接拿到供步骤 2 使用的 `DataId`。稳妥做法：在 Cypher 中 `RETURN` 能定位实体的具体属性（如 `RETURN n.name`），或改用 `list-kg-entity`（manage-kg-knowledge Skill）按属性过滤查回 `EntityId`；也需确认该实体类型**已发布到图引擎**（未发布类型对 get-kg-neighbor 会报 `DPN.Planning.KgEntityNotExists`）。标量统计（如 `count(n)`）走 `RowList`，不受影响。

#### Cypher 常用查询模式

```
# 1. 查询所有某类型实体
MATCH (c:COMPANY) RETURN c.name, c.industry LIMIT 20

# 2. 查询两个实体间的关系路径
MATCH (a:MovieActor)-[r:ACTED_IN]->(f:Film)
WHERE a.name = '张三'
RETURN a.name, f.title, r.role

# 3. 多跳路径查询（两端节点必须带标签，禁止裸 (a)/(b)）
MATCH path = (a:COMPANY)-[*1..3]->(b:COMPANY)
WHERE a.name = '起点节点'
RETURN path LIMIT 5

# 4. 聚合统计
MATCH (n:COMPANY)-[r:INVEST]->(m:COMPANY)
RETURN n.name, count(r) AS invest_count
ORDER BY invest_count DESC LIMIT 10

# 5. 属性过滤
MATCH (n:Film) WHERE n.year > 2020 RETURN n.title, n.year
```

> **限制**：`exec-kg-cypher` 仅支持查询数据，不支持 `CREATE`、`MERGE`、`DELETE`、`SET` 等写入/修改语句。注意上方所有示例的节点模式均带类型标签——这是硬性要求，不是风格偏好。

### 步骤 2：邻居节点遍历

从指定实体出发，遍历其邻居节点，用于发现关联关系、构建局部子图。

```bash
aliyun dataphin-public get-kg-neighbor \
  --op-tenant-id "{OpTenantId}" \
  --workspace-id "{WorkspaceId}" \
  --entity-data-id "{DataId}" \
  --entity-type "{EntityType}" \
  --neighbors-query '{"Depth": 1, "DirectionType": "Both"}' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}"
```

> **重要**：
> - `--entity-data-id` 与 `--entity-type` 均为**必填**
> - DataId 来源：exec-kg-cypher 返回的 `NodeList[].DataId`，或 `list-kg-entity` 返回的 `EntityList[].EntityId`
> - 遍历控制参数收在 `--neighbors-query` JSON 对象内，方向字段名是 **`DirectionType`**（不是 `Direction`）

**响应处理：**
- `Data.NodeList[]`：邻居节点列表（含 `EntityId`、`EntityType`、`PropertyList[].Code/Value/DataType`）
- `Data.EdgeList[]`：连接关系列表（含 `RelationId`、`RelationType`、`SourceEntityId`、`TargetEntityId`、`PropertyList[]`）

#### 进阶遍历参数

```bash
# 仅沿出边方向遍历，深度 2，过滤关系类型
aliyun dataphin-public get-kg-neighbor \
  --op-tenant-id "{OpTenantId}" \
  --workspace-id "{WorkspaceId}" \
  --entity-data-id "{DataId}" \
  --entity-type "{EntityType}" \
  --neighbors-query '{"Depth": 2, "DirectionType": "Out", "RelationTypes": ["ACTED_IN", "INVEST"]}' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}"
```

`--neighbors-query` 结构：

| 字段 | 类型 | 可选值 | 说明 |
|------|------|--------|------|
| DirectionType | String | `In` / `Out` / `Both` | 遍历方向，默认 Both |
| Depth | Integer | 1~N | 扩展深度，默认 1 |
| RelationTypes | Array\<String\> | 关系类型编码数组 | 仅遍历指定关系类型（可选） |

### 步骤 3：关键词 + 语义混合搜索（引擎无关，V6.2.3+）

`SearchKgBySemantic` 同时执行关键词匹配与语义向量检索，经 RRF 算法融合排序返回；当语义搜索条件不满足（如无向量模型/无 SemanticEnabled 属性）时**自动降级为仅关键词搜索**。Neo4j 与 Lindorm 均支持，是 Lindorm 空间“找实体”的首选通道。

> **仅支持实体搜索，不支持关系搜索**（产品侧确认）：无关系类型过滤参数，出参 `MatchType` 恒为 `Entity`。要看关系请拿到实体 ID 后转步骤 2 邻居遍历。

> **命令可用性**：该 API 为 V6.2.3 新增，当前 CLI 插件（0.7.x）**尚未注册** `search-kg-by-semantic` 命令（`aliyun dataphin-public --help` 实测 18 个 KG 命令中无此项）。路径：① 先 `aliyun plugin update` 后重试；② 插件仍无则走 Python Tea SDK 泛化调用（`Action=SearchKgBySemantic`，formData POST，参考 [Python SDK 模板](./references/python-sdk-template.md)）；③ 在 Dataphin 智能工作台内直接用 `run_kg_query(action=SearchKgBySemantic)`（已封装签名，不依赖插件）。

> **🚨 body 字段名是 `SearchCommand`（实测）**：接口设计文档上写的 `SearchKgBySemanticCommand` **服务端不认**，传它会报 `Dataphin.OpenAPI.BadRequest: Missing required argument: SearchCommand`（工作台 trace fdbd9ed2 首次真机调用实测）。与 `exec-kg-cypher` 的 `ExecCommand`、`create-kg-entity` 的 `CreateCommand` 同款命名风格。

插件已注册时的 CLI 形式（参数名按 body 字段 kebab 化推断，**插件尚未注册该命令，未实测**）：

```bash
aliyun dataphin-public search-kg-by-semantic \
  --op-tenant-id "{OpTenantId}" \
  --workspace-id "{WorkspaceId}" \
  --search-command '{
    "QueryText": "做新能源汽车的公司",
    "EntityTypeCodes": ["COMPANY"],
    "TopK": 20,
    "MinSimilarity": 0.6
  }' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}"
```

`SearchCommand` 字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| QueryText | String | 是 | 自然语言查询文本，0~500 字符 |
| EntityTypeCodes | Array\<String\> | 否 | 实体类型编码过滤；不传则搜所有实体类型 |
| PropertyCode | String | 否 | 指定某个属性编码做语义搜索；不传则搜所有 `SemanticEnabled = true` 的属性 |
| TopK | Integer | 否 | 返回上限，默认 20，范围 1~100 |
| MinSimilarity | Float | 否 | 最低相似度阈值 0.0~1.0，默认 0.0（不过滤），**仅语义搜索路径生效** |

**响应处理（`SearchKgBySemanticResult`）：**

- `TotalCount`：命中总数
- `SearchResults[]`：按相似度得分降序，每项含：
  - `MatchType`：匹配类型（当前恒为 `Entity`）
  - `MatchSource`：`keyword`（仅关键词命中）/ `semantic`（仅语义命中）/ `both`（两路均命中）
  - `ItemId` / `ItemTypeCode`：实体 ID 与实体类型编码（`ItemId` 可直接当作步骤 2 的 `--entity-data-id`）
  - `MatchedPropertyCode` / `MatchedPropertyValue`：命中的属性编码与实际值
  - `SimilarityScore`：余弦相似度得分 0.0~1.0

> `MatchSource=keyword` 占比异常高时，通常意味着该空间没配向量模型或目标属性未开 `SemanticEnabled`（已降级为关键词搜索），向用户说明而不是反复调 `MinSimilarity`。

> **语义未生效的正解在 Schema 属性层，不是 Cypher**：开启语义检索 = 在 Schema 的实体/关系属性上置 `isSemanticEnabled: true` 并导入发布（见 [manage-kg-schema](../manage-kg-schema/SKILL.md) §开启语义检索），平台自动建向量索引；**不要用 `exec-kg-cypher` 手建向量索引**（只读通道，CREATE 会被拒）。另注意 Neo4j 版本门槛：平台发布时自动执行的 `CREATE VECTOR INDEX` 需 Neo4j 5.11+，低版本实例向量索引创建必失败（trace 72c13131 实测，报 `Invalid input 'VECTOR'`），此时语义搜索永远降级为关键词——属引擎版本限制，引导升级而非重试。

### 步骤 4：组合查询模式

典型的知识图谱探索流程：先定位目标实体 → 再邻居遍历展开子图。定位手段按引擎选：Neo4j 可用 Cypher；Lindorm 用语义搜索或 `list-kg-entity`。

**模式 A（Neo4j）：Cypher 定位 → 邻居展开**

```bash
# Step A: 用 Cypher 找到目标实体的 DataId
aliyun dataphin-public exec-kg-cypher \
  --op-tenant-id "{OpTenantId}" --workspace-id "{WorkspaceId}" \
  --exec-command '{"Query": "MATCH (n:Drug {drug_code: '\''D002'\''}) RETURN n LIMIT 1", "Limit": 1}' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}"
# → 从响应 Data.NodeList[0] 提取 DataId（如 "0a259156-d9f9-4bc1-be44-9b942a0b0e1a"）和 EntityType（如 "Drug"）

# Step B: 以该实体为起点遍历邻居（深度 2、双向）
aliyun dataphin-public get-kg-neighbor \
  --op-tenant-id "{OpTenantId}" --workspace-id "{WorkspaceId}" \
  --entity-data-id "0a259156-d9f9-4bc1-be44-9b942a0b0e1a" \
  --entity-type "Drug" \
  --neighbors-query '{"Depth": 2, "DirectionType": "Both"}' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}"
# → Data.NodeList[] 和 Data.EdgeList[] 包含完整的子图数据
```

> 可用全局参数 `--cli-query <jmespath>` 直接过滤输出，如 `--cli-query 'Data.NodeList[0].DataId'`。

**模式 B（Lindorm，也适用于 Neo4j）：语义搜索 / 实体列表定位 → 邻居展开**

```bash
# Step A（任选一种定位方式）
# A1. 自然语言定位（推荐，拿 SearchResults[0].ItemId）
#     见步骤 3；CLI 未注册时用 SDK 泛化调用或工作台 run_kg_query
# A2. 按类型 + 属性精确定位（manage-kg-knowledge）
aliyun dataphin-public list-kg-entity \
  --op-tenant-id "{OpTenantId}" --workspace-id "{WorkspaceId}" \
  --entity-type "COMPANY" \
  --list-query '{"Keyword": "阿里", "FilterList": [{"PropertyCode": "industry", "Op": "eq", "Value": "互联网"}], "PageNum": 1, "PageSize": 20}' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}" \
  --cli-query 'PageResult.EntityList[0].EntityId'

# Step B: 以得到的 EntityId 为起点遍历邻居（引擎无关）
aliyun dataphin-public get-kg-neighbor \
  --op-tenant-id "{OpTenantId}" --workspace-id "{WorkspaceId}" \
  --entity-data-id "{EntityId}" \
  --entity-type "COMPANY" \
  --neighbors-query '{"Depth": 2, "DirectionType": "Both"}' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}"
```

> `list-kg-entity` 的实体类型走**扁平参数** `--entity-type`（实测把 `EntityType` 写进 `--list-query` 会报 `unknown field: EntityType`）；分页/过滤才在 `--list-query` 里。

### 兜底：旧版本独立部署（SDK 泛化调用）

独立部署低于 KG OpenAPI 发布版本（< v6.1.1）未发布 KG OpenAPI 时，使用封装脚本 `scripts/query-kg.py`（Python Tea SDK `call_api()`）：

```bash
pip install alibabacloud-tea-openapi alibabacloud-tea-util
# 前置环境变量：ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
#              DATAPHIN_ENDPOINT / DATAPHIN_TENANT_ID / DATAPHIN_WORKSPACE_ID
python3 scripts/query-kg.py cypher --query "MATCH (n:COMPANY) RETURN n.name LIMIT 10" [--limit 100] [--ignore-ssl]
python3 scripts/query-kg.py neighbor --entity-data-id "<DataId>" --entity-type "<EntityType>" [--direction Both] [--depth 1] [--ignore-ssl]
```

> 脚本已固化 `ExecCommand` 参数名、`EntityDataId`/`EntityType` 必填、POST 方法等实测暗坑；独立部署自签证书加 `--ignore-ssl`。SDK 调用细节见 [Python SDK 模板](./references/python-sdk-template.md)。

## 9. Success Verification

1. **引擎判定正确**：所选命令与空间引擎匹配（Lindorm 空间未发起任何 `exec-kg-cypher` 调用）
2. **Cypher 查询（Neo4j）**：`exec-kg-cypher` 返回非空 `Data.RowList`（标量查询）或 `Data.NodeList`（节点查询）
3. **邻居遍历**：`get-kg-neighbor` 返回 `Data.NodeList` 和 `Data.EdgeList`，且与预期关联关系一致
4. **语义搜索**：`SearchKgBySemanticResult.TotalCount > 0` 且 `SearchResults[].SimilarityScore` 降序；`MatchSource` 含 `semantic`/`both` 说明语义路径生效（全为 `keyword` 则已降级）
5. **无错误**：响应中 `Code` 为 `OK`、`Success` 为 `true`，无 `Dataphin.KG.*` 错误码

## 10. Cleanup

本 Skill 为纯只读查询，不创建任何资源，无需清理。

## 11. Command Tables

| CLI 命令 | 用途 | 适用引擎 | 关键参数 |
|------|------|------|----------|
| `exec-kg-cypher` | 执行 Cypher 查询（只读） | **仅 Neo4j** | `--exec-command`（JSON：Query/Limit/Params） |
| `get-kg-neighbor` | 获取邻居节点 | Neo4j + Lindorm | `--entity-data-id` + `--entity-type`（均必填）、`--neighbors-query`（JSON：Depth/DirectionType/RelationTypes） |
| `search-kg-by-semantic` | 关键词+语义混合搜索（**仅实体**，V6.2.3+） | Neo4j + Lindorm | `--search-command`（JSON：QueryText/EntityTypeCodes/PropertyCode/TopK/MinSimilarity；body 字段名实测为 `SearchCommand`） |
| ~~`exec-kg-gremlin`~~ | Gremlin 查询 | — | **API 尚未上线，命令不存在，不要尝试** |

> `exec-kg-cypher` / `get-kg-neighbor` 已注册到 CLI 插件（>= 0.7.1，`--help` 实测 Online version v6.1.1）；`search-kg-by-semantic` 为 V6.2.3 新增，插件 0.7.x 尚未注册（先 `aliyun plugin update`，仍无则走 SDK 泛化调用或工作台 `run_kg_query`）。公共参数 `--op-tenant-id` / `--workspace-id` 必填。旧版本独立部署（< v6.1.1）用 `scripts/query-kg.py` SDK 兜底。

详见 [相关命令索引](./references/related-commands.md)。

## 12. Best Practices

- **先确认图引擎，再选命令（最重要）**：Neo4j 支持 Cypher；**Lindorm 不支持 Cypher**，`exec-kg-cypher` 固定报 `DPN.Commons.InternalError`。引擎不明时直接问用户（OpenAPI 无查空间引擎的接口），不要默认 Neo4j。完整矩阵见 [图引擎能力矩阵](../graph-engine-capabilities.md)
- **Lindorm 上的 InternalError 不要重试（实测）**：改写语句、降 `Limit`、换标签都无效；**也不要把 Gremlin 语句塞进 `--exec-command` 的 `Query`**（trace f3781307 这两个反模式各浪费一轮）
- **不要尝试 `exec-kg-gremlin`**：`ExecKgGremlin` API 尚未上线，CLI 插件（实测 18 个 KG 命令）无此命令；也不要用 `aliyun dataphin-public --version` 探版本（非法用法，报 `parse failed --version must be assigned with value`）
- **Lindorm 空间的图查询组合**：`search-kg-by-semantic`（自然语言找实体）+ `list-kg-entity`（类型/属性过滤）+ `get-kg-neighbor`（展子图）；确需多跳图计算则引导用户到控制台图谱视图
- **语义搜索仅实体 + body 字段名是 `SearchCommand`（实测）**：`SearchKgBySemantic` 不支持关系搜索（无关系类型过滤参数，`MatchType` 恒为 `Entity`）；要看关系先拿 `ItemId` 再 `get-kg-neighbor`。**接口文档写的 `SearchKgBySemanticCommand` 服务端不认**，传它报 `Dataphin.OpenAPI.BadRequest: Missing required argument: SearchCommand`。`MinSimilarity` 只影响语义路径，全部命中都是 `MatchSource=keyword` 时说明已降级（缺向量模型/属性未开 SemanticEnabled），别反复调阈值
- **CLI 原生优先**：KG API 已注册到 CLI 插件（>= 0.7.1），直接使用 `aliyun dataphin-public exec-kg-cypher` / `get-kg-neighbor`，无需 SDK；`search-kg-by-semantic`（V6.2.3 新增）插件未注册时才退 SDK/工作台工具
- **插件版本前置检查**：命令报 unknown command 时先 `aliyun plugin update`（KG 命令自 0.7.x 注册）
- **`--exec-command` 字段名（实测）**：参数名是 `--exec-command`（不是 `--execute-command`），JSON 内查询字段是 `Query`（不是 `Code`）；写错报 `Error: --exec-command is required`
- **DirectionType 字段名**：`--neighbors-query` 中方向字段是 `DirectionType`（不是 `Direction`），取值 `In` / `Out` / `Both`
- **EntityDataId + EntityType 必填**：get-kg-neighbor 两者均必填；DataId 来自 `list-kg-entity` 的 `EntityList[].EntityId`、`search-kg-by-semantic` 的 `SearchResults[].ItemId`，或（Neo4j）Cypher 的 `NodeList[].DataId`
- **Cypher 只读**：仅支持查询，不支持 `CREATE`/`MERGE`/`DELETE`/`SET` 等写入语句
- **节点必须带类型标签，禁止裸 `MATCH (n)`（重要）**：无标签查询会扫描底层图引擎 Space 全库（实测百万级节点，性能灾难；共享 Space 的测试/POC 环境还会扫到其他空间数据——客户部署要求一个 Space 仅绑定一个知识图谱空间）。所有节点模式（含多跳路径 `(a:TYPE)-[*1..3]->(b:TYPE)` 两端）都要显式指定实体类型标签
- **Limit 控制**：Cypher 查询务必加 `LIMIT`，避免返回数据量过大
- **先定位再遍历**：不知道 DataId 时，先用（Neo4j）Cypher 或（两引擎）`list-kg-entity` / `search-kg-by-semantic` 定位目标实体，再用 get-kg-neighbor 展开
- **Depth 控制**：深度越大返回数据指数增长，建议 ≤ 3
- **RelationTypes 过滤**：邻居遍历时指定 RelationTypes 可大幅减少返回数据量
- **JMESPath 过滤**：CLI 全局参数 `--cli-query` 可直接提取响应字段（如 `Data.NodeList[0].DataId`）
- **大整数 ID**：WorkspaceId 等 ID 用字符串传参
- **独立部署 Endpoint**：`--endpoint dataphin-openapi.<env>.aliyun.com`（不带 `https://` 前缀）；报 `no such host` 先核对环境是不是选错了（异常环境下同一 WorkspaceId 会报 `DPN.Planning.KgWorkspaceNotExists`）
- **旧环境兜底**：独立部署低于 KG OpenAPI 发布版本（< v6.1.1，以 `--help` 显示的 Online version 为准）无 KG OpenAPI，退回 `scripts/query-kg.py` SDK 泛化调用
