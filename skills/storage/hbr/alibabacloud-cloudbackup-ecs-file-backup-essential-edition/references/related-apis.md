# Related APIs - ECS File Backup Essential Edition

## API & CLI Command Reference

| Product | CLI Command | API Action | Description | CLI Supported |
|---------|-------------|------------|-------------|---------------|
| HBR | `aliyun hbr open-hbr-service` | OpenHbrService | Enable Cloud Backup service (开通云备份服务) | Yes |
| HBR | `aliyun hbr create-backup-plan` | CreateBackupPlan | Create/activate a backup plan (创建/激活备份计划) | Yes |
| HBR | `aliyun hbr describe-backup-plans` | DescribeBackupPlans | Query backup plan list (查询备份计划列表) | Yes |
| HBR | `aliyun hbr disable-backup-plan` | DisableBackupPlan | Pause a backup plan (暂停备份计划) | Yes |
| HBR | `aliyun hbr enable-backup-plan` | EnableBackupPlan | Resume a backup plan (恢复备份计划) | Yes |
| HBR | `aliyun hbr delete-backup-plan` | DeleteBackupPlan | Delete/cancel a backup plan (删除/取消备份计划) | Yes |
| HBR | `aliyun hbr update-backup-plan` | UpdateBackupPlan | Update a backup plan (schedule/priority, etc.) (更新备份计划) | Yes |
| HBR | `aliyun hbr describe-backup-jobs-2` | DescribeBackupJobs2 | Query backup job list (查询备份任务列表) | Yes |
| HBR | `aliyun hbr describe-backup-clients` | DescribeBackupClients | Query backup client status (查询备份客户端状态) | Yes |
| HBR | `aliyun hbr search-historical-snapshots` | SearchHistoricalSnapshots | Search historical backup snapshots (搜索历史备份版本) | Yes |
| HBR | `aliyun hbr get-basic-statistics` | GetBasicStatistics | Get basic statistics including capacity (获取基础统计信息) | Yes |
| HBR | `aliyun hbr create-restore-job` | CreateRestoreJob | Create a restore job (创建恢复任务) | Yes |
| HBR | `aliyun hbr describe-restore-jobs-2` | DescribeRestoreJobs2 | Query restore job status (查询恢复任务状态) | Yes |

## API Version Information

| Product | API Version | Endpoint |
|---------|-------------|----------|
| HBR (Cloud Backup, 云备份) | 2017-09-08 | hbr.{region}.aliyuncs.com |

## Key Parameter Descriptions

### edition

- `BASIC` - Essential Edition (基础版, for ECS File Backup Essential Edition)

### source-type

- `ECS_FILE` - ECS file backup (ECS文件备份)

### performanceLevel (Backup Priority, 备份优先级)

| Value | Meaning | Max Throughput | Recommended Data Volume |
|-------|---------|----------------|-------------------------|
| `L0` | Low priority (低优先级) | 10 MB/s, 1 vCPU | < 600 GB |
| `L1` | High priority (高优先级) | 30 MB/s, 2 vCPU | < 2 TB |

### Backup Plan Status (备份计划状态)

| Status | Description |
|--------|-------------|
| `ENABLED` | Enabled (已启用) |
| `DISABLED` | Paused (已暂停) |

### Client Status (客户端状态)

| Status | Description |
|--------|-------------|
| Preparing (准备中) | Client is being installed |
| Ready (就绪) | Client is ready |
| Backing Up (备份中) | Backup is in progress |

## Console-Only Operations (Not Available via CLI)

The following features are currently **not available via CLI** and require console access:

| Feature | Description | Console Path |
|---------|-------------|--------------|
| Backup Overview Dashboard | Visual display of backed-up ECS instances, block storage capacity, etc. | Cloud Backup Console > ECS File Backup Essential Edition |
| Browse File Directory | Browse the directory structure of backed-up files online | Backup Plan Details > Browse Files |
| Selective Single-File Restore | Select specific files to restore through the UI | Backup Plan Details > Restore Files |
| Modify Backup Time Window | Change the daily backup start time | Backup Plan Details > Edit |

## References

- [Cloud Backup API Documentation](https://help.aliyun.com/zh/cloud-backup/developer-reference/api-hbr-2017-09-08-overview)
- [ECS File Backup Essential Edition User Guide](https://help.aliyun.com/zh/cloud-backup/user-guide/ecs-file-backup-essential-edition)
