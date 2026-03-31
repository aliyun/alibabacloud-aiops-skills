# RAM Permission Policies - ECS File Backup Essential Edition

## Required Permissions

### Least-Privilege Policy

The following is the minimum set of RAM permissions required to use ECS File Backup Essential Edition CLI commands:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hbr:OpenHbrService",
        "hbr:CreateBackupPlan",
        "hbr:DescribeBackupPlans",
        "hbr:DisableBackupPlan",
        "hbr:EnableBackupPlan",
        "hbr:DeleteBackupPlan",
        "hbr:DescribeBackupJobs2",
        "hbr:DescribeBackupClients",
        "hbr:SearchHistoricalSnapshots",
        "hbr:GetBasicStatistics",
        "hbr:CreateRestoreJob",
        "hbr:DescribeRestoreJobs2"
      ],
      "Resource": "*"
    }
  ]
}
```

### Permission Descriptions

| API Action | Description | Operation Type |
|------------|-------------|----------------|
| `hbr:OpenHbrService` | Enable Cloud Backup service (开通云备份服务, one-time operation) | Service Activation |
| `hbr:CreateBackupPlan` | Create a backup plan; activate ECS instance backup (创建备份计划) | Write |
| `hbr:DescribeBackupPlans` | Query backup plan list and status (查询备份计划列表和状态) | Read-only |
| `hbr:DisableBackupPlan` | Pause a backup plan (暂停备份计划) | Write |
| `hbr:EnableBackupPlan` | Resume a paused backup plan (恢复已暂停的备份计划) | Write |
| `hbr:DeleteBackupPlan` | Delete a backup plan / cancel backup (删除备份计划) | Write |
| `hbr:DescribeBackupJobs2` | Query backup job execution status (查询备份任务执行状态) | Read-only |
| `hbr:DescribeBackupClients` | Query backup client status (查询备份客户端状态) | Read-only |
| `hbr:SearchHistoricalSnapshots` | Search historical backup snapshots (搜索历史备份版本) | Read-only |
| `hbr:GetBasicStatistics` | Get capacity statistics (获取容量统计信息) | Read-only |
| `hbr:CreateRestoreJob` | Create a file restore job (创建文件恢复任务) | Write |
| `hbr:DescribeRestoreJobs2` | Query restore job status (查询恢复任务状态) | Read-only |

### Read-Only Policy

If you only need to view backup status and capacity information:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hbr:DescribeBackupPlans",
        "hbr:DescribeBackupJobs2",
        "hbr:DescribeBackupClients",
        "hbr:SearchHistoricalSnapshots",
        "hbr:GetBasicStatistics",
        "hbr:DescribeRestoreJobs2"
      ],
      "Resource": "*"
    }
  ]
}
```

### Service-Linked Role

When ECS File Backup Essential Edition is activated for the first time, the system automatically creates a service-linked role:

- **Role Name**: `AliyunServiceRoleForHbrEcsBackup`
- **Purpose**: Cloud Backup service uses this role to install backup clients and perform backup operations
- **Creation Method**: Automatically created; no manual configuration required

> **Note**: If the account lacks permission to create service-linked roles, backup activation may fail. Ensure the account has the `ram:CreateServiceLinkedRole` permission.

### Recommended System Policies

Alibaba Cloud provides the following system policies for direct use:

| Policy Name | Description |
|-------------|-------------|
| `AliyunHBRFullAccess` | Full access to Cloud Backup |
| `AliyunHBRReadOnlyAccess` | Read-only access to Cloud Backup |

## References

- [Cloud Backup RAM Permission Reference](https://help.aliyun.com/zh/cloud-backup/developer-reference/authorization-rules)
- [RAM Access Control Console](https://ram.console.aliyun.com/)
