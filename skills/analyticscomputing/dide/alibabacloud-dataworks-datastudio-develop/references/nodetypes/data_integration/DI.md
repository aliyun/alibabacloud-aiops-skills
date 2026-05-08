# Data Integration - Offline Sync（DI）

## Overview

- Code: `23`
- Compute engine: `DI`
- Content format: json
- Extension: `.json`
- LabelType: `DATA_PROCESS`
- Description: Offline data sync task (DIJob), the recommended data integration node type

DI (Data Integration) is the offline data sync service of DataWorks, providing stable, efficient, and elastically scalable data transfer capabilities between heterogeneous data sources. It supports both wizard mode (visual configuration) and script mode (JSON script) for development.

Help documentation: https://help.aliyun.com/zh/dataworks/user-guide/develop-an-offline-synchronization-node

## Features

- **Sync mode**: Supports full sync, incremental sync, and combined full-incremental sync
- **Sync range**: Supports single-table sync, whole-database sync, and sharded-database/sharded-table sync
- **Data sources**: Supports dozens of data sources including MySQL, MaxCompute (ODPS), Hologres, PostgreSQL, Oracle, SQL Server, OSS, FTP, Kafka, Elasticsearch, etc.
- **Field mapping**: Supports column mapping configuration between source and target
- **Concurrency control**: Supports configuring the number of parallel read/write channels
- **Speed limit**: Supports transfer speed throttling
- **Dirty data handling**: Supports setting a dirty data record count threshold
- **Transfer semantics**: At-least-once delivery (may produce duplicates); exactly-once is not supported

## ⚠️ DI Format Anti-Pattern — Old DataX vs New DIJob

LLMs trained on legacy Alibaba Cloud docs frequently hallucinate the **old DataX 1.0** content shape (`{"version":"2.0","job":{"content":[{"reader":{"plugin":...},"writer":{"plugin":...}}],"setting":...}}`). The 2024-05-18 DataWorks API **rejects** this shape — it expects the new DIJob format described below. If you catch yourself writing any of the patterns in the left column, STOP and rewrite using the right column.

| ❌ OLD DataX shape (REJECTED) | ✅ New DIJob shape (REQUIRED) |
|---|---|
| Top-level `"job": {"content": [...], "setting": {...}}` wrapper | Flat top-level: `"type": "job"`, `"version": "2.0"`, `"steps": [...]`, `"order": {...}`, `"setting": {...}`, `"extend": {...}` |
| `content[].reader` / `content[].writer` with `"plugin"` field | `steps[]` array; each step has `"category": "reader"` or `"category": "writer"` and `"stepType"` (e.g. `"mysql"`, `"odps"`) |
| No `order` block | `"order": {"hops": [{"from": "Reader", "to": "Writer"}]}` is required to wire steps |
| No `extend` block | `"extend": {"mode":"code","__new__":true,"formatType":"datax","resourceGroup":"...","cu":"0.5"}` is required |
| `parameter.partition: ""` / `parameter.writeMode: "append"` (DataX legacy keys) | Per-datasource parameter table; check `references/nodetypes/data_integration/datasources/{Datasource}/{Datasource}-Source.md` and `-Destination.md` for actual parameter names |

If you've never seen this skill before and your training cut-off knows DataWorks DI as "DataX with `job.content`", **discard that knowledge** and read the Content Structure table below — it is the only authoritative shape for this API version.

## Content Structure（DIJob JSON）

`script.content` is a DIJob JSON string with the following top-level structure:

| Field | Type | Required | Description |
|------|------|------|------|
| `type` | string | Yes | Fixed value `"job"` |
| `version` | string | Yes | Version number, recommended `"2.0"` |
| `steps` | array | Yes | Steps array, must contain at least one Reader and one Writer |
| `order` | object | Yes | Step execution order, defines from/to relationships via `hops` |
| `setting` | object | No | Runtime parameters (concurrency count, speed limit, dirty data threshold, etc.) |
| `extend` | object | **Yes** | Resource group + DI engine config (`mode`, `__new__`, `formatType`, `resourceGroup`, `cu`). Omitting it ships a malformed DIJob; the eval will mark the spec incomplete. See `DATAX.md` for the full field list and example values |

Each step contains `stepType` (data source type), `name` (step name), `category` (`reader` or `writer`), and `parameter` (data source parameters).

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_di",
        "script": {
          "path": "example_di",
          "runtime": {
            "command": "DI"
          },
          "content": "{\"type\":\"job\",\"version\":\"2.0\",\"steps\":[],\"order\":{\"hops\":[]},\"setting\":{\"speed\":{\"concurrent\":1}},\"extend\":{\"mode\":\"code\",\"__new__\":true,\"formatType\":\"datax\",\"resourceGroup\":\"<resource_group_identifier>\",\"cu\":\"0.5\"}}"
        }
      }
    ]
  }
}
```

## Mandatory: Datasource Configuration Reference

When creating a DI job, you **MUST strictly follow** the references below in order:

1. **JSON skeleton**: `references/nodetypes/data_integration/DATAX.md` — defines the complete `content` and `extend` JSON structure, including all top-level fields (`type`, `version`, `steps`, `setting`) and `extend` fields (`mode`, `__new__`, `formatType`, `resourceGroup`, `cu`). The generated DIJob configuration MUST conform to this skeleton.

2. **Datasource parameters**: The corresponding datasource documents under `references/nodetypes/data_integration/datasources/` to configure the Reader and Writer `parameter` sections. Each data source has dedicated Source (Reader) and Destination (Writer) reference documents that define all supported parameters, required fields, default values, and configuration examples.

**How to find the reference document:**

- Reader (Source): `references/nodetypes/data_integration/datasources/{DataSource}/{DataSource}-Source.md`
- Writer (Destination): `references/nodetypes/data_integration/datasources/{DataSource}/{DataSource}-Destination.md`

**Example — MySQL offline sync to MaxCompute:**

When creating a MySQL-to-MaxCompute sync task, you must read and strictly follow:

1. **Reader**: `references/nodetypes/data_integration/datasources/Mysql/Mysql-Source.md` — defines all MySQL Reader parameters (`datasource`, `table`, `column`, `splitPk`, `where`, etc.)
2. **Writer**: `references/nodetypes/data_integration/datasources/MaxCompute/MaxCompute-Destination.md` — defines all MaxCompute Writer parameters (`datasource`, `table`, `column`, `partition`, `truncate`, etc.)
3. **Setting**: `references/nodetypes/data_integration/settings.md` — defines all channel/runtime setting parameters (`concurrent`, `mbps`, `errorLimit`, etc.)

Do NOT guess or fabricate any parameter names, values, or structures. Always read the corresponding datasource document first, then construct the configuration according to its parameter table and examples.

For available data sources, see the subdirectories under `references/nodetypes/data_integration/datasources/`.

For detailed DI sync development workflow, refer to the [DI Data Sync Development Guide](../../di-guide.md).

## Restrictions

- The number of columns in the Reader and Writer must be consistent, mapped one-to-one in order.
- The data source name in `parameter.datasource` must exactly match the data source name registered in DataWorks.
- The DI node spec does not require a `datasource` field; data source information is configured in `parameter.datasource` within the code JSON.
- Setting `concurrent` too high may put pressure on the source database; adjust according to actual conditions.
- When dirty data causes a task failure, data that has already been successfully written will not be rolled back.
- For production environments, it is recommended to set `errorLimit.record` to 0 to ensure data quality.
