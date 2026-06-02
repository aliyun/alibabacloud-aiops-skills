# Verification Methods: ECS Patch Management

This document describes how to verify the success of each step in the ECS patch management workflow.

---

## Step 1: Verify CLI and Credentials

**Verification:** Confirm Aliyun CLI is installed and credentials are valid.

```bash
aliyun version
aliyun configure list
aliyun ecs describe-regions --region cn-hangzhou
```

**Success Criteria:**
- CLI version >= 3.3.3
- `aliyun configure list` shows a valid profile with credentials
- `describe-regions` returns a JSON response with region list

---

## Step 2: Verify Target Instances Exist and Are Running

**Command:**
```bash
aliyun ecs describe-instances \
  --region <region-id> \
  --instance-ids '["<instance-id>"]' \
  --cli-query 'Instances.Instance[].{InstanceId:InstanceId, Status:Status, OSName:OSName}'
```

**Success Criteria:**
- Returns the target instance(s)
- Instance `Status` is `Running`
- Instance has a supported OS (CentOS, Ubuntu, Debian, Windows, etc.)

---

## Step 3: Verify Template Availability

**Command:**
```bash
aliyun oos list-templates \
  --region <region-id> \
  --name ACS-ECS-BulkyApplyPatchBaseline
```

**Success Criteria:**
- Template `ACS-ECS-BulkyApplyPatchBaseline` is found in the response
- Template is `Shared` or `Public` type

---

## Step 4: Verify Execution Started Successfully

**Command:**
```bash
aliyun oos start-execution \
  --region <region-id> \
  --biz-region-id <region-id> \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --parameters '<JSON_PARAMETERS>'
```

**Success Criteria:**
- Response contains `ExecutionId` field
- Initial `Status` is `Running` or `Started`

**Example Response:**
```json
{
  "Execution": {
    "ExecutionId": "exec-xxxxxxxxxxxxxxx",
    "Status": "Running",
    "TemplateName": "ACS-ECS-BulkyApplyPatchBaseline",
    "StartDate": "2024-01-15T10:30:00Z"
  }
}
```

---

## Step 5: Monitor Execution Progress

**Command:**
```bash
aliyun oos list-executions \
  --region <region-id> \
  --biz-region-id <region-id> \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --cli-query 'Executions.Execution[?TemplateName==`ACS-ECS-BulkyApplyPatchBaseline`].{ExecutionId:ExecutionId, Status:Status, StartDate:StartDate, EndDate:EndDate}'
```

**Status Values and Meanings** (canonical list — kept in sync with `SKILL.md` Step 4):

| Status | Terminal? | Meaning | Action |
|--------|-----------|---------|--------|
| `Success` | ✅ Terminal | Execution completed successfully | Proceed to Step 6 |
| `Failed` | ✅ Terminal | Execution failed | Check logs in Step 7 |
| `Cancelled` | ✅ Terminal | Execution was cancelled | Restart if needed |
| `Started` | ⏳ Non-terminal | Execution has been kicked off | Continue polling |
| `Running` | ⏳ Non-terminal | Execution is in progress | Continue polling |
| `Queued` | ⏳ Non-terminal | Execution is queued | Continue polling |
| `Waiting` | ⏳ Non-terminal | Execution is waiting for confirmation | Confirm or cancel |

---

## Step 6: Verify Patch Scan Results

**Command:**
```bash
aliyun oos list-instance-patches \
  --region <region-id> \
  --biz-region-id <region-id> \
  --instance-id <instance-id>
```

**Success Criteria for Scan:**
- Returns list of patches with their status
- Patches with status `Missing` indicate patches that need to be installed
- Patches with status `Installed` indicate already installed patches

**Key Patch Statuses:**

| Status | Description |
|--------|-------------|
| `Installed` | Patch is installed |
| `Missing` | Patch is available but not installed |
| `NotApplicable` | Patch does not apply to this system |
| `Failed` | Patch installation failed |

---

## Step 7: Verify Patch Installation Results

**Command:**
```bash
aliyun oos list-instance-patch-states \
  --region <region-id> \
  --biz-region-id <region-id> \
  --instance-ids '["<instance-id>"]'
```

**Success Criteria for Install:**
- Execution status is `Success`
- Number of `Missing` patches decreased compared to pre-install scan
- No patches with `Failed` status (or acceptable failures)

---

## Step 8: Check Execution Logs for Details

**Command:**
```bash
aliyun oos list-execution-logs \
  --region <region-id> \
  --execution-id <execution-id>
```

**Success Criteria:**
- Logs show successful patch scan/installation steps
- No error messages in the log output
- All target instances are processed

---

## Step 9: Verify Snapshot Creation (if enabled)

**Command:**
```bash
aliyun ecs describe-snapshots \
  --region <region-id> \
  --instance-id <instance-id>
```

**Success Criteria (when `whetherCreateSnapshot=true`):**
- New snapshot exists with recent creation time
- Snapshot `Status` is `accomplished` (completed)

---

## Overall Success Criteria Summary

| Phase | Verification | Command |
|-------|-------------|---------|
| Pre-flight | CLI version >= 3.3.3 | `aliyun version` |
| Pre-flight | Credentials valid | `aliyun configure list` |
| Pre-flight | Instance running | `aliyun ecs describe-instances` |
| Pre-flight | Template available | `aliyun oos list-templates` |
| Execution start | ExecutionId returned | `aliyun oos start-execution` output |
| Execution progress | Status = Success | `aliyun oos list-executions` |
| Scan result | Patches listed | `aliyun oos list-instance-patches` |
| Install result | Missing patches reduced | `aliyun oos list-instance-patch-states` |
| Logs | No errors | `aliyun oos list-execution-logs` |
| Snapshot (optional) | Snapshot created | `aliyun ecs describe-snapshots` |
