# DLF Read-only Query API Reference

## API Overview

All APIs are ROA-style (RESTful) and use AK signature authentication.

| API | HTTP | Path | SDK Method | Description |
|-----|------|------|---------|------|
| ListCatalogs | GET | `/dlf/v1/catalogs` | `list_catalogs(request)` | List Catalogs |
| GetCatalog | GET | `/dlf/v1/catalogs/{catalog}` | `get_catalog(catalog)` | Get Catalog by name |
| GetCatalogById | GET | `/dlf/v1/catalogs/id/{id}` | `get_catalog_by_id(id)` | Get Catalog by ID |
| ListDatabases | GET | `/dlf/v1/{catalogId}/databases` | `list_databases(catalog_id, request)` | List database names |
| ListDatabaseDetails | GET | `/dlf/v1/{catalogId}/database-details` | `list_database_details(catalog_id, request)` | List database details |
| GetDatabase | GET | `/dlf/v1/{catalogId}/databases/{database}` | `get_database(catalog_id, database)` | Get database details |
| ListTables | GET | `/dlf/v1/{catalogId}/databases/{database}/tables` | `list_tables(catalog_id, database, request)` | List table names |
| ListTableDetails | GET | `/dlf/v1/{catalogId}/databases/{database}/table-details` | `list_table_details(catalog_id, database, request)` | List table details |
| GetTable | GET | `/dlf/v1/{catalogId}/databases/{database}/tables/{table}` | `get_table(catalog_id, database, table)` | Get table details |

## ListCatalogs

**Request parameters (ListCatalogsRequest):**

| Parameter | Type | Required | Description |
|------|------|------|------|
| `max_results` | int | No | Max records per page, default 1000 |
| `page_token` | str | No | Page token |
| `catalog_name_pattern` | str | No | Name fuzzy match |

**Returns:** `catalogs` (list), `next_page_token` (str)

**Catalog object fields:** `id`, `name`, `owner`, `status`, `type`, `is_shared`, `share_id`, `options`, `created_at`, `updated_at`, `created_by`, `updated_by`

**Catalog Status enum:** `NEW`, `INITIALIZING`, `RUNNING`, `TERMINATED`, `DELETED`

## GetCatalog / GetCatalogById

- `get_catalog(catalog: str)` — by Catalog name
- `get_catalog_by_id(id: str)` — by Catalog ID (e.g. clg-paimon-xxxx)

Returns the same fields as above.

## ListDatabases

**Request parameters (ListDatabasesRequest):**

| Parameter | Type | Required | Description |
|------|------|------|------|
| `max_results` | int | No | Max records per page, default 1000 |
| `page_token` | str | No | Page token |
| `database_name_pattern` | str | No | Name fuzzy match (e.g. `database%`) |

**Returns:** `databases` (list[str]), `next_page_token` (str)

## ListDatabaseDetails

Request parameters are the same as ListDatabases.

**Returns:** `database_details` (list), `next_page_token` (str)

**Database object fields:** `id`, `name`, `owner`, `location`, `options`, `created_at`, `created_by`, `updated_at`, `updated_by`

## GetDatabase

`get_database(catalog_id: str, database: str)` — returns the same fields as above.

## ListTables

**Request parameters (ListTablesRequest):**

| Parameter | Type | Required | Description |
|------|------|------|------|
| `max_results` | int | No | Max records per page |
| `page_token` | str | No | Page token |
| `table_name_pattern` | str | No | Name fuzzy match (e.g. `user%`) |

**Returns:** `tables` (list[str]), `next_page_token` (str)

## ListTableDetails

Request parameters are the same as ListTables.

**Returns:** `table_details` (list), `next_page_token` (str)

## GetTable

`get_table(catalog_id: str, database: str, table: str)`

**Table object fields:**

| Field | Type | Description |
|------|------|------|
| `id` | str | Table ID |
| `name` | str | Table name |
| `path` | str | Storage path (oss://...) |
| `is_external` | bool | Whether external table |
| `schema_id` | int | Schema version |
| `schema` | Schema | Schema object |
| `owner` | str | Owner |
| `storage_class` | str | Storage class |
| `created_at` | int | Created timestamp (ms) |
| `updated_at` | int | Updated timestamp (ms) |
| `created_by` | str | Creator |
| `updated_by` | str | Last updater |

**Schema structure:**

| Field | Type | Description |
|------|------|------|
| `fields` | list | Column list (id, name, type) |
| `partition_keys` | list[str] | Partition keys |
| `primary_keys` | list[str] | Primary keys |
| `options` | dict | Table properties |
| `comment` | str | Table comment |

## Error Codes

| HTTP status code | Description | Recommended action |
|------------|------|---------|
| 400 | Request parameter error | Check parameter format |
| 401 | Authentication failed | Check AK/SK |
| 403 | Insufficient permission | Grant DLF data permissions |
| 404 | Resource not found | Verify the resource name |
