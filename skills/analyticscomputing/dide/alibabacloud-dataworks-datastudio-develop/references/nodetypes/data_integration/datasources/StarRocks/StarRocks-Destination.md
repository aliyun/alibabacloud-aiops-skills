# Introduction

The StarRocks data source provides you with bidirectional read and write capabilities for StarRocks. This article introduces the data synchronization capabilities of DataWorks for StarRocks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| datasource | StarRocks data source name. | Y | None | Y |  |
| selectedDatabase | StarRocks database name. | N | The database name configured in the StarRocks data source. | Y |  |
| loadProps | StarRocks StreamLoad request parameters. When using StreamLoad CSV import, you can configure import parameters here. If there is no special configuration, use {}. Configurable parameters include: * column_separator: CSV import column delimiter, default \t. * row_delimiter: CSV import row delimiter, default \n. If your data contains \t or \n, you need to customize other characters as delimiters. Example of using special characters: ```json {"column_separator":"\\x01","row_delimiter":"\\x02"} ``` StreamLoad also supports JSON format import. You can configure: ```json { "format": "json" } ``` Configurable parameters in JSON format: * **strip_outer_array**: Used to specify whether to trim the outermost array structure. Value range: `true` and `false`. Default value: `false`. In real business scenarios, the JSON data to be imported may have a pair of square brackets `[]` representing the array structure in the outermost layer. In this case, it is recommended to set this parameter to `true`, so that StarRocks will trim the outer square brackets `[]` and import each inner array as a separate row of data. If this parameter is set to `false`, StarRocks will parse the entire JSON data file into an array and import it as a single row of data. For example, the JSON data to be imported is as follows: ```json [{"category":1,"author":2},{"category":3,"author":4}] ``` * If this parameter is set to `true`, StarRocks will parse `{"category":1,"author":2}` and `{"category":3,"author":4}` into two rows of data and import them into the corresponding data rows in the destination StarRocks table. * If this parameter is set to `false`, StarRocks will parse the entire JSON array into one row of data and import it into the destination StarRocks table. * **ignore_json_size**: Used to specify whether to check the size of the JSON Body in the HTTP request. **Note** The size of the JSON Body in the HTTP request cannot exceed `100MB` by default. If the JSON Body size exceeds `100MB`, an error message will appear: `The size of this batch exceed the max size [104857600] of json type data data [8617627793].Set ignore_json_size to skip check,although it may lead huge memory consuming.` To avoid this error, you can add `ignore_json_size: true` in the HTTP request header to skip the JSON Body size check. * **compression**: Specifies which compression algorithm to use during StreamLoad data transfer. Supports `GZIP`, `BZIP2`, `LZ4_FRAME`, and `ZSTD` algorithms. * **strict_mode**: Used to specify whether to enable strict mode. Value range: * `true`: Enable strict mode. StarRocks will filter out erroneous data rows, only import correct data rows, and return details of the erroneous data. * `false`: Disable strict mode. StarRocks will convert failed fields to `NULL` values and import the erroneous data rows containing `NULL` values together with the correct data rows. Default value: `false`. | Y | None | Y |  |
| column | The collection of column names to be synced in the configured table. | Y | None | Y |  |
| loadUrl | Enter the StarRocks FrontEnd IP and HTTP Port (default is usually `8030`). If there are multiple FrontEnd nodes, you can configure all of them, separated by commas (,). | Y | None | Y |  |
| table | The name of the selected table to be synced. | Y | None | Y |  |
| preSql | The SQL statements executed first before the data synchronization task. For example, to clear old data in the table before execution (truncate table tablename). | N | None | Y |  |
| postSql | The SQL statements executed after the data synchronization task. | N | None | Y |  |
| maxBatchRows | Maximum number of rows written per batch. | N | 500000 | Y |  |
| maxBatchSize | Maximum number of bytes written per batch. | N | 5242880 | Y |  |
| strategyOnError | The handling strategy when batch writing to StarRocks encounters an exception. Value range: * `exit`: The sync task fails and exits when writing to StarRocks encounters an exception. * `batchDirtyData`: The current batch of data is counted as dirty data when writing to StarRocks encounters an exception. Default value: `exit`. | N | exit | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
    "stepType": "starrocks",
    "parameter": {
        "selectedDatabase": "didb1",
        "loadProps": {
            "row_delimiter": "\\x02",
            "column_separator": "\\x01"
        },
        "datasource": "starrocks_public",
        "column": [
            "id",
            "name"
        ],
        "loadUrl": [
            "1.1.X.X:8030"
        ],
        "table": "table1",
        "preSql": [
            "truncate table table1"
        ],
        "postSql": [
        ],
        "maxBatchRows": 500000,
        "maxBatchSize": 5242880,
        "strategyOnError": "exit"
    },
    "name": "Writer",
    "category": "writer"
}
```
