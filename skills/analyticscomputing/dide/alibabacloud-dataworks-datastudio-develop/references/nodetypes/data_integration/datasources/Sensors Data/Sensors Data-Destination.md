# Introduction

DataWorks Data Integration supports using Sensors Data Writer to write data to Sensors Data. This article introduces the data synchronization capabilities of DataWorks for Sensors Data.

> **Supported Direction**: This data source only supports being used as a destination (write), and does not support being used as a source (read).

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| sdkDataAddress | Data storage path, i.e., the URL address where Sensors Data receives data. The format of this address is: `http://localhost:8106/sa?project=default`. This address can be obtained from **Sensors Data Analytics** > **Basic Settings** > **Data Access** > **Server-side Tracking** > **Copy HTTP Data Receiver URL**. | Y | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
             "stepType": "sahistory", //Plugin name.
             "parameter": {
                "type": "item", //The data type written to Sensors Data. Possible values are: track/user/item, corresponding to events/users/attributes in the Sensors Data system.
                     "item": {       //Since the type parameter is set to item, the item parameter needs to be defined here.
                    "itemType": "course", //Define the item type as student course
                    "typeIsColumn": false, //Whether the item type appears in the column parameter
                    "itemIdColumn": "course_id" //Define the field name for itemID
                },
                "column": [     //Define the column mapping between the source table and the destination table
                    {
                        "name": "course_id",    //The destination table field column name is course_id
                        "index": 0              //Take the 1st column data from the source table and write it to the course_id column of the destination table
                    },
                    {
                        "name": "course_name",  //The destination table field column name is course_name
                        "index": 1              //Take the 2nd column data from the source table and write it to the course_name column of the destination table
                    },
                    {
                        "name": "course_schedule",  //The destination table field column name is course_schedule
                        "index": 2                  //Take the 3rd column data from the source table and write it to the course_schedule column of the destination table
                        "dataConverters":[          //Converter, implements data type conversion.
                               {
                                    "type": "Long2Date"   //Converter type.
                                }
                          ]
                    }
                ],
                "sdkDataAddress": "http://bigdata-project.datasink.sensorsdata.cn/sa?project=default&token=1111111111111111", //Data storage path, i.e., the URL address where Sensors Data receives data
                  },
            "name": "Writer",
            "category": "writer"
        }
```
