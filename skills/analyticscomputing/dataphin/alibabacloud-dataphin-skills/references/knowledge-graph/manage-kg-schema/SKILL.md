---
name: manage-kg-schema
description: |
  知识图谱本体模型（Schema）管理。通过 CLI 原生命令完成：整体 Schema 的导出（YAML）、导入（YAML）、发布到图引擎并查询发布结果。实体类型/关系类型/属性的增删改通过编辑 Schema YAML 后整体导入实现，不提供细粒度的单类型 CRUD 接口。
  触发场景：知识图谱 Schema / 本体模型 / 实体类型 / 关系类型 / Schema 导入导出 / Schema 发布。
---

# 知识图谱本体模型管理（manage-kg-schema）

## 1. Scenario Description

数据架构师通过阿里云 CLI 管理知识图谱的本体模型（Schema）。当前 KG Schema OpenAPI **仅提供整体 Schema 级别的操作**（导出 / 导入 / 发布），**不提供**实体类型、关系类型的细粒度单独 CRUD 接口。因此新增 / 修改 / 删除实体类型、关系类型、属性，均通过「导出 YAML → 本地编辑 → 整体导入 → 发布」的流程完成。

**业务流程：**
```
导出当前 Schema（基线）→ 本地编辑 YAML（增删改类型/属性）→ 整体导入 Schema → 发布 Schema → 查询发布结果
```

**资源拓扑：**
```
知识图谱空间（Workspace）
├── 实体类型（EntityType）
│   ├── 属性定义（Properties）
│   └── 继承关系（ParentTypeId）
├── 关系类型（RelationType）
│   ├── 起始/目标实体类型
│   ├── 基数（Cardinality）
│   └── 关系属性
├── Schema 版本
│   ├── 草稿态（Draft）
│   └── 已发布版本（Published）
└── 发布任务（PublishTask）
    ├── 四项校验（连接/完整性/兼容性/偏离）
    └── 数据调整策略（BackfillDefault）
```

**前置条件：**
- 知识图谱空间（Workspace）已存在，当前用户有空间管理权限
- OpTenantId（租户 ID）已知

> **CLI 原生支持**：KG OpenAPI 已正式发布（CLI `--help` 实测显示 Online version: **v6.1.1**，以 `aliyun dataphin-public export-kg-schema --help` 实际输出为准），并注册到 `aliyun-cli-dataphin-public` 插件（**>= 0.7.1**）。本 Skill 全部使用 CLI 原生命令 `export-kg-schema` / `import-kg-schema` / `publish-kg-schema` / `get-kg-schema-publish-result`。独立部署低于该版本（< v6.1.1）的旧环境未发布 KG OpenAPI，可退回 Python Tea SDK 泛化调用（辅助脚本 `scripts/export-schema.py` / `scripts/import-schema.py`）。
>
> **重要（能力边界）**：当前 KG Schema OpenAPI **仅支持整体 Schema 操作**——导出、导入、发布及查询发布结果。**不存在** `CreateKgEntityType` / `UpdateKgEntityType` / `DeleteKgEntityType` / `CreateKgRelationType` 等细粒度单类型 CRUD 接口。所有类型/属性的增删改，请编辑导出的 YAML 后整体重新导入。

> **🚨 建模前先确认图引擎**：导出/导入/发布这 4 个接口本身引擎无关，**但 YAML 里的 `dataType` 与业务识别规则随引擎变化**（Lindorm 图引擎自 V6.2.3 支持）：
>
> | 建模项 | Neo4j | Lindorm 图引擎 |
> |---|---|---|
> | 日期/时间 `DATE` `TIMESTAMP` `DURATION` | ✅ | ❌ 不支持 → 用 `STRING` 存 ISO 8601 字串 |
> | 多值 | `LIST` ✅ / `SET` ❌ | `LIST` ❌ / **`SET` ✅**（V6.2.3 新增） |
> | 嵌套 `EMBEDDED` / `MAP<K,V>` | ✅ | ❌ 不支持 → 用 `STRING` 存 JSON 文本 |
> | `UNKNOWN`（AI 抽取待确认） | ✅ | ❌ 不支持 |
> | `GEOPOINT` | ✅ Point | ✅（底层落 String） |
> | 业务识别规则 | 含编辑距离、时间类规则 | ❌ 无编辑距离、无时间类规则（其余精确/忽略大小写/包含/等于/数值/语义相似度均支持） |
>
> 完整类型映射表与替代写法见 [图引擎能力矩阵](../graph-engine-capabilities.md)。**向 Lindorm 空间导入含不支持类型的 YAML 会在导入/发布阶段失败或被静默降级，请在编辑阶段就按引擎裁剪。**

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

# 安装 Python 依赖（YAML 预校验脚本需要 pyyaml；SDK 兜底脚本另需 tea-openapi）
pip3 install pyyaml

# 验证：KG Schema 命令已注册
aliyun dataphin-public export-kg-schema --help
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
aliyun dataphin-public export-kg-schema --help
```

**凭证不可打印**：任何时候不得将 AccessKey ID/Secret 输出到终端或日志。

## 5. RAM Policy

本 Skill 涉及的最小 RAM 权限：

```json
{
  "Effect": "Allow",
  "Action": [
    "dataphin:ExportKgSchema",
    "dataphin:ImportKgSchema",
    "dataphin:PublishKgSchema",
    "dataphin:GetKgSchemaPublishResult"
  ],
  "Resource": "*"
}
```

### Permission Failure Handling

若遇到权限错误（HTTP 403 或 ErrorCode 含 `Forbidden`/`NoPermission`/`Dataphin.KG.NoPermission`），请：
1. 确认 RAM 用户已附加上述策略
2. 确认策略中 Resource 范围覆盖目标租户
3. 确认当前用户具有知识图谱空间的管理权限
4. 联系租户管理员授权

详见 [RAM 策略参考](../../ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation**
> 执行前必须确认以下业务参数：

| 参数 | CLI 标志 | 含义 | 获取方式 | 必填 |
|------|---------|------|---------|------|
| **图引擎** | （不是 CLI 参数） | 空间绑定的引擎：`Neo4j` / `Lindorm` | **向用户确认**（决定 YAML 里可用的 `dataType`） | **是（编辑 YAML 前置）** |
| OpTenantId | `--op-tenant-id` | 租户 ID | profile 或询问用户 | 是 |
| WorkspaceId | `--workspace-id` | 知识图谱空间 ID | **必须向用户索取**（见下方说明） | 是 |
| Schema YAML 内容 | `--import-command` 的 `Content` | 编辑后的完整本体模型 | 导出基线后本地编辑 | 导入操作 |
| MergeStrategy | `--import-command` 的 `MergeStrategy` | 导入合并策略 `Replace`/`Merge` | 用户指定 | 导入操作 |
| Description | `--publish-command` 的 `Description` | 发布备注 | 用户指定 | 发布操作 |

> **WorkspaceId 无自助发现途径**：KG OpenAPI **不提供列出 KG 空间的接口**（全部 18 个 KG 命令中无任何 list-workspace 类命令），WorkspaceId 必须向用户索取（32 位小写 hex 字符串，可在控制台知识图谱空间列表页查到）。不要尝试猜命令或翻 help 探索。

详细 API 入参/出参见 [KG Schema API 参数参考](./references/kg-schema-api-params.md)。

## 7. Observability

本子 Skill 的 session-id **继承自父 Skill `alibabacloud-dataphin-skills`**，不重新生成。

所有 CLI 命令携带：
```
--user-agent AlibabaCloud-Agent-Skills/manage-kg-schema/{SESSION_ID}
```

其中 `{SESSION_ID}` 为父 Skill 生成的 32 字符小写十六进制字符串。

## 8. Core Workflow

> **能力边界（务必先读）**：KG Schema OpenAPI **仅支持整体 Schema 操作**——`export-kg-schema`（导出）、`import-kg-schema`（导入）、`publish-kg-schema`（发布）、`get-kg-schema-publish-result`（查询发布结果）。**不存在** `CreateKgEntityType` / `UpdateKgEntityType` / `DeleteKgEntityType` / `CreateKgRelationType` 等细粒度单类型 CRUD 接口。新增 / 修改 / 删除实体类型、关系类型、属性，统一通过「**导出 YAML → 本地编辑 → 整体导入 → 发布**」完成。

### 步骤 1：导出当前 Schema（基线）

```bash
# 导出 YAML 并直接提取 Schema 内容存为基线文件
aliyun dataphin-public export-kg-schema \
  --op-tenant-id "{OpTenantId}" \
  --workspace-id "{WorkspaceId}" \
  --output-format yaml \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-schema/{SESSION_ID}" \
  --cli-query 'SchemaInfo.Content'
```

**可选参数：**
- `--output-format`：`yaml`（默认）/ `json`
- `--version-id`：空或 `-1` 返回草稿态；`0` 返回最新已发布版本；正整数返回指定版本

**响应处理：**
- Schema 内容位于 **`SchemaInfo.Content`**（字符串），输出格式位于 `SchemaInfo.OutputFormat`
- 用 `--cli-query 'SchemaInfo.Content'` 可直接提取内容（输出为 JSON 引号包裹的字符串，需反序列化：`python3 -c "import json,sys; print(json.load(sys.stdin))" < raw.txt > schema.yaml`）
- 响应不含 `VersionId`（版本号通过 `get-kg-schema-publish-result` 获取）

将导出的 YAML 保存为本地文件（如 `schema.yaml`）作为编辑基线。若空间为空、首次建模，可跳过导出直接从零编写 YAML。

### 步骤 2：本地编辑并预校验 YAML

在导出的 YAML 上直接增删改实体类型 / 关系类型 / 属性——**这是唯一的类型级变更方式**（无单类型 CRUD API）：
- **新增**类型/属性：在 `entityTypes` / `relationTypes` / `properties` 下追加条目
- **修改**类型/属性：直接改对应字段值
- **删除**类型/属性：从 YAML 移除对应条目，随后以 `Replace` 策略导入（见步骤 3）

编辑完成后运行 `scripts/validate-schema.py` 预校验，提前发现常见错误：

```bash
# 仅校验
python3 alibabacloud-dataphin-skills/references/knowledge-graph/manage-kg-schema/scripts/validate-schema.py <yaml_file>

# 自动修复可处理的问题（dataType 大小写、补充缺失 boolean 字段等）：
python3 alibabacloud-dataphin-skills/references/knowledge-graph/manage-kg-schema/scripts/validate-schema.py <yaml_file> --fix
```

校验规则覆盖：
- 实体/属性/关系编码格式
- 每个实体至少一个 `isPrimaryKey: true`（useSysPk=false 时）
- 每个实体至少一个 `isUsedShow: true`
- dataType 全大写
- cardinalType 合法值
- 属性/关系引用的实体存在性
- **唯一性**：实体/关系的编码与名称各自空间内唯一，且编码与名称均**跨类型（实体↔关系）唯一**；属性编码/名称在同一类型内唯一

**YAML Schema 格式要点：**

| 层级 | 关键字段 | 说明 |
|------|----------|------|
| 顶层 | `name`, `description`, `workspaceId`, `entityTypes`, `relationTypes` | 空间标识用 `workspaceId` |
| 实体类型 | `code`, `name`, `description`, `useSysPk`, `icon`, `properties` | `code` 大写字母开头、**仅含字母/数字（不含下划线）**、2-64 字符；`useSysPk` 控制系统/业务主键 |
| 关系类型 | `code`, `name`, `sourceEntityCode`, `targetEntityCode`, `hasDirection`, `cardinalType`, `properties` | `code` 大写开头、**仅含大写字母/数字/下划线（不含小写，SCREAMING_SNAKE）**，如 `POC_EQUITY_INVESTMENT`；`cardinalType` 取值 `MULTI_TO_MULTI` / `ONE_TO_MANY` 等 |
| 属性 | `code`, `name`, `dataType`, `isPrimaryKey`, `isRequired`, `isIndexed`, `isUsedShow`, `isSemanticEnabled`, `defaultValue` | `dataType` 全大写（`STRING`/`INTEGER`/`FLOAT`/`DATE` 等）；每个实体至少一个 `isPrimaryKey: true` 和一个 `isUsedShow: true`；`isSemanticEnabled: true` 开启该属性的语义检索（见下方专节） |

> **`isUsedShow`** 标记用于展示的属性（每个实体类型必须至少有一个）。`useSysPk: true` 时使用系统主键，所有属性 `isPrimaryKey` 为 false。

#### 按图引擎裁剪 `dataType`（Lindorm 空间必看）

| 意图 | Neo4j 写法 | Lindorm 写法 |
|---|---|---|
| 注册日期 / 创建时间 | `dataType: DATE` / `TIMESTAMP` | `dataType: STRING`（值存 `2024-01-28` / `2024-01-28T14:30:00Z`） |
| 标签、别名等多值 | `dataType: LIST` | `dataType: SET` |
| 地址、扩展字段等嵌套对象 | `dataType: EMBEDDED` / `MAP` | `dataType: STRING`（存 JSON 文本） |
| 时长 | `dataType: DURATION` | `dataType: INTEGER`（存秒数）或 `STRING`（存 ISO Duration） |
| AI 抽取待定类型 | `dataType: UNKNOWN` | `dataType: STRING` |

两引擎均不支持：`DECIMAL` / `BIGINTEGER` / `DATETIMERANGE`（高精度数值用 `STRING` 存，时间区间拆两个字段）。完整矩阵见 [图引擎能力矩阵](../graph-engine-capabilities.md)。

> **业务识别规则（实体消歧）也随引擎**：Lindorm 不支持**编辑距离**与**时间类型规则**（控制台选项隐藏）。需要“名称近似去重”时，在 Lindorm 空间改用语义相似度 / 忽略大小写 / 包含策略（识别规则本身在控制台配置，OpenAPI 不提供规则管理接口）。

#### 开启语义检索（isSemanticEnabled，引擎无关）

语义检索（`SearchKgBySemantic` 的语义路径）的开启方式是**属性层开关**：在实体/关系属性上置 `isSemanticEnabled: true`，导入并发布后平台**自动**创建向量索引（Neo4j 上自动执行 `CREATE VECTOR INDEX ... ON (n.__system_kg_embedding__<prop>__)`）。**不需要也不能用 Cypher 手建向量索引**（`exec-kg-cypher` 只读，CREATE 会被拒）。

> **Neo4j 版本门槛 5.11+（trace 72c13131 实测）**：`CREATE VECTOR INDEX` 是 Neo4j 5.11+ 语法，低版本实例发布带语义属性的 Schema 必失败，发布结果日志里报 `Invalid input 'VECTOR': expected "(", "allShortestPaths" or "shortestPath"`。这是**引擎版本限制不是操作错误**，重试无效；正解是升级 Neo4j 到 5.11+，或由管理员确认实例支持向量索引。详见 [图引擎能力矩阵](../graph-engine-capabilities.md) §语义检索开启方式与向量索引。

**YAML 示例片段：**

```yaml
name: 我的知识图谱
description: 示例 Schema
workspaceId: "{WorkspaceId}"
entityTypes:
- code: COMPANY
  name: 公司
  useSysPk: false
  description: 企业实体
  properties:
  - code: name
    name: 公司名称
    dataType: STRING
    isPrimaryKey: true
    isRequired: true
    isIndexed: true
    isUsedShow: true
    defaultValue: ''
  - code: industry
    name: 行业
    dataType: STRING
    isPrimaryKey: false
    isRequired: false
    isIndexed: false
    isUsedShow: false
    defaultValue: ''
relationTypes: []
```

### 步骤 3：导入 Schema（YAML）

#### 前置检查：空间状态必须可编辑

导入前先跑 `get-kg-schema-publish-result`（见步骤 5，不带 `--version-id` 返回最近一次发布记录）检查空间状态：若 `Data.Status` 为 `RollbackFailed`（发布失败且回滚失败），空间处于不可编辑状态，`import-kg-schema` / `publish-kg-schema` 均会返回 400 `DPN.Planning.KgWorkspaceStatusNotEditable`（「知识图谱空间处于不可编辑状态:ROLLBACK_FAILED」）。**此状态 OpenAPI 侧无任何恢复/重置命令，请勿重试，唯一出路是到 Dataphin 控制台人工恢复该空间**。

#### HITL 确认（写操作 / 高危）

执行前确认：
- Schema YAML 内容来源
- 合并策略：Replace（替换）/ Merge（合并）
- 影响范围：Replace 会删除空间中 YAML 未包含的类型（**删除类型即通过此方式**：从 YAML 移除后 Replace 导入）
- **Merge 不删除**：`Merge` 只新增/更新，**不会删除** YAML 中未列出的已有类型（即使响应/日志显示"已删除"，草稿态仍保留）。**需删除已有类型时必须用 Replace。**

**确认后执行：**

```bash
# YAML 内容含换行/引号，建议用 python3 组装 ImportCommand JSON 再传入
python3 -c "
import json
content = open('schema.yaml').read()
cmd = {'Content': content, 'InputFormat': 'yaml', 'MergeStrategy': 'Merge'}
open('import-cmd.json', 'w').write(json.dumps(cmd, ensure_ascii=False))
"

aliyun dataphin-public import-kg-schema \
  --op-tenant-id "{OpTenantId}" \
  --workspace-id "{WorkspaceId}" \
  --import-command "$(cat import-cmd.json)" \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-schema/{SESSION_ID}"
```

> **字段名注意**：`--import-command` JSON 结构为 `{Content, InputFormat, MergeStrategy}`——格式字段名是 **`InputFormat`**（取值 `yaml`/`json`），不是 `Format`。

**响应处理：**
- `ImportResult.EntityTypeCount` / `RelationTypeCount`：**计数不可信，不可作为导入验证依据**——实测以 Replace 导入 7 实体/9 关系的基线，响应却返回 9/10（导入前草稿态的计数），Merge 场景同样不可信。唯一可信验证是导入/发布后 `export-kg-schema` 核对类型清单
- 导入仅写入草稿态；须经步骤 4 发布后才在图引擎生效

### 步骤 4：发布 Schema

#### HITL 确认（写操作 / 高危 / 异步）

执行前确认：
- 发布备注描述
- 是否有破坏性变更（如非必填→必填）需要数据调整策略
- 影响范围：将草稿态 Schema 发布为正式版本并同步到图引擎

**确认后执行：**

```bash
aliyun dataphin-public publish-kg-schema \
  --op-tenant-id "{OpTenantId}" \
  --workspace-id "{WorkspaceId}" \
  --publish-command '{
    "Description": "新增公司实体类型及投资关系类型",
    "DataAdjustmentPolicies": []
  }' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-schema/{SESSION_ID}"
```

**响应处理：**
- 提取 `Data.VersionId`（预期发布后的最新模型版本号），用于步骤 5 查询发布结果
- **返回 ok 只是受理成功**：向量索引创建等实际执行结果必须到步骤 5 复核（trace 72c13131 实测：publish 返回成功，但发布结果里向量索引创建失败），不要凭发布返回 ok 就宣布成功

### 步骤 5：查询发布结果

```bash
# 不带 --version-id 时返回最近一次发布记录
aliyun dataphin-public get-kg-schema-publish-result \
  --op-tenant-id "{OpTenantId}" \
  --workspace-id "{WorkspaceId}" \
  --version-id {VersionId} \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-schema/{SESSION_ID}"
```

**响应处理：**
- `Data.Status`：`Publishing`（执行中）/ `Published`（成功）/ `Partial`（部分完成）/ `Failed`（失败）/ `RollbackFailed`（**发布失败且回滚失败**——空间进入不可编辑状态，后续 `import-kg-schema` / `publish-kg-schema` 均报 400 `DPN.Planning.KgWorkspaceStatusNotEditable`）
- `Data.Content`：发布过程日志（含各阶段时间戳与校验结果）；含 `isSemanticEnabled` 属性时重点看向量索引创建记录——出现「属性新增向量索引：X 失败」+ `Invalid input 'VECTOR'` 即 Neo4j 版本 < 5.11（见步骤 2 专节，不要重试）
- `Data.VersionId`：本次发布的版本号
- 如为 Publishing 状态，间隔 5 秒后重新查询，直到终态
- 如为 `RollbackFailed`：**不要重试导入/发布**——OpenAPI 侧无恢复/重置命令，必须到 Dataphin 控制台人工恢复空间后再继续

### 兜底：旧版本独立部署（SDK 泛化调用）

独立部署低于 KG OpenAPI 发布版本（< v6.1.1）时，使用辅助脚本（Python Tea SDK `call_api()`）：

```bash
pip3 install pyyaml alibabacloud-tea-openapi alibabacloud-tea-util
export ALIBABA_CLOUD_ACCESS_KEY_ID=... ALIBABA_CLOUD_ACCESS_KEY_SECRET=...
export DATAPHIN_ENDPOINT={endpoint} DATAPHIN_TENANT_ID={OpTenantId} DATAPHIN_WORKSPACE_ID={WorkspaceId}

# 只读导出基线（--output 存文件；独立部署自签证书加 --ignore-ssl）
python3 scripts/export-schema.py --ignore-ssl --output schema.yaml

# 端到端导入（本地校验 → 导出基线 → 导入 → 验证 → 发布 → 轮询）
python3 scripts/import-schema.py <yaml_file> --ignore-ssl [--skip-publish] [--merge-strategy Merge]
```

> SDK 调用细节见 [Python SDK 模板](./references/python-sdk-template.md) 与 [scripts/README.md](./scripts/README.md)。

## 9. Success Verification

1. **Schema 内容**：`export-kg-schema` 返回的 `SchemaInfo.Content` 含预期的实体类型和关系类型
2. **发布成功**：`get-kg-schema-publish-result` 返回 `Data.Status: Published`
3. **发布日志**：`Data.Content` 日志显示各阶段（版本快照/类型处理）均完成、无报错
4. **语义检索（若开启）**：`Data.Content` 中向量索引创建无失败记录；可再用 `SearchKgBySemantic` 验证 `MatchSource` 含 `semantic`/`both`（全为 `keyword` 说明语义路径未生效）

## 10. Cleanup

无细粒度删除接口。清理某个实体类型/关系类型的方式：**从 YAML 中移除对应条目，再以 `Replace` 策略整体导入并发布**：

```bash
# 1. 导出当前 Schema 作为基线
aliyun dataphin-public export-kg-schema \
  --op-tenant-id "{OpTenantId}" --workspace-id "{WorkspaceId}" \
  --output-format yaml \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-schema/{SESSION_ID}" \
  --cli-query 'SchemaInfo.Content'

# 2. 本地编辑 YAML，删除不需要的 entityTypes / relationTypes 条目
#    （删除实体类型前，需一并删除 YAML 中引用该类型的所有关系类型）

# 3. 以 Replace 策略整体导入（Replace 会删除空间中 YAML 未包含的类型）
aliyun dataphin-public import-kg-schema \
  --op-tenant-id "{OpTenantId}" --workspace-id "{WorkspaceId}" \
  --import-command '{"Content": "...(移除目标类型后的 YAML)...", "InputFormat": "yaml", "MergeStrategy": "Replace"}' \
  --profile {profile} --endpoint {endpoint} \
  --user-agent "AlibabaCloud-Agent-Skills/manage-kg-schema/{SESSION_ID}"

# 4. 发布使删除生效（见步骤 4）
```

## 11. Command Tables

| CLI 命令 | 用途 | 类型 | 关键参数 |
|------|------|------|----------|
| `export-kg-schema` | 导出整体 Schema（YAML/JSON） | 读 | `--output-format`、`--version-id` |
| `import-kg-schema` | 导入整体 Schema | 写（高危） | `--import-command`（JSON：`{Content, InputFormat, MergeStrategy}`） |
| `publish-kg-schema` | 发布 Schema（异步） | 写（高危） | `--publish-command`（JSON：`{Description, DataAdjustmentPolicies}`） |
| `get-kg-schema-publish-result` | 查询发布结果 | 读 | `--version-id`（空=最近一次） |

> KG Schema OpenAPI **仅提供以上 4 个整体 Schema 命令**，无实体类型/关系类型的细粒度 CRUD 命令。命令已注册到 CLI 插件（>= 0.7.1，`--help` 实测 Online version v6.1.1）。

详见 [相关命令索引](./references/related-commands.md)。

## 12. Best Practices

- **仅整体 Schema 操作（重要）**：无 `CreateKgEntityType` 等细粒度单类型 API。类型/属性的增删改一律「导出 YAML → 编辑 → 整体导入 → 发布」；删除类型用 `Replace` 策略导入移除了该类型的 YAML
- **先确认图引擎再编辑 YAML（重要）**：`dataType` 可用集合随引擎变化——Lindorm 不支持 `DATE`/`TIMESTAMP`/`LIST`/`DURATION`/`EMBEDDED`/`MAP`/`UNKNOWN`（时间类改 `STRING` 存 ISO 字串，多值改 `SET`，嵌套改 `STRING` 存 JSON），而 `SET` 仅 Lindorm 支持。引擎不明时先问用户，详见 [图引擎能力矩阵](../graph-engine-capabilities.md)
- **业务识别规则的引擎差异**：Lindorm 无编辑距离与时间类规则，近似去重改用语义相似度/忽略大小写/包含（规则在控制台配置，OpenAPI 无规则管理接口）
- **CLI 原生优先**：KG API 已注册到 CLI 插件（>= 0.7.1），直接使用 `aliyun dataphin-public <cmd>`；命令报 unknown command 时先 `aliyun plugin update`
- **InputFormat 字段名（重要）**：`--import-command` JSON 的格式字段是 `InputFormat`（不是 `Format`），取值 `yaml`/`json`
- **YAML 传参用文件组装**：YAML 内容含换行/引号，直接内联 shell 易转义出错，建议用 python3 组装 ImportCommand JSON 文件后 `"$(cat import-cmd.json)"` 传入
- **编码唯一性**：EntityCode / RelationCode 在空间内唯一，编辑 YAML 时保证不重复
- **导入 YAML 必填字段**：每个属性必须包含 `code`/`name`/`dataType`/`isPrimaryKey`/`isRequired`/`isIndexed`/`isUsedShow`/`defaultValue`；每个实体至少一个 `isPrimaryKey: true` 和一个 `isUsedShow: true`
- **dataType 全大写**：`STRING` / `INTEGER` / `FLOAT` / `BOOLEAN` / `DATE` / `TIMESTAMP` / `DECIMAL`（具体可用范围按图引擎裁剪，见上文）
- **useSysPk**：实体级别 `useSysPk: true` 表示系统自动生成主键（此时所有属性 `isPrimaryKey` 为 false）；`false` 表示业务主键模式
- **cardinalType 枚举**：`MULTI_TO_MULTI` / `ONE_TO_MANY` / `ONE_TO_ONE`（关系基数）
- **导入策略选择**：`Replace`（完整替换，慎用）vs `Merge`（增量合并，推荐日常使用）
- **Merge 删除语义（重要）**：`Merge` 只做新增/更新，**不会删除** YAML 中未列出的已有类型——实测即使 Import 响应报 count 减少、发布日志写"处理被删除…完成"，草稿态实际仍保留原类型。**如需删除已有类型，必须改用 `Replace` 策略（从 YAML 移除该类型后 Replace 导入并发布）。**
- **ImportResult 计数不可信（重要）**：`ImportResult.EntityTypeCount` / `RelationTypeCount` 在 **Merge / Replace 两种策略下均不可作为验证依据**（实测 Replace 导入返回的是导入前草稿态的计数）。唯一可信验证是导入/发布后 `export-kg-schema` 核对类型清单
- **导入前空间状态前置检查（重要）**：导入/发布前先跑 `get-kg-schema-publish-result` 检查空间状态；遇 400 `DPN.Planning.KgWorkspaceStatusNotEditable`（如 `RollbackFailed` 发布失败且回滚失败）时 **API 侧无解、盲目重试无效**，需到 Dataphin 控制台人工恢复空间。注意：Schema 面不可编辑**不影响**数据面读写（`create-kg-entity` / `exec-kg-cypher` 等基于已发布版本仍正常，见 manage-kg-knowledge）
- **发布是异步的**：`publish-kg-schema` 返回 `Data.VersionId`，需轮询 `get-kg-schema-publish-result` 获取最终状态（`Data.Status`）
- **破坏性变更**：非必填→必填时需提供 `DataAdjustmentPolicies` 中的 `BackFillDefaultValuePolicy` 策略，否则返回 `Dataphin.KG.RequiredDefaultMissing`
- **版本查询**：`export-kg-schema --version-id`：空/`-1`=草稿态、`0`=最新已发布版本、正整数=指定版本
- **大整数 ID**：WorkspaceId 等 ID 用字符串传参
- **独立部署 Endpoint**：`--endpoint dataphin-openapi.<env>.aliyun.com`（不带 `https://` 前缀）
- **旧环境兜底**：独立部署低于 KG OpenAPI 发布版本（< v6.1.1，以 `--help` 显示的 Online version 为准）无 KG OpenAPI，退回 `scripts/export-schema.py` / `scripts/import-schema.py` SDK 泛化调用
