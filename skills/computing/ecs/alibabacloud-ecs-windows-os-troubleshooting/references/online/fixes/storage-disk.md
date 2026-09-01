# Storage Disk and Volume Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Disk offline

**Fix operation**:

```powershell
# Set offline disk to online (replace $diskNum with actual disk number)
$diskNum = <DiskNumber>
Set-Disk -Number $diskNum -IsOffline $false

# If disk is read-only, also clear read-only flag
Set-Disk -Number $diskNum -IsReadOnly $false

# Change SAN policy to OnlineAll to prevent newly attached disks from staying offline
Set-StorageSetting -NewDiskPolicy OnlineAll
```

**Verification**:

```powershell
Get-Disk -Number $diskNum | Select-Object Number, OperationalStatus, IsOffline, IsReadOnly | Format-Table -AutoSize
(Get-StorageSetting).NewDiskPolicy
```

Expected result: OperationalStatus = Online, IsOffline = False, NewDiskPolicy = OnlineAll

**Risk notes**:

- **Session impact**: None; bringing a disk online does not affect existing disks.
- **Persistence scope**: SAN policy change is persistent and survives reboots.
- **Rollback command**: `Set-Disk -Number $diskNum -IsOffline $true; Set-StorageSetting -NewDiskPolicy OfflineShared`
- **Note**: If multiple disks have duplicate UniqueIDs, bringing them online simultaneously may cause Windows to recognize different disks as the same device, posing a data corruption risk. Resolve the UniqueID issue first.

---

### Root cause: Disk unmanageable (dynamic/foreign disk)

**Description**:

Dynamic disks or foreign disks cannot be managed through standard PowerShell commands (`Get-Disk`/`Set-Disk`) and require operations via Disk Management (diskmgmt.msc) or diskpart:
- **Dynamic disk**: If dynamic disk features (spanned volumes, mirrored volumes) is not needed, it is recommended to convert to a basic disk (requires deleting all volumes first, which will lose data)
- **Foreign disk**: Right-click in Disk Management and select "Import Foreign Disk", or use diskpart to import:

```powershell
# Import foreign dynamic disk (replace X with actual disk number)
"select disk X", "online", "import" | diskpart
```

- **Verify import result**: After importing, re-run the dual verification from Step 1 to confirm that `Get-Disk` can now recognize the disk

---

### Root cause: Disk UniqueID duplication

**Fix operation**:

```powershell
# Confirm UniqueID duplication
Get-Disk | Select-Object Number, SerialNumber, UniqueId | Group-Object UniqueId | Where-Object { $_.Count -gt 1 }
```

The root cause is typically that the legacy VirtIO driver does not correctly pass through the disk serial number. The fix is to update the VirtIO driver to the latest version.

**Verification**:

```powershell
# Verify after driver update and reboot
Get-Disk | Select-Object Number, UniqueId | Group-Object UniqueId | Where-Object { $_.Count -gt 1 }
```

Expected result: No output (no duplicate UniqueIDs)

**Risk notes**:

- **Session impact**: None; driver update requires reboot to take effect.
- **Persistence scope**: Persistent after driver update.
- **Rollback command**: Roll back the driver via Device Manager or reinstall the previous driver version.
- **Note**: Updating the VirtIO driver requires rebooting the instance; recommended to operate during a maintenance window.

To check VirtIO driver version and status, refer to the cloud-driver diagnostic section

---

### Root cause: Disk size mismatch with expectation

**Fix operation**:

```powershell
# Rescan disk to refresh disk size information
$diskNum = <DiskNumber>
Update-Disk -Number $diskNum

# Verify refresh result
Get-Disk -Number $diskNum | Select-Object Number, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
```

If `Update-Disk` is ineffective, try the diskpart method:

```powershell
"rescan" | diskpart
```

**Verification**:

```powershell
Get-Disk -Number $diskNum | Select-Object Number, Size, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
```

Expected result: Disk size matches the cloud platform console

**Risk notes**:

- **Session impact**: None; rescan is a read-only operation.
- **Persistence scope**: No persistent changes involved.
- **Rollback command**: No rollback needed.

---

### Root cause: Disk unpartitioned

**Fix operation**:

```powershell
# Initialize disk and create partition (GPT partition style recommended)
$diskNum = <DiskNumber>
Initialize-Disk -Number $diskNum -PartitionStyle GPT

# Create partition and format as NTFS
New-Partition -DiskNumber $diskNum -UseMaximumSize -AssignDriveLetter | Format-Volume -FileSystem NTFS -Confirm:$false
```

**Verification**:

```powershell
Get-Partition -DiskNumber $diskNum | Select-Object PartitionNumber, DriveLetter, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
```

Expected result: Partition created with a drive letter assigned

**Risk notes**:

- **Session impact**: None; initialization only operates on new disks.
- **Persistence scope**: Partition and format are permanent.
- **Rollback command**: No rollback (data will be erased).
- **Note**: Initializing a disk erases all data on the disk; ensure the disk is new or has no important data before operating.

---

### Root cause: Disk has unallocated space

**Fix operation**:

```powershell
# Expand the last partition to maximum available space
$diskNum = <DiskNumber>
$partNum = <PartitionNumber>
$maxSize = (Get-PartitionSupportedSize -DiskNumber $diskNum -PartitionNumber $partNum).SizeMax
Resize-Partition -DiskNumber $diskNum -PartitionNumber $partNum -Size $maxSize
```

**Verification**:

```powershell
Get-Disk -Number $diskNum | Select-Object Number, Size, AllocatedSize, @{N='UnallocatedGB';E={[math]::Round(($_.Size - $_.AllocatedSize)/1GB, 2)}}
```

Expected result: Unallocated space close to 0

**Risk notes**:

- **Session impact**: None; online partition expansion does not interrupt I/O.
- **Persistence scope**: Partition expansion is permanent.
- **Rollback command**: `Resize-Partition -DiskNumber $diskNum -PartitionNumber $partNum -Size <OriginalSize>` (shrinking partitions has limitations).
- **Note**: Partition expansion is an online operation and generally safe, but creating a snapshot backup beforehand is recommended.

---

### Root cause: MBR disk exceeds 2TB limit

**Fix operation**:

```powershell
# MBR to GPT conversion (only data disks support online conversion, system disk does not)
# Windows Server 2019+ can use mbr2gpt
mbr2gpt /convert /disk:<DiskNumber> /allowFullOS
```

**Verification**:

```powershell
Get-Disk -Number <DiskNumber> | Select-Object Number, PartitionStyle, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
```

Expected result: PartitionStyle = GPT

**Risk notes**:

- **Session impact**: None; conversion process does not affect existing data access (when successful).
- **Persistence scope**: Partition table conversion is permanent.
- **Rollback command**: No online rollback (requires backing up data and reinitializing as MBR).
- **Note**: MBR to GPT conversion carries a risk of data loss; data must be backed up before operating. System disk conversion requires a special procedure with additional constraints.

---

### Root cause: Partition type unrecognized

**Description**:

Common causes of unrecognized partition type:
- **Linux partition**: Windows does not natively support read/write for ext4/xfs/btrfs and other Linux file systems; partitions showing as Unknown is normal behavior
- **Partition table corruption**: If an originally Windows partition becomes Unknown, the partition table metadata may be corrupted and a data recovery tool is needed

---

### Root cause: Partition unformatted

**Fix operation**:

```powershell
# Format partition (will erase all data on the partition)
Format-Volume -DriveLetter <DriveLetter> -FileSystem NTFS -Confirm:$false
```

**Verification**:

```powershell
Get-Volume -DriveLetter <DriveLetter> | Select-Object DriveLetter, FileSystem, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
```

Expected result: FileSystem = NTFS

**Risk notes**:

- **Session impact**: None; formatting only affects the target partition.
- **Persistence scope**: Formatting is permanent.
- **Rollback command**: No rollback (data will be erased).
- **Note**: Formatting erases all data on the partition; confirm there is no important data on the partition before operating.

---

### Root cause: Partition unmounted (no drive letter)

**Fix operation**:

```powershell
# 1. Assign drive letter to partition
$diskNum = <DiskNumber>
$partNum = <PartitionNumber>
$letter = '<DriveLetter>'
Set-Partition -DiskNumber $diskNum -PartitionNumber $partNum -NewDriveLetter $letter

# 2. If automount is disabled, enable auto-mount (prevent drive letter loss after reboot)
"automount enable" | diskpart
```

**Verification**:

```powershell
Get-Partition -DiskNumber $diskNum -PartitionNumber $partNum | Select-Object DriveLetter
"automount" | diskpart
```

Expected result: DriveLetter is the specified drive letter, automount shows enabled

**Risk notes**:

- **Session impact**: None; assigning a drive letter takes effect immediately with no side effects.
- **Persistence scope**: Drive letter assignment and automount setting are persistent and survive reboots.
- **Rollback command**: `Remove-PartitionAccessPath -DiskNumber $diskNum -PartitionNumber $partNum -AccessPath '<DriveLetter>:'`
- **Note**: Assigning a drive letter and enabling automount carry no risk, but ensure the target drive letter is not already in use.

---

### Root cause: Last partition cannot be expanded

**Description**:

Common causes and handling methods for the last partition not being expandable:

- **Recovery partition behind the partition**: A Recovery Partition is located at the end of the disk, blocking the data partition from expanding backward. The recovery partition must be deleted or moved first, then the target partition can be expanded
- **File system does not support online expansion**: FAT32 does not support online expansion; must convert to NTFS first (`convert <DriveLetter>: /fs:ntfs`)
- **Disk is a dynamic disk**: Volume expansion behavior on dynamic disks is different and must be operated via Disk Management

```powershell
# View partition layout to confirm if recovery partition is blocking expansion
Get-Partition -DiskNumber <DiskNumber> | Sort-Object Offset | Select-Object PartitionNumber, Type, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}, Offset
```

---

### Root cause: Volume Cluster Size limiting expansion

**Description**:

The maximum capacity of an NTFS volume is limited by the Cluster Size (allocation unit size): Maximum volume capacity = Cluster Size x 2^32. Windows uses the default 4KB Cluster Size during formatting, corresponding to a maximum volume capacity of 16TB.

When the total capacity after cloud disk expansion exceeds the limit corresponding to the Cluster Size, the volume expansion operation will fail.

```powershell
# Confirm current volume Cluster Size
Get-Volume -DriveLetter <DriveLetter> | Select-Object DriveLetter, FileSystem, AllocationUnitSize, @{N='ClusterSizeKB';E={$_.AllocationUnitSize/1KB}}, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
```

**Solution**: Cluster Size cannot be modified online. You need to back up data -> reformat with a larger Cluster Size -> restore data.

**Risk notes**:

- **Session impact**: None; reformatting requires offline operation.
- **Persistence scope**: Formatting is permanent.
- **Rollback command**: No rollback (requires backing up data and reformatting).
- **Note**: A larger Cluster Size increases storage space waste for small files (each file occupies at least one Cluster)

---

### Root cause: System disk free space insufficient (<=1GB)

**Fix operation**:

```powershell
# 1. Check temporary file usage
Get-ChildItem -Path C:\Windows\Temp -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum
Get-ChildItem -Path $env:TEMP -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum

# 2. Clean Windows Update cache
Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Windows\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
Start-Service -Name wuauserv

# 3. Run disk cleanup (interactive)
cleanmgr /d C
```

**Verification**:

```powershell
Get-Volume -DriveLetter C | Select-Object DriveLetter, @{N='FreeGB';E={[math]::Round($_.SizeRemaining/1GB, 2)}}
```

Expected result: Free space greater than 1GB

**Risk notes**:

- **Session impact**: None; cleanup operations do not affect existing business processes.
- **Persistence scope**: File deletion is permanent.
- **Rollback command**: Cannot roll back deleted temporary files.
- **Note**: Cleaning temporary files is generally safe. Cleaning the Windows Update cache will cause downloaded but uninstalled updates to be re-downloaded.

---

### Root cause: NTFS MFT too large (>=10GB)

**Description**:

MFT (Master File Table) is the core metadata structure of the NTFS file system. Each file and directory corresponds to one record in the MFT. When a large number of small files have been created on a volume, the MFT continues to grow. Even after files are deleted, the disk space occupied by the MFT is not automatically reclaimed.

Impact of an oversized MFT:
- Disk space statistics anomaly (actual total file size is much smaller than the used space on the volume)
- File operation performance degradation

There is currently no safe online MFT shrink method. Available options:
1. Back up data -> format the volume -> restore data (MFT will be rebuilt at a reasonable size)
2. If the business impact is minimal, this alert can be ignored

---

### Root cause: CHKDSK reports file system errors

**Fix operation**:

```powershell
# Step 1: Read-only scan to assess filesystem state (does not modify any data)
chkdsk <DriveLetter>: /scan

# Step 2: If read-only scan confirms errors, perform repair (requires exclusive volume access)
# Data disks can be repaired directly; system disk repair will be scheduled at next reboot
# chkdsk <DriveLetter>: /f
```

**Verification**:

```powershell
# Filter ProviderName in FilterHashtable directly: the Application log is
# high-volume, so "latest N + filter afterwards" returns nothing.
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Chkdsk','Wininit'; StartTime=(Get-Date).AddDays(-1)} -MaxEvents 5 -ErrorAction SilentlyContinue | Select-Object TimeCreated, Id, Message
```

Expected result: CHKDSK completion event reports no errors

**Risk notes**:

- **Session impact**: `chkdsk /scan` has no impact; `chkdsk /f` requires exclusive volume access, and the system disk will execute at next reboot.
- **Persistence scope**: Fix results are permanent.
- **Rollback command**: Cannot roll back file system fixes.
- **Note**: `chkdsk /scan` is a read-only operation and is safe with no risk. `chkdsk /f` may cause data loss if power is interrupted during the repair process.
