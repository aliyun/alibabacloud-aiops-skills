# Introduction

The AnalyticDB for MySQL 2.0 data source provides you with a bidirectional channel for reading from and writing to AnalyticDB for MySQL 2.0. This article introduces DataWorks' support for AnalyticDB for MySQL 2.0 data synchronization capabilities.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| table | The name of the table to export. | Y | None | N |  |
| column | Column names. If not specified, all columns are used. | N | \* | N |  |
| limit | Limits the number of records to export. | N | None | N |  |
| where | Where condition for adding filter criteria. The String here is directly appended to the query statement as an SQL condition, for example `where id < 100`. | N | None | N |  |
| mode | Currently supports two import types: Select and ODPS. * Select: Uses limit pagination. * ODPS: Uses ODPS DUMP to export data, requires ODPS access permissions. | N | Select | N |  |
| odps.accessKey | Required when mode=ODPS. The cloud account AccessKey used by AnalyticDB for MySQL 2.0 to access ODPS, requires Describe, Create, Select, Alter, Update, and Drop permissions. | N | None | N |  |
| odps.accessId | Required when mode=ODPS. The cloud account AccessID used by AnalyticDB for MySQL 2.0 to access ODPS, requires Describe, Create, Select, Alter, Update, and Drop permissions. | N | None | N |  |
| odps.odpsServer | Required when mode=ODPS. ODPS API address. | N | None | N |  |
| odps.tunnelServer | Required when mode=ODPS. ODPS Tunnel address. | N | None | N |  |
| odps.project | Required when mode=ODPS. ODPS Project name. | N | None | N |  |
| odps.accountType | Effective when mode=ODPS. ODPS access account type. | N | aliyun | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "ads",
      "parameter": {
        "datasource": "ads_demo",
        "table": "th_test",
        "column": [
          "id",
          "testtinyint",
          "testbigint",
          "testdate",
          "testtime",
          "testtimestamp",
          "testvarchar",
          "testdouble",
          "testfloat"
        ],
        "odps": {
          "accessId": "<yourAccessKeyId>",
          "accessKey": "<yourAccessKeySecret>",
          "account": "*********@aliyun.com",
          "odpsServer": " http://service.cn-shanghai-vpc.maxcompute.aliyun-inc.com/api",
          "tunnelServer": "http://dt.cn-shanghai-vpc.maxcompute.aliyun-inc.com",
          "accountType": "aliyun",
          "project": "odps_test"
        },
        "mode": "ODPS"
      },
      "name": "Reader",
      "category": "reader"
    }
```
