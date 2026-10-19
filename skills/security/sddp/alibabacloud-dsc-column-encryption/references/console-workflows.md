# Console Filters and Complete Workflows

The main page, account permissions drawer, permission change dialog, and encryption configuration drawer at `?p=sddp#/DE/cn-zhangjiakou` were checked in Microsoft Edge on 2026-09-05. Query APIs and status semantics are also based on the new architecture implementation in `yundun-dsc-service`.

Before following these workflows, the user or trusted platform prepares a named CLI profile as described in [runtime-constraints.md](runtime-constraints.md). OAuth, AK, StsToken and RamRoleArn are supported. Use the same profile and mode for all queries, preflight checks and execution; `--profile dsc-oauth` remains the default. Being logged into the console in a browser does not mean CLI credentials are configured.

## Main Page Filters

| Page control | Input resolution and query parameters |
| --- | --- |
| Region | Value returned by `regions` → `--region-id`; Zhangjiakou is `cn-zhangjiakou` |
| All asset types | RDS → `RDS` / 5; PolarDB → `POLARDB` / 8; PolarDB-X 2.0 → `PolarDBX2` / 27 |
| All encryption statuses | Encrypted columns → `Success`; unencrypted columns → `NotEncrypted`; encryption failed → `Failed`; omit when not filtering |
| Template | `Items[].Id` from `templates --all-pages` → `--template-id`; show the template actually selected if the user does not specify one |
| All models | `identify-models --template-id …` (returns `RuleList` in one response, without pagination parameters) → `--template-rule-ids` for the main table/column status; table/column dropdowns use `--rule-id`; do not guess IDs from model names |
| All sensitivity levels | `sensitivity-levels --template-id …` (equivalent to `risk-levels`) → `--risk-level-ids` for the main table/column status; table/column dropdowns use `--risk-level-id`; resolve "S3 and above" from that template's returned levels |
| Instance name | Selected `InstanceId` → `--instance-id`; use `--instance-search` for fuzzy search |
| All databases | `DbName` returned by `databases` → `--db-name` |
| All tables | `Name` returned by `tables` → `--table-name`; preserve PostgreSQL/Oracle `schema.table` |
| All columns | `Name` from `columns` → `--column-name`; use `masking-columns` for final column status and creation candidates |

The main page has no separate engine dropdown. If the user specifies MySQL, PostgreSQL, or Oracle, filter by the actual `EngineType`; do not infer the engine from the product name alone. See `--help` and [query-guide.md](query-guide.md) for supported command parameters and exact filter scopes.

After a region change, fetch that region's instances and catalogs again. After an instance change, clear the old database, table, and column selections; after a database change, clear the old table and column selections. After a template change, resolve levels and models again. Do not reuse level IDs from the previous template.

"All" means omitting that filter field. Returned statuses such as `Processing` are not the same set as the statuses allowed in requests; do not send every returned enum value as a filter.

## Encrypt or Disable Encryption for Filtered Results

1. Query matching instances, then query `masking-columns` for each instance, retaining the same template, model, level, database, table, and column criteria. To find all unencrypted columns, omit `--masking-status NotEncrypted` when enumerating instances and apply it only to each instance's column query. Otherwise, partially encrypted instances are excluded and their unencrypted columns are missed. When only reproducing the console's main table, the user's instance-status filter may be retained, but the result must not be treated as a complete column inventory.
2. "All matching columns" requires reading every page and checking completeness. If the page limit is reached, whole or partial pages repeat, totals change, responses are incomplete, or queries fail, first narrow the scope or obtain a new valid snapshot. Do not use statistics-card counts as exact target lists or infer deletion from incomplete results.
3. Group results by `(RegionId, ProductCode, InstanceId)`, combining the unique columns of each table into `SubRuleList[].Columns`. Each create/delete request contains exactly one instance. Comma-separated instance IDs and cross-instance subrules are not allowed.
4. Generate a local configuration and run read-only preflight for each instance. Summarize each group's template, column list, unique column count, account permissions, and actual algorithm/key. Save each `EffectivePlan` with its corresponding confirmation token; do not store OAuth tokens or any cloud credentials in the configuration.
5. After the user confirms the exact plan, submit once per instance, sequentially. Account authorization and algorithm changes apply at instance scope; show their actual impact in the confirmation summary.
6. Verify each column and report counts and reasons for completed, failed, processing, and unknown results. If any result fails or remains uncertain, verify the already-submitted instances first and pause batches not yet submitted; do not replay the entire batch.

Use `DeleteDataMaskingRule` to disable encryption; select only `Success` columns by default. Retrying failed columns requires an explicit user request. See [SKILL.md](../SKILL.md) for the production execution workflow.

[config.example.json](config.example.json) omits algorithm and key fields by default so that new columns on an existing instance inherit its configuration; preflight resolves defaults for a new instance. Add `EncAlgorithm`, `EncryptionKeyMode`, and `EncryptionKeyId` only when the user explicitly selects an algorithm or key. Explicit `kms_key` without a key can inherit only an existing KMS key; a new instance requires a Key ID.

## Filter and Set Account Permissions

The account drawer includes all permissions, all asset types, instance name, and account search controls. It supports individual and batch changes.

| Page display | Query `--auth-role` / change `AuthRole` | Permission meaning |
| --- | --- | --- |
| Plaintext access | `fullAccess` | Queries of encrypted columns can return plaintext |
| Ciphertext access (JDBC decryption) | `restrictedAccess` | The database returns ciphertext, used through a supported client decryption path |
| Ciphertext access (no decryption permission) | `noneAccess` | Disables JDBC decryption for RDS MySQL rules using a local key; actual capability preflight is required |
| Encryption not configured | `unconfigured` (query only) | No column encryption authorization status yet; not a writable role |

Use `accounts --account-name … --instance-id … --product-code … --auth-role … --all-pages` for exact selection; use `--account-search` or `--instance-search` for fuzzy names. The main "ciphertext access" card totals both `restrictedAccess,noneAccess` categories. `UserList[].AccountId` uses the returned `AccountName`, not the numeric record `Id`; verify the product and instance even when account names match.

The expiration dropdown for `fullAccess` maps as follows: set → `SET` (future Unix milliseconds); preserve expiration time → `PRESERVE`; remove expiration time → `CLEAR`. Non-plaintext roles must completely omit both expiration fields. Selecting an expiration option, clicking a role, or closing the dialog does not establish a successful save.

A single request can include only accounts of the same product in the same region, and one `AuthRole` applies to every account. Separate different products, roles, or expiration requirements into distinct preflight plans. The user may confirm the exact batch plan once before sequential execution. Query templates and database/table/column filters do not restrict permissions to a column; account authorization applies to the instance.

Page hints may differ from actual product capabilities. Follow API preflight and the product Handler's role validation; in particular, do not infer from a shared hint that every database supports `noneAccess`.

## Other Page Operations and Boundaries

| Need | Entry point |
| --- | --- |
| Quota, sensitive columns/encryption status, and account statistics | `page`, `user-status`, `total-sensitive`, `column-count`, `account-count` |
| Instance encryption eligibility and reasons | `check-instance`, `instance-attribute` |
| View/change the algorithm, local key, or KMS key | `algorithms`, `kms-keys`; `UpdateDataMaskingEncryptionAlgorithm` |
| Refresh the current list | Repeat the query with the same criteria; read-only |
| Synchronize cloud assets | `SyncDataAssets`; covers all assets of the specified product in the region |
| Query and upgrade to supported kernel versions | `mini-engine-versions`; `UpgradeKernelVersion` |

The "upgrade" control beside the quota at the top of the page opens purchase/capacity expansion, not a kernel upgrade. A database's "go to upgrade" link may also open the product console; clicking it does not establish successful execution of `UpgradeKernelVersion`. Purchasing capacity, creating a KMS key, authorizing asset access, running classification/grading tasks, and adapting JDBC applications belong to their respective product workflows and must not be presented as column encryption APIs. The current SDDP page does not include the DAS-only `CreateMetadataSyncTask`.

## Ready-to-Use Requests

- Use `$alibabacloud-dsc-column-encryption` to list all matching unencrypted RDS columns at sensitivity level S3 or above under the financial industry template in Zhangjiakou.
- Use `$alibabacloud-dsc-column-encryption` to generate an encryption plan for the email and mobile columns of app_db.users on the specified instance, inheriting its current algorithm and key.
- Use `$alibabacloud-dsc-column-encryption` to query all accounts with ciphertext access on the specified instance, then give the selected app_user plaintext access while preserving its expiration time.
- Use `$alibabacloud-dsc-column-encryption` to check the specified instance's available algorithms, KMS keys, and available kernel upgrades, and generate a change plan for confirmation.
