# Introduction

The LogHub (SLS) data source provides you with a bidirectional channel for reading from and writing to LogHub (SLS). This article introduces the LogHub (SLS) data synchronization capabilities of DataWorks.

# Source
## Parameter Description
| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. | Y | None | Y | |
| logstore | The name of the destination log store. | Y | None | Y | |
| beginDateTime | The start time offset for data consumption. `yyyyMMddHHmmss` format. | Y | ${startTime} | Y | Frontend default value: ${startTime} |
| endDateTime | The end time offset for data consumption. `yyyyMMddHHmmss` format. | Y | ${endTime} | Y | Frontend default value: ${endTime} |
| column | The collection of column names in each data record. | Y | None | Y | |
| batchSize | The number of data records queried from the log service at one time. | N | 256 | Y | Value range (0,1000]; frontend default value: 256 |
| query | Filter data using LogHub query syntax or SPL statements. | N | None | Y | Linkage logic: modifying query triggers re-fetching of table column information |
| maxRetryTimes | Maximum retry count. | N | 7 | Y | Minimum value is 1; frontend default value: 7 |
| retryIntervalSeconds | Retry interval (seconds). | N | 1 | Y | Minimum value is 1; frontend default value: 1 |
| endPoint | Log service entry URL. | Y | None | N | |
| accessId | The access key for accessing the log service, used to identify the user. | Y | None | N | |
| accessKey | The access key for accessing the log service, used to authenticate the user. | Y | None | N | |
| project | The project name of the destination log service. | Y | None | N | |

## Configuration Example

```json
{
  "stepType":"LogHub",
  "parameter":{
      "datasource":"",
      "column":[
        "col0",
        "col1",
        "col2",
        "col3"
      ],
      "beginDateTime":"",
      "batchSize":"",
      "endDateTime":"",
      "fieldDelimiter":",",
      "logstore":"",
      "query":"* | where regexp_like(col0, '[0-9]+') | extend col100=cast(col2 as BIGINT), extend col101=date_parse(col3, '%Y-%m-%d %H:%i') "
  },
  "name":"Reader",
  "category":"reader"
}
```
