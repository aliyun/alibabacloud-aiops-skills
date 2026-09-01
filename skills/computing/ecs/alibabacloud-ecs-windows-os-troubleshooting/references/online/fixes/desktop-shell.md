# Desktop Shell Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Login Shell configuration abnormal

**Fix operation**:

```powershell
# Restore default Shell configuration
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'Shell' -Value 'explorer.exe'
# Remove user-level Shell override (if exists)
Remove-ItemProperty -Path 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'Shell' -ErrorAction SilentlyContinue
```

**Verification**:

```powershell
(Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'Shell').Shell
```

Expected result: Returns `explorer.exe`; after logoff and re-login the desktop displays normally

**Risk notes**:

- **Session impact**: Requires logoff/re-login to take effect; does not affect current RDP session.
- **Persistence scope**: Registry modification; preserved across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'Shell' -Value '<original value>'`
- **Note**: If Shell was intentionally modified to another program (e.g., kiosk mode), confirm the original intent before restoring.

### Root cause: Explorer.exe not started

**Fix operation**:

```powershell
# Manually start Explorer.exe
Start-Process explorer.exe
```

**Verification**:

```powershell
Get-Process -Name explorer -ErrorAction SilentlyContinue | Select-Object Id, ProcessName | Format-Table -AutoSize
```

Expected result: explorer.exe process exists; desktop and taskbar display normally

**Risk notes**:

- **Session impact**: None; only starts a process.
- **Persistence scope**: Temporary operation; after reboot depends on Shell registry configuration to auto-start.
- **Rollback command**: `Stop-Process -Name explorer -Force`
- **Note**: If Explorer crashes immediately after launch, it may be caused by third-party Shell extensions; try troubleshooting in Safe Mode.

### Root cause: DWM not started

**Fix operation**:

```powershell
# Start DWM service
Set-Service -Name UxSms -StartupType Automatic
Start-Service UxSms
```

**Verification**:

```powershell
Get-Service UxSms | Select-Object Name, Status | Format-Table -AutoSize
Get-Process dwm -ErrorAction SilentlyContinue
```

Expected result: UxSms service running; dwm.exe process exists

**Risk notes**:

- **Session impact**: None; does not affect RDP connection.
- **Persistence scope**: StartupType change preserved across reboots.
- **Rollback command**: `Stop-Service UxSms; Set-Service -Name UxSms -StartupType Disabled`
- **Note**: On Windows Server Core edition DWM may not be available; this is normal behavior.

### Root cause: Console session state abnormal (ConsoleSessionStatusError)

**Fix operation**:

1. Restart Remote Desktop Services:
   ```powershell
   Restart-Service TermService -Force
   ```
2. If the issue persists, check whether third-party remote control software (e.g., VNC Server) is installed and confirm it is not occupying the Console session
3. Reboot the instance if necessary

**Verification**:

```powershell
query session
```

Expected result: Console session State is Active or Connected

**Risk notes**:
- **Session impact**: Restarting TermService will disconnect all active RDP sessions; users will need to reconnect.
- **Persistence scope**: Service restart is transient; no persistent configuration change is made.
- **Rollback command**: No rollback needed (service restart is transient); if required, `Restart-Service TermService -Force` again.
