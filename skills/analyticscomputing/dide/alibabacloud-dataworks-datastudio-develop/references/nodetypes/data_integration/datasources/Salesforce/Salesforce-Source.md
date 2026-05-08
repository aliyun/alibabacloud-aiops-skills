# Introduction

Salesforce provides on-demand customized software services covering various aspects of customer relationship management, such as contact management, product catalogs, order management, opportunity management, and sales management. DataWorks Data Integration supports reading data from Salesforce data sources. This article introduces the details of using Salesforce.

> **Supported Direction**: This data source only supports being used as a source (read), and does not support being used as a destination (write).

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | Y | Data source name. Script mode supports adding data sources. The value of this configuration item must be consistent with the name of the added data source. | None | Y |  |
| serviceType | N | Sync mode. Supports the following configuration items: * sobject: Query Salesforce Object. * query: Query data using SOQL query statements. * bulk1: Query Salesforce Object using Salesforce Bulk API 1.0. * bulk2: Query Salesforce Object using Salesforce Bulk API 2.0. **Important** * bulk1 and bulk2 modes do not support composite field types such as address and geolocation. * bulk2 mode does not support distributed tasks. * In some cases, bulk1 may perform better than bulk2. You can test the performance with your own Salesforce Objects and choose accordingly. | sobject | Y |  |
| table | Y | Salesforce Object, similar to a table name, such as Account, Case, Group. Required when serviceType is configured as sobject, bulk1, or bulk2. | None | Y |  |
| beginDateTime | N | * The start and end time positions for data consumption. Used when serviceType is configured as sobject, bulk1, or bulk2. * Filters data using the last modified time of the Salesforce Object. The last modified time field is automatically searched in the following priority order: SystemModstamp>LastModifiedDate>CreatedDate. * Follows the left-closed, right-open principle. * Time string in yyyymmddhhmmss format. You can use this with scheduling parameters to achieve incremental data extraction. | None | Y |  |
| endDateTime | N | * The start and end time positions for data consumption. Used when serviceType is configured as sobject, bulk1, or bulk2. * Filters data using the last modified time of the Salesforce Object. The last modified time field is automatically searched in the following priority order: SystemModstamp>LastModifiedDate>CreatedDate. * Follows the left-closed, right-open principle. * Time string in yyyymmddhhmmss format. You can use this with scheduling parameters to achieve incremental data extraction. | None | Y |  |
| splitPk | N | * Split key. Used when serviceType is configured as sobject. * When Salesforce Reader extracts data, if splitPk is specified, it indicates that you want to use the field represented by splitPk for data sharding. Data synchronization will then start concurrent tasks to improve efficiency. * splitPk supports datetime, int, and long fields. If the field does not match these 3 data types, the task will report an error. | None | Y |  |
| blockCompoundColumn | N | Composite data type behavior. Used when serviceType is configured as bulk1 or bulk2. Values: * true: When composite data types exist, the task fails. You need to remove the column mapping for composite data types and rerun. * false: Composite data types are read as NULL values. | true | Y |  |
| bulkQueryJobTimeoutSeconds | N | * Batch data preparation timeout, in seconds. Used when serviceType is configured as bulk1 or bulk2. * Before starting to read data, the Salesforce server needs to run a task to prepare the batch data. If this task runs longer than this configuration, it is considered a data preparation timeout, and the task fails. | 86400 | Y |  |
| batchSize | N | * Number of records downloaded per batch. Used when serviceType is configured as bulk1 or bulk2. * This configuration only needs to be slightly larger than the per-batch record count of the Salesforce batch data preparation task's automatic sharding to achieve the highest download performance. * Data download is streamed, so increasing this configuration item does not consume more memory. * Advanced mode; wizard mode does not support this parameter. | 300000 | Y |  |
| where | N | * Filter condition. Used when serviceType is configured as sobject, bulk1, or bulk2. * In real business scenarios, you can filter data, for example, Name != 'Aliyun'. * If the where statement is not specified, data synchronization treats it as syncing all data. * You cannot specify the where condition as limit 10, which does not conform to the SOQL WHERE clause constraints. | None | Y |  |
| query | N | * Query statement. Used when serviceType is configured as query. * In some business scenarios, the where configuration item is not sufficient to describe the filtering conditions. You can use this configuration item to customize the filter SQL. After configuring this item, the data synchronization system will ignore the table, column, beginDateTime, endDateTime, where, and splitPk configuration items and directly use this configuration item's content to filter data. For example: `select Id, Name, IsDeleted from Account where Name!='Aliyun'`. * Advanced mode; wizard mode does not support this parameter. | None | Y |  |
| queryAll | N | * Query statement, including deleted data. Used when serviceType is configured as sobject or query. * When configured as true, the query includes deleted records. The IsDeleted field can be used to distinguish whether a record has been deleted. | false | Y |  |
| column | Y | The collection of column names to be synced in the configured table, using JSON array to describe field information. * Supports column pruning, allowing you to select partial columns for export. * Supports column reordering, allowing you to export columns not in the table schema order. * Supports constant configuration, as follows: ```json [ { "name": "Id", "type": "STRING" }, { "name": "Name", "type": "STRING" }, { "name": "'123'", "type": "LONG" }, { "name": "'abc'", "type": "STRING" } ] ``` **Note** * **Id, Name** are regular column names. * **'123'** is an integer constant (note that it needs to be enclosed in single quotes). * **'abc'** is a string constant (note that it needs to be enclosed in single quotes). * column must explicitly specify the collection of columns to sync; it cannot be empty. | None | Y |  |
| connectTimeoutSeconds | N | * Timeout for establishing an HTTP connection, in seconds. If this configuration item is exceeded, the task fails. * Advanced mode; wizard mode does not support this parameter. | 30 | Y |  |
| socketTimeoutSeconds | N | * HTTP connection loses response, in seconds. If the interval between preceding and subsequent message transmissions is greater than this configuration item, the task fails. * Advanced mode; wizard mode does not support this parameter. | 600 | Y |  |
| retryIntervalSeconds | N | * Retry interval, in seconds. * Advanced mode; wizard mode does not support this parameter. | 60 | Y |  |
| retryTimes | N | * Number of retries. * Advanced mode; wizard mode does not support this parameter. | 3 | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
      "stepType":"salesforce",
      "parameter":{
        "datasource":"",
        "serviceType": "sobject",
        "table": "Account",
        "beginDateTime": "20230817184200",
        "endDateTime": "20231017184200",
        "where": "",
        "column": [
          {
            "type": "STRING",
            "name": "Id"
          },
          {
            "type": "STRING",
            "name": "Name"
          },
          {
            "type": "BOOL",
            "name": "IsDeleted"
          },
          {
            "type": "DATE",
            "name": "CreatedDate"
          }
        ]
      },
      "name":"Reader",
      "category":"reader"
    }
```
