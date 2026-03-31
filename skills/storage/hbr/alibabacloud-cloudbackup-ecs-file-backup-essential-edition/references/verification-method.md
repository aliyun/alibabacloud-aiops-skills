# Verification Methods - ECS File Backup Essential Edition

This document describes how to verify that each operation has been executed successfully.

## 1. Activate Backup Verification

### Verification Steps

**Step 1: Confirm the backup plan has been created**
```bash
aliyun hbr describe-backup-plans \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --filters '[{"Key":"instanceId","Values":["<INSTANCE_ID>"]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**:
- The `BackupPlans` array contains a backup plan for the corresponding instance
- `BusinessStatus` is `ACTIVE`

**Step 2: Confirm backup job status**
```bash
aliyun hbr describe-backup-jobs-2 \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --filters '[{"Key":"instanceId","Values":["<INSTANCE_ID>"]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**:
- The first record returned is the latest backup job (sorted by creation time in descending order)
- `Status` is `COMPLETE` or `PARTIAL_COMPLETE`, indicating a successful backup

### Success Criteria
- Backup plan `BusinessStatus` is `ACTIVE`
- Latest backup job `Status` is `COMPLETE` or `PARTIAL_COMPLETE`

---

## 2. Pause Backup Verification

### Verification Steps

```bash
aliyun hbr describe-backup-plans \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --filters '[{"Key":"planId","Values":["<PLAN_ID>"]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**:
- The `Disabled` field is `true`

### Success Criteria
- Backup plan `Disabled` is `true`
- No new backup jobs are generated

---

## 3. Resume Backup Verification

### Verification Steps

```bash
aliyun hbr describe-backup-plans \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --filters '[{"Key":"planId","Values":["<PLAN_ID>"]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**:
- The `Disabled` field is `false`

### Success Criteria
- Backup plan `Disabled` is `false`
- The next backup window will execute a backup job

---

## 4. Cancel Backup Verification

### Verification Steps

```bash
# Check whether the backup plan has been deleted
aliyun hbr describe-backup-plans \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --filters '[{"Key":"instanceId","Values":["<INSTANCE_ID>"]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**:
- The `BackupPlans` array is empty
- Or it does not contain a backup plan for the specified instance

### Success Criteria
- No backup plan found for the corresponding instance
- The instance is no longer billed

---

## 5. Free Quota Viewing Verification

### Verification Steps

```bash
aliyun hbr get-basic-statistics \
  --edition BASIC \
  --source-type ECS_FILE \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**:
- Returns a `GlobalStatistics` object
- Contains the `ProtectedDataSize` field (unit: bytes)

### Key Metric Interpretation

| Metric | Description |
|--------|-------------|
| `ProtectedDataSize` | Total block storage capacity of backed-up ECS instances (bytes) |
| Free Quota (免费额度) | 100 GiB/account (permanent, shared across all regions) = 107,374,182,400 bytes |

**Calculation Example**:
```
ProtectedDataSize = 53,687,091,200 bytes = 50 GiB
Remaining Free Quota = 100 GiB - 50 GiB = 50 GiB
```

### Success Criteria
- The `ProtectedDataSize` value is retrieved successfully
- The value matches the console display

---

## 6. File Restore Verification

### Verification Steps

**Step 1: Query status after creating a restore job**
```bash
aliyun hbr describe-restore-jobs-2 \
  --region <REGION_ID> \
  --edition BASIC \
  --restore-type ECS_FILE \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Result**:
- The newly created restore job can be found
- The `Status` field shows the job status

### Restore Job Status Descriptions

| Status | Description |
|--------|-------------|
| `CREATED` | Job has been created (任务已创建) |
| `RUNNING` | Restore in progress (正在恢复) |
| `COMPLETE` | Restore completed (恢复完成) |
| `FAILED` | Restore failed (恢复失败) |
| `CANCELED` | Canceled (已取消) |

### Success Criteria
- Restore job status is `COMPLETE`
- Restored files are visible on the target ECS instance

---

## General Troubleshooting

### Common Errors and Solutions

| Error Message | Possible Cause | Solution |
|---------------|----------------|----------|
| `InvalidInstanceId` | ECS instance ID does not exist | Verify the instance ID is correct |
| `Forbidden.RAM` | Insufficient permissions | Check RAM policy configuration |
| `ServiceNotActivated` | Service not enabled | Run `open-hbr-service` first |
| `ClientNotInstalled` | Cloud Assistant (云助手) not installed | Install Cloud Assistant Agent on the ECS instance |

### Debug Command

```bash
# Enable verbose logging
aliyun hbr describe-backup-plans \
  --region cn-hangzhou \
  --edition BASIC \
  --source-type ECS_FILE \
  --log-level=debug \
  --user-agent AlibabaCloud-Agent-Skills
```
