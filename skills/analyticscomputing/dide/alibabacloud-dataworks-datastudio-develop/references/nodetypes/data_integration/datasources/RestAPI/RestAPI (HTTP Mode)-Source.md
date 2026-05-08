# Introduction

You can create a RestAPI data source to write JSON data from RESTful interfaces to other data sources (such as MaxCompute) through sync tasks. Additionally, the RestAPI data source also supports being used as a destination to receive data from other data sources. This article introduces the data synchronization capabilities of DataWorks for RestAPI.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| url | RESTful interface address. | Y | None | Y |  |
| dataMode | The format of the JSON data returned by the RESTful request. * oneData: Retrieve one piece of data from the returned JSON. * multiData: Retrieve a JSON array from the returned JSON and pass multiple data records to the writer. | Y | None | Y |  |
| responseType | The data format of the returned result. Currently, only JSON format is supported. | Y | JSON | Y |  |
| column | The list of fields to read. type specifies the data type of the source, and name specifies the JSON path for the current column data. You can specify column field information as follows. "column":[{"type":"long","name":"a.b" //find data from a.b path},{"type":"string","name":"a.c"//find data from a.c path}] For the column information you specify, both type and name must be filled in. | Y | None | Y |  |
| dataPath | The path to query a single JSON object or JSON array from the returned result. | N | None | Y |  |
| method | Request method, supports get or post. | Y | None | Y |  |
| customHeader | Header information passed to the RESTful interface. | N | None | Y |  |
| parameters | Parameter information passed to the RESTful interface. * For get method, enter `abc=1&def=1`. * For post method, enter JSON type parameters. | N | None | Y |  |
| dirtyData | The handling method when data cannot be found from the specified column JSON path. * dirty: When a column cannot be found during data parsing, the entire record is treated as dirty data. * null: When a column cannot be found during data parsing, the column is set to null. | Y | dirty | Y |  |
| requestTimes | The number of requests to the RESTful address. * single: Only one request is made. * multiple: Multiple requests are made. | Y | single | Y |  |
| requestParam | When requestTimes is set to multiple, you need to specify the loop parameter, such as pageNumber. The plugin will loop through the RESTful interface by passing the pageNumber parameter based on the three parameters startIndex, endIndex, and step, making multiple requests. | N | None | Y |  |
| startIndex | The starting point of the loop request. The starting point is included in the loop request. | N | None | Y |  |
| endIndex | The ending point of the loop request. The ending point is included in the loop request. | N | None | Y |  |
| step | The step size of the loop request. | N | None | Y |  |
| authType | Authentication method. Includes: * **Basic Auth**: Basic authentication. If the data source API supports authentication via username and password, you can select this authentication method, and after selection, configure the username and password for authentication. During subsequent data integration, when connecting to the data source, the credentials are passed to the RESTful address via the Basic Auth protocol to complete authentication. * **Token Auth**: Token authentication. If the data source API supports Token-based authentication, you can select this authentication method, and after selection, configure the fixed Token value for authentication. During subsequent data integration, when connecting to the data source, authentication is performed by passing the token in the header, for example: {"Authorization":"Bearer TokenXXXXXX"}. **Note** When you need to use a custom encryption method, you can consider using the `Token` authentication method and providing the encrypted authentication information as `AuthToken`. | N | None | Y |  |
| authUsername/authPassword | The username and password for Basic Auth authentication. | N | None | Y |  |
| authToken | The token for Token Auth authentication. | N | None | Y |  |
| accessKey/accessSecret | Account information for Aliyun API signature authentication. | N | None | Y |  |
| socketTimeout | Socket timeout parameter for accessing the RESTful interface data, in milliseconds. | N | 60000 | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "restapi",
  "parameter": {
    "url": "",
    "dataMode": "",
    "responseType": "",
    "column": [],
    "dataPath": "",
    "method": "",
    "customHeader": "",
    "parameters": "",
    "dirtyData": "",
    "requestTimes": "",
    "requestParam": "",
    "startIndex": ""
  },
  "name": "Reader",
  "category": "reader"
}
```
