# Reference Index

| Reference file | APIs covered | Typical scenarios | Load when |
|----------------|--------------|-------------------|-----------|
| [instance-lifecycle.md](instance-lifecycle.md) | `CreateDBInstance`, `DeleteDBInstance`, `RestartDBInstance`, `DescribeDBInstanceAttribute`, `DescribeDBInstances`, `DescribeDBInstanceTopology`, `DescribeTasks`, `ModifyDBInstanceDescription`, `ModifyDBInstanceMaintainTime`, `UpgradeDBInstanceKernelVersion` | Create, delete, restart, describe/list, modify description/maintenance window, upgrade kernel | User intent is instance lifecycle operation |
| [scaling.md](scaling.md) | `UpdatePolarDBXInstanceNode`, `ModifyDBInstanceClass`, `DescribeScaleOutMigrateTaskList` | Scale nodes, upgrade/downgrade, view migration progress | User intent is scaling or class change |
| [parameters.md](parameters.md) | `DescribeDBInstanceConfig`, `ModifyDBInstanceConfig`, `DescribeParameters`, `ModifyParameter`, `DescribeParameterTemplates` | View/modify instance config and compute/storage parameters | User intent is parameter management |
| [monitoring-logs.md](monitoring-logs.md) | `DescribeDBNodePerformance`, `DescribeSlowLogRecords`, `DescribeBinaryLogList` | Query node performance, slow SQL, binlog list | User intent is monitoring or log query |
| [account-management.md](account-management.md) | `CreateAccount`, `DeleteAccount`, `DescribeAccountList`, `CreateSuperAccount`, `ResetAccountPassword`, `ResetAccountPasswordRestrict`, `ModifyAccountDescription`, `ModifyAccountPrivilege` | Manage database accounts | User intent is account management |
| [database-management.md](database-management.md) | `CreateDB`, `DeleteDB`, `DescribeDbList`, `DescribeDistributeTableList`, `DescribeArchiveTableList`, `ModifyDatabaseDescription` | Manage databases and tables | User intent is database management |
| [backup-restore.md](backup-restore.md) | `CreateBackup`, `DescribeBackupPolicy`, `UpdateBackupPolicy`, `DescribeBackupSet`, `DescribeBackupSetList`, `DescribeOpenBackupSet`, `RestoreDBInstance` | Backup, restore, clone | User intent is backup/restore |
| [security-access.md](security-access.md) | `DescribeSecurityIps`, `ModifySecurityIps`, `DescribeDBInstanceSSL`, `UpdateDBInstanceSSL`, `DescribeDBInstanceTDE`, `UpdateDBInstanceTDE`, `DescribeUserEncryptionKeyList`, `CheckCloudResourceAuthorized` | IP whitelist, SSL, TDE, KMS | User intent is security/access control |
| [sql-audit-compliance.md](sql-audit-compliance.md) | `EnableSqlAudit`, `DisableSqlAudit`, `DescribeSqlAuditInfo`, `CheckSqlAuditSlsStatus`, `EnableRightsSeparation`, `DisableRightsSeparation` | SQL audit, rights separation | User intent is audit/compliance |
| [operation-tasks.md](operation-tasks.md) | `DescribeActiveOperationTasks`, `DescribeActiveOperationTaskCount`, `DescribeActiveOperationMaintainConf`, `ModifyActiveOperationMaintainConf`, `ModifyActiveOperationTasks`, `CancelActiveOperationTasks`, `DescribeEvents`, `SkipCurrentStep`, `CheckHealth`, `DescribeComponentPropeties` | O&M events, maintenance, events | User intent is O&M task management |
| [ha-migration.md](ha-migration.md) | `DescribeDBInstanceHA`, `SwitchDBInstanceHA`, `MigrateDBInstance`, `AlignStoragePrimaryAzone`, `ConfirmNoConnection`, `StartSwitchDatabase`, `DescribeTransformStatus`, `CreateTransformOperation` | HA switch, zone migration, transform | User intent is HA/migration |
| [connection-endpoint.md](connection-endpoint.md) | `DescribeDBInstanceEndpoint`, `ModifyDBInstanceConnectionString`, `ModifyDBInstanceVip`, `CreateCustomEndpoint`, `DeleteCustomEndpoint`, `ModifyCustomEndpoint`, `ModifyCustomEndpointNet`, `DescribeCustomEndpointList`, `DescribeDBInstanceViaEndpoint`, `CreateSubCNInstance`, `DeleteSubCNInstance` | Connection strings, VIP, endpoints | User intent is connection/endpoint |
| [tags-resourcegroup.md](tags-resourcegroup.md) | `TagResources`, `UntagResources`, `ListTagResources`, `DescribeTags`, `ChangeResourceGroup`, `UpdateCustinsParam` | Tags, resource group | User intent is tagging/resource group |
| [metadata-query.md](metadata-query.md) | `DescribeRegions`, `DescribeAvailableCrossRegions`, `DescribeEnabledCrossRegions`, `DescribeRdsVpcs`, `DescribeRdsVswitches`, `DescribeCharacterSet`, `DescribePolarxDataNodes`, `DescribeParameterGroups` | Regions, VPC, char set, data nodes | User intent is metadata query |
| [cold-storage.md](cold-storage.md) | `AllocateColdDataVolume`, `ReleaseColdDataVolume`, `DescribeColdDataBasicInfo`, `CreateStoragePool`, `DescribeStoragePoolInfo`, `DescribeShowStorageInfo` | Cold-data volume, storage pool | User intent is cold storage |
| [data-import.md](data-import.md) | `CreateDataImportTask`, `DescribeDataImportTaskInfo`, `RestartDataImportTask`, `StopDataImportTask`, `CreateStructureImportTask`, `DescribeStructureImportTaskInfo`, `RefreshImportMeta` | Data / structure import | User intent is data import |
| [data-evaluate-migration.md](data-evaluate-migration.md) | `CreateSQLEvaluateTask`, `DescribeEvaluateAndImportTask`, `DescribeEvaluateAndImportTasks`, `DeleteEvaluateAndImportTask`, `CreateRplInspectionTask`, `DescribeRplInspectionTask`, `CloseEngineMigration`, `ModifyEngineMigration` | SQL eval, replication, engine migration | User intent is evaluate/migration |
| [sql-flashback.md](sql-flashback.md) | `DescribeSqlFlashbackTaskList`, `PreCheckSqlFlashbackTask`, `SubmitSqlFlashbackTask` | SQL flashback recovery | User intent is SQL flashback |
| [cdc.md](cdc.md) | `DescribeCdcInfo`, `DescribeCdcClassList`, `DescribeCdcVersionList`, `ModifyCdcClass`, `UpgradeCDCVersion` | CDC / log engine | User intent is CDC management |
| [columnar.md](columnar.md) | `AttachColumnarInstance`, `DescribeColumnarInfo`, `DescribeColumnarClassList`, `DescribeColumnarVersionList`, `ModifyColumnarClass`, `UpgradeColumnarVersion` | Columnar (column store) | User intent is columnar management |
| [gdn.md](gdn.md) | `CreateGdnInstance`, `DeleteGdnInstance`, `DescribeGdnInstances`, `CreateGdnStandbyMember`, `SwitchGdnMemberRole` | Global Database Network | User intent is GDN management |
| [mem0.md](mem0.md) | `CreateMem0`, `DeleteMem0`, `DescribeMem0Info`, `DescribeMem0SecurityIps`, `ModifyMem0SecurityIps`, `ResetMem0AccountPassword`, `CreateGatewayConsumerForPolarDBX` | Mem0 memory engine | User intent is Mem0 management |
| [cli-installation-guide.md](cli-installation-guide.md) | aliyun CLI install/upgrade, plugin update, credential configuration, STS identity check | Fix CLI environment, config, and identity issues | Pre-flight CLI/config/identity checks fail |
| [ram-policies.md](ram-policies.md) | Minimum RAM action set, permission check commands, common permission error handling | Fix insufficient RAM permissions | Pre-flight RAM permission check fails |

---

## CLI command pattern

All business commands use plugin mode:

```bash
aliyun polardbx <action-name> --biz-region-id <RegionId> --region <RegionId> [other parameters]
```

- **Always pass `--region <RegionId>` (same value as `--biz-region-id`)**: the CLI resolves the API endpoint from the profile default region or the global `--region` flag; `--biz-region-id` alone does NOT route the request to that region's endpoint.
- Read operations should append: `--connect-timeout 3 --read-timeout 10`
- Write operations should append: `--connect-timeout 3 --read-timeout 30`
- Write operations should carry `--client-token` for idempotency
- Every `aliyun` API command must also include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}` per the Observability section in SKILL.md
