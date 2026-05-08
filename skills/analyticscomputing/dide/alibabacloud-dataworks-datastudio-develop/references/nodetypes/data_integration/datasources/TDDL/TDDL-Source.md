# Introduction

TDDL (Taobao Distributed Data Layer) is a distributed database access engine designed to solve the problems faced when databases move from standalone to distributed architectures. Data Integration supports TDDL read and write capabilities.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name, fixed as `_TDDL`, displayed as TDDL Metadata Center. | Y | _TDDL | Y | |
| appName | The TDDL APP name to sync. | Y | None | Y | |
| guid | TDDL table guid. A guid uniquely identifies a TDDL table. | Y | None | Y | |
| table | Table name. | Y | None | Y | |
| column | The collection of column names to be synced. | Y | None | Y | |
| masterSlave | The method for reading TDDL database master and slave databases. | N | None | Y | Options: slave (prefer slave database), master (read only master database), only_slave (read only slave database) |
| slaveDelayLimit | The maximum allowed delay for the slave database, in seconds. | N | 300 | Y | Required only when masterSlave is slave or only_slave |
| checkSlave | Whether to check the slave database. | N | None | Y | true when masterSlave is slave or only_slave; otherwise false |
| where | Filter condition. | N | None | Y | |
| socketTimeout | Socket timeout, in milliseconds. | N | 3600000 | Y | |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "tddl",
  "parameter": {
    "checkSlave": true,
    "slaveDelayLimit": 300,
    "appName": "DATAWORKS_DI_DATAXCDC_APP",
    "datasource": "_TDDL",
    "column": [
      "id"
    ],
    "socketTimeout": 3600000,
    "guid": "tddl.DATAWORKS_DI_DATAXCDC_APP.cx_decimal",
    "masterSlave": "slave",
    "where": "",
    "table": "cx_decimal"
  },
  "name": "Reader",
  "category": "reader"
}
```
