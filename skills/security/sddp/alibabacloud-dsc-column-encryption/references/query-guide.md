# Read-Only Query Guide for the Column Encryption Page

`scripts/query_column_encryption.py` allows only query actions. It registers no create, modify, delete, authorize, synchronize, or upgrade actions. It covers the query capabilities used by the current DSC Risk Governance > Column Encryption page under `Sddp/2026-01-20`.

## Page Capabilities and Commands

| Page area or purpose | Command | Action |
| --- | --- | --- |
| Reproduce the initial page in one command | `page` | Combination of the initial-page Actions below |
| Column encryption quota | `user-status` | `GetUserStatus` |
| Regions | `regions` | `ListRegions` |
| Classification and grading templates | `templates` | `ListTemplates` |
| Sensitive data catalog summary | `total-sensitive` | `ListTotalSensitiveInfo` |
| Account cards | `account-count` | `GetDataMaskingAccountCount` |
| Sensitivity levels | `sensitivity-levels` (alias: `risk-levels`) | `ListRiskLevels` |
| Identification models | `identify-models` | `ListIdentifyModels` |
| Instance filters and main table | `instances` | `ListDataMaskingInstances` |
| Column statistics cards | `column-count` | `GetDataMaskingColumnCount` |
| Instance encryption eligibility check | `check-instance` | `CheckDataMaskingInstance` |
| Database dropdown | `databases` | `ListDataSources` |
| Table dropdown | `tables` | `ListTables` |
| Column dropdown | `columns` | `ListColumns` |
| Expanded instance details/final column selection | `masking-columns` | `ListDataMaskingColumns` |
| Database accounts and permissions | `accounts` | `ListDataAssetAccounts` |
| Available algorithms | `algorithms` | `ListDataMaskingEncryptionAlgorithms` |
| Instance engine, version, and KMS capabilities | `instance-attribute` | `GetInstanceAttribute` |
| KMS candidates and availability | `kms-keys` | `ListKmsKeys` + KMS `DescribeKey` |
| Available kernel upgrade versions | `mini-engine-versions` | `ListMiniEngineVersions` |

Use the narrow command for a narrow request: `check-instance` checks one known instance's eligibility; `accounts` searches account access and expiry. Neither command requires `page` or `masking-columns`. Use `page` when the user requests the overview/statistics combination, and `masking-columns` when selecting or inspecting columns. A business-ineligible instance or incomplete account search is a result to report, not permission to run another workflow or expand the query.

Every command supports `--profile`, defaulting to `dsc-oauth`. Select a named CLI profile configured for OAuth, AK, StsToken or RamRoleArn; the output reports its actual mode. Before a request, verify the mode remains unchanged and execute through that profile, ignoring inherited AK/STS environment variables. Authentication failure must not fall back to another identity. The CLI owns credentials; scripts and agents do not read or export them. See [runtime-constraints.md](runtime-constraints.md) for setup and expiry handling.

`sensitivity-levels` and `risk-levels` are equivalent read-only commands. Both require `--template-id` and call `ListRiskLevels` with the same parameters, authentication checks, output fields and failure behavior. Existing `risk-levels` invocations remain supported; neither spelling adds permissions, requests or retries.

For `page`, `instances`, and `masking-columns`, prefer `--sensitivity-level-ids` to filter by a comma-separated list of positive sensitivity-level IDs. `--risk-level-ids` remains a compatible alias: both spellings use the same CSV validation and normalization, populate the same `RiskLevelIds` API parameter, and preserve authentication, pagination, and error behavior. The alias does not add filters to summary cards or `column-count`.

## Combined Filter Examples

The IDs and resource names below illustrate syntax only. Replace them with values from current queries before running the commands. See [console-workflows.md](console-workflows.md) for mappings between console controls and parameters.

```bash
# Query instances using the main page criteria; retain the user's selected status when querying only the instance table
python3 <skill-dir>/scripts/query_column_encryption.py page \
  --region-id cn-zhangjiakou --template-id 123456 --product-code RDS \
  --masking-status NotEncrypted --sensitivity-level-ids 3,4,5 --template-rule-ids 789 \
  --instance-search rm-xxx --db-name app_db --table-name users --column-name email \
  --all-pages --profile dsc-oauth

# Read all unencrypted columns on one instance matching the level, model, database, and table criteria
python3 <skill-dir>/scripts/query_column_encryption.py masking-columns \
  --region-id cn-zhangjiakou --template-id 123456 --product-code RDS \
  --instance-id rm-xxx --db-name app_db --table-name users \
  --masking-status NotEncrypted --sensitivity-level-ids 3,4,5 --template-rule-ids 789 \
  --all-pages --profile dsc-oauth

# Combine product, instance name, account name, and permission filters
python3 <skill-dir>/scripts/query_column_encryption.py accounts \
  --region-id cn-zhangjiakou --product-code RDS --instance-search rm-xxx \
  --account-search app --auth-role restrictedAccess,noneAccess --all-pages \
  --profile dsc-oauth
```

`page.InstanceFilters` describes the instance table criteria. `CardScope` makes clear that statistics cards support only their own fields, such as region, template, and product; they do not accept instance, engine, column-name, or encryption-status filters. Do not interpret card totals as the number of matches in the currently filtered table.

Pass a complete ID to `--instance-id` where possible (native backend matching semantics vary with combined criteria). `--account-name` matches the account exactly. `--instance-search` and `--account-search` use client-side substring matching. `instances/page --engine-type` also uses exact client-side filtering because some backend paths ignore the engine parameter. These client-side filters first read all candidates from page 1, then filter and paginate, emitting `LocalFilter`, `SourceTotalCount`, and the final `TotalCount`. If the source query is incomplete, `TotalCount=null`, and the result must not be treated as complete.

The source scan for client-side filtering still obeys `--max-pages`, including when filtering itself enables sequential source reads. For example, `accounts --instance-search ... --account-search ... --max-pages 1` reads at most one source page; it does not override the limit to find every match. Preserve an explicit page budget and report truncation instead of increasing it or treating zero observed matches as proof of absence.

`masking-columns --product-ids` supports only one product ID and maps it to the backend's effective `ProductId`. Query multiple products separately; the script rejects multiple values rather than applying a silently ineffective filter. It also explicitly rejects mismatched `ProductCode` and `ProductId/ProductIds`, or simultaneous single-level and multiple-level filters.

## Target Discovery for a Requested Creation

This flow fills missing creation parameters for an authorized online request. It is not a mandatory sequence for an explanation, offline draft or a scoped read-only query; use the matching command above when its inputs are already known.

1. Use `regions` to select `RegionId`.
2. Use `templates --all-pages` to select `Items[].Id` as `TemplateId`.
3. Use `instances --region-id ... --template-id ...` to select `Items[].InstanceId`, `ProductCode`, and `EngineType`.
4. Use `check-instance` to validate the candidate instance. Inspect `ErrorCode` even after HTTP success; only `Success` confirms business eligibility.
5. Use `databases` to select `Items[].DbName`. This API requires `ProductCode`, but the database inventory itself is not filtered by `TemplateId`.
6. For `tables`, pass `DataAssetSourceId=InstanceId` and `DataSourceName=DbName`; the script already performs this field mapping.
7. For `masking-columns`, pass `InstanceId`, `DbName`, `TableName`, `EngineType`, and `TemplateId`, and select columns from `Items[].Name`.
8. Use `algorithms`, `instance-attribute`, `kms-keys`, and `accounts` to complete the creation parameters. The `Items[].AccountName` returned by `accounts` is the account name to write into `UserList[].AccountId`; `Items[].Id` identifies the query record and must not be substituted. Bind the account name together with `ProductCode` and `InstanceId`.

`columns` reproduces the page's "all columns" filter dropdown. Prefer `masking-columns` for the final candidate list before creation because it returns:

- `MaskingStatus`
- `RiskLevelId` / `RiskLevelName`
- `RuleId` / `RuleName`
- `ErrorCode` / `ErrorMessage`
- `DataType`

## TemplateId Semantics

- `TemplateId` applies to queries of templates, sensitivity levels, identification models, instances, tables, columns, column status, and column statistics.
- When it is omitted, most server APIs use the primary template. Like the console, `page` defaults to the first template returned by `ListTemplates` and includes `TemplateContext.Selection` in the output.
- If the user specifies an ID explicitly, `page` first verifies that it exists. Creation preflight also calls `ListTemplates` again to validate it.
- The current `CreateDataMaskingRule` AMP contract has no `TemplateId`. It is selection and verification context, not a create-request field. The creation script includes it in the plan fingerprint and confirmation summary but removes it from the write request.
- For compatibility with historical identification results, `ListTables`, `ListColumns`, `ListDataMaskingColumns`, and column statistics may fall back to built-in template `98` if the specified template has no results on the initial page and no sensitivity-level or model filter is specified. Receiving data therefore does not prove that it matched the explicit template. If strict template attribution is required, verify it further through sensitivity-level/identification-model filters or data catalog queries.

## Pagination and Search

- Paginated list commands query the first page by default. `--all-pages` reads sequentially using `CurrentPage` / `PageSize`, up to `--max-pages` (default 100); table queries using a Marker continue with the returned `NextMarker`. `identify-models` returns `RuleList` in one response and does not support these pagination parameters.
- For complete queries, check for `PaginationComplete=true` and the absence of `PaginationTruncated` / `PaginationStalled`. Repeated pages, partially overlapping records, changing totals across pages, missing verifiable lists/totals, an empty page while results remain, or reaching the limit prevent a query from being considered complete. Do not count the same entity twice even if its status, role, or expiration changes. Invalid records, malformed totals, or a unique-record count greater than the total cannot prove completeness. Without a total, a response shorter than the requested PageSize alone does not establish the last page. A missing match in an incomplete query does not prove that the target does not exist. A single-page result has no full-query completion marker and does not establish that the server has no next page.
- `page --all-pages` reads every instance and checks each one's eligibility; the number of calls increases accordingly for large instance inventories.
- Like the current console, `page`, `account-count`, and `column-count` do not send `ProductIds` by default. They filter by product ID only when `--product-ids` is explicitly supplied.
- `templates --name` and `identify-models --name` use client-side substring matching because the current AMP contract exposes no name-search field.
- PostgreSQL and Oracle may return `schema.table` in `ListTables.Items[].Name`. Pass it unchanged to `--table-name` in subsequent queries and also supply the correct `--engine-type`.

## Status and Filter Considerations

Column statuses:

- Allowed request filter values: `NotEncrypted`, `Success`, `Failed`.
- Additional possible response values: `Processing`, `Deleting`, `DeleteFailed`.
- Use `NotEncrypted` for creation candidates by default. Select `Failed` only if the user explicitly asks to retry failed columns.
- Page statistics: total columns = `TotalCount`; sensitive columns = `SensitiveCount`; encrypted = `MaskedCount`; failed = `MaskingFailedCount`; unencrypted = `SensitiveCount - MaskedCount - MaskingFailedCount`.

To find all unencrypted columns, omit `--masking-status NotEncrypted` when enumerating instances, then query column-level status with `masking-columns --masking-status NotEncrypted`. Under instance-level filter semantics, the unencrypted filter excludes partially encrypted instances even though they may still contain unencrypted columns. Instance filter results cannot replace per-column verification. If instance filters contradict column statuses, preserve the original responses and report the API semantic inconsistency; do not automatically select columns or claim verified status based on instance results.

Account card calculations:

- Plaintext access = `FullAccessCount`
- Ciphertext access = `RestrictedAccessCount + NoneAccessCount`
- Encryption not configured = `TotalCount - FullAccessCount - RestrictedAccessCount - NoneAccessCount`

The KMS page first obtains keys/aliases from `ListKmsKeys`, then uses KMS `DescribeKey` to check `KeyMetadata.KeyState == Enabled`. By default, `kms-keys` reproduces both steps and places the final available choices in `SelectableKeys`. If the calling identity lacks `kms:DescribeKey`, it preserves each key's read-only error and performs no writes.

## When Data Is Empty

Empty database, table, or column results do not usually mean that the script lacks an API. The column encryption page depends on assets authorized and synchronized into DSC, along with completed classification and grading results. Check the following in order:

1. Whether the instance has been authorized for DSC access.
2. Whether metadata has been synchronized.
3. Whether the classification and grading identification task has completed.
4. Whether the queried region, product, instance, and `TemplateId` are consistent.

Asset authorization, synchronization, and identification tasks can all change external state and are outside this read-only query script. If the user explicitly requests `SyncDataAssets`, use the preflight and confirmation workflow in [write-guide.md](write-guide.md). DAS `CreateMetadataSyncTask` is not part of the current SDDP page.
