---
name: manage-kg-knowledge
description: |
  知识图谱知识数据管理与查询。通过 CLI 原生命令完成：实体与关系的增删改查、批量写入、Cypher 图查询、邻居节点遍历。
  触发场景：知识图谱数据 / 创建实体 / 创建关系 / 批量导入 / Cypher 查询 / 邻居遍历 / 知识数据管理。
---

# 知识图谱知识数据管理（manage-kg-knowledge）

## 1. Scenario Description

数据工程师通过阿里云 CLI 管理知识图谱中的实体和关系数据，包括单条 CRUD、批量写入、Cypher 图查询和邻居节点遍历。

**业务流程：**
```
确认 Schema 就绪 → 创建实体 → 批量导入实体 → 创建关系 → 查询数据 → Cypher 图查询 → 邻居遍历
```

**资源拓扑：**
```
知识图谱空间（Workspace）
├── 实体（Entity）
│   ├── 所属实体类型（EntityType）
│   └── 属性键值对（PropertyList）
├── 关系（Relation）
│   ├── 所属关系类型（RelationType）
│   ├── 起始实体 → 目标实体
│   └── 关系属性键值对
└── 图查询引擎
    ├── Cypher 查询（只读，**仅 Neo4j 引擎**）
    └── 邻居节点遍历（引擎无关）
```

**前置条件：**
- 知识图谱空间已存在且 Schema 已发布到图引擎（`manage-kg-schema` Skill 产出）
- OpTenantId（租户 ID）和 WorkspaceId（空间 ID）已知
- 实体类型和关系类型已在 Schema 中定义
- 写入前已取得目标类型的**主键与必填属性清单**（`export-kg-schema` 中 `isPrimaryKey: true` / `isRequired: true` 的属性）

> **实体/关系 CRUD 引擎无关**：本 Skill 的 12 个知识数据接口在 Neo4j 与 Lindorm 图引擎上用法一致，不需按引擎分叉。**但两处依然受引擎影响**：① 步骤 5 的 Cypher 查询**仅 Neo4j 可用**（Lindorm 报 `DPN.Commons.InternalError`，详见 [图引擎能力矩阵](../graph-engine-capabilities.md) 与 `query-kg` Skill）；② 属性值的可用类型由 Schema 建模时的引擎约束决定（如 Lindorm 无 `DATE`，时间值已存为 ISO 字串）。

> **Schema 面与数据面状态隔离（实测）**：空间 Schema 面处于异常态（如 `RollbackFailed` 发布失败且回滚失败、导入/发布报 `DPN.Planning.KgWorkspaceStatusNotEditable`）**不影响数据面读写**——`create-kg-entity` / `create-kg-relation` / `exec-kg-cypher` / `get-kg-neighbor` / `delete-*` 等基于**已发布版本**的类型定义全部正常。看到 Schema 面报「空间不可编辑」时，不要误判整个空间不可用而放弃数据操作；数据操作仅依赖已发布版本的类型定义。

> **CLI 原生支持**：KG OpenAPI 已正式发布（CLI `--help` 实测显示 Online version: **v6.1.1**，以实际输出为准），并注册到 `aliyun-cli-dataphin-public` 插件（**>= 0.7.1**）。本 Skill 全部使用 CLI 原生命令（kebab-case，如 `create-kg-entity`）。独立部署低于该版本的旧环境未发布 KG OpenAPI，可退回 Python Tea SDK 泛化调用（见 [Python SDK 模板](./references/python-sdk-template.md)）。

## 2. Installation

```bash
# 安装 aliyun CLI（>= 3.4.8）：https://github.com/aliyun/aliyun-cli
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 安装 dataphin-public 插件（KG 命令要求插件 >= 0.7.1）
aliyun plugin install --names aliyun-cli-dataphin-public

# 已安装旧版本时升级
aliyun plugin update

# 验证 KG 命令已注册
aliyun dataphin-public --help | grep -i kg-entity
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

# 检查插件版本（KG 命令要求 >= 0.7.1）
aliyun plugin list | grep dataphin-public
```

**凭证不可打印**：任何时候不得将 AccessKey ID/Secret 输出到终端或日志。

## 5. RAM Policy

本 Skill 涉及的最小 RAM 权限：

```json
{
  "Effect": "Allow",
  "Action": [
    "dataphin:CreateKgEntity",
    "dataphin:UpdateKgEntity",
    "dataphin:DeleteKgEntity",
    "dataphin:GetKgEntity",
    "dataphin:ListKgEntity",
    "dataphin:BatchCreateKgEntity",
    "dataphin:CreateKgRelation",
    "dataphin:UpdateKgRelation",
    "dataphin:DeleteKgRelation",
    "dataphin:GetKgRelation",
    "dataphin:ListKgRelation",
    "dataphin:BatchCreateKgRelation",
    "dataphin:ExecKgCypher",
    "dataphin:GetKgNeighbor"
  ],
  "Resource": "*"
}
```

### Permission Failure Handling

若遇到权限错误（HTTP 403 或 ErrorCode 含 `Forbidden`/`NoPermission`/`Dataphin.KG.NoPermission`），请：
1. 确认 RAM 用户已附加上述策略
2. 确认策略中 Resource 范围覆盖目标租户
3. 确认当前用户在知识图谱空间中具有数据操作权限
4. 联系租户管理员授权

详见 [RAM 策略参考](../../ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation**
> 执行前必须确认以下业务参数：

| 参数 | 含义 | 获取方式 | 必填 |
|------|------|---------|------|
| OpTenantId | 租户 ID | profile 或询问用户 | 是 |
| WorkspaceId | 知识图谱空间 ID | **必须向用户索取**（见下方说明） | 是 |
| EntityType | 实体类型编码 | `export-kg-schema`（manage-kg-schema）| 实体操作 |
| RelationType | 关系类型编码 | `export-kg-schema`（manage-kg-schema）| 关系操作 |
| PropertyList | 属性键值对列表 | 用户指定，Code 必须匹配 Schema 定义 | 写操作 |

> **WorkspaceId 无自助发现途径**：KG OpenAPI **不提供列出 KG 空间的接口**（全部 18 个 KG 命令中无任何 list-workspace 类命令），WorkspaceId 必须向用户索取（32 位小写 hex 字符串，可在控制台知识图谱空间列表页查到）。不要尝试猜命令或翻 help 探索。

> Endpoint 传值**不带 `https://` 前缀**（如 `dataphin-openapi.<env>.aliyun.com`），带前缀会报 DNS 解析错误。

详细 API 入参/出参见 [KG Knowledge API 参数参考](./references/kg-knowledge-api-params.md)。

## 7. Observability

本子 Skill 的 session-id **继承自父 Skill `alibabacloud-dataphin-skills`**，不重新生成。

所有 CLI 命令携带：
```
--user-agent AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}
```

其中 `{SESSION_ID}` 为父 Skill 生成的 32 字符小写十六进制字符串。

## 8. Core Workflow

### 步骤 1：创建实体

#### HITL 确认（写操作）

执行前确认：
- 实体类型编码（必须在 Schema 中已定义）
- 属性键值对（Code 必须匹配 Schema 属性定义）
- 影响范围：在图引擎中新增一条实体记录

> **🚨 先取必填属性清单，再拼 PropertyList（实测高频报错）**：缺一个必填属性就报 400 `DPN.Planning.KgEntityParamInvalid: Knowledge graph entity parameter is invalid: 必填属性 [xxx] 不能为空`（trace f3781307 连碰 5 次，每次差一个字段）。正确做法：**写入前先 `export-kg-schema` 拿该实体类型的属性清单**，按 `isPrimaryKey: true` 与 `isRequired: true` 逐项补齐后一次提交，不要“报错一个补一个”地试。`useSysPk: true` 的类型不需传主键（系统生成 `_sys_id`），但其他必填属性仍要传全。

**确认后执行：**

```bash
aliyun dataphin-public create-kg-entity \
  --op-tenant-id {OpTenantId} \
  --workspace-id "{WorkspaceId}" \
  --create-command '{
    "EntityType": "COMPANY",
    "PropertyList": [
      {"Code": "name", "Value": "阿里巴巴集团"},
      {"Code": "industry", "Value": "互联网"},
      {"Code": "founded_year", "Value": "1999"}
    ]
  }' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}"
```

> **注意**：KG 写操作的请求体标志不是通用的 `--body`，而是对应的命令对象标志（`--create-command` / `--update-command` / `--exec-command`），否则报缺参错误。

**响应处理：**
- 提取 `CreateResult.EntityId`（实测为 UUID 字符串），后续创建关系时引用

### 步骤 2：批量创建实体

```bash
aliyun dataphin-public batch-create-kg-entity \
  --op-tenant-id {OpTenantId} \
  --workspace-id "{WorkspaceId}" \
  --create-command '{
    "EntityList": [
      {
        "EntityType": "COMPANY",
        "PropertyList": [
          {"Code": "name", "Value": "腾讯"},
          {"Code": "industry", "Value": "互联网"}
        ]
      },
      {
        "EntityType": "COMPANY",
        "PropertyList": [
          {"Code": "name", "Value": "华为"},
          {"Code": "industry", "Value": "通信"}
        ]
      }
    ]
  }' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}"
```

**响应处理：**
- `CreateResult.SuccessCount`：成功数量
- `CreateResult.FailCount`：失败数量
- `CreateResult.SuccessEntityList`：成功创建的实体，每个元素**仅含 `EntityType` 和 `EntityId`，不含 `PropertyList`**

> **注意（EntityId 无法映射回输入）**：`SuccessEntityList` 不返回属性信息，批量创建同一类型的多条实体时，无法从响应直接判断哪个 `EntityId` 对应哪条输入数据（只能靠 `EntityType` 区分不同类型）。若后续需要用 `EntityId` 创建关系，请采用以下任一方式定位：
> - **(a) 唯一业务编码回查（推荐）**：为每条实体设置一个唯一的业务编码属性（如 `tech_code`），创建后用 `list-kg-entity` + `FilterList` 按该编码逐条查回 `EntityId`；
> - **(b) 逐条创建**：改用逐条 `create-kg-entity`，由调用方自行维护「输入顺序 → 返回 EntityId」的映射。

### 步骤 3：查询实体

```bash
# 获取实体详情
aliyun dataphin-public get-kg-entity \
  --op-tenant-id {OpTenantId} \
  --workspace-id "{WorkspaceId}" \
  --entity-type "COMPANY" \
  --entity-id "{EntityId}" \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}"

# 列出实体（带关键词搜索和属性过滤）
aliyun dataphin-public list-kg-entity \
  --op-tenant-id {OpTenantId} \
  --workspace-id "{WorkspaceId}" \
  --entity-type "COMPANY" \
  --list-query '{
    "Keyword": "阿里",
    "FilterList": [
      {"PropertyCode": "industry", "Op": "eq", "Value": "互联网"}
    ],
    "PageNum": 1,
    "PageSize": 20
  }' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}"
```

**查询行为说明：**
- `--entity-type` 必填（避免跨类型全量扫描），且是**扁平参数**——实测把 `EntityType` 写进 `--list-query` JSON 会报 `Error: unknown field: EntityType`；`--list-query` 只放 `Keyword` / `FilterList` / `PageNum` / `PageSize`
- `Keyword` 仅匹配已索引（Indexed=true）的属性，模糊匹配
- `FilterList.Op` 支持：`eq`/`neq`/`contains`/`gt`/`gte`/`lt`/`lte`/`like`，多条件 AND 关系
- 出参（实测）：`PageResult.EntityList[].{EntityId, EntityType, PropertyList[].{Code, DataType, Value}}` + `PageResult.TotalCount`
- `get-kg-entity` / `delete-kg-entity` 同样走扁平参数 `--entity-type` + `--entity-id`（两者均必填，缺则报 `required flags missing`）

### 步骤 4：创建关系

#### HITL 确认（写操作）

执行前确认：
- 关系类型编码、起始实体 ID、目标实体 ID
- 影响范围：在图引擎中新增一条关系记录

> **字段名是 `SourceEntityId` / `TargetEntityId`（实测）**：写成 `SrcEntityId` 会报 `Error: unknown field: SrcEntityId`；也没有 `FromEntityId`/`ToEntityId` 这类别名。

**确认后执行：**

```bash
aliyun dataphin-public create-kg-relation \
  --op-tenant-id {OpTenantId} \
  --workspace-id "{WorkspaceId}" \
  --create-command '{
    "RelationType": "INVEST",
    "SourceEntityId": "{SourceEntityId}",
    "TargetEntityId": "{TargetEntityId}",
    "PropertyList": [
      {"Code": "shareholding_ratio", "Value": "33%"}
    ]
  }' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}"
```

### 步骤 5：Cypher 图查询（仅 Neo4j 引擎空间）

> **❌ Lindorm 图引擎空间不可用**：`exec-kg-cypher` 在 Lindorm 上固定返回 `DPN.Commons.InternalError`（实测），且 Gremlin 对应的 `ExecKgGremlin` API 尚未上线。Lindorm 空间请用 `list-kg-entity`（类型+属性过滤）+ `get-kg-neighbor`（关系网络）+ `search-kg-by-semantic`（自然语言找实体，仅实体）组合代替，详见 [图引擎能力矩阵](../graph-engine-capabilities.md)。

```bash
aliyun dataphin-public exec-kg-cypher \
  --op-tenant-id {OpTenantId} \
  --workspace-id "{WorkspaceId}" \
  --exec-command '{
    "Query": "MATCH (c:COMPANY)-[r:INVEST]->(t:COMPANY) WHERE c.name = '\''阿里巴巴集团'\'' RETURN c, r, t LIMIT 10",
    "Limit": 100
  }' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}"
```

**响应处理（实测字段均在 `Data` 下）：**
- `Data.RowList`：表格结果行（如聚合查询 `count(n)`）
- `Data.NodeList` / `Data.EdgeList`：图结构结果（返回节点/边时）

> **注意**：`exec-kg-cypher` 仅支持查询数据，不支持修改及写入知识图谱。
> **⚠️ 实测已知问题**：`RETURN n` 返回整节点时，节点的 `DataId` 可能为 null；需要拿实体 ID 时改用 `list-kg-entity`（返回 `EntityId`）或在 Cypher 中 RETURN 具体属性。
> **🚨 节点必须带类型标签，禁止裸 `MATCH (n)`**：无标签查询（如 `MATCH (n) RETURN labels(n), count(*)`）会扫描底层图引擎 Space 全库——实测扫到 100+ 种标签、百万级节点，是性能灾难。测试/POC 环境若多个知识图谱空间共享同一 Space，还会扫到其他空间数据（实际客户部署要求**一个 Space 仅绑定一个知识图谱空间**，按规范部署时无跨空间数据问题）。带标签（如 `MATCH (n:COMPANY)`）时按类型精确命中。所有 Cypher 查询的节点模式都必须显式指定本空间 Schema 中定义的实体类型标签。

### 步骤 6：邻居节点遍历

```bash
aliyun dataphin-public get-kg-neighbor \
  --op-tenant-id {OpTenantId} \
  --workspace-id "{WorkspaceId}" \
  --entity-data-id "{EntityId}" \
  --entity-type "COMPANY" \
  --neighbors-query '{"Depth": 1, "DirectionType": "Both"}' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}"
```

**参数说明：**
- `--entity-data-id` / `--entity-type` 均必填
- `--neighbors-query`（可选）：`{Depth: 深度, DirectionType: In/Out/Both, RelationTypes: ["关系类型编码", ...]}`——方向字段名是 **DirectionType**（不是 Direction）

**响应处理：**
- `Data.NodeList`：邻居节点列表
- `Data.EdgeList`：连接关系列表

## 9. Success Verification

1. **实体创建**：`create-kg-entity` 返回 `CreateResult.EntityId`
2. **批量写入**：`batch-create-kg-entity` 返回 `SuccessCount` 等于预期数量，`FailCount` 为 0
3. **关系创建**：`create-kg-relation` 返回 RelationId
4. **查询验证**：`list-kg-entity` / `exec-kg-cypher` 能查到已写入的数据

## 10. Cleanup

如需清理测试数据：

```bash
# 删除关系（需先删关系再删实体）
aliyun dataphin-public delete-kg-relation \
  --op-tenant-id {OpTenantId} --workspace-id "{WorkspaceId}" \
  --relation-type "INVEST" --relation-id "{RelationId}" \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}"

# 删除实体
aliyun dataphin-public delete-kg-entity \
  --op-tenant-id {OpTenantId} --workspace-id "{WorkspaceId}" \
  --entity-type "COMPANY" --entity-id "{EntityId}" \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-knowledge/{SESSION_ID}"
```

## 11. Command Tables

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-kg-entity` | 创建实体 | 写 |
| `update-kg-entity` | 更新实体 | 写 |
| `delete-kg-entity` | 删除实体 | 写（高危） |
| `get-kg-entity` | 获取实体详情 | 读 |
| `list-kg-entity` | 获取实体列表（搜索/过滤） | 读 |
| `batch-create-kg-entity` | 批量创建实体 | 写 |
| `create-kg-relation` | 创建关系 | 写 |
| `update-kg-relation` | 更新关系 | 写 |
| `delete-kg-relation` | 删除关系 | 写（高危） |
| `get-kg-relation` | 获取关系详情 | 读 |
| `list-kg-relation` | 获取关系列表 | 读 |
| `batch-create-kg-relation` | 批量创建关系 | 写 |
| `exec-kg-cypher` | 执行 Cypher 查询（只读） | 读 |
| `get-kg-neighbor` | 获取邻居节点 | 读 |

> 命令已注册到 CLI 插件（>= 0.7.1，`--help` 实测 Online version v6.1.1）。

详见 [相关命令索引](./references/related-commands.md)。

## 12. Best Practices

- **CLI 原生优先**：KG API 已注册到 CLI 插件（>= 0.7.1），直接使用 `aliyun dataphin-public <cmd>`；命令报 unknown command 时先 `aliyun plugin update`
- **CRUD 引擎无关，但 Cypher 仅 Neo4j（重要）**：12 个实体/关系接口在 Neo4j 与 Lindorm 上用法一致；但步骤 5 的 `exec-kg-cypher` 在 Lindorm 空间固定报 `DPN.Commons.InternalError`（不是环境故障，且 `ExecKgGremlin` 尚未上线）——改用 `list-kg-entity` + `get-kg-neighbor` + `search-kg-by-semantic`，详见 [图引擎能力矩阵](../graph-engine-capabilities.md)
- **必填属性先查后写（重要）**：写入前先 `export-kg-schema` 取目标类型的 `isPrimaryKey` / `isRequired` 属性清单并一次补齐；缺字段报 `DPN.Planning.KgEntityParamInvalid: 必填属性 [xxx] 不能为空`，不要逐个报错逐个补（实测一轮重复 5 次）
- **关系字段名（实测）**：`SourceEntityId` / `TargetEntityId`；写成 `SrcEntityId` 报 `unknown field: SrcEntityId`
- **定位参数走扁平 flag（实测）**：`list-kg-entity` / `get-kg-entity` / `delete-kg-entity` 的类型与 ID 用 `--entity-type` / `--entity-id` 扁平传参，写进 `--list-query` 会报 `unknown field: EntityType`；`--list-query` 只放 Keyword/FilterList/分页
- **命令对象标志（重要）**：KG 写操作请求体不是通用 `--body`，而是对应的命令对象标志。映射关系：`create-kg-entity`/`batch-create-kg-entity`/`create-kg-relation`/`batch-create-kg-relation` → `--create-command`；`update-kg-entity`/`update-kg-relation` → `--update-command`；`exec-kg-cypher` → `--exec-command`
- **Schema 先行**：写入数据前必须确保 Schema 已发布到图引擎（`manage-kg-schema` 完成）
- **EntityType/RelationType 必填**：`list-kg-entity` 需 `--entity-type`、`list-kg-relation` 需 `--relation-type`，避免跨类型全量扫描
- **删除顺序**：先删关系，再删实体；删除有关联关系的实体会失败
- **批量操作**：`batch-create-kg-entity`/`batch-create-kg-relation` 支持部分成功，需检查 FailCount
- **批量创建后获取 EntityId**：`SuccessEntityList` 仅含 `EntityType` + `EntityId`，不含 `PropertyList`，同类型多条实体无法从响应映射回输入。如需将 `EntityId` 用于后续操作，建议：(a) 为每条实体设置唯一业务编码属性，创建后用 `list-kg-entity` + `FilterList` 按编码查回；(b) 或改用逐条 `create-kg-entity` 并自行维护映射
- **Cypher 只读**：`exec-kg-cypher` 仅支持查询，不支持写入和修改；`RETURN n` 时节点 `DataId` 可能为 null，取实体 ID 用 `list-kg-entity`（且该命令在两个引擎上都可用）
- **Cypher 节点必须带类型标签，禁止裸 `MATCH (n)`（重要）**：无标签查询会扫描底层图引擎 Space 全库（实测百万级节点，性能灾难；共享 Space 的测试/POC 环境还会扫到其他空间数据——客户部署要求一个 Space 仅绑定一个知识图谱空间）。所有节点模式（含多跳路径两端）都要显式指定实体类型标签
- **Schema 面异常不影响数据面（实测）**：空间处于 `RollbackFailed` 等不可编辑状态时，数据面读写（create/delete/exec-kg-cypher/get-kg-neighbor 等）基于已发布版本类型定义全部正常，不要误判整个空间不可用
- **PropertyList 值类型**：所有 Value 按字符串传入（`"Value": "1999"`），DataType 在 Schema 中定义
- **邻居遍历方向**：`--neighbors-query` 中 `DirectionType` 取值 `In`（入边）/ `Out`（出边）/ `Both`（双向），默认 Both；字段名是 DirectionType 不是 Direction
- **Keyword 搜索**：仅对 `Indexed=true` 的属性生效，模糊匹配
- **Endpoint 格式**：`dataphin-openapi.<env>.aliyun.com`，**不带 `https://` 前缀**
- **字段提取**：可用全局参数 `--cli-query <JMESPath>`（如 `--cli-query 'CreateResult.EntityId'`）直接提取响应字段
- **旧环境兜底**：独立部署低于 KG OpenAPI 发布版本（< v6.1.1，以 `--help` 显示的 Online version 为准）未发布 KG OpenAPI 时，退回 Python Tea SDK `call_api()` 泛化调用，见 [Python SDK 模板](./references/python-sdk-template.md)
