# Introduction

The Kafka data source provides you with a bidirectional channel for reading from and writing to Kafka. It supports Alibaba Cloud Kafka, as well as self-built Kafka versions 0.10.2 up to and including 2.2.x. For Kafka versions below 0.10.2, data synchronization is not supported because partition data offset retrieval is not supported and the data structure may not support timestamps.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. | Y | None | Y | |
| topic | The Kafka Topic. | Y | None | Y | |
| keyColumns | The collection of source columns used as the Key. | N | None | Y | Frontend option (KafkaKeyValue component) |
| keyWriteMode | Key write format. | N | text | Y | Frontend option (KafkaKeyValue component) |
| keyType | Key type. | Y | string | Y | Frontend option; frontend options: `string` → `string`; `bytearray` → `bytearray`; frontend default value: string |
| valueType | Value type. | Y | string | Y | Frontend option; frontend options: same as keyType; frontend default value: string |
| encoding | Encoding. | N | UTF-8 | Y | Display condition: displayed when keyType or valueType is string; frontend default value: UTF-8 |
| writeMode | Value write format. | N | json | Y | Frontend option; frontend options: `text` → `text`; `json` → `json`; frontend default value: json |
| fieldDelimiter | Delimiter. | Required when writeMode=text | \t | Y | Display condition: writeMode=text; frontend default value: \t |
| nullKeyFormat | Null key replacement string. | N | Null | Y | Display condition: keyColumns.length > 0; frontend option; frontend options: `Null` → `null`; `Empty string` → `emptyString`; `Custom string` → `customString`; frontend default value: null |
| nullValueFormat | Null value replacement string. | N | None | Y | Frontend option; frontend options: `Null` → `null`; `Empty string` → `emptyString`; `Custom string` → `customString` |
| acks | Write success confirmation method. | N | 1 | Y | Frontend option; frontend options: `Primary replica write success` → `1`; `All replicas write success` → `all`; `No confirmation` → `0`; frontend default value: 1 |
| batchConfig | Single write size. | N | default | Y | Frontend option; frontend options: `Default` → `default`; `Default x 2` → `default_2`; `Default x 3` → `default_3`; `Default x 5` → `default_5`; `Default x 10` → `default_10`; frontend default value: default |
| timeout | Write timeout. | N | default | Y | Frontend option; frontend options: same as batchConfig; frontend default value: default |
| column | The collection of fields to write to the destination table (JSON format). | Required when writeMode=json and valueIndex is not configured | None | Y |  |
| partition | Specifies the partition number to write to. | N | None | N | Script mode configuration |
| valueIndex | The column index used as the Value. | N | None | N | Script mode configuration |
| keyIndex | The column index used as the Key. | N | None | N | Script mode configuration; choose one of keyIndex or keyIndexes |
| keyIndexes | The array of column indexes used as the Key. | N | None | N | Script mode configuration; choose one of keyIndex or keyIndexes |
| timestampIndex | The source column index used as the timestamp. | N | None | N | Script mode configuration |
| timestampDateFormat | Timestamp parsing format. | N | None | N | Script mode configuration |
| timeZone | The time zone used for timestamp parsing. | N | None | N | Script mode configuration |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "kafka",
  "parameter": {
    "datasource": "kafka_target",
    "topic": "kafka_topic_name",
    "writeMode": "json",
    "keyType": "BYTEARRAY",
    "valueType": "BYTEARRAY",
    "column": [
      {"name": "id", "type": "STRING"},
      {"name": "name", "type": "STRING"}
    ]
  },
  "name": "Writer",
  "category": "writer"
}
```
