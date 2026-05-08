# Introduction

Tablestore is a NoSQL data storage service built on the Alibaba Cloud Apsara distributed system. The Tablestore data source provides you with bidirectional read and write capabilities for Tablestore. This article introduces the data synchronization capabilities of DataWorks for Tablestore.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | Y | None | Y |  |
| endPoint | The EndPoint (service address) of the Tablestore Server. | Y | None | Y |  |
| accessId | The AccessKey ID for Tablestore. | Y | None | Y |  |
| accessKey | The AccessKey Secret for Tablestore. | Y | None | Y |  |
| instanceName | The Tablestore instance name. An instance is the entity through which you use and manage Tablestore services. After activating the Tablestore service, you need to create an instance through the management console, and then create and manage tables within the instance. An instance is the basic unit of Tablestore resource management. Tablestore's access control and resource metering for applications are both completed at the instance level. | Y | None | Y |  |
| table | The name of the selected table to be extracted. Only one table can be specified here. There is no need for multi-table synchronization in Tablestore. | Y | None | Y |  |
| newVersion | Defines the version of the Tablestore Writer plugin used. * false: Old version Tablestore Writer, only supports row mode writing to wide tables. * true: New version Tablestore Writer, supports **row mode**, **column mode**, **time series tables**, and **wide tables**, and also supports primary key auto-increment column functionality. The new Tablestore Writer not only supports new features but also has relatively lower system resource overhead, so using the new Tablestore Writer is recommended. The new version plugin configuration is compatible with the old version plugin configuration, meaning that old tasks can run normally after adding the newVersion=true configuration. | Y | false | Y |  |
| mode | Defines the data writing mode. Currently, two modes are supported: * normal: Write data in regular format (**row mode**). * multiVersion: Write data in multi-version format (**column mode**). This configuration only takes effect under the newVersion:true configuration. The old Tablestore Writer ignores the mode configuration and only supports row mode writing. | N | normal | Y |  |
| isTimeseriesTable | Defines whether the data table being operated on is a time series data table. * false: The data table is a regular wide table. * true: The data table is a time series data table. This configuration only takes effect under the newVersion:true & mode:normal configuration (column mode is not compatible with time series tables). | N | false | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"ots",//Plugin name.
            "parameter":{
                "datasource":"",//Data source.
                "table":"",//Table name.
                "newVersion":"true",//Use the new version otswriter
                "mode": "normal",//Write data in row mode
                "isTimeseriesTable":"false",//Configure this table as a wide table (not a time series table)
                "primaryKey" : [//Tablestore primary key information.
                    {"name":"gid", "type":"INT"},
                    {"name":"uid", "type":"STRING"}
                 ],
                "column" : [//Fields.
                      {"name":"col1", "type":"INT"},
                      {"name":"col2", "type":"DOUBLE"},
                      {"name":"col3", "type":"STRING"},
                      {"name":"col4", "type":"STRING"},
                      {"name":"col5", "type":"BOOL"}
                  ],
                "writeMode" : "PutRow"    //Write mode.
            },
            "name":"Writer",
            "category":"writer"
        }
```
