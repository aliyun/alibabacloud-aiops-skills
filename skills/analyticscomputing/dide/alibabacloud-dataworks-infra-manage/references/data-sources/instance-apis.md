# InstanceMode Data Source Instance Query API Reference

When creating InstanceMode data sources, you can call the corresponding cloud product's OpenAPI to query the instance list for user selection.

> **Important**: The user may not have permissions to call these APIs. If the instance list query fails, **do not block the subsequent process**; prompt the user to manually input the instance ID.

---

## Instance Query API Summary

| Data source type | Product | API | CLI Command |
|-----------|------|-----|----------|
| `mysql` | RDS MySQL | DescribeDBInstances | `aliyun rds DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills --Engine MySQL` |
| `postgresql` | RDS PostgreSQL | DescribeDBInstances | `aliyun rds DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills --Engine PostgreSQL` |
| `sqlserver` | RDS SQL Server | DescribeDBInstances | `aliyun rds DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills --Engine SQLServer` |
| `polardb` | PolarDB MySQL | DescribeDBClusters | `aliyun polardb DescribeDBClusters --user-agent AlibabaCloud-Agent-Skills --DBType MySQL` |
| `drds` | DRDS | DescribeDrdsInstances | `aliyun drds DescribeDrdsInstances --user-agent AlibabaCloud-Agent-Skills` |
| `hologres` | Hologres | ListInstances | `aliyun hologram ListInstances --user-agent AlibabaCloud-Agent-Skills` |
| `analyticdb_for_mysql` | AnalyticDB MySQL | DescribeDBClusters | `aliyun adb DescribeDBClusters --user-agent AlibabaCloud-Agent-Skills` |
| `analyticdb_for_postgresql` | AnalyticDB PostgreSQL | DescribeDBInstances | `aliyun gpdb DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills` |
| `starrocks` | EMR StarRocks | ListCluster | `aliyun emr ListCluster --user-agent AlibabaCloud-Agent-Skills --ClusterType OLAP` |
| `milvus` | Milvus | ListInstances | `aliyun milvus ListInstances --user-agent AlibabaCloud-Agent-Skills` |
| `mongodb` | MongoDB | DescribeDBInstances | `aliyun dds DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills` |
| `kafka` | Kafka | GetInstanceList | `aliyun alikafka GetInstanceList --user-agent AlibabaCloud-Agent-Skills` |
| `opensearch` | OpenSearch | ListInstances | `aliyun searchengine ListInstances --user-agent AlibabaCloud-Agent-Skills` |

---

## Detailed API Description

### RDS MySQL (`mysql`)

**API**: DescribeDBInstances - Query Instance List
**Documentation**: https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/api-rds-2014-08-15-describedbinstances-mysql

```bash
aliyun rds DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" --Engine MySQL --PageSize 50 2>/dev/null | jq -r '
  .Items.DBInstance[] |
  "ID: \(.DBInstanceId) | Name: \(.DBInstanceDescription // .DBInstanceId) | Status: \(.DBInstanceStatus)"
'
```

---

### RDS PostgreSQL (`postgresql`)

**API**: DescribeDBInstances - Query Instance List
**Documentation**: https://help.aliyun.com/zh/rds/apsaradb-rds-for-postgresql/api-rds-2014-08-15-describedbinstances-postgresql

```bash
aliyun rds DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" --Engine PostgreSQL --PageSize 50 2>/dev/null | jq -r '
  .Items.DBInstance[] |
  "ID: \(.DBInstanceId) | Name: \(.DBInstanceDescription // .DBInstanceId) | Status: \(.DBInstanceStatus)"
'
```

---

### RDS SQL Server (`sqlserver`)

**API**: DescribeDBInstances - Query Instance List
**Documentation**: https://help.aliyun.com/zh/rds/apsaradb-rds-for-sql-server/api-rds-2014-08-15-describedbinstances-sqlserver

```bash
aliyun rds DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" --Engine SQLServer --PageSize 50 2>/dev/null | jq -r '
  .Items.DBInstance[] |
  "ID: \(.DBInstanceId) | Name: \(.DBInstanceDescription // .DBInstanceId) | Status: \(.DBInstanceStatus)"
'
```

---

### PolarDB MySQL (`polardb`)

**API**: DescribeDBClusters - Query Cluster List
**Documentation**: https://help.aliyun.com/zh/polardb/api-polardb-2017-08-01-describedbclusters

```bash
aliyun polardb DescribeDBClusters --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" --DBType MySQL 2>/dev/null | jq -r '
  .Items.DBCluster[] |
  "ID: \(.DBClusterId) | Name: \(.DBClusterDescription // .DBClusterId) | Status: \(.DBClusterStatus)"
'
```

> **Note**: When creating a data source, use the `clusterId` parameter (not `instanceId`), and specify the `dbType` parameter (`mysql` or `postgresql`).

---

### DRDS (`drds`)

**API**: DescribeDrdsInstances - Query Instance List
**Documentation**: https://help.aliyun.com/zh/drds/api-drds-2019-01-23-describedrdsinstances

```bash
aliyun drds DescribeDrdsInstances --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" 2>/dev/null | jq -r '
  .Instances.Instance[] |
  "ID: \(.DrdsInstanceId) | Name: \(.Description // .DrdsInstanceId) | Status: \(.Status)"
'
```

> **Note**: The returned JSON path is `.Instances.Instance[]`, not `.Data.Instances.Instance[]`.

---

### Hologres (`hologres`)

**API**: ListInstances - Get Instance List
**Documentation**: https://help.aliyun.com/zh/hologres/developer-reference/api-hologram-2022-06-01-listinstances

```bash
aliyun hologram POST /api/v1/instances --user-agent AlibabaCloud-Agent-Skills --region "<REGION>" --body '{}' 2>/dev/null | jq -r '
  .InstanceList[] |
  "ID: \(.InstanceId) | Name: \(.InstanceName) | Status: \(.InstanceStatus)"
'
```

> **Note**: The Hologres API requires a POST request with an empty body `--body '{}'`. When creating a data source, `username`/`password` are not required; the `authType` parameter is needed.

---

### AnalyticDB MySQL (`analyticdb_for_mysql`)

**API**: DescribeDBClusters - Query Instance List
**Documentation**: https://help.aliyun.com/zh/analyticdb/analyticdb-for-mysql/developer-reference/api-adb-2019-03-15-describedbclusters

```bash
aliyun adb DescribeDBClusters --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" 2>/dev/null | jq -r '
  .Items.DBCluster[] |
  "ID: \(.DBClusterId) | Name: \(.DBClusterDescription // .DBClusterId) | Status: \(.DBClusterStatus)"
'
```

> **Note**: This API does not support the `--PageSize` parameter; it returns 30 records by default.

---

### AnalyticDB PostgreSQL (`analyticdb_for_postgresql`)

**API**: DescribeDBInstances - Query Database Instance List
**Documentation**: https://help.aliyun.com/zh/analyticdb/analyticdb-for-postgresql/developer-reference/api-gpdb-2016-05-03-describedbinstances

```bash
aliyun gpdb DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" --PageSize 50 2>/dev/null | jq -r '
  .Items.DBInstance[] |
  "ID: \(.DBInstanceId) | Name: \(.DBInstanceDescription // .DBInstanceId) | Status: \(.DBInstanceStatus)"
'
```

---

### StarRocks (`starrocks`)

**API**: DescribeInstances - Query Instance List
**Documentation**: https://help.aliyun.com/zh/emr-serverless-starrocks/developer-reference/api-starrocks-2022-10-19-describeinstances

```bash
aliyun starrocks DescribeInstances --user-agent AlibabaCloud-Agent-Skills --region "<REGION>" 2>/dev/null | jq -r '
  .Data[] |
  "ID: \(.InstanceId) | Name: \(.InstanceName) | Status: \(.InstanceStatus)"
'
```

> **Note**: The returned JSON path is `.Data[]`, and field names are lowercase. When creating a data source, specify the `instanceType` parameter (`serverless` or `emr-olap`).

---

### Milvus (`milvus`)

**API**: list-instances - Get Instance List
**Documentation**: https://help.aliyun.com/zh/milvus/developer-reference/api-milvus-2023-10-12-listinstances

> **Prerequisites**: You need to install the Milvus CLI plugin first:
> ```bash
> aliyun plugin install --names aliyun-cli-milvus
> ```

```bash
aliyun milvus list-instances --user-agent AlibabaCloud-Agent-Skills --region "<REGION>" 2>/dev/null | jq -r '
  .Data[] |
  "ID: \(.InstanceId) | Name: \(.ClusterName) | Status: \(.InstanceStatus)"
'
```

> **Note**: The command and parameters are lowercase (`list-instances`, `--region`). The returned JSON path is `.Data[]`.

---

### MongoDB (`mongodb`)

**API**: DescribeDBInstances - Query MongoDB Instance List
**Documentation**: https://help.aliyun.com/zh/mongodb/developer-reference/api-dds-2015-12-01-describedbinstances

```bash
aliyun dds DescribeDBInstances --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" 2>/dev/null | jq -r '
  .DBInstances.DBInstance[] |
  "ID: \(.DBInstanceId) | Name: \(.DBInstanceDescription // .DBInstanceId) | Status: \(.DBInstanceStatus)"
'
```

> **Note**: This API returns 30 records by default; the `--PageSize` parameter is not needed.

---

### Kafka (`kafka`)

**API**: GetInstanceList - Query Instance Information for a Specific Region
**Documentation**: https://help.aliyun.com/zh/apsaramq-for-kafka/cloud-message-queue-for-kafka/developer-reference/api-alikafka-2019-09-16-getinstancelist

```bash
aliyun alikafka GetInstanceList --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" 2>/dev/null | jq -r '
  .InstanceList.InstanceVO[] |
  "ID: \(.InstanceId) | Name: \(.InstanceName) | Status: \(.Status)"
'
```

---

### OpenSearch (`opensearch`)

**API**: ListInstances - Get Instance List
**Documentation**: https://help.aliyun.com/zh/open-search/developer-reference/api-searchengine-2021-10-25-listinstances

```bash
aliyun searchengine ListInstances --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" 2>/dev/null | jq -r '
  .result[] |
  "ID: \(.instanceId) | Name: \(.description // .instanceId) | Type: \(.edition)"
'
```

> **Note**: The returned JSON fields are lowercase: `result`, `instanceId`, etc.

---

## Recommended Process

When creating an InstanceMode data source:

1. **Try to query the instance list**
   ```bash
   aliyun <product> <api> --RegionId "<REGION>" ...
   ```

2. **Query successful** → Display list for user to select instance ID

3. **Query failed** → Prompt user: "Unable to retrieve the instance list, please enter the instance ID directly"

---

## Error Handling

Common Errors and Handling:

| Error | Cause | Handling |
|------|------|----------|
| `Forbidden.Access` | No API permission for this product | Prompt user to input instance ID |
| `InvalidRegionId` | Region does not exist | Check region parameter |
| `ServiceUnavailable` | Product service unavailable | Prompt user to retry later or input manually |

**Key Principle**: When instance list query fails, **do not block the data source creation process**; fall back to letting the user manually input the instance ID.
