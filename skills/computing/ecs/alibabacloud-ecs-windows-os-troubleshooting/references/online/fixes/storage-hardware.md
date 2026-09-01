# Storage Hardware and Drivers Diagnostic Fix Plan

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: SCSI Controller Status Abnormal

**Fix operation**:

```powershell
# Rescan devices
pnputil /scan-devices
```

**Verification**:

```powershell
Get-PnpDevice -Class SCSIAdapter | Select-Object FriendlyName, Status
```

Expected result: All SCSI controllers show OK status

**Risk notes**:

- **Session impact**: None, rescanning is a read-only operation.
- **Persistence scope**: No persistent changes involved.
- **Rollback command**: No rollback needed.
- **Note**: If the controller hardware or driver has issues, rescanning may not resolve them. You may need to update the driver or contact cloud platform support.

---

### Root cause: SCSI Controller Has No Associated Disks

**Fix operation**:

```powershell
# Rescan disks
"rescan" | diskpart

# Rescan devices
pnputil /scan-devices
```

**Verification**:

```powershell
Get-Disk | Select-Object Number, FriendlyName, OperationalStatus
```

Expected result: Disks associated with the controller appear in the disk list

**Risk notes**:

- **Session impact**: None, rescanning is a read-only operation.
- **Persistence scope**: No persistent changes involved.
- **Rollback command**: No rollback needed.
- **Note**: If the cloud platform side disk mount is normal but still not visible in the system, it may be a driver issue.

---

### Root cause: Disk Drive Status Abnormal

**Fix operation**:

```powershell
# Re-enable abnormal disk devices (operate one by one to avoid accidentally affecting system disk)
# Replace <InstanceId> with the abnormal device instance ID confirmed during diagnosis
$instanceId = '<InstanceId>'
Disable-PnpDevice -InstanceId $instanceId -Confirm:$false
Enable-PnpDevice -InstanceId $instanceId -Confirm:$false
```

**Verification**:

```powershell
Get-PnpDevice -Class DiskDrive | Select-Object FriendlyName, Status
```

Expected result: All disk devices show OK status

**Risk notes**:

- **Session impact**: Disabling and re-enabling disk devices will cause brief disk unavailability.
- **Persistence scope**: Persists after enabling, retained across reboot.
- **Rollback command**: `Disable-PnpDevice -InstanceId '<InstanceId>' -Confirm:$false`
- **Note**: Do not perform this operation on the system disk.

---

### Root cause: Residual Filter Drivers in Registry

**Fix operation**:

```powershell
# View residual filter drivers (first confirm which device instances have issues)
# Delete device instance-level residual filter drivers (replace <InstanceId> with actual value)
$path = "HKLM:\SYSTEM\CurrentControlSet\Enum\<InstanceId>"

# View current values
Get-ItemProperty -Path $path -Name UpperFilters, LowerFilters -ErrorAction SilentlyContinue | Select-Object UpperFilters, LowerFilters

# Delete residual filter drivers (caution: confirm they are residual items)
# Remove-ItemProperty -Path $path -Name UpperFilters -ErrorAction SilentlyContinue
# Remove-ItemProperty -Path $path -Name LowerFilters -ErrorAction SilentlyContinue
```

**Verification**:

Check disk status after reboot:

```powershell
Get-Disk | Select-Object Number, OperationalStatus
```

Expected result: Disk status normal

**Risk notes**:

- **Session impact**: None, registry changes require reboot to take effect.
- **Persistence scope**: Written to registry, retained across reboot.
- **Rollback command**: Restore original UpperFilters/LowerFilters values and reboot.
- **Note**: Deleting a filter driver that is in use may cause disk inaccessibility or BSOD. It is recommended to create a system restore point before performing this operation.

---

### Root cause: Disk Class Driver Not Found

**Fix operation**:

```powershell
# Reinstall disk class driver (VirtIO/SCSI controller driver)
# Scan for hardware changes to trigger driver re-detection
pnputil /scan-devices

# If scan does not resolve, force reinstall the storage controller driver
# First, identify the problematic storage controller
Get-PnpDevice -Class SCSIAdapter -ErrorAction SilentlyContinue | Where-Object { $_.Status -ne 'OK' } | Select-Object InstanceId, FriendlyName, Status | Format-Table -AutoSize

# Disable and re-enable the storage controller to trigger driver reload
$controller = Get-PnpDevice -Class SCSIAdapter -ErrorAction SilentlyContinue | Where-Object { $_.Status -ne 'OK' } | Select-Object -First 1
if ($controller) {
    Disable-PnpDevice -InstanceId $controller.InstanceId -Confirm:$false
    Start-Sleep -Seconds 2
    Enable-PnpDevice -InstanceId $controller.InstanceId -Confirm:$false
}
```

**Verification**:

```powershell
Get-Disk | Select-Object Number, OperationalStatus, HealthStatus
Get-PnpDevice -Class SCSIAdapter -ErrorAction SilentlyContinue | Select-Object FriendlyName, Status | Format-Table -AutoSize
```

Expected result: Disk status normal, SCSI controllers show OK status

**Risk notes**:

- **Session impact**: Reinstalling the driver may cause brief disk offline.
- **Persistence scope**: Persists after driver reinstallation, retained across reboot.
- **Rollback command**: Roll back to the previous driver version or use the cloud platform driver repair tool to restore.
- **Note**: For cloud servers, if the VirtIO driver is abnormal, you may need to use the cloud platform's driver repair tool or reinstall the instance to resolve the issue.

---

### Root cause: Disk Class Filter Driver Abnormal

**Fix operation**:

```powershell
# View current class filter drivers
$diskPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e967-e325-11ce-bfc1-08002be10318}"
Get-ItemProperty -Path $diskPath -Name UpperFilters, LowerFilters -ErrorAction SilentlyContinue | Select-Object UpperFilters, LowerFilters

# Remove abnormal filter drivers (only remove confirmed residual items, keep standard filter drivers partmgr, EhStorClass)
# Example: suppose need to remove "badfilter"
# $current = (Get-ItemProperty -Path $diskPath -Name UpperFilters).UpperFilters
# $new = $current | Where-Object { $_ -ne 'badfilter' }
# Set-ItemProperty -Path $diskPath -Name UpperFilters -Value $new
```

**Verification**:

Check disk status after reboot:

```powershell
Get-Disk | Select-Object Number, OperationalStatus | Format-Table -AutoSize
Get-PnpDevice -Class DiskDrive | Select-Object FriendlyName, Status | Format-Table -AutoSize
```

Expected result: Disk and device status normal

**Risk notes**:

- **Session impact**: None, registry changes require reboot to take effect.
- **Persistence scope**: Written to registry, retained across reboot.
- **Rollback command**: Restore original UpperFilters/LowerFilters values and reboot.
- **Note**: Modifying class-level filter drivers affects all devices of the same class. Before proceeding, make sure to confirm that the items to be deleted are residual. A reboot is required after modification.

---

### Root cause: Non-Standard Filter Drivers Present

**Note**:

Non-Windows standard filter drivers were detected, typically installed by third-party storage management software (such as antivirus software, encryption software, disk caching software). If the service status is normal, it generally does not affect disk functionality, but may increase I/O latency or introduce compatibility issues.

Recommendations:
- Confirm the source and purpose of non-standard filter drivers
- If they are residual from uninstalled software, clean them up following the method in "Disk Class Filter Driver Abnormal"
- If they are from software currently in use, evaluate whether they need to be retained

---

### Root cause: Standard Filter Drivers Missing

**Fix operation**:

```powershell
# Restore standard filter drivers (using DiskDrive class as example)
$diskPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e967-e325-11ce-bfc1-08002be10318}"

# Set correct standard filter drivers according to OS version
# Windows 8/Server 2012 and above: UpperFilters = partmgr, LowerFilters = EhStorClass
# Windows 7/Server 2008 R2: UpperFilters = partmgr, LowerFilters empty
Set-ItemProperty -Path $diskPath -Name UpperFilters -Value @('partmgr')
# Set-ItemProperty -Path $diskPath -Name LowerFilters -Value @('EhStorClass')  # Win8+
```

**Verification**:

Check disk status after reboot:

```powershell
Get-Disk | Select-Object Number, OperationalStatus
```

Expected result: Disk status normal

**Risk notes**:

- **Session impact**: None, registry changes require reboot to take effect.
- **Persistence scope**: Written to registry, retained across reboot.
- **Rollback command**: Remove the added standard filter drivers and reboot (not recommended).
- **Note**: Restoring standard filter drivers is generally safe, but a reboot is required for the changes to take effect.

---

### Root cause: VirtIO Storage Driver Internal Error (Event ID 11)

**Fix operation**:

```powershell
# Check current VirtIO storage driver version (best package in DriverStore;
# PnP selects the active one at boot, do not read the loaded .sys version)
Get-PnpDevice -Class SCSIAdapter | Where-Object { $_.FriendlyName -like '*VirtIO*' } | Select-Object FriendlyName, Service | Format-Table -AutoSize
Get-WindowsDriver -Online -ErrorAction SilentlyContinue |
  Where-Object { $_.OriginalFileName -match '(?i)(viostor|vioscsi)\.inf$' } |
  Group-Object { Split-Path $_.OriginalFileName -Leaf } |
  ForEach-Object {
    $_.Group | Sort-Object @{e={ if ($_.Version -as [version]) { [version]$_.Version } else { [version]'0.0.0' } }} -Descending | Select-Object -First 1
  } |
  Select-Object OriginalFileName, Version, Date | Format-Table -AutoSize
```

**Verification**:

After updating the driver, monitor for 7 days to see if Event ID 11 recurs:

```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='disk'; Id=11; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 5 -ErrorAction SilentlyContinue
```

Expected result: No Event ID 11 events

**Risk notes**:

- **Session impact**: None, driver updates require reboot to take effect.
- **Persistence scope**: Persists after driver update.
- **Rollback command**: Roll back the driver via Device Manager or reinstall the previous driver version.
- **Note**: Updating the VirtIO driver requires rebooting the instance.

---

### Root cause: Disk Device Removal Failed (Event 225)

**Note**:

Event ID 225 indicates that the PnP manager cannot safely remove the device, typically occurring when hot-detaching a cloud disk. Common causes:
- A process is still accessing files or directories on the disk
- A volume on the disk is still mounted
- Third-party software (such as antivirus or backup software) holds a handle to the disk

Recommendations before detaching a cloud disk:
1. Close all programs accessing the disk
2. Set the disk offline in Disk Management first
3. Then detach it from the cloud platform console
