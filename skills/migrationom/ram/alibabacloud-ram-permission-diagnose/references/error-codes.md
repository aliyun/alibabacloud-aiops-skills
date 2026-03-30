# Alibaba Cloud RAM Permission ErrorCode Reference

## Insufficient Permission (requires authorization repair)

| ErrorCode | Description | Typical Scenario |
|-----------|-------------|-----------------|
| `NoPermission` | The current identity does not have permission to perform this operation | Most common — RAM user/role missing the required Action |
| `Forbidden` | Operation denied | Some services use this code instead of NoPermission |
| `AccessDenied` | Access denied | Commonly used by OSS, STS, and other services |
| `Forbidden.RAM` | Denied by RAM policy | Contains information related to RAM sub-accounts |
| `Forbidden.NotSupportRAM` | This operation does not support RAM sub-accounts | Requires primary account operation or special authorization |

## STS / Token Issues (requires renewal or reconfiguration)

| ErrorCode | Description | How to Handle |
|-----------|-------------|---------------|
| `InvalidSecurityToken.Expired` | STS Token has expired | Re-run AssumeRole to obtain a new token |
| `InvalidSecurityToken.MismatchWithAccessKey` | Token does not match the AK | Verify that AK/SK/Token all come from the same AssumeRole call |
| `InvalidSecurityToken` | Token is invalid | Check token format and validity |
| `SecurityTokenExpired` | Security token expired (used by some services) | Same as above — re-obtain token |

## Service-Linked Role Issues (requires creating an SLR)

| ErrorCode | Description | How to Handle |
|-----------|-------------|---------------|
| `ServiceRoleNotFound` | Service-linked role does not exist | Create the SLR for the corresponding service |
| `ServiceLinkedRoleNotExist` | Same as above (used by some services) | Create the SLR for the corresponding service |

## Permission Level Probing Reference

The following ErrorCodes indicate **the identity has permission but the parameter or resource has an issue** — they do not indicate insufficient permission. Encountering these codes during probing means the permission exists at that level:
- `InvalidParameter`, `MissingParameter`
- `EntityNotExist`, `EntityNotExists`
- `NotFound`, `ResourceNotFound`
- `InvalidInput`

The following ErrorCodes explicitly indicate **insufficient permission** — stop probing and record the level upon encountering them:
- `NoPermission`, `Forbidden`, `AccessDenied`
- `Forbidden.RAM`, `Forbidden.NotSupportRAM`
