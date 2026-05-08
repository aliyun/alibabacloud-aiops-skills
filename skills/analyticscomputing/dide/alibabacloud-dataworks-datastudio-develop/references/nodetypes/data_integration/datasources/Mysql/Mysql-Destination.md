# Introduction

The MySQL data source provides you with a bidirectional channel for reading from and writing to MySQL. This article introduces the MySQL data synchronization capabilities of DataWorks.

# Destination

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Notes |
|----------|----------|----------|--------|------------------|------|
| datasource | Data source name, must be exactly consistent with the created data source name. | Y | None | Y | |
| table | Destination table name. | Y | None | Y | Linkage logic: after selecting a table, the column information of the table is fetched |
| column | Destination table write fields (JSON array). Use `["*"]` for writing all columns. | Y | None | Y | |
| selectedDatabase | Selected database name. | N | None | Y | Display condition: when the data source supports database selection; linkage logic: switching clears the table field |
| writeMode | Primary key conflict handling strategy. | Y | insert | Y | Frontend options: `insert into (report dirty data on primary key/constraint conflict)` → `insert`; `on duplicate key update (update data on primary key/unique key conflict)` → `update`; `replace into (delete then insert on primary key/constraint conflict)` → `replace`; linkage logic: selecting replace displays a warning; selecting update displays the updateColumn field |
| updateColumn | When writeMode is update, specifies the list of fields to actually update on conflict. Empty means update all columns. | N | Empty | Y | Display condition: when writeMode is update; prerequisite: data source provides the table's column name list |
| nullMode | NULL handling strategy. | Y | writeNull | Y | Frontend options: `Write NULL` → `writeNull`; `Write default value` → `skipNull`; prerequisite: when writeMode is update, only writeNull can be selected |
| skipNullColumn | Effective when nullMode is skipNull, specifies the columns that do not force writing NULL. Format `["c1","c2"]`, must be a subset of column. | Required when nullMode=skipNull | None | Y | Display condition: when nullMode is skipNull; prerequisite: data source provides the table's column name list |
| preSql | SQL executed before synchronization (such as `TRUNCATE TABLE`). Script mode supports multiple statements, transactions are not supported. | N | None | Y | Supports multiple SQL statements |
| postSql | SQL executed after synchronization. Script mode supports multiple statements, transactions are not supported. | N | None | Y | Supports multiple SQL statements |
| batchSize | Batch commit record count. Too large may cause process OOM. | N | 256 | Y | Frontend default value: 256 |
| encoding | Encoding format. | N | None | Y | Frontend default value: uses database encoding; frontend options: UTF-8, GBK, GB2312, etc. |
| socketTimeout | Socket timeout (milliseconds). | N | None | Y | Frontend default value: 3600000 (1 hour) |
| session | Session parameter configuration. | N | None | Y | Supports multiple entries |
| dbRule | Database sharding rule. | N | None | Y | Display condition: when the table type is a logical table |
| dbNamePattern | Sharded database name pattern. | N | None | Y | Display condition: when the table type is a logical table |
| tableRule | Table sharding rule. | N | None | Y | Display condition: when the table type is a logical table |
| tableNamePattern | Sharded table name pattern. | N | None | Y | Display condition: when the table type is a logical table |
## Configuration Example

```json
    {
            "stepType": "mysql",
            "parameter": {
                "postSql": [],
                "datasource": "yuanyuan_mysql",
                "nullMode": "writeNull",
                "column": [
                    "id",
                    "name"
                ],
                "writeMode": "insert",
                "batchSize": 1024,
                "encoding": "UTF-8",
                "table": "tb_3",
                "preSql": []
            },
            "name": "Writer",
            "category": "writer"
        }
```
