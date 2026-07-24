# MMS Commands — Data Source & Metadata

MMS provides API capabilities through the MaxCompute OpenAPI (product code `MaxCompute`, version `2022-01-04`).  
CLI invocation format: `aliyun maxcompute <command> [params] --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}`

## Data Source Management

### ListMmsDataSources — List Data Sources

```bash
aliyun maxcompute list-mms-data-sources \
  --name <name> \
  --type <Hive|BigQuery|Snowflake|Redshift|Databricks|MaxCompute> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

> When resolving Name → ID, prefer narrowing with `--name`; do not default to a full unfiltered listing first.

| Parameter | Type | Description |
|------|------|------|
| name | string | Filter by name |
| type | string | Filter by data source type |
| region | string | Filter by region |
| pageNum | integer | Page number |
| pageSize | integer | Items per page |

### GetMmsDataSource — Get Data Source Details

```bash
aliyun maxcompute get-mms-data-source \
  --source-id <sourceId> \
  --with-config true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### Create/Update/Delete Data Sources

> **[MUST] For creating, updating, and deleting data sources, guide the user to complete the operation in the console.**  
> Console URL: `https://maxcompute.console.aliyun.com/{region}/mma/datasource`

## Metadata Scanning (Inventory)

### CreateMmsFetchMetadataJob — Initiate Metadata Inventory

```bash
aliyun maxcompute create-mms-fetch-metadata-job \
  --source-id <sourceId> \
  [--db-name <dbName>] \
  [--table-names <table1> <table2> ...] \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### GetMmsFetchMetadataJob — Check Inventory Status

```bash
aliyun maxcompute get-mms-fetch-metadata-job \
  --source-id <sourceId> \
  --scan-id <scanId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

## Metadata Management

### ListMmsDbs — List Databases

```bash
aliyun maxcompute list-mms-dbs \
  --source-id <sourceId> \
  --name <name> \
  --status <status> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### GetMmsDb — Get Database Details

```bash
aliyun maxcompute get-mms-db \
  --source-id <sourceId> \
  --db-id <dbId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### ListMmsTables — List Tables

Under the same `source_id`, **tables with identical names may exist across different databases**. If the user has already provided `source_id` and only queries by table name **without** specifying a database, prefer **omitting `db-name`** and search tables directly using `source_id` + `--name`; only add `db-name` (or ask the user to confirm the database name) when multiple results are returned and disambiguation is needed.

```bash
aliyun maxcompute list-mms-tables \
  --source-id <sourceId> \
  --db-name <dbName> \
  --name <name> \
  --status <status> \
  --has-partitions true \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

When querying by table name only, without specifying a database (`db-name` can be omitted; refer to the actual API for details):

```bash
aliyun maxcompute list-mms-tables \
  --source-id <sourceId> \
  --name <tableNameOrLikePattern> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

| Parameter | Type | Description |
|------|------|------|
| dbId | integer | Filter by database ID |
| dbName | string | Filter by database name |
| name | string | Filter by table name |
| dstProjectName | string | Filter by destination project name |
| dstSchemaName | string | Filter by destination schema |
| type | string | Filter by table type |
| hasPartitions | boolean | Whether the table has partitions |
| status | array | Filter by status |

### GetMmsTable — Get Table Details

```bash
aliyun maxcompute get-mms-table \
  --source-id <sourceId> \
  --table-id <tableId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### ListMmsPartitions — List Partitions

```bash
aliyun maxcompute list-mms-partitions \
  --source-id <sourceId> \
  --db-name <dbName> \
  --table-name <tableName> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```

### GetMmsPartition — Get Partition Details

```bash
aliyun maxcompute get-mms-partition \
  --source-id <sourceId> \
  --partition-id <partitionId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service/{session-id}
```
