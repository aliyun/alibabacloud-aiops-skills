# System Update Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Fix 1: Repair Dependent Services (UpdateDependentServiceInvalid)

**Applicable Root cause**: UpdateDependentServiceInvalid

```powershell
# Start critical services and set them to automatic startup
foreach ($svc in @('wuauserv','BITS','CryptSvc','TrustedInstaller')) {
  Set-Service -Name $svc -StartupType Automatic -ErrorAction SilentlyContinue
  Start-Service -Name $svc -ErrorAction SilentlyContinue
}
```

**Risk notes**:
- **Session impact**: Brief interruption to Windows Update, BITS, and cryptographic services during restart; does not affect RDP.
- **Persistence scope**: Survives reboot (services set to Automatic startup).
- **Rollback command**: `Set-Service -Name wuauserv -StartupType Manual; Set-Service -Name BITS -StartupType Manual; Set-Service -Name CryptSvc -StartupType Manual; Set-Service -Name TrustedInstaller -StartupType Manual`

### Fix 2: Correct WSUS Configuration (WUServerConfigError)

**Applicable Root cause**: WUServerConfigError

```powershell
$wsusPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate'
$auPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU'
Set-ItemProperty -Path $wsusPath -Name 'WUServer' -Value 'http://update.cloud.aliyuncs.com'
Set-ItemProperty -Path $wsusPath -Name 'WUStatusServer' -Value 'http://update.cloud.aliyuncs.com'
Set-ItemProperty -Path $auPath -Name 'UseWUServer' -Value 1 -Type DWord
# Restart Windows Update service to apply the configuration
Restart-Service wuauserv -Force
```

**Risk notes**:
- **Session impact**: Windows Update service restart may briefly interrupt ongoing update operations; does not affect RDP.
- **Persistence scope**: Survives reboot (registry change in WindowsUpdate policy key).
- **Rollback command**: `Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' -Name 'WUServer','WUStatusServer' -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' -Name 'UseWUServer' -ErrorAction SilentlyContinue; Restart-Service wuauserv -Force`

### Fix 3: Uninstall Problematic Hotfix (ProblematicHotfixInstalled)

**Applicable Root cause**: ProblematicHotfixInstalled

```powershell
# Uninstall specified KB (replace KBXXXXXXX with the actual KB number)
wusa /uninstall /kb:XXXXXXX /quiet /norestart
# Restart system after uninstallation
```

> It is recommended to create a system restore point or snapshot before uninstalling, to allow rollback.

**Risk notes**:
- **Session impact**: None during uninstall (quiet mode); system reboot required afterward which will disconnect RDP.
- **Persistence scope**: Survives reboot (hotfix is permanently removed).
- **Rollback command**: Reinstall the hotfix via `wusa <KBXXXXXXX>.msu /quiet` or through Windows Update.

### Fix 4: Sync WinHTTP Proxy (WinhttpConfigError)

**Applicable Root cause**: WinhttpConfigError

```powershell
# Import IE proxy settings into WinHTTP
netsh winhttp import proxy source=ie
# Or directly set WinHTTP proxy
# netsh winhttp set proxy proxy-server="http=proxy:port;https=proxy:port"
```

**Risk notes**:
- **Session impact**: None; affects new network connections using WinHTTP, not the current RDP session.
- **Persistence scope**: Survives reboot (WinHTTP proxy setting is persistent).
- **Rollback command**: `netsh winhttp reset proxy`

### Fix 5: Reset Update Cache and Pending Operations (UpdatePendingOperationStuck / UpdateCacheCorrupted)

**Applicable Root cause**: UpdatePendingOperationStuck, UpdateCacheCorrupted

```powershell
# Stop update-related services before resetting caches
Stop-Service wuauserv -Force -ErrorAction SilentlyContinue
Stop-Service BITS -Force -ErrorAction SilentlyContinue
Stop-Service CryptSvc -Force -ErrorAction SilentlyContinue
Stop-Service msiserver -Force -ErrorAction SilentlyContinue

# Rename update caches (kept as .bak for rollback instead of deleting)
Rename-Item 'C:\Windows\SoftwareDistribution' 'SoftwareDistribution.bak' -Force -ErrorAction SilentlyContinue
Rename-Item 'C:\Windows\System32\Catroot2' 'Catroot2.bak' -Force -ErrorAction SilentlyContinue

# Move aside stuck pending operation file
if (Test-Path 'C:\Windows\WinSxS\pending.xml') {
  Rename-Item 'C:\Windows\WinSxS\pending.xml' 'pending.xml.bak' -Force
}

# Restart services
Start-Service CryptSvc
Start-Service BITS
Start-Service wuauserv
Start-Service msiserver -ErrorAction SilentlyContinue
Write-Host "Update caches reset. Please retry Windows Update, then reboot."
```

**Risk notes**: Session impact: does not disconnect RDP; restarting wuauserv/BITS/CryptSvc briefly affects background updates and certificate verification cache. Persistence: renamed directories are retained after reboot. Rollback: stop services, then rename `.bak` directories/files back to their original names and start services. Note: The first update check after reset takes longer; if there are unfinished pending installations, a reboot is required after reset before continuing with updates.
