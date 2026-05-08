# Introduction

The DataHub data source serves as a data hub, providing you with a bidirectional channel for reading from and writing to DataHub databases, capable of quickly solving computation problems for massive data. This article introduces DataWorks' support for DataHub data synchronization capabilities.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| topic | DataHub topic name (topic). | Y | None | Y | |
| batchSize | The amount of data read at one time. | N | 1,024 | Y | Frontend default value: `1024` |
| beginDateTime | The start time position for data consumption, the left boundary of the time range (inclusive on the left, exclusive on the right). | Y | None | Y | **Required field**; Format: `yyyyMMddHHmmss` |
| endDateTime | The end time position for data consumption, the right boundary of the time range (inclusive on the left, exclusive on the right). | Y | None | Y | **Required field**; Format: `yyyyMMddHHmmss` |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "datahub",
  "parameter": {
    "endpoint": "",
    "accessId": "",
    "accessKey": "",
    "project": "",
    "topic": "",
    "batchSize": 1024,
    "beginDateTime": "",
    "endDateTime": ""
  },
  "name": "Reader",
  "category": "reader"
}
```
