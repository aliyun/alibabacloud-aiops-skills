# 工作流 pipelineConfig 规范（更新场景）：结构 / 编辑规则 / 自检清单

> `update-pipeline`（PipelineType=14 非结构化工作流）的 `--pipeline-config` 字段规范。
> 本篇结构提炼自真实环境回读的工作流配置（已脱敏泛化）。编辑时严格对照本文与 `get-pipeline-by-id` 实时回读结果，禁止凭记忆发挥。

## 一、顶层结构

```json
{
  "steps": [ { ...算子节点... } ],
  "hops":  [ { ...连线... } ]
}
```

> ⚠️ 与 `create-work-flow-by-json` 的 `WorkFlowJson` 差一层包裹：创建接口是 `{"pipelineDTO": {"steps": [...], "hops": [...]}}`，
> 而 `update-pipeline` 的 `--pipeline-config` 直接是 `{"steps": [...], "hops": [...]}`。以 `get-pipeline-by-id` 回读到的实际层级为准。
>
> ⚠️ **OA 回读形态**（实测，POC v6.2）：`get-pipeline-by-id` 返回的是 PascalCase OA 结构——`PipelineConfig.Hops[].Source/Target` 为**步骤名**（非 UUID）、`Steps[].PluginConfig` 为 JSON **字符串**（需二次解析）。
> 更新时按回读形态原样回传即可：改 PluginConfig 内字段后重新序列化回字符串，Hops 保持步骤名连线。本文后续章节的 camelCase/UUID 形态适用于界面导出 JSON；两种形态字段语义一致。
>
> 🔴 **硬约束（实测 + 官方契约双重证实）：`--pipeline-config` 提交只接受 OA 形态。** 用 UUID/pipelineDTO 形态提交会返回 OK 但**静默清空 DAG**（解析出 0 step 后全量覆盖）。官方契约（`fetch_api_metadata.py dataphin-public 2023-06-30 UpdatePipeline` 可查证）的字段白名单：
> - `Steps[]` 仅 5 字段：`PluginConfig`(字符串,必填) / `StepType` / `StepName` / `IsDistribute` / `Key`；
> - `Hops[]` 仅 3 字段：`Source` / `Target`（均为 StepName）/ `SendTo`；
> - **无任何坐标字段**（附加 x/y 提交会被静默丢弃）——画布布局无法经本通道配置，每次更新后需界面重新整理并保存；
> - 白名单外字段一律被服务端（`com.alibaba.dataphin.pipeline.common.facade.openapi.model` OA 模型类）丢弃。

### hops[]（连线）

```json
{
  "id": "<sourceUUID>-<targetUUID>",
  "source": "<sourceUUID>",
  "target": "<targetUUID>",
  "enabled": null,
  "hopType": "distribute",
  "sendTo": null
}
```

- `source` / `target` 是 **step 的 UUID id**（不是 StepName——StepName 连线是集成管道 PipelineType 0/1 的形态）；
- `id` 严格等于 `source + "-" + target` 拼接；
- `enabled` / `sendTo` 回读是什么就回传什么（通常为 `null`），不要删字段。

### steps[]（算子节点）

```json
{
  "id": "<UUID v4>",
  "name": "<算子显示名>",
  "description": null,
  "key": "<算子key，如 ppt_parse / text_chunking / llm_inference / text_embedding>",
  "type": "<normal|text|document|image|video|audio|vector>",
  "pluginConfig": { ... },
  "webConfig": {},
  "parallel": null,
  "distribute": true,
  "mainOutput": null,
  "x": 774, "y": 24,
  "readCount": null, "writeCount": null, "errorCount": null,
  "reader": false, "writer": false
}
```

- `id === pluginConfig.stepId`、`key === pluginConfig.webPluginKey`（三处联动，改任何一处必须同步）；
- `x` / `y` 是画布坐标，新增 step 时给一个不与现有节点重叠的值（如同列 y 递增 140）即可；
- `webConfig` / `parallel` / `mainOutput` / `readCount` 等运行时/画布字段：**原样保留，不理解不要动**。

### pluginConfig（算子配置，五大区块 + 公共字段）

```json
{
  "stepName": "<与 step.name 一致>",
  "name": "<与 step.name 一致>",
  "stepId": "<与 step.id 一致>",
  "webPluginKey": "<与 step.key 一致>",
  "noFlowTimeout": 30,
  "sqlTimeout": 30,
  "neuronInput":      { ...从哪张表哪些列读... },
  "neuronParameters": { ...算子专属参数（部分算子才有）... },
  "neuronModel":      { ...模型配置（LLM/多模态/Embedding 类算子才有）... },
  "neuronOutput":     { ...写回哪张表哪些列... },
  "setting": {
    "requiredResource": { "mem": "2048", "cpus": "1" },
    "resourceModifiedByUser": false
  }
}
```

`neuronInput` / `neuronOutput` 的环境值字段组（一起出现、一起替换）：

| 字段 | 含义 | 来源 |
|---|---|---|
| `datasetId` / `datasetName` / `datasetType` / `datasetProjectId` | 数据集标识 | `get-dataset` 回读 `DatasetDTO` |
| `datasetVersion` / `datasetVersionId` | 版本号 / 版本 ID | `VersionList[]` |
| `datasetTable` | 元数据表名 | `MetadataStorageConfig.TableName` |
| `datasetPath` / `mountPath` | 文件存储路径 / 挂载路径 | `FileStorageConfig` |
| `storageDsId` / `metadataDsId` | 文件/元数据存储数据源 ID | `FileStorageConfig` / `MetadataStorageConfig` |

其余业务字段：

- `neuronInput.inputColumn[]`：`{sourceColumnName, sourceColumnContentType(TEXT|URL), sourceColumnType, columnName}` —— `columnName` 是算子输入占位名（如 `file_url` / `content`），不可随意改；
- `neuronInput.filters[]`：SQL 片段字符串（如 `"page_markdown_url <> ''"`）；
- `neuronOutput.columnMappings[]`：`{targetColumn(表列名), sourceColumnType: "NEURON", sourceColumn(算子输出字段名)}`；
- `neuronOutput.loadStrategy`：`OVERWRITE` / `UPSERT`；
- `neuronOutput.outputSelf`：`true` 表示写回输入行本身（如解析补列）、`false` 表示产出新行。

### 真实形态示例（单个 LLM 推理 step，环境值已泛化）

```json
{
  "id": "4e28f8ab-f06a-4e4d-a1bc-84c8483dd4de",
  "name": "解决方案要素提取",
  "key": "llm_inference",
  "type": "text",
  "pluginConfig": {
    "neuronModel": {
      "enableDeepThink": false,
      "modelPrompt": "<按业务语境定制的提示词，≤2000 字符>",
      "enableOutputMultiColumn": false,
      "modelId": "<实际环境模型实例ID>",
      "maxTokens": 12800
    },
    "stepName": "解决方案要素提取",
    "name": "解决方案要素提取",
    "stepId": "4e28f8ab-f06a-4e4d-a1bc-84c8483dd4de",
    "noFlowTimeout": 30,
    "sqlTimeout": 30,
    "neuronInput": {
      "storageDsId": "<存储数据源ID>",
      "mountPath": "<挂载路径>",
      "datasetVersion": "V3",
      "datasetName": "<数据集名>",
      "datasetTable": "<元数据表名>",
      "inputColumn": [
        { "sourceColumnName": "page_content", "sourceColumnContentType": "TEXT",
          "sourceColumnType": "text", "columnName": "content" }
      ],
      "datasetPath": "<数据集路径>",
      "datasetProjectId": "<项目ID>",
      "metadataDsId": "<元数据数据源ID>",
      "datasetId": "<数据集ID>",
      "datasetType": "HYBRID",
      "outputSelf": false,
      "datasetVersionId": "<版本ID>"
    },
    "neuronOutput": {
      "loadStrategy": "UPSERT",
      "columnMappings": [
        { "targetColumn": "solution_elements", "sourceColumnType": "NEURON", "sourceColumn": "answer" }
      ],
      "outputSelf": true,
      "...": "（其余环境值字段组与 neuronInput 同源，此处省略）"
    },
    "webPluginKey": "llm_inference",
    "setting": {
      "requiredResource": { "mem": "2048", "cpus": "0.5" },
      "variables": { "concurrency": "100" },
      "resourceModifiedByUser": true
    }
  },
  "webConfig": {},
  "distribute": true,
  "x": 774, "y": 584,
  "reader": false, "writer": false
}
```

## 二、更新编辑规则（按变更类型）

**总原则：最小 diff。在 `get-pipeline-by-id` 回读 JSON 上就地改，未涉及的 step/hop/字段逐字节原样回传。**

### 1. 改提示词 / 模型参数

- 只动 `pluginConfig.neuronModel` 内字段（`modelPrompt` / `modelId` / `maxTokens` / `enableDeepThink` 等）；
- `modelId` 换新值时必须来自实际环境模型实例（取不到时向用户索要），禁止编造；
- `modelPrompt` ≤2000 字符，按业务语境定制。

### 2. 新增算子

1. 生成新 UUID v4 作 `step.id`，同步写 `pluginConfig.stepId`；`key` / `webPluginKey` / `type` 按算子清单取值（见兄弟 skill `create-unstructured-workflow` 的 `references/operator-reference.md`）；
2. 补 `hops`：断开原连线（删旧 hop）→ 插入新节点前后两条 hop（id 按拼接规则生成）；
3. 检查字段契约：新算子的 `inputColumn` 能从上游落表列取到、`columnMappings` 的 `targetColumn` 在表 schema 中存在（不存在需先扩表——回到 `create-dataset` skill 的 update-dataset 流程）；
4. 画布坐标避开现有节点。

### 3. 删除算子

1. 从 `steps[]` 移除该 step；
2. 清理其作为 source / target 的**所有** hops；上下游需要保持连通时补一条新 hop；
3. 检查下游：被删算子落表的列若仍被下游 `inputColumn` 引用，必须一并调整下游或放弃删除。

### 4. 调整连线

- 只动 `hops[]`；`hop.id` 必须重新按 `source-target` 拼接；
- 每条新连线重新校验字段契约与内容类型兼容（LLM/评分/去重类算子不吃 URL 输入，桥接规则同创建时）。

### 5. 切换数据集版本 / 表

- 环境值字段组（§一 表格中的字段）**成组替换**，全部来自 `get-dataset` 回读；
- 同一算子的 `neuronInput` 与 `neuronOutput` 可指向不同版本（跨版本落表），但各自内部必须自洽。

### 6. 改资源规格

- `setting.requiredResource.mem` / `cpus` 改值后，同时置 `resourceModifiedByUser: true`。

### 7. 开/关多列输出（llm_inference / image_understanding 专属）

开启（单列 → 多列，实测验证过的完整改法）：

1. `neuronModel.enableOutputMultiColumn = true`，新增 `customOutputColumns[{name,type,comment,example}]`（字段级拆分规则写在 comment/example）；
2. `modelPrompt` 同步改写：删除“输出 JSON 格式”类指令，改为整体分析要求；
3. `neuronOutput.columnMappings` 整组替换：删除原单列映射（`answer`/`image_content` 开启后不复存在），改为逐字段 `customOutputColumns[].name → 表列`（表列不存在时先走 `update-dataset-schema` 扩表）；
4. ⚠️ **下游连带变更必查**：原单列（如 JSON 列）此后无算子写入，下游算子（如 text_embedding）若以它为 `inputColumn`，必须同步切到新列（如 summary），否则下游读空。

关闭（多列 → 单列）反向同理：恢复单列映射 + 提示词改回格式化输出 + 下游输入列切回。

## 三、更新自检清单（提交前逐条过）

- [ ] JSON 可解析；顶层为 `{"steps": [...], "hops": [...]}`（无 pipelineDTO 包裹）；
- [ ] 已有 step 的 `id` / `pluginConfig.stepId` 与基线完全一致（未被改动）；
- [ ] 新增 step 满足 `id === stepId`（新 UUID v4）、`webPluginKey === key`、`stepName === name === step.name`；
- [ ] 所有 `hop.source/target` 指向存在的 step；`hop.id === source + "-" + target`；无悬空连线；
- [ ] 每条连线满足字段契约（上游落表列 ⊇ 下游 inputColumn 需求）与内容类型兼容；
- [ ] 环境值均来自回读或 `get-dataset`，成组一致，无占位串残留；
- [ ] `columnMappings` 无 `targetColumn` 为空的行；
- [ ] 未变更部分与基线 diff 为零（`jq -S` 排序后比对，仅剩本次变更项）；
- [ ] 提交后**立即回读校验步骤数/连线数**（防 pipelineDTO 形态误提交导致静默清空）；若开/关了多列输出，验证下游算子输入列已同步切换。
