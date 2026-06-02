# RAM Permission Policies

This document lists the full RAM permissions required by the `alibabacloud-aes-sysom-pai-diagnosis` skill.

When any command or API call fails due to permission errors, use the `ram-permission-diagnose` skill to guide the user through requesting these permissions.

---

## Required Permissions Overview

| Service | Action | Used By Step |
|---------|--------|--------------|
| SysOM | `sysom:InitialSysom` | Step 5 — SysOM role initialization |
| SysOM | `sysom:InvokeDiagnosis` | Step 7 — Invoke diagnosis |
| SysOM | `sysom:GetDiagnosisResult` | Step 7 — Poll diagnosis result |
| PAI EAS | `eas:ListServices` | Step 6A — Verify EAS service ID exists (EAS only) |
| PAI DLC | `pai-dlc:GetJob` | Step 6B — Verify DLC job exists and check ResourceType (DLC only) |

---

## Recommended RAM Policy

Attach the following custom policy to the user / role that runs this skill:

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
    },
    {
      "Effect": "Allow",
      "Action": [
        "eas:ListServices"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "pai-dlc:GetJob"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Managed Policy Alternatives

If you prefer Alibaba Cloud managed policies (broader scope, simpler to attach):

| Managed Policy | Coverage |
|----------------|----------|
| `AliyunSysOMFullAccess` | All SysOM operations |
| `AliyunSysOMReadOnlyAccess` | SysOM read-only (sufficient for diagnosis polling, but NOT for `InitialSysom`) |
| `AliyunPAIFullAccess` | All PAI operations including EAS `ListServices` |
| `AliyunEASFullAccess` | EAS operations only |
| `AliyunEASReadOnlyAccess` | EAS read-only (sufficient for `ListServices`) |

> **Recommended minimal combination for this skill**: `AliyunSysOMFullAccess` + `AliyunEASReadOnlyAccess`.

---

## Permission Failure Diagnosis

When you encounter a `Forbidden.RAM` / `NoPermission` error:

1. Identify the failing API from the error message (e.g., `eas:ListServices`)
2. Check whether the corresponding action is included in the policy attached to the current identity
3. If not, request the user to attach the missing permission via the [RAM Console](https://ram.console.aliyun.com/policies)
4. Use the `ram-permission-diagnose` skill for guided remediation
