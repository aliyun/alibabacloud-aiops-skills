# Identity Active Directory Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Domain secure channel broken

**Fix operation**:

```powershell
# Reset computer account password and repair secure channel (requires domain admin credentials)
Test-ComputerSecureChannel -Repair -Credential (Get-Credential -Message "Enter domain administrator credentials")
```

**Verification**:

```powershell
Test-ComputerSecureChannel
```

Expected result: Returns True

**Risk notes**:

- **Session impact**: None; does not affect existing connections.
- **Persistence scope**: Computer account password update is persistent.
- **Rollback command**: If the password on the domain controller side has expired, you may need to reset the computer account on the domain controller.

### Root cause: Netlogon service not started

**Fix operation**:

```powershell
Set-Service -Name Netlogon -StartupType Automatic
Start-Service Netlogon
```

**Verification**:

```powershell
Get-Service Netlogon | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

Expected result: Status is Running, StartType is Automatic

**Risk notes**:

- **Session impact**: None; only starts a service.
- **Persistence scope**: StartupType change preserved across reboots.
- **Rollback command**: `Stop-Service Netlogon; Set-Service -Name Netlogon -StartupType Manual`
- **Note**: If the secure channel is already broken, repair the secure channel first.

### Root cause: Computer account password change disabled

**Fix operation**:

```powershell
# Enable automatic computer account password change
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters' -Name 'DisablePasswordChange' -Value 0 -Type DWord
```

**Verification**:

```powershell
(Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters').DisablePasswordChange
```

Expected result: Returns 0

**Risk notes**:

- **Session impact**: None; only modifies registry.
- **Persistence scope**: Registry modification preserved across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters' -Name 'DisablePasswordChange' -Value 1`
- **Note**: After enabling automatic password change, the system will periodically update the computer account password according to MaximumPasswordAge (default 30 days); this is the recommended security configuration.
