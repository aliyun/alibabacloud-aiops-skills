# Introduction

DataWorks Data Integration supports using the OpenSearch Writer to write data to OpenSearch. This article introduces the offline OpenSearch data writing capabilities of DataWorks.

> **Supported Direction**: This data source only supports being used as a Destination (write), and does not support being used as a Source (read).

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The table name to write data to. | Y | None | Y | |
| pageSize | The number of data records written at one time. | N | 100 | Y | Frontend default value: 100; range: 1-10000. |
| accessId | The AccessKey ID in the access key. | Y | None | N | |
| accessKey | The AccessKey Secret in the access key, equivalent to the login password. | Y | None | N | |
| host | The OpenSearch connection service address, which you can view on the Application Details page. The production service address is usually: `http://opensearch-cn-internal.aliyuncs.com/`, and the test service address is: `http://opensearch-cn-corp.aliyuncs.com/`. | Y | None | N | |
| indexName | The name of the OpenSearch project. | Y | None | N | |
| column | The list of fields to be imported. When importing all fields, you can configure it as `"column":["*"]`. OpenSearch supports column selection and column reordering. | Y | None | N | |
| batchSize | The number of data records written at one time. OpenSearch writes in batches. Usually, OpenSearch's advantage lies in querying, and the write transactions per second (TPS) are not high. Please set this according to the resources applied for by your account. | N | 300 | N | |
| writeMode | OpenSearch Writer ensures write idempotency by configuring "writeMode":"add/update": * "add": When a write failure occurs and the task runs again, OpenSearch Writer will clear that data record and import the new data (atomic operation). * "update": Indicates that the inserted data is inserted in a modification manner (atomic operation). | Y | None | N | |
| ignoreWriteError | Ignore write errors. Configuration example: `"ignoreWriteError":true`. | N | false | N | |
| version | OpenSearch version information, for example `"version":"v3"`. Since V2 has many restrictions on push operations, it is recommended to use the V3 version. | N | v2 | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "opensearch",
  "parameter": {
    "accessId": "",
    "accessKey": "",
    "host": "",
    "indexName": "",
    "table": "",
    "column": [],
    "batchSize": 1024,
    "writeMode": "",
    "ignoreWriteError": "",
    "version": ""
  },
  "name": "Writer",
  "category": "writer"
}
```
