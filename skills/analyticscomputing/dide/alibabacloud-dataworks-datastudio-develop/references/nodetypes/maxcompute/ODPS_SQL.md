# MaxCompute SQL（ODPS_SQL）

## Overview

- Compute engine: `ODPS`
- Content format: sql
- Extension: `.sql`
- Code: 10
- Data source type: `odps`
- Description: MaxCompute SQL statements

The MaxCompute SQL node is the most commonly used data processing node in DataWorks. It is used to execute standard SQL statements on MaxCompute (formerly ODPS). It is suitable for distributed processing scenarios involving massive data (TB-level) with low real-time requirements, supporting common operations such as DDL, DML, DQL, etc.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource
- The RAM account must have **Developer** or **Workspace Admin** role permissions

## Core Features

### SQL Syntax

Supports MaxCompute SQL syntax, including DDL, DML, DQL statements, as well as built-in functions and user-defined functions (UDFs). Supports dynamic scheduling parameter input in the `${variable_name}` format.

```sql
-- Create partitioned table
CREATE TABLE IF NOT EXISTS dwd_user_info (
  user_id   BIGINT,
  user_name STRING,
  age       INT
) PARTITIONED BY (dt STRING)
LIFECYCLE 90;

-- Partition write (using scheduling parameters)
INSERT OVERWRITE TABLE dwd_user_info PARTITION (dt='${bizdate}')
SELECT user_id, user_name, age
FROM ods_user_info
WHERE dt = '${bizdate}';

-- Aggregation query
SELECT city, COUNT(*) AS cnt
FROM dwd_user_info
WHERE dt = '${bizdate}'
GROUP BY city
ORDER BY cnt DESC
LIMIT 100;
```

### Scheduling Parameters

Supports defining dynamic parameters using the `${variable_name}` format. Values are assigned to variables in the scheduling configuration. Common system parameters include:

- `${bizdate}`: Business date (yyyymmdd format)
- `${yyyymmdd}`: Run date
- `${yyyy-mm-dd}`: Run date (hyphenated format)

### Execution Notes

- In Data Studio, all keyword statements are merged and executed upfront; in the scheduling environment, statements are executed in the actual written order
- Only single-line comments `--` are supported

## Restrictions

| Restriction | Requirement |
|-------|------|
| Code size | Up to 128 KB |
| SQL command count | Up to 200 |
| Query result rows | Up to 10,000 |
| Query result size | Up to 10 MB |
| Comment style | Only single-line comments `--` are supported |

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_sql",
        "script": {
          "path": "example_odps_sql",
          "runtime": {
            "command": "ODPS_SQL"
          },
          "content": "SELECT col1, COUNT(*) AS cnt FROM my_table WHERE dt='${bizdate}' GROUP BY col1;"
        }
      }
    ]
  }
}
```

### Complete Spec Example

A complete node definition including scheduling, data source, and dependency configuration:

```json
{
  "version": "1.1.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "dwd_user_info",
        "recurrence": "Normal",
        "instanceMode": "T+1",
        "rerunMode": "Allowed",
        "script": {
          "path": "dwd_user_info",
          "language": "odps-sql",
          "runtime": {
            "command": "ODPS_SQL"
          },
          "parameters": [
            {
              "name": "bizdate",
              "scope": "NodeParameter",
              "type": "System",
              "value": "$yyyymmdd",
              "artifactType": "Variable"
            }
          ]
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 00 02 * * ?",
          "startTime": "1970-01-01 00:00:00",
          "endTime": "9999-01-01 00:00:00",
          "timezone": "Asia/Shanghai"
        },
        "datasource": {
          "name": "odps_first",
          "type": "odps"
        },
        "runtimeResource": {
          "resourceGroup": "S_res_group_XXX"
        }
      }
    ]
  }
}
```

## Reference

- [MaxCompute SQL Node](https://help.aliyun.com/zh/dataworks/user-guide/maxcompute-sql-node)
