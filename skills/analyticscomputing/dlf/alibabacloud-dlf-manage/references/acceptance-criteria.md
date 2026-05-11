# Acceptance Criteria: alibabacloud-dlf-manage

**Scenario**: Read-only metadata query for the DLF data lake
**Purpose**: Skill test acceptance criteria

---

# Correct Python SDK Code Patterns

## 1. Import Patterns

#### ✅ CORRECT
```python
from alibabacloud_tea_openapi.models import Config
from alibabacloud_dlfnext20250310.client import Client
from alibabacloud_dlfnext20250310 import models as dlf_models
```

#### ❌ INCORRECT
```python
# Wrong: using the Common SDK instead of the dedicated SDK
from alibabacloud_tea_openapi.client import Client as OpenApiClient

# Wrong: importing a module that does not exist
from alibabacloud_dlf.client import Client
```

## 2. Authentication — use the CredentialClient default credential chain

#### ✅ CORRECT
```python
from alibabacloud_credentials.client import Client as CredentialClient

credential = CredentialClient()
config = Config(
    credential=credential,
    endpoint='dlfnext.cn-hangzhou.aliyuncs.com',
    region_id='cn-hangzhou'
)
client = Client(config)
```

#### ❌ INCORRECT
```python
# Wrong: hard-coded credentials
config = Config(
    access_key_id='LTAI5t...',
    access_key_secret='abc123...',
)

# Wrong: explicitly reading env vars and passing AK/SK
config = Config(
    access_key_id=os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID'),
    access_key_secret=os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET'),
)
```

## 3. Endpoint format

#### ✅ CORRECT
```python
config.endpoint = 'dlfnext.cn-hangzhou.aliyuncs.com'
config.endpoint = f'dlfnext.{region}.aliyuncs.com'
```

#### ❌ INCORRECT
```python
# Wrong: using the legacy DLF endpoint
config.endpoint = 'dlf.cn-hangzhou.aliyuncs.com'
# Wrong: includes the https prefix
config.endpoint = 'https://dlfnext.cn-hangzhou.aliyuncs.com'
```

## 4. API call patterns

#### ✅ CORRECT — ListCatalogs
```python
request = dlf_models.ListCatalogsRequest()
response = client.list_catalogs(request)
catalogs = response.body.catalogs
```

#### ✅ CORRECT — GetCatalog
```python
response = client.get_catalog('my_catalog')
```

#### ✅ CORRECT — ListDatabases (requires catalog_id)
```python
request = dlf_models.ListDatabasesRequest()
response = client.list_databases('clg-paimon-xxxx', request)
databases = response.body.databases
```

#### ✅ CORRECT — GetTable (requires catalog_id + database + table)
```python
response = client.get_table('clg-paimon-xxxx', 'my_db', 'my_table')
table = response.body
schema = table.schema
```

#### ❌ INCORRECT
```python
# Wrong: ListCatalogs does not take a catalog_id
response = client.list_catalogs('clg-paimon-xxxx', request)

# Wrong: using catalog name instead of catalog_id to query databases
response = client.list_databases('my_catalog_name', request)  # should use catalog ID

# Wrong: omitting the request object
response = client.list_databases('clg-paimon-xxxx')  # missing request argument
```

## 5. Pagination

#### ✅ CORRECT
```python
page_token = None
all_items = []
while True:
    request = dlf_models.ListTablesRequest(
        max_results=100,
        page_token=page_token
    )
    response = client.list_tables(catalog_id, database, request)
    all_items.extend(response.body.tables or [])
    page_token = response.body.next_page_token
    if not page_token:
        break
```

#### ❌ INCORRECT
```python
# Wrong: no pagination — may lose data
request = dlf_models.ListTablesRequest()
response = client.list_tables(catalog_id, database, request)
# Directly using response.body.tables ignores the possibility of a next page
```

## 6. Read-only constraint

#### ✅ CORRECT — this Skill only uses query APIs
```
list-catalogs, get-catalog, get-catalog-by-id,
list-databases, list-database-details, get-database,
list-tables, list-table-details, get-table
```

#### ❌ INCORRECT — must not use write operations
```python
# Wrong: this Skill does not contain write operations
client.create_database(...)
client.drop_table(...)
client.alter_catalog(...)
```
