# RAM Policies (sysom-inspection)

本文档说明 `alibabacloud-alinux-sysom-inspection` 在调用 SysOM OpenAPI 时所需的最小 RAM 权限。

## Required SysOM Actions

| API | RAM Action | Purpose |
|---|---|---|
| `InitialSysom` | `sysom:InitialSysom` | 校验开通状态与权限，必要时执行开通流程 |
| `InstallAgentWithType` | `sysom:InstallAgentWithType` | 为目标 ECS 安装 SysOM Agent |
| `CreateInstanceInspection` | `sysom:CreateInstanceInspection` | 发起实例巡检任务 |
| `GetInspectionReport` | `sysom:GetInspectionReport` | 查询巡检报告 |
| `InvokeDiagnosis` | `sysom:InvokeDiagnosis` | 发起内存专项诊断（memgraph） |
| `GetDiagnosisResult` | `sysom:GetDiagnosisResult` | 轮询诊断结果 |

## Example Policy Statement

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
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

- 若使用子账号执行巡检/诊断，需确保该账号具备以上全部 Action。
- 若提示服务未开通或角色未就绪，请先完成 SysOM 开通流程后重试。
