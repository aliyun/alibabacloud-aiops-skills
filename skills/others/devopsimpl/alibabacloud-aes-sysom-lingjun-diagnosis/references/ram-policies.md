# RAM Policies: alibabacloud-aes-sysom-lingjun-diagnosis

This document lists all APIs and their corresponding RAM permissions used by the SysOM lingjun deep diagnosis skill.

> Node enrollment / Agent installation is **not** part of this skill, so `sysom:InstallAgent`, `sysom:ListInstanceStatus` and `sysom:UninstallAgent` are intentionally **not** requested.

---

## SysOM Permissions

| API | RAM Action | Description |
|-----|-----------|-------------|
| InitialSysom | `sysom:InitialSysom` | Initialize SysOM role authorization |
| CheckInstanceSupport | `sysom:CheckInstanceSupport` | Check if the lingjun node supports SysOM diagnosis |
| InvokeDiagnosis | `sysom:InvokeDiagnosis` | Invoke intelligent diagnosis (channel `eflo`) |
| GetDiagnosisResult | `sysom:GetDiagnosisResult` | Get diagnosis result |
| ListAlertItems | `sysom:ListAlertItems` | Get available alert items list |
| CreateAlertStrategy | `sysom:CreateAlertStrategy` | Create alert strategy |
| CreateAlertDestination | `sysom:CreateAlertDestination` | Create alert destination (SDK call) |
| UpdateAlertDestination | `sysom:UpdateAlertDestination` | Update alert destination (SDK call) |
| DeleteAlertDestination | `sysom:DeleteAlertDestination` | Delete alert destination (SDK call) |
| GetAlertDestination | `sysom:GetAlertDestination` | Get alert destination details (SDK call) |
| ListAlertDestinations | `sysom:ListAlertDestinations` | List alert destinations (SDK call) |

## ECS Permissions

> The ECS Cloud Assistant status API is used as a prerequisite check for lingjun nodes (the lingjun node ID is passed as the instance ID).

| API | RAM Action | Description |
|-----|-----------|-------------|
| DescribeCloudAssistantStatus | `ecs:DescribeCloudAssistantStatus` | Check Cloud Assistant online status on the lingjun node |

## Minimum Permission Policy Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sysom:InitialSysom",
        "sysom:CheckInstanceSupport",
        "sysom:InvokeDiagnosis",
        "sysom:GetDiagnosisResult",
        "sysom:ListAlertItems",
        "sysom:CreateAlertStrategy",
        "sysom:CreateAlertDestination",
        "sysom:UpdateAlertDestination",
        "sysom:DeleteAlertDestination",
        "sysom:GetAlertDestination",
        "sysom:ListAlertDestinations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeCloudAssistantStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Tiers

| Phase | Required Permissions | Description |
|-------|---------------------|-------------|
| Diagnosis | `sysom:InitialSysom`, `sysom:CheckInstanceSupport`, `sysom:InvokeDiagnosis`, `sysom:GetDiagnosisResult`, `ecs:DescribeCloudAssistantStatus` | Minimum permissions for deep diagnosis |
| Alert | `sysom:ListAlertItems`, `sysom:CreateAlertStrategy` | Configure anomaly event alerts |
| Alert Destination | `sysom:CreateAlertDestination`, `sysom:UpdateAlertDestination`, `sysom:DeleteAlertDestination`, `sysom:GetAlertDestination`, `sysom:ListAlertDestinations` | Manage alert destinations (SDK call) |
