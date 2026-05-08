# Introduction

Tablestore is a NoSQL data storage service built on the Alibaba Cloud Apsara distributed system. The Tablestore data source provides you with bidirectional read and write capabilities for Tablestore. This article introduces the data synchronization capabilities of DataWorks for Tablestore.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| endpoint | The EndPoint (service address) of the Tablestore Server. | Y | None | Y |  |
| accessId | The AccessKey ID for Tablestore. | Y | None | Y |  |
| accessKey | The AccessKey Secret for Tablestore. | Y | None | Y |  |
| instanceName | The Tablestore instance name. An instance is the entity through which you use and manage Tablestore services. After activating the Tablestore service, you need to create an instance through the management console, and then create and manage tables within the instance. An instance is the basic unit of Tablestore resource management. Tablestore's access control and resource metering for applications are both completed at the instance level. | Y | None | Y |  |
| table | The name of the selected table to be extracted. Only one table can be specified here. There is no need for multi-table synchronization in Tablestore. | Y | None | Y |  |
| newVersion | Defines the version of the Tablestore Reader plugin used. * false: Old version Tablestore Reader, only supports **row mode** reading of **wide tables**. * true: New version Tablestore Reader, supports **row mode**, **column mode**, **time series tables**, and **wide tables**. The new Tablestore Reader not only supports new features but also has relatively lower system resource overhead, so using the new Tablestore Reader is recommended. The new version plugin configuration is compatible with the old version plugin configuration, meaning that old tasks can run normally after adding the newVersion=true configuration. | N | false | Y |  |
| mode | Defines the data reading mode. Currently, two modes are supported: * normal: Read data in row mode. The data format is {primary key column value, regular column value}. * multiVersion: Read data in column mode. The data format is {primary key, regular column name, timestamp, regular column value}. This configuration only takes effect under the new Tablestore Reader (newVersion:true) configuration. The old Tablestore Reader ignores the mode configuration and only supports row mode reading. | N | normal | Y |  |
| isTimeseriesTable | Defines whether the data table being operated on is a time series data table: * false: The data table is a regular wide table. * true: The data table is a time series data table. This configuration only takes effect under the newVersion:true & mode:normal configuration. The old Tablestore Reader does not support time series tables, and time series tables cannot be read in column mode. | N | false | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"ots",//Plugin name.
            "parameter":{
                "datasource":"",//Data source.
                "newVersion":"true",//Use the new version otsreader
                "mode": "normal",//Read data in row mode
                "isTimeseriesTable":"false",//Configure this table as a wide table (not a time series table)
                "column":[//Fields.
                    {
                        "name":"column1"//Field name.
                    },
                    {
                        "name":"column2"
                    },
                    {
                        "name":"column3"
                    },
                    {
                        "name":"column4"
                    },
                    {
                        "name":"column5"
                    }
                ],
                "range":{
                    "split":[
                        {
                            "type":"STRING",
                            "value":"beginValue"
                        },
                        {
                            "type":"STRING",
                            "value":"splitPoint1"
                        },
                        {
                            "type":"STRING",
                            "value":"splitPoint2"
                        },
                        {
                            "type":"STRING",
                            "value":"splitPoint3"
                        },
                        {
                            "type":"STRING",
                            "value":"endValue"
                        }
                    ],
                    "end":[
                        {
                            "type":"STRING",
                            "value":"endValue"
                        },
                        {
                            "type":"INT",
                            "value":"100"
                        },
                        {
                            "type":"INF_MAX"
                        },
                        {
                            "type":"INF_MAX"
                        }
                    ],
                    "begin":[
                        {
                            "type":"STRING",
                            "value":"beginValue"
                        },
                        {
                            "type":"INT",
                            "value":"0"
                        },
                        {
                            "type":"INF_MIN"
                        },
                        {
                            "type":"INF_MIN"
                        }
                    ]
                },
                "table":""//Table name.
            },
            "name":"Reader",
            "category":"reader"
        }
```
