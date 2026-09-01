# Cloud Driver Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: VirtIO driver version too old

**Fix operation**:

```powershell
# 1. Download VirtIO driver package
# Prefer user-provided URL; if not available, generate by rule:
# http://windows-driver-{region}.oss-{region}-internal.aliyuncs.com/virtio/latest.zip
$region = '<Region>'   # e.g. cn-hangzhou
$url = '<UserProvidedURL>'
if (-not $url -or $url -like '<*>') {
    $url = "http://windows-driver-${region}.oss-${region}-internal.aliyuncs.com/virtio/latest.zip"
}
$zipPath = Join-Path $env:TEMP 'virtio.zip'
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -TimeoutSec 300

# 2. Extract
$drvDir = Join-Path $env:TEMP 'virtio'
Expand-Archive -Path $zipPath -DestinationPath $drvDir -Force

# 3. Install all driver packages online (pnputil matches hardware automatically)
Get-ChildItem -Path $drvDir -Recurse -Filter *.inf | ForEach-Object {
    pnputil /add-driver $_.FullName /install
}

# 4. Clean up downloaded files
Remove-Item -Path $zipPath, $drvDir -Recurse -Force -ErrorAction SilentlyContinue
# A reboot is required to fully apply the updated drivers
```

**Verification**:

```powershell
# Verify the best installed driver package per INF (PnP selects the active one
# at boot by Rank -> Date -> Version; do not read the loaded .sys version)
Get-WindowsDriver -Online -ErrorAction SilentlyContinue |
  Where-Object { $_.OriginalFileName -match '(?i)(viostor|vioscsi|netkvm|balloon|vioser|pvpanic|fwcfg)\.inf$' } |
  Group-Object { Split-Path $_.OriginalFileName -Leaf } |
  ForEach-Object {
    $_.Group | Sort-Object @{e={ if ($_.Version -as [version]) { [version]$_.Version } else { [version]'0.0.0' } }} -Descending | Select-Object -First 1
  } |
  Select-Object OriginalFileName, Version, Date | Format-Table -AutoSize
```

Expected result: The 4th segment of the best package version number >= 58017 (old version packages may still remain in the driver repository; use the package with the highest version number)

**Risk notes**:

- **Session impact**: Updating drivers requires a reboot, which will interrupt all connections.
- **Persistence scope**: Permanently installed, retained after reboot.
- **Rollback command**: Roll back via system snapshot (it is recommended to create a snapshot before updating).

---

### Root cause: Driver installation blocked by policy

**Fix operation**:

```powershell
# Windows Server 2016+ remove block policy
Remove-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\DeviceInstall\Parameters' -Name DeviceInstallDisabled -ErrorAction SilentlyContinue

# Windows Server 2012 and earlier
Remove-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\PlugPlay\Parameters' -Name DeviceInstallDisabled -ErrorAction SilentlyContinue
```

**Verification**:

```powershell
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\DeviceInstall\Parameters' -Name DeviceInstallDisabled -ErrorAction SilentlyContinue | Select-Object DeviceInstallDisabled
```

Expected result: Registry key does not exist (no output)

**Risk notes**:

- **Session impact**: None, only removes a registry key.
- **Persistence scope**: Registry changes are retained after reboot. If set by domain GPO, it will be overwritten on the next GPO refresh.
- **Rollback command**: `Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\DeviceInstall\Parameters' -Name DeviceInstallDisabled -Value 1 -Type DWord`

---

### Root cause: Xen driver residual

**Fix operation**:

```powershell
# Remove XenPCI service hide_devices parameter
Remove-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\XenPCI\Parameters' -Name hide_devices -ErrorAction SilentlyContinue

# Uninstall Xen driver packages (one by one)
$xenDrivers = Get-WindowsDriver -Online | Where-Object { $_.OriginalFileName -match 'xen' }
foreach ($d in $xenDrivers) {
  pnputil /delete-driver $d.Driver /uninstall /force
}
```

**Verification**:

```powershell
Get-WindowsDriver -Online -ErrorAction SilentlyContinue |
  Where-Object { $_.OriginalFileName -match 'xen' } |
  Select-Object Driver, OriginalFileName | Format-Table -AutoSize
```

Expected result: No Xen-related driver packages in output

**Risk notes**:

- **Session impact**: A reboot is required after uninstall to take effect, which will interrupt all connections.
- **Persistence scope**: Permanently uninstalled, retained after reboot.
- **Rollback command**: Roll back via system snapshot (Xen drivers cannot be reinstalled after uninstall).
- **Note**: Ensure VirtIO drivers are installed before performing this operation, otherwise disk or network may become unavailable.
