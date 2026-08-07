# 实时工作流（PipelineType=15）实测笔记

> 来源：真实环境回读的最简实时工作流（reader_dataset → ppt_parse，PipelineType=15），已脱敏。
> **能力定级（实测）**：✅ REALTIME 数据集可经 `create-dataset` 创建（传 RealtimeMetaTableConfig）；✅ 实时工作流可经 `create-work-flow-by-json --task-type 5` 创建（pipelineDTO 形态，回读 PipelineType=15、DAG 完整）——**前提是组装基线来自已有实时工作流的回读（复刻/局部变体）**；❌ 从零设计实时链路仍不支持（算子知识库仅含离线，见 §七未验证项）。

## 一、与离线工作流的核心差异（实测对照）

| 维度 | 离线（PipelineType=14） | 实时（PipelineType=15，实测） |
|---|---|---|
| 链路起点 | `file_basic_info`（扫描文件落元数据表） | **`reader_dataset`**（"读数据集"，StepType=normal，流式源） |
| 输入数据集 | OFFLINE（PG/Milvus 元数据表） | REALTIME（`RealtimeMetaTableConfig` + Kafka 实时元表，**无 MetadataStorageConfig**） |
| **数据传递机制** | hops 只定执行顺序，**数据靠数据集表传递**（上游 columnMappings 落表列 → 下游 sourceColumnName 读表列） | **节点间流式直连**：下游 `inputColumn` 直接引用上游 step 的输出流，不经过表 |
| inputColumn 形态 | `{sourceColumnName: "<表列名>", sourceColumnType: "text", ...}` | `{sourceNodeName, sourceNodeId: "<上游stepId>", sourceColumnName: "<上游stepId>.result.<列名>", sourceColumnType: "VARCHAR(512)"}` |
| 算子输出 | `neuronOutput.columnMappings` 必须落表 | 可 `neuronOutput: {"writeToDataset": false}`（不落表，流式透传） |
| 环境值 | datasetId/versionId/storageDsId/**metadataDsId/datasetTable** 等 | 仅 storageDsId/datasetPath/mountPath/datasetId/datasetVersion(Id)/datasetName/datasetType/datasetProjectId——**无 metadataDsId/datasetTable** |

⚠️ 离线 spec 的「数据传递机制」心智模型（hops 只定顺序、数据靠表）**仅适用于离线**；实时是 hops 即数据流。

## 二、reader_dataset 算子真实骨架（脱敏）

```jsonc
{
  "stepName": "读数据集", "name": "读数据集",
  "stepId": "<UUID，= step.id>",
  "noFlowTimeout": 30, "sqlTimeout": 30,
  "webPluginKey": "reader_dataset",
  "neuronInput": {                       // 指向 REALTIME 数据集（无 metadataDsId/datasetTable）
    "storageDsId": "<文件存储数据源 ID>",
    "datasetPath": "<ProdPath>", "mountPath": "<MountPath>",
    "datasetId": "<datasetId>", "datasetName": "<数据集名>",
    "datasetType": "HYBRID", "datasetProjectId": 1234567890123456,
    "datasetVersion": "V1", "datasetVersionId": "<versionId>",
    "outputSelf": false
  },
  "neuronOutput": {                      // 与 neuronInput 同数据集同版本，outputSelf=true
    "...同 neuronInput 各字段...": "...",
    "outputSelf": true
  },
  "setting": { "requiredResource": { "mem": "2048", "cpus": "1" }, "resourceModifiedByUser": false }
}
```

- 无 `inputColumn` / `columnMappings` / `filters`——它是流式源，输出流的列 = 实时元表 TableSchema 的列；
- outputSelf 规则与离线一致（同数据集同版本 → true）。

## 三、下游算子消费流的 inputColumn 形态（脱敏，以 ppt_parse 为例）

```jsonc
"neuronInput": {
  "inputColumn": [
    {
      "sourceNodeName": "读数据集",                            // 上游 step 名
      "sourceNodeId": "<上游 stepId>",                          // 上游 step 的 UUID
      "sourceColumnName": "<上游stepId>.result.file_path",      // 引用格式：stepId.result.<元表列名>
      "sourceColumnContentType": "URL",                         // URL 语义列（元表列 Url:true）
      "sourceColumnType": "VARCHAR(512)",                       // 元表列类型
      "columnName": "file_url"                                  // 算子输入占位名（与离线一致）
    }
  ]
},
"neuronOutput": { "writeToDataset": false }                     // 不落表（流式）
```

其余区块（neuronModel/neuronParameters/setting）与离线同算子一致。

## 四、REALTIME 数据集契约（get-dataset/list-datasets 回读形态）

```
Scenario=REALTIME / Type=HYBRID / StorageType=OSS / MetadataStorageType=STREAM_TABLE
DataVersionConfig:
  FileStorageConfig: { DataSourceId, ProdPath, MountPath, FileStorageType: "OSS" }
  MetadataStorageConfig: null                    ← 恒为空
  RealtimeMetaTableConfig:                       ← 替代者
    DatasourceType: "KAFKA_9_11"                 ← 固定 Kafka（枚举带版本后缀；type-list 查数据源同理用 KAFKA_9_11，KAFKA 查不到）
    MetaTableName: "<实时元表名>"                 ← 元表需先在研发流程创建（list-files --category streamMeta 可查）
    TableSchema.Columns: [...]                   ← 由元表自动同步，URL 列带 Url:true
```

前置链：Kafka 数据源 → 实时元表（研发流程建）→ REALTIME 数据集（create-dataset 传 RealtimeMetaTableConfig）→ 实时工作流。

## 五、复刻/变体创建的组装要点（实测验证过）

基于回读基线（OA 形态）转 pipelineDTO 形态提交 `create-work-flow-by-json --task-type 5`：

1. 每个 step 新生成 UUID（`id === pluginConfig.stepId`）；
2. **流式 inputColumn 的上游引用必须同步替换**：`sourceNodeId` 与 `sourceColumnName`（格式 `<上游stepId>.result.<列名>`）里的旧 stepId 一并换成新 UUID，否则引用悬空；
3. 数据集环境值（datasetId/datasetName/datasetVersionId）换成目标 REALTIME 数据集的回读值；
4. hops 用新 UUID 拼接（`id = source-target`）；所有 step 带 `distribute: true`、`webConfig: {requireCompeleted: true}`；
5. `--task-type 5`，`--submit false` 存草稿；`--directory` 仅传已存在目录；
6. 创建后**必回读校验**：`PipelineType=15`、步骤数/连线数、reader 指向、流式引用保留（服务端会重建 stepId 并同步引用，属正常）。

## 六、其他实测事实

- `ScheduleConfig` 实时任务同样存在（含 virtual_root_node 上游、DAILY 等字段）——更新时照旧原样回传；
- `Settings` 含流式专属配置（如 `speed.concurrent`）；
- 实时工作流与非结构化离线工作流一样**无 CLI 列表途径**（list-files 全部 11 个 category 均不含），定位键只能来自界面/创建回执；
- `update-pipeline` 更新实时工作流理论上用 `--pipeline-type 15`（未实测）；回读同为 OA 形态（Steps 按 StepName、PluginConfig 字符串）。

## 七、仍未验证项（从零设计实时链路前必须补的知识）

1. ~~`create-work-flow-by-json --task-type 5` 是否接受实时 JSON~~ ✅ 已验证走通（见 §五）；
2. 实时链路末端如何落表/落数据集（本样本 writeToDataset=false，落表算子形态未见）；
3. 其余算子在实时模式下的参数差异（算子配置知识库当前只含离线）；
4. 实时任务的提交/启动/运维链路（本验证仅到草稿创建）。
