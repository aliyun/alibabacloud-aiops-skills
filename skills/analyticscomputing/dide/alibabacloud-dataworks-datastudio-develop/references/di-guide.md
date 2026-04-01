# DI Data Synchronization Development Guide

DI (Data Integration) is DataWorks' offline data synchronization service that supports data migration and synchronization across various heterogeneous data sources. This document describes the DI node code format, configuration methods, and common scenarios.

## DI Node Overview

DI node type identifiers in FlowSpec:

| Field | Value |
|------|------|
| `script.runtime.command` | `DI` |
| `script.language` | `di` |
| Code file extension | `.json` |
| `datasourceType` | `null` (no node-level datasource needed) |

The DI node's code file is a JSON-formatted DIJob definition that describes the complete configuration for data reading (Reader) and writing (Writer).

---

## DIJob JSON Structure

Top-level structure of the DI code file:

```json
{
  "type": "job",
  "version": "2.0",
  "steps": [
    { "stepType": "mysql", "name": "Reader", "category": "reader", "parameter": { ... } },
    { "stepType": "odps", "name": "Writer", "category": "writer", "parameter": { ... } }
  ],
  "order": {
    "hops": [
      { "from": "Reader", "to": "Writer" }
    ]
  },
  "setting": {
    "speed": { "concurrent": 3, "throttle": false },
    "errorLimit": { "record": 0 }
  }
}
```

### Top-Level Fields

| Field | Type | Required | Description |
|------|------|------|------|
| `type` | string | Yes | Fixed value `"job"` |
| `version` | string | Yes | Version number, recommended `"2.0"` |
| `steps` | array | Yes | Step array, must contain at least one Reader and one Writer |
| `order` | object | Yes | Step execution order |
| `setting` | object | No | Runtime parameter configuration |

---

## steps Configuration

The `steps` array contains two types of steps: Reader (reads source data) and Writer (writes to target).

### Step Common Fields

| Field | Type | Required | Description |
|------|------|------|------|
| `stepType` | string | Yes | Data source type identifier (e.g., `mysql`, `odps`, `oss`, `hologres`) |
| `name` | string | Yes | Step name, referenced in `order.hops` |
| `category` | string | Yes | Step category: `"reader"` or `"writer"` |
| `parameter` | object | Yes | Step parameters, varies by data source type |

---

## Reader Configuration Details

### MySQL Reader

Reads data from a MySQL database.

```json
{
  "stepType": "mysql",
  "name": "Reader",
  "category": "reader",
  "parameter": {
    "datasource": "my_mysql_datasource",
    "column": ["id", "name", "age", "created_at"],
    "connection": [
      {
        "table": ["user_info"],
        "datasource": "my_mysql_datasource"
      }
    ],
    "where": "created_at >= '${bizdate} 00:00:00'",
    "splitPk": "id",
    "encoding": "UTF-8"
  }
}
```

| Parameter | Type | Required | Description |
|------|------|------|------|
| `datasource` | string | Yes | Datasource name (a MySQL datasource registered in DataWorks) |
| `column` | array[string] | Yes | List of column names to read |
| `connection` | array | Yes | Connection configuration, contains table name and datasource |
| `connection[].table` | array[string] | Yes | Table name list |
| `connection[].datasource` | string | Yes | Datasource name |
| `where` | string | No | Filter condition (SQL WHERE clause) |
| `splitPk` | string | No | Split key for concurrent reads, recommend using the primary key |
| `encoding` | string | No | Character encoding, default `UTF-8` |

### MaxCompute (ODPS) Reader

Reads data from a MaxCompute table.

```json
{
  "stepType": "odps",
  "name": "Reader",
  "category": "reader",
  "parameter": {
    "datasource": "odps_first",
    "table": "ods_user_info",
    "column": [
      {"name": "id", "type": "bigint"},
      {"name": "name", "type": "string"},
      {"name": "age", "type": "bigint"}
    ],
    "partition": "dt=${bizdate}"
  }
}
```

| Parameter | Type | Required | Description |
|------|------|------|------|
| `datasource` | string | Yes | MaxCompute datasource name |
| `table` | string | Yes | Table name |
| `column` | array | Yes | Column definitions, can be strings (column names) or objects (with name and type) |
| `partition` | string | No | Partition filter condition (e.g., `dt=20260321`) |
| `where` | string | No | Filter condition |

### OSS Reader

Reads data from OSS object storage.

```json
{
  "stepType": "oss",
  "name": "Reader",
  "category": "reader",
  "parameter": {
    "datasource": "my_oss_datasource",
    "object": ["data/input/user_info_${bizdate}.csv"],
    "column": [
      {"type": "long", "index": 0},
      {"type": "string", "index": 1},
      {"type": "long", "index": 2},
      {"type": "date", "index": 3}
    ],
    "fieldDelimiter": ",",
    "encoding": "UTF-8",
    "fileFormat": "csv"
  }
}
```

| Parameter | Type | Required | Description |
|------|------|------|------|
| `datasource` | string | Yes | OSS datasource name |
| `object` | array[string] | Yes | File path list (supports wildcards) |
| `column` | array | Yes | Column definitions, with `type` (data type) and `index` (column position, starting from 0) |
| `fieldDelimiter` | string | No | Field delimiter |
| `encoding` | string | No | Character encoding, default `UTF-8` |
| `fileFormat` | string | No | File format: `csv`, `text`, `parquet`, `orc`, `json` |

### Hologres Reader

Reads data from Hologres.

```json
{
  "stepType": "hologres",
  "name": "Reader",
  "category": "reader",
  "parameter": {
    "datasource": "my_holo_datasource",
    "table": "public.user_info",
    "column": ["id", "name", "age"]
  }
}
```

### PostgreSQL Reader

Reads data from PostgreSQL.

```json
{
  "stepType": "postgresql",
  "name": "Reader",
  "category": "reader",
  "parameter": {
    "datasource": "my_pg_datasource",
    "column": ["id", "name", "age"],
    "connection": [
      {
        "table": ["user_info"],
        "datasource": "my_pg_datasource"
      }
    ],
    "where": "created_at >= '${bizdate}'"
  }
}
```

---

## Writer Configuration Details

### MaxCompute (ODPS) Writer

Writes to a MaxCompute table.

```json
{
  "stepType": "odps",
  "name": "Writer",
  "category": "writer",
  "parameter": {
    "datasource": "odps_first",
    "table": "dwd_user_info",
    "column": [
      {"name": "id", "type": "bigint"},
      {"name": "name", "type": "string"},
      {"name": "age", "type": "bigint"}
    ],
    "partition": "dt=${bizdate}",
    "truncate": true
  }
}
```

| Parameter | Type | Required | Description |
|------|------|------|------|
| `datasource` | string | Yes | MaxCompute datasource name |
| `table` | string | Yes | Target table name |
| `column` | array | Yes | Column definitions, can be strings or objects (with name and type) |
| `partition` | string | No | Target partition (e.g., `dt=20260321`) |
| `truncate` | boolean | No | Whether to clear the partition/table first, default `true` |

### Hologres Writer

Writes to a Hologres table.

```json
{
  "stepType": "hologres",
  "name": "Writer",
  "category": "writer",
  "parameter": {
    "datasource": "my_holo_datasource",
    "table": "public.dwd_user_info",
    "column": ["id", "name", "age", "updated_at"],
    "writeMode": "insertOrReplace",
    "batchSize": 512
  }
}
```

| Parameter | Type | Required | Description |
|------|------|------|------|
| `datasource` | string | Yes | Hologres datasource name |
| `table` | string | Yes | Target table name (including schema, e.g., `public.table_name`) |
| `column` | array[string] | Yes | Column name list |
| `writeMode` | string | No | Write mode: `insertOrIgnore` (ignore on conflict), `insertOrReplace` (overwrite on conflict), `insertOrUpdate` (update on conflict) |
| `conflictMode` | string | No | Conflict handling mode |
| `batchSize` | integer | No | Batch write size, default 512 |

### MySQL Writer

Writes to a MySQL database.

```json
{
  "stepType": "mysql",
  "name": "Writer",
  "category": "writer",
  "parameter": {
    "datasource": "my_mysql_datasource",
    "column": ["id", "name", "age", "updated_at"],
    "connection": [
      {
        "table": ["target_user_info"],
        "datasource": "my_mysql_datasource"
      }
    ],
    "writeMode": "replace",
    "preSql": ["DELETE FROM target_user_info WHERE dt='${bizdate}'"],
    "postSql": [],
    "batchSize": 1024
  }
}
```

| Parameter | Type | Required | Description |
|------|------|------|------|
| `datasource` | string | Yes | MySQL datasource name |
| `column` | array[string] | Yes | Column name list |
| `connection` | array | Yes | Connection configuration, contains target table name and datasource |
| `writeMode` | string | No | Write mode: `insert`, `replace`, `update` |
| `preSql` | array[string] | No | SQL statements to execute before writing |
| `postSql` | array[string] | No | SQL statements to execute after writing |
| `batchSize` | integer | No | Batch write size, default 1024 |

### OSS Writer

Writes to OSS object storage.

```json
{
  "stepType": "oss",
  "name": "Writer",
  "category": "writer",
  "parameter": {
    "datasource": "my_oss_datasource",
    "object": "data/output/result_${bizdate}.csv",
    "column": [
      {"name": "id", "type": "long"},
      {"name": "name", "type": "string"},
      {"name": "amount", "type": "double"}
    ],
    "writeMode": "truncate",
    "fieldDelimiter": ",",
    "encoding": "UTF-8",
    "fileFormat": "csv"
  }
}
```

| Parameter | Type | Required | Description |
|------|------|------|------|
| `datasource` | string | Yes | OSS datasource name |
| `object` | string | Yes | Output file path |
| `column` | array | Yes | Column definitions, with `name` (column name) and `type` (data type) |
| `writeMode` | string | No | Write mode: `truncate` (overwrite), `append`, `nonConflict` (write only when no conflict) |
| `fieldDelimiter` | string | No | Field delimiter |
| `encoding` | string | No | Character encoding, default `UTF-8` |
| `fileFormat` | string | No | File format: `csv`, `text`, `parquet`, `orc`, `json` |

---

## setting Configuration

`setting` defines the runtime parameters for the data synchronization task.

```json
"setting": {
  "speed": {
    "concurrent": 3,
    "throttle": false,
    "mbps": 10,
    "dmu": 5
  },
  "errorLimit": {
    "record": 0
  }
}
```

### speed (Speed Configuration)

| Parameter | Type | Description |
|------|------|------|
| `concurrent` | integer | Concurrency level, i.e., the number of simultaneous data channels, minimum 1 |
| `throttle` | boolean | Whether to enable throttling. When `true`, bandwidth is limited by `mbps` |
| `mbps` | number | Throttle value (MB/s), only effective when `throttle` is `true` |
| `dmu` | integer | Data Migration Unit count, affects resource allocation |

### errorLimit (Error Tolerance Configuration)

| Parameter | Type | Description |
|------|------|------|
| `record` | integer | Maximum number of dirty data records allowed. `0` means no dirty data is allowed; the task will fail if the threshold is exceeded |

---

## order Configuration

`order` defines the execution order between steps.

```json
"order": {
  "hops": [
    { "from": "Reader", "to": "Writer" }
  ]
}
```

- `from`: The `name` of the source step
- `to`: The `name` of the target step
- For simple single-Reader single-Writer scenarios, only one hop is needed

---

## Common Data Synchronization Scenarios

### Scenario 1: MySQL to MaxCompute

Synchronize MySQL business data to MaxCompute for offline analysis.

```json
{
  "type": "job",
  "version": "2.0",
  "steps": [
    {
      "stepType": "mysql",
      "name": "Reader",
      "category": "reader",
      "parameter": {
        "datasource": "rds_prod",
        "column": ["id", "user_name", "email", "status", "created_at"],
        "connection": [
          {
            "table": ["t_user"],
            "datasource": "rds_prod"
          }
        ],
        "where": "created_at >= '${bizdate} 00:00:00' AND created_at < '${bizdate} 23:59:59'",
        "splitPk": "id"
      }
    },
    {
      "stepType": "odps",
      "name": "Writer",
      "category": "writer",
      "parameter": {
        "datasource": "odps_first",
        "table": "ods_user",
        "column": [
          {"name": "id", "type": "bigint"},
          {"name": "user_name", "type": "string"},
          {"name": "email", "type": "string"},
          {"name": "status", "type": "bigint"},
          {"name": "created_at", "type": "datetime"}
        ],
        "partition": "dt=${bizdate}",
        "truncate": true
      }
    }
  ],
  "order": {
    "hops": [{ "from": "Reader", "to": "Writer" }]
  },
  "setting": {
    "speed": { "concurrent": 5, "throttle": false },
    "errorLimit": { "record": 0 }
  }
}
```

### Scenario 2: MySQL to Hologres

Synchronize MySQL data to Hologres for real-time analysis.

```json
{
  "type": "job",
  "version": "2.0",
  "steps": [
    {
      "stepType": "mysql",
      "name": "Reader",
      "category": "reader",
      "parameter": {
        "datasource": "rds_prod",
        "column": ["id", "product_name", "price", "stock"],
        "connection": [
          {
            "table": ["t_product"],
            "datasource": "rds_prod"
          }
        ]
      }
    },
    {
      "stepType": "hologres",
      "name": "Writer",
      "category": "writer",
      "parameter": {
        "datasource": "holo_prod",
        "table": "public.ods_product",
        "column": ["id", "product_name", "price", "stock"],
        "writeMode": "insertOrReplace",
        "batchSize": 512
      }
    }
  ],
  "order": {
    "hops": [{ "from": "Reader", "to": "Writer" }]
  },
  "setting": {
    "speed": { "concurrent": 3, "throttle": false },
    "errorLimit": { "record": 0 }
  }
}
```

### Scenario 3: MaxCompute to MySQL

Export MaxCompute analysis results back to MySQL for use by business systems.

```json
{
  "type": "job",
  "version": "2.0",
  "steps": [
    {
      "stepType": "odps",
      "name": "Reader",
      "category": "reader",
      "parameter": {
        "datasource": "odps_first",
        "table": "ads_user_report",
        "column": [
          {"name": "user_id", "type": "bigint"},
          {"name": "total_orders", "type": "bigint"},
          {"name": "total_amount", "type": "double"},
          {"name": "report_date", "type": "string"}
        ],
        "partition": "dt=${bizdate}"
      }
    },
    {
      "stepType": "mysql",
      "name": "Writer",
      "category": "writer",
      "parameter": {
        "datasource": "rds_prod",
        "column": ["user_id", "total_orders", "total_amount", "report_date"],
        "connection": [
          {
            "table": ["t_user_report"],
            "datasource": "rds_prod"
          }
        ],
        "writeMode": "replace",
        "preSql": ["DELETE FROM t_user_report WHERE report_date='${bizdate}'"],
        "batchSize": 1024
      }
    }
  ],
  "order": {
    "hops": [{ "from": "Reader", "to": "Writer" }]
  },
  "setting": {
    "speed": { "concurrent": 3, "throttle": true, "mbps": 5 },
    "errorLimit": { "record": 0 }
  }
}
```

### Scenario 4: OSS to MaxCompute

Import CSV files from OSS into MaxCompute.

```json
{
  "type": "job",
  "version": "2.0",
  "steps": [
    {
      "stepType": "oss",
      "name": "Reader",
      "category": "reader",
      "parameter": {
        "datasource": "oss_data_lake",
        "object": ["data/daily/${bizdate}/*.csv"],
        "column": [
          {"type": "long", "index": 0},
          {"type": "string", "index": 1},
          {"type": "string", "index": 2},
          {"type": "double", "index": 3},
          {"type": "date", "index": 4}
        ],
        "fieldDelimiter": ",",
        "encoding": "UTF-8",
        "fileFormat": "csv"
      }
    },
    {
      "stepType": "odps",
      "name": "Writer",
      "category": "writer",
      "parameter": {
        "datasource": "odps_first",
        "table": "ods_external_data",
        "column": [
          {"name": "id", "type": "bigint"},
          {"name": "category", "type": "string"},
          {"name": "description", "type": "string"},
          {"name": "amount", "type": "double"},
          {"name": "event_date", "type": "datetime"}
        ],
        "partition": "dt=${bizdate}",
        "truncate": true
      }
    }
  ],
  "order": {
    "hops": [{ "from": "Reader", "to": "Writer" }]
  },
  "setting": {
    "speed": { "concurrent": 3, "throttle": false },
    "errorLimit": { "record": 10 }
  }
}
```

---

## DI Node Creation Process

The DI node creation process is the same as for regular nodes; the only difference is that the code file is in JSON format.

```bash
# 1. Create the node directory
mkdir -p ./sync_user_to_odps

# 2. Copy the node template
# Refer to the DI template in assets/templates/ and modify accordingly

# 3. Edit spec.json
#    - name: sync_user_to_odps
#    - script.runtime.command: DI
#    - script.language: di
#    - No need to configure datasource (DI node datasources are configured in the code JSON)

# 4. Write the DI code file
#    Create sync_user_to_odps.json and fill in the DIJob JSON

# 5. Create dataworks.properties
cat > ./sync_user_to_odps/dataworks.properties << 'EOF'
projectIdentifier=my_project
spec.runtimeResource.resourceGroup=S_res_group_xxx
EOF

# 6. Build spec JSON and submit via API
aliyun dataworks-public CreateNode \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --Spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Important Notes

1. **Datasource name consistency**: The datasource name in `parameter.datasource` and `connection[].datasource` must exactly match the datasource name registered in DataWorks
2. **Column count alignment**: The number of columns in Reader and Writer must be identical, with one-to-one correspondence in order
3. **Partition format**: MaxCompute partition values use the `dt=${bizdate}` format, supporting scheduling parameter substitution
4. **Concurrency setting**: Setting `concurrent` too high may put excessive load on the source database; adjust based on actual conditions
5. **Dirty data handling**: For production environments, it is recommended to set `errorLimit.record` to 0 to ensure data quality
6. **DI nodes have no datasource field**: Unlike ODPS_SQL and similar nodes, the DI node's spec.json does not require a `datasource` field; datasource information is configured in `parameter.datasource` within the code JSON
