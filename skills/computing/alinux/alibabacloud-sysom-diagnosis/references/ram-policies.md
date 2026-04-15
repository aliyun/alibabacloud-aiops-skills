# RAM Policy - SysOM 诊断技能

本文件列出 `alibabacloud-sysom-diagnosis` Skill 所需的 RAM 权限（用于远程深度诊断相关 OpenAPI）。

## 权限列表

### SysOM 诊断调用权限

| API 名称 | 权限 Action | 说明 |
|----------|-------------|------|
| `InitialSysom` | `sysom:InitialSysom` | precheck 与开通/权限校验 |
| `InvokeDiagnosis` | `sysom:InvokeDiagnosis` | 发起诊断任务 |
| `GetDiagnosisResult` | `sysom:GetDiagnosisResult` | 查询诊断任务结果 |

## 最小权限策略模板

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sysom:InitialSysom",
        "sysom:InvokeDiagnosis",
        "sysom:GetDiagnosisResult"
      ],
      "Resource": "*"
    }
  ]
}
```

## 系统策略推荐

| 策略名称 | 说明 |
|----------|------|
| AliyunSysomFullAccess | SysOM完全访问权限 |
