# Performance Lifecycle Diagnostic Fix Guide

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Auto-end tasks policy not enabled (unattended shutdown stuck)

**Fix**:

```powershell
# Enable auto-termination of unresponsive tasks (current user HKCU)
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name AutoEndTasks -Value "1" -Type String
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name AutoEndTasks | Select-Object -ExpandProperty AutoEndTasks
```

Expected result: Return value is 1

**Risk notes**:

- **Session impact**: None, only affects behavior during next shutdown/logoff.
- **Persistence scope**: Written to registry, persisted across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name 'AutoEndTasks' -Value '0'`
- **Note**: After enabling, shutdown will no longer show the "waiting for programs to close" prompt; unresponsive applications will be automatically force-terminated, which may cause loss of unsaved data.

### Root cause: Shutdown service wait timeout too long or too short

**Fix**:

```powershell
# Restore WaitToKillServiceTimeout to default value 5000 (5 seconds, in ms)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control" -Name WaitToKillServiceTimeout -Value 5000 -Type DWord
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control" -Name WaitToKillServiceTimeout | Select-Object -ExpandProperty WaitToKillServiceTimeout
```

Expected result: Return value is 5000

**Risk notes**:

- **Session impact**: None, only affects the service termination wait time during next shutdown.
- **Persistence scope**: Written to registry, persisted across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control' -Name 'WaitToKillServiceTimeout' -Value '<OriginalValue>' -Type DWord`
- **Note**: Shortening the wait time may cause some services to not complete cleanup operations (such as writing logs, releasing resources) before closing. If services depend on long cleanup times, consider increasing to 20000~60000. Modifying this registry key requires Administrator privileges.

### Root cause: Shutdown application wait timeout too long

**Fix**:

```powershell
# Restore WaitToKillAppTimeout to default value 20000 (20 seconds)
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name WaitToKillAppTimeout -Value "20000" -Type String
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name WaitToKillAppTimeout | Select-Object -ExpandProperty WaitToKillAppTimeout
```

Expected result: Return value is 20000

**Risk notes**:

- **Session impact**: None, only affects the current user's next shutdown/logoff behavior.
- **Persistence scope**: Written to HKCU registry, only applies to the current user.
- **Rollback command**: `Set-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name 'WaitToKillAppTimeout' -Value '<OriginalValue>' -Type String`
- **Note**: Only applies to the current user. After shortening the wait time, unsaved documents may not get a prompt for the user to save in time.

### Root cause: Hung app detection timeout too long

**Fix**:

```powershell
# Restore HungAppTimeout to default value 5000 (5 seconds)
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name HungAppTimeout -Value "5000" -Type String
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name HungAppTimeout | Select-Object -ExpandProperty HungAppTimeout
```

Expected result: Return value is 5000

**Risk notes**:

- **Session impact**: None, only affects the threshold for the system to determine "not responding" for the current user.
- **Persistence scope**: Written to HKCU registry, only applies to the current user.
- **Rollback command**: `Set-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name 'HungAppTimeout' -Value '<OriginalValue>' -Type String`
- **Note**: After shortening, the system will determine applications as "not responding" faster and enter the termination process. Normally busy applications may be falsely flagged.
