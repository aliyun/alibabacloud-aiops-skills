# Introduction

The LogHub (SLS) data source provides you with a bidirectional channel for reading from and writing to LogHub (SLS). This article introduces the LogHub (SLS) data synchronization capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. | Y | None | Y | |
| logstore | The name of the destination log store. | Y | None | Y | |
| topic | The topic name of the destination log service. | N | Empty string | Y | Frontend default value: empty string |
| batchSize | The number of data records pushed at one time. | N | 1024 | Y | Minimum value is 1; frontend default value: 1024 |
| column | The collection of column names in each data record. | Y | None | Y | |
| endpoint | Log service entry URL. | Y | None | N | |
| accessKeyId | The AccessKeyId for accessing the log service. | Y | None | N | |
| accessKeySecret | The AccessKeySecret for accessing the log service. | Y | None | N | |
| project | The project name of the destination log service. | Y | None | N | |

## Configuration Example

```json
{
   "stepType": "loghub",
   "parameter": {
       "datasource": "",
       "column": [
          "col0",
          "col1",
          "col2",
          "col3",
          "col4",
          "col5"
       ],
       "topic": "",
       "batchSize": "1024",
       "logstore": ""
   },
   "name": "Writer",
   "category": "writer"
}
```
