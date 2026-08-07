# 工作流 JSON 规范：结构 / 链路推导 / 环境值映射 / 三层验证

> `create-work-flow-by-json` 的 `WorkFlowJson` 字段规范。组装时严格对照本文，禁止凭记忆发挥。
>
> 📌 **可直接抄的完整骨架**：[`workflow-example.json`](workflow-example.json)——真实环境验证过的 6 算子工作流（file_basic_info → ppt_doc_transform → ppt_parse → text_chunking 桥接 → llm_inference → text_embedding）已脱敏，`<...>` 占位符标明每个环境值的回读来源；同分类算子结构高度相似（如 pdf_parser/word_parse ≈ ppt_parse），可照改。
>
> 🔁 **缺算子骨架时的降级链**（目标算子不在示例中且无把握时，按序兜底，**禁止凭空构造 pluginConfig**）：
> 1. 用户能提供同租户已有非结构化工作流的 PipelineId/FileId → `get-pipeline-by-id` 回读作基线（按 `PipelineType=14` 确认，0/1 是集成管道不可用；⚠️ 实测非结构化工作流无 CLI 列表途径——`list-files` 各 category 均不含工作流类目，定位键只能来自创建回执或界面）；
> 2. 都没有 → 请用户在界面随手搭一个**含目标算子的最简工作流**（不必配完整），告知 PipelineId 后回读拿真实结构再组装。

## 一、顶层结构

```json
{
  "pipelineDTO": {
    "steps": [ { "id": "...", "name": "...", "key": "...", "type": "...", "x": 305, "y": 144,
                 "reader": false, "writer": false, "distribute": true,
                 "webConfig": { "requireCompeleted": true }, "pluginConfig": { ... } } ],
    "hops":  [ { "hopType": "distribute", "id": "<sourceId>-<targetId>",
                 "source": "<sourceId>", "target": "<targetId>" } ]
  }
}
```

### steps[]（算子节点）

- `id` 为 UUID v4，**必须与 `pluginConfig.stepId` 完全一致**；
- `key` 为算子 key（如 `ppt_parse`），`type` 为算子分类（`normal`/`text`/`document`/`image`/`video`/`audio`/`vector`）；
- **`type` 取值规则 [人工注入]**：必须等于该算子在 [`operator-reference.md`](operator-reference.md) 算子清单中所属的**分类分节名**，逐算子查表确认，**禁止从示例骨架照抄或按名字类比推断**——实测踩坑：`image_basic_info` 属 **image** 分类，被类比 `file_basic_info` 误写成 `normal`。特例：`file_basic_info` 是唯一**双分类**算子（normal/text 均合法，本套件示例用 normal）；其余基本信息算子均单一分类（image→image、video→video、audio→audio）；
- `pluginConfig.webPluginKey` 与 step `key` 一致；
- `pluginConfig` 五大区块：`neuronInput` / `neuronParameters?` / `neuronModel?` / `neuronOutput` / `setting`（`?` 表示部分算子才有）；
- **画布坐标 `x`/`y` [人工注入]**：默认按**纵向布局**生成——主干链路 `x` 固定（如 300），`y` 从 100 起每节点 **+140** 向下递增；并行分支同 `y`、`x` 左右错开 ±290（与界面手工纵向摆放保存后的范式同构）。⚠️ 实测：**API 传入的坐标在界面首次打开时会被前端自动横排布局覆盖**，界面拖拽保存后才持久化——验证指引中应提示用户首次打开后纵向整理并保存一次；
- **`distribute` 标记 [Agent 自主发现]**：界面保存版**所有 step（含首节点）均带 `"distribute": true`**，组装时统一设置，不要只给下游节点——实测外部案例：漏在 **6 路分叉点**上的节点缺此字段，创建成功但运行异常；
- **`webConfig` 固定传 `{"requireCompeleted": true}` [人工注入]**：不要传空 `{}`（健康骨架均带此值；旧版本文顶层示例曾误写 `{}` 被外部照抄，已纠正）；
- **`neuronInput` 环境值字段带全 [Agent 自主发现]**：即便是文件扫描类首节点（file_basic_info），HYBRID 数据集时 `neuronInput` 也应带 `datasetTable` 与 `metadataDsId`（界面保存版如此），不要裁剪；
- **`neuronOutput.outputSelf` 规则 [人工注入]**：算子的输入与输出指向**同一数据集同一版本（即回写自己读取的那张表）**时必须为 `true`；跨数据集或跨版本落表时为 `false`。对照真实示例：解析/推理/向量化算子同表 UPSERT 回写 → `true`；切分算子 V1 表读、V2 表写（同数据集跨版本）与基本信息算子跨数据集落表 → `false`；
- **`neuronOutput.loadStrategy` 规则 [人工注入]**：枚举 `APPEND`(追加数据) / `UPSERT`(主键冲突时更新) / `OVERWRITE`(覆盖数据)。默认值按输出目标元数据表判定：**表有主键 → 默认 `UPSERT`；表无主键 → `APPEND`**；`OVERWRITE` 仅在用户明确需要全量覆盖（如首节点全量重扫）时显式选用；
- 部分字段存在联动：如 `neuronModel.modelId` 仅 `modelSource === 'MULTIMODAL'` 时出现，`modelPrompt` 仅 `enable_image_interpretation === true` 时展示且必填（≤2000 字符）。

### hops[]（连线）

- `id` = source UUID + `-` + target UUID 拼接；
- 所有 step（含首节点）统一带 `"distribute": true` 标记（见上方 steps 规则）。

### 数据传递机制（核心心智模型）

**hops 只定执行顺序，数据靠数据集表传递**：

- 上游算子 `neuronOutput.columnMappings` 把输出字段写入数据集表列（`targetColumn` = 表列名）；
- 下游算子 `neuronInput.inputColumn` 从表列读取（`sourceColumnName` = 表列名，`columnName` = 算子输入占位名）；
- **`columnName` 是算子契约固定值，不是自由命名 [人工注入]**：各算子的输入参数名由算子定义（INPUT_COLUMNS）固定——如 `image_understanding`→**`image_url`**、`llm_inference`/`text_embedding`→`content`、文档解析类（ppt_parse 等）→`file_url`；**不要把上游表列名照抄进 columnName**——实测踩坑：外部用户 8 个 image_understanding 节点 columnName 照抄上游列名 `file_url`（应为 `image_url`），创建/回读均不拦，**运行才报错**；取值以健康样本同算子的 columnName 或算子文档为准；
- URL 语义列的 `inputColumn.sourceColumnContentType = 'URL'`；
- 判断两个算子能否串接，看的是：**上游落表的列能否满足下游 INPUT_COLUMNS 的需求**。

## 二、算子链路推导规则

1. 逐算子查 INPUT_COLUMNS（消费什么，TEXT/URL 内容类型）与 OUTPUT_COLUMNS（产出什么）——清单见 [`operator-reference.md`](operator-reference.md)。
2. **输出字段 ⊇ 下游输入字段** 即可连接；同时检查**内容类型兼容**——「仅解析 PG 元数据表字段值」的算子（`llm_inference` / `text_quality_score` / `simhash_dedup` / `md5_dedup` 等）**不能直接消费 URL 列**。
3. 基本信息类算子（`file/image/video/audio_basic_info`）通常作为链路起点，负责把 `file_url` / `file_extension` 等元数据落表。
4. 典型链路模式：
   - 文档：`file_basic_info → pdf_parser/word_parse/ppt_parse → 文本清洗类 → text_chunking → llm_inference / text_embedding`
   - 音频：`audio_basic_info → audio_transcoding → audio_to_text → 文本链路`
   - 视频：`video_basic_info → video_keyframe_extraction → 图片链路`，或 `→ video_audio_extractor → 音频链路`
   - 图片：`image_basic_info → image_ocr / image_understanding → 文本链路`
   - PPT 按页构建知识库（两种做法）：
     - ① 文本路线：`ppt_doc_transform(pagetoppt 按页拆分) → ppt_parse(页级 markdown_url) → URL→PG 文本桥接 → llm_inference → text_embedding`
     - ② 视觉路线：`ppt_doc_transform(pagetopng 按页转 PNG) → image_understanding(视觉模型直接提取关键信息)`

### URL→PG 文本桥接

下游算子只吃表字段文本、上游产出是 URL 时的两种手段：

| 手段 | 说明 | 优先级 |
|---|---|---|
| `text_chunking` | 把 `chunkSize` 调到足够大（整页/整文档不被切开的字符数），实质是「URL 文件内容 → 表字段文本」的搬运，chunk 是副作用 | **优先**（零代码） |
| `python_executor` | 自写脚本读取 URL 对应文件内容，写入 PG 表文本字段 | 兜底（灵活，需写代码） |

### 多列输出（enableOutputMultiColumn）[人工注入]

把大模型输出直接拆成多个结构化字段落表（免去 JSON 单列再加工）：

- **仅两个算子支持**：`llm_inference`（关闭时单列默认 `answer`）、`image_understanding`（关闭时单列默认 `image_content`）；
- 结构（`neuronModel` 内）：

```jsonc
"enableOutputMultiColumn": true,
"customOutputColumns": [            // 每项：字段名 / 类型 / 语义说明 / 示例
  { "name": "summary",  "type": "string", "comment": "图片内容 2-4 句概括", "example": "该图展示了…" },
  { "name": "category", "type": "string", "comment": "定位类别，从 11 类中选一", "example": "方案架构" }
]
```

- **联动**：开启后 `columnMappings.sourceColumn` 取 `customOutputColumns[].name`（不再是 answer/image_content），逐字段映射到表列；输出表需为每个自定义列预留对应表列；⚠️ **下游连带变更**：单列模式的输出列（如 JSON 列）在多列模式下不再被写入，下游算子（如 text_embedding）若以它为输入必须同步切到新列（如 summary）；
- **提示词分工**：`modelPrompt` 写整体分析要求；字段级拆分规则写在每列的 `comment`（含取值约束，如"取值：高/中/低"）+ `example`（真实样例），两者共同构成模型的拆分指令；
- **选型建议**（Step 2 设计稿时与用户确认）：要素提取类场景两种输出模式——① 单列 JSON（表列少、后续加工灵活）；② 多列输出（每要素一列，SQL 直查/分析友好）。字段明确且需直接消费时优先多列输出。

## 三、字段取值原则

| 字段类别 | 原则 |
| --- | --- |
| 结构字段（字段名/层级/枚举值/联动） | 严格对齐算子参考与真实示例，禁止发挥 |
| 环境值（datasetId / modelId / storageDsId 等） | **必须来自 `get-dataset` 回读或实际环境，禁止编造** |
| 业务内容字段（modelPrompt / LLM 提示词 / 描述） | **按业务语境定制生成，禁止跨场景生搬硬套**：医药场景带靶点/临床指标术语，制造业换设备/工艺语言，无明确语境给通用版 |

其他注意：

- 产品无内置默认提示词（前端默认值只是占位串）；
- `columnMappings` 中 `targetColumn` 为空的行（界面未配置完的空行）组装时应剔除。

## 四、环境值映射表（get-dataset → WorkFlowJson，组装核心）

工作流 JSON 中 `neuronInput` / `neuronOutput` 的环境值，全部由 **`get-dataset` 返回的 DatasetDTO** 取得：

| 工作流字段（neuronInput/Output） | 数据集 API 字段来源 |
| --- | --- |
| `datasetId` | `DatasetDTO.Id` |
| `datasetName` | `DatasetDTO.Name` |
| `datasetType` | `DatasetDTO.Type` |
| `datasetProjectId` | `DatasetDTO.ProjectId` |
| `datasetVersion` | `VersionList[].Version` |
| `datasetVersionId` | `VersionList[].Id` |
| `datasetPath` | `FileStorageConfig.ProdPath` |
| `mountPath` | `FileStorageConfig.MountPath` |
| `storageDsId` | `FileStorageConfig.DataSourceId` |
| `metadataDsId` | `MetadataStorageConfig.DataSourceId` |
| `datasetTable` | `MetadataStorageConfig.TableName` |
| `inputColumn[].sourceColumnName` / `columnMappings[].targetColumn` | `TableSchema.Columns[].Name` |

> `modelId` 不在此表内——模型名 → 环境内模型实例 ID 的映射因租户而异，需从实际环境查询或向用户索要。

## 五、结构自检清单（Step 4 完成后逐条过）

- [ ] JSON 可解析；顶层为 `{"pipelineDTO": {"steps": [...], "hops": [...]}}`；
- [ ] 所有 `step.id` 唯一且 `=== pluginConfig.stepId`；`pluginConfig.webPluginKey === step.key`；
- [ ] 所有 `hop.source/target` 指向存在的 step；`hop.id === source + "-" + target`；
- [ ] 每条连线满足字段契约（上游落表列 ⊇ 下游 inputColumn 需求）与内容类型兼容（URL 不直连仅文本算子）；
- [ ] 逐算子校验 `outputSelf`：输入与输出同数据集同版本 → 必为 `true`；跨数据集/跨版本 → 必为 `false`；
- [ ] 逐算子校验 `loadStrategy`：输出目标表有主键 → `UPSERT`；无主键 → `APPEND`；`OVERWRITE` 需有明确全量覆盖理由；
- [ ] 坐标为纵向布局：主干 `x` 固定、`y` 递增（步进 ~140），并行分支同 `y` 错 `x`；
- [ ] 所有 step（含首节点）带 `distribute: true`（分叉点漏标→运行异常，实测）且 `webConfig: {"requireCompeleted": true}`（非空 `{}`）；`neuronInput` 环境值字段带全（含首节点的 datasetTable/metadataDsId）；
- [ ] 每个 step 的 `type` 与其 `key` 在 operator-reference 清单的分类一致（逐算子查表，勿类比推断）；
- [ ] 开启多列输出时：`columnMappings.sourceColumn` ⊆ `customOutputColumns[].name`，且目标表已为每列预留字段；未开启时 sourceColumn 为单列默认名（answer/image_content）；
- [ ] 环境值均来自 `get-dataset` 回读，无占位串残留；
- [ ] 创建后立即 `get-pipeline-by-id` 回读——除校验步骤数/连线数外，这同时是 **OA 可转换性体检**：create 通道宽松放行，畸形/缺字段配置能创建成功但回读时服务端 NPE（实测外部案例：buildOAPipelineConfig 空指针，导致后续永久无法 API 更新）——回读报错即配置不健康，当场排查勿留到更新时爆雷；
- [ ] **neuronModel 字段纪律**：`modelId` 必须为**字符串**（实测外部案例传 int + 夹带自造字段 `llmModelProviderId`/`modelSource`，创建成功但回读 NPE）；字段集以健康样本为准（image_understanding 多列输出仅：modelPrompt/modelId/maxTokens/enableOutputMultiColumn/customOutputColumns），**不要携带来源不明的额外字段**；
- [ ] **inputColumn.columnName 逐算子核对为契约固定值**（image_understanding→image_url、llm/embedding→content、解析类→file_url），不是上游列名的照抄——创建/回读不拦、运行才爆；
- [ ] `columnMappings` 无 `targetColumn` 为空的行；
- [ ] 向量列 dimension 与 Embedding 算子 `vectorDimension` 一致。

## 六、三层验证法（成本从低到高）

**API 调用成功 ≠ 配置完全正确**，三层各验不同的东西：

1. **结构自检**（本地，零成本）：上方清单逐条过。（可选深度核验：界面创建同样工作流 → 下载 JSON → 与生成版 diff；`jq -S` 排序后比对，忽略 UUID/画布坐标/用户内容字段，重点盯 `pluginConfig` 字段层级、`neuronParameters`、枚举值、`columnMappings`、`filters` 写法。）
2. **OpenAPI 结构验证**：`create-work-flow-by-json` 真实创建。降低副作用：`TaskType=3` + `Submit=false` + `Directory` 指测试目录。拿到 `PipelineId` = 顶层结构过关；报错含字段名则对照算子校验规则修。
3. **界面打开 + 试跑（语义验证，必做）**：后端对 `pluginConfig` 深层字段校验较宽松（很多校验在前端表单），API 成功后必须界面打开工作流，看画布渲染、算子配置面板回显是否完整；有条件点试运行确认末端表落数。验证完删除测试任务。

## 七、运行时行为备注

| 算子 | 行为 | 影响 |
| --- | --- | --- |
| 解析类（pdf_parser / word_parse / ppt_parse 等） | **算子内部自动跳过不匹配的文件类型** | `neuronInput.filters` 的 `file_extension = '.xxx'` 非必需，属减少无效行扫描的优化项；大表或多解析算子并行时建议显式加 |
| 文本推理 LLM（llm_inference） | **不支持 URL 类型字段作为输入，仅读 PG 表文本字段值** | 上游产出 `markdown_url` 等 URL 列时不能直连，先做 URL→PG 桥接（见第二节） |
