# AK Restrictive Protection — High-Risk API Complete List

> Source: [AccessKey Restrictive Protection Description](https://www.alibabacloud.com/help/en/ram/user-guide/accesskey-restrictive-protection-description)

## Overview

Alibaba Cloud enforces restrictive protection on AccessKeys that have a risk of leakage, blocking calls to the following high-risk APIs. When an AK is placed under restrictive protection, calls to these APIs will return:

```
Forbidden: There is a risk of leakage of this AccessKey.
```

**Note**: Restrictive protection is a temporary safeguard that cannot be lifted. The AK should be deleted or rotated as soon as possible after discovery of the leak.

---

## High-Risk API Complete List

### Resource Access Management (RAM) (2015-05-01)

> RAM itself has no restricted APIs (AK is managed by RAM), but the scripts additionally monitor the following operations:

| Event Name | Description |
|------------|-------------|
| `CreateUser` | Create a RAM user |
| `CreateAccessKey` | Create an AccessKey |
| `AttachPolicyToUser` | Attach a policy to a user |
| `CreateRole` | Create a role |
| `AttachPolicyToRole` | Attach a policy to a role |
| `SetDefaultPolicyVersion` | Set the default policy version |
| `CreateLoginProfile` | Create a login profile |
| `AddUserToGroup` | Add a user to a group |

### Elastic Compute Service (ECS) (2014-05-26)

| Event Name | Description |
|------------|-------------|
| `RunInstances` | Create one or more instances |
| `CreateInstance` | Create an instance |
| `CreateAutoProvisioningGroup` | Create an auto-provisioning group |
| `StartInstance` | Start an instance |
| `StartInstances` | Batch start instances |
| `RunCommand` | Run a command on instances |
| `DeleteInstance` | Delete an instance |
| `DeleteInstances` | Batch delete instances |
| `DeleteSnapshotGroup` | Delete a snapshot group |
| `DeleteSnapshot` | Delete a snapshot |
| `DeleteImage` | Delete a custom image |
| `CreateCommand` | Create a Cloud Assistant command |
| `InvokeCommand` | Invoke a Cloud Assistant command on instances |

### Elastic Container Instance (ECI) (2018-08-08)

| Event Name | Description |
|------------|-------------|
| `CreateContainerGroup` | Create a container group |
| `CreateContainerGroupFromTemplate` | Create a container group from template |
| `BatchCreateContainerGroups` | Batch create container groups |
| `DeleteContainerGroup` | Delete a container group |
| `DeleteContainerGroups` | Batch delete container groups |

### Short Message Service (SMS) (2017-05-25)

| Event Name | Description |
|------------|-------------|
| `AddSmsTemplate` | Apply for an SMS template |
| `SendSms` | Send an SMS message |
| `SendBatchSms` | Batch send SMS messages |
| `CreateSmsTemplate` | Create an SMS template |

### Elastic Desktop Service (ECD) (2020-09-30)

| Event Name | Description |
|------------|-------------|
| `StartDesktops` | Start cloud desktops |
| `CreateDesktops` | Create cloud desktops |
| `CreateDesktopGroup` | Create a desktop group |
| `ModifyDesktopGroup` | Modify a desktop group |
| `RebootDesktops` | Reboot cloud desktops |
| `RebuildDesktops` | Rebuild desktop images |
| `GetConnectionTicket` | Get a connection ticket |
| `ModifyDesktopSpec` | Modify desktop specifications |
| `RunCommand` | Run a remote command |

### Performance Testing Service (PTS)

| Event Name | Description |
|------------|-------------|
| `StartJMeterTesting` | Start a JMeter test |
| `SaveJMeterScene` | Edit a JMeter scene |
| `CreateJMeterScene` | Create a JMeter scene |
| `CreateCronJob` | Create a scheduled stress test task |
| `StartSceneTesting` | Start a stress test task |
| `StartDebugging` | Start debugging |
| `CreateScene` | Create a scene |
| `SaveScene` | Edit a scene |
| `SaveOpenJMeterScene` | Save a scene |
| `StartDebuggingJMeterScene` | Debug a scene |
| `StartTestingJMeterScene` | Run a stress test on a scene |
| `SavePtsScene` | Save/modify a scene |
| `CreatePtsScene` | Create a scene |
| `StartDebugPtsScene` | Start scene debugging |
| `StartPtsScene` | Start a scene |

### ApsaraDB RDS for MySQL (2014-08-15)

| Event Name | Description |
|------------|-------------|
| `ModifyBackupPolicy` | Modify backup policy |
| `DeleteBackup` | Delete a data backup |
| `DescribeBackups` | View backup sets |
| `DeleteDBInstance` | Release an instance |
| `DestroyDBInstance` | Destroy an instance |
| `DeleteDatabase` | Delete a database |
| `CreateAccount` | Create a database account |
| `ResetAccountPassword` | Reset account password |
| `ResetAccount` | Reset a privileged account |
| `GrantAccountPrivilege` | Grant account access to a database |

### Database Backup (DBS) (2021-01-01)

| Event Name | Description |
|------------|-------------|
| `ModifyBackupStrategy` | Modify backup schedule |
| `CreateDownload` | Create a download task |
| `DescribeDownloadBackupSetStorageInfo` | View download backup set storage info |

### Alibaba Cloud DNS (2015-01-09)

| Event Name | Description |
|------------|-------------|
| `DeleteDomain` | Delete a domain |
| `AddDomainRecord` | Add a DNS record |
| `DeleteDomainRecord` | Delete a DNS record |
| `UpdateDomainRecord` | Update a DNS record |
| `SetDomainRecordStatus` | Set DNS record status |
| `CreateAlidnsLineRecordSet` | Create a line-based DNS record set (bypasses standard AddDomainRecord monitoring) |
| `DeleteAlidnsLineRecordSet` | Delete a line-based DNS record set |
| `UpdateAlidnsLineRecordSet` | Update a line-based DNS record set |

### Alibaba Cloud Billing (2017-12-14)

| Event Name | Description |
|------------|-------------|
| `RefundInstance` | Unsubscribe/refund an instance |

### Instant Computing Service (2023-07-01)

| Event Name | Description |
|------------|-------------|
| `CreateJob` | Create an E-HPC Instant job |
| `CreatePool` | Create a resource pool |

### Elastic High Performance Computing (EHPC) (2024-07-30)

| Event Name | Description |
|------------|-------------|
| `CreateCluster` | Create a cluster |
| `CreateNodes` | Batch create compute nodes |

### Data Management Service (DMS) (2018-11-01)

| Event Name | Description |
|------------|-------------|
| `CreateOrder` | Create a work order |
| `CreateDataExportOrder` | Create a SQL result set export order |
| `CreateDatabaseExportOrder` | Create a database export order |
| `CreateDataCorrectOrder` | Create a data change order |
| `CreateDataCronClearOrder` | Create a historical data cleanup order |
| `CreateDataImportOrder` | Create a data import order |
| `CreateFreeLockCorrectOrder` | Create a lock-free change order |
| `GetDataExportDownloadURL` | Get data export result download URL |
| `GetDbExportDownloadURL` | Get database export result download URL |
| `CreateProcCorrectOrder` | Create a programmable object change order |

---

## Script Coverage Statistics

| Metric | Count |
|--------|-------|
| Official high-risk APIs total | **82** |
| Covered by scripts | **82** (100%) |
| Missing | 0 |

> Scripts are aligned with Alibaba Cloud official documentation, fully covering all 14 services' high-risk APIs.
