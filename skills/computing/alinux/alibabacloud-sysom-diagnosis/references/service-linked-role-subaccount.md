# SysOM Activation for Subaccounts and Service-Linked Roles (SLR)

When a subaccount activates SysOM in the **Alinux console**, it may fail with missing permissions like **`ram:CreateServiceLinkedRole`**. In that case, handling must be done by the **primary account** or an account with RAM administration privileges, or according to organizational IAM policy.

Common handling patterns (subject to console behavior and tenant governance):

1. Use an authorized account to activate SysOM (SLR is usually auto-created as **`AliyunServiceRoleForSysom`** during activation).
2. In **RAM console**, attach a custom policy to the subaccount that allows creating service-linked roles (policy content must comply with your organization security requirements).
3. Let administrators pre-activate SysOM and create SLR, then allow subaccounts to use SysOM features only.

For full authentication flows and AK/RAM Role paths, see [authentication.md](./authentication.md) and [openapi-permission-guide.md](./openapi-permission-guide.md).
