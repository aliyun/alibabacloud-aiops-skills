# System Configuration and Service Diagnosis Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: System PATH environment variable tampered

**Fix**: Append missing system PATH entries via offline registry operations

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

    $envKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        "$currentControlSet\Control\Session Manager\Environment", $true)
    if (-not $envKey) { throw "Cannot open Environment key" }

    $currentPath = $envKey.GetValue('Path', '')
    Write-Host "Current PATH: $currentPath"

    # Check and append missing paths
    $required = @(
        '%SystemRoot%',
        '%SystemRoot%\System32',
        '%SystemRoot%\System32\Wbem',
        '%SystemRoot%\System32\WindowsPowerShell\v1.0'
    )
    $pathLower = $currentPath.ToLower()
    $missing = @()
    foreach ($req in $required) {
        if ($pathLower -notlike "*$($req.ToLower())*") {
            $missing += $req
        }
    }

    if ($missing.Count -gt 0) {
        $newPath = ($currentPath.TrimEnd(';') + ';' + ($missing -join ';'))
        $envKey.SetValue('Path', $newPath, [Microsoft.Win32.RegistryValueKind]::ExpandString)
        Write-Host "PATH updated, added: $($missing -join ', ')"
    } else {
        Write-Host "All required paths present."
    }
    $envKey.Close(); $envKey.Dispose()
} catch {
    Write-Host "Fix PATH failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SYSTEM"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Risk notes**: Low risk. Only appends missing standard paths without removing existing entries; if the user has custom PATH ordering dependencies, the append operation will not break the original order

### Root cause: Crash dump not enabled

**Fix**: Enable Automatic Memory Dump (CrashDumpEnabled=7)

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"

# CrashDumpEnabled values:
# 0: Disabled
# 1: Complete memory dump
# 2: Kernel memory dump
# 3: Small memory dump (64KB)
# 7: Automatic memory dump (recommended)
$type = 7
$exitCode = 0

try {
    Write-Host "Loading SYSTEM registry hive..."
    & reg load "HKLM\_SYSTEM" $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    if (-not $select) { throw "Unable to open _SYSTEM\Select" }
    $currentControlSet = "_SYSTEM\ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()
    Write-Host "Current control set: $currentControlSet"

    Write-Host "Setting CrashDumpEnabled to $type..."
    $crashControlBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        "$currentControlSet\Control\CrashControl", $true)
    if (-not $crashControlBase) { throw "Cannot open CrashControl key" }
    $crashControlBase.SetValue('CrashDumpEnabled', $type, [Microsoft.Win32.RegistryValueKind]::DWord)
    $crashControlBase.Close(); $crashControlBase.Dispose()

    Write-Host "CrashDump enabled successfully."
} catch {
    Write-Host "Enable CrashDump failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SYSTEM"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Risk notes**: Low risk. Enabling crash dump only modifies the CrashControl registry value and does not affect system boot; it may increase disk space usage (dump file size depends on memory size)

### Root cause: IFEO stack commit size too large

**Fix**: Delete the abnormal MinimumStackCommitInBytes value

```powershell
$bootLetter = '<BootLetter>'
$softHive = "${bootLetter}:\Windows\System32\config\SOFTWARE"
$exitCode = 0

# Input: list of process names found in diagnostic steps
$processNames = @('<ProcessName1>', '<ProcessName2>')

try {
    & reg load "HKLM\_SOFTWARE" $softHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SOFTWARE hive." }

    $ifeoBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        "_SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options", $true)
    if (-not $ifeoBase) { throw "Cannot open IFEO key" }

    foreach ($name in $processNames) {
        $subKey = $ifeoBase.OpenSubKey($name, $true)
        if ($subKey) {
            $val = $subKey.GetValue('MinimumStackCommitInBytes')
            if ($null -ne $val) {
                Write-Host "Removing MinimumStackCommitInBytes from $name (was 0x$($val.ToString('X')))"
                $subKey.DeleteValue('MinimumStackCommitInBytes')
            }
            $subKey.Close(); $subKey.Dispose()
        }
    }
    $ifeoBase.Close(); $ifeoBase.Dispose()

    Write-Host "IFEO fix completed."
} catch {
    Write-Host "Fix IFEO failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SOFTWARE"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Risk notes**: Low risk. Removing the abnormal MinimumStackCommitInBytes restores the process default stack behavior; only affects the target processes and does not impact system boot

### Root cause: Sysprep unrecoverable error

**Fix**: Cannot be recovered via offline fix; it is recommended to replace the system image and recreate the instance

**Risk notes**: Not applicable (no offline fix available); it is recommended that the user back up data and rebuild the instance

### Root cause: BootExecute abnormal entry references a non-existent program

**Fix**: Remove abnormal entries pointing to missing programs and restore to only the standard autochk

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

    $smKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        "$currentControlSet\Control\Session Manager", $true)
    if (-not $smKey) { throw "Cannot open Session Manager key" }

    $bootExec = $smKey.GetValue('BootExecute')
    Write-Host "Current BootExecute: $($bootExec -join '; ')"

    # Filter: keep standard entries + entries with existing files
    $standard = @('autocheck autochk *')
    $kept = @()
    $removed = @()
    foreach ($entry in $bootExec) {
        $trimmed = $entry.Trim()
        if ($trimmed -eq '' -or $standard -contains $trimmed) {
            $kept += $trimmed
            continue
        }
        $exeName = ($trimmed -split '\s+')[0]
        $exePath = "${bootLetter}:\Windows\System32\$exeName"
        if (-not $exePath.EndsWith('.exe')) { $exePath += '.exe' }
        if (Test-Path $exePath -ErrorAction SilentlyContinue) {
            $kept += $trimmed
        } else {
            $removed += $trimmed
        }
    }

    if ($removed.Count -gt 0) {
        Write-Host "Removing entries: $($removed -join '; ')"
        $smKey.SetValue('BootExecute', $kept, [Microsoft.Win32.RegistryValueKind]::MultiString)
        Write-Host "BootExecute updated."
    } else {
        Write-Host "No missing-binary entries found."
    }
    $smKey.Close(); $smKey.Dispose()
} catch {
    Write-Host "Fix BootExecute failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SYSTEM"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**:

```powershell
& reg load "HKLM\_SYSTEM" "${bootLetter}:\Windows\System32\config\SYSTEM"
$select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
$currentControlSet = "_SYSTEM\ControlSet00$($select.GetValue('Current'))"
$select.Close(); $select.Dispose()
$smKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("$currentControlSet\Control\Session Manager", $false)
$smKey.GetValue('BootExecute')
$smKey.Close(); $smKey.Dispose()
[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()
& reg unload "HKLM\_SYSTEM"
```

Expected result: only `autocheck autochk *` and entries whose binary files are confirmed to exist

**Risk notes**: Removing BootExecute entries may cause related boot-time programs to no longer run (e.g., third-party disk checkers). Only entries whose files do not exist are removed to ensure safety.

### Root cause: CcProtect abnormal service

**Fix**: Disable the CcProtect service or remove the service entry from the registry

**Option 1: Set start mode to Disabled (4)**

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

    $svcKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        "$currentControlSet\Services\CcProtect", $true)
    if ($svcKey) {
        Write-Host "Setting CcProtect Start=4 (Disabled)"
        $svcKey.SetValue('Start', 4, [Microsoft.Win32.RegistryValueKind]::DWord)
        $svcKey.Close(); $svcKey.Dispose()
    } else {
        Write-Host "CcProtect service not found."
    }

    Write-Host "CcProtect disabled."
} catch {
    Write-Host "Fix CcProtect failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SYSTEM"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Option 2: Remove the CcProtect service entry from the registry**

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

    $servicesBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        "$currentControlSet\Services", $true)

    if ($servicesBase.GetSubKeyNames() -contains 'CcProtect') {
        Write-Host "Removing CcProtect service key"
        $servicesBase.DeleteSubKeyTree('CcProtect')
    } else {
        Write-Host "CcProtect service not found."
    }
    $servicesBase.Close(); $servicesBase.Dispose()

    Write-Host "CcProtect service removed."
} catch {
    Write-Host "Remove CcProtect failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SYSTEM"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: Re-read `Services\CcProtect` under the active ControlSet to confirm the key does not exist or Start=4

**Risk notes**: If the system does depend on this driver, disabling or removing it may cause related software to malfunction. It is recommended to confirm with the user whether they are aware of the software's purpose before proceeding.

### Root cause: Auto-Start service with Critical/Severe error control level

**Fix**: Lower the ErrorControl of the problematic service to Normal (1)

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

# Input: list of problematic service names found in diagnostic steps
$serviceNames = @('<ServiceName1>', '<ServiceName2>')

try {
    & reg load "HKLM\_SYSTEM" $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    $currentControlSet = "_SYSTEM\ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    $servicesBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        "$currentControlSet\Services", $true)

    foreach ($name in $serviceNames) {
        $svcKey = $servicesBase.OpenSubKey($name, $true)
        if ($svcKey) {
            $ec = $svcKey.GetValue('ErrorControl')
            if ($ec -ge 2) {
                Write-Host "Setting $name ErrorControl from $ec to 1 (Normal)"
                $svcKey.SetValue('ErrorControl', 1, [Microsoft.Win32.RegistryValueKind]::DWord)
            }
            $svcKey.Close(); $svcKey.Dispose()
        }
    }
    $servicesBase.Close(); $servicesBase.Dispose()

    Write-Host "ErrorControl fix completed."
} catch {
    Write-Host "Fix ErrorControl failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SYSTEM"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Risk notes**: Medium risk. After lowering ErrorControl, a service startup failure will no longer trigger a BSOD/rollback but will be silently ignored; if the service is boot-critical (e.g., a storage stack service), a failure may cause system functionality issues without any error. It is recommended to only apply this to entries that are clearly third-party services

### Root cause: Boot-Start third-party driver file missing / Boot-Start third-party driver abnormal

**Applicable root causes**: BootStartDriverMissing / BootStartThirdPartyDriver

**Fix**: Offline disable the problematic service (set Start to 4 Disabled)

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

# Input: list of suspect third-party Boot/System-Start service names found in Step 13
$serviceNames = @('<ServiceName1>', '<ServiceName2>')

try {
    & reg load "HKLM\_SYSTEM" $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    $currentControlSet = "_SYSTEM\ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    $servicesBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        "$currentControlSet\Services", $true)

    foreach ($name in $serviceNames) {
        $svcKey = $servicesBase.OpenSubKey($name, $true)
        if ($svcKey) {
            $start = $svcKey.GetValue('Start')
            if ($start -eq 0 -or $start -eq 1) {
                Write-Host "Setting $name Start from $start to 4 (Disabled)"
                $svcKey.SetValue('Start', 4, [Microsoft.Win32.RegistryValueKind]::DWord)
            }
            $svcKey.Close(); $svcKey.Dispose()
        }
    }
    $servicesBase.Close(); $servicesBase.Dispose()

    Write-Host "Boot-start third-party driver fix completed."
} catch {
    Write-Host "Fix boot-start driver failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload "HKLM\_SYSTEM"
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: Re-read the corresponding service key under the active ControlSet to confirm Start=4; detach the disk and start the instance to verify recovery

**Risk notes**: Medium risk. After disabling a Boot/System-Start third-party driver the system will no longer load it; if system functionality depends on that driver (e.g., a storage filter driver) it may trigger a new boot failure; only apply to third-party entries confirmed in Step 13, and it is recommended that the user confirm the software the driver belongs to before proceeding. If recovery is needed after disabling, set Start back to the original value (0/1)
