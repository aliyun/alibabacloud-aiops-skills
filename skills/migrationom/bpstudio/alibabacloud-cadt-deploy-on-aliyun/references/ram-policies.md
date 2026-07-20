# RAM Policies: alibabacloud-cadt-deploy-on-aliyun

This document lists all Alibaba Cloud APIs and their RAM permission declarations involved during Skill execution.

---

## Permission Summary

| Service | Action | Purpose | Phase |
|---------|--------|---------|-------|
| STS | `sts:GetCallerIdentity` | Resolve current account UID (identity) | step-1 Session init |
| BPStudio | `bpstudio:GetToken` | Obtain STS temporary credentials for OSS upload | step-2 Upload |
| BPStudio | `bpstudio:ExecuteOperation` | Execute sync Operations (EcsGetDesc, etc.) | step-1/3 |
| BPStudio | `bpstudio:ExecuteOperationAsync` | Execute async Operations (InstallApplication, etc.) | step-2/3 |
| BPStudio | `bpstudio:GetExecuteOperationResult` | Poll async Operation results | step-2/3 |
| OSS | `oss:PutObject` | Upload build artifacts to OSS | step-2 Upload |
| OSS | `oss:GetObject` | Verify uploaded object stat info | step-2 Verification |
| ECS | `ecs:RunCommand` | Execute commands on ECS instances (forensics/diagnostics) | step-3 Root cause analysis |
| ECS | `ecs:DescribeInvocationResults` | Query command execution results | step-3 Root cause analysis |
| ECS | `ecs:SendFile` | Send files to ECS | step-3 (optional) |
| ECS | `ecs:DescribeInstances` | Query ECS instance info (IP, status, OS) | step-1/3 |

---

## Least-Privilege RAM Policy (JSON)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bpstudio:GetToken",
        "bpstudio:ExecuteOperation",
        "bpstudio:ExecuteOperationAsync",
        "bpstudio:GetExecuteOperationResult"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:PutObject",
        "oss:GetObject"
      ],
      "Resource": "acs:oss:*:*:China-aliyun-China-hangzhou-bpstudio-*/*",
      "Condition": {}
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunCommand",
        "ecs:DescribeInvocationResults",
        "ecs:SendFile",
        "ecs:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note**: The OSS Resource bucket name starts with `bpstudio-`; the actual value is returned by `bpstudio:GetToken`. Adjust the wildcard pattern according to your environment.

---

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Per-Step Permission Details

### step-1: Session Init

| API | Permission | Description |
|-----|------------|-------------|
| `aliyun sts get-caller-identity` | `sts:GetCallerIdentity` | Get account UID for OSS Object Key prefix |
| `aliyun ecs describe-instances` (EcsGetDesc) | `ecs:DescribeInstances` | Query ECS instance info (IP, status) |

### step-2: Compile, Package & Upload

| API | Permission | Description |
|-----|------------|-------------|
| `aliyun bpstudio get-token` | `bpstudio:GetToken` | Obtain STS credentials |
| `aliyun ossutil cp` | `oss:PutObject` | Upload artifact to OSS |
| `aliyun ossutil stat` | `oss:GetObject` | Verify uploaded file size |
| `aliyun bpstudio execute-operation` (EcsGetDesc, EcsSendFile) | `bpstudio:ExecuteOperation` | Execute sync operations |
| `aliyun bpstudio get-execute-operation-result` | `bpstudio:GetExecuteOperationResult` | Poll operation results |

### step-3: Deploy + Failure Recovery

| API | Permission | Description |
|-----|------------|-------------|
| `aliyun bpstudio execute-operation-async` (InstallApplication) | `bpstudio:ExecuteOperationAsync` | Async deployment |
| `aliyun bpstudio get-execute-operation-result` | `bpstudio:GetExecuteOperationResult` | Poll deployment results |
| `aliyun ecs describe-instances` (EcsGetDescList) | `ecs:DescribeInstances` | Batch query ECS instances |
| `aliyun ecs run-command` (EcsRunCommand) | `ecs:RunCommand` | Remote diagnostics & forensics |
| `aliyun ecs describe-invocation-results` | `ecs:DescribeInvocationResults` | Query command output |

