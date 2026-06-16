# Related Commands

This document lists all available script commands for Yunxiao Flow pipeline troubleshooting.

> **Token Note**: The `--token` parameter in all scripts below can be provided via the environment variable `YUNXIAO_ACCESS_TOKEN`. If the environment variable is set, the `--token` argument can be omitted.

## Python Scripts

### 1. Get Pipeline Run Information

**Script:** `scripts/yunxiao_flow_get_pipeline_runs.py`

**Purpose:** Get pipeline run status, stages, jobs, and step information.

**Usage:**
```bash
python3 scripts/yunxiao_flow_get_pipeline_runs.py \
  --org-id <org-id> \
  --pipeline-id <pipeline-id> \
  --pipeline-runid <pipeline-runid> \
  --token <token> \
  [--domain <domain>]
```

**Parameters:**
| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| --org-id | Yes | Organization ID | None |
| --pipeline-id | Yes | Pipeline ID | None |
| --pipeline-runid | Yes | Pipeline Run ID | None |
| --token | No | Personal access token (can also be provided via environment variable YUNXIAO_ACCESS_TOKEN) | None |
| --domain | No | API domain | openapi-rdc.aliyuncs.com |

**Output:** JSON containing pipeline run details, including status, stages, jobs, and steps

---

### 2. Get Job Step Logs

**Script:** `scripts/yunxiao_flow_get_job_step_log.py`

**Purpose:** Get detailed execution logs for a specific pipeline step.

**Usage:**
```bash
python3 scripts/yunxiao_flow_get_job_step_log.py \
  --org-id <org-id> \
  --pipeline-id <pipeline-id> \
  --pipeline-runid <pipeline-runid> \
  --job-id <job-id> \
  --step-index <step-index> \
  --token <token> \
  [--domain <domain>] \
  [--build-id <build-id>] \
  [--offset <offset>] \
  [--limit <limit>] \
  [--full-log]
```

**Parameters:**
| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| --org-id | Yes | Organization ID | None |
| --pipeline-id | Yes | Pipeline ID | None |
| --pipeline-runid | Yes | Pipeline Run ID | None |
| --job-id | Yes | Job ID | None |
| --step-index | Yes | Step Index | None |
| --token | No | Personal access token (can also be provided via environment variable YUNXIAO_ACCESS_TOKEN) | None |
| --domain | No | API domain | openapi-rdc.aliyuncs.com |
| --build-id | No | Build ID | None |
| --offset | No | Log start position | 1 |
| --limit | No | Log length limit | 100 |
| --full-log | No | Get complete log (flag) | False |

**Output:** JSON containing `last`, `logs`, and `more` fields with step execution logs

---

### 3. Get VM Deployment Order

**Script:** `scripts/yunxiao_flow_get_vm_deploy_order.py`

**Purpose:** Get VM deployment order details, including machine list.

**Usage:**
```bash
python3 scripts/yunxiao_flow_get_vm_deploy_order.py \
  --org-id <org-id> \
  --pipeline-id <pipeline-id> \
  --deploy-order-id <deploy-order-id> \
  --token <token> \
  [--domain <domain>]
```

**Parameters:**
| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| --org-id | Yes | Organization ID | None |
| --pipeline-id | Yes | Pipeline ID | None |
| --deploy-order-id | Yes | Deployment Order ID | None |
| --token | No | Personal access token (can also be provided via environment variable YUNXIAO_ACCESS_TOKEN) | None |
| --domain | No | API domain | openapi-rdc.aliyuncs.com |

**Output:** JSON containing deployment order details and machine list, including `machineSn`

---

### 4. Get VM Deployment Machine Log

**Script:** `scripts/yunxiao_flow_get_vm_deploy_machine_log.py`

**Purpose:** Get deployment logs for a specific VM machine.

**Usage:**
```bash
python3 scripts/yunxiao_flow_get_vm_deploy_machine_log.py \
  --org-id <org-id> \
  --pipeline-id <pipeline-id> \
  --pipeline-runid <pipeline-runid> \
  --deploy-order-id <deploy-order-id> \
  --machine-sn <machine-sn> \
  --token <token> \
  [--domain <domain>]
```

**Parameters:**
| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| --org-id | Yes | Organization ID | None |
| --pipeline-id | Yes | Pipeline ID | None |
| --pipeline-runid | Yes | Pipeline Run ID | None |
| --deploy-order-id | Yes | Deployment Order ID | None |
| --machine-sn | Yes | Machine Serial Number | None |
| --token | No | Personal access token (can also be provided via environment variable YUNXIAO_ACCESS_TOKEN) | None |
| --domain | No | API domain | openapi-rdc.aliyuncs.com |

**Output:** JSON containing machine deployment logs

### 5. Login to Web Terminal of Specified Container Environment

**Script:** `scripts/webTerminal.py`

**Purpose:** Login to the web terminal of a specified container environment to execute shell commands. **Note**: The script runs in a thread, and the link is only valid once. Do not close the script before troubleshooting is complete. <terminalUrl> must be wrapped in quotes.

**Usage:**
```bash
python3 scripts/webTerminal.py --terminalUrl "<terminalUrl>"
```
**Note**: After connecting to ECI using the script, subsequent commands need a newline character \n to trigger execution.

---

## API Endpoints Used

### Central Organization (24-char org-id)

**Base URL:** `https://openapi-rdc.aliyuncs.com`

**Endpoints:**
- Pipeline Run: `/oapi/v1/flow/organizations/{org-id}/pipelines/{pipeline-id}/pipelineRuns/{pipeline-runid}`
- Job Step Log: `/oapi/v1/flow/organizations/{org-id}/pipelines/{pipeline-id}/pipelineRuns/{pipeline-runid}/jobs/{job-id}/step/log`
- VM Deploy Order: `/oapi/v1/flow/organizations/{org-id}/pipelines/{pipeline-id}/deploy/{deploy-order-id}`
- VM Deploy Machine Log: `/oapi/v1/flow/organizations/{org-id}/pipelines/{pipeline-id}/deploy/{deploy-order-id}/machine/{machine-sn}/log`

### Regional Organization (32-char org-id)

**Base URL:** `https://{org-specific-domain}.devops.aliyuncs.com`

**Endpoints:**
- Get Pipeline Run: `/oapi/v1/flow/pipelines/{pipeline-id}/runs/{pipeline-runid}`
- Job Step Log: `/oapi/v1/flow/pipelines/{pipeline-id}/pipelineRuns/{pipeline-runid}/jobs/{job-id}/step/log`
- VM Deploy Order: `/oapi/v1/flow/pipelines/{pipeline-id}/deploy/{deploy-order-id}`
- VM Deploy Machine Log: `/oapi/v1/flow/pipelines/{pipeline-id}/deploy/{deploy-order-id}/machines/{machine-sn}/log`

---

## Authentication

All scripts use token-based authentication via the `x-yunxiao-token` HTTP header. Token can be provided in two ways:
1. Command-line argument `--token`
2. Environment variable `YUNXIAO_ACCESS_TOKEN` (recommended)

**Token Format:** `pt-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**How to Obtain:**
1. Log in to Yunxiao Console
2. Go to Personal Settings > Personal Access Tokens
3. Create a new token with required permissions
4. Copy the token (shown only once)

---

## Error Handling

All scripts handle common error scenarios:
- Invalid org-id format
- Invalid token
- Resource not found (404)
- Permission denied (403)
- Server error (500)

Error messages are printed to stderr with descriptive messages.
