# MariaDB（Mariadb）

## Overview

- Compute engine: `DATABASE`
- Content format: sql
- Extension: `.sql`
- Data source type: `mariadb`
- Description: Execute SQL statements against MariaDB database

Used to directly execute SQL queries and data processing against MariaDB database to execute SQL queries and data processing. The corresponding data source type must be registered in the workspace beforehand.

## Prerequisites

- The data source type has been added to the DataWorks workspace MariaDB type data source
- The data source connectivity test has passed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_mariadb",
        "script": {
          "path": "example_mariadb",
          "runtime": {
            "command": "Mariadb"
          },
          "content": "SELECT 1;"
        }
      }
    ]
  }
}
```

## Restrictions

- SQL syntax must comply with MariaDB database specifications（highly MySQL-compatible)
- Mixing DDL and DML statements in a single node is not supported (separate execution recommended)
- Execution timeout is limited by the data source configuration
