# Change Guide for the Column Encryption Page

`scripts/manage_column_encryption.py` wraps the five SDDP page write Actions other than creation. Each JSON object may contain only one `Action`. By default, it performs only local validation; `--preflight` is read-only. Only `--execute --confirm-token ...` submits a single write request.

Both preflight and execution call APIs through the same Alibaba Cloud CLI profile and mode: OAuth, AK, StsToken or RamRoleArn. The default is `--profile dsc-oauth`; replace it with the user's selected profile for other modes. Local dry runs require no credentials. See [runtime-constraints.md](runtime-constraints.md) for online setup. The profile name is a script argument, not a field in the business JSON.

## Delete Column Encryption Rules

```json
{
  "Action": "DeleteDataMaskingRule",
  "RegionId": "cn-hangzhou",
  "TemplateId": 123456,
  "ProductCode": "RDS",
  "InstanceId": "rm-xxx",
  "EngineType": "mysql",
  "SubRuleList": [
    {"DbName": "app_db", "TableName": "users", "Columns": "email,mobile"}
  ],
  "Lang": "zh_cn"
}
```

Preflight confirms that the template exists, validates instance eligibility and the actual engine, and requires every exact target to be currently `Success`. After deletion, the read-only terminal state is `NotEncrypted` or the target no longer being visible in a complete, valid snapshot. Partially overlapping pages, changing totals, missing response fields, or query failures cannot prove that the target is absent and cannot establish successful deletion. Deleting the last effective rule on an instance also disables that instance's column encryption asset status.

## Change Account Permissions

```json
{
  "Action": "UpdateDataMaskingUsers",
  "RegionId": "cn-hangzhou",
  "ProductCode": "RDS",
  "AuthRole": "fullAccess",
  "UserList": [
    {"InstanceId": "rm-xxx", "AccountId": "app_user"}
  ],
  "ExpireTimeOperation": "PRESERVE",
  "Lang": "zh_cn"
}
```

Set `AccountId` to the database account name (`ListDataAssetAccounts.Items[].AccountName`, such as `app_user`), not the numeric record `Items[].Id`. Both preflight and verification after a write must check the account's association with the product and instance. A returned record with the same name but a different product must neither pass validation nor establish write success.

A single request can contain accounts from multiple instances of the same product in the same region. `AuthRole` applies to the entire batch:

- `fullAccess`: plaintext access; supports `PRESERVE`, `CLEAR`, and `SET`.
- `restrictedAccess`: ciphertext access (JDBC decryption); both expiration fields must be omitted.
- `noneAccess`: ciphertext access (no decryption permission); supported only for RDS MySQL with a currently effective `client_key` rule. Expiration fields must also be omitted.
- `unconfigured`: encryption not configured; a query filter only, not a role that can be assigned.

For `SET`, add a future timestamp in milliseconds:

```json
"ExpireTimeOperation": "SET",
"ExpireTime": 1893456000000
```

Preflight validates each instance's eligibility and actual engine, confirms that each account exists, and binds the current role, expiration time, and key mode to the confirmation token. After execution, verify roles and expiration times through `ListDataAssetAccounts`.

Account permission and expiration queries operate at instance scope and are not restricted by the main page's template, database, table, or column criteria. For an instance with no encryption rules, public queries may continue to show `unconfigured` and hide expiration even after the backend has accepted permission settings. In that case, do not claim verified completion or submit repeatedly.

The hidden original expiration for `unconfigured + PRESERVE` cannot be determined through public queries; it does not mean permanent access. The plan marks `ExpireTimeKnown=false`, and execution does not claim that preservation of the expiration time has been proven. The result remains `PENDING` with an explanation. Allowlists configured during creation follow the same rule. Change the expiration requirement only if the user explicitly chooses `CLEAR` or `SET`; do not clear expiration on your own to make verification pass.

## Change the Algorithm or Key Mode

Local key example:

```json
{
  "Action": "UpdateDataMaskingEncryptionAlgorithm",
  "RegionId": "cn-hangzhou",
  "ProductCode": "RDS",
  "InstanceId": "rm-xxx",
  "EncryptionAlgorithm": "AES_256_GCM",
  "EncryptionKeyMode": "client_key"
}
```

KMS example:

```json
{
  "Action": "UpdateDataMaskingEncryptionAlgorithm",
  "RegionId": "cn-hangzhou",
  "ProductCode": "RDS",
  "InstanceId": "rm-xxx",
  "EncryptionAlgorithm": "AES_256_GCM",
  "EncryptionKeyMode": "kms_key",
  "EncryptionKeyId": "key-xxx"
}
```

This is an instance-level change affecting all effective rules on that instance. The current backend permits changes only for RDS MySQL and PolarDB-X 2.0. Preflight checks instance eligibility, existing rules, the current algorithm list, KMS capabilities, `ListKmsKeys` candidates, and KMS `DescribeKey.KeyState=Enabled`.

The AMP `UpdateDataMaskingEncryptionAlgorithm` API has no `EncryptionKeyMode` parameter. The script uses it for validation and confirmation, but the actual request lets the server infer the mode from the presence or absence of `EncryptionKeyId`. After execution, verify the algorithm and Key ID through `ListDataMaskingInstances`.

## Synchronize Assets

```json
{
  "Action": "SyncDataAssets",
  "RegionId": "cn-hangzhou",
  "ProductCode": "RDS"
}
```

The scope is all assets of this product for the calling account in the region, rather than one instance, and synchronization also covers databases, accounts, and allowlists. `ProductId` is a private field in AMP; public requests can use only `ProductCode`.

The page has no Action for querying synchronization task status. After receiving `RequestId`, report only `ACCEPTED_UNVERIFIED`; do not claim synchronization is complete or resubmit because of a timeout.

## Upgrade the Kernel

```json
{
  "Action": "UpgradeKernelVersion",
  "RegionId": "cn-hangzhou",
  "ProductCode": "RDS",
  "InstanceId": "rm-xxx",
  "UpgradeTime": "MaintainTime",
  "KernelVersion": "20260131",
  "Lang": "zh_cn"
}
```

To specify a time, use:

```json
"UpgradeTime": "SpecifyTime",
"SwitchTime": 1893456000000
```

Preflight obtains the current version and maintenance window through `GetInstanceAttribute`, and uses `ListMiniEngineVersions` to require that the target version is currently available. PolarDB-X 2.0 does not support `SpecifyTime`. Upgrades may affect database availability and require separate, explicit confirmation. AMP does not return a task ID. After execution, poll the current version and report `PENDING` if it does not reach the target within the waiting window.

## Shared Safety Semantics

- `RegionId` is used only for Host routing through `sddp.<RegionId>.aliyuncs.com`; it is not included in ordinary request parameters.
- `TemplateId` is used only for column selection and verification during creation/deletion. It is not sent to any write API.
- If `ProductId` is public and supplied, it must match `ProductCode`; the synchronization API forbids it.
- Reject legacy fields `ServiceRegionId` and `BackendRegionId`, and private fields `ResourceGroupId` and `CooperationChannel`.
- The confirmation token binds the write parameters and the original state observed during preflight. Execution reruns preflight and rejects the old token if the original state has changed.
- Set CLI request retries to 0 and disable automatic throttling retries. If the network result is uncertain, verify through read-only queries and do not automatically resubmit.
- Online calls verify the selected profile's supported mode and reject changes during a workflow, then use that profile through the CLI while ignoring inherited AK/STS environment variables. Failure must not trigger profile/mode fallback. The CLI owns signing and supported refresh flows; fixed StsToken credentials must be renewed by the user or trusted platform. Scripts and agents do not read, export or copy cloud credentials. Confirmation tokens bind the profile name and mode; valid credentials never replace approval of the exact business plan.
