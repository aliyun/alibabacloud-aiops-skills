# MaxCompute Script（ODPS_SCRIPT）

## Overview

- Compute engine: `ODPS`
- Content format: sql
- Extension: `.ms`
- Code: 24
- Data source type: `odps`
- Description: MaxCompute Script (multi-statement script)

The MaxCompute Script node is based on the MaxCompute 2.0 SQL engine and supports combining multiple SQL statements into a single script that is compiled and executed as a whole. By submitting once to generate a unified execution plan, it improves resource utilization efficiency. It is suitable for complex multi-step query scenarios.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource
- The required tables have been created and data added in MaxCompute

## Core Features

### Multi-statement Script

Supports using the `@variable := SELECT...` syntax to define table variables. Variables can be used in subsequent JOIN, UNION, and other operations, enabling step-by-step processing of complex queries.

```sql
-- MaxCompute Script example
@user_base := SELECT user_id, user_name, city FROM ods_user_info WHERE dt = '${bizdate}';
@order_agg := SELECT user_id, SUM(amount) AS total_amount FROM ods_order WHERE dt = '${bizdate}' GROUP BY user_id;

INSERT OVERWRITE TABLE dwd_user_order PARTITION (dt='${bizdate}')
SELECT a.user_id, a.user_name, a.city, b.total_amount
FROM @user_base a
LEFT JOIN @order_agg b ON a.user_id = b.user_id;
```

### Differences from Regular SQL Nodes

| Dimension | MaxCompute Script | Regular ODPS_SQL |
|------|------------------|--------------|
| Execution mode | Compiled and executed as a whole | Executed statement by statement |
| Number of jobs | Single job | Multiple jobs |
| Applicable scenarios | Complex multi-step queries | Simple single-step operations |

## Restrictions

- At most one SELECT statement with screen-displayed results is supported
- At most one CREATE TABLE AS statement is supported (it must be the last statement)
- If any statement fails, the entire script fails
- Writing to and then reading from the same table is prohibited
- Jobs are generated only after all input data is ready

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_script",
        "script": {
          "path": "example_odps_script",
          "runtime": {
            "command": "ODPS_SQL_SCRIPT"
          },
          "content": "--MaxCompute Script\nSELECT 1;"
        }
      }
    ]
  }
}
```

## Reference

- [MaxCompute Script Node](https://help.aliyun.com/zh/dataworks/user-guide/maxcompute-script-node)
