# Network Configuration Diagnosis Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Network adapter driver not installed

**Fix**: Add netkvm driver via DISM (refer to the driver fix recommendations in the same directory)

### Root cause: Default network adapter disabled

**Fix**: Clear the disabled bit (bit0) of ConfigFlags for the disabled network adapter device instance to re-enable it:

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    # Input: DeviceInstanceID of the disabled VirtIO NIC found in Step 2
    $devIds = @('<DeviceInstanceID1>')
    $enumBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Enum", $true)
    foreach ($id in $devIds) {
        $devKey = $enumBase.OpenSubKey($id, $true)
        if ($devKey) {
            $flags = $devKey.GetValue('ConfigFlags')
            if ($flags -band 1) {
                $newFlags = $flags -band (-bnot 1)
                $devKey.SetValue('ConfigFlags', $newFlags, [Microsoft.Win32.RegistryValueKind]::DWord)
                Write-Host "Enabled: $id (ConfigFlags $flags -> $newFlags)"
            }
            $devKey.Close(); $devKey.Dispose()
        } else {
            Write-Host "Not found: $id"
        }
    }
    $enumBase.Close(); $enumBase.Dispose()
} catch {
    Write-Host "Enable NIC failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: Re-read the ConfigFlags of the corresponding device instance and confirm bit0 has been cleared

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to clear the disabled flag (ConfigFlags bit0) for the specified network adapter
- Persistence scope: Survives reboot -- the NIC will rejoin binding on next boot
- Rollback: Set ConfigFlags bit0 back to 1 (disabled) for the affected device instance in the offline SYSTEM hive

### Root cause: Static IP configuration inconsistent with VPC

**Fix**:

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    # Input: Interface GUID of the affected NIC.
    # On a running system, use: Get-NetAdapter | Select-Object Name, InterfaceGuid, InterfaceIndex
    # On the offline hive, enumerate Tcpip\Parameters\Interfaces subkeys and match by adapter name or IP.
    $interfaceGuid = '<InterfaceGuid>'  # e.g. {a1b2c3d4-e5f6-7890-abcd-ef1234567890}
    $ifacePath = "HKLM:\_SYSTEM\${csName}\Services\Tcpip\Parameters\Interfaces\$interfaceGuid"
    # Switch to DHCP
    Set-ItemProperty $ifacePath -Name EnableDHCP -Value 1
    Write-Host "Switched to DHCP: $ifacePath"
} catch {
    Write-Host "Switch to DHCP failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: Check network connectivity after boot

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to switch the affected NIC from static IP to DHCP
- Persistence scope: Survives reboot -- the DHCP configuration persists on the target system
- Rollback: Set `EnableDHCP` back to 0 and restore the original IP address, subnet mask, and gateway values in the interface's Tcpip\Parameters\Interfaces key. If user services depend on a fixed IP (e.g., whitelists, DNS records), they must be reconfigured after recovery

### Root cause: Network filter driver residue

**Fix**: Remove driver names from UpperFilters/LowerFilters whose service files do not exist

**Risk notes**:
- Session impact: Removes filter driver entries from the offline SYSTEM registry hive for NIC instances where the corresponding .sys files are missing
- Persistence scope: Survives reboot -- registry changes persist on the target system
- Rollback: Re-add the removed filter driver names to UpperFilters/LowerFilters in the offline SYSTEM hive. Removing filter drivers may cause related security software or network management tools to stop functioning properly; only entries whose corresponding .sys files are missing are removed to ensure safety

### Root cause: Non-VirtIO virtual NIC residue

**Applicable root cause**: NonVirtioNicPresent

**Fix**: Offline disable residual non-VirtIO NIC devices (set ConfigFlags under Enum for the corresponding devices to 1 = CONFIGFLAG_DISABLED)

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    # Input: DeviceInstanceID list of non-VirtIO NICs found in Step 5
    $devIds = @('<DeviceInstanceID1>', '<DeviceInstanceID2>')
    $enumBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Enum", $true)
    foreach ($id in $devIds) {
        $devKey = $enumBase.OpenSubKey($id, $true)
        if ($devKey) {
            $devKey.SetValue('ConfigFlags', 1, [Microsoft.Win32.RegistryValueKind]::DWord)
            Write-Host "Disabled: $id"
            $devKey.Close(); $devKey.Dispose()
        } else {
            Write-Host "Not found: $id"
        }
    }
    $enumBase.Close(); $enumBase.Dispose()
} catch {
    Write-Host "Disable non-VirtIO NIC failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Verification**: After boot, check Device Manager and `Get-NetAdapter` to confirm residual NICs are disabled and the VirtIO NIC obtains an IP normally; network connectivity is restored

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to set ConfigFlags to 1 (disabled) for non-VirtIO NIC device instances
- Persistence scope: Survives reboot -- the disabled NICs remain disabled on next boot
- Rollback: Set ConfigFlags back to 0 for the affected device instances in the offline SYSTEM hive to re-enable the NIC. If a NIC actually in use was mistakenly disabled, setting its ConfigFlags back to 0 restores it
