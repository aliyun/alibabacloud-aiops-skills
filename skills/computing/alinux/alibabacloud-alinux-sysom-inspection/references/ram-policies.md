# RAM Policies (sysom-inspection)

This document describes the minimum RAM permissions required by `alibabacloud-alinux-sysom-inspection` when calling SysOM OpenAPI.

## Required SysOM Actions

| API | RAM Action | Purpose |
|---|---|---|
| `ListAllInstances` | `sysom:ListAllInstances` | List instances by region and management status (paginated) for inspection target selection |
| `InitialSysom` | `sysom:InitialSysom` | Validate activation status and permissions; optionally perform activation |
| `InstallAgentWithType` | `sysom:InstallAgentWithType` | Install SysOM Agent on the target ECS instance |
| `CreateInstanceInspection` | `sysom:CreateInstanceInspection` | Start an instance inspection task |
| `GetInspectionReport` | `sysom:GetInspectionReport` | Query inspection report details |
| `InvokeDiagnosis` | `sysom:InvokeDiagnosis` | Start memory-focused diagnosis (`memgraph`) |
| `GetDiagnosisResult` | `sysom:GetDiagnosisResult` | Poll diagnosis execution result |

## Example Policy Statement

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sysom:ListAllInstances",
        "sysom:InitialSysom",
        "sysom:InstallAgentWithType",
        "sysom:CreateInstanceInspection",
        "sysom:GetInspectionReport",
        "sysom:InvokeDiagnosis",
        "sysom:GetDiagnosisResult"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- If you use a RAM sub-account for inspection/diagnosis, ensure it has all actions listed above.
- If the API indicates service is not activated or role readiness is missing, complete SysOM activation first and retry.
