# 数据集参数参考：枚举 / 组合矩阵 / 不可变字段 / 建表红线 / 入参出参骨架

> `create-dataset` / `update-dataset` 的业务参数权威参考（离线场景为主）。

## 一、核心模型

- **数据集（Dataset）**：非结构化数据的逻辑容器；**版本（V1/V2…）是配置载体**——文件路径、元数据表、表结构全挂在版本上，下游工作流引用是版本级（`datasetVersionId`）。
- **类型决定存储组成**：`FILE`（仅文件存储）/ `TABLE`（仅元数据存储）/ `HYBRID`（两者都有）。
- **创建后不可变（5 字段）**：`Scenario` / `Type` / `StorageType` / `MetadataStorageType` / `ContentType`——建完锁死（如改 Scenario 报 `SCENARIO_NOT_ALLOW_MODIFY`），错了只能删了重建。

## 二、枚举取值

| 字段 | 枚举 | 备注 |
|---|---|---|
| `Scenario` | `OFFLINE`（默认）/ `REALTIME` | REALTIME 已实测可经 API 创建（见 §八），需环境开关 + 实时元表前置 |
| `Type` | `FILE` / `TABLE` / `HYBRID` | 实时场景仅 TABLE/HYBRID（违反报 `REALTIME_DATASET_TYPE_NOT_SUPPORTED`） |
| `StorageType` | `OSS` / `S3` | 文件存储 |
| `MetadataStorageType` | `POSTGRESQL` / `MILVUS` / `LINDORM` | 离线元数据存储；实时固定 STREAM_TABLE |
| `ContentType` | `GENERAL` / `TEXT` / `IMAGE` / `AUDIO` / `VIDEO` / `TABLE` / `INDEX` | 界面新建仅 TEXT/IMAGE/AUDIO/VIDEO 4 种；API 可建全部 7 种 |
| `MetadataStorageMode` | `CREATE`（新建表）/ `EXISTING`（已有表） | CREATE 手动给表名，EXISTING 选已有表 |

### 场景 × 类型 × 存储组合矩阵

| 场景 | 可用类型 | 对象存储 | 元数据存储 |
|------|---------|---------|-----------|
| OFFLINE | FILE / TABLE / HYBRID | OSS / S3 | POSTGRESQL / MILVUS / LINDORM |
| REALTIME | TABLE / HYBRID | OSS | 实时元表（固定） |

## 三、约束红线（违反即报错）

| # | 约束 | 违反后果 |
|---|------|---------|
| 1 | 同项目内数据集名称唯一 | `DATASET_NAME_DUPLICATE` |
| 2 | 同数据集下版本号唯一 | `DATASET_VERSION_DUPLICATE` |
| 3 | 五个不可变字段创建后不可改 | 如 `SCENARIO_NOT_ALLOW_MODIFY` |
| 4 | 元数据表名 `^[a-z][a-z0-9_]{0,63}$`；字段名 `^[a-z][a-z0-9_]*$` 同表唯一 | 参数校验失败 |
| 5 | 同一数据集不能并发提交（排他锁） | `DATASET_IS_PUBLISHING` |
| 6 | 数据集至少保留 1 个版本 | 删除最后版本被拒 |
| 7 | Milvus 必须同时有主键字段 + 向量字段；主键仅 INT64/VARCHAR 单选；不支持 DDL 导入 | 提交校验拦截 |
| 8 | 向量字段必须配 `EmbeddingModel + Dimension` | 提交校验拦截 |
| 9 | 仅文本类型字段可 `Url:true` | 类型变化时标记失效 |

主键规则随存储类型变：PostgreSQL = 数值+文本单选；Milvus 仅 INT64/VARCHAR 单选；Lindorm 所有类型可多选组合主键。

向量索引：PG pgvector 仅 `IVFFlat`/`HNSW`；Milvus 支持 `AUTOINDEX`/`FLAT`/`IVF_FLAT`/`IVF_SQ8`/`IVF_PQ`/`HNSW`/`DISKANN` 等 14 种；`IndexParams`：HNSW `{M:30, efConstruction:360}`、IVF_FLAT `{nlist:128}`；`SimilarityType`：`COSINE`（默认）/`L2`/`IP`；Dimension 与下游 Embedding 算子 `vectorDimension` 一致（如 text-embedding-v4 → 1024）。

> ⚠️ **向量列写法有环境差异**（实测）：公共云契约为 `Type="FLOAT_VECTOR"` + `EmbeddingModel=模型名`；独立部署/POC 环境真实范式为 `Type="vector(1024)"` + `EmbeddingModel=模型实例 ID`（如 `8762613`）、`IndexParams` 如 `{M:16, EfConstruction:200}`。建表前先 `list-datasets --include-version-list true` 回读同环境已有数据集的列定义，照真实范式填写。

## 四、CreateCommand JSON 骨架（`create-dataset --create-command`）

```jsonc
{
  "Name": "解决方案知识库",                 // 必填，同项目唯一
  "Type": "HYBRID",                        // 必填，不可变
  "ContentType": "TEXT",                   // 必填，不可变
  "DirName": "/",                          // 必填，目录
  "Scenario": "OFFLINE",                   // 必填，不可变
  "StorageType": "OSS",                    // 不可变（Type 含文件存储时给）
  "MetadataStorageType": "POSTGRESQL",     // 不可变（Type 含元数据存储时给）
  "Description": "PPT 按页解析知识库",
  "Owner": "300000913",                    // 可选，负责人 ID，多个逗号分隔
  "Version": "V1",                         // 不传默认 V1
  "VersionConfig": {
    "VersionDescription": "初始版本",
    "FileStorageConfig": {                 // Type=FILE/HYBRID 时必填
      "DataSourceId": "<文件存储数据源 ID，字符串>",
      "ProdPath": "<生产路径>",             // BASIC 项目不需要 DevPath
      "MountPath": "<挂载路径>"
    },
    "MetadataStorageConfig": {             // Type=TABLE/HYBRID 时必填
      "MetadataStorageMode": "CREATE",
      "DataSourceId": "<元数据存储数据源 ID，字符串>",
      "ProdSchema": "<生产 database.schema>",
      "TableName": "solution_kb_pages",
      "TableSchema": {
        "Columns": [
          { "Name": "id",            "Type": "int8",         "Pk": true },
          { "Name": "file_url",      "Type": "varchar",      "Pk": false, "Url": true },
          { "Name": "page_content",  "Type": "text",         "Pk": false },
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

`TableSchema.Columns[]` 字段说明：`Name`/`Type` 必填；`Pk` 必填（是否主键）；`Url` 可选（仅文本类型）；`Comment` 可选；`ElementType`/`MaxCapacity` 仅 `Type=ARRAY` 时有效（默认容量 4096）；`VectorIndexConfig` 仅向量类型（`FLOAT_VECTOR`/`FLOAT16_VECTOR`/`BFLOAT16_VECTOR`）时配置。

## 五、UpdateCommand JSON 骨架（`update-dataset --update-command`）

```jsonc
{
  "Id": 12345,                     // 必填，数据集 ID（业务主键）
  "FileId": "<创建时的文件 ID>",    // ★ 必填（即使只改名字）——先 get-dataset 回读取
  "Name": "新名称",                 // 可选，传哪个改哪个
  "Description": "...",            // 可选
  "Version": "V2",                 // 可选，新增/更新版本
  "VersionConfig": { ... }         // 可选，结构同 CreateCommand.VersionConfig
}
```

> 五个不可变字段（Scenario/Type/StorageType/MetadataStorageType/ContentType）**不要**放进 UpdateCommand——即使字段在契约中存在，修改也会被拒。

## 六、DatasetDTO 出参速查（get-dataset / list-datasets 返回）

| 字段 | 说明 |
|---|---|
| `Id` | 数据集 ID（业务主键，19 位大整数按字符串记录） |
| `Name` / `Type` / `Scenario` / `StorageType` / `MetadataStorageType` / `ContentType` | 与创建入参对应（核对五不可变字段） |
| `FileId` / `Directory` | 文件 ID（update 必填项来源）/ 目录 |
| `OwnerList[]` | `{UserId, UserName}` |
| `VersionList[].Id` | **版本 ID（即下游工作流的 datasetVersionId）** |
| `VersionList[].Version` | 版本号（V1/V2…） |
| `VersionList[].DataVersionConfig.FileStorageConfig` | `DataSourceId`（storageDsId）/ `ProdPath` / `MountPath` |
| `VersionList[].DataVersionConfig.MetadataStorageConfig` | `DataSourceId`（metadataDsId）/ `TableName` / `TableSchema.Columns[]` |

> 下游工作流环境值映射的完整表见同模块 [`../../create-unstructured-workflow/references/workflow-json-spec.md`](../../create-unstructured-workflow/references/workflow-json-spec.md) §四。

## 七、编排纪律

1. **建数据集在前、建工作流在后**；五个不可变字段一次定型并经用户确认。
2. 删数据集/版本前必须**自行先查**下游引用（界面会拦，OpenAPI 不拦、无回收站）。
3. 建完必 `get-dataset` 回读逐项核对（OpenAPI 直连不跑界面四阶段校验流水线）。
4. 权限：调用者 RAM 账号需项目级数据集读写权限；401/403 先查 RAM 授权与租户 ID。

## 八、REALTIME 数据集创建（实测验证 [Agent 自主发现]）

**前置链**：Kafka 数据源（Type 枚举 `KAFKA_9_11`，⚠️ `--type-list KAFKA` 查不到）→ 实时元表 → REALTIME 数据集。

> ⚠️ **实时元表无 skill/OpenAPI 创建能力**：元表只能在 Dataphin 界面（研发 → 实时元表）预先创建。因此创建 REALTIME 数据集前必须：
> 1. **先向用户交代这一现实**（元表需界面先建，Agent 无法代劳）；
> 2. **引导用户提供已存在的元表名称**（MetaTableName）——可用 `list-files --category streamMeta --project-id ...` 列出项目内已有元表供用户选；项目内为空则请用户先去界面建；
> 3. TableSchema 列定义与元表保持一致（由元表同步，不要自行发挥）。

**创建命令**（与离线同构，差异在 scenario/metadata-storage-type 与 VersionConfig 内容）：

```bash
aliyun dataphin-public create-dataset --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --name "<名>" --type HYBRID --content-type TEXT --dir-name / \
  --scenario REALTIME --storage-type OSS --metadata-storage-type STREAM_TABLE \
  --version V1 --version-config "$(cat version-config.json)"
```

**VersionConfig 骨架**（用 `RealtimeMetaTableConfig` 替代 MetadataStorageConfig）：

```jsonc
{
  "VersionDescription": "...",
  "FileStorageConfig": { "DataSourceId": "<OSS 数据源 ID>", "ProdPath": "<路径>", "MountPath": "<挂载>" },
  "RealtimeMetaTableConfig": {
    "DatasourceType": "KAFKA_9_11",          // 固定 Kafka（带版本后缀）
    "MetaTableName": "<已存在的实时元表名>",   // 元表需先建
    "ProjectId": 1234567890123456,
    "TableSchema": { "Columns": [           // 与元表一致；URL 语义列带 Url:true
      { "Name": "id", "Type": "VARCHAR(512)", "Pk": false, "Url": false },
      { "Name": "file_path", "Type": "VARCHAR(512)", "Pk": false, "Url": true }
    ]}
  }
}
```

**回读契约特征**（验证时核对）：`MetadataStorageType=STREAM_TABLE`；`DataVersionConfig.MetadataStorageConfig` 恒为 `null`；元表结构落在 `RealtimeMetaTableConfig.TableSchema`。下游衔接：实时工作流的 reader_dataset 引用此数据集（见兄弟 skill `create-unstructured-workflow` 的 `references/realtime-workflow-notes.md`）。
