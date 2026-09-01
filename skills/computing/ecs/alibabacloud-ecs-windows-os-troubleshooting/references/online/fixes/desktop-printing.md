# Desktop Printing Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Print Spooler service not started

**Fix operation**:

```powershell
Set-Service -Name Spooler -StartupType Automatic
Start-Service Spooler
```

**Verification**:

```powershell
Get-Service Spooler | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

Expected result: Status is Running, StartType is Automatic

**Risk notes**:

- **Session impact**: Starting Spooler does not affect existing RDP connections.
- **Persistence scope**: StartupType changes are retained after reboot.
- **Rollback command**: `Stop-Service Spooler; Set-Service -Name Spooler -StartupType Disabled`
- **Security note**: Print Spooler has historical security vulnerabilities (PrintNightmare, etc.). If the server does not require printing functionality, it is recommended to keep it disabled.

### Root cause: Print queue jammed

**Fix operation**:

```powershell
# Clear print queue
Stop-Service Spooler -Force
Remove-Item -Path "$env:SystemRoot\System32\spool\PRINTERS\*" -Force -ErrorAction SilentlyContinue
Start-Service Spooler
```

**Verification**:

```powershell
$spoolFiles = Get-ChildItem -Path "$env:SystemRoot\System32\spool\PRINTERS" -ErrorAction SilentlyContinue
Write-Host "Spool files remaining: $($spoolFiles.Count)"
Get-Service Spooler | Select-Object Name, Status | Format-Table -AutoSize
```

Expected result: Spool directory is empty, Spooler service is running

**Risk notes**:

- **Session impact**: Spooler stops briefly (a few seconds), does not affect RDP connections.
- **Persistence scope**: Deleted print jobs are not recoverable.
- **Rollback command**: Cannot be rolled back; cleared print queues cannot be restored.
