# Introduction

DataWorks Data Integration supports using Stream Reader and Stream Writer plugins for bidirectional read and write capabilities through Stream. This article introduces the data read and write capabilities of DataWorks for Stream.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| column | The column data and types of the generated source data. Multiple columns can be configured. You can configure random string generation with a specified range, as shown in the example below. ```json "column" : [ { "random": "8,15" }, { "random": "10,10" } ] ``` Configuration item description: * "random": "8, 15": Indicates random generation of strings with a length of 8 to 15 characters. * "random": "10, 10": Indicates random generation of strings with a length of 10 characters. | Y | None | Y |  |
| sliceRecordCount | Indicates the number of copies of the column to be generated in a loop. | Y | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"stream",//Plugin name.
            "parameter":{
                "column":[//Fields.
                    {
                        "type":"string",//Data type.
                        "value":"field"//Value.
                    },
                    {
                        "type":"long",
                        "value":100
                    },
                    {
                        "dateFormat":"yyyy-MM-dd HH:mm:ss",//Date format.
                        "type":"date",
                        "value":"2014-12-12 12:12:12"
                    },
                    {
                        "type":"bool",
                        "value":true
                    },
                    {
                        "type":"bytes",
                        "value":"byte string"
                    }
                ],
                "sliceRecordCount":"100000"//Indicates the number of copies of the column to be generated in a loop.
            },
            "name":"Reader",
            "category":"reader"
        }
```
