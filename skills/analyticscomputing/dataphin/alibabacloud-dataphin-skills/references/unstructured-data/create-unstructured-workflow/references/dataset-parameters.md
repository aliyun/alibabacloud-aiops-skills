# 数据集参数参考：枚举 / 不可变字段 / 建表红线 / CreateCommand 骨架

> `create-dataset` / `get-dataset` / `list-datasets` / `update-dataset` / `delete-dataset` 的业务参数规范。

## 一、核心模型速记

- **类型决定存储组成**：`FILE`（仅文件存储）/ `TABLE`（仅元数据存储）/ `HYBRID`（两者都有）——工作流算子的 `storageDsId`（文件）与 `metadataDsId`（元数据）是否同时出现，由此决定。
- **版本是配置载体**：文件路径、元数据表、表结构全挂在版本（V1/V2…）上；工作流引用是**版本级**（`datasetVersionId`）。
- **创建后不可变（5 字段）**：`Scenario` / `Type` / `StorageType` / `MetadataStorageType` / `ContentType`——建完就锁死，错了只能删了重建。**设计稿必须一次定型并经用户确认。**

## 二、枚举取值

| 字段 | 枚举 | 备注 |
|---|---|---|
| `Scenario` | `OFFLINE`（默认）/ `REALTIME` | 本 skill 仅覆盖 OFFLINE |
| `Type` | `FILE` / `TABLE` / `HYBRID` | — |
| `StorageType` | `OSS` / `S3` | 文件存储 |
| `MetadataStorageType` | `POSTGRESQL` / `MILVUS` / `LINDORM` | 元数据存储（离线） |
| `ContentType` | `GENERAL` / `TEXT` / `IMAGE` / `AUDIO` / `VIDEO` / `TABLE` / `INDEX` | 界面新建仅 4 种（TEXT/IMAGE/AUDIO/VIDEO），API 可建 GENERAL 等全部 7 种 |
| `MetadataStorageMode` | `CREATE`（新建表）/ `EXISTING`（已有表） | VersionConfig 内 |
| 加载策略（工作流算子侧） | `APPEND` / `UPSERT` / `OVERWRITE` | 属工作流算子写入配置，非数据集字段 |

## 三、建表（元数据存储）红线

工作流的输出表就是数据集的元数据表，`create-dataset` 时这些校验是硬的：

1. **表名**：`^[a-z][a-z0-9_]{0,63}$`（小写开头，≤64）；字段名 `^[a-z][a-z0-9_]*$` 且同表唯一。
2. **主键规则随存储类型变**：PostgreSQL = 数值+文本单选；**Milvus 仅 INT64/VARCHAR 单选**；Lindorm 所有类型可多选组合主键。
3. **Milvus 硬约束**：必须同时有主键字段 + 向量字段；且不支持 DDL 导入。
4. **向量字段**：`Type` 用 `FLOAT_VECTOR`（或 `FLOAT16_VECTOR`/`BFLOAT16_VECTOR`），必须配 `VectorIndexConfig{EmbeddingModel, Dimension, IndexType, SimilarityType}`；**Dimension 与 Embedding 算子 `vectorDimension` 一致**（text-embedding-v4 → 1024）。
5. **向量索引类型**：PG pgvector 仅 `IVFFlat` / `HNSW`；Milvus 支持 `AUTOINDEX` / `FLAT` / `IVF_FLAT` / `IVF_SQ8` / `IVF_PQ` / `HNSW` / `DISKANN` 等 14 种；IndexParams：HNSW 传 `{M:30, efConstruction:360}`，IVF_FLAT 传 `{nlist:128}`；SimilarityType：`COSINE`（默认）/ `L2` / `IP`。⚠️ 实测环境差异：独立部署/POC 环境真实范式为 `Type="vector(1024)"` + `EmbeddingModel=模型实例 ID`（非 `FLOAT_VECTOR` + 模型名），建表前先回读同环境已有数据集照真实范式填写。
6. **URL 标记**：仅文本类型字段可 `Url:true`——工作流里 `sourceColumnContentType='URL'` 的列（file_url、markdown_url 等）建表时应带此标记。
7. **名称唯一**：同项目数据集名唯一；同数据集版本号唯一。
8. **表 schema 按链路末端算子的 `columnMappings.targetColumn` 设计**（含中间列）。

## 四、CreateCommand JSON 骨架（`create-dataset --create-command`）

```jsonc
{
  "Name": "解决方案知识库",                 // 必填，同项目唯一
  "Type": "HYBRID",                        // 必填，不可变
  "ContentType": "TEXT",                   // 必填，不可变
  "DirName": "/",                          // 必填，目录
  "Scenario": "OFFLINE",                   // 必填，不可变
  "StorageType": "OSS",                    // 不可变
  "MetadataStorageType": "POSTGRESQL",     // 不可变
  "Description": "PPT 按页解析知识库",
  "Version": "V1",                         // 不传默认 V1
  "VersionConfig": {
    "VersionDescription": "初始版本",
    "FileStorageConfig": {
      "DataSourceId": "<文件存储数据源 ID，字符串>",   // 必填
      "ProdPath": "<生产路径>",                        // 必填（BASIC 项目不需要 DevPath）
      "MountPath": "<挂载路径>"                        // 必填
    },
    "MetadataStorageConfig": {
      "MetadataStorageMode": "CREATE",                 // 必填：CREATE 新建表 / EXISTING 已有表
      "DataSourceId": "<元数据存储数据源 ID，字符串>",  // 必填
      "ProdSchema": "<生产 database.schema>",           // 必填
      "TableName": "solution_kb_pages",                 // 必填，正则见上
      "TableSchema": {
        "Columns": [
          { "Name": "id",            "Type": "int8",         "Pk": true },
          { "Name": "file_url",      "Type": "varchar",      "Pk": false, "Url": true },
          { "Name": "page_content",  "Type": "text",         "Pk": false },
          { "Name": "summary",       "Type": "text",         "Pk": false },
          { "Name": "content_vector","Type": "FLOAT_VECTOR", "Pk": false,
            "VectorIndexConfig": {
              "EmbeddingModel": "text-embedding-v4",
              "Dimension": 1024,
              "IndexType": "HNSW",
              "SimilarityType": "COSINE",
              "IndexParams": { "M": 30, "efConstruction": 360 }
            } }
        ]
      }
    }
  }
}
```

## 五、五个命令的调用差异（易错）

| 命令 | ProjectId 位置与类型 | 关键点 |
|---|---|---|
| `create-dataset` | `--project-id`（String） | 出参 `DatasetId`（业务主键） |
| `update-dataset` | `--project-id`（String） | **`FileId` 必填**（创建时的文件 ID，先 get-dataset 回读）；传哪个字段改哪个 |
| `get-dataset` | `--project-id`（Long） | 出参 DatasetDTO **含完整 VersionList**（工作流环境值来源） |
| `list-datasets` | body 内 `ProjectId`（integer） | 默认不带版本详情，要 `IncludeVersionList=true` |
| `delete-dataset` | `--project-id`（Long） | **无回收站，不自查下游引用**——删除前人工确认无工作流引用 |

## 六、编排纪律

1. **建数据集在前、建工作流在后**；五个不可变字段一次定型。
2. 删数据集/版本前必须**自行先查**下游引用（界面会拦，OpenAPI 不拦）。
3. 建完数据集后必须 `get-dataset` 回读确认（OpenAPI 直连不跑界面的四阶段校验流水线），再往工作流 JSON 填环境值。
4. 权限：调用者 RAM 账号需项目级数据集读写权限，401/403 时先查 RAM 授权与项目权限。
