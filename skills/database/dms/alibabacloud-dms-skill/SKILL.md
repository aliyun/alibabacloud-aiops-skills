---
name: alibabacloud-dms-skill
description: |
  Alibaba Cloud DMS Database Read/Write Skill. Use this skill to search for target databases in DMS and execute SQL queries and data modifications.
  Triggers: "DMS query", "database query", "execute SQL", "search database", "DMS SQL", "insert data", "update data".
---

# Alibaba Cloud DMS Database Read/Write

Search for target databases and execute SQL queries and data modifications via Alibaba Cloud DMS OpenAPI.

## Scenario Description

This skill implements the following workflow:

1. **Search Target Database** — Search databases by keyword to get Database ID
2. **Execute SQL Query** — Execute SQL statements on the target database

### Architecture

```
User Request → Search Database → Get Database ID → Execute SQL → Return Results
```

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

- Aliyun CLI >= 3.3.1
- jq (for JSON parsing): `brew install jq`
- Credentials configured via `aliyun configure`

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Permissions

> **[MUST] RAM Permission Pre-check:** Verify that the current user has the following RAM permissions before execution.
> See `references/ram-policies.md` for the complete permission list.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., database keyword, SQL statement, db-id, etc.)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|------------------|-------------|---------|
| keyword | Required | Database search keyword | - |
| db-id | Required | Database ID (obtained from search results) | - |
| sql | Required | SQL statement to execute | - |
| logic | Optional | Whether to use logic database mode | false |

## Core Workflow

### Task 1: Search Target Database

Search for databases by keyword to get the Database ID:

```bash
./scripts/search_database.sh <keyword> --json
```

Example:

```bash
# Search for databases containing "mydb"
./scripts/search_database.sh mydb --json
```

The output includes `database_id`, `schema_name`, `db_type`, `host`, `port`, etc.

### Task 2: Execute SQL Query

Execute SQL using the Database ID obtained in the previous step:

```bash
./scripts/execute_query.sh --db-id <database_id> --sql "<SQL_statement>"
```

Examples:

```bash
# List tables
./scripts/execute_query.sh --db-id 78059000 --sql "SHOW TABLES"

# Query data with JSON output
./scripts/execute_query.sh --db-id 78059000 --sql "SELECT * FROM users LIMIT 10" --json

# Logic database mode
./scripts/execute_query.sh --db-id 78059000 --sql "SELECT 1" --logic
```

### Complete Example

```bash
# 1. Search database (assuming searching for "order")
./scripts/search_database.sh order --json
# Example output:
# [{"DatabaseId": "78059000", "SchemaName": "order_db", ...}]

# 2. Execute query
./scripts/execute_query.sh --db-id 78059000 --sql "SELECT COUNT(*) FROM orders"
```

## Success Verification

After executing SQL, check the returned results:

1. Script return code is 0
2. Output contains query results (column names and row data)
3. No error messages

```bash
# Verify query success
./scripts/execute_query.sh --db-id <db-id> --sql "SELECT 1" --json
# Expected output: [{"Success": true, "RowCount": 1, ...}]
```

## Cleanup

This skill only performs query operations and does not create resources. No cleanup is required.

## Available Scripts

| Script | Description |
|--------|-------------|
| `scripts/search_database.sh` | Search databases by keyword |
| `scripts/execute_query.sh` | Execute SQL queries |

> **Note:** Scripts use aliyun-cli credentials configured via `aliyun configure`.

## Best Practices

1. **Confirm database** — Verify the target database before executing SQL
2. **Use --json parameter** — Facilitates programmatic processing of output
3. **Be cautious with sensitive operations** — For UPDATE/DELETE operations, execute SELECT first to confirm

## Reference Links

| Document | Description |
|----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI Installation Guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM Permission Policies |
| [references/related-apis.md](references/related-apis.md) | Related API List |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance Criteria |
