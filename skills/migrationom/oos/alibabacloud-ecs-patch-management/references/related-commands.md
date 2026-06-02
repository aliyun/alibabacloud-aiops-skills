# Related CLI Commands: ECS Patch Management

This document lists all Aliyun CLI commands used in the ECS Patch Management skill.

---

## OOS Commands

### Start Execution

Start a patch scanning or installation execution using the `ACS-ECS-BulkyApplyPatchBaseline` template.

```bash
aliyun oos start-execution \
  --region <region-id> \
  --biz-region-id <region-id> \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --parameters '<JSON_PARAMETERS>'
```

**Key Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--template-name` | string | Template name: `ACS-ECS-BulkyApplyPatchBaseline` |
| `--parameters` | string | JSON string with execution parameters |
| `--biz-region-id` | string | Region ID where the execution runs |
| `--mode` | string | Execution mode: `Automatic` (default), `FailurePause`, `Debug` |
| `--safety-check` | string | Security check: `Skip`, `ConfirmEveryHighRiskAction` (default) |
| `--loop-mode` | string | Loop mode: `Automatic`, `FirstBatchPause`, `EveryBatchPause` |

**Parameters JSON structure for Scan:**

```json
{
  "regionId": "<region-id>",
  "action": "scan",
  "targets": {
    "ResourceIds": ["<instance-id-1>", "<instance-id-2>"],
    "RegionId": "<region-id>",
    "Type": "ResourceIds"
  }
}
```

**Parameters JSON structure for Install:**

```json
{
  "regionId": "<region-id>",
  "action": "install",
  "rebootIfNeed": true,
  "whetherCreateSnapshot": true,
  "retentionDays": 7,
  "targets": {
    "ResourceIds": ["<instance-id-1>", "<instance-id-2>"],
    "RegionId": "<region-id>",
    "Type": "ResourceIds"
  }
}
```

### List Executions

Query execution history and status.

```bash
aliyun oos list-executions \
  --region <region-id> \
  --biz-region-id <region-id> \
  --template-name ACS-ECS-BulkyApplyPatchBaseline \
  --status <status>
```

**Status values:**
- **Terminal** (stop polling): `Success`, `Failed`, `Cancelled`
- **Non-terminal** (keep polling): `Started`, `Running`, `Queued`, `Waiting`

See `SKILL.md` Step 4 for the canonical status taxonomy used by this skill.

### List Execution Logs

Query logs for a specific execution.

```bash
aliyun oos list-execution-logs \
  --region <region-id> \
  --execution-id <execution-id> \
  --biz-region-id <region-id>
```

### List Task Executions

Query task-level execution details.

```bash
aliyun oos list-task-executions \
  --region <region-id> \
  --biz-region-id <region-id> \
  --execution-id <execution-id>
```

### Cancel Execution

Cancel a running execution.

```bash
aliyun oos cancel-execution \
  --region <region-id> \
  --execution-id <execution-id>
```

### List Patch Baselines

Query available patch baselines.

```bash
aliyun oos list-patch-baselines \
  --region <region-id> \
  --biz-region-id <region-id> \
  --operation-system <OS-Type>
```

**OS Types:** `Windows`, `Ubuntu`, `CentOS`, `Debian`, `AliyunLinux`, `RedhatEnterpriseLinux`, `Anolis`, `AlmaLinux`

### List Instance Patches

Query patches installed on a specific instance.

```bash
aliyun oos list-instance-patches \
  --region <region-id> \
  --biz-region-id <region-id> \
  --instance-id <instance-id> \
  --patch-statuses <status>
```

### List Instance Patch States

Query patch compliance states for instances.

```bash
aliyun oos list-instance-patch-states \
  --region <region-id> \
  --biz-region-id <region-id> \
  --instance-ids '["<instance-id-1>", "<instance-id-2>"]'
```

---

## ECS Commands

### Describe Instances

Query ECS instance information to verify target instances.

```bash
aliyun ecs describe-instances \
  --region <region-id> \
  --instance-ids '["<instance-id-1>", "<instance-id-2>"]'
```

---

## Command Quick Reference Table

| Action | Command | Description |
|--------|---------|-------------|
| Scan patches | `aliyun oos start-execution --template-name ACS-ECS-BulkyApplyPatchBaseline --parameters '{"action":"scan",...}'` | Start patch scan execution |
| Install patches | `aliyun oos start-execution --template-name ACS-ECS-BulkyApplyPatchBaseline --parameters '{"action":"install",...}'` | Start patch install execution |
| Check status | `aliyun oos list-executions --template-name ACS-ECS-BulkyApplyPatchBaseline` | Query execution status |
| View logs | `aliyun oos list-execution-logs --execution-id <id>` | View execution logs |
| View patches | `aliyun oos list-instance-patches --instance-id <id>` | View instance patches |
| View patch states | `aliyun oos list-instance-patch-states --instance-ids '[...]'` | View patch compliance |
| Cancel execution | `aliyun oos cancel-execution --execution-id <id>` | Cancel running execution |
| List baselines | `aliyun oos list-patch-baselines` | List available patch baselines |
| Verify instances | `aliyun ecs describe-instances --instance-ids '[...]'` | Verify target instances |
