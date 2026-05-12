# RAM Policies: SASE PA Network Diagnosis

## Required Permissions

| Action | Resource | Description |
|--------|----------|-------------|
| `csas:ListUserDevices` | `*` | Query user device list (to obtain DevTag) |
| `csas:CreatePADiagnosisTask` | `*` | Create Private Access diagnosis task |
| `csas:GetPADiagnosisTask` | `*` | Query Private Access diagnosis task details |

## RAM Policy Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "csas:ListUserDevices",
        "csas:CreatePADiagnosisTask",
        "csas:GetPADiagnosisTask"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- Product RAM code: `csas` (Secure Access Service Edge)
- Reference: [RAM Policy Elements Reference](https://help.aliyun.com/zh/sase/developer-reference/api-csas-2023-01-20-ram)
- If the API returns `Forbidden` or `NoPermission` error, verify that the current account/RAM user has been granted the above permissions
- Follow the principle of least privilege: only grant diagnosis-related permissions
