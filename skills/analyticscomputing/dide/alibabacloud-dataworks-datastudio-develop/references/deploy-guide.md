# Deployment Guide

This document provides a detailed description of the deployment (online/offline) process in DataWorks data development. Deployment is an asynchronous multi-stage pipeline that requires polling for status and advancing each stage.

---

## Workspace Modes and Deployment

DataWorks workspaces have two modes with different deployment processes:

| | Simple Mode | Standard Mode |
|---|---|---|
| Environments | Production only | Development + Production |
| Development flow | Create node -> Deploy -> Production scheduling | Create node (dev) -> Submit -> Deploy -> Production scheduling |
| Deployment meaning | Deploy directly to production | Deploy from development to production environment |
| Number of stages | Fewer (3 observed in practice) | More (may include code review, smoke test, approval, etc.) |

**How to determine**: Use the `GetProject` API to check `envTypes`; size=1 means Simple Mode, size=2 means Standard Mode.

---

## Deployment State Machine

### Pipeline Overall Status

```
Init -> Running -> Success
                -> Fail
                -> Termination
                -> Cancel
```

| Status | Meaning |
|------|------|
| `Init` | Initialized |
| `Running` | In progress (includes waiting for stage advancement) |
| `Success` | All stages completed, deployment successful |
| `Fail` | A stage has failed |
| `Termination` | Terminated |
| `Cancel` | Cancelled |

### Stage Status

Each stage has the same status values as the Pipeline: `Init` / `Running` / `Success` / `Fail` / `Termination` / `Cancel`

### Stage Types

| Type | Meaning | Requires manual advancement |
|------|------|:---:|
| `Build` | Build the deployment package | No (runs automatically) |
| `Check` | Check (production checker, code review, etc.) | Yes |
| `Deploy` | Deploy to production environment | Yes |
| `Offline` | Take offline | Yes |
| `Delete` | Delete | Yes |

### Observed Stages in Simple Mode

```
Step 1: BUILD_PACKAGE (Type=Build)     <- Runs automatically
Step 2: PROD_CHECK   (Type=Check)      <- Requires ExecPipelineRunStage to advance
Step 3: PROD         (Type=Deploy)     <- Requires ExecPipelineRunStage to advance
```

BUILD_PACKAGE includes the following checks:
- `BuildPackageChecker` -- Package build check
- `NodeParentDependency` -- Downstream dependency check
- `NodeInProcess` -- In-progress offline process check

### Possible Stages in Standard Mode

Stages in Standard Mode are based on the actual response from `GetPipelineRun` and may include:
- `DEV_CHECK` -- Development environment check
- Code review stage
- Smoke test stage
- Approval stage (may require manual action in the console)
- `PROD_CHECK` -- Production environment check
- `PROD` -- Deploy to production

**Do not hardcode the stage list**; always handle stages dynamically based on the Stages returned by the API.

---

## Deployment API Overview

| API | Purpose |
|-----|------|
| `CreatePipelineRun` | Create a deployment process |
| `GetPipelineRun` | Get deployment status and stages |
| `ExecPipelineRunStage` | Advance a stage (async) |
| `ListPipelineRunItems` | View the list of nodes included in the deployment |
| `ListPipelineRuns` | Query deployment history |
| `AbolishPipelineRun` | Cancel a deployment |

---

## CLI vs SDK Response Field Differences

> **Important**: The `aliyun` CLI and Python SDK return different JSON structures; do not mix them.

| Scenario | CLI (`aliyun` command) | Python SDK |
|------|---------------------|------------|
| Deployment creation returns ID | `json['Id']` | `resp.body.id` |
| Get Pipeline object | `json['Pipeline']` | `resp.body.pipeline.to_map()` |
| Pipeline status | `json['Pipeline']['Status']` | `pipeline['Status']` |
| Stages list | `json['Pipeline']['Stages']` | `pipeline['Stages']` |

---

## Deployment Process (Online)

### Step 1: Create Deployment

**CLI**:
```bash
aliyun dataworks-public CreatePipelineRun \
  --ProjectId $PROJECT_ID \
  --Type Online \
  --ObjectIds "[\"$WORKFLOW_ID\"]" \
  --user-agent AlibabaCloud-Agent-Skills
# Example response: {"Id": "ae781cc7-...", "RequestId": "..."}
# Record the Id for subsequent polling
```

**SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreatePipelineRunRequest

resp = client.create_pipeline_run(CreatePipelineRunRequest(
    project_id=PROJECT_ID,
    type='Online',
    object_ids=['node_ID_or_workflow_ID']
))
run_id = resp.body.id
```

**Notes**:
- `type` values: `Online` (deploy) or `Offline` (take offline)
- `object_ids` only processes the first entity and its child entities; batch deployment of multiple independent entities is not supported
- When deploying a workflow, pass the workflow ID to deploy all internal nodes simultaneously

### Step 2: Poll and Advance Each Stage

**CLI** (copy-ready):
```bash
#!/bin/bash
# Deployment polling and advancement script (CLI version)
PIPELINE_ID="<Id returned by CreatePipelineRun>"
PROJECT_ID="<project_ID>"

for i in $(seq 1 60); do
  RESP=$(aliyun dataworks-public GetPipelineRun \
    --Id "$PIPELINE_ID" --ProjectId "$PROJECT_ID" \
    --user-agent AlibabaCloud-Agent-Skills 2>&1)

  # Note: CLI returns Pipeline as the top-level key (not PipelineRun)
  STATUS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('Pipeline',{}).get('Status',''))")
  echo "[$i] Pipeline status: $STATUS"

  # Terminal state check
  if [ "$STATUS" = "Success" ] || [ "$STATUS" = "Fail" ] || [ "$STATUS" = "Cancel" ]; then
    echo "Pipeline finished: $STATUS"
    break
  fi

  # Find the Init stage that needs to be advanced (all prior stages are Success)
  STAGE_CODE=$(echo "$RESP" | python3 -c "
import sys, json
data = json.load(sys.stdin).get('Pipeline', {})
stages = data.get('Stages', [])
for s in stages:
    if s.get('Status') == 'Init':
        prior_ok = all(s2.get('Status') == 'Success' for s2 in stages if s2.get('Step',0) < s.get('Step',0))
        if prior_ok:
            print(s.get('Code', ''))
            break
")

  if [ -n "$STAGE_CODE" ]; then
    echo "  Pushing stage: $STAGE_CODE"
    aliyun dataworks-public ExecPipelineRunStage \
      --Id "$PIPELINE_ID" --ProjectId "$PROJECT_ID" --Code "$STAGE_CODE" \
      --user-agent AlibabaCloud-Agent-Skills
  fi

  sleep 5
done
```

**SDK**:
```python
import time
from alibabacloud_dataworks_public20240518.models import (
    GetPipelineRunRequest, ExecPipelineRunStageRequest
)

MAX_POLL = 60       # Maximum number of polling attempts
POLL_INTERVAL = 3   # Polling interval (seconds)

for i in range(MAX_POLL):
    time.sleep(POLL_INTERVAL)

    resp = client.get_pipeline_run(GetPipelineRunRequest(
        project_id=PROJECT_ID,
        id=run_id
    ))
    pipeline = resp.body.pipeline.to_map()
    status = pipeline['Status']
    stages = pipeline.get('Stages', [])

    # Print current status
    stage_info = ' -> '.join(f"{s['Code']}({s['Status']})" for s in stages)
    print(f"[{status}] {stage_info}")

    # Terminal state check
    if status in ('Success', 'Fail', 'Termination', 'Cancel'):
        if status == 'Success':
            print("Deployment successful")
        else:
            msg = pipeline.get('Message', '')
            print(f"Deployment ended: {status}, {msg}")
        break

    # Find the stage that needs to be advanced
    for j, stage in enumerate(stages):
        if stage['Status'] == 'Fail':
            print(f"Stage failed: {stage['Name']} - {stage.get('Message', '')}")
            break

        if stage['Status'] == 'Init':
            # Check if all prior stages have completed
            prev_all_success = all(
                stages[k]['Status'] == 'Success' for k in range(j)
            )
            if prev_all_success:
                print(f"Advancing stage: {stage['Name']} ({stage['Code']})")
                try:
                    client.exec_pipeline_run_stage(ExecPipelineRunStageRequest(
                        project_id=PROJECT_ID,
                        id=run_id,
                        code=stage['Code']
                    ))
                except Exception as e:
                    print(f"Advancement failed: {e}")
            break  # Process only one stage at a time
```

### Step 3: Confirm Deployment Result

```python
from alibabacloud_dataworks_public20240518.models import ListPipelineRunItemsRequest

resp = client.list_pipeline_run_items(ListPipelineRunItemsRequest(
    project_id=PROJECT_ID,
    pipeline_run_id=run_id,
    page_number=1,
    page_size=50
))
for item in resp.body.paging_info.pipeline_run_items:
    m = item.to_map()
    print(f"{m['Name']}: {m.get('Status', 'N/A')}")
```

---

## Offline Process

The offline process uses `type` `Offline`. **Stages differ from the online process** (4 stages observed in practice):

```
Online Stages: BUILD_PACKAGE(Build) -> PROD_CHECK(Check) -> PROD(Deploy)
Offline Stages: OfflineCheck(Check) -> PROD_CHECK(Check) -> PROD(Offline) 
```

| Stage | Type | Description |
|-------|------|------|
| `OfflineCheck` | Check | Pre-offline check (runs automatically) |
| `PROD_CHECK` | Check | Production checker (requires advancement) |
| `PROD` | Offline | Remove from production scheduling (requires advancement) |


```python
resp = client.create_pipeline_run(CreatePipelineRunRequest(
    project_id=PROJECT_ID,
    type='Offline',
    object_ids=['node_ID_or_workflow_ID']
))
run_id = resp.body.id
# Subsequent polling and advancement is the same as the online process, but note the different stages
```

The polling and advancement logic is identical to the online process (see Step 2). The Agent does not need to differentiate between online/offline stage codes; simply advance dynamically based on the Stages returned by `GetPipelineRun`.

---

## Cancel Deployment

If a deployment is stuck or needs to be revoked:

```python
from alibabacloud_dataworks_public20240518.models import AbolishPipelineRunRequest

client.abolish_pipeline_run(AbolishPipelineRunRequest(
    project_id=PROJECT_ID,
    id=run_id
))
```

---

## Query Deployment History

```python
from alibabacloud_dataworks_public20240518.models import ListPipelineRunsRequest

resp = client.list_pipeline_runs(ListPipelineRunsRequest(
    project_id=PROJECT_ID,
    page_number=1,
    page_size=20
))
for run in resp.body.paging_info.pipeline_runs:
    m = run.to_map()
    stages = ' -> '.join(f"{s['Code']}({s['Status']})" for s in m.get('Stages', []))
    print(f"{m['Id']} [{m['Status']}] {stages}")
```

You can filter by `status` (e.g., only Running deployments) or by `object_id` (deployment history for a specific node).

---

## FAQ

### 1. Deployment stuck at PROD_CHECK or a Check stage

**Cause**: Check-type stages do not execute automatically; they require `ExecPipelineRunStage` to advance.

**Solution**: Ensure the polling logic includes advancement logic -- when an `Init` stage is encountered and all prior stages are `Success`, advance it automatically.

### 2. ExecPipelineRunStage returns success but stage status doesn't change

**Cause**: `ExecPipelineRunStage` is an async trigger; the response only indicates successful triggering, not stage completion.

**Solution**: Continue polling and wait for the stage status to change from `Init` to `Running` and then to `Success`.

### 3. Approval stage cannot be advanced via API

**Symptom**: Calling `ExecPipelineRunStage` returns an error, or the stage status remains unchanged.

**Cause**: In Standard Mode, certain stages (such as approval) require a user with specific permissions to operate manually in the DataWorks console.

**Solution**: The Agent should recognize this situation and inform the user: "The current deployment is awaiting approval. Please approve it on the Task Deployment page in the DataWorks console." After approval is completed, continue polling and advancing subsequent stages.

### 4. Deployment failed with error in Stage.Message

**Solution**: Read the `Message` field of the failed stage. Common causes include:
- Node code syntax errors
- Upstream dependency node not yet deployed
- Incorrect resource group configuration
- Insufficient permissions

### 5. Passed multiple object_ids but only the first one took effect

**Cause**: The official `CreatePipelineRun` documentation states "only the first entity in the array and its child entities will be successfully deployed."

**Solution**: To deploy multiple independent entities, create separate PipelineRuns. If the nodes are within the same workflow, simply deploy the workflow ID to include all child nodes.

### 6. Deployment is stuck and needs to be cancelled

**Solution**: Call `AbolishPipelineRun` to cancel. After cancellation, the Pipeline status changes to `Cancel`.

### 7. Deployment during the bulk instance generation window

**Note**: The period from 23:30 to 24:00 each day is the bulk instance generation window. Deployments during this period will not take effect until the **third day** after the operation, not the next day. Avoid deploying during this window.
