---
name: create-dataset
description: |-
  创建 Dataphin 非结构化数据集（含全生命周期管理）：设计确认 → list-datasets 查重 → create-dataset 创建 → get-dataset 回读验证；
  另覆盖 update-dataset 更新、delete-dataset 删除（高危）。
  当用户场景涉及数据集（Dataset）的创建 / 查询 / 复用 / 更新 / 删除，或为非结构化工作流准备输入输出载体时进入。

  触发词：创建数据集、新建数据集、数据集管理、元数据表、表结构设计、向量表、Milvus 数据集、
  create-dataset、list-datasets、get-dataset、update-dataset、delete-dataset、Dataset。

  关键限制：Scenario/Type/StorageType/MetadataStorageType/ContentType 五字段创建后不可变；同项目数据集名唯一；
  Milvus 必须主键+向量字段齐备；delete-dataset 无回收站且不自查下游引用；写操作前必须 HITL 确认。
---

# 创建 Dataphin 非结构化数据集（设计 → 查重 → 创建 → 回读验证）

## 1. Scenario Description

数据集是 Dataphin 非结构化数据处理的输入输出载体（文件存储 + 元数据表）。本 skill 覆盖数据集全生命周期：

1. **设计确认**：五个不可变字段 + 表 schema 一次定型，经用户确认；
2. **查重复用**：`list-datasets` 按关键词搜索，命中且配置匹配则直接复用；
3. **创建**：`create-dataset` 提交 CreateCommand（含 VersionConfig / TableSchema）；
4. **回读验证**：`get-dataset` 回读 DatasetDTO + VersionList 确认落库正确（下游工作流环境值的唯一来源）；
5. **更新 / 删除**：`update-dataset`（FileId 必填）/ `delete-dataset`（高危，先自查下游引用）。

**Architecture**：`Dataphin Tenant + Project + Dataset(文件存储数据源 OSS/S3 + 元数据存储数据源 PG/Milvus/Lindorm) + DatasetVersion(V1/V2…携带存储配置与表 schema)`。

**典型下游**：创建完数据集后，通常衔接 `create-unstructured-workflow` skill 组装非结构化工作流（工作流 JSON 的环境值从本 skill 的 get-dataset 回读结果取）。

## 2. Installation

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```

（详见 [`references/cli-installation-guide.md`](references/cli-installation-guide.md)）

## 3. Environment Variables

**认证信息统一使用阿里云 CLI 配置（profile）：凭证预先通过 `aliyun configure --profile <name>` 配置，本 skill 不直接读取 AK/SK 环境变量或任何本地文件。**

| 配置项 | 必填 | 说明 |
|---|---|---|
| CLI profile | 是 | `aliyun configure list` 中的有效 profile（AK / STS / RamRoleArn 均可）；执行命令时用 `--profile <name>` 指定，缺省用默认 profile |
| endpoint | 独立部署时必填 | 公共云用默认 endpoint；独立部署/POC 环境由父 skill Step 0 配置专用 profile（含 endpoint）并统一透传 |
| `DATAPHIN_PROFILE` | 否 | 多租户场景下的 dataphin 本地 profile 名（`--dataphin-profile`） |

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

**Pre-check: Aliyun CLI >= 3.4.8 required**
> Run `aliyun version` to verify >= 3.4.8. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [`../../ram-policies.md`](../../ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--op-tenant-id` | 是 | 租户 ID（大整数，shell 变量传递） | — |
| ProjectId | 是 | 项目 ID | — |
| Name | 是 | 数据集名（同项目唯一） | — |
| **五个不可变字段** | 是 | Scenario / Type / StorageType / MetadataStorageType / ContentType（枚举见 [`references/dataset-parameters.md`](references/dataset-parameters.md)） | Scenario=`OFFLINE` |
| 文件存储配置 | Type=FILE/HYBRID 时必填 | DataSourceId / ProdPath / MountPath | — |
| 元数据存储配置 | Type=TABLE/HYBRID 时必填 | DataSourceId / ProdSchema / TableName / TableSchema.Columns | Mode=`CREATE` |
| 表名 | 元数据存储时必填 | 匹配 `^[a-z][a-z0-9_]{0,63}$` | — |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/create-dataset/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public get-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "12345" \
  --user-agent AlibabaCloud-Agent-Skills/create-dataset/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="30001011"
PROJECT_ID="789"
PROFILE="<aliyun configure list 中的有效 profile 名>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/create-dataset/$SESSION_ID"
```

**本 skill 所有 `aliyun` API 命令统一携带 `--profile "$PROFILE"`（认证信息只来自 CLI 配置）；独立部署模式下按父 skill Step 0 约定另追加 `--skip-secure-verify`。**

### Step 1 参数收集与设计确认（⏸ 写操作前必须过这一关）

**先做固定参数检查与映射**——创建数据集依赖一组环境参数，逐项按三档策略处理：用户输入**能明确映射的直接用（反查校验后）；能从环境推断的给候选待确认；都没有的明确向用户索要**，不猜、不编造：

| 固定参数 | 用户输入可映射时 | 信息不全时 |
|---|---|---|
| 文件存储数据源 | 给了名称 → `list-data-source-with-config --keyword` 反查 ID；给了 ID → 直接用 | 列项目内已有数据集在用的存储源作候选，或请用户提供数据源名 |
| 元数据存储数据源 | 同上 | 同上（PG/Milvus 选型一并确认） |
| 生产路径 ProdPath | 给了 `oss://bucket/path/` 全路径 → 拆 bucket 校验与数据源配置一致，取相对路径 | 请用户提供文件存放路径 |
| MountPath | 用户指定 → 直接用 | 按业务名生成 `/mnt/data/<名>` 待确认 |
| 元数据表结构 | 给了字段清单 → 按建表红线校验 | 服务于工作流时按链路算子输出字段自动设计，进设计稿待确认 |
| 五个不可变字段 | 显式给出 → 用 | 按场景推荐默认（OFFLINE/HYBRID/OSS/POSTGRESQL + 按模态定 ContentType）待确认；**REALTIME 场景**已实测支持（STREAM_TABLE + RealtimeMetaTableConfig，见 dataset-parameters §八） |
| 实时元表 MetaTableName（仅 REALTIME） | 给了元表名 → 用 `list-files --category streamMeta` 反查确认存在 | **先告知现实：元表无 skill/OpenAPI 创建能力，只能界面预建**；列出项目内已有元表供用户选，为空则引导用户先去界面建再回来 |

参数全部就位后产出**数据集设计稿**并经用户确认（五个不可变字段建完锁死，错了只能删了重建）：

- 名称（同项目唯一）/ Scenario / Type / StorageType / MetadataStorageType / ContentType；
- 每张表的完整 schema（列名/类型/主键/URL 标记/向量索引配置）；
- 全部枚举与「场景 × 类型 × 存储」组合矩阵、建表红线见 [`references/dataset-parameters.md`](references/dataset-parameters.md)。

**未经用户对设计稿书面确认，不得进入 Step 3 写操作。**

### Step 2 查重复用

```bash
aliyun dataphin-public list-datasets --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --keyword "<业务关键词>" --include-version-list true --page 1 --page-size 10 \
  --profile "$PROFILE" --user-agent "$UA"
```

> ⚠️ 本 skill 命令示例为插件 >= 0.7.0 的展平参数格式；旧版插件是嵌套对象参数（`--dataset-query`/`--create-command`/`--update-command`）。旧写法在新插件下**不报错但被静默忽略**，以 `--help` 实时输出为准。

命中且五个不可变字段与设计稿一致、表 schema 满足需要 → **直接复用**，跳到 Step 4 回读；名称重复但配置不符 → 换名或与用户确认删旧建新。

### Step 3 创建数据集（写操作，HITL 确认后执行）

```bash
# VersionConfig JSON 骨架见 references/dataset-parameters.md §四；先展示给用户确认
aliyun dataphin-public create-dataset --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --name "<数据集名>" --type HYBRID --content-type TEXT --dir-name / --scenario OFFLINE \
  --storage-type OSS --metadata-storage-type POSTGRESQL --version V1 \
  --version-config "$(cat version-config-v1.json)" \
  --profile "$PROFILE" \
  --cli-dry-run          # 先模拟运行验证请求体；用户确认后去掉本行并追加 --user-agent "$UA" 正式执行
```

成功返回 `DatasetId`（业务主键，按字符串记录）。**一次只能建 1 个版本**：多版本多表（如源表/中间表/结果表）需先回读取 `FileId`，再用 Step 5 的 `update-dataset` 逐个追加 V2/V3。

### Step 4 回读验证（必做，无论新建还是复用）

```bash
aliyun dataphin-public get-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "<DatasetId>" \
  --profile "$PROFILE" --user-agent "$UA"
```

核对返回的 DatasetDTO：五字段与设计稿一致、`VersionList[].Id`（datasetVersionId）存在、`TableSchema.Columns` 完整。OpenAPI 直连不跑界面的四阶段校验流水线，**回读即兜底核验**；回读结果是下游工作流环境值的唯一来源。

### Step 5（按需）更新 / 删除

```bash
# 更新/追加版本：--id 与 --file-id 必填（FileId 从 get-dataset 或 list-datasets 回读取），传哪个字段改哪个
aliyun dataphin-public update-dataset --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --id "<DatasetId>" --file-id "<FileId>" --version V2 \
  --version-config "$(cat version-config-v2.json)" \
  --profile "$PROFILE" --user-agent "$UA"

# 删除（高危）：见 §10 Cleanup
```

### 执行前确认（写操作必备 / HITL 章节）

> 本 skill 涉及写操作（`create-dataset` / `update-dataset` / `delete-dataset`），调用方执行前必须二次确认：
> - 即将执行的命令全文（脱敏后）与入参 JSON（设计稿）
> - 影响范围（哪个 tenant / project / 数据集）
> - 是否可回滚（五个不可变字段建后锁死；delete 无回收站）
> - 替代方案（`--cli-dry-run` 模拟运行 / `list-datasets` 只读复用）
>
> `delete-dataset` 为高危操作且 **OpenAPI 不自查下游引用**——删除前必须先确认无工作流引用该数据集版本，并逐次经用户人工确认。

仅当用户明确回复"确认 / yes / 执行"后才发起命令。

## 9. Success Verification

三步法：

1. **同步返回**：`create-dataset` 返回 `Code: OK` + `DatasetId` ≠ 业务完全正确；
2. **list 反查**：`list-datasets` 按名称关键词命中新建数据集；
3. **get 回读**：`get-dataset` 返回的五字段、VersionList、TableSchema 与设计稿逐项一致（含向量列 Dimension、URL 标记、主键标记）。

## 10. Cleanup

```bash
# 删除测试数据集（高危：无回收站、不自查下游引用；先人工确认无工作流引用，逐次经用户确认）
aliyun dataphin-public delete-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "<DatasetId>" \
  --profile "$PROFILE" --user-agent "$UA"
```

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参（JSON 内引号包住），避免 JS 精度截断。
2. 写操作必须执行前 HITL 二次确认；正式执行前先 `--cli-dry-run` 验证请求体。
3. 五个不可变字段设计稿一次定型；建完必 `get-dataset` 回读。
4. 认证只走阿里云 CLI profile（`--profile`），skill 不读取/不传递任何 AK/SK 明文。
5. 「常见坑」每条标来源 `[Agent 自主发现] / [人工注入]`。

### ✗ 平台限制

#### ✗ OpenAPI 未覆盖重命名 / 版本单独删除 / 提交进度查询 / 下游引用查询 / 目录树
- 限制描述：这些能力仅界面（前端内部接口）提供，OpenAPI 只开放 Create/Get/List/Update/Delete 5 个。
- 替代方案：重命名可走 `update-dataset` 的 `Name` 字段；删数据集前的下游引用检查须**人工在界面确认**或询问用户。

#### ✗ 前端提交是异步四阶段校验，OpenAPI 是同步直落
- 限制描述：界面提交有「对象检查→权限检查→提交执行」流水线兜底，OpenAPI 直连不跑这些校验。
- 替代方案：建完必 `get-dataset` 回读逐项核对（§9 第 3 步）。

### 常见坑

#### [人工注入] 五个不可变字段建错只能删了重建
- 现象：想把 POSTGRESQL 改成 MILVUS，`update-dataset` 报错或不生效。
- 结论：`Scenario`/`Type`/`StorageType`/`MetadataStorageType`/`ContentType` 创建后锁死（对应错误码如 `SCENARIO_NOT_ALLOW_MODIFY`）；设计稿必须一次定型并经用户确认。

#### [人工注入] UpdateDataset 的 FileId 必填
- 现象：只改名字也报参数缺失。
- 结论：`UpdateCommand.FileId` 必填（创建时的文件 ID），先 `get-dataset` 回读取。

#### [人工注入] ListDatasets 默认不带版本详情
- 现象：返回的 DatasetDTO 无 VersionList，拿不到 datasetVersionId。
- 结论：加 `IncludeVersionList: true`，或改用 `get-dataset`。

#### [人工注入] Milvus 表结构约束
- 现象：Milvus 数据集提交失败。
- 结论：必须同时有主键字段（仅 INT64/VARCHAR 单选）+ 向量字段（配 `VectorIndexConfig`）；且不支持 DDL 导入。

#### [人工注入] 同名/并发冲突错误码
- 现象：`DATASET_NAME_DUPLICATE` / `DATASET_VERSION_DUPLICATE` / `DATASET_IS_PUBLISHING`。
- 结论：同项目数据集名唯一、同数据集版本号唯一、同一数据集不能并发提交（排他锁）；建前先 `list-datasets` 查重。

#### [Agent 自主发现] 五个命令的 ProjectId 类型不一致
- 现象：`create-dataset`/`update-dataset` 的 `--project-id` 是 String，`get-dataset`/`delete-dataset` 是 Long，`list-datasets` 在 body 内是 integer。
- 结论：生成调用命令时按各命令 `--help` 输出为准，不要复用同一种写法。

#### [Agent 自主发现] ContentType 界面 4 种、API 7 种
- 现象：界面新建只有 TEXT/IMAGE/AUDIO/VIDEO，API 契约还有 GENERAL/TABLE/INDEX。
- 结论：用 API 建 GENERAL 等类型可行（界面建不出来）；建后界面可正常查看。

#### [Agent 自主发现] 插件 0.7.0 参数展平 + 本地 profile 默认值静默覆盖
- 现象：旧版嵌套参数（`--create-command`/`--dataset-query`/`--update-command`）在 >=0.7.0 下不报错但被忽略，缺省值从 `~/.aliyun/dataphin-public/config.json` 本地 profile 填充，ProjectId 可能指向错误项目；旧版插件（0.5.x）则存在 Columns 内嵌 schema 校验 bug（报 `map type value expected`）。
- 结论：先 `aliyun plugin update`；写操作前必跑 `--cli-dry-run` 核对请求体实际取值；参数形态以 `--help` 实时输出为准。

#### [Agent 自主发现] 独立部署环境向量列写法与公共云契约不同
- 现象：独立部署/POC 环境真实数据集的向量列 `Type="vector(1024)"`、`VectorIndexConfig.EmbeddingModel` 填模型**实例 ID**（如 `8762613`）；公共云 API 文档写法是 `FLOAT_VECTOR` + 模型名。
- 结论：建表前先 `list-datasets --include-version-list true` 回读同环境已有数据集的列定义，照环境真实范式填写，不要直接抬文档枚举。

#### [Agent 自主发现] get-dataset 与 create-dataset 权限点不同
- 现象：同一账号 `create/update/list-datasets` 成功，`get-dataset` 却报 `DPN.Filter.NoPermission`（Dataphin 项目 RBAC，非 RAM）。
- 结论：回读受阻时用 `list-datasets --keyword <名> --include-version-list true` 兜底（返回同构 DatasetDTO）；彻底解决需在控制台升级调用账号的项目角色。

#### [Agent 自主发现] 数据源 Type 与数据集存储类型枚举不一致，用错静默空结果
- 现象：Step 1 反查存储数据源时 `list-data-source-with-config --type-list POSTGRESQL` 返回空列表且 `Success=true`；改 `POSTGRE_SQL` 才命中。Kafka 同理：`KAFKA` 查不到，必须用 `KAFKA_9_11`（带版本后缀）。
- 结论：数据源 Type 枚举（`POSTGRE_SQL`/`KAFKA_9_11`）与数据集存储枚举（`POSTGRESQL`/`STREAM_TABLE`）是两套，不可互用；空结果先查枚举拼写。

#### [Agent 自主发现] 502 BadGateway `RPC invoke createDataset failed` 可能已创建成功
- 现象：`create-dataset` 返回 `Dataphin.OpenAPI.BadGateway`（HTTP 502，消息体 `RPC invoke ... createDataset ... failed`）看似失败；改参数重试时改报 `DPN.Resource.DuplicateFileName: 存在同名文件`——回读才发现**首次调用已完整创建（含表结构）**，502 仅是服务端异步 RPC 超时。
- 结论：**502 后禁止直接重试**——先 `list-datasets --include-version-list true` 回读确认实际状态（已存在 → 直接用或按需 update；确不存在 → 才重试）；盲重试会撞同名冲突。附带结论：`varchar(512)`/`int4` 等非 `text` 列型可正常建表，不是 502 原因。

#### [Agent 自主发现] 多环境切换：插件 profile 跳环境污染 + 参数顺序影响 endpoint
- 现象一：在 B 环境调用时显式传了 `--id`/`--project-id`，服务端却报 **A 环境的项目** `not exists`——插件 profile `default` 存的是 A 环境租户/项目，会覆盖命令行参数。
- 现象二：`--profile` 写在 `--endpoint` **之后**时 endpoint 回落到 current profile 的值——实测导致一批查询静默打到另一个环境（返回体 `TenantId` 不对才发现）。
- 结论（多环境操作三条纪律）：① 每环境建独立插件 profile（`~/.aliyun/dataphin-public/config.json` 新增条目），命令带 `--dataphin-profile <env>`；② endpoint 写入主 CLI profile（`~/.aliyun/config.json`）而非依赖命令行顺序；③ **每次只读返回后用响应体里的 `TenantId`/`ProjectId` 交叉核对**（最可靠的串环境检测手段）。

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
- [`references/dataset-parameters.md`](references/dataset-parameters.md)（枚举 / 组合矩阵 / 不可变字段 / 建表红线 / CreateCommand·UpdateCommand 骨架 / DatasetDTO 出参 / **REALTIME 创建实测 §八**）
- 下游衔接：`create-unstructured-workflow`（经套件入口路由加载）（工作流环境值从本 skill 回读结果取）
- OpenAPI 文档：[CreateDataset](https://api.aliyun.com/document/dataphin-public/2023-06-30/CreateDataset) / [GetDataset](https://api.aliyun.com/document/dataphin-public/2023-06-30/GetDataset) / [ListDatasets](https://api.aliyun.com/document/dataphin-public/2023-06-30/ListDatasets) / [UpdateDataset](https://api.aliyun.com/document/dataphin-public/2023-06-30/UpdateDataset) / [DeleteDataset](https://api.aliyun.com/document/dataphin-public/2023-06-30/DeleteDataset)
