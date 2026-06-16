# Yunxiao Flow Troubleshooting Guide

## Organization Type Detection

| Organization Type | Organization ID Length | Domain Example |
|-------------------|----------------------|----------------|
| Central Organization | 24 characters | openapi-rdc.aliyuncs.com |
| Regional Organization | 32 characters | xxx-xxx.devops.aliyuncs.com |

## Knowledge Base Selection Guide

When troubleshooting, read the corresponding reference file based on the failure scenario:

| Failure Scenario | Reference File |
|-----------------|----------------|
| Image build failure | `flow_build_docker.md` |
| Docker deployment failure | `flow_deploy_docker.md` |
| Kubernetes deployment failure | `flow_deploy_kubectl.md` |
| VM deployment failure | `flow_deploy_vm.md` |
| Function Compute deployment failure | `flow_deploy_fc.md` |
| Python unit test failure | `flow_test_python.md` |
| Java/Maven unit test failure | `flow_test_maven.md` |
| Node.js unit test failure | `flow_test_nodeJS.md` |
| Golang unit test failure | `flow_test_golang.md` |
| PHP unit test failure | `flow_test_php.md` |
| Pipeline variable issues | `flow_variables.md` |
| Java build/deploy failure | `flow_build_java.md` |
| Node build/deploy failure | `flow_build_nodeJs.md` |
| Python build/deploy failure | `flow_build_python.md` |
| Custom environment build issues | `flow_customEnvironmentBuild.md` |
| Code clone issues | `flow_git_clone.md` |
| Runtime environment and workspace issues | `flow_workspace_runtime.md` |


**Must Read**:
- `yunxiao_base.md` - Yunxiao fundamentals
- `yunxiao_flow_get_pipeline_runs.md` - pipeline_runs output field description

## Build Cluster Identification

Obtain from the "Request Runtime Environment" step logs (do NOT use `params.buildNodeGroup`):

| Type | Log Pattern |
|------|-------------|
| Default Build Cluster | `[Build Cluster Info] >> Cluster Name : Yunxiao China Hong Kong Build Cluster` |
| VPC Build Cluster | `[Build Cluster Info] >> Cluster Name : Hangzhou VPC Build Cluster` |
| Private Build Cluster | `[Runner Group Info]: >> RunnerGroupName : xxxxx` |

## Analysis Key Points

Before analysis, confirm:
1. Build cluster used by the current job (obtained from "Request Runtime Environment" logs)
2. Whether code was cloned, and the cloned branch and commit

## Output Format

```
## Pipeline Issue Analysis Report

### Basic Information
- Pipeline ID, Run ID, Status
- Failed Stage and Job names
- Build cluster name

### Failure Location
- Step name, Step Index
- Executed command/configuration

### Error Log Summary
- Key error messages
- Error location

### Root Cause Analysis
- Problem cause

### Solution
- Configuration items to modify
- Parameters to adjust
```
