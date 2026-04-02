# Related APIs for DMS Database Query

This document lists all APIs used in the DMS database query workflow.

## API Summary Table

| Product | API Name | SDK Method | Description |
|---------|----------|------------|-------------|
| DMS | GetUserActiveTenant | `get_user_active_tenant()` | Get current user's tenant ID |
| DMS | SearchDatabase | `search_database()` | Search databases by keyword |
| DMS | ExecuteScript | `execute_script()` | Execute SQL scripts |

## API Details

### GetUserActiveTenant

**Description**: Get the active tenant information for the current user. All DMS API calls require the Tid (tenant ID) parameter.

**Endpoint**: `dms-enterprise.cn-hangzhou.aliyuncs.com`

**Request Parameters**: None required

**Response**:
```json
{
  "RequestId": "xxx",
  "Success": true,
  "Tenant": {
    "Tid": 12345,
    "TenantName": "xxx",
    "Status": "ACTIVE"
  }
}
```

**SDK Usage**:
```python
from alibabacloud_dms_enterprise20181101 import models as dms_models

resp = client.get_user_active_tenant(dms_models.GetUserActiveTenantRequest())
tid = resp.body.tenant.tid
```

---

### SearchDatabase

**Description**: Search for databases by keyword. Returns matching databases with their IDs, types, and connection information.

**Endpoint**: `dms-enterprise.cn-hangzhou.aliyuncs.com`

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Tid | Long | Yes | Tenant ID |
| SearchKey | String | Yes | Search keyword |

**Response**:
```json
{
  "RequestId": "xxx",
  "Success": true,
  "SearchDatabaseList": {
    "SearchDatabase": [
      {
        "DatabaseId": "12345",
        "SchemaName": "mydb",
        "DbType": "MySQL",
        "Host": "rm-xxx.mysql.rds.aliyuncs.com",
        "Port": 3306,
        "Encoding": "utf8mb4",
        "EnvType": "product"
      }
    ]
  }
}
```

**SDK Usage**:
```python
from alibabacloud_dms_enterprise20181101 import models as dms_models

req = dms_models.SearchDatabaseRequest(
    search_key="mydb",
    tid=tid
)
resp = client.search_database(req)
for db in resp.body.search_database_list.search_database:
    print(db.database_id, db.schema_name)
```

---

### ExecuteScript

**Description**: Execute SQL scripts on a specified database. Supports SELECT, DML (INSERT/UPDATE/DELETE), and DDL statements.

**Endpoint**: `dms-enterprise.cn-hangzhou.aliyuncs.com`

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Tid | Long | Yes | Tenant ID |
| DbId | Long | Yes | Database ID |
| Script | String | Yes | SQL statement to execute |
| Logic | Boolean | No | Whether to use logic database mode (default: false) |

**Response**:
```json
{
  "RequestId": "xxx",
  "Success": true,
  "Results": {
    "Results": [
      {
        "Success": true,
        "Message": "",
        "RowCount": 10,
        "ColumnNames": ["id", "name", "created_at"],
        "Rows": {
          "Row": [
            {"RowValue": ["1", "Alice", "2024-01-01"]}
          ]
        }
      }
    ]
  }
}
```

**SDK Usage**:
```python
from alibabacloud_dms_enterprise20181101 import models as dms_models

req = dms_models.ExecuteScriptRequest(
    tid=tid,
    db_id=12345,
    script="SELECT * FROM users LIMIT 10",
    logic=False
)
resp = client.execute_script(req)
for result in resp.body.results.results:
    print(result.column_names)
    for row in result.rows.row:
        print(row.row_value)
```

## Additional Useful APIs

These APIs are not used in the core workflow but may be useful for extended scenarios:

| API Name | Description |
|----------|-------------|
| ListDatabases | List all databases for an instance |
| GetDatabase | Get database details by ID |
| ListTables | List tables in a database |
| ListColumns | List columns in a table |
| GetMetaTableDetailInfo | Get table metadata |

## API Documentation Links

- [DMS OpenAPI Overview](https://api.aliyun.com/product/dms-enterprise)
- [API Reference](https://help.aliyun.com/zh/dms/developer-reference/)
- [SDK Downloads](https://help.aliyun.com/zh/dms/developer-reference/sdk-download)
