---
name: update-unstructured-workflow
description: |-
  更新指定的 Dataphin 非结构化工作流：get-pipeline-by-id 回读现有配置 → 局部修改算子/连线/提示词/模型参数 →
  update-pipeline 提交（PipelineType=14）→ 回读验证。
  当用户场景涉及修改已存在的非结构化工作流（调整提示词 / 换模型 / 增删算子 / 调整连线 / 切换数据集版本 / 改资源规格 / 改调度）时进入。

  触发词：更新工作流、修改工作流、update-pipeline、调整算子、改提示词、换模型、加一个算子、
  删除算子、修改非结构化工作流、update unstructured workflow。

  关键限制：必须先 get-pipeline-by-id 回读、在回读结果上就地修改，禁止凭记忆重建整个 JSON；
  update-pipeline 是全量覆盖式更新（提交什么就变成什么）；已有 step 的 UUID/stepId 不可改；
  写操作前必须 HITL 确认。
---

# 更新指定 Dataphin 非结构化工作流（回读 → 局部修改 → 提交 → 验证）

## 1. Scenario Description

用户对**已存在**的非结构化工作流提出修改诉求（例："把要素提取那步的提示词换成新版""在解析后面加一个去重算子""向量化换成另一个模型"），本 skill 自动完成：

1. 定位目标工作流（PipelineId / FileId / NodeId 任一）；
2. `get-pipeline-by-id` 回读现有全量配置（steps + hops + 调度配置），保存为基线；
3. 变更设计（输出变更摘要 diff，**暂停等用户确认**）；
4. 在回读 JSON 上**就地局部修改**（未变更部分原样保留）+ 结构自检；
5. `update-pipeline` 提交（`--pipeline-type 14`，默认 `--submit false`）；
6. 回读 diff 验证 + 界面回显指引。

**Architecture**：`Dataphin Tenant + BASIC Project + 已存在的非结构化工作流(算子 DAG) + 数据集 + 模型实例`。

> 创建新工作流请走兄弟 skill `create-unstructured-workflow`（经套件入口路由加载）；本 skill 只负责**更新已存在**的工作流。

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
| ProjectId | 是 | 工作流所属 BASIC 模式项目 ID | — |
| 定位键 | 是 | `PipelineId` / `FileId` / `NodeId` 至少一个（创建回执或界面 URL 可取） | — |
| 变更内容描述 | 是 | 要改什么（提示词/模型/算子增删/连线/数据集版本/资源规格/调度） | — |
| `--submit` | 否 | 是否提交生效（**不传时 API 默认提交**，本 skill 默认显式传 `false` 存草稿） | `false` |
| `--comment` | 否 | 本次变更备注（建议写变更摘要） | — |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/update-unstructured-workflow/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public get-pipeline-by-id --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --context Env=PROD ProjectId="$PROJECT_ID" --pipeline-id "$PIPELINE_ID" \
  --user-agent AlibabaCloud-Agent-Skills/update-unstructured-workflow/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow（五步流程）

```bash
TENANT_ID="30001011"        # 租户 ID
PROJECT_ID="789"            # 工作流所属 BASIC 模式项目 ID
PIPELINE_ID="12345"         # 目标工作流 PipelineId（或改用 --file-id / --node-id）
PROFILE="<aliyun configure list 中的有效 profile 名>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/update-unstructured-workflow/$SESSION_ID"
```

**本 skill 所有 `aliyun` API 命令统一携带 `--profile "$PROFILE"`；独立部署模式下按父 skill Step 0 约定另追加 `--skip-secure-verify`。**

**铁律：`update-pipeline` 是全量覆盖式更新——提交的 pipelineConfig 就是更新后的完整 DAG。所有修改必须建立在 `get-pipeline-by-id` 回读结果之上做局部编辑，禁止凭记忆重建整个 JSON；未变更的 step/hop/字段原样保留。**

### Step 1 定位目标工作流（只读）

用户提供 `PipelineId` / `FileId` / `NodeId` 任一即可（三选一）。

**标准动作 [人工注入]**：产品当前缺工作流 list 接口，但有 [GetPipelineById](https://api.aliyun.com/document/dataphin-public/2023-06-30/GetPipelineById)（即 `get-pipeline-by-id`）可按 ID 查详情——因此用户想查询/更新某个工作流而未给 ID 时，**直接开口问用户要工作流 ID**（界面任务详情/地址栏 URL/创建回执 `Data.PipelineId` 均可见），不要猜、不要翻项目文件树硬找。

> ⚠️ **非结构化工作流当前无 CLI 列表途径**（实测）：CLI 无 `list-pipelines` 命令；`list-files` 的 category 枚举中无工作流类目——`offlinePipeline` 只列**集成管道**（自建的非结构化工作流不在其中），`realtimePipeline` 类目不存在（报 InternalError）。若误用 `list-files` 找到的文件，回读后按 `PipelineType` 判定：0/1=集成管道（不在本 skill 范围）、14=非结构化工作流、15=实时工作流。

### Step 2 回读现有配置（基线，必做）

```bash
aliyun dataphin-public get-pipeline-by-id --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --context Env=PROD ProjectId="$PROJECT_ID" --pipeline-id "$PIPELINE_ID" \
  --profile "$PROFILE" --user-agent "$UA" > pipeline-baseline.json
```

> ⚠️ `--context` 与顶层 `--project-id` 需**同时传**：顶层 `--project-id` 仅在本地 dataphin profile 已配置默认项目时可省，外部环境未配 profile 时缺它直接报 `--project-id is required`（实测外部用户踩中）。

- 回读结果中的工作流配置（steps + hops）、任务基本信息（NodeName/NodeId/FileId/Directory）、调度配置是后续三步的**唯一数据来源**；
- **仅支持 BASIC 模式项目，`Env` 固定 `PROD`**（与创建时一致）；
- 回读失败报 `DPN.Filter.NoPermission` 时按 §5 权限处理流程走（项目级 RBAC，见 §12 常见坑）。

### Step 3 变更设计（产出变更摘要，⏸ 暂停等用户确认）

按变更类型对照 [`references/pipeline-config-spec.md`](references/pipeline-config-spec.md) 的编辑规则设计修改方案：

| 变更类型 | 触碰的字段 | 关键约束 |
|---|---|---|
| 改提示词 / 模型参数 | `pluginConfig.neuronModel.modelPrompt` / `modelId` / `maxTokens` 等 | `modelId` 必须来自实际环境模型实例，禁止编造 |
| 增/删算子 | `steps[]` + `hops[]` 同步增删 | 新 step 生成新 UUID v4；删 step 必须同时删除其关联 hops 并重接上下游 |
| 调整连线 | `hops[]` | `hop.id === source + "-" + target`；字段契约（上游落表列 ⊇ 下游 inputColumn）仍须满足 |
| 切换数据集版本 / 表 | `neuronInput` / `neuronOutput` 环境值 | 新值必须来自 `get-dataset` 回读（datasetVersionId/datasetTable 等成组换，不能只换一半） |
| 改资源规格 | `pluginConfig.setting.requiredResource` | 同时置 `resourceModifiedByUser: true` |
| 开/关多列输出 | `neuronModel.enableOutputMultiColumn`/`customOutputColumns` + `columnMappings` 整组替换 | 仅 llm_inference/image_understanding；原单列（answer/image_content）不复存在，**下游以原列为输入的算子必须同步切列**（详见 spec §二.7） |
| 改调度 | ScheduleConfig | 仅在用户明确要求时改；否则原样回传回读值 |

输出**变更设计稿**：目标工作流标识 + 变更前后 diff 摘要（改哪些 step 的哪些字段、增删哪些 step/hop）+ 风险提示（是否影响下游落表），⏸ **等用户书面确认后才进 Step 4**。

### Step 4 就地修改 + 结构自检（本地，不调写 API）

在 `pipeline-baseline.json` 的工作流配置上做最小 diff 编辑，产出 `pipeline-updated.json`。完成后跑 [`references/pipeline-config-spec.md`](references/pipeline-config-spec.md) §更新自检清单：

- 已有 step 的 `id` / `pluginConfig.stepId` 未被改动；新增 step 满足 `id === stepId`、`webPluginKey === key`；
- 所有 `hop.source/target` 指向存在的 step，`hop.id` 拼接正确，无悬空连线（被删 step 的 hops 已清理）；
- 每条连线字段契约与内容类型兼容（LLM/评分/去重类算子不吃 URL 输入，桥接规则同创建时）；
- 环境值均来自回读或 `get-dataset`，无占位串、无编造值；
- 未变更的 step/hop 与基线逐字段一致（`jq -S` 排序后 diff 仅剩本次变更项）。

### Step 5 提交更新（写操作，执行前 HITL 确认，见下方「执行前确认」）

```bash
# 先 dry-run 验证请求体序列化（不发真实请求），核对 Body 里 Context.ProjectId 与 NodeInfo 定位键
aliyun dataphin-public update-pipeline --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --context Env=PROD ProjectId="$PROJECT_ID" \
  --node-info "{\"PipelineId\": $PIPELINE_ID}" \
  --pipeline-type 14 \
  --pipeline-config "$(jq -c '<回读结构中工作流配置的路径>' pipeline-updated.json)" \
  --schedule-config '<Step 2 回读的调度配置原样回传>' \
  --submit false --comment "<本次变更摘要>" \
  --profile "$PROFILE" --cli-dry-run

# 用户确认后去掉 --cli-dry-run 正式执行（追加 --user-agent "$UA"）
```

- `--node-info`：JSON 字符串，`PipelineId` / `FileId` / `NodeId` 至少一个（与 Step 1 定位键一致）；不改任务名/目录时**不要**携带 `NodeName` / `Directory` 之外的臆造字段；
- `--pipeline-type 14`：非结构化工作流（15 为实时工作流；0/1 为集成管道，不在本 skill 范围）；
- `--pipeline-config`：更新后的完整工作流 JSON 字符串（结构见 [`references/pipeline-config-spec.md`](references/pipeline-config-spec.md)）；
- `--schedule-config` 必填：不改调度时**原样回传 Step 2 回读值**，禁止自行构造；
- `--mode` / `--pipeline-json` 是集成管道脚本模式参数，**工作流任务不支持脚本模式，不要传**；
- 默认 `--submit false` 存草稿；用户明确要求变更立即生效时才 `--submit true`。

### Step 6 验证（回读 diff + 界面回显）

```bash
aliyun dataphin-public get-pipeline-by-id --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --context Env=PROD ProjectId="$PROJECT_ID" --pipeline-id "$PIPELINE_ID" \
  --profile "$PROFILE" --user-agent "$UA" > pipeline-after.json
```

与 `pipeline-updated.json` 比对确认变更已落库（详见 §9）。

### 执行前确认（写操作必备 / HITL 章节）

> 本 skill 涉及写操作（`update-pipeline`），调用方执行前必须二次确认：
> - 即将执行的命令全文（脱敏后）与变更设计稿（diff 摘要）
> - 影响范围（哪个 tenant / project / 工作流；`--submit true` 时变更立即生效）
> - 是否可回滚（**无版本回退 OpenAPI**——回滚手段是用 Step 2 的 `pipeline-baseline.json` 再执行一次 update-pipeline 恢复基线，基线文件必须保留到验证完成）
> - 替代方案（`--cli-dry-run` 模拟运行 / `--submit false` 存草稿先界面核验）
>
> 仅当用户明确回复"确认 / yes / 执行"后才发起命令。

## 9. Success Verification

三层验证法：

1. **API 返回**：`update-pipeline` 返回 `Code: OK`。
2. **回读 diff**：`get-pipeline-by-id` 再次回读，确认变更字段已生效、未变更字段与基线一致（`jq -S` 排序后 diff 仅剩本次变更项）。
3. **界面回显 + 试跑（语义验证，必做）**：后端对 `pluginConfig` 深层字段校验较宽松，界面打开工作流确认画布渲染、被改算子面板回显正确；有条件试运行一小批数据确认落表正常。`--submit false` 时提醒用户草稿需在界面提交后才生效。

## 10. Cleanup

本 skill 不创建新资源，无需清理。若需回滚本次变更：

```bash
# 用 Step 2 保存的基线重新提交一次（同样走 HITL 确认）
aliyun dataphin-public update-pipeline --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --context Env=PROD ProjectId="$PROJECT_ID" \
  --node-info "{\"PipelineId\": $PIPELINE_ID}" --pipeline-type 14 \
  --pipeline-config "$(jq -c '<基线中工作流配置的路径>' pipeline-baseline.json)" \
  --schedule-config '<基线调度配置>' --submit false \
  --profile "$PROFILE" --user-agent "$UA"
```

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参（JSON 内引号包住），避免 JS 精度截断。
2. 写操作必须执行前 HITL 二次确认；正式执行前先 `--cli-dry-run` 验证请求体。
3. **先回读、后修改、再提交**——基线 JSON 保留到验证完成，它同时是唯一的回滚手段。
4. 最小 diff 原则：只动用户要求变更的字段，其余原样回传；不理解的字段（`webConfig` / `x` / `y` / `parallel` 等）不要删、不要改。
5. 认证只走阿里云 CLI profile（`--profile`），skill 不读取/不传递任何 AK/SK 明文。
6. 「常见坑」每条标来源 `[Agent 自主发现] / [人工注入]`。

### ✗ 平台限制

#### ✗ 仅支持 BASIC 模式项目
- 限制描述：非结构化工作流 OpenAPI 链路当前仅支持 BASIC 模式项目，`Context.Env` 固定传 `PROD`。
- 替代方案：DEV-PROD 项目暂无 OpenAPI 途径，走界面修改。

#### ✗ 无版本历史 / 回退 OpenAPI
- 限制描述：`update-pipeline` 全量覆盖，OpenAPI 无「查看历史版本 / 一键回退」能力。
- 替代方案：更新前必存基线 JSON（Step 2），回滚 = 重放基线。

### 常见坑

#### [人工注入] 工作流的 hops 用 UUID 连线，与 OpenAPI 文档描述的集成管道形态不同
- 现象：UpdatePipeline OpenAPI 文档把 `Hops[].Source/Target` 描述为「步骤名称（StepName）」，但对非结构化工作流（PipelineType=14），实际结构是 `steps[].id`（UUID v4）连线、`hop.id = sourceUUID-targetUUID`，与 `get-pipeline-by-id` 回读及 `create-work-flow-by-json` 的 pipelineDTO 内层一致。
- 结论：文档描述的 StepName 形态是集成管道（PipelineType 0/1）的；工作流一律以**回读结构**为准，见 `references/pipeline-config-spec.md`。

#### [人工注入] 全量覆盖语义：漏传 step 等于删除该 step
- 现象：只想改一个算子，提交的 pipelineConfig 却只包含被改的 step，其余算子全部消失。
- 结论：`update-pipeline` 提交的是**完整 DAG**；必须在回读 JSON 上做最小 diff 编辑后整体回传。

#### [人工注入] 切数据集版本只换 datasetVersionId 导致配置自相矛盾
- 现象：把某算子输出切到新版本，只改了 `datasetVersionId`，`datasetVersion` / `datasetTable` 还指旧版本，任务行为异常。
- 结论：数据集环境值（datasetVersion/datasetVersionId/datasetTable 及必要时 storageDsId/metadataDsId）**成组替换**，新值全部来自 `get-dataset` 回读。

#### [Agent 自主发现] 插件 0.7.x 参数已展平，--update-command 嵌套写法被静默忽略
- 现象：按 OpenAPI 文档拼 `--update-command '{...}'` 不报错但不生效，实际入参取了本地 profile 默认值——尤其 `UpdateCommand.ProjectId` 会被 `~/.aliyun/dataphin-public/config.json` 的默认项目静默覆盖，指向错误项目。
- 结论：以 `aliyun dataphin-public update-pipeline --help` 实时输出为准（`--node-info` / `--pipeline-config` / `--schedule-config` 展平必填）；**必须显式传 `--project-id`**；写操作前必跑 `--cli-dry-run` 同时核对 `Context.ProjectId` 与 `UpdateCommand.ProjectId`。

#### [Agent 自主发现] --schedule-config 是必填项，不改调度也要传
- 现象：只改算子配置、不传 `--schedule-config`，CLI 直接报缺参。
- 结论：不修改调度时把 Step 2 回读的调度配置**原样回传**；禁止随手编 cron。

#### [Agent 自主发现] 回读是 OA 形态：Hops 按步骤名连线、PluginConfig 是 JSON 字符串
- 现象：`get-pipeline-by-id` 对工作流（PipelineType=14）返回的 `PipelineConfig.Hops[].Source/Target` 是**步骤名**（非 UUID），`Steps[].PluginConfig` 是 JSON **字符串**（需二次解析）——与界面导出的 UUID 连线形态不同。
- 结论：更新时按回读的 OA 形态原样回传即可（改 PluginConfig 内字段后重新序列化回字符串）；两种形态都合法，以回读到的为准。

#### [Agent 自主发现] 每次更新后服务端重新生成所有 stepId
- 现象：`update-pipeline` 成功后再回读，所有 step 的 `pluginConfig.stepId` 全部变化（含未改动的 step）。
- 结论：OA 形态按 StepName 定位算子，服务端每次更新重建内部 UUID；回读 diff 验证时应**忽略 stepId 字段**，只比对业务字段。另：`--comment` 会被写入 `ScheduleConfig.nodeDesc`，diff 时同样预期内。

#### [Agent 自主发现] 用 pipelineDTO（UUID）形态提交 update-pipeline 会静默清空 DAG（高危）
- 现象：把创建通道的 `{"pipelineDTO":{steps,hops}}` 形态传给 `--pipeline-config`，返回 `Code: OK`，但回读发现工作流变成 **0 步骤 0 连线**——服务端没解析出任何 step，全量覆盖直接清空了 DAG，且不报错。
- 结论：`--pipeline-config` **只接受 OA 形态**（`{Steps:[{StepName,Key,StepType,IsDistribute,PluginConfig字符串}],Hops:[{Source,Target}]}`）；提交后**必须立即回读校验步骤数/连线数**，不能只看 Code: OK；万一清空，重放基线/上一版 OA 配置可完整恢复。

#### [Agent 自主发现] OA 形态无坐标字段，每次更新都会重置画布布局
- 现象：用户界面拖成纵向并保存后，经 `update-pipeline` 更新再打开又变回横排（前端内部接口可见 step 坐标被置为 x:0,y:0）。
- 结论：OA 形态不携带坐标字段；实测在 OA Step 上附加 `x/y/X/Y` 提交返回 OK 但字段被静默丢弃（回读无）；前端内部接口的 pipelineDTO 带 x/y 但那是登录态通道，不在 OpenAPI 范围。**布局无法通过本通道配置；验证指引应提醒用户每次 API 更新后界面重新整理布局并保存。**

#### [Agent 自主发现] DPN.Filter.NoPermission 是 Dataphin 项目 RBAC，非 RAM
- 现象：RAM 策略齐全仍报 `DPN.Filter.NoPermission`（HTTP 400）。
- 结论：任务开发是项目级权限点，需在 Dataphin 控制台把调用账号的项目角色升为含任务开发权限的角色（开发/管理员），与 RAM 策略无关。

#### [人工注入] GetPipelineById 对特定配置的工作流抛服务端 NPE，阻断更新链路
- 现象：外部用户的某 API 创建工作流回读确定性报服务端空指针（`ConverterService.buildOAPipelineConfig` NPE），Step 2 拿不到基线，三段式正确拦截后续写操作。
- 边界（同环境对照组实测）：**非所有 API 创建的工作流都会触发**——含 filters/多列输出/实时的工作流回读均正常；触发源是个别工作流的**特定缺失/空字段**（OA 转换器假设非空），勿过度概括为通道不可用。
- 根因认知：**create 通道宽松放行，创建成功 ≠ 配置健康**——畸形配置能落库，到回读/更新时才在 OA 转换处爆炸。
- 处置路径：① 拿创建时的 workflow JSON 与已验证骨架逐算子比对缺失/异常字段（实锤案例：`modelId` 传了 int + 夹带自造字段 `llmModelProviderId`/`modelSource`；另查 modelId 在该项目是否真实存在——界面模型管理核对）；② 界面打开看回显（界面不经 OA 转换，若界面正常而 OpenAPI 炸则实锤转换器缺空值防护，报产研）；③ 修复后 create 重建 + 立即回读验证，短期改动可界面完成。

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
- [`references/pipeline-config-spec.md`](references/pipeline-config-spec.md)（工作流 pipelineConfig 结构 / 更新编辑规则 / 自检清单）
- 兄弟 skill：`create-unstructured-workflow`（经套件入口路由加载）（创建链路 + 算子清单 + 数据集环境值映射）
- OpenAPI 文档：[UpdatePipeline](https://api.aliyun.com/document/dataphin-public/2023-06-30/UpdatePipeline) / [GetPipelineById](https://api.aliyun.com/document/dataphin-public/2023-06-30/GetPipelineById)
