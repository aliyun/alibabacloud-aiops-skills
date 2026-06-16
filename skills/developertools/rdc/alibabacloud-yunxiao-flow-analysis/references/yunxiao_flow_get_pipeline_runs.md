# yunxiao_flow_get_pipeline_runs.py Output Field Description

## Top-Level JSON Fields

```json
{
  "org_id": "Organization ID",
  "pipelineId": "Pipeline ID",
  "pipelineRunId": "Pipeline Run ID",
  "status": "Status of a pipeline run",
  "stageGroup": "Brief version of build stages",
  "groups": "Build stage names",
  "pipelineType": "Pipeline type",
  "stages": "Stage array, each stage described below"
}
```

### Field Description

| Field | Type | Description |
|-------|------|-------------|
| org_id | string | Organization ID |
| pipelineId | integer | Pipeline ID |
| pipelineRunId | integer | Pipeline Run ID (run number) |
| status | string | Pipeline run status: SUCCESS/FAIL/RUNNING/INIT |
| stageGroup | array | Stage grouping structure, e.g., `[["Group0-Stage0"], ["Group1-Stage0", "Group1-Stage1"]]` |
| groups | array | Pipeline group information, containing name and id |
| pipelineType | array/null | Pipeline type: `null` or `default`: Graphical pipeline; `PIPELINEASCODE`: YAML pipeline (Pipeline as Code) |
| stages | array | Detailed information array of all stages |

---

## Stage

```json
{
  "name": "Stage name",
  "status": "Stage execution status",
  "id": "Stage ID",
  "stage_index": "GroupX-StageX",
  "jobs": "Job array"
}
```

### Stage Field Description

| Field | Type | Description |
|-------|------|-------------|
| name | string | Stage name, e.g., "Build Image", "Command", "New Stage" |
| status | string | Execution status: `SUCCESS`: Execution succeeded; `FAIL`: Execution failed; `INIT`: Not executed; `RUNNING`: Currently executing |
| id | integer | Stage ID |
| stage_index | string | Stage index, e.g., `Group0-Stage0` |
| jobs | array | All jobs contained in this stage |

---

## Job

```json
{
  "id": "Job ID",
  "name": "Job name",
  "status": "Job execution status",
  "startTime": "Job start time (millisecond timestamp)",
  "endTime": "Job end time (millisecond timestamp)",
  "steps": "Step array",
  "params": "Job parameter configuration",
  "result": "Job execution result"
}
```

### Job Field Description

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Job ID (needed when calling get_job_step_log) |
| name | string | Job name, e.g., "Build and Push Image to ACR Personal Edition", "Execute Command 1" |
| status | string | Execution status: SUCCESS/FAIL/INIT/RUNNING |
| startTime | integer | Start time (millisecond timestamp) |
| endTime | integer | End time (millisecond timestamp) |
| steps | array | All steps contained in this job |
| params | object | Job parameter configuration (see below) |
| result | object | Job execution result and output variables |

### params Field Description

| Field | Type | Description |
|-------|------|-------------|
| sources | array | Pipeline source configuration (code repositories, artifact sources, Jenkins, Flow pipelines) |
| caches | array | Pipeline cache directory configuration, e.g., `["/root/.m2", "/root/.npm"]` |
| SYSTEM_GLOBAL_VARIABLES_KEYS | array | User-defined environment variable key list |
| buildEnvironment | string | Build environment type: `specify_container`: Specified container environment; `container`: Default container environment; `vm`: Default VM environment |
| specifyContainerImageId | string | Image ID used by the specified container environment |
| runnerCacheMode | string | Cache mode: `local`: Local cache; `cloud`: Yunxiao managed cache |
| EXECUTOR_NAME | string | Build executor name |
| BUILD_EXECUTOR | string | Pipeline trigger user |
| BUILD_MESSAGE | string | Pipeline trigger message |
| CI_SOURCE_NAME | string | Code source name |
| CI_COMMIT_SHA | string | Commit SHA |
| CI_COMMIT_REF_NAME | string | Branch name |
| debugPolicy | string | Job debug strategy. "none" means debug is not enabled. |
| debugRetentionMinutes | integer | Build environment retention time (from job start, in minutes) |
| enableDockerDaemon | bool | Enable Docker Daemon (when enabled, custom docker build commands can be executed.) |

### result Field Description

| Field | Type | Description |
|-------|------|-------------|
| successful | boolean | Whether execution was successful |
| data | object | Output variable set |
| code | integer | Error code (on failure) |
| message | string | Error message (on failure) |
| requestId | string | Request ID |

---

## Step

```json
{
  "nodeName": "Step name",
  "stepIndex": "Step index",
  "status": "Step execution status",
  "stepType": "Step type",
  "command": "Executed command (for command-type steps)"
}
```

### Step Field Description

| Field | Type | Description |
|-------|------|-------------|
| nodeName | string | Step name, e.g., "Request Runtime Environment (0s)", "Clone Code (2s)", "Execute Command (1s)" |
| stepIndex | integer | Step index (needed when calling get_job_step_log) |
| status | string | Execution status: success/fail/ready/running |
| stepType | string | Step type, e.g., `Command_production`, `DockerBuildPushACR_production` |
| command | string | Executed command content (command-type steps only) |
| stepIdentifier | string | Step unique identifier |

### Common Step Types

| Step Name | Description | Log Characteristics |
|-----------|-------------|---------------------|
| Request Runtime Environment | Request build machine | Contains build machine info, image info |
| Clean Workspace | Pre-build cleanup | Cleanup of temp files, old code |
| Clone Code | Download code source | Contains git clone info |
| Pipeline Cache | Restore cache | Shows restored cache directories |
| Execute Command | Execute user scripts | Contains user commands and output |
| Image Build | Build Docker image | Contains docker build output |
| Cache Upload | Upload cache | Shows uploaded cache files |
| Batch Set Variables | Set environment variables | Shows set variables |

---

## Quick Failure Location

```python
# Pseudocode example
def find_failure(data):
    # 1. Check overall pipeline status
    if data['status'] == 'SUCCESS':
        return "Pipeline succeeded"
    
    # 2. Traverse stages to find failed stage
    for stage in data['stages']:
        if stage['status'] == 'FAIL':
            # 3. Find failed job in failed stage
            for job in stage['jobs']:
                if job['status'] == 'FAIL':
                    # 4. Find failed step in failed job
                    for step in job['steps']:
                        if step['status'] == 'fail':
                            return {
                                'stage': stage['name'],
                                'job': job['name'],
                                'job_id': job['id'],
                                'step': step['nodeName'],
                                'step_index': step['stepIndex']
                            }
    return "Failure location not found"
```

---

## Timestamp Conversion

```python
# Convert millisecond timestamp to readable time
from datetime import datetime

timestamp_ms = 1774316754000
readable_time = datetime.fromtimestamp(timestamp_ms / 1000)
# Output: 2026-03-24 09:45:54
```
