# Column Encryption API Contract for the New Architecture

The API inventory retains the verification recorded by the existing skill on 2026-09-04 against the `Sddp 2026-01-20` definitions in AMP project `3755263`, branch `master`, and the frontend package `yd-sddpV2/DE/1.0.4`. It was checked again on 2026-09-05 against the live Edge page and the current local source in `WorkProject/refactor2/yundun-dsc-service`; the repository HEAD was `b9e52357`, with the user's existing uncommitted changes preserved. Checking the current source does not re-establish which version is deployed online.

The scripts use the Python standard library for orchestration. They verify the specified CLI profile's mode (OAuth, AK, StsToken or RamRoleArn), then invoke the following APIs through that profile. The CLI owns credentials and signing. Business parameters, API versions, and regional endpoints follow the contract below; neither the profile nor RoleArn is an SDDP API parameter. See [runtime-constraints.md](runtime-constraints.md) for authentication prerequisites and verification boundaries.

## Complete Page Action Inventory

The current `?p=sddp#/DE/<RegionId>` page uses 25 SDDP Actions:

- General information and statistics: `GetUserStatus`, `ListRegions`, `ListTemplates`, `ListTotalSensitiveInfo`, `GetDataMaskingAccountCount`, `GetDataMaskingColumnCount`
- Filters and catalogs: `ListRiskLevels`, `ListIdentifyModels`, `ListDataMaskingInstances`, `ListDataSources`, `ListTables`, `ListColumns`
- Instance details: `CheckDataMaskingInstance`, `ListDataMaskingColumns`, `ListDataAssetAccounts`, `ListDataMaskingEncryptionAlgorithms`, `GetInstanceAttribute`, `ListKmsKeys`, `ListMiniEngineVersions`
- Changes: `CreateDataMaskingRule`, `DeleteDataMaskingRule`, `UpdateDataMaskingUsers`, `UpdateDataMaskingEncryptionAlgorithm`, `SyncDataAssets`, `UpgradeKernelVersion`

KMS candidate validation also calls the external KMS `2016-01-20 DescribeKey` API. See [query-guide.md](query-guide.md) and [write-guide.md](write-guide.md) for the corresponding safe commands and parameter mappings.

## Create API: `CreateDataMaskingRule`

- Action: `CreateDataMaskingRule`
- RAM Action: `yundun-sddp:CreateDataMaskingRule`
- Protocol: RPC over HTTPS, POST
- Regional endpoint: `sddp.<RegionId>.aliyuncs.com`
- Backend: `POST /datamasking/rule/create`
- Rate limit: 100 requests/second for both the user and the API
- Response: only `RequestId` is guaranteed; it acknowledges asynchronous acceptance, not the final encryption result

Public create fields:

| Field | Description |
| --- | --- |
| `RegionId` | Region used for Host routing; also the instance's region |
| `ProductCode` | `RDS`, `POLARDB`, `PolarDBX2` |
| `ProductId` | Optional; 5, 8, and 27 respectively. If supplied, it must match the product code |
| `InstanceId` | One instance ID |
| `EngineType` | Optional hint; the server resolves the actual engine again from instance attributes |
| `EncAlgorithm` | `AES_128_GCM`, `AES_256_GCM`, `SM4_128_GCM` |
| `EncryptionKeyMode` | `client_key` or `kms_key` |
| `EncryptionKeyId` | Key ID for KMS mode |
| `SubRuleList` | JSON array |
| `UserList` | JSON array |
| `ExpireTimeOperation` | `PRESERVE`, `CLEAR`, or `SET`; defaults to `PRESERVE` |
| `ExpireTime` | Unix timestamp in milliseconds for `SET` |
| `RiskHandleId` | Optional associated risk remediation ID |
| `Lang` | Optional language |

The only public fields in `SubRuleList[]` are `DbName`, `TableName`, and `Columns`. `Columns` is a comma-separated string of column names.

The only public field in `UserList[]` is `AccountId`. Its value is the database account name from `ListDataAssetAccounts.Items[].AccountName`, such as `app_user`, not the account record's numeric `Items[].Id`. When selecting an account, also verify `ProductCode` and `InstanceId`; matching the name alone is insufficient. The server sets every account role in a create request to `fullAccess`.

`ResourceGroupId` and `CooperationChannel` are private fields. The new architecture has neither the old script's `ServiceRegionId` nor `BackendRegionId`, and it does not accept the instance, region, engine, or key fields from legacy subrules.

`TemplateId` is not a public parameter of the current `CreateDataMaskingRule` API. It is used only for page filters, catalog queries, statistics, and asynchronous status verification; the script does not send it to the create API.

## Read-Only Preflight

Before creation, call the following with the same `RegionId`, `ProductCode`, and `InstanceId`:

1. `CheckDataMaskingInstance`: even if the outer request succeeds, inspect the business `ErrorCode`; only `Success` means the instance is eligible.
2. `GetInstanceAttribute`: obtain the actual engine, version, status, and `KmsEncryptionSupported`.
3. `ListDataMaskingEncryptionAlgorithms`: submit only if the target algorithm is present and no business error is returned.
4. `ListKmsKeys`: in KMS mode, confirm that the specified Key ID exists; the instance must also report KMS support.
5. KMS `DescribeKey`: confirm that the exact Key ID has state `Enabled`.
6. `ListDataMaskingInstances`, `ListDataMaskingColumns`, and `ListDataAssetAccounts`: read all pages for the instance's current algorithm/key, exact target columns, and selected accounts. The confirmation token binds this original state.

Do not equate OpenAPI HTTP success with successful business preflight. Partially overlapping pages, changing totals, or missing verifiable list/total information prevent the results from being treated as a complete snapshot or proof that a target does not exist.

## Asynchronous Verification

Query `ListDataMaskingColumns` by region, `TemplateId`, product, instance, database, table, and column. `Items[].Name` is the column name. Statuses include:

- `NotEncrypted`
- `Processing`
- `Success`
- `Failed`
- `Deleting`
- `DeleteFailed`

Report creation complete only when every target column is `Success` and the instance algorithm/key plus the selected allowlisted accounts' roles and expiration times match expectations. For `Failed`, return both `ErrorCode` and `ErrorMessage`. A missing record or a record still in `Processing` can only be reported as pending; do not automatically retry creation. Column-name queries may use fuzzy matching, so the script reads all pages and then verifies the database, table, and column exactly.

## Delete API: `DeleteDataMaskingRule`

- Backend: `POST /datamasking/rule/delete`
- Public parameters: `ProductId?`, `ProductCode`, `InstanceId`, `EngineType?`, `SubRuleList`, `Lang?`, and Host `RegionId`
- `SubRuleList[]`: only `DbName`, `TableName`, and comma-separated `Columns`
- Response: `RequestId`

The server locks and revalidates each instance. If no rule matches, the operation is a no-op; deleting the last effective rule disables the instance's column encryption status. The page's disable action targets `Success` columns, and the script likewise allows only exact targets whose preflight status is `Success`. Completion requires a complete, valid `ListDataMaskingColumns` snapshot showing `NotEncrypted` or that the target is no longer visible; pagination anomalies or query failures cannot prove deletion. `DeleteFailed` is a failure.

## Account API: `UpdateDataMaskingUsers`

- Backend: `POST /datamasking/user/batch/updateDataMaskingUsers`
- Public parameters: `ProductId?`, `ProductCode`, `AuthRole`, `UserList`, `Lang?`, `ExpireTimeOperation?`, `ExpireTime?`, and Host `RegionId`
- `UserList[]`: `AccountId` (database account name `AccountName`, not record `Id`) and `InstanceId`
- Response: `RequestId`; account changes in the cloud run asynchronously

A single request may span multiple instances of the same product in the same region, but one `AuthRole` applies to the whole batch. The server first verifies that every instance belongs to the product and that each Handler supports the role, then sends an asynchronous message for each instance.

`fullAccess` supports `PRESERVE`, `CLEAR`, and `SET`. `SET` requires a future timestamp in milliseconds; the server truncates it to seconds, and it must not exceed `2145953410000`. Requests for roles other than `fullAccess` must completely omit both expiration fields. `noneAccess` is available only for RDS MySQL when the instance already has an effective `client_key` rule. Verify roles and expiration times through `ListDataAssetAccounts`.

## Algorithm and Key API: `UpdateDataMaskingEncryptionAlgorithm`

- Backend: `POST /datamasking/rule/instance/modifyDataMaskingEncryptionAlgorithm`
- Public parameters: `EncryptionAlgorithm`, `ProductId?`, `ProductCode`, `InstanceId`, `EncryptionKeyId?`, `Lang?`, and Host `RegionId`
- Response: `RequestId`

This API does not expose `EncryptionKeyMode`. The server infers `kms_key` or `client_key` from the presence of `EncryptionKeyId`, and updates the algorithm/key for every rule on the instance. In the current code, only RDS MySQL and PolarDB-X 2.0 support changes. The algorithm must be available at the time of the request. KMS mode additionally requires instance KMS support, a key present in `ListKmsKeys`, and an `Enabled` result from `DescribeKey`. If neither the algorithm nor the key changes, the server performs a no-op. Verify the current algorithm and key through `ListDataMaskingInstances`.

## Asset Synchronization API: `SyncDataAssets`

- Backend: `POST /data/asset/sync`
- Public parameters: `ProductCode` and Host `RegionId`
- `ProductId` and `CooperationChannel` are private parameters and must not be sent
- Response: `RequestId`

The scope is all assets of the specified product for the calling account in that region, not one instance. Synchronization also covers databases, accounts, and allowlists, and may remove local asset records that no longer exist. The server prevents concurrent synchronization for the same product and handles internal message delivery itself; the client must not retry.

The current page has no SDDP Action for querying this synchronization task's final status. `RequestId` therefore means only that the request was accepted; it cannot prove completion.

## Upgrade API: `UpgradeKernelVersion`

- Backend: `POST /datamasking/check/instance/upgradeKernelVersion`
- Public parameters: `ProductId?`, `ProductCode`, `InstanceId`, `UpgradeTime`, `SwitchTime?`, `KernelVersion`, `Lang?`, and Host `RegionId`
- Response: AMP exposes only `RequestId`; the backend's internal task ID is not mapped to public output

`UpgradeTime` is `Immediate`, `MaintainTime`, or `SpecifyTime`. Only `SpecifyTime` includes a future `SwitchTime` in milliseconds; PolarDB-X 2.0 does not support `SpecifyTime`. The target version must come from a current `ListMiniEngineVersions` response. Observe the final version through `GetInstanceAttribute.CurrentKernelVersion`; if a scheduled task is not yet due or the upgrade takes longer, report only `PENDING`.

## Shared Field Boundaries

`TemplateId` is used for queries of templates, sensitivity levels, identification models, instances, tables, columns, column status, and column statistics. It is also part of the confirmation context for selecting columns before creation/deletion and verifying them afterward. However, it is not a public parameter of any of the six write APIs above and must not be sent to them.

`ResourceGroupId` and `CooperationChannel` are private fields. The new architecture does not use the old script's `ServiceRegionId` or `BackendRegionId`, and it does not accept legacy subrule fields for instance, region, engine, or key.

Do not equate OpenAPI HTTP success or `RequestId` with business completion. Creation, deletion, account changes, algorithm/key changes, and upgrades require observing the target state through the corresponding read-only APIs. Asset synchronization can only be marked `ACCEPTED_UNVERIFIED`.

## DAS Mode Boundary

The frontend action registry also contains `CreateMetadataSyncTask`, but it is shown only in the embedded page with `isFromDAS=true`, and its actual base path is `/openapi/DAS/2020-01-16/`. The current `?p=sddp` page neither renders nor calls it, and the SDDP AMP definitions in `yundun-dsc-service` have no Action with that name. It therefore is not one of the 25 SDDP APIs above and must not be presented as an SDDP `2026-01-20` request.
