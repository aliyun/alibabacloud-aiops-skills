# Introduction

The DataHub data source serves as a data hub, providing you with a bidirectional channel for reading from and writing to DataHub databases, capable of quickly solving computation problems for massive data. This article introduces DataWorks' support for DataHub data synchronization capabilities.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| topic | DataHub topic name (topic). | Y | None | Y | |
| maxCommitSize | When the accumulated data Buffer size reaches this value, data is batch-submitted to the destination, in Bytes. | N | 1,048,576 (1MB) | Y | Frontend default value: `1048576` (bytes) |
| maxRetryCount | Maximum number of retries for task failures. | N | 500 | Y | Frontend default value: `500` (times) |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "datahub",//Plugin name.
            "parameter": {
                "datasource": "",//Data source.
                "topic": "",//Topic is the smallest unit of DataHub subscription and publishing. You can use Topic to represent a class or a type of streaming data.
                "maxRetryCount": 500,//Maximum number of retries for task failures.
                "maxCommitSize": 1048576//When the accumulated data Buffer size reaches maxCommitSize (in Bytes), data is batch-submitted to the destination.
                 //DataHub limits the number of data records written per request to 10,000. Exceeding 10,000 records will exceed the limit and cause task errors. Please control the number of records written to DataHub per batch based on your average data size per record * 10,000 records. For example, if each record is 10KB, this parameter should be set to a value lower than 10*10000KB.
            },
            "name": "Writer",
            "category": "writer"
        }
```
