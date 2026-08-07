---
name: update-dataset-schema
description: |-
  更新 Dataphin 非结构化数据集的元数据表结构（加列/改列）。核心约束：**表结构不能在线编辑**——
  正确流程是「即席查询执行 ALTER SQL 改库表 → update-dataset 重新提交表结构 → 回读验证」三段式。
  当用户场景涉及数据集表结构变更（加字段/加向量列/改注释）、"数据集表结构怎么改"、"重新加载表结构"时进入。

  触发词：更新数据集表结构、数据集加列、修改元数据表、加字段、重新加载表结构、ALTER TABLE 数据集、
  update-dataset-schema、表结构变更。

  关键限制：表结构无在线编辑入口，必须 SQL + 重新提交两步走；Milvus 不支持 DDL（仅 PG/Lindorm 适用）；
  已有工作流引用的列禁止删改（只加不减最安全）；写操作前必须 HITL 确认。
---

# 更新数据集表结构（ALTER SQL → 重新提交 schema → 回读验证）

## 1. Scenario Description

数据集的元数据表结构**不能在线编辑**（界面与 OpenAPI 均无直接改列入口）。变更表结构（典型：为多列输出加字段、补 URL 桥接列、加向量列）必须三段式：

1. **即席查询执行数据库 SQL**（`execute-ad-hoc-task`，DATABASE_SQL 类型直连元数据 PG 数据源）改物理表结构；
2. **数据集重新提交表结构**（`update-dataset` 携带与库中一致的完整 TableSchema，等价于界面"重新加载表结构"）；
3. **回读验证**（`get-dataset` / `list-datasets` 核对列清单与物理表一致）。

**Architecture**：`Dataphin Project + Dataset(版本级 TableSchema) + 元数据存储数据源(PostgreSQL) + 即席查询(DATABASE_SQL 通道)`。

**上下游衔接**：常由 `create-unstructured-workflow`（经套件入口路由加载） 的链路改造触发（如 LLM 算子改多列输出需为每个 customOutputColumns 字段加表列）。

## 2. Installation

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```

（详见 [`references/cli-installation-guide.md`](references/cli-installation-guide.md)）

## 3. Environment Variables

**认证信息统一使用阿里云 CLI 配置（profile）：凭证预先通过 `aliyun configure --profile <name>` 配置，本 skill 不直接读取 AK/SK 环境变量或任何本地文件。**

| 配置项 | 必填 | 说明 |
|---|---|---|
| CLI profile | 是 | `aliyun configure list` 中的有效 profile；执行命令时用 `--profile <name>` 指定 |
| endpoint | 独立部署时必填 | 独立部署/POC 环境由父 skill Step 0 配置专用 profile（含 endpoint）并统一透传 |
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
> 2. Configure credentials **outside of this session**
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

**固定参数检查与映射**（三档策略：明确映射直接用 / 环境可推断给候选待确认 / 缺失向用户索要，不猜不编造）：

| 参数 | 必填 | 收集策略 |
|---|---|---|
| 目标数据集 | 是 | 给了名称 → `list-datasets --keyword` 反查；给了 ID → 直接回读 |
| 目标版本/表 | 是 | 从回读的 VersionList 列出候选（版本号+表名）让用户选 |
| 元数据数据源 ID / Schema | 自动 | 从回读的 `MetadataStorageConfig.DataSourceId/ProdSchema` 取，**不询问** |
| 变更内容 | 是 | 用户给出加哪些列（名/类型/注释）；服务于工作流改造时按算子输出字段自动设计待确认 |
| 执行项目 | 是 | 即席查询所在项目（默认数据集所属项目，需用户确认有权限） |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/update-dataset-schema/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public get-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "12345" \
  --user-agent AlibabaCloud-Agent-Skills/update-dataset-schema/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow（三段式）

```bash
TENANT_ID="30001011"
PROJECT_ID="789"
PROFILE="<aliyun configure list 中的有效 profile 名>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/update-dataset-schema/$SESSION_ID"
```

**本 skill 所有 `aliyun` API 命令统一携带 `--profile "$PROFILE"`；独立部署模式下按父 skill Step 0 约定另追加 `--skip-secure-verify`。**

### Step 1 回读现状 + 变更设计稿（⏸ 暂停等用户确认）

```bash
# 回读数据集：拿 MetadataStorageConfig（DataSourceId/ProdSchema/TableName/TableSchema）与 FileId
aliyun dataphin-public list-datasets --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --keyword "<数据集名>" --include-version-list true --page 1 --page-size 10 \
  --profile "$PROFILE" --user-agent "$UA"
```

产出**变更设计稿**并经用户确认：

- 现状列清单 vs 目标列清单 diff（只加不减最安全）；
- 对应 ALTER SQL（如 `ALTER TABLE public.<表名> ADD COLUMN <列> <类型>; COMMENT ON COLUMN ... IS '...';`）；
- 变更后的**完整** `TableSchema.Columns`（含既有列 + 新列，与库中最终结构逐列一致）；
- **前置自查**：该数据集版本被哪些工作流引用（OpenAPI 无引用查询，界面确认或询问用户）——已被引用的列**禁止删改**。

### Step 2 即席查询执行 ALTER SQL（写操作，HITL 确认后执行）

```bash
# DATABASE_SQL 直连元数据 PG 数据源（--data-source-id/--data-source-schema 用 Step 1 回读值）
aliyun dataphin-public execute-ad-hoc-task --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --operator-type DATABASE_SQL \
  --data-source-id "<元数据数据源 ID，字符串>" \
  --data-source-schema "<ProdSchema，如 public>" \
  --code "ALTER TABLE <表名> ADD COLUMN <列名> <类型>;" \
  --profile "$PROFILE" --user-agent "$UA"

# 确认执行成功（TaskStatus=SUCCESS；sub-task-id 从 0 开始）
aliyun dataphin-public get-ad-hoc-task-log --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --task-id "<TaskId>" --sub-task-id 0 --offset 0 \
  --profile "$PROFILE" --user-agent "$UA"

# 可选：反查物理表结构确认列已生效
# --code "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='<schema>' AND table_name='<表名>' ORDER BY ordinal_position"
```

即席查询参数细节（OperatorType 枚举 / 结果格式 / 常见报错）见兄弟 skill `execute-ad-hoc-task`（经套件入口路由加载）。

### Step 3 数据集重新提交表结构（写操作，HITL 确认后执行）

```bash
# update-dataset 携带变更后的完整 TableSchema（等价界面"重新加载表结构"）
# --id/--file-id 必填（FileId 从 Step 1 回读取）；VersionConfig 其余字段保持回读原值
aliyun dataphin-public update-dataset --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --id "<DatasetId>" --file-id "<FileId>" --version "<目标版本，如 V3>" \
  --version-config "$(cat version-config-updated.json)" \
  --profile "$PROFILE" --user-agent "$UA"
```

- `version-config-updated.json` = Step 1 回读的该版本 VersionConfig 原样 + `TableSchema.Columns` 替换为变更后完整列清单（**必须与库中实际结构一致**，含既有列；只传新列会导致 schema 记录与物理表不一致）；
- `MetadataStorageMode` 保持回读原值；FileStorageConfig 原样回填。

### Step 4 回读验证

```bash
aliyun dataphin-public list-datasets --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --keyword "<数据集名>" --include-version-list true --page 1 --page-size 10 \
  --profile "$PROFILE" --user-agent "$UA"
```

核对目标版本 `TableSchema.Columns` 与 Step 2 的物理表结构逐列一致（列名/类型/主键/URL 标记）。

### 执行前确认（写操作必备 / HITL 章节）

> 本 skill 涉及写操作（`execute-ad-hoc-task` 执行 DDL / `update-dataset`），调用方执行前必须二次确认：
> - 即将执行的 ALTER SQL 全文与 update-dataset 入参 JSON（变更设计稿）
> - 影响范围（哪个数据集/版本/物理表；哪些工作流引用了该版本）
> - 是否可回滚（**ALTER TABLE 加列可逆（DROP COLUMN）；删列/改类型高危且可能丢数据**）
> - 替代方案（`--cli-dry-run` 模拟运行 / 只加不减的兼容式变更）
>
> DDL 属数据库层高危操作：**删列、改列类型、改主键必须逐条人工确认**，且先确认无工作流引用该列。

仅当用户明确回复"确认 / yes / 执行"后才发起命令。

## 9. Success Verification

三步法：

1. **DDL 生效**：`get-ad-hoc-task-log` 返回 `TaskStatus: SUCCESS`；information_schema 反查新列存在；
2. **schema 提交**：`update-dataset` 返回 `Code: OK`；
3. **一致性回读**：`list-datasets --include-version-list true` 中目标版本列清单与物理表逐列一致；如服务于工作流改造，回到 `create-unstructured-workflow` 用新列组装并在界面确认算子面板能选到新列。

## 10. Cleanup

本 skill 不产生独立资源。若变更需回退：

```bash
# 回退加列（确认无数据/无引用后，逐条人工确认）
# --code "ALTER TABLE <表名> DROP COLUMN <列名>;"
# 然后按 Step 3 再次 update-dataset 提交回退后的 TableSchema
```

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参；写操作前先 `--cli-dry-run` 验证请求体。
2. **只加不减**是最安全的变更姿势；删列/改类型前必须确认无工作流引用。
3. `update-dataset` 提交的 TableSchema 必须是**完整列清单**且与物理表一致——它是"重新登记"，不是"增量补丁"。
4. 认证只走阿里云 CLI profile（`--profile`），skill 不读取/不传递任何 AK/SK 明文。
5. 「常见坑」每条标来源 `[Agent 自主发现] / [人工注入]`。

### ✗ 平台限制

#### ✗ 表结构无在线编辑入口
- 限制描述：界面与 OpenAPI 均不能直接修改已有元数据表的列，只能"库表 DDL + 重新提交 schema"两步走（本 skill 即此流程）。
- 替代方案：N/A（本 skill 就是替代方案）。

#### ✗ Milvus 不支持 DDL 导入
- 限制描述：Milvus 类型元数据存储无法用本 skill 的 ALTER 流程改结构。
- 替代方案：新建正确 schema 的版本/数据集迁移。

#### ✗ OpenAPI 无下游引用查询
- 限制描述：无法通过 API 查询数据集版本被哪些工作流引用。
- 替代方案：界面「资产中心 → 数据集 → 引用」确认，或向用户求证。

### 常见坑

#### [人工注入] 表结构不能在线编辑，必须两步走
- 现象：直接 `update-dataset` 改 TableSchema 但物理表未变，或在界面找不到编辑列入口。
- 结论：先即席查询 ALTER 物理表，再 update-dataset 重新提交与库中一致的完整 schema；顺序不能反。

#### [人工注入] update-dataset 是"重新登记"不是"增量补丁"
- 现象：只传新增列的 TableSchema，导致数据集 schema 记录丢失既有列。
- 结论：提交的 `TableSchema.Columns` 必须是变更后的完整列清单（回读原值 + 新列）。

#### [人工注入] DATABASE_SQL 必须同时传 data-source-id 与 data-source-schema
- 现象：只传 `--data-source-id` 报参数缺失。
- 结论：PG 类即席查询两参数齐传；取值直接用数据集回读的 `MetadataStorageConfig.DataSourceId/ProdSchema`。

#### [人工注入] 已被工作流引用的列禁止删改
- 现象：删列后引用该列的算子 inputColumn/columnMappings 失配，试运行报错。
- 结论：变更前自查下游引用（界面确认）；原则上只加不减。

#### [Agent 自主发现] 多条 SQL 分号提交会被拆成并行子任务，执行顺序不保证
- 现象：10 条分号分隔的 SQL 一次提交，返回 `SubTaskCount: 10` 并行执行；`COMMENT ON COLUMN summary` 抢在 `ADD COLUMN summary` 之前跑，报 `column does not exist`。
- 结论：**有依赖顺序的 DDL 必须分批串行提交**（先一批 ADD COLUMN，确认全部 SUCCESS 后再一批 COMMENT），或逐条提交；失败子任务单独补跑即可（其余子任务不受影响）。逐子任务查 `get-ad-hoc-task-log` 确认状态，不能只看提交成功。

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
- 即席查询细节：`execute-ad-hoc-task`（经套件入口路由加载）（OperatorType 枚举 / 结果格式 / 常见报错）
- 数据集参数与建表红线：[`../create-dataset/references/dataset-parameters.md`](../create-dataset/references/dataset-parameters.md)
- 下游衔接：`create-unstructured-workflow`（经套件入口路由加载）（多列输出等场景的表列扩展）
- OpenAPI 文档：[ExecuteAdHocTask](https://api.aliyun.com/document/dataphin-public/2023-06-30/ExecuteAdHocTask) / [UpdateDataset](https://api.aliyun.com/document/dataphin-public/2023-06-30/UpdateDataset) / [GetDataset](https://api.aliyun.com/document/dataphin-public/2023-06-30/GetDataset)
