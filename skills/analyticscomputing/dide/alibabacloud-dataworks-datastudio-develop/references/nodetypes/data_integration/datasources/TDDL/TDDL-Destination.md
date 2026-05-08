# Introduction

TDDL (Taobao Distributed Data Layer) is a distributed database access engine designed to solve the problems faced when databases move from standalone to distributed architectures. Data Integration supports TDDL read and write capabilities.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name, fixed as `_TDDL`, displayed as TDDL Metadata Center. | Y | _TDDL | Y | |
| appName | The TDDL APP name to sync. | Y | None | Y | |
| guid | TDDL table guid. A guid uniquely identifies a TDDL table. | Y | None | Y | |
| table | Table name. | Y | None | Y | |
| column | The list of fields in the destination table to write data to. | Y | None | Y | |
| writeMode | The mode for writing to TDDL. insert: Reports dirty data on primary key/unique key conflict; update: Updates data on primary key/unique key conflict; replace: Deletes then inserts data on primary key/unique key conflict. | N | insert | Y | |
| updateColumn | Must be filled when writeMode is update. Specifies the list of columns to update. | N | None | Y | Only required when writeMode is update; format example `"updateColumn": ["name","create_time"]` |
| batchSize | Number of records per batch write. | N | 2048 | Y | |
| connectionMode | The method for connecting to TDDL. Default is via tddl client; also supports direct connection to physical databases via the direct mode. | N | tddl | Y | Options: tddl, direct |
| dbRule | Database sharding rule, using Groovy syntax. | N | None | Y | Only fill when connectionMode is direct |
| dbNamePattern | Database name placeholder expression, using Groovy syntax. | N | None | Y | Only fill when connectionMode is direct |
| tableRule | Table sharding rule, using Groovy syntax. | N | None | Y | Only fill when connectionMode is direct |
| tableNamePattern | Table name placeholder expression, using Groovy syntax. | N | None | Y | Only fill when connectionMode is direct |
| preSql | The SQL statements executed first before the data synchronization task. | N | None | Y | |
| postSql | The SQL statements executed after the data synchronization task. | N | None | Y | |
| socketTimeout | Socket timeout, in milliseconds. | N | 3600000 | Y | |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "tddl",
  "parameter": {
    "postSql": [
      ""
    ],
    "connectionMode": "tddl",
    "appName": "DATAWORKS_DI_DATAXCDC_APP",
    "datasource": "_TDDL",
    "column": [
      "id",
      "name",
      "create_time",
      "create_decimal"
    ],
    "socketTimeout": 3600000,
    "guid": "tddl.DATAWORKS_DI_DATAXCDC_APP.add_table_use",
    "writeMode": "insert",
    "batchSize": 2048,
    "table": "add_table_use",
    "preSql": [
      ""
    ]
  },
  "name": "Writer",
  "category": "writer"
}
```
