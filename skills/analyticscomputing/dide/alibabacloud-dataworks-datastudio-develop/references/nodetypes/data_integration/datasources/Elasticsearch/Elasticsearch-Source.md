# Introduction

The Elasticsearch data source provides you with a bidirectional channel for reading from and writing to Elasticsearch. This article introduces the Elasticsearch data synchronization capabilities supported by DataWorks.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name. In script mode, you can add a data source, and the value of this configuration item must be consistent with the name of the added data source. | Y | None | Y | |
| index | The index name in Elasticsearch. | Y | None | Y | |
| type | The type name of the index in Elasticsearch (index type). | N | Index name | Y | Display condition: Only displayed when ES version is below 7.0 (when data source `needElasticSearchType` is true) |
| search | Elasticsearch query parameter (search query condition). | Y | None | Y | Required, must be valid JSON |
| pageSize | The number of records read per request (page size). | N | 100 | Y | Frontend default value: `100` |
| scroll | Elasticsearch pagination parameter, sets the cursor retention time (cursor time). | Y | 10m | Y | Frontend default value: `10m` |
| strictMode | Reads data from Elasticsearch in strict mode. Stops reading when Elasticsearch shard.failed occurs, avoiding reading partial data. | N | true | N | |
| sort | The sorting method for returned results. | N | None | Y | Must be valid JSON |
| retryCount | The number of retries after failure. | N | 300 | N | |
| connTimeOut | Client connection timeout. | N | 600,000 | N | |
| readTimeOut | Client read timeout. | N | 600,000 | N | |
| multiThread | HTTP request, whether multi-threaded. | N | true | N | |
| preemptiveAuth | Whether HTTP uses preemptive authentication mode. | N | false | N | |
| retrySleepTime | The time interval between retries after failure. | N | 1000 | N | |
| discovery | Whether to enable node discovery. * true: Connect to a random node in the cluster. * false: Send query requests to the configured endpoint. | N | false | N | |
| compression | Whether to use GZIP compression for the request body. When enabled, the http.compression setting must be enabled on the ES node. | N | false | N | |
| dateFormat | When the field to be synchronized has a date type and the field mapping does not have a format configuration, you need to configure the dateFormat parameter. The configuration format is as follows: `"dateFormat" : "yyyy-MM-dd\|\|yyyy-MM-dd HH:mm:ss"`. | N | None | N | |
| full | Whether to synchronize the entire document content as a single field to the destination. | N | false | Y | Frontend default value: `false`; |
| arrayColumnSplitKeys | Split array columns into multiple rows. | N | None | Y |  |
| multi | This configuration is an advanced feature with five usage modes. The two sub-attributes are `multi.key` and `multi.mult`. For configuration details, refer to the table content in the advanced feature documentation. | N | None | N | |

> Y = Yes, N = No

## Configuration Example

```json
{
            "category":"reader",
            "name":"Reader",
            "parameter":{
                "column":[ //Columns to read.
                    "id",
                    "name"
                ],
                "endpoint":"http://es-cn-xxx.elasticsearch.aliyuncs.com:9200", //Service address.
                "index":"aliyun_es_xx",  //Index.
                "password":"*******",  //Password.
                "multiThread":true,
                "scroll":"5m",  //Scroll flag.
                "pageSize":5000,
                "connTimeOut":600000,
                "readTimeOut":600000,
                "retryCount":30,
                "retrySleepTime":"10000",
                "search":{
                            "range":{
                                "gmt_modified":{
                                    "gte":0
                                }
                            }
                        },  //Query parameter, same as Elasticsearch query content, uses _search API, renamed to search.
                "type":"doc",
                "username":"aliyun_di"  //Username.
            },
            "stepType":"elasticsearch"
        }
```
