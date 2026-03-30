# RAM Hints for ram-permission-diagnose Skill
<!-- ram-hints-version: 1 -->

## Action Permission Mapping

### Diagnostic Operations (read-only)

| Operation | Required Actions | Optional Actions | Resource Pattern |
|-----------|-----------------|-----------------|-----------------|
| Decode encrypted diagnostic message (L1) | ram:DecodeDiagnosticMessage | - | acs:ram:*:*:* |
| Query current user info (L2) | ram:GetUser | - | acs:ram:*:*:user/* |
| List policies attached to a user (L2) | ram:ListPoliciesForUser | - | acs:ram:*:*:* |
| List policies attached to a role (L2) | ram:ListPoliciesForRole | - | acs:ram:*:*:* |
| Read policy content (L2) | ram:GetPolicy,ram:GetPolicyVersion | - | acs:ram:*:*:policy/* |
| List policy versions (L2) | ram:ListPolicyVersions | - | acs:ram:*:*:policy/* |
| Query CP control policies (L2) | ram:ListControlPolicies,ram:GetControlPolicy | - | acs:ram:*:*:* |

### Repair Operations (write — required for L3)

| Operation | Required Actions | Optional Actions | Resource Pattern |
|-----------|-----------------|-----------------|-----------------|
| Create custom policy | ram:CreatePolicy | - | acs:ram:*:*:policy/* |
| Attach policy to user | ram:AttachPolicyToUser | - | acs:ram:*:*:* |
| Attach policy to role | ram:AttachPolicyToRole | - | acs:ram:*:*:* |
| Update policy version | ram:CreatePolicyVersion,ram:DeletePolicyVersion | ram:ListPolicyVersions | acs:ram:*:*:policy/* |
| Detach policy from user | ram:DetachPolicyFromUser | - | acs:ram:*:*:* |
| Detach policy from role | ram:DetachPolicyFromRole | - | acs:ram:*:*:* |

## Recommended System Policies

- Diagnostic only (L1+L2): `AliyunRAMReadOnlyAccess`
- Full functionality (L1+L2+L3): `AliyunRAMFullAccess`

## Official RAM Documentation

- https://help.aliyun.com/document_detail/28630.html (RAM authorization action list — manually maintained)
