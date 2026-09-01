# Driver Integrity Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: VirtIO driver not installed or files missing

**Fix operation**: Download the VirtIO driver package from OSS and install offline:

```powershell
$bootLetter = '<BootLetter>'
$osVersion = '<win7|win8|win10>'  # Select based on target OS version
$arch = '<amd64|x86>'           # Select based on target OS architecture
$names = @('viostor', 'vioser', 'netkvm', 'pvpanic', 'balloon', 'fwcfg')

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

# 3. Install drivers one by one
$srcDir = Join-Path $drvDir "$osVersion\$arch"
foreach ($name in $names) {
    $inf = Join-Path $srcDir "$name.inf"
    if (!(Test-Path $inf)) { continue }
    Write-Host "Installing driver: $inf"
    Add-WindowsDriver -Path "${bootLetter}:\" -Driver $inf -ForceUnsigned
    # offline driver install does not reliably copy .sys files, ensure manually
    $bin = Join-Path $srcDir "$name.sys"
    $dst = "${bootLetter}:\Windows\System32\drivers\$name.sys"
    if (!(Test-Path $dst) -and (Test-Path $bin)) {
        Copy-Item -Path $bin -Destination $dst
    }
}

# 4. Ensure netkvm service is not disabled (Start=3 means manual start)
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$hivePath = "HKLM\_SYSTEM"
& reg load $hivePath $sysHive
if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive" }

try {
    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    if (-not $select) { throw "Unable to read SYSTEM\Select" }
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    $netkvmSvc = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Services\netkvm", $true)
    if ($netkvmSvc) {
        $start = $netkvmSvc.GetValue('Start')
        if ($start -eq 4) {
            $netkvmSvc.SetValue('Start', 3, [Microsoft.Win32.RegistryValueKind]::DWord)
        }
        $netkvmSvc.Close(); $netkvmSvc.Dispose()
    }
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
}

# 5. Clean up downloaded files
Remove-Item -Path $zipPath, $drvDir -Recurse -Force -ErrorAction SilentlyContinue
```

**Verification**: Re-check whether the corresponding service entries are created under the Services key in the active ControlSet, and whether .sys files exist in the drivers directory

**Risk notes**:
- Session impact: Downloads and installs VirtIO driver packages to the offline disk via DISM; loads the SYSTEM registry hive to verify netkvm service is not disabled
- Persistence scope: Survives reboot -- driver files and registry changes persist on the target system
- Rollback: Remove installed drivers using `Remove-WindowsDriver -Path "${bootLetter}:\" -Driver <OemInf>` and delete copied .sys files from `Windows\System32\drivers\`

---

### Root cause: VirtIO driver signature invalid

**Fix operation**: Uninstall old driver + reinstall:

```powershell
$bootLetter = '<BootLetter>'

# 1. Get installed VirtIO driver OEM package names
$virtioInfs = @('viostor','netkvm','balloon','pvpanic','vioser','fwcfg')
$oems = Get-WindowsDriver -Path "${bootLetter}:\" | Where-Object {
    $infName = (Split-Path $_.OriginalFileName -Leaf) -replace '\.inf$',''
    $infName -in $virtioInfs
} | Select-Object -ExpandProperty Driver

# 2. Uninstall old drivers
foreach ($oem in $oems) {
    Write-Host "Removing driver: $oem"
    Remove-WindowsDriver -Path "${bootLetter}:\" -Driver $oem
}

# 3. Clean up driver binary files
$bins = @('viostor.sys', 'vioser.sys', 'netkvm.sys', 'pvpanic.sys', 'balloon.sys', 'fwcfg.sys')
foreach ($bin in $bins) {
    $path = "${bootLetter}:\Windows\System32\drivers\$bin"
    if (Test-Path $path) {
        & takeown /F $path
        & icacls $path /grant "$(whoami):(F)"
        Remove-Item $path -Force -ErrorAction SilentlyContinue
    }
}

# 4. Reinstall (follow the 'VirtIO driver not installed' fix flow)
```

**Risk notes**:
- Session impact: Uninstalls existing VirtIO driver packages and deletes .sys files from the offline disk; target system loses storage driver until reinstalled
- Persistence scope: Survives reboot -- driver removal persists until reinstalled
- Rollback: Reinstall the VirtIO drivers following the "VirtIO driver not installed" fix flow; MUST reinstall immediately to avoid disk inaccessibility

---

### Root cause: VirtIO driver service configuration error (abnormal Start value)

**Fix operation**:

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    if (-not $select) { throw "Unable to read SYSTEM\Select" }
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    # viostor/vioscsi must be Boot-Start(0)
    $bootStartDrivers = @('viostor', 'vioscsi')
    foreach ($drv in $bootStartDrivers) {
        $svcKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Services\$drv", $true)
        if ($svcKey) {
            $svcKey.SetValue('Start', 0, [Microsoft.Win32.RegistryValueKind]::DWord)
            Write-Host "Set $drv Start=0 (Boot)"
            $svcKey.Close(); $svcKey.Dispose()
        }
    }

    # netkvm should be System-Start(1) or Manual(3), must not be Disabled(4)
    $netkvmKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Services\netkvm", $true)
    if ($netkvmKey) {
        $start = $netkvmKey.GetValue('Start')
        if ($start -eq 4) {
            $netkvmKey.SetValue('Start', 3, [Microsoft.Win32.RegistryValueKind]::DWord)
            Write-Host "Set netkvm Start=3 (Manual)"
        }
        $netkvmKey.Close(); $netkvmKey.Dispose()
    }
} catch {
    Write-Host "Fix driver start value failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: After re-mounting the SYSTEM HIVE, read the Start value of `HKLM:\_SYSTEM\<CsName>\Services\viostor` -> 0

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to correct driver service Start values (viostor/vioscsi to Boot-Start(0), netkvm to Manual(3))
- Persistence scope: Survives reboot -- registry changes persist on the target system
- Rollback: Restore the original Start values in the offline SYSTEM hive

---

### Root cause: Boot-critical driver file missing

**Fix operation**: Determine based on the specific missing driver:
- Built-in system driver: Copy from `C:\Windows\System32\drivers\` of a system with the same version
- Third-party driver: Recommended to disable the driver (Start=4)

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    if (-not $select) { throw "Unable to read SYSTEM\Select" }
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    $driverName = '<DriverServiceName>'
    $drvKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Services\$driverName", $true)
    if ($drvKey) {
        $drvKey.SetValue('Start', 4, [Microsoft.Win32.RegistryValueKind]::DWord)
        Write-Host "Disabled driver: $driverName (Start=4)"
        $drvKey.Close(); $drvKey.Dispose()
    }
} catch {
    Write-Host "Disable driver failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to set the specified driver service Start to 4 (Disabled)
- Persistence scope: Survives reboot -- registry change persists on the target system
- Rollback: Set the driver service Start value back to its original value in the offline SYSTEM hive. Disabling built-in Boot-Start drivers (such as disk.sys, partmgr.sys) will cause BSOD 0x7B; only execute after confirming that the driver is not a member of the boot-critical chain

---

### Root cause: Xen driver residuals

**Fix operation**:

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    if (-not $select) { throw "Unable to read SYSTEM\Select" }
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    # Disable XenPCI and associated services
    $xenServices = @('XenPCI', 'XENBUS', 'xenvbd', 'xennet', 'xenvif')
    foreach ($svc in $xenServices) {
        $svcKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Services\$svc", $true)
        if ($svcKey) {
            $svcKey.SetValue('Start', 4, [Microsoft.Win32.RegistryValueKind]::DWord)
            Write-Host "Disabled $svc"
            $svcKey.Close(); $svcKey.Dispose()
        }
    }

    # Delete hide_devices parameter
    $xenPciKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Services\XenPCI\Parameters", $true)
    if ($xenPciKey) {
        $xenPciKey.DeleteValue('hide_devices', $false)
        $xenPciKey.Close(); $xenPciKey.Dispose()
    }
} catch {
    Write-Host "Remove Xen drivers failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: After re-mounting the SYSTEM HIVE, read the Start value of `HKLM:\_SYSTEM\<CsName>\Services\XenPCI` -> 4

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to disable Xen services and remove the hide_devices parameter
- Persistence scope: Survives reboot -- registry changes persist on the target system
- Rollback: Re-enable Xen services by setting Start back to original values and recreate the hide_devices parameter if needed. Disabling Xen services does not affect Alibaba Cloud KVM/VirtIO platform operation

---

### Root cause: Disk filter driver residuals (UpperFilters/LowerFilters)

**Fix operation**: Remove SCSI instance-level filter drivers:

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$filtersToRemove = @('<FilterDriverNameToRemove>')
$exitCode = 0

try {
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    $baseKey = [Microsoft.Win32.Registry]::LocalMachine
    $scsiKey = $baseKey.OpenSubKey("_SYSTEM\${csName}\Enum\SCSI", $false)
    if ($scsiKey) {
        foreach ($deviceName in $scsiKey.GetSubKeyNames()) {
            $deviceKey = $scsiKey.OpenSubKey($deviceName, $false)
            foreach ($instance in $deviceKey.GetSubKeyNames()) {
                $instKey = $deviceKey.OpenSubKey($instance, $true)
                # Process UpperFilters
                $upper = $instKey.GetValue('UpperFilters')
                if ($upper) {
                    $new = $upper | Where-Object { $filtersToRemove -notcontains $_ }
                    if ($new.Count -lt $upper.Count) {
                        if ($new.Count -gt 0) {
                            $instKey.SetValue('UpperFilters', [string[]]$new, [Microsoft.Win32.RegistryValueKind]::MultiString)
                        } else {
                            $instKey.DeleteValue('UpperFilters')
                        }
                    }
                }
                # Process LowerFilters
                $lower = $instKey.GetValue('LowerFilters')
                if ($lower) {
                    $new = $lower | Where-Object { $filtersToRemove -notcontains $_ }
                    if ($new.Count -lt $lower.Count) {
                        if ($new.Count -gt 0) {
                            $instKey.SetValue('LowerFilters', [string[]]$new, [Microsoft.Win32.RegistryValueKind]::MultiString)
                        } else {
                            $instKey.DeleteValue('LowerFilters')
                        }
                    }
                }
                $instKey.Close()
            }
            $deviceKey.Close()
        }
        $scsiKey.Close()
    }
} catch {
    Write-Host "Remove SCSI filter driver failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: Re-check whether UpperFilters/LowerFilters under instance keys in Enum\SCSI have been cleared

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to remove specified filter driver entries from SCSI device instances
- Persistence scope: Survives reboot -- registry changes persist on the target system
- Rollback: Re-add the removed filter driver names to UpperFilters/LowerFilters in the offline SYSTEM hive. After removing filter drivers, related security software may not work properly

---

### Root cause: NVMe storage controller driver abnormal (stornvme)

**Fix operation**: Restore stornvme service registration and files

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    & reg load "HKLM\_SYSTEM" $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    $currentControlSet = "_SYSTEM\ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    $svcPath = "$currentControlSet\Services\stornvme"
    $svcKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($svcPath, $true)
    if (-not $svcKey) {
        # Service does not exist, create full registry entry
        $svcKey = [Microsoft.Win32.Registry]::LocalMachine.CreateSubKey($svcPath)
        $svcKey.SetValue('Description', 'Microsoft Standard NVMe Express Driver', [Microsoft.Win32.RegistryValueKind]::String)
        $svcKey.SetValue('DisplayName', 'stornvme', [Microsoft.Win32.RegistryValueKind]::String)
        $svcKey.SetValue('ErrorControl', 1, [Microsoft.Win32.RegistryValueKind]::DWord)
        $svcKey.SetValue('Group', 'SCSI miniport', [Microsoft.Win32.RegistryValueKind]::String)
        $svcKey.SetValue('ImagePath', 'System32\drivers\stornvme.sys', [Microsoft.Win32.RegistryValueKind]::ExpandString)
        $svcKey.SetValue('Start', 0, [Microsoft.Win32.RegistryValueKind]::DWord)
        $svcKey.SetValue('Tag', 33, [Microsoft.Win32.RegistryValueKind]::DWord)
        $svcKey.SetValue('Type', 1, [Microsoft.Win32.RegistryValueKind]::DWord)
        Write-Host "Created stornvme service registry entry."
    } else {
        # Service exists but disabled, restore to Boot-Start
        $start = $svcKey.GetValue('Start')
        if ($start -eq 4) {
            $svcKey.SetValue('Start', 0, [Microsoft.Win32.RegistryValueKind]::DWord)
            Write-Host "Set stornvme Start=0 (Boot)."
        }
    }
    $svcKey.Close(); $svcKey.Dispose()

    # Check binary file existence
    $sysFile = "${bootLetter}:\Windows\System32\drivers\stornvme.sys"
    if (!(Test-Path $sysFile)) {
        Write-Host "WARNING: stornvme.sys not found at $sysFile. Need to copy from same-version system."
    }

    Write-Host "stornvme fix completed."
} catch {
    Write-Host "Fix stornvme failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SYSTEM"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: Re-read Services\stornvme under the active ControlSet to confirm Start=0 and ImagePath file exists

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to restore stornvme service registration (create or re-enable as Boot-Start)
- Persistence scope: Survives reboot -- registry changes persist on the target system
- Rollback: Restore the original stornvme service registry entry or set Start back to 4 (Disabled) if it was previously disabled. If the binary file is missing, it must be copied from the same OS version; version mismatch may cause BSOD

---

### Root cause: Boot device PCI/SCSI registry instance missing or disabled

**Fix operation**: Clear the device disabled flag (reset ConfigFlags to zero)

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    & reg load "HKLM\_SYSTEM" $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    $currentControlSet = "_SYSTEM\ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    # Input: disabled device paths found in diagnostic steps
    $disabledPaths = @('<PCI_DeviceInstancePath>', '<SCSI_DeviceInstancePath>')

    $enumBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        "$currentControlSet\Enum", $true)

    foreach ($devPath in $disabledPaths) {
        # devPath format e.g. PCI\VEN_1AF4&DEV_1001&SUBSYS_00021AF4&REV_00\3&13c0b0c5&0&10
        $subKey = $enumBase.OpenSubKey($devPath, $true)
        if ($subKey) {
            $flags = $subKey.GetValue('ConfigFlags')
            if ($flags -band 1) {
                $newFlags = $flags -band (-bnot 1)
                $subKey.SetValue('ConfigFlags', $newFlags, [Microsoft.Win32.RegistryValueKind]::DWord)
                Write-Host "Enabled device: $devPath (ConfigFlags $flags -> $newFlags)"
            }
            $subKey.Close(); $subKey.Dispose()
        } else {
            Write-Host "WARNING: Device path not found: $devPath"
        }
    }
    $enumBase.Close(); $enumBase.Dispose()

    Write-Host "Boot device instance fix completed."
} catch {
    Write-Host "Fix boot device failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SYSTEM"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: Re-read the ConfigFlags of the corresponding device instance to confirm bit0 has been cleared

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to clear the disabled flag (ConfigFlags bit0) for specified device instances
- Persistence scope: Survives reboot -- registry changes persist on the target system
- Rollback: Set ConfigFlags bit0 back to 1 (disabled) for the affected device instances in the offline SYSTEM hive. If the instance is completely missing (not disabled), device enumeration records cannot be rebuilt offline; the driver needs to be reinstalled or injected via DISM. Enabling the wrong device may cause resource conflicts
