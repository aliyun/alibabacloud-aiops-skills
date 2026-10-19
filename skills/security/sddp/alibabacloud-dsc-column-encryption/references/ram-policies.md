# RAM Permissions

## Authentication is separate from authorization

Use an explicit Alibaba Cloud CLI profile in OAuth, AK, StsToken or RamRoleArn mode. Credential setup is performed by the user or trusted platform outside the agent session; see [runtime-constraints.md](runtime-constraints.md). OAuth application assignment, holding an AccessKey or obtaining an STS token does not itself grant DSC or KMS API permissions.

For RamRoleArn, the source identity needs `sts:AssumeRole` scoped to the intended role, and the role's trust policy must allow that source identity. The target role needs the relevant DSC/KMS permissions below. An administrator must review both sides; the skill does not attach either policy. See the [official role-assumption prerequisites](https://www.alibabacloud.com/help/en/ram/user-guide/assume-a-ram-role). These authentication permissions are separate from the 26 business API dependencies.

The examples below are permission inventories for administrator review, not instructions to grant access automatically. Start with queries; add only the changes the operator is authorized to perform. Do not default to administrator policies or wildcard actions. AK is opt-in, not a fallback after another mode fails. This skill does not create roles, attach policies, or change OAuth application assignments.

## DSC scope and contract source

The 25 actions in `related_apis.yaml` use the RAM prefix `yundun-sddp:`, not `sddp:`. The reviewed `Sddp/2026-01-20` AMP definitions specify gateway authorization at operation granularity, with resource template `acs:yundun-sddp::{#accountId}:*`. The examples retain that account-level scope. Replace `<account-id>` with the resource-owning Alibaba Cloud account ID; confirm the deployed API contract with your administrator before attaching a policy.

The action/resource mappings were checked against the saved AMP definitions dated 2026-09-05 and the repository API contract. The [public DSC RAM reference](https://help.aliyun.com/en/dsc/data-security-center/developer-reference/api-sddp-2019-01-03-ram) also documents the namespace and operation-level model, but its older API catalog is not the source for the new action names.

These DSC permissions are not restricted to one database instance, table or column. `RegionId`, `TemplateId`, `InstanceId` and column filters are business parameters, not RAM resource boundaries. In particular, a classification template cannot narrow an instance-wide account or algorithm change.

## Query permissions

This policy covers all 19 bundled DSC queries, including discovery, preflight and post-write verification. An administrator may select a smaller set for a narrower workflow, but must retain all queries that workflow needs. A failed preflight permission check is not permission to skip validation.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sddp:GetUserStatus",
        "yundun-sddp:ListRegions",
        "yundun-sddp:ListTemplates",
        "yundun-sddp:ListTotalSensitiveInfo",
        "yundun-sddp:GetDataMaskingAccountCount",
        "yundun-sddp:ListIdentifyModels",
        "yundun-sddp:ListRiskLevels",
        "yundun-sddp:ListDataMaskingInstances",
        "yundun-sddp:GetDataMaskingColumnCount",
        "yundun-sddp:CheckDataMaskingInstance",
        "yundun-sddp:ListDataSources",
        "yundun-sddp:ListTables",
        "yundun-sddp:ListColumns",
        "yundun-sddp:ListDataMaskingColumns",
        "yundun-sddp:ListDataAssetAccounts",
        "yundun-sddp:ListDataMaskingEncryptionAlgorithms",
        "yundun-sddp:GetInstanceAttribute",
        "yundun-sddp:ListKmsKeys",
        "yundun-sddp:ListMiniEngineVersions"
      ],
      "Resource": ["acs:yundun-sddp::<account-id>:*"]
    }
  ]
}
```

`ListKmsKeys` lists candidate keys through DSC; the reviewed platform metadata labels its operation type as write, although the API contract and skill use it only to query keys. Do not infer permission scope from a UI badge or add unrelated write actions because of that label.

## Change permissions: opt in per operation

The following is the complete six-action inventory, not the default policy for a query-only user. Retain only approved actions and combine them with the required query permissions above. Having RAM permission does not replace the user's approval of an exact `EffectivePlan` and its confirmation token.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sddp:CreateDataMaskingRule",
        "yundun-sddp:DeleteDataMaskingRule",
        "yundun-sddp:UpdateDataMaskingUsers",
        "yundun-sddp:UpdateDataMaskingEncryptionAlgorithm",
        "yundun-sddp:SyncDataAssets",
        "yundun-sddp:UpgradeKernelVersion"
      ],
      "Resource": ["acs:yundun-sddp::<account-id>:*"]
    }
  ]
}
```

Creating or deleting rules changes column protection. Account-access updates change plaintext visibility and possibly expiry. Algorithm/key changes affect the instance configuration. Asset synchronization and kernel upgrades can have wider scope or availability impact; approve them separately. Never automatically retry an uncertain write.

## KMS inspection: limit access to approved keys

The `kms-keys` query and create/algorithm-change preflight call `Kms/2016-01-20 DescribeKey` when inspecting KMS keys. This reads key metadata and state, not key material. Grant `kms:DescribeKey` only for the approved key ARN or explicit list of key ARNs:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["kms:DescribeKey"],
      "Resource": ["acs:kms:<region>:<account-id>:key/<key-id>"]
    }
  ]
}
```

Replace all placeholders with the actual key region, owning account and key ID. A broad key-listing query may encounter keys outside this grant; do not silently broaden the policy. Use explicit approved targets or report the missing permission.

See the [DescribeKey API reference](https://help.aliyun.com/zh/kms/key-management-service/developer-reference/api-kms-2016-01-20-describekey) and the [official key-scoped RAM policy example](https://help.aliyun.com/en/kms/key-management-service/use-cases/use-oss-client-encryption-combined-with-kms-managed-keys-to-achieve-data-security). Only the `DescribeKey` action and key ARN pattern are relevant here; do not copy that example's OSS, encryption/decryption or credential setup permissions into this skill's caller policy.

This skill does not directly call `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey` or key-management write APIs. DSC's separate service-side encryption authorization and KMS key policy may still need administrator setup; caller metadata access alone does not prove the service can use the key.

## Permission failure handling

Stop before a write when a required query or KMS check is denied. Report the specific action, intended resource and safe error code/request ID when available. Ask the administrator to review that minimum permission. Do not print raw CLI diagnostics, tokens or credential files, grant permissions yourself, switch identity silently, or fall back to AK. After an approved permission or identity change, repeat discovery and preflight before seeking approval for the effective write plan.
