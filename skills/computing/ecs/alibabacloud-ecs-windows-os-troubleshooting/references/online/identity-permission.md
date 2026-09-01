# Identity Permission Diagnostics

## Function Description

Diagnoses Windows system disk root directory permissions, user group membership and remote login permissions, Temp folder permissions, ForceGuest configuration, remote login deny policy, and Guest account status. Covers 6 diagnostic steps.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Step |
|-------------|---------------|
| Black screen or crash after login, Explorer fails to load | Step 1 (System Disk Root Directory Permissions) |
| Prompted "you need the right to sign in through RDS", user has no RDP permission | Step 2 (User Group Membership and Remote Login Permissions) |
| Update installation failure, error 0x80070005 | Step 3 (Temp Folder Permissions) |
| Local account remote login failure, forced mapping to Guest | Step 4 (ForceGuest Configuration) |
| Policy denies specific users RDP login | Step 5 (Remote Login Deny Policy) |
| Unauthorized access risk exists | Step 6 (Guest Account Status) |

## Diagnostic Steps

### Step 1: System Disk Root Directory Permission Check

**Data Collection**:

> Collection target: Check access permissions for BUILTIN\Users and NT AUTHORITY\SERVICE on the C:\ root directory

- PowerShell script: [identity-permission.ps1](references/online/scripts/identity-permission.ps1) Section Step 1

**Analysis Approach**:

1. Check BUILTIN\Users permissions:
   - Normal: BUILTIN\Users has read + execute permissions
   - Abnormal: BUILTIN\Users has no read or execute permissions -> **Root cause**: System disk access denied (SystemDiskAccessDenied), **Severity**: Critical
2. Check NT AUTHORITY\SERVICE permissions:
   - Normal: NT AUTHORITY\SERVICE has no explicit deny
   - Abnormal: NT AUTHORITY\SERVICE is explicitly denied -> **Root cause**: Service account cannot access system disk, **Severity**: Critical

### Step 2: User Group Membership and Remote Login Permission Check

**Data Collection**:

> Collection target: Check members of key user groups, confirm whether the target user has remote login permissions

- PowerShell script: [identity-permission.ps1](references/online/scripts/identity-permission.ps1) Section Step 2

**Analysis Approach**:

1. Check target user's remote login permissions:
   - Normal: Target user is in Administrators or Remote Desktop Users group -> Has remote login permissions
   - Abnormal: Target user is not in any authorized group -> **Root cause**: Missing remote login permissions, **Severity**: Critical
2. Check group membership reasonableness:
   - Abnormal: Unexpected administrator account found -> Need to confirm legitimacy, **Severity**: Warning

### Step 3: Temp Folder Permission Check

**Data Collection**:

> Collection target: Check full control permissions for Administrators on the Temp folder

- PowerShell script: [identity-permission.ps1](references/online/scripts/identity-permission.ps1) Section Step 3

**Analysis Approach**:

1. Check Temp folder permissions:
   - Normal: BUILTIN\Administrators has full control
   - Abnormal: BUILTIN\Administrators has no full control -> **Root cause**: Temp folder permissions insufficient (TempFolderAccessDenied), **Severity**: Warning

### Step 4: ForceGuest Configuration Check

**Data Collection**:

> Collection target: Check whether local users are forced to be mapped to Guest

- PowerShell script: [identity-permission.ps1](references/online/scripts/identity-permission.ps1) Section Step 4

**Analysis Approach**:

1. Check ForceGuest configuration:
   - Normal: ForceGuest does not exist or is 0 -> Network access uses the actual account
   - Abnormal: ForceGuest is not 0 -> **Root cause**: Local user remote access forced to map to Guest (ForceGuestAccess), **Severity**: Critical

> When ForceGuest is enabled, all local users' remote access will be mapped to the Guest account, causing severely limited permissions.

### Step 5: Remote Login Deny Policy Check

**Data Collection**:

> Collection target: Check whether specific users are denied remote desktop login via local security policy

- PowerShell script: [identity-permission.ps1](references/online/scripts/identity-permission.ps1) Section Step 5

**Analysis Approach**:

1. Check remote login deny policy:
   - Normal: SeDenyRemoteInteractiveLogonRight is not configured or does not include the target user/group
   - Abnormal: Target user or their group is listed in SeDenyRemoteInteractiveLogonRight -> **Root cause**: Policy denies remote login (DenyRDPLogonPolicy), **Severity**: Critical
2. Check remote login allow policy:
   - Normal: SeRemoteInteractiveLogonRight includes Administrators or Remote Desktop Users
   - Abnormal: Policy is configured but does not include the target user's group -> **Root cause**: User not granted remote login permissions, **Severity**: Critical

> Note: Once SeRemoteInteractiveLogonRight is explicitly configured, it overrides default behavior and only allows users/groups in the list to log in remotely.

### Step 6: Guest Account Status Check

**Data Collection**:

> Collection target: Check whether the Guest account is enabled

- PowerShell script: [identity-permission.ps1](references/online/scripts/identity-permission.ps1) Section Step 6

**Analysis Approach**:

1. Check Guest account status:
   - Normal: Guest account is Disabled (security best practice)
   - Abnormal: Guest account is Enabled -> **Root cause**: Unauthorized access risk exists, **Severity**: Warning

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Temp permission issues affecting Windows Update | -> [system-update.md](references/online/system-update.md) |
| Conditional jump | System disk permissions affecting RDP | -> [rdp-auth.md](references/online/rdp-auth.md) |
| Conditional jump | SeDenyRemoteInteractiveLogonRight pushed via Group Policy | -> [system-gpo.md](references/online/system-gpo.md) |
| Chained successor | Root cause not confirmed in this file | -> [system-gpo.md](references/online/system-gpo.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [identity-permission.md](references/online/fixes/identity-permission.md).
