# RAM Policies for SysOM Diagnosis Skill

This file lists RAM permissions required by `alibabacloud-sysom-diagnosis` for remote deep-diagnosis OpenAPI calls.

## Permission List

### SysOM Diagnosis Invocation Permissions

| API Name | RAM Action | Description |
|----------|-------------|------|
| `InitialSysom` | `sysom:InitialSysom` | precheck and activation/permission validation |
| `InvokeDiagnosis` | `sysom:InvokeDiagnosis` | start diagnosis task |
| `GetDiagnosisResult` | `sysom:GetDiagnosisResult` | query diagnosis task result |

## Minimum Policy Template

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

## Recommended System Policy

| Policy Name | Description |
|----------|------|
| `AliyunSysomFullAccess` | Full access to SysOM |
