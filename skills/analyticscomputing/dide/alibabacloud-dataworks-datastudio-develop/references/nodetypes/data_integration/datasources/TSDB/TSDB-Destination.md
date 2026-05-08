# Introduction

DataWorks Data Integration supports using TSDB Writer to write data points to the Alibaba Cloud native multi-model database Lindorm TSDB. This article introduces the data write capabilities of DataWorks for TSDB.

> **Supported Direction**: This data source only supports being used as a destination (write), and does not support being used as a source (read).

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| Data Source is TSDB | maxRetryTime | The number of retries after failure. | No, data type is INT, must be greater than 1. | Y | 3 |
| Data Source is TSDB | ignoreWriteError | If set to true, write errors are ignored and writing continues. If writing still fails after multiple retries, the write task is terminated. | No, data type is BOOL. | Y | false |
| Data Source is RDB | table | The table name (metric) to import into TSDB. If multiField is false, this does not need to be filled in. The corresponding metric needs to be written in the column field. | Required when multiField is true. | Y | None |
| Data Source is RDB | multiField | Use the HTTP API multi-field (multiple fields) method to write to TSDB. **Note** If you use the Lindorm TSDB native SQL capability to access data written via the HTTP API method, you need to pre-create the table in TSDB; otherwise, you can only query data using the TSDB HTTP API method. | Required. | Y | false **Note** When using multi-field writing in the current TSDB version, this value must be set to true. |
| Data Source is RDB | column | The field names of the table in the relational database. | Yes | Y | None **Note** The field order here must be consistent with the order of the column fields configured in the Reader plugin. |
| Data Source is RDB | columnType | The types of table fields in the relational database mapped to TSDB types. Supported types are as follows: * timestamp: This field is a timestamp. * tag: This field is a tag. * field_string: The value of this field is a string type. * field_double: The value of this field is a numeric type. * field_boolean: The value of this field is a boolean type. | Yes | Y | None **Note** The field order here must be consistent with the order of the column fields configured in the Reader plugin. |
| Data Source is RDB | batchSize | The number of records per batch write. | No, data type is INT, must be greater than 0. | Y | 100 |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "tsdb",
  "parameter": {
    "Data Source is TSDB": "",
    "Data Source is RDB": ""
  },
  "name": "Writer",
  "category": "writer"
}
```
