# Introduction

DataWorks Data Integration supports using the Lindorm Reader and Lindorm Writer plugins to read from and write to Lindorm via a bidirectional channel. This article introduces the Lindorm data reading and writing capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| configuration | The configuration information provided by each Lindorm cluster for the DataX client connection. You can query it through the Lindorm cluster console. After obtaining the configuration information, you can contact the Lindorm database administrator to convert it to the following JSON format: *{"key1":"value1","key2":"value2"}* . For example: *{"lindorm.zookeeper.quorum":"????","lindorm.zookeeper.property.clientPort":"????"}* **Note** If you are writing JSON code manually, you need to escape double quotes as *\\"* . | Y | None | Y |  |
| table | The name of the Lindorm table to be written to. Lindorm table names are case-sensitive. | Y | None | Y |  |
| namespace | The namespace of the Lindorm table to be written to. Lindorm table namespaces are case-sensitive. | Y | None | Y |  |
| encoding | Encoding method, values are UTF-8 or GBK. Generally used to convert Lindorm byte[] type stored in binary to String type. | N | UTF-8 | Y |  |
| columns | The list of fields to be written. The write field list supports column pruning and column reordering. Column pruning means you can select partial columns for export, and column reordering means you can export without following the table schema order. * For table type tables, just fill in the column names, and the schema information will be automatically obtained from the table's meta. * For widecolumn type or table type tables. | Y | None | Y |  |
| nullMode | When the value read from the source data is null, the nullMode parameter in Lindorm Writer can be configured with different content to achieve different processing methods. * **SKIP** : Indicates not to write this column to Lindorm. * **EMPTY_BYTES** : Indicates to write an empty byte array to the corresponding field in Lindorm when the field value is empty. * **NULL** : Indicates to write a null value. * **DELETE** : Indicates to delete the corresponding field in Lindorm when the field value is empty. | N | EMPTY_BYTES | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "lindorm",
  "parameter": {
    "configuration": "",
    "table": "",
    "namespace": "",
    "encoding": "",
    "columns": [],
    "nullMode": ""
  },
  "name": "Writer",
  "category": "writer"
}
```
