# `--pipeline-config` 完整骨架手册

> 本文件由 `scripts/split-large-skills.ts` 从 `alibabacloud-dataphin-create-pipeline-task/SKILL.md` 抽离，遵循 agent-skills-spec 渐进披露原则（L3 资源）。

---

## `--pipeline-config` 完整骨架（MySQL → MaxCompute 实例）

`pipeline-config` 由 `Steps`（节点）+ `Hops`（DAG 边）组成；**每个 Step 的 `PluginConfig` 必须是 JSON 字符串**（CLI 不会自动序列化嵌套对象）。

```jsonc
{
  "Steps": [
    {
      "StepName": "MySQL_1",
      "StepType": "input",
      "Key": "mysqlinput",
      "PluginConfig": "<MySQL reader pluginConfig 的 JSON.stringify 结果，见下>"
    },
    {
      "StepName": "MaxCompute_1",
      "StepType": "output",
      "Key": "maxcomputeoutput",
      "PluginConfig": "<MaxCompute writer pluginConfig 的 JSON.stringify 结果，见下>"
    }
  ],
  "Hops": [
    { "Source": "MySQL_1", "Target": "MaxCompute_1" }
  ]
}
```

### MySQL reader 的 `PluginConfig`（mysqlinput）

```jsonc
{
  "dsName": "<mysql数据源名>",            // 必填，对应已建的 MySQL 数据源
  "dsId":   "<数据源ID>",                  // 必填（字符串，避免精度丢失）
  "dsType": "MYSQL",
  "schemaName": "<db-name>",               // 库名
  "tables": ["<table-name>"],              // 单表数组；多表见 multiTable=true
  "multiTable": false,
  "prefix": "<table-name>",                // 通常与 tables[0] 同名
  "driverVersion": "MYSQL_8_X",            // 枚举见下
  "timeZoneFrom": "datasource",
  "noFlowTimeout": 30,                     // 无数据流超时（秒）
  "sqlTimeout": 30,
  "pluginAlias": "mysqlinput",
  "webPluginKey": "mysqlinput",
  "stepName": "MySQL_1",
  "currentProjectId": <project-id-int>,
  "columns": [                             // 字段定义；每列结构见下
    {
      "name": "<col-name>",
      "originalName": "<col-name>",
      "type": "String",                     // CLI 通用类型：String/Long/Double/Boolean/Date
      "rawDataType": "text",                // 源类型，原样
      "dataType": "text",
      "originalType": "text",
      "seqNumber": 1,
      "pk": false, "pt": false,
      "partitioned": false, "partition": false,
      "allowEmpty": false,
      "isSourceData": true,
      "comment": "",
      "guid": ""                            // 可留空
    }
    // ... 其他列
  ],
  "column": [                               // 简版列（与 columns 一一对应）
    { "name": "<col>", "originalName": "<col>", "type": "String",
      "originalType": "text", "id": "<col>", "index": 1,
      "isPk": false, "isSourceData": true, "comment": "" }
  ],
  "desc": "<注释>"
}
```

`driverVersion` 枚举：`MYSQL_5_1_43` / `MYSQL_5_X` / `MYSQL_8_X` / `MYSQL_8_4_X` / `RDS_MYSQL`。

### MaxCompute writer 的 `PluginConfig`（maxcomputeoutput）

```jsonc
{
  "dsName": "<maxcompute数据源名>",
  "dsId":   "<数据源ID>",
  "dsType": "MAX_COMPUTE",
  "dsProjectId": <project-id-int>,
  "table": "<目标表名>",
  "partition": "ds='${bizdate}'",          // 分区表达式；非分区表传空串
  "loadStrategy": "append",                 // append | overwrite
  "prodTableNotExistAction": "autocreate",  // autocreate | error
  "pluginAlias": "maxcomputeoutput",
  "columns": [
    {
      "name": "<col>",
      "originalName": "<col>",
      "type": "String",
      "dataType": "string",
      "rawDataType": "string",
      "originalType": "string",
      "seqNumber": 1,
      "pk": false, "pt": false,
      "partitioned": false, "partition": false,
      "allowEmpty": false,
      "comment": "",
      "guid": ""
    }
  ],
  "columnMappings": [                       // ⚠ 必填：reader↔writer 列映射
    { "order": 0, "sourceColumn": "<src-col>",
      "inputColumnIndex": 0,
      "targetColumn": "<tgt-col>",
      "type": "String", "originalType": "string" }
  ],
  "prodTableDdl": "create table `#{tableName}` (\n  `col` string\n) partitioned by (`ds` string) lifecycle 3600"
                                            // prodTableNotExistAction=autocreate 时生效；#{tableName} 是占位符
}
```

> `columnMappings` 的 `inputColumnIndex` 从 0 开始，必须与 reader `columns` 的顺序对齐。

### Doris reader 的 `PluginConfig`（dorisinput）

```jsonc
{
  "dsName": "<doris数据源名>",
  "dsId":   "<数据源ID>",
  "dsType": "DORIS",
  "schemaName": "<db-name>",               // Doris 的库名
  "tables": ["<table-name>"],
  "multiTable": false,
  "prefix": "<table-name>",
  "timeZoneFrom": "datasource",
  "noFlowTimeout": 30,
  "sqlTimeout": 30,
  "pluginAlias": "dorisinput",
  "webPluginKey": "dorisinput",
  "stepName": "Doris_1",
  "currentProjectId": <project-id-int>,
  "columns": [
    {
      "name": "user_id",
      "originalName": "user_id",
      "type": "String",                     // CLI 通用类型：String / Long / Double / Boolean / Date
      "rawDataType": "largeint",             // 源原始类型
      "dataType": "largeint",
      "originalType": "largeint",
      "seqNumber": 1,
      "pk": true, "pt": false,
      "partitioned": false, "partition": false,
      "allowEmpty": false,
      "isSourceData": true,
      "comment": "", "guid": ""
    }
    // ... 其他列
  ],
  "column": [
    { "name": "user_id", "originalName": "user_id", "type": "String",
      "originalType": "largeint", "id": "user_id", "index": 1,
      "isPk": true, "isSourceData": true, "comment": "" }
  ],
  "desc": ""
}
```

> Doris reader 的结构与 MySQL reader 基本一致，区别：`dsType` = `DORIS`、`pluginAlias` / `webPluginKey` = `dorisinput`、无 `driverVersion` 字段。

### PostgreSQL writer 的 `PluginConfig`（postgresqloutput）

```jsonc
{
  "dsName": "<pg数据源名>",
  "dsId":   "<数据源ID>",
  "dsType": "POSTGRE_SQL",
  "schemaName": "<schema-name>",            // ⚠ 必填：PostgreSQL 的 schema（如 "public"、"dataphin"）
  "table": "<目标表名>",
  "loadStrategy": "append",                 // append | overwrite
  "prodTableNotExistAction": "error",       // ⚠ CLI 场景只用 "error"，autocreate 不生效
  "pluginAlias": "postgresqloutput",
  "webPluginKey": "postgresqloutput",
  "stepName": "PostgreSQL_1",
  "currentProjectId": <project-id-int>,
  "columns": [
    {
      "name": "user_id",
      "originalName": "user_id",
      "type": "String",
      "dataType": "numeric",                // ⚠ 目标列类型必须是 PG 兼容类型
      "rawDataType": "numeric",
      "originalType": "numeric",
      "seqNumber": 1,
      "pk": true, "pt": false,
      "partitioned": false, "partition": false,
      "allowEmpty": false,
      "comment": "", "guid": ""
    }
    // ... 其他列
  ],
  "columnMappings": [                       // ⚠ 必填：reader↔writer 列映射
    {
      "order": 0,
      "sourceColumn": "user_id",            // reader 列名
      "inputColumnIndex": 0,                // 对应 reader columns 的下标（从 0 开始）
      "targetColumn": "user_id",            // writer 列名
      "type": "String",                     // CLI 通用类型
      "originalType": "numeric"             // ⚠ 这里填目标(PG)列类型，不是源列类型
    }
    // ... 其他列
  ]
}
```

> **关键差异**（相对 MaxCompute writer）：
> - `dsType` = `POSTGRE_SQL`（注意下划线）
> - `schemaName` 必填（PG 有 schema 概念，常见值 `public` / 自定义 schema）
> - 无 `partition` / `prodTableDdl` 字段（PG 非分区表场景不需要）
> - `columns` 的 `dataType` / `originalType` 必须填 **PostgreSQL 兼容类型**（numeric / varchar / smallint 等），不能照搬源端类型
> - `columnMappings[].originalType` 填**目标列（PG）**类型

#### Doris → PostgreSQL 常见类型映射

| Doris 源类型 | PostgreSQL 目标类型 | CLI `type` | 说明 |
|---|---|---|---|
| `LARGEINT` | `NUMERIC` | String | Doris LARGEINT 128 位，PG 无直接对等，用 NUMERIC 无精度损失 |
| `BIGINT` | `BIGINT` | Long | 直接对等 |
| `INT` | `INTEGER` | Long | 直接对等 |
| `SMALLINT` | `SMALLINT` | Long | 直接对等 |
| `TINYINT` | `SMALLINT` | Long | PG 无 TINYINT，用 SMALLINT 兼容 |
| `VARCHAR(n)` | `VARCHAR(n)` | String | 直接对等 |
| `CHAR(n)` | `CHAR(n)` | String | 直接对等 |
| `DOUBLE` | `DOUBLE PRECISION` | Double | |
| `FLOAT` | `REAL` | Double | |
| `DECIMAL(p,s)` | `NUMERIC(p,s)` | String | |
| `DATE` | `DATE` | Date | |
| `DATETIME` | `TIMESTAMP` | Date | |
| `BOOLEAN` | `BOOLEAN` | Boolean | |

---
