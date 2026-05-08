# Introduction

DataWorks Data Integration supports using the IoT Reader plugin to read system tables, product tables, and custom storage tables provided by the IoT Enterprise Instance Data Service. This article introduces the IoT data reading capabilities of DataWorks.

> **Supported Direction**: This data source only supports being used as a Source (read), and does not support being used as a Destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| table | The table identifier of the data storage table. For more information about the data storage tables supported by IoT Reader, please refer to Supported Storage Tables. | Y | None | Y | |
| date | The date format is yyyyMMdd, for example 20151111, which means to export the data of that day. For product time-series tables, the date parameter must be specified. For non-product time-series tables, the date parameter will be ignored. | N | '${bizdate}' | Y | Frontend default value: '${bizdate}' (scheduling parameter) |
| accessId | The AccessKey ID used to access the IoT Enterprise Instance. You can view the AccessKey ID and AccessKey Secret of your Alibaba Cloud account on the Console AccessKey Management page. | Y | None | N | |
| accessKey | The AccessKey Secret used to access the IoT Enterprise Instance. You can view the AccessKey ID and AccessKey Secret of your Alibaba Cloud account on the Console AccessKey Management page. | Y | None | N | |
| regionId | The region ID of the IoT Enterprise Instance. It must be consistent with the region where DataWorks is located. Only Standard and Premium instances in East China 2 (Shanghai), North China 2 (Beijing), and South China 1 (Shenzhen) regions support IoT Reader. | Y | None | N | |
| instanceId | The IoT Enterprise Instance ID. You can view the current instance ID on the Instance Overview page of the IoT Platform console. | Y | None | N | |
| column | The column information of the IoT data storage table to be read. For example, if the fields of the custom storage table test are id, name, and age: * If you need to read id, name, and age in order, you should configure it as `"column":["id","name","age"]` or configure it as `"column":["*"]`. Configuring (*) is not recommended because table field order changes, type changes, or additions/deletions may cause incorrect task results or even task failure. * If you want to read name and id in order, you should configure it as `"column":["name","id"]`. | Y | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType": "iot", // Please specify "iot", indicating the IoT Reader data source
            "parameter": {
                "accessId": "********", // The accessId used to access the IoT Enterprise Instance
                "accessKey": "******", // The accessKey used to access the IoT Enterprise Instance
                "regionId": "cn-shanghai", // The region ID of the IoT Enterprise Instance
                "instanceId": "iot-*******", // The IoT Enterprise Instance ID
                "column": [ // The column information of the IoT data storage table to be read
                    "product_key",
                    "device_name",
                    "iot_id",
                    "event_time",
                    "event_date",
                    "items"
                ],
                "table": "product.h******", // The table identifier of the data storage table
                "date": "${bizdate}" // The date format is yyyyMMdd, such as "20151111", which means to export the data of that day
            },
            "name": "Reader",
            "category": "reader"
        }
```
