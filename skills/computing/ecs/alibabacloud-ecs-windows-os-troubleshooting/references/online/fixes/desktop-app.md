# Desktop Application Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: .NET Framework not installed

**Fix operation**:

```powershell
# Install .NET Framework 3.5 (requires Windows installation source)
Enable-WindowsOptionalFeature -Online -FeatureName NetFx3 -All -NoRestart
# .NET Framework 4.8 needs to be downloaded from Microsoft official website
```

**Verification**:

```powershell
$v4 = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -ErrorAction SilentlyContinue).Release
Write-Host ".NET 4.x Release: $v4"
```

Expected result: Release value exists and meets application requirements

**Risk notes**:

- **Session impact**: .NET 3.5 installation does not require a reboot and does not affect existing connections; .NET 4.8 installation requires a reboot after completion.
- **Persistence scope**: Permanently installed, retained after reboot.
- **Rollback command**: `Disable-WindowsOptionalFeature -Online -FeatureName NetFx3 -NoRestart` (only for 3.5; 4.8 must be uninstalled via "Programs and Features").

### Root cause: Windows Installer service disabled

**Fix operation**:

```powershell
Set-Service -Name msiserver -StartupType Manual
Start-Service msiserver
```

**Verification**:

```powershell
Get-Service msiserver | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

Expected result: Status is Running, StartType is Manual

**Risk notes**:

- **Session impact**: None, does not affect existing connections.
- **Persistence scope**: StartupType changes are retained after reboot.
- **Rollback command**: `Set-Service -Name msiserver -StartupType Disabled; Stop-Service msiserver`
