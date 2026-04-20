# RAM Policies: alibabacloud-aes-sysom-os-diagnosis

This document lists all APIs and their corresponding RAM permissions used by the SysOM deep diagnosis skill.

---

## SysOM Permissions

| API | RAM Action | Description |
|-----|-----------|-------------|
| InitialSysom | `sysom:InitialSysom` | Initialize SysOM role authorization |
| CheckInstanceSupport | `sysom:CheckInstanceSupport` | Check if instance supports SysOM diagnosis |
| InvokeDiagnosis | `sysom:InvokeDiagnosis` | Invoke intelligent diagnosis |
| GetDiagnosisResult | `sysom:GetDiagnosisResult` | Get diagnosis result |
| InstallAgent | `sysom:InstallAgent` | Enroll instance (install Agent) |
| InstallAgentForCluster | `sysom:InstallAgentForCluster` | Enroll ACK cluster |
| ListInstanceStatus | `sysom:ListInstanceStatus` | Query instance enrollment status |
| ListClusters | `sysom:ListClusters` | Query cluster enrollment status |
| ListAlertItems | `sysom:ListAlertItems` | Get available alert items list |
| CreateAlertStrategy | `sysom:CreateAlertStrategy` | Create alert strategy |
| CreateAlertDestination | `sysom:CreateAlertDestination` | Create alert destination (SDK call) |
| UpdateAlertDestination | `sysom:UpdateAlertDestination` | Update alert destination (SDK call) |
| DeleteAlertDestination | `sysom:DeleteAlertDestination` | Delete alert destination (SDK call) |
| GetAlertDestination | `sysom:GetAlertDestination` | Get alert destination details (SDK call) |
| ListAlertDestinations | `sysom:ListAlertDestinations` | List alert destinations (SDK call) |

## ECS Permissions

| API | RAM Action | Description |
|-----|-----------|-------------|
| DescribeCloudAssistantStatus | `ecs:DescribeCloudAssistantStatus` | Check Cloud Assistant online status |

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
        "sysom:InstallAgent",
        "sysom:InstallAgentForCluster",
        "sysom:ListInstanceStatus",
        "sysom:ListClusters",
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
| Enrollment | `sysom:InstallAgent` or `sysom:InstallAgentForCluster`, `sysom:ListInstanceStatus`, `sysom:ListClusters` | Enroll instances or clusters |
| Alert | `sysom:ListAlertItems`, `sysom:CreateAlertStrategy` | Configure anomaly event alerts |
| Alert Destination | `sysom:CreateAlertDestination`, `sysom:UpdateAlertDestination`, `sysom:DeleteAlertDestination`, `sysom:GetAlertDestination`, `sysom:ListAlertDestinations` | Manage alert destinations (SDK call) |
