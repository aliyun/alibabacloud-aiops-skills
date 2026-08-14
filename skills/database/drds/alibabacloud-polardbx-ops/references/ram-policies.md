# RAM Permissions

This file is loaded when the pre-flight RAM permission check fails.

---

## Minimum RAM action set

If the user only uses the instance lifecycle and O&M operations covered by this skill, the RAM policy needs at least the following actions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "polardbx:CreateDBInstance",
        "polardbx:DeleteDBInstance",
        "polardbx:RestartDBInstance",
        "polardbx:DescribeDBInstanceAttribute",
        "polardbx:DescribeDBInstances",
        "polardbx:DescribeDBInstanceTopology",
        "polardbx:DescribeTasks",
        "polardbx:ModifyDBInstanceDescription",
        "polardbx:ModifyDBInstanceMaintainTime",
        "polardbx:UpgradeDBInstanceKernelVersion",
        "polardbx:UpdatePolarDBXInstanceNode",
        "polardbx:ModifyDBInstanceClass",
        "polardbx:DescribeScaleOutMigrateTaskList",
        "polardbx:DescribeDBInstanceConfig",
        "polardbx:ModifyDBInstanceConfig",
        "polardbx:DescribeParameters",
        "polardbx:ModifyParameter",
        "polardbx:DescribeParameterTemplates",
        "polardbx:DescribeDBNodePerformance",
        "polardbx:DescribeSlowLogRecords",
        "polardbx:DescribeBinaryLogList"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Extended action set (all modules)

When the user needs the extended modules (account, database, backup, security, audit, O&M tasks, HA/migration, connection/endpoint, tags, metadata, cold storage, data import/evaluate, SQL flashback, CDC, columnar, GDN, Mem0), add the following actions as well:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "polardbx:CreateAccount",
        "polardbx:DeleteAccount",
        "polardbx:DescribeAccountList",
        "polardbx:CreateSuperAccount",
        "polardbx:ResetAccountPassword",
        "polardbx:ResetAccountPasswordRestrict",
        "polardbx:ModifyAccountDescription",
        "polardbx:ModifyAccountPrivilege",
        "polardbx:CreateDB",
        "polardbx:DeleteDB",
        "polardbx:DescribeDbList",
        "polardbx:DescribeDistributeTableList",
        "polardbx:DescribeArchiveTableList",
        "polardbx:ModifyDatabaseDescription",
        "polardbx:CreateBackup",
        "polardbx:DescribeBackupPolicy",
        "polardbx:UpdateBackupPolicy",
        "polardbx:DescribeBackupSet",
        "polardbx:DescribeBackupSetList",
        "polardbx:DescribeOpenBackupSet",
        "polardbx:RestoreDBInstance",
        "polardbx:DescribeSecurityIps",
        "polardbx:ModifySecurityIps",
        "polardbx:DescribeDBInstanceSSL",
        "polardbx:UpdateDBInstanceSSL",
        "polardbx:DescribeDBInstanceTDE",
        "polardbx:UpdateDBInstanceTDE",
        "polardbx:DescribeUserEncryptionKeyList",
        "polardbx:CheckCloudResourceAuthorized",
        "polardbx:EnableSqlAudit",
        "polardbx:DisableSqlAudit",
        "polardbx:DescribeSqlAuditInfo",
        "polardbx:CheckSqlAuditSlsStatus",
        "polardbx:EnableRightsSeparation",
        "polardbx:DisableRightsSeparation",
        "polardbx:DescribeActiveOperationTasks",
        "polardbx:DescribeActiveOperationTaskCount",
        "polardbx:DescribeActiveOperationMaintainConf",
        "polardbx:ModifyActiveOperationMaintainConf",
        "polardbx:ModifyActiveOperationTasks",
        "polardbx:CancelActiveOperationTasks",
        "polardbx:DescribeEvents",
        "polardbx:SkipCurrentStep",
        "polardbx:CheckHealth",
        "polardbx:DescribeComponentPropeties",
        "polardbx:DescribeDBInstanceHA",
        "polardbx:SwitchDBInstanceHA",
        "polardbx:MigrateDBInstance",
        "polardbx:AlignStoragePrimaryAzone",
        "polardbx:ConfirmNoConnection",
        "polardbx:StartSwitchDatabase",
        "polardbx:DescribeTransformStatus",
        "polardbx:CreateTransformOperation",
        "polardbx:DescribeDBInstanceEndpoint",
        "polardbx:ModifyDBInstanceConnectionString",
        "polardbx:ModifyDBInstanceVip",
        "polardbx:CreateCustomEndpoint",
        "polardbx:DeleteCustomEndpoint",
        "polardbx:ModifyCustomEndpoint",
        "polardbx:ModifyCustomEndpointNet",
        "polardbx:DescribeCustomEndpointList",
        "polardbx:DescribeDBInstanceViaEndpoint",
        "polardbx:CreateSubCNInstance",
        "polardbx:DeleteSubCNInstance",
        "polardbx:TagResources",
        "polardbx:UntagResources",
        "polardbx:ListTagResources",
        "polardbx:DescribeTags",
        "polardbx:ChangeResourceGroup",
        "polardbx:UpdateCustinsParam",
        "polardbx:DescribeRegions",
        "polardbx:DescribeAvailableCrossRegions",
        "polardbx:DescribeEnabledCrossRegions",
        "polardbx:DescribeRdsVpcs",
        "polardbx:DescribeRdsVswitches",
        "polardbx:DescribeCharacterSet",
        "polardbx:DescribePolarxDataNodes",
        "polardbx:DescribeParameterGroups",
        "polardbx:AllocateColdDataVolume",
        "polardbx:ReleaseColdDataVolume",
        "polardbx:DescribeColdDataBasicInfo",
        "polardbx:CreateStoragePool",
        "polardbx:DescribeStoragePoolInfo",
        "polardbx:DescribeShowStorageInfo",
        "polardbx:CreateDataImportTask",
        "polardbx:DescribeDataImportTaskInfo",
        "polardbx:RestartDataImportTask",
        "polardbx:StopDataImportTask",
        "polardbx:CreateStructureImportTask",
        "polardbx:DescribeStructureImportTaskInfo",
        "polardbx:RefreshImportMeta",
        "polardbx:CreateSQLEvaluateTask",
        "polardbx:DescribeEvaluateAndImportTask",
        "polardbx:DescribeEvaluateAndImportTasks",
        "polardbx:DeleteEvaluateAndImportTask",
        "polardbx:CreateRplInspectionTask",
        "polardbx:DescribeRplInspectionTask",
        "polardbx:CloseEngineMigration",
        "polardbx:ModifyEngineMigration",
        "polardbx:DescribeSqlFlashbackTaskList",
        "polardbx:PreCheckSqlFlashbackTask",
        "polardbx:SubmitSqlFlashbackTask",
        "polardbx:DescribeCdcInfo",
        "polardbx:DescribeCdcClassList",
        "polardbx:DescribeCdcVersionList",
        "polardbx:ModifyCdcClass",
        "polardbx:UpgradeCDCVersion",
        "polardbx:AttachColumnarInstance",
        "polardbx:DescribeColumnarInfo",
        "polardbx:DescribeColumnarClassList",
        "polardbx:DescribeColumnarVersionList",
        "polardbx:ModifyColumnarClass",
        "polardbx:UpgradeColumnarVersion",
        "polardbx:CreateGdnInstance",
        "polardbx:DeleteGdnInstance",
        "polardbx:DescribeGdnInstances",
        "polardbx:CreateGdnStandbyMember",
        "polardbx:SwitchGdnMemberRole",
        "polardbx:CreateMem0",
        "polardbx:DeleteMem0",
        "polardbx:DescribeMem0Info",
        "polardbx:DescribeMem0SecurityIps",
        "polardbx:ModifyMem0SecurityIps",
        "polardbx:ResetMem0AccountPassword",
        "polardbx:CreateGatewayConsumerForPolarDBX"
      ],
      "Resource": "*"
    }
  ]
}
```

> Public-network actions (`polardbx:AllocateInstancePublicConnection`, `polardbx:ReleaseInstancePublicConnection`, `polardbx:AllocateMem0PublicConnection`, `polardbx:ReleaseMem0PublicConnection`) are intentionally excluded per the skill's no-public-exposure security policy. Grant them only if the user explicitly accepts the risk.

### Method 1: Call a PolarDB-X read API directly

```bash
aliyun polardbx describe-db-instances \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

Success: returns an instance list or empty list.  
Failure: errors such as `Forbidden.RAM` or `NoPermission` indicate the current identity lacks permissions.

### Method 2: View policies attached to the current user/role

```bash
# Current user
aliyun ram list-policies-for-user --user-name <UserName>

# Current role
aliyun ram list-policy-versions --policy-name <PolicyName>
```

---

## Common permission error handling

| Error code | Meaning | Fix |
|------------|---------|-----|
| `Forbidden.RAM` | RAM authorization failed | Ask the admin to attach a custom policy containing the actions above to the current identity |
| `NoPermission` | No permission to perform the operation | Check whether `sts:AssumeRole` or finer-grained authorization is needed |
| `InvalidAction.NotFound` | The API is not supported in the current region | Change `RegionId` and retry |

---

## Security principles

- Follow the least-privilege principle; do not directly grant `polardbx:*`.
- To control permissions per instance, replace `Resource` with the specific instance ARN.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
