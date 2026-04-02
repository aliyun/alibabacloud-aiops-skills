# Acceptance Criteria: DMS Database Query

**Scenario**: DMS Database Query Workflow
**Purpose**: Skill testing acceptance criteria

---

## Correct SDK Code Patterns

### 1. Import Patterns

#### ✅ CORRECT
```python
from alibabacloud_dms_enterprise20181101.client import Client as DmsClient
from alibabacloud_dms_enterprise20181101 import models as dms_models
from alibabacloud_tea_openapi import models as open_api_models
```

#### ❌ INCORRECT
```python
# Wrong: Using old SDK import paths
from aliyunsdkdms_enterprise.request.v20181101 import GetUserActiveTenantRequest

# Wrong: Missing required imports
from alibabacloud_dms_enterprise20181101 import Client  # Missing models
```

---

### 2. Client Initialization

#### ✅ CORRECT
```python
def create_client() -> DmsClient:
    ak = os.getenv("ALICLOUD_ACCESS_KEY_ID") or os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
    sk = os.getenv("ALICLOUD_ACCESS_KEY_SECRET") or os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    if not ak or not sk:
        raise RuntimeError("Missing credentials")
    config = open_api_models.Config(
        access_key_id=ak,
        access_key_secret=sk,
        endpoint="dms-enterprise.cn-hangzhou.aliyuncs.com",
    )
    return DmsClient(config)
```

#### ❌ INCORRECT
```python
# Wrong: Hardcoded credentials
config = open_api_models.Config(
    access_key_id="LTAI5tXXXXXXXX",  # NEVER hardcode
    access_key_secret="8dXXXXXXXXXX",  # NEVER hardcode
)

# Wrong: Missing endpoint
config = open_api_models.Config(
    access_key_id=ak,
    access_key_secret=sk,
    # endpoint missing
)
```

---

### 3. Get Tenant ID (Tid)

#### ✅ CORRECT
```python
def get_tid(client: DmsClient) -> int:
    resp = client.get_user_active_tenant(dms_models.GetUserActiveTenantRequest())
    if not resp.body.success:
        raise RuntimeError(f"Failed to get Tid: {resp.body.error_message}")
    return resp.body.tenant.tid
```

#### ❌ INCORRECT
```python
# Wrong: Not checking success status
def get_tid(client):
    resp = client.get_user_active_tenant(dms_models.GetUserActiveTenantRequest())
    return resp.body.tenant.tid  # May fail silently

# Wrong: Hardcoded Tid
tid = 12345  # NEVER hardcode Tid
```

---

### 4. Search Database

#### ✅ CORRECT
```python
def search_databases(keyword: str) -> list[dict]:
    client = create_client()
    tid = get_tid(client)
    req = dms_models.SearchDatabaseRequest(search_key=keyword, tid=tid)
    resp = client.search_database(req)
    records = []
    if resp.body.search_database_list and resp.body.search_database_list.search_database:
        for db in resp.body.search_database_list.search_database:
            records.append({
                "database_id": db.database_id,
                "schema_name": db.schema_name,
            })
    return records
```

#### ❌ INCORRECT
```python
# Wrong: Not passing Tid
req = dms_models.SearchDatabaseRequest(search_key=keyword)  # Missing tid

# Wrong: Not handling empty results
for db in resp.body.search_database_list.search_database:  # May raise AttributeError
    pass
```

---

### 5. Execute SQL Query

#### ✅ CORRECT
```python
def execute_query(db_id: int, sql: str, logic: bool = False) -> list[dict]:
    client = create_client()
    tid = get_tid(client)
    req = dms_models.ExecuteScriptRequest(
        tid=tid,
        db_id=db_id,
        script=sql,
        logic=logic,
    )
    resp = client.execute_script(req)
    if not resp.body.success:
        raise RuntimeError(f"SQL execution failed: {resp.body.error_message}")
    # Process results...
```

#### ❌ INCORRECT
```python
# Wrong: Using wrong parameter names
req = dms_models.ExecuteScriptRequest(
    tid=tid,
    database_id=db_id,  # Wrong: should be db_id
    sql=sql,  # Wrong: should be script
)

# Wrong: Not checking success status
resp = client.execute_script(req)
return resp.body.results  # May contain error
```

---

## Test Scenarios

### Scenario 1: Get Tenant ID

**Input**: Valid credentials in environment variables
**Expected Output**: Integer Tid value
**Verification**:
```bash
python scripts/get_tid.py
# Output: 12345 (numeric Tid)
```

### Scenario 2: Search Database

**Input**: Keyword "test"
**Expected Output**: List of matching databases
**Verification**:
```bash
python scripts/search_database.py test --json
# Output: [{"database_id": "xxx", "schema_name": "test_db", ...}]
```

### Scenario 3: Execute SQL Query

**Input**: Valid db_id and SQL "SELECT 1"
**Expected Output**: Query results
**Verification**:
```bash
python scripts/execute_query.py --db-id 12345 --sql "SELECT 1" --json
# Output: [{"success": true, "row_count": 1, ...}]
```

---

## Error Handling Patterns

### ✅ CORRECT Error Handling
```python
try:
    results = execute_query(db_id, sql)
except RuntimeError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
```

### ❌ INCORRECT Error Handling
```python
# Wrong: Catching all exceptions silently
try:
    results = execute_query(db_id, sql)
except:
    pass  # Silently ignoring errors

# Wrong: No error handling
results = execute_query(db_id, sql)  # May crash
```

---

## Environment Requirements

- Python >= 3.10
- Required packages: `alibabacloud-dms-enterprise20181101`, `alibabacloud-tea-openapi`, `alibabacloud-credentials`
- Environment variables: `ALICLOUD_ACCESS_KEY_ID`, `ALICLOUD_ACCESS_KEY_SECRET`
