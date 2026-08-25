# Dgate MCP tools

Prefer the dedicated tool that matches the task.

| Intent | Tool | Required identity or target input |
|---|---|---|
| List visible catalogs | `meta_catalog_list` | Optional `MaxResults`, `NextToken` |
| Search catalogs | `meta_catalog_search` | Optional `searchKey`, `catalogType`, `dbType` |
| List databases | `meta_database_list` | `CatalogUuid` |
| List tables | `meta_table_list` | `DatabaseUuid` |
| Read columns | `meta_table_columns` | `databaseUuid`, `tableQualifiedName` |
| Read indexes | `meta_table_indexes` | `databaseUuid`, `tableQualifiedName` |
| List visible datasource records | `datasource_list` | Optional `MaxResults`, `NextToken` |
| Inspect platform role | `acl_whoami` | None |
| List real data permissions | `acl_my_permissions` | Optional `MaxResults`, `NextToken` |
| Search DataWiki | `wiki_search` | `wikiUuid`, `query` |
| Run one read-only statement | `exec_sql` | One target plus `statement` |
| Inspect long-tail Actions | `gateway_describe` | Optional `action` |
| Invoke a read-only long-tail Action | `gateway_call` | `action`, exact `params` |

For `exec_sql`, identify the target with one of:

- `databaseUuid`; or
- `catalogUuid`; or
- `catalogName`.

Use `qualifiedName` only with `catalogUuid` or `catalogName`. The execution channel accepts one statement, not a batch. Set bounded `maxRows`, an appropriate execution `timeout`, and a client timeout at least ten seconds longer than `waitSeconds`.

## Long-tail Actions

Call `gateway_describe` before `gateway_call`. Proceed only when the Action exists, the returned parameter names are understood, and `mutating=false`. Preserve parameter names exactly; do not invent or rename them.

Useful read-only Actions include policy, masking, audit, datasource detail, and DataWiki detail lookups when a dedicated tool is unavailable. Never request `CreateAgenticSqlExecuteCredential`; it returns credential material and is permanently blocked from the generic tool.

## Structured envelopes

Control-plane tools return:

```text
schemaVersion, status, requestId, elapsedMs, data, pagination, error, notices
```

Use `data` only when `status=SUCCEEDED`. For list results, continue with the exact `pagination.nextToken` while `pagination.hasMore=true`. On failure, interpret `error.httpStatus`, `error.errorCode`, and `error.errorMessage` instead of parsing free-form text.

`exec_sql` returns:

```text
schemaVersion, status, requestId, kind, elapsedMs, result, async, error, notices
```

Valid statuses include `SUCCEEDED`, `FAILED`, `RUNNING`, and `TIMED_OUT_WAITING`. Report any policy-blocked or other non-success status unchanged and stop without asking for approval, overriding the gate, or retrying. `result.preview` is an ordered row matrix aligned with `result.columns`. When `result.truncated=true`, narrow the query or lower the requested scope rather than treating the preview as complete.
