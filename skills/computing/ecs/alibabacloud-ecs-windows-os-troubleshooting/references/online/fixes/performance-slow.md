# Performance Slow Diagnostic Fix Guide

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Page file not configured

**Fix**:

```powershell
# Enable system-managed automatic page file
$cs = Get-CimInstance Win32_ComputerSystem
$cs | Set-CimInstance -Property @{AutomaticManagedPagefile=$true}
```

**Verification**:

```powershell
(Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile
```

Expected result: Returns True

**Risk notes**:

- **Session impact**: None, requires system reboot to take effect.
- **Persistence scope**: Written to system configuration, persisted across reboots.
- **Rollback command**: `$cs = Get-CimInstance Win32_ComputerSystem; $cs | Set-CimInstance -Property @{AutomaticManagedPagefile=$false}`, then manually configure the page file size.
- **Note**: After enabling automatic page file management, a system reboot is required to take effect. The page file size will be automatically managed by the system.

### Root cause: BCD boot configuration limits processor count

**Fix**:

```powershell
# Remove processor count limit from BCD
bcdedit /deletevalue numproc
bcdedit /deletevalue usebootprocessoronly
```

**Verification**:

```powershell
# Verify BCD configuration
bcdedit /enum | Select-String -Pattern "numproc|usebootprocessoronly"
```

Expected result: No output (configuration has been removed); after reboot, the system will use all available CPUs.

**Risk notes**:

- **Session impact**: None, requires system reboot to take effect.
- **Persistence scope**: Written to BCD configuration, persisted across reboots.
- **Rollback command**: `bcdedit /set numproc <OriginalValue>; bcdedit /set usebootprocessoronly <OriginalValue>`
- **Note**: Modifying BCD configuration requires a system reboot to take effect. If the limit was intentional (e.g., for application compatibility), removing it may cause application issues.

### Root cause: BCD boot configuration truncates memory

**Fix**:

```powershell
# Remove memory truncation configuration from BCD
bcdedit /deletevalue truncatememory
bcdedit /deletevalue removememory
```

**Verification**:

```powershell
# Verify BCD configuration
bcdedit /enum | Select-String -Pattern "truncatememory|removememory"
```

Expected result: No output; after reboot, the system will use all physical memory.

**Risk notes**:

- **Session impact**: None, requires system reboot to take effect.
- **Persistence scope**: Written to BCD configuration, persisted across reboots.
- **Rollback command**: `bcdedit /set truncatememory <OriginalValue>; bcdedit /set removememory <OriginalValue>`
- **Note**: Modifying BCD configuration requires a system reboot to take effect. If memory truncation was set to resolve specific hardware compatibility issues, removing it may cause system instability.

### Root cause: Hyper-threading not enabled

**Fix**:

Hyper-threading is determined by the ECS instance specification and BIOS configuration, and cannot be modified within the operating system. If disabled due to registry mitigation settings:

```powershell
# Remove hyper-threading disable configuration from CPU microarchitecture security mitigations
Remove-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name FeatureSettingsOverride -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name FeatureSettingsOverrideMask -ErrorAction SilentlyContinue
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name FeatureSettingsOverride, FeatureSettingsOverrideMask -ErrorAction SilentlyContinue | Select-Object FeatureSettingsOverride, FeatureSettingsOverrideMask
```

Expected result: Properties do not exist (removed); after reboot, hyper-threading will be restored.

**Risk notes**:

- **Session impact**: None, requires system reboot to take effect.
- **Persistence scope**: After removing registry mitigations, the change is permanent.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' -Name 'FeatureSettingsOverride' -Value <OriginalValue> -Type DWord; Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' -Name 'FeatureSettingsOverrideMask' -Value <OriginalValue> -Type DWord`
- **Note**: After removing CPU microarchitecture security mitigations, the system will no longer have protection against Spectre/Meltdown-class vulnerabilities. Please weigh this against your security requirements. Modification requires a system reboot to take effect.

### Root cause: Power plan set to power-saving mode

**Fix**:

```powershell
# Switch to High Performance power plan
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
```

**Verification**:

```powershell
powercfg /getactivescheme
```

Expected result: Shows High Performance

**Risk notes**:

- **Session impact**: Takes effect immediately; CPU frequency policy switches in real time.
- **Persistence scope**: Power plan switch is permanent, persisted across reboots.
- **Rollback command**: `powercfg /setactive <OriginalPlanGUID>`
- **Note**: Under the High Performance power plan, the CPU always runs at maximum frequency and does not adjust frequency based on load. This has no significant side effects for cloud server scenarios.

### Root cause: Third-party file system filter driver causing system slowdown

> Corresponding diagnostic step: Step 8 (File System Filter Driver Check) - Analysis points 1 and 2

**Fix**:

```powershell
# Check third-party filter driver details (replace <FilterName> with actual name, e.g. CcProtect)
fltmc volumes <FilterName>

# Uninstall the corresponding software via Control Panel or use the vendor's uninstall tool
# If uninstall not possible, try stopping and disabling the driver service:
# sc query <DriverServiceName>
# sc stop <DriverServiceName>
# sc config <DriverServiceName> start= disabled
```

**Verification**:

```powershell
# Verify filter driver has been removed
fltmc filters | Select-String -Pattern "<FilterName>"
```

Expected result: No matching output (filter driver has been removed); file open and program launch speeds return to normal.

**Risk notes**:

- **Session impact**: After stopping the filter driver, the corresponding security software's real-time protection is immediately disabled.
- **Persistence scope**: Disabling the service is permanent; uninstalling the software is a permanent removal.
- **Rollback command**: `sc config <DriverServiceName> start= auto; sc start <DriverServiceName>`, or reinstall the corresponding security software.
- **Note**: Uninstalling security software or disabling its filter driver will reduce system security protection. Only operate after confirming the driver is the root cause of the performance issue. It is recommended to contact the software vendor for an official uninstall tool first.
