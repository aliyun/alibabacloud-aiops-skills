# RAM Policies for EMAS APM Remote Log (TLog) Operations

This document lists the RAM (Resource Access Management) permissions required for all API operations involved in the EMAS APM remote log (TLog) workflow.

## Required RAM Permissions

| API Operation | Required Permission | Description |
|---------------|--------------------|-------------|
| `GetTlogDeviceList` | `apm:GetTlogDeviceList` | Query the list of devices available for remote log retrieval |
| `GetTlogDeviceInfo` | `apm:GetTlogDeviceInfo` | Get detailed information about a specific device |
| `CreateTlogTask` | `apm:CreateTlogTask` | Create a remote log retrieval task |
| `GetTlogTaskInfo` | `apm:GetTlogTaskInfo` | Query the overall progress and status of a log retrieval task |
| `GetTlogTaskCollections` | `apm:GetTlogTaskCollections` | Query the collection status of each device in a task |
| `SearchTlog` | `apm:SearchTlog` | Search and query log details by device and time window |
| `GetTlogCollectList` | `apm:GetTlogCollectList` | Query the list of actively submitted log records |

## System Policies

Alibaba Cloud provides the following system policies for EMAS:

| Policy Name | Description |
|-------------|-------------|
| `AliyunEMASFullAccess` | Full access to all EMAS services, including APM |
| `AliyunEMASReadOnlyAccess` | Read-only access to EMAS services |

## Custom Policy Example

For least-privilege access, create a custom RAM policy:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "apm:GetTlogDeviceList",
        "apm:GetTlogDeviceInfo",
        "apm:CreateTlogTask",
        "apm:GetTlogTaskInfo",
        "apm:GetTlogTaskCollections",
        "apm:SearchTlog",
        "apm:GetTlogCollectList"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
