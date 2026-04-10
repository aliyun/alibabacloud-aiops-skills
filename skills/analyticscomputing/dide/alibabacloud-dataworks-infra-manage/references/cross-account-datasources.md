# Cross-Account Data Source Configuration Guide

Use cross-account mode when you need to access resources under other Alibaba Cloud accounts.

---

## Cross-Account Configuration Process

### Step 1: Resource Account (Target Account) Preparation

In the account where the resource resides (e.g., `<TARGET_ACCOUNT_ID>`):

1. Create a RAM role (e.g., `<CROSS_ACCOUNT_ROLE_NAME>`)
2. Configure trust policy to allow the source account (e.g., `<SOURCE_ACCOUNT_ID>`) to assume
3. Grant the role permissions to access target resources (e.g., MaxCompute project access)

**Trust Policy Example:**
```json
{
  "Statement": [{
    "Action": "sts:AssumeRole",
    "Effect": "Allow",
    "Principal": {
      "RAM": ["acs:ram::<SOURCE_ACCOUNT_ID>:root"],
      "Service": ["<SOURCE_ACCOUNT_ID>@engine.dataworks.aliyuncs.com"]
    }
  }],
  "Version": "1"
}
```

### Step 2: Create Data Source in the DataWorks Account (Source Account)

Create a data source in the DataWorks account and configure cross-account parameters:

- `crossAccountOwnerId`: Alibaba Cloud UID of the resource account
- `crossAccountRoleName`: RAM role name in the resource account
- `authType`: `RamRole` (required for MaxCompute/Hologres cross-account scenarios)

---

## Cross-Account Data Source Type Quick Reference

| Data source type | Type | Connection mode | authType | Required parameters | Special notes |
|-----------|------|---------|----------|---------|---------|
| MaxCompute | maxcompute | UrlMode | RamRole | project, regionId, endpointMode | Does not require username/password |
| Hologres | hologres | InstanceMode | RamRole | instanceId, regionId, database | Does not require username/password |
| MySQL | mysql | InstanceMode | - | instanceId, regionId, database, username, password | Standard cross-account |
| PostgreSQL | postgresql | InstanceMode | - | instanceId, regionId, database, username, password | Standard cross-account |
| PolarDB | polardb | InstanceMode | - | clusterId, regionId, database, dbType, username, password | Uses clusterId instead of instanceId |
| SQLServer | sqlserver | InstanceMode | - | instanceId, regionId, database, username, password | Standard cross-account |
| AnalyticDB MySQL | analyticdb_for_mysql | InstanceMode | - | instanceId, regionId, database, username, password | Standard cross-account |
| AnalyticDB PostgreSQL | analyticdb_for_postgresql | InstanceMode | - | instanceId, regionId, database, username, password | Standard cross-account |
| StarRocks | starrocks | InstanceMode | - | instanceId, instanceType, regionId, database, username, password | Must provide `instanceType` (`emr-olap` or `serverless`) |

> **Note**: Only MaxCompute and Hologres require explicitly setting `authType: RamRole` for cross-account. Other types do not need to set authType.

---

## Cross-Account Configuration Examples

### MaxCompute Cross-Account

```json
{
  "project": "target_mc_project",
  "regionId": "cn-zhangjiakou",
  "endpointMode": "SelfAdaption",
  "authType": "RamRole",
  "crossAccountOwnerId": "<TARGET_ACCOUNT_ID>",
  "crossAccountRoleName": "<CROSS_ACCOUNT_ROLE_NAME>",
  "envType": "Prod"
}
```

### Hologres Cross-Account

```json
{
  "instanceId": "hgpostcn-cn-xxxxx",
  "regionId": "cn-zhangjiakou",
  "database": "mydb",
  "authType": "RamRole",
  "crossAccountOwnerId": "<TARGET_ACCOUNT_ID>",
  "crossAccountRoleName": "<CROSS_ACCOUNT_ROLE_NAME>",
  "envType": "Prod"
}
```

### MySQL Cross-Account

```json
{
  "instanceId": "rm-xxxxx",
  "regionId": "cn-zhangjiakou",
  "database": "mydb",
  "username": "myuser",
  "password": "<PASSWORD>",
  "crossAccountOwnerId": "<TARGET_ACCOUNT_ID>",
  "crossAccountRoleName": "<CROSS_ACCOUNT_ROLE_NAME>",
  "envType": "Prod"
}
```

### PolarDB Cross-Account

```json
{
  "clusterId": "pc-xxxxx",
  "regionId": "cn-zhangjiakou",
  "database": "mydb",
  "dbType": "mysql",
  "username": "myuser",
  "password": "<PASSWORD>",
  "crossAccountOwnerId": "<TARGET_ACCOUNT_ID>",
  "crossAccountRoleName": "<CROSS_ACCOUNT_ROLE_NAME>",
  "envType": "Prod"
}
```

### PostgreSQL Cross-Account

```json
{
  "instanceId": "pgm-xxxxx",
  "regionId": "cn-zhangjiakou",
  "database": "postgres",
  "username": "myuser",
  "password": "<PASSWORD>",
  "crossAccountOwnerId": "<TARGET_ACCOUNT_ID>",
  "crossAccountRoleName": "<CROSS_ACCOUNT_ROLE_NAME>",
  "envType": "Prod"
}
```

### SQLServer Cross-Account

```json
{
  "instanceId": "rm-xxxxx",
  "regionId": "cn-zhangjiakou",
  "database": "mydb",
  "username": "myuser",
  "password": "<PASSWORD>",
  "crossAccountOwnerId": "<TARGET_ACCOUNT_ID>",
  "crossAccountRoleName": "<CROSS_ACCOUNT_ROLE_NAME>",
  "envType": "Prod"
}
```

### AnalyticDB MySQL Cross-Account

```json
{
  "instanceId": "am-xxxxx",
  "regionId": "cn-zhangjiakou",
  "database": "mydb",
  "username": "myuser",
  "password": "<PASSWORD>",
  "crossAccountOwnerId": "<TARGET_ACCOUNT_ID>",
  "crossAccountRoleName": "<CROSS_ACCOUNT_ROLE_NAME>",
  "envType": "Prod"
}
```

### AnalyticDB PostgreSQL Cross-Account

```json
{
  "instanceId": "gp-xxxxx",
  "regionId": "cn-zhangjiakou",
  "database": "postgres",
  "username": "myuser",
  "password": "<PASSWORD>",
  "crossAccountOwnerId": "<TARGET_ACCOUNT_ID>",
  "crossAccountRoleName": "<CROSS_ACCOUNT_ROLE_NAME>",
  "envType": "Prod"
}
```

### StarRocks Cross-Account

```json
{
  "instanceId": "c-xxxxx",
  "instanceType": "serverless",
  "regionId": "cn-zhangjiakou",
  "database": "mydb",
  "username": "sr_user",
  "password": "<PASSWORD>",
  "crossAccountOwnerId": "<TARGET_ACCOUNT_ID>",
  "crossAccountRoleName": "<CROSS_ACCOUNT_ROLE_NAME>",
  "envType": "Prod"
}
```

---

## CLI Command Examples

Complete command for creating a cross-account data source:

```bash
aliyun dataworks-public CreateDataSource --user-agent AlibabaCloud-Agent-Skills \
  --region cn-zhangjiakou \
  --ProjectId 12345 \
  --Name cross_account_mysql \
  --Type mysql \
  --ConnectionPropertiesMode InstanceMode \
  --ConnectionProperties '{"envType":"Prod","instanceId":"rm-xxxxx","regionId":"cn-zhangjiakou","database":"mydb","username":"myuser","password":"<PASSWORD>","crossAccountOwnerId":"<TARGET_ACCOUNT_ID>","crossAccountRoleName":"<CROSS_ACCOUNT_ROLE_NAME>"}' \
  --Description "Cross-account MySQL datasource"
```

---

## Detailed Configuration Documentation

For detailed cross-account configuration of each data source type, please refer to:

- [data-sources/maxcompute.md](data-sources/maxcompute.md)
- [data-sources/hologres.md](data-sources/hologres.md)
- [data-sources/mysql.md](data-sources/mysql.md)
- [data-sources/postgresql.md](data-sources/postgresql.md)
- [data-sources/polardb.md](data-sources/polardb.md)
- [data-sources/sqlserver.md](data-sources/sqlserver.md)
- [data-sources/analyticdb_for_mysql.md](data-sources/analyticdb_for_mysql.md)
- [data-sources/analyticdb_for_postgresql.md](data-sources/analyticdb_for_postgresql.md)
- [data-sources/starrocks.md](data-sources/starrocks.md)
