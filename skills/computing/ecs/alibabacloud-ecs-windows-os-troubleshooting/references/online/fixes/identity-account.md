# Identity Account Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Fix 1: Unlock account (RDPAccountLocked)

**Applicable root cause**: RDPAccountLocked

```powershell
#requires -RunAsAdministrator
# Unlock local user account (lockout caused by too many failed password attempts)
$user = [ADSI]"WinNT://$env:COMPUTERNAME/<UserName>,user"
$user.IsAccountLocked = $false
$user.SetInfo()

# For domain user account (requires ActiveDirectory module)
# Unlock-ADAccount -Identity <UserName>
```

**Verification**:

```powershell
$user = [ADSI]"WinNT://$env:COMPUTERNAME/<UserName>,user"
[PSCustomObject]@{
    AccountLocked = $user.IsAccountLocked
} | Format-List
```

Expected result: `AccountLocked` shows `False`

**Risk notes**:
- **Session impact**: None; account is unlocked immediately, affected user can log in right away.
- **Persistence scope**: Survives reboot (lockout state is stored in SAM database).
- **Rollback command**: `$user = [ADSI]"WinNT://$env:COMPUTERNAME/<UserName>,user"; $user.IsAccountLocked = $true; $user.SetInfo()`

### Fix 2: Enable disabled account (RDPAccountDisabled)

**Applicable root cause**: RDPAccountDisabled

```powershell
Enable-LocalUser -Name '<UserName>'
```

**Verification**:

```powershell
Get-LocalUser -Name '<UserName>' | Select-Object Name, Enabled | Format-List
```

Expected result: `Enabled` shows `True`

**Risk notes**:
- **Session impact**: None; account is enabled immediately.
- **Persistence scope**: Survives reboot.
- **Rollback command**: `Disable-LocalUser -Name '<UserName>'`

### Fix 3: Reset expired password

**Applicable scenario**: Password has expired

```powershell
# Reset password via Cloud Assistant
Set-LocalUser -Name '<UserName>' -Password (ConvertTo-SecureString '<NewPassword>' -AsPlainText -Force)
# Or reset password via ECS console
```

**Verification**:

```powershell
Get-LocalUser -Name '<UserName>' | Select-Object Name, PasswordExpires, PasswordRequired | Format-List
```

Expected result: Command executes successfully; account password has been updated

**Risk notes**:
- **Session impact**: None; active sessions are not disrupted. The affected user must use the new password on next login.
- **Persistence scope**: Survives reboot.
- **Rollback command**: `Set-LocalUser -Name '<UserName>' -Password (ConvertTo-SecureString '<OldPassword>' -AsPlainText -Force)`

### Fix 4: Create Administrator account (AdminUserNotExist)

**Applicable root cause**: AdminUserNotExist

```powershell
New-LocalUser -Name 'Administrator' -Description 'Built-in Administrator account' -NoPassword
Add-LocalGroupMember -Group 'Administrators' -Member 'Administrator'
# Set password via ECS console or Cloud Assistant
```

**Verification**:

```powershell
Get-LocalUser -Name 'Administrator' | Select-Object Name, SID, Enabled | Format-List
Get-LocalGroupMember -Group 'Administrators' | Where-Object { $_.Name -eq 'Administrator' } | Format-Table -AutoSize
```

Expected result: Administrator account exists, SID ends with -500, belongs to Administrators group

**Risk notes**:
- **Session impact**: None; new account creation does not disrupt existing sessions.
- **Persistence scope**: Survives reboot.
- **Rollback command**: `Remove-LocalUser -Name 'Administrator'`
