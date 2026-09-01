# System Management Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Fix 1: Modify Execution Policy

**Applicable scenario**: PowerShell script is blocked by execution policy

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine -Force
```

**Verification**:

```powershell
Get-ExecutionPolicy -Scope LocalMachine
```

Expected result: Returns `RemoteSigned` or `Unrestricted`

**Risk notes**:
- **Session impact**: None; affects only new PowerShell sessions, not the current one.
- **Persistence scope**: Survives reboot (LocalMachine scope is persistent).
- **Rollback command**: `Set-ExecutionPolicy -ExecutionPolicy Restricted -Scope LocalMachine -Force`

### Fix 2: Enable and Configure WinRM

**Applicable scenario**: WinRM service is not running or not configured

```powershell
# Quick WinRM configuration (start service + create listener + firewall rule)
winrm quickconfig -force
```

**Verification**:

```powershell
Test-WSMan -ErrorAction SilentlyContinue
# Or check WinRM service status
Get-Service WinRM | Select-Object Name, Status
```

Expected result: `Test-WSMan` returns protocol version information, WinRM service status is `Running`

**Risk notes**:
- **Session impact**: WinRM service start may briefly affect remote management connections; does not affect RDP.
- **Persistence scope**: Survives reboot (service set to Automatic, listener and firewall rule are persistent).
- **Rollback command**: `Set-Service -Name WinRM -StartupType Disabled; Stop-Service WinRM -Force`

### Fix 3: Repair WMI Repository

**Applicable scenario**: WMI repository is corrupted

```powershell
# Stop WMI service
Stop-Service Winmgmt -Force
# Rebuild WMI repository
winmgmt /resetrepository
# Restart service
Start-Service Winmgmt
```

**Verification**:

```powershell
Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object Name
```

Expected result: Successfully returns computer name with no WMI errors

> Rebuilding the WMI repository will reset all WMI class definitions; some third-party applications may need to re-register their WMI providers.

**Risk notes**:
- **Session impact**: WMI-dependent services and monitoring tools may temporarily fail during repository rebuild; current RDP session is not affected.
- **Persistence scope**: Survives reboot (repository is rebuilt on disk).
- **Rollback command**: No direct rollback; restore from system backup or snapshot if WMI was in a better state before.

### Fix 4: Repair Event Log Service

**Applicable scenario**: Event Log service is stopped or logs are full

```powershell
# Start Event Log service
Start-Service EventLog
# WARNING: This permanently clears the event log. Back up first:
# wevtutil epl System "$env:TEMP\SystemEventLogBackup.evtx"
# wevtutil epl Application "$env:TEMP\ApplicationEventLogBackup.evtx"
Clear-EventLog -LogName System
Clear-EventLog -LogName Application
```

**Verification**:

```powershell
Get-Service EventLog | Select-Object Name, Status
Get-WinEvent -LogName System -MaxEvents 1 | Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-List
```

Expected result: EventLog service status is `Running`, `Get-WinEvent` successfully returns the most recent event

**Risk notes**:
- **Session impact**: Event Log service restart is brief; clearing logs permanently deletes historical event records.
- **Persistence scope**: Survives reboot (cleared logs cannot be recovered; service startup type is persistent).
- **Rollback command**: No rollback for cleared logs; restore from backup `.evtx` files if backed up before clearing.
