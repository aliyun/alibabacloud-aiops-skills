---
name: alibabacloud-dlf-manage
description: |
  Query Catalog, database, and table metadata resources in Alibaba Cloud Data Lake Formation (DLF).
  Provides read-only queries via the DLF OpenAPI Python SDK, supporting listing and viewing
  Catalogs, databases, tables with their detailed information and Schema definitions.
  Use cases: "list available Catalogs", "list databases", "view table schema",
  "search tables", "search tables by name", "fuzzy search", "view DLF metadata",
  "what databases are in the data lake", "what columns does a table have",
  "find tables whose name contains xxx".
  This Skill only contains read-only operations — no create, modify, or delete operations.
---

# DLF Data Lake Metadata Query

Query Catalog, Database, and Table metadata resources in Alibaba Cloud Data Lake Formation (DLF).

> **CRITICAL: Use only the Python SDK script provided by this Skill.**
> All operations go through the DLF Python SDK (`alibabacloud-dlfnext20250310`) via `scripts/dlf_metadata_query.py`.
> This Skill does not invoke any shell-based command-line client and does not require AI-Mode configuration.
>
> - **DO NOT** attempt access via any shell-based command-line client — DLF is not exposed through one in this Skill
> - **DO NOT** use curl, wget, or other HTTP clients to call the DLF API directly
> - **MUST** use the `scripts/dlf_metadata_query.py` script provided by this Skill, which wraps the DLF Python SDK
> - All query operations are executed via `python3 scripts/dlf_metadata_query.py <action> [options]`

## Architecture

```
Catalog (Data Catalog)
  └── Database
        └── Table
              ├── Schema (column definitions)
              ├── PartitionKeys (partition keys)
              ├── PrimaryKeys (primary keys)
              └── Options (table properties)
```

## Installation

```bash
pip install -r requirements.txt
```

`requirements.txt` pins the full transitive dependency closure (including
`alibabacloud-dlfnext20250310==3.0.0`) for reproducible installs.

> **Pre-check: Python SDK dependency**
>
> ```bash
> python3 -c "from alibabacloud_dlfnext20250310.client import Client; print('SDK OK')"
> ```
> If not installed, run `pip install -r requirements.txt`.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> Use the default credential chain (CredentialClient) to obtain credentials automatically. Supported sources (in priority order):
> 1. Environment variables (ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET)
> 2. Configuration file (~/.alibabacloud/credentials)
> 3. ECS Instance RAM Role
> 4. OIDC Role ARN
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** explicitly handle or pass AK/SK in code — rely on the default credential chain
>
> See https://help.aliyun.com/document_detail/378659.html for credential configuration details.

## RAM Permissions

This Skill only involves read-only operations (List / Get). See [references/ram-policies.md](references/ram-policies.md) for the full permission list.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before invoking the API,
> the following user-specific parameters must be confirmed with the user; do not assume them.
> Region defaults to cn-hangzhou; if the user does not specify one, use the default without asking.

| Parameter | Required | Description | Default |
|------|------|------|--------|
| `region` | No | Region ID | cn-hangzhou |
| `catalog_name` | Conditional | Catalog name (`--catalog`, required for GetCatalog) | - |
| `catalog_id` | Conditional | Catalog ID (`--catalog-id`, required when querying databases/tables, e.g. clg-paimon-xxxx) | - |
| `database` | Conditional | Database name (`--database`) | - |
| `table` | Conditional | Table name (`--table`) | - |

## Core Workflow

> The script automatically reads AK/SK from environment variables and reports a clear error if they are missing.
> Region defaults to cn-hangzhou; use the default if the user does not specify one.

**You MUST use** `scripts/dlf_metadata_query.py` to query metadata. Do not use shell-based command-line clients or curl. Actions are in **kebab-case**.

> **CRITICAL — list vs. list-*-details: pick the lightest action that satisfies the request.**
> - For listing names / IDs (including fuzzy search): use `list-databases` / `list-tables`. These call the `ListDatabases` / `ListTables` API.
> - For full attributes / Schema / properties: use `list-database-details` / `list-table-details` / `get-database` / `get-table`. These call the heavier `*-details` / `Get*` APIs.
> - **Default to the lightweight `list-*` action** unless the user explicitly asks for full configuration, Schema, or properties. Calling `list-*-details` when only names are needed is incorrect.

### Query Operations

```bash
# ---- Catalog ----

# 1. List all Catalogs (names + minimal info — preferred for listing/searching)
python3 scripts/dlf_metadata_query.py list-catalogs

# 2. Fuzzy-search Catalogs by name (uses ListCatalogs)
python3 scripts/dlf_metadata_query.py list-catalogs --pattern test

# 3. Get Catalog details (by name) — use only when full Catalog config is needed
python3 scripts/dlf_metadata_query.py get-catalog --catalog <catalog_name>

# 4. Get Catalog details (by ID) — use only when full Catalog config is needed
python3 scripts/dlf_metadata_query.py get-catalog-by-id --id <catalog_id>

# ---- Database ----

# 5. List databases (NAMES only — DEFAULT for "list / show / which databases", calls ListDatabases)
python3 scripts/dlf_metadata_query.py list-databases --catalog-id <catalog_id>

# 6. List database details (full attributes, calls ListDatabaseDetails) — use ONLY when the user asks for properties / configs / location / owner
python3 scripts/dlf_metadata_query.py list-database-details --catalog-id <catalog_id>

# 7. Get a single database's details (calls GetDatabase) — use when the user asks for ONE specific database's full info
python3 scripts/dlf_metadata_query.py get-database --catalog-id <catalog_id> --database <db_name>

# ---- Table ----

# 8. List tables (NAMES only — DEFAULT for "list / show / which tables", calls ListTables)
python3 scripts/dlf_metadata_query.py list-tables --catalog-id <catalog_id> --database <db_name>

# 9. Fuzzy-search tables by name (DEFAULT for "search / find tables matching ...", calls ListTables)
python3 scripts/dlf_metadata_query.py list-tables --catalog-id <catalog_id> --database <db_name> --pattern user%

# 10. List table details with Schema (calls ListTableDetails) — use ONLY when the user explicitly asks for Schema / columns / properties of all tables
python3 scripts/dlf_metadata_query.py list-table-details --catalog-id <catalog_id> --database <db_name>

# 11. Get a single table's details with Schema (calls GetTable) — use when the user asks for ONE specific table's Schema
python3 scripts/dlf_metadata_query.py get-table --catalog-id <catalog_id> --database <db_name> --table <table_name>
```

Specify region (defaults to cn-hangzhou): add `--region cn-shanghai`

### Typical Query Flow

```
1. list-catalogs          → get catalog_name and catalog_id (names only)
2. list-databases         → use catalog_id to view available database names
3. list-tables            → use catalog_id + database to view available table names
4. get-table              → use catalog_id + database + table to view ONE table's Schema
```

> Only step 4 (`get-table`) is a "details" call, because Schema is what the user actually asked for. Steps 1–3 stay on the lightweight `list-*` actions.

### Fuzzy Search

All list operations support the `--pattern` argument for fuzzy name matching, using `%` as the wildcard. **Use the lightweight `list-*` action for pattern search unless the user explicitly asks for the full Schema / properties of every match.**

```bash
# Search Catalogs whose name contains "test"
python3 scripts/dlf_metadata_query.py list-catalogs --pattern %test%

# Search databases whose name starts with "prod_"
python3 scripts/dlf_metadata_query.py list-databases --catalog-id <catalog_id> --pattern prod_%

# Search tables whose name starts with "user" (DEFAULT — calls ListTables)
python3 scripts/dlf_metadata_query.py list-tables --catalog-id <catalog_id> --database <db_name> --pattern user%
```

> **Anti-pattern**: do not use `list-table-details --pattern ...` to search by name. That calls `ListTableDetails` and is heavier than required. Reach for `list-table-details` only when the user has explicitly asked for the Schema / columns of every matching table.

### Output Format

- **List operations**: `{"count": N, "items": [...]}`
- **Get operations**: a single JSON object
- **Errors**: `{"error": "...", "hint": "..."}`

## Verification

If `list-catalogs` returns the Catalog list, the connection and permissions are working:

```bash
python3 scripts/dlf_metadata_query.py list-catalogs --region cn-hangzhou
```

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

## Best Practices

1. **Prefer the lightweight `list-*` action over `list-*-details` / `get-*`.** When the task only requires listing resource **names**, **IDs**, or **fuzzy matching**, you MUST use `list-catalogs` / `list-databases` / `list-tables` (which call `ListCatalogs` / `ListDatabases` / `ListTables`). Only use `list-*-details` or `get-*` when the user explicitly asks for full configuration, Schema, columns, properties, owner, or location. Reaching for the heavier API when the lighter one suffices is incorrect.
2. **List before Get**: use list-catalogs to obtain catalog_id first, then use catalog_id to query databases and tables.
3. **Use fuzzy search with the lightweight action**: the `--pattern` argument supports fuzzy matching; use it on `list-tables` (not `list-table-details`) unless full Schema is also requested.
4. **Pagination**: use `--max-results` and `--page-token` for paginated queries when there is a lot of data.
5. **Catalog ID vs Name**: when querying Database/Table, use `catalog_id` (e.g. clg-paimon-xxxx), not the catalog name.

## References

| Reference | Description |
|---------|------|
| [references/related-apis.md](references/related-apis.md) | Full API list and parameter descriptions |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
| [references/verification-method.md](references/verification-method.md) | Verification method |
| [DLF API overview](https://help.aliyun.com/zh/dlf/dlf-2-0/developer-reference/api-dlfnext-2025-03-10-overview) | Official API documentation |
| [DLF product documentation](https://help.aliyun.com/zh/dlf/dlf-2-0) | Product documentation |
| [Python SDK PyPI](https://pypi.org/project/alibabacloud-dlfnext20250310/) | SDK version info |
