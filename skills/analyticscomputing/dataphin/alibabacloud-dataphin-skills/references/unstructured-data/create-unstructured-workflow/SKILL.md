---
name: create-unstructured-workflow
description: |-
  从一句业务需求（如"PPT 按页构建解决方案知识库"）出发，端到端创建 Dataphin 非结构化工作流：
  需求分析 → 算子链路设计 → 数据集设计与创建 → 工作流 JSON 组装 → create-work-flow-by-json 创建 → 输出验证指引。
  当用户场景涉及非结构化数据处理（文档解析 / 图片理解 / 音视频处理 / 知识库构建 / 向量化入库）或数据集增删改查时进入。

  触发词：非结构化工作流、创建工作流、知识库构建、文档解析、向量化、create-work-flow-by-json、unstructured workflow。

  关键限制：**仅支持离线（OFFLINE）**——实时工作流（TaskType=5/REALTIME 数据集）不在范围，Step 1 预检到即告知；仅 BASIC 项目（Env=PROD）；数据集 5 字段建后不可变；LLM/评分/去重算子不吃 URL 需桥接；环境值必须回读禁止编造；写操作前 HITL 确认。
---

# 创建 Dataphin 非结构化工作流（需求 → 数据集 → 工作流 → 验证）

## 1. Scenario Description

用户用一句业务需求触发（例："把 OSS 上的产品 PPT 按页解析，构建可检索的解决方案知识库"），本 skill 自动完成：

1. 需求分析（识别模态 + 格式兼容预检）；
2. 算子链路设计（输出设计稿，**暂停等用户确认**）；
3. 数据集准备（`list-datasets` 搜索复用 → 不存在则 `create-dataset` → `get-dataset` 回读）；
4. 组装工作流 JSON（算子骨架 + 回读环境值 + 业务定制提示词）；
5. `create-work-flow-by-json` 创建（默认测试模式 `TaskType=3 + Submit=false`）;
6. 输出三层验证指引（结构自检 → PipelineId → 界面回显 + 试跑）。

**Architecture**：`Dataphin Tenant + BASIC Project + Dataset(文件存储 OSS + 元数据存储 PG/Milvus) + 非结构化工作流(算子 DAG) + 模型实例(LLM/Embedding)`。

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
| ProjectId | 是 | BASIC 模式项目 ID | — |
| 业务需求描述 | 是 | 一句话业务目标（决定模态与链路） | — |
| 源数据格式 | 是 | 文件扩展名清单（决定格式兼容预检结果） | — |
| 数据集名 / 表名 | 是 | 用户确认（表名须匹配 `^[a-z][a-z0-9_]{0,63}$`） | — |
| TaskName / Directory | 是 | 工作流任务名 / 所属目录 | 测试目录 |
| TaskType / Submit | 否 | 调度类型 / 是否提交 | `3`（手动）/ `false` |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/create-unstructured-workflow/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public list-datasets --op-tenant-id "$TENANT_ID" \
  --dataset-query '{"ProjectId": 123, "Keyword": "知识库", "IncludeVersionList": true, "Page": 1, "PageSize": 10}' \
  --user-agent AlibabaCloud-Agent-Skills/create-unstructured-workflow/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow（六步流程）

```bash
TENANT_ID="30001011"        # 租户 ID
PROJECT_ID="789"            # BASIC 模式项目 ID
PROFILE="<aliyun configure list 中的有效 profile 名>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/create-unstructured-workflow/$SESSION_ID"
```

**本 skill 所有 `aliyun` API 命令统一携带 `--profile "$PROFILE"`（认证信息只来自 CLI 配置）；独立部署模式下按父 skill Step 0 约定另追加 `--skip-secure-verify`。**

**铁律：所有算子配置、字段结构、枚举值只能来自 `references/` 参考文档或 API 实时回读，禁止凭记忆编造。**

### Step 1 需求分析（只读，不调 API）

1. **覆盖边界预检（先于一切，30 秒内给结论）**：出现下列任一信号——用户提“**实时**工作流”/要求 `TaskType=5`，或输入数据集 `Scenario=REALTIME`（元数据为 STREAM_TABLE 实时元表、无 MetadataStorageConfig）——**立即按实时能力边界处置**（见 §12 ✗ 平台限制）：有已有实时工作流可回读作基线 → 可走复刻/变体链路（[`references/realtime-workflow-notes.md`](references/realtime-workflow-notes.md)）；无基线 → 告知超范围引导界面；**禁止**按离线范式出候选链路、**禁止**把 `TaskType=3` 当默认往下引导。可承接的离线子任务（如结果数据集创建）可继续。
2. 从需求识别：**数据模态**（文档/图片/音频/视频/混合）、**源数据格式**（扩展名清单）、**目标产出**（知识库/清洗/打标/向量入库）。
3. 按 [`references/operator-reference.md`](references/operator-reference.md) §支持格式做**格式兼容预检**——特别注意窄格式算子（`video_basic_info` 仅 mp4/mov/m4v、`audio_chunk` 支持面窄、`image_ocr` 仅 jpg/png），不兼容时前置转码算子或提示换链路。
4. 信息不足（模态/格式/产出不明）先问用户，不要猜；但**边界判定不靠提问**——信号已明确时直接给结论。

### Step 2 链路设计（多方案对比 → 设计稿，⏸ 两次暂停等用户确认）

**同一业务场景往往有多种工作流解法**（例：PPT 关键信息提取有文本路线 `ppt_parse+llm` 与视觉路线 `pagetopng+image_understanding`）：

0. 存在 >=2 条可行链路时，先输出**候选方案对比表**（链路 / 优势 / 局限 / 适用条件）⏸ 让用户选定路线，再细化设计；仅一条合理链路时直接出设计稿并说明理由。

选定路线后，按 [`references/workflow-json-spec.md`](references/workflow-json-spec.md) §链路推导规则设计算子链：

1. 逐算子核对 INPUT_COLUMNS（消费什么，TEXT/URL）与 OUTPUT_COLUMNS（产出什么）。
2. 连接判定 = **输出字段 ⊇ 下游输入字段** 且 **内容类型兼容**：LLM 推理/文本质量分/去重类算子**仅读 PG 表文本字段值，不支持 URL 输入**；上游产出 `xxx_url` 时必须桥接（`text_chunking` 调大 chunkSize 优先，`python_executor` 兜底）。
3. **多分支抽取链路提示 filters 分流 [人工注入]**：分类节点（如打标输出 doc_type）后接 N 个按类抽取节点时，若抽取节点不加 `filters` 分流，每条数据会被 N 个节点全量跑一遍（模型调用费 ×N，实测外部案例 6 分支全量跑）——设计时应提示用户按分类列加 filters；⚠️ filters 结构尚无实测验证过的骨架，优先引导界面配置或回读已有带 filters 的工作流作基线。
4. 模型按 operator-reference §推荐模型选型；`modelId` 留待 Step 4 从实际环境取。
5. 输出设计稿（需求理解 / 算子链 + 每条连线的字段契约 / 数据集五不可变字段 + 表 schema / 模型与提示词全文 / 资源清单与风险），⏸ **等用户书面确认后才进 Step 3**——数据集 5 个字段创建后不可变，一次定型；元数据表与工作流配置均以此设计稿为准。

### Step 3 数据集准备（参数映射 → 搜索复用 → 创建 → 回读）

**先做固定参数检查与映射**（文件存储数据源 / 元数据存储数据源 / 生产路径 / 元数据表结构）：用户输入能明确映射的直接用（如给了数据源名 → `list-data-source-with-config` 反查 ID；给了 `oss://` 全路径 → 拆 bucket 校验后取相对路径）；信息不全的向用户索要，不猜不编造。三档策略详见兄弟 skill `create-dataset`（经套件入口路由加载） Step 1 的参数映射表。

> 数据集全生命周期（设计/查重/创建/更新/删除）的完整规范见兄弟 skill `create-dataset`（经套件入口路由加载）；本步只覆盖工作流编排所需的最小闭环。

```bash
# 3.1 先搜索复用（include-version-list=true 才带版本详情）
aliyun dataphin-public list-datasets --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --keyword "<业务关键词>" --include-version-list true --page 1 --page-size 10 \
  --profile "$PROFILE" --user-agent "$UA"

# 3.2 不存在 → 创建（VersionConfig JSON 骨架见 references/dataset-parameters.md；执行前 HITL 确认）
aliyun dataphin-public create-dataset --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --name "<数据集名>" --type HYBRID --content-type TEXT --dir-name / --scenario OFFLINE \
  --storage-type OSS --metadata-storage-type POSTGRESQL --version V1 \
  --version-config "$(cat version-config-v1.json)" \
  --profile "$PROFILE" --user-agent "$UA"
# 多版本多表时：create-dataset 一次仅建 1 个版本，V2+ 用 update-dataset 逐个追加（--id/--file-id 必填，FileId 从回读取）

# 3.3 回读确认（必做，无论新建还是复用；返回的 DatasetDTO 是 Step 4 环境值的唯一来源）
aliyun dataphin-public get-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "<DatasetId>" \
  --profile "$PROFILE" --user-agent "$UA"
```

> ⚠️ 以上为插件 >= 0.7.0 的展平参数格式；旧版插件是嵌套对象参数（`--dataset-query`/`--create-command`）。旧写法在新插件下**不报错但被静默忽略**，以 `aliyun dataphin-public <cmd> --help` 实时输出为准。

- 复用判定：五个不可变字段（Scenario/Type/StorageType/MetadataStorageType/ContentType）与设计稿一致且表 schema 满足链路需要。
- 表 schema 设计红线（表名正则 / Milvus 主键+向量约束 / 向量维度对齐 / URL 列标记）见 [`references/dataset-parameters.md`](references/dataset-parameters.md)。

### Step 4 组装工作流 JSON（本地组装，不调写 API）

按 [`references/workflow-json-spec.md`](references/workflow-json-spec.md) 全文执行（含可直接抄的完整骨架 [`references/workflow-example.json`](references/workflow-example.json) 与缺骨架时的降级链），要点：

1. 顶层 `{"pipelineDTO": {"steps": [...], "hops": [...]}}`；每个 step 新生成 UUID v4 且 `step.id === pluginConfig.stepId`、`pluginConfig.webPluginKey === step.key`；**所有 step（含首节点）带 `"distribute": true`**；画布坐标按纵向布局生成（主干 `x` 固定、`y` 步进 140），但注意首次界面打开会被前端自动横排覆盖，需界面整理保存一次固化。
2. **环境值**（datasetId/versionId/storageDsId/metadataDsId/datasetTable/mountPath 等）只能按 §环境值映射表从 Step 3 `get-dataset` 回读结果填充，**禁止编造**；`modelId` 从实际环境模型实例取（取不到时向用户索要）。
3. **outputSelf 规则**：算子的 `neuronInput` 与 `neuronOutput` 指向**同一数据集同一版本（回写自己读的那张表）**时，`neuronOutput.outputSelf` 必须为 `true`；跨数据集或跨版本时为 `false`。
4. **loadStrategy 规则**：输出目标元数据表**有主键 → 默认 `UPSERT`（主键冲突时更新）；无主键 → `APPEND`（追加）**；`OVERWRITE`（覆盖）仅在用户明确需要全量覆盖时显式选用。
5. 提示词类字段（modelPrompt / LLM prompt）按业务语境**定制生成**，禁止跨场景生搬硬套；要素提取类场景先与用户确认输出模式——单列 JSON，或 **多列输出**（`enableOutputMultiColumn + customOutputColumns`，仅 llm_inference/image_understanding 支持，每要素直接拆列落表，见 spec §多列输出）。
6. 组装完跑 §结构自检清单（id/hop 引用一致、字段契约、outputSelf/loadStrategy 与表结构一致、无占位串残留），全过才进 Step 5。

### Step 5 创建工作流（写操作，执行前 HITL 确认，见下方「执行前确认」）

```bash
# 先 dry-run 验证请求体序列化（不发真实请求），重点核对 Body 里 Context.ProjectId 是否为目标项目
WORKFLOW_JSON=$(jq -c . workflow.json)
aliyun dataphin-public create-work-flow-by-json --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --env PROD --task-name "<任务名>" --task-type 3 --submit false \
  --work-flow-json "$WORKFLOW_JSON" \
  --profile "$PROFILE" --cli-dry-run

# 用户确认后去掉 --cli-dry-run 正式执行（追加 --user-agent "$UA"）
```

- `--directory` 仅在目标目录**已存在**时传（否则报 `DPN.Resource.DirectoryNotFound`，API 不自动建目录）；测试阶段建议不传，落根目录。

- 默认测试模式 `TaskType=3`（手动调度）+ `Submit=false`；用户明确要周期任务才用 `TaskType=1`，此时 `ScheduleConfig` 必填（如 `{"cronExpression":"0 0 0 * * ?"}`）。
- **仅支持 BASIC 模式项目，`Env` 固定 `PROD`**；返回 `Data.PipelineId` 即顶层结构过关，BASIC 项目无需关注 SubmitId/Version。

### Step 6 输出验证指引（交给用户）

后端对 `pluginConfig` 深层字段校验较宽松，**API 成功 ≠ 配置完全正确**。输出：创建结果摘要（DatasetId/VersionId/PipelineId/NodeId）+ 界面验证步骤（首次打开先**纵向整理布局并保存一次**（前端首开会自动横排）→ 画布渲染 → 算子面板回显 → 试运行落数 → 可选下载 JSON diff），详见 §9。

### 执行前确认（写操作必备 / HITL 章节）

> 本 skill 涉及写操作（`create-dataset` / `create-work-flow-by-json` / `update-dataset` / `delete-dataset`），调用方执行前必须二次确认：
> - 即将执行的命令全文（脱敏后）与入参 JSON（设计稿）
> - 影响范围（哪个 tenant / project / 数据集 / 目录）
> - 是否可回滚（数据集 5 字段不可变，错了只能删了重建）
> - 替代方案（`--cli-dry-run` 模拟运行 / `list-datasets` 只读复用）
>
> `delete-dataset` 为高危操作且 **OpenAPI 不自查下游引用**——删除前必须先确认无工作流引用该数据集版本，并逐次经用户人工确认。

仅当用户明确回复"确认 / yes / 执行"后才发起命令。

## 9. Success Verification

三层验证法（详见 [`references/workflow-json-spec.md`](references/workflow-json-spec.md) §三层验证）：

1. **结构自检**（Step 4 本地）：JSON 合法、id/hop 引用一致、字段契约满足、无占位串。
2. **API 返回**：`create-work-flow-by-json` 返回 `Code: OK` + `Data.PipelineId`；`get-dataset` 反查数据集存在且 schema 正确。
3. **界面回显 + 试跑**（语义验证，必做）：界面打开工作流看画布渲染与算子面板回显完整，试运行一小批数据确认末端表落数、向量列写入正常。

## 10. Cleanup

```bash
# 删除测试数据集（高危：先自查下游工作流引用，OpenAPI 不会自动拦截；逐次经用户确认）
aliyun dataphin-public delete-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "<DatasetId>" \
  --profile "$PROFILE" --user-agent "$UA"
```

测试工作流任务当前无删除 OpenAPI，请在 Dataphin 界面（研发 IDE → 非结构化工作流）删除。

> 创建后需要修改已有工作流（改提示词 / 换模型 / 增删算子 / 调整连线）→ 走兄弟 skill `update-unstructured-workflow`（经套件入口路由加载）（get-pipeline-by-id 回读 → 局部修改 → update-pipeline 提交）。

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参（JSON 内引号包住），避免 JS 精度截断。
2. 写操作必须执行前 HITL 二次确认；正式执行前先 `--cli-dry-run` 验证请求体。
3. 数据集**建在前、工作流建在后**；建完必 `get-dataset` 回读再填环境值。
4. 认证只走阿里云 CLI profile（`--profile`），skill 不读取/不传递任何 AK/SK 明文。
5. 「常见坑」每条标来源 `[Agent 自主发现] / [人工注入]`。

### ✗ 平台限制

#### ✗ 实时工作流（TaskType=5 / PipelineType=15）仅支持复刻/变体，不支持从零设计
- 限制描述：本 skill 的算子清单、链路范式均为**离线（OFFLINE）**；实时机制根本不同（流式直连不经表、reader_dataset 流式源、REALTIME 数据集用 STREAM_TABLE 实时元表），照离线范式组装必败。
- 实测已验证可走通的部分：✅ `create-dataset` 建 REALTIME 数据集（传 RealtimeMetaTableConfig）；✅ 基于**已有实时工作流回读基线**的复刻/局部变体可经 `create-work-flow-by-json --task-type 5` 创建——完整结构与组装要点见 [`references/realtime-workflow-notes.md`](references/realtime-workflow-notes.md)。
- 从零设计实时链路（无基线可抄）时：明确告知用户引导界面创建，或请用户界面搭最简样板后回读（同降级链）。

#### ✗ 仅支持 BASIC 模式项目
- 限制描述：`create-work-flow-by-json` 当前仅支持 BASIC 模式项目，`Context.Env` 固定传 `PROD`。
- 替代方案：DEV-PROD 项目暂无 OpenAPI 途径，走界面创建。

#### ✗ OpenAPI 未覆盖数据集重命名 / 版本单独删除 / 下游引用查询
- 限制描述：这些能力只有界面（前端内部接口）提供。
- 替代方案：编排时删数据集前**人工自查**下游引用；重命名走界面。

### 常见坑

> **错误暴露三层模型 [人工校准]**：非结构化工作流的配置错误按暴露时机分三层——① **创建时拦**（如 DirectoryNotFound、越权）；② **回读时爆**（如 modelId 类型错/自造字段 → GetPipelineById NPE）；③ **运行时才爆**（如 columnName 非契约值、分叉点漏 distribute）——创建/回读都不拦、界面回显可能也正常，最隐蔽。因此：创建后必回读（拦②）+ 组装前过完整自检清单（拦③）+ 少量数据试跑（兜底）。排障时首选 **A/B 对照法**：拿同环境可运行的健康样本与故障 JSON 逐字段 diff，差异即嫌疑（实测两次定位均靠此法收网）。

#### [人工注入] LLM/评分/去重类算子直连 URL 列导致空跑
- 现象：`llm_inference` 等算子上游接 `markdown_url` 类 URL 列，任务不报错但无产出。
- 结论：这类算子仅读 PG 表文本字段值；必须插入 URL→PG 桥接（大 chunkSize 的 `text_chunking` 或 `python_executor`）。

#### [人工注入] ListDatasets 拿不到 versionId
- 现象：返回的 DatasetDTO 无 VersionList。
- 结论：默认不带版本详情，需 `IncludeVersionList=true` 或改用 `get-dataset`。

#### [人工注入] UpdateDataset 报参数缺失
- 现象：只改名字也报错。
- 结论：`FileId` 必填（创建时的文件 ID），先 `get-dataset` 回读取。

#### [人工注入] API 成功但界面回显缺项
- 现象：`create-work-flow-by-json` 返回 PipelineId，但界面打开算子面板部分配置为空。
- 结论：后端深层字段校验宽松（很多校验在前端表单）；必须按 §9 第 3 层界面核验，对照算子校验规则补字段。

#### [Agent 自主发现] Create/Get/List/Delete 的 ProjectId 类型不一致
- 现象：`create-dataset`/`update-dataset` 的 `--project-id` 是 String，`get-dataset`/`delete-dataset`/`list-datasets`(body) 是 Long/integer。
- 结论：生成调用命令时按各命令 `--help` 输出为准，不要复用同一种写法。

#### [Agent 自主发现] 插件 0.7.0 参数展平 + 本地 profile 默认值静默覆盖
- 现象：旧版嵌套参数（`--context`/`--create-command`/`--dataset-query`）在 >=0.7.0 下不报错但被忽略，缺省值从 `~/.aliyun/dataphin-public/config.json` 的本地 profile 填充——ProjectId 可能指向错误项目。
- 结论：写操作前必跑 `--cli-dry-run`，核对 Body 中 `Context.ProjectId` 等实际取值；参数形态以 `--help` 实时输出为准。⚠️ 展平程度**逐命令不一致**：dataset 系列与 create-work-flow-by-json 已全展平，但 `get-pipeline-by-id`/`update-pipeline` 仍保留 `--context Env=xxx ProjectId=xxx` 嵌套键值对——不要把“全展平”当成插件级规律。

#### [Agent 自主发现] Directory 目录不存在直接报错
- 现象：`--directory /xxx` 报 `DPN.Resource.DirectoryNotFound`。
- 结论：API 不自动建目录；目录需界面预建，或不传落根目录。

#### [Agent 自主发现] DPN.Filter.NoPermission 是 Dataphin 项目 RBAC，非 RAM
- 现象：同一账号 `create-dataset` 成功但 `create-work-flow-by-json`/`get-dataset` 报 `DPN.Filter.NoPermission`（HTTP 400）。
- 结论：数据集读写与任务开发是不同项目权限点；需在 Dataphin 控制台把调用账号的项目角色升为含任务开发权限的角色（开发/管理员），与 RAM 策略无关。

#### [Agent 自主发现] 解析产物 URL 必须先落上游表列才能被下游引用
- 现象：链路 `ppt_parse → text_chunking` 时，若页表未预留 `page_markdown_url` 列，ppt_parse 的 `markdown_url` 无处落表，下游 inputColumn 无列可选。
- 结论：设计表 schema 时逐连线检查“上游 columnMappings 落到哪张表哪列、下游从同表同列读”，中间 URL 列（带 Url:true）预留齐全。

#### [Agent 自主发现] API 传入坐标首次打开被前端自动横排覆盖
- 现象：WorkFlowJson 传纵向坐标（x 固定、y 步进 140），界面首次打开仍横向平铺展示；界面拖拽保存后坐标才持久化（保存后下载的 JSON 即纵向范式 x 固定/y 步进 140）。另：后续若经 `update-pipeline` 更新（OA 形态无坐标字段），布局会再次被重置为自动横排。
- 结论：纵向坐标照常生成（保存后生效），验证指引中提示用户首次打开后「纵向整理 + 保存一次」固化布局；每次 API 更新后需重新整理。

#### [Agent 自主发现] 界面回环 diff 确认的两处组装细节
- 现象：界面保存版与 API 组装版逐字段 diff，仅两处差异：① 所有 step（含首节点）都带 `distribute: true`；② 首节点 file_basic_info 的 `neuronInput` 也补齐了 `datasetTable`/`metadataDsId`。
- 结论：组装时照此对齐；其余字段（outputSelf/loadStrategy/列映射/提示词）与界面保存版完全一致，组装范式可信。

#### [Agent 自主发现] 数据源 Type 与数据集存储类型枚举不一致，用错静默空结果
- 现象：`list-data-source-with-config --type-list POSTGRESQL` 返回空列表且 `Success=true`（不报错）；改 `POSTGRE_SQL` 才命中。
- 结论：**数据源 Type 枚举带下划线**（`POSTGRE_SQL`），而数据集 `MetadataStorageType` 枚举不带（`POSTGRESQL`）——同产品两套枚举，反查数据源时勿直接复用数据集枚举；空结果时先怀疑枚举拼写再怀疑环境。

#### [人工注入] step.type 从示例照抄/类比推断导致分类错误
- 现象：外部用户用 skill 生成的工作流中 `image_basic_info` 的 `type` 被写成 `normal`（类比了示例里的 `file_basic_info`），正确值为 `image`。
- 结论：`step.type` 必须逐算子按 operator-reference 清单分类查表（分节名即 type）；“基本信息”类算子四个分类各不相同；自检清单已加 key→type 校验项。

#### [Agent 自主发现] 写操作报 502 BadGateway 可能已创建成功，禁止直接重试
- 现象：写操作返回 `Dataphin.OpenAPI.BadGateway`（HTTP 502，`RPC invoke ... failed`）看似失败，实测却是服务端异步 RPC 超时而**资源已完整创建**（create-dataset 实例：盲重试改报 `DuplicateFileName`）。
- 结论：502 后先回读确认（数据集用 `list-datasets --include-version-list true`，工作流用创建回执的 PipelineId + `get-pipeline-by-id`），**存在则直接用、确不存在才重试**；工作流若 502 且无回执 PipelineId，由于无 list 接口，需引导用户界面确认后再决定重试/清理。

#### [Agent 自主发现] 多环境切换：插件 profile 跳环境污染 + 参数顺序影响 endpoint
- 现象：插件 profile `default`（存 A 环境租户/项目）会覆盖 B 环境命令行参数；`--profile` 写在 `--endpoint` 之后时 endpoint 回落到 current profile——两者均使请求静默打到错误环境。
- 结论：每环境建独立插件 profile + `--dataphin-profile <env>`；endpoint 写入主 CLI profile；**每次返回后用响应体 `TenantId`/`ProjectId` 交叉核对**，写操作前另用 `--cli-dry-run` 核 Endpoint 行。

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
- [`references/workflow-json-spec.md`](references/workflow-json-spec.md)（工作流 JSON 结构 / 链路推导 / 环境值映射 / 三层验证）
- [`references/workflow-example.json`](references/workflow-example.json)（真实环境验证过的 6 算子完整骨架，脱敏，可直接照改）
- [`references/realtime-workflow-notes.md`](references/realtime-workflow-notes.md)（实时工作流 PipelineType=15 实测结构：reader_dataset 骨架 / 流式 inputColumn / REALTIME 数据集契约；仅供解读，创建能力未解锁）
- [`references/operator-reference.md`](references/operator-reference.md)（47 算子清单 / 推荐模型 / 支持格式 / 典型链路）
- [`references/dataset-parameters.md`](references/dataset-parameters.md)(数据集枚举 / 不可变字段 / 建表红线 / CreateCommand 骨架)
- 兄弟 skill：`update-unstructured-workflow`（经套件入口路由加载）（更新已有工作流：回读 → 局部修改 → 提交）
- OpenAPI 文档：[CreateWorkFlowByJson](https://api.aliyun.com/document/dataphin-public/2023-06-30/CreateWorkFlowByJson) / [CreateDataset](https://api.aliyun.com/document/dataphin-public/2023-06-30/CreateDataset) / [GetDataset](https://api.aliyun.com/document/dataphin-public/2023-06-30/GetDataset) / [ListDatasets](https://api.aliyun.com/document/dataphin-public/2023-06-30/ListDatasets)
