# Introduction

You can create a RestAPI data source to write JSON data from RESTful interfaces to other data sources (such as MaxCompute) through sync tasks. Additionally, the RestAPI data source also supports being used as a destination to receive data from other data sources. This article introduces the data synchronization capabilities of DataWorks for RestAPI.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| url | RESTful interface address. | Y | None | Y |  |
| dataMode | The format of the JSON data passed by the RESTful request. * oneData: Only one piece of data is passed per request. Multiple requests are made for multiple data records. * multiData: A batch of data is passed per request. The number of requests is determined by the number of tasks split by the reader. | Y | None | Y |  |
| column | The list of field paths for generating JSON data. type specifies the data type of the source, and name specifies the JSON path where the current column data is placed. You can specify column field information as follows. "column":[{"type":"long","name":"a.b" //place column data to path a.b},{"type":"string","name":"a.c"//place column data to path a.c}] **Note** For the column information you specify, both type and name must be filled in. | Y | None | Y |  |
| dataPath | The JSON object path where the data result is placed. | N | None | Y |  |
| method | Request method, supports post and put. | Y | None | Y |  |
| customHeader | Header information passed to the RESTful interface. | N | None | Y |  |
| authType | Authentication method. * **Basic Auth**: Basic authentication. If the data source API supports authentication via username and password, you can select this authentication method, and after selection, configure the username and password for authentication. During subsequent data integration, when connecting to the data source, the credentials are passed to the RESTful address via the Basic Auth protocol to complete authentication. * **Token Auth**: Token authentication. If the data source API supports Token-based authentication, you can select this authentication method, and after selection, configure the fixed Token value for authentication. During subsequent data integration, when connecting to the data source, authentication is performed by passing the token in the header, for example: {"Authorization":"Bearer TokenXXXXXX"}. **Note** When you need to use a custom encryption method, you can consider using the `Token` authentication method and providing the encrypted authentication information as `AuthToken`. | N | None | Y |  |
| authUsername/authPassword | The username and password for Basic Auth authentication. | N | None | Y |  |
| authToken | The token for Token Auth authentication. | N | None | Y |  |
| accessKey/accessSecret | Account information for Aliyun API signature authentication. | N | None | Y |  |
| batchSize | When dataMode is multiData, the maximum number of data records per request. | Y | 512 | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
            "stepType":"restapi",
            "parameter":{
                "url":"http://127.0.0.1:5000/writer1",
                "dataMode":"oneData",
                "responseType":"json",
                "column":[
                    {
                        "type":"long", //place column data to path a.b
                        "name":"a.b"
                    },
                    {
                        "type":"string", //place column data to path a.c
                        "name":"a.c"
                    }
                ],
                "method":"post",
                "defaultHeader":{
                    "X-Custom-Header":"test header"
                },
                "customHeader":{
                    "X-Custom-Header2":"test header2"
                },
                "parameters":"abc=1&amp;def=1",
                "batchSize":256
            },
            "name":"restapiwriter",
            "category":"writer"
        }
```
