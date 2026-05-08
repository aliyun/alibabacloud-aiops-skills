# Introduction

The Kafka data source provides you with a bidirectional channel for reading from and writing to Kafka. It supports Alibaba Cloud Kafka, as well as self-built Kafka versions 0.10.2 up to and including 2.2.x. For Kafka versions below 0.10.2, data synchronization is not supported because partition data offset retrieval is not supported and the data structure may not support timestamps.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. | Y | None | Y | |
| topic | The Kafka Topic. | Y | None | Y | |
| groupId | Consumer group ID. | N | Auto-generated random string starting with `datax_` | Y | Frontend option; must avoid duplication with other consumer processes; frontend default value: randomly generated |
| beginType | Read start offset. | Y | specific | Y | Frontend option; frontend options: `Specified Time` → `specific`; `Partition Start Offset` → `earliest`; `Group Current Offset` → `current`; frontend default value: specific |
| beginDateTime | The start time offset for data consumption. yyyymmddhhmmss format. | Required when beginType=specific | None | Y | Display condition: beginType=specific |
| endType | Read end offset. | Y | specific | Y | Frontend option; frontend options: `Specified Time` → `specific`; `Partition Latest Offset` → `latest`; frontend default value: specific |
| endDateTime | The end time offset for data consumption. yyyymmddhhmmss format. | Required when endType=specific | None | Y | Display condition: endType=specific |
| timeZone | The time zone corresponding to the start/end time. | N | System time zone of the region | Y | |
| keyType | Key type. | Y | string | Y | Frontend option; frontend options: `string` → `string`; `bytearray` → `bytearray`; `double` → `double`; `long` → `long`; frontend default value: string |
| valueType | Value type. | Y | string | Y | Frontend option; frontend options: same as keyType; frontend default value: string |
| encoding | Encoding. | N | UTF-8 | Y | Display condition: displayed when keyType or valueType is string; frontend default value: UTF-8 |
| stopWhenPollEmpty | Sync end strategy. | N | false | Y | Frontend option; frontend options: `No new data for 1 minute` → `true`; `Reach specified end offset` → `false`; frontend default value: false |
| autoOffsetReset | Offset reset strategy. | N | none | Y | Frontend option; frontend options: `Exception exit` → `none`; `Return to start offset` → `earliest`; `Jump to latest offset` → `latest`; frontend default value: none |
| fetchMinBytes | Minimum read size per fetch. | N | 1 | Y | Frontend option; frontend options: `1 B` → `1`; `512 KB` → `524288`; `1 MB` → `1048576`; frontend default value: 1 |
| fetchMaxWaitMs | Read time per fetch. | N | 500 | Y | Frontend option; frontend options: `500 milliseconds` → `500`; `1 second` → `1000`; frontend default value: 500 |
| sessionTimeoutMs | Read timeout. | N | 30000 | Y | Frontend option; frontend options: `30 seconds` → `30000`; `1 minute` → `60000`; frontend default value: 30000 |
| column | The collection of Kafka data columns to be read. | Y | None | Y |  |
| dataFormat | The data format of the message Value. | N | json | N | Script mode configuration; supports json and text |
| fieldDelimiter | Field delimiter when dataFormat is text. | N | None | N | Only effective when dataFormat=text |
| headerEncoding | Character encoding of the message Header. | N | UTF-8 | N | Script mode configuration |
| beginTimestampMillis | The start Unix timestamp (milliseconds) for consumption. | N | None | N | Script mode configuration |
| endTimestampMillis | The end Unix timestamp (milliseconds) for consumption. | N | None | N | Script mode configuration |
| beginOffset | The start offset for data consumption. | N | None | N | Script mode configuration |
| endOffset | The end offset for data consumption. | N | None | N | Script mode configuration |
| skipExceedRecord | Whether to output data beyond the offset range. | N | false | N | Script mode configuration |
| partition | Only read data from the specified partition. | N | None | N | Script mode configuration |
| kafkaConfig | KafkaConsumer extended parameters. | N | None | N | Script mode configuration |
| waitTIme | Maximum wait time (seconds) for the consumer to pull data. | N | 60 | N | Script mode configuration |
| stopWhenReachEndOffset | Stop after reading to the latest offset of all Topic partitions. | N | false | N | Script mode configuration; only effective when stopWhenPollEmpty=true |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "kafka",
  "parameter": {
    "datasource": "kafka_source",
    "topic": "topic_name",
    "column": [
      "__key__",
      "__value__",
      "__partition__",
      "__headers__",
      "__offset__",
      "__timestamp__"
    ],
    "keyType": "BYTEARRAY",
    "valueType": "BYTEARRAY",
    "beginType": "specific",
    "endType": "specific",
    "beginDateTime": "20250101000000",
    "endDateTime": "20250102000000"
  },
  "name": "Reader",
  "category": "reader"
}
```
