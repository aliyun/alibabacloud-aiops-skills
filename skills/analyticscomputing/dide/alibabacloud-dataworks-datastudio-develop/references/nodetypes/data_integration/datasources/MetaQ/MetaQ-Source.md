# Introduction

DataWorks Data Integration supports using the MetaQ Reader to read data from Message Queue (MQ for short). This article introduces the MetaQ data reading capabilities of DataWorks.

> **Supported Direction**: This data source only supports being used as a Source (read), and does not support being used as a Destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| accessId | The access key for accessing the message queue, used to identify the user. | Y | None | N |  |
| accessKey | The access key for accessing the message queue, used to authenticate the user. | Y | None | N |  |
| consumerId | A Consumer is the consumer of messages, also known as a message subscriber, responsible for receiving and consuming messages. consumerId is the identifier of a type of Consumer. This type of Consumer typically receives and consumes a category of messages with consistent consumption logic. | Y | None | N |  |
| topicName | Message topic, a first-level message type, used to classify messages through topics. | Y | None | N |  |
| subExpression | Message sub-topic. | Y | None | N |  |
| onsChannel | Used for message queue authentication. | Y | None | N |  |
| unitName | The destination unit for receiving messages. Common units are as follows: * sh: Center * unsz: Shenzhen unit * us: United States * en-us: Europe * rg-ru: Russia * zbyk: Zhangbei Youku * unzbyun: Zhangbei Cloud * unshyun: Shanghai Cloud * lazada-sg: Singapore Lazada * lazada-my: Malaysia Lazada * lazada-vn: Vietnam Lazada * lazada-ph: Philippines Lazada * lazada-th: Thailand Lazada * lazada-id: Indonesia Lazada | N | None | N |  |
| instanceName | The instance name of the Consumer. | N | None | N |  |
| domainName | The access point of the message queue. | Y | None | N |  |
| contentType | The message type, supports singlestringcolumn (message is STRING type), text (message is text type), and json (message is JSON type). | Y | None | N |  |
| beginOffset | The Offset where the task starts reading, supports begin (from the very beginning) and lastRead (the Offset from the last read). | N | None | N |  |
| nullCurrentOffset | When the last Offset is empty, the starting point for reading. Supports begin (from the very beginning) and current (current offset). | Y | None | N |  |
| fieldDelimiter | The column delimiter for message strings in delimiter mode, such as commas, etc. Supports control characters, such as \\u0001. | Y | None | N |  |
| column | The list of fields to be read. | Y | None | N |  |
| beginDateTime | The start time offset for data consumption, the left boundary of the time range (left-closed, right-open). beginDateTime is a time string in yyyyMMddHHmmss format, which can be used in conjunction with DataWorks scheduling time parameters. | No **Note** beginDateTime and endDateTime are used together. | None | N |  |
| endDateTime | The end time offset for data consumption, the right boundary of the time range (left-closed, right-open). endDateTime is a time string in yyyyMMddHHmmss format, which can be used in conjunction with DataWorks scheduling time parameters. | No **Note** beginDateTime and endDateTime are used together. | None | N |  |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "metaq",
  "parameter": {
    "accessId": "<yourAccessKeyId>",
    "accessKey": "<yourAccessKeySecret>",
    "consumerId": "Test01",
    "topicName": "test",
    "subExpression": "*",
    "onsChannel": "ALIYUN",
    "domainName": "***.aliyun.com",
    "contentType": "singlestringcolumn",
    "beginOffset": "lastRead",
    "nullCurrentOffset": "begin",
    "fieldDelimiter": ",",
    "column": [
      "col0"
    ]
  },
  "name": "Reader",
  "category": "reader"
}
```
