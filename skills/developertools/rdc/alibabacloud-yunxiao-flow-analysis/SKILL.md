---
name: alibabacloud-yunxiao-flow-analysis
description: |
  Yunxiao Flow Pipeline Troubleshooting and Solutions. Used to diagnose pipeline execution failures and provide fix recommendations.
  Trigger scenarios: Pipeline build errors, pipeline run failures, host deployment failures, k8s deployment failures, java build errors, python build errors, node build errors, unit test failures, image build failures, docker deployment failures, pipeline variable substitution errors, pipeline variables replaced with empty values.
---

# Yunxiao Flow Pipeline Troubleshooting

## Scenario Description

This skill provides comprehensive troubleshooting and analysis capabilities for Yunxiao Flow pipeline failures. It helps diagnose issues across various pipeline stages, including:

**Covered Pipeline Types:**
- Image Build (Docker)
- Docker Deployment
- Kubernetes Deployment
- VM Deployment
- Function Compute Deployment
- Unit Testing (Python, Maven/Java, Node.js, Golang, PHP)

**Architecture:** Python Scripts → Yunxiao Flow API → Pipeline Execution Logs → Failure Analysis → Solution Recommendations.

## Installation

The websocket-client library is required.

## Environment Variables

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| YUNXIAO_ACCESS_TOKEN | Yunxiao Personal Access Token (format: `pt-xxx`) | Yes |

## Authentication

Before executing any commands, ensure you have a valid Yunxiao Personal Access Token configured via environment variable.

```bash
export YUNXIAO_ACCESS_TOKEN="pt-xxxxxxxxxxxxx"
```

**Security Design:**
- Token is read **exclusively** from environment variable `YUNXIAO_ACCESS_TOKEN` — CLI arguments are not supported to prevent exposure in process listings (`ps`/`top`), shell history, and `/proc/*/cmdline`
- Token format is validated (`pt-` prefix) before any network transmission to prevent accidental credential leakage
- All API communication uses HTTPS with TLS encryption
- Scripts have built-in token masking in output, showing only the first 6 and last 6 characters

**Security Rules:**
- **NEVER** read, echo, or print the full token value
- **NEVER** ask the user to input the token directly in the conversation
- **NEVER** hardcode token values in scripts
- **NEVER** pass token via command-line arguments (use environment variable only)
- Tokens should be obtained from Yunxiao Console > Personal Settings > Personal Access Tokens

## RAM Permissions

This skill uses token-based authentication for Yunxiao Flow API. Required permissions:

- **Flow Pipeline all modules:** Read-only access

For detailed permission requirements and failure handling, see [references/ram-policies.md](references/ram-policies.md).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Verify that the Yunxiao Personal Access Token has the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **Important: Parameter Confirmation** — Before executing any command or API call,
> all customizable parameters must be confirmed with the user. Never assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| org-id | Required | Organization ID (24 characters for central org, 32 characters for regional org) | None |
| pipeline-id | Required | Pipeline ID | None |
| pipeline-runid | Required | Pipeline Run ID | None |
| YUNXIAO_ACCESS_TOKEN | Required (environment variable) | Personal Access Token (format: pt-xxx), set via `export YUNXIAO_ACCESS_TOKEN="pt-xxx"` | None |
| domain | Optional | API domain (default: openapi-rdc.aliyuncs.com) | openapi-rdc.aliyuncs.com |

## Core Workflow

### Step 1: Get Pipeline Run Status

> **Note**: All scripts read the token from environment variable `YUNXIAO_ACCESS_TOKEN`. Ensure it is set before running any command.

```bash
python3 scripts/yunxiao_flow_get_pipeline_runs.py \
  --org-id <org-id> --pipeline-id <pipeline-id> \
  --pipeline-runid <pipeline-runid> --domain <domain>
```

**Analyze the returned JSON:**
1. Check the `status` field (SUCCESS/FAIL/RUNNING/INIT)
2. Traverse `stages` to find the failed stage
3. Find the failed job within the failed stage
4. Find the failed step within the failed job

### Step 2: Get Failed Step Logs

```bash
python3 scripts/yunxiao_flow_get_job_step_log.py \
  --org-id <org-id> --pipeline-id <pipeline-id> --pipeline-runid <pipeline-runid> \
  --job-id <job-id> --step-index <step-index> --build-id <build-id> \
  --domain <domain> --full-log
```

### Step 3: Get VM Deployment Logs (if applicable)

```bash
python3 scripts/yunxiao_flow_get_vm_deploy_machine_log.py \
  --org-id <org-id> --pipeline-id <pipeline-id> --pipeline-runid <pipeline-runid> \
  --deploy-order-id <deploy-order-id> --machine-sn <machine-sn> \
  --domain <domain>
```

### Step 4: Consult Reference Documents for Analysis

Read the corresponding reference documents based on the failure scenario. For detailed guidance, see `references/troubleshooting-guide.md`.

**Must read:** `yunxiao_base.md`, `yunxiao_flow_get_pipeline_runs.md`

### Step 5: Analyze and Provide Solutions

After confirming the build cluster and code clone information, output:
1. Pipeline basic information, which must include: build cluster (build cluster name must NOT be obtained from `params.buildNodeGroup`. It **MUST** be obtained from the "Request Runtime Environment" step logs.), build environment, trigger time, status, failed job, failed step, downloaded code source, job workspace (can be viewed from the `PROJECT_DIR` in the Pipeline Cache step)
2. Failed step information
3. Error log summary
4. Root cause analysis
5. Solution recommendations (configuration changes, parameter adjustments, operational steps)

## Success Verification Method

For verification steps, see [references/verification-method.md](references/verification-method.md)

## Cleanup

No resource cleanup required. This skill only performs read operations for analysis purposes.

## Best Practices

1. **Always validate org-id length** to determine organization type (24 chars = central org, 32 chars = regional org)
2. **Check build cluster type from "Request Runtime Environment" step logs**, not from `params.buildNodeGroup`
3. **Read base reference documents first**: Read `yunxiao_base.md` and `yunxiao_flow_get_pipeline_runs.md` before scenario-specific files
4. **Extract build cluster information from log patterns**:
   - Default: `[Build Cluster Info] >> Cluster Name : Yunxiao China Hong Kong Build Cluster`
   - VPC: `[Build Cluster Info] >> Cluster Name : Hangzhou VPC Build Cluster`
   - Private: `[Runner Group Info]: >> RunnerGroupName : xxxxx`
5. **Verify code clone information**: Check branch name and commit SHA before analysis
6. **Match failure scenarios** to corresponding reference documents in the troubleshooting guide table

## Reference Document Links

| Reference Document | Description |
|-------------------|-------------|
| [troubleshooting-guide.md](references/troubleshooting-guide.md) | Complete troubleshooting guide (org types, knowledge base selection, build cluster identification) |
| [yunxiao_base.md](references/yunxiao_base.md) | Yunxiao fundamentals (org types, API versions, PAT, pipeline concepts) |
| [yunxiao_flow_get_pipeline_runs.md](references/yunxiao_flow_get_pipeline_runs.md) | Pipeline runs API field documentation |
| [flow_git_clone.md](references/flow_git_clone.md) | Code clone error troubleshooting |
| [flow_build_docker.md](references/flow_build_docker.md) | Docker image build troubleshooting |
| [flow_build_nodeJs.md](references/flow_build_nodeJs.md) | Node.js build troubleshooting |
| [flow_build_python.md](references/flow_build_python.md) | Python build troubleshooting |
| [flow_customEnvironmentBuild.md](references/flow_customEnvironmentBuild.md) | Custom environment build error troubleshooting |
| [flow_build_java.md](references/flow_build_java.md) | Java build troubleshooting |
| [flow_deploy_docker.md](references/flow_deploy_docker.md) | Docker deployment troubleshooting |
| [flow_deploy_kubectl.md](references/flow_deploy_kubectl.md) | Kubernetes deployment troubleshooting |
| [flow_deploy_vm.md](references/flow_deploy_vm.md) | VM deployment troubleshooting |
| [flow_deploy_fc.md](references/flow_deploy_fc.md) | Function Compute deployment troubleshooting |
| [flow_test_python.md](references/flow_test_python.md) | Python unit test troubleshooting |
| [flow_test_maven.md](references/flow_test_maven.md) | Maven/Java unit test troubleshooting |
| [flow_test_nodeJS.md](references/flow_test_nodeJS.md) | Node.js unit test troubleshooting |
| [flow_test_golang.md](references/flow_test_golang.md) | Golang unit test troubleshooting |
| [flow_test_php.md](references/flow_test_php.md) | PHP unit test troubleshooting |
| [flow_variables.md](references/flow_variables.md) | Pipeline variable configuration |
| [flow_workspace_runtime.md](references/flow_workspace_runtime.md) | Workspace and runtime environment troubleshooting |
| [ram-policies.md](references/ram-policies.md) | RAM permission requirements and authentication guide |
| [related-commands.md](references/related-commands.md) | Complete list of all script commands |

## Tools

| Script | Function |
|--------|----------|
| `yunxiao_flow_get_pipeline_runs.py` | Get pipeline run information |
| `yunxiao_flow_get_job_step_log.py` | Get step execution logs |
| `yunxiao_flow_get_vm_deploy_order.py` | Get VM deployment order details |
| `yunxiao_flow_get_vm_deploy_machine_log.py` | Get VM deployment machine logs |
| `webTerminal.py` | Connect to container environment debug terminal |
