# Identity Permission Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Fix 1: Fix system disk root directory permissions (SystemDiskAccessDenied)

**Applicable root cause**: SystemDiskAccessDenied

```powershell
icacls 'C:\' /grant 'BUILTIN\Users:(OI)(CI)(RX)'
icacls 'C:\' /grant 'NT AUTHORITY\SERVICE:(OI)(CI)(RX)'
```

**Verification**:

```powershell
# Verify using Get-Acl to avoid parsing cmd output across locales
$acl = Get-Acl 'C:\'
$acl.Access | Where-Object { $_.IdentityReference -match 'BUILTIN\\Users|NT AUTHORITY\\SERVICE' } | Select-Object IdentityReference, FileSystemRights, AccessControlType | Format-Table -AutoSize
```

Expected result: Shows `BUILTIN\Users:(OI)(CI)(RX)` and `NT AUTHORITY\SERVICE:(OI)(CI)(RX)`

**Risk notes**:
- **Session impact**: None; permission changes take effect immediately for new file access operations.
- **Persistence scope**: Survives reboot (ACL changes are persisted on disk).
- **Rollback command**: `icacls 'C:\' /remove 'BUILTIN\Users'; icacls 'C:\' /remove 'NT AUTHORITY\SERVICE'`

### Fix 2: Fix Temp folder permissions (TempFolderAccessDenied)

**Applicable root cause**: TempFolderAccessDenied

```powershell
icacls "$env:TEMP" /grant 'BUILTIN\Administrators:(OI)(CI)(F)'
icacls "$env:TEMP" /grant 'BUILTIN\Users:(OI)(CI)(RX)'
```

**Verification**:

```powershell
# Verify using Get-Acl to avoid parsing cmd output across locales
$acl = Get-Acl $env:TEMP
$acl.Access | Where-Object { $_.IdentityReference -match 'BUILTIN\\Administrators|BUILTIN\\Users' } | Select-Object IdentityReference, FileSystemRights, AccessControlType | Format-Table -AutoSize
```

Expected result: Shows `BUILTIN\Administrators:(OI)(CI)(F)` and `BUILTIN\Users:(OI)(CI)(RX)`

**Risk notes**:
- **Session impact**: None; permission changes take effect immediately for new file access operations.
- **Persistence scope**: Survives reboot (ACL changes are persisted on disk).
- **Rollback command**: `icacls "$env:TEMP" /remove 'BUILTIN\Administrators'; icacls "$env:TEMP" /remove 'BUILTIN\Users'`

### Fix 3: Disable ForceGuest (ForceGuestAccess)

**Applicable root cause**: ForceGuestAccess

```powershell
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name 'ForceGuest' -Value 0 -Type DWord
```

**Verification**:

```powershell
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name 'ForceGuest' | Select-Object ForceGuest
```

Expected result: `ForceGuest` value is `0`

**Risk notes**:
- **Session impact**: May affect network authentication for currently connected SMB sessions; new connections will use normal authentication.
- **Persistence scope**: Survives reboot (registry change in Lsa key).
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name 'ForceGuest' -Value 1 -Type DWord`

### Fix 4: Remove remote logon deny policy (DenyRDPLogonPolicy)

**Applicable root cause**: DenyRDPLogonPolicy

```powershell
# Export current security policy
secedit /export /cfg "$env:TEMP\secpol_fix.cfg" /quiet
# Remove target user/group from SeDenyRemoteInteractiveLogonRight
# Manual edit: remove the target SID/name from the line, then import
$content = Get-Content "$env:TEMP\secpol_fix.cfg"
$content = $content -replace '(<TargetUserOrSID>,?)', ''
Set-Content -Path "$env:TEMP\secpol_fix.cfg" -Value $content
secedit /configure /db "$env:TEMP\secpol.sdb" /cfg "$env:TEMP\secpol_fix.cfg" /areas USER_RIGHTS /quiet
Remove-Item "$env:TEMP\secpol_fix.cfg","$env:TEMP\secpol.sdb" -Force -ErrorAction SilentlyContinue
```

**Verification**:

```powershell
secedit /export /cfg "$env:TEMP\secpol_verify.cfg" /quiet
Get-Content "$env:TEMP\secpol_verify.cfg" | Select-String 'SeDenyRemoteInteractiveLogonRight'
Remove-Item "$env:TEMP\secpol_verify.cfg" -Force -ErrorAction SilentlyContinue
```

Expected result: Target user/group no longer appears in the SeDenyRemoteInteractiveLogonRight line

> Note: If this policy is pushed by domain Group Policy, local modifications will be overwritten on the next GPO refresh; it must be modified on the domain controller side.

**Risk notes**:
- **Session impact**: None for current sessions; affected users can establish new RDP connections immediately.
- **Persistence scope**: Survives reboot (security policy is persisted in the database).
- **Rollback command**: Re-add the user/group to `SeDenyRemoteInteractiveLogonRight` via `secedit /configure` with the original policy configuration.

### Fix 5: Disable Guest account

**Applicable scenario**: Guest account is enabled

```powershell
Disable-LocalUser -Name 'Guest'
```

**Verification**:

```powershell
Get-LocalUser -Name 'Guest' | Select-Object Name, Enabled | Format-List
```

Expected result: `Enabled` shows `False`

**Risk notes**:
- **Session impact**: If Guest had an active session it remains; new Guest logins are blocked immediately.
- **Persistence scope**: Survives reboot.
- **Rollback command**: `Enable-LocalUser -Name 'Guest'`
