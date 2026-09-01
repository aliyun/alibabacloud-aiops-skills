# Storage Disk and Volume Diagnosis

## Overview

Diagnoses the complete chain of issues in the Windows storage stack from physical disk to logical volume. Covers disk online/offline status, SAN policy, dynamic/external disks, UniqueID conflicts, disk capacity consistency, partition table type and 2TB limit, unpartitioned/unallocated space, partition type identification, formatting and mount status, partition extension feasibility, Cluster Size capacity limit, volume space usage, file system health (MFT bloat, CHKDSK errors). Covers 15 known issue items.


**Input**: User problem description (required), error code/event ID/screenshot (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|----------------------|-------------------|
| Newly mounted data disk not visible, disk shows "offline" | Step 1 (disk status and attributes) -> Step 2 (partition table and space allocation) |
| Disk marked as "dynamic" or "external" | Step 1 (disk status and attributes) |
| Data abnormality after mounting multiple cloud disks | Step 1 (disk status and attributes) |
| System volume capacity unchanged after expansion | Step 1 (disk status and attributes) -> Step 2 (partition table and space allocation) |
| MBR disk exceeds 2TB and cannot be used | Step 2 (partition table and space allocation) |
| Partition shows "unknown" or prompts for formatting | Step 3 (partition status and mount) |
| Partition has no drive letter, not visible in "My Computer" | Step 3 (partition status and mount) |
| Extend volume failed | Step 3 (partition status and mount) -> Step 4 (volume capacity and Cluster Size limit) |
| System disk space insufficient, running slowly | Step 5 (volume space usage) |
| Disk performance degraded, MFT too large | Step 6 (file system health) |
| File read/write abnormal, files lost | Step 6 (file system health) |

## Diagnostic Steps

### Step 1: Disk Status and Attribute Check

**Data Collection**:

> Collection target: Obtain online/offline status, health status, partition style, UniqueID, capacity, read-only attributes for all disks, and the current SAN policy configuration. **Important**: `Get-Disk` is based on the Storage Management API and may hide dynamic disks or disks with abnormal status. Therefore, you MUST also use `diskpart list disk` to obtain the full underlying physical disk view, and perform a differential comparison between the two.

- PowerShell script: [storage-disk.ps1](references/online/scripts/storage-disk.ps1) Section Step 1
- Dual verification differential analysis can be based on `GuestOS:Disk` + `GuestOS:Volume` returns for equivalent comparison

**Analysis Approach**:

1. **Dual verification comparison (Part B/C vs Part A)**:
   - Normal: Disk numbers listed by `diskpart list disk` and `Get-Disk` are completely consistent
   - Abnormal: Disks present in `diskpart` but missing in `Get-Disk` -> These disks are likely **dynamic disks** in Foreign/offline/abnormal metadata state
   - Abnormal: A disk marked as **Dyn** in `diskpart` output but not shown or shown as RAW/Unknown in `Get-Disk` -> **Root cause**: Disk is a dynamic disk with possible metadata abnormality/Foreign state, **Severity**: Warning
   - Handling strategy: For disks that `Get-Disk` cannot find, do not mark as "non-existent"; continue tracking their volume status through `Win32_DiskDrive` and `Win32_Volume` in Part C

2. Check disk online status:
   - Normal: All disks are in Online status and not offline
   - Abnormal: Disk is in Offline status -> **Root cause**: Disk offline, **Severity**: Warning
   - Supplementary SAN policy check: If the policy is not OnlineAll, newly mounted disks will be offline by default

3. Check whether the disk is manageable:
   - Normal: Partition style is GPT or MBR (basic disk)
   - Abnormal: Disk type marked as dynamic disk or external disk -> **Root cause**: Disk not manageable (dynamic/external disk), **Severity**: Warning

4. Check for duplicate UniqueID:
   - Normal: All disks have distinct UniqueIDs
   - Abnormal: Two or more disks share the same UniqueID -> **Root cause**: Disk UniqueID conflict, **Severity**: Critical
   - Explanation: UniqueID conflicts are common in Alibaba Cloud ECS scenarios with older VirtIO drivers (drivers that do not correctly pass through disk serial numbers), causing Windows enumeration conflicts; in severe cases, this may lead to data overwrites

5. Check whether disk size is consistent with expectations (requires the user to provide cloud platform disk specifications as reference):
   - Normal: Disk size recognized in-system matches the cloud platform console
   - Abnormal: In-system size is smaller than cloud platform size -> **Root cause**: Disk size mismatch with expectations, **Severity**: Warning
   - Explanation: When the system does not automatically sense the new size after expansion, use `Update-Disk` or diskpart `rescan` to refresh

If the disk is completely unrecognizable or the storage controller has abnormal markings in Device Manager, see -> [storage-hardware.md](references/online/storage-hardware.md)

### Step 2: Partition Table and Space Allocation Check

**Data Collection**:

> Collection target: Obtain partition style, allocated space, unallocated space for each disk, and basic information of all partitions

- PowerShell script: [storage-disk.ps1](references/online/scripts/storage-disk.ps1) Section Step 2

**Analysis Approach**:

1. Check whether the disk is partitioned:
   - Normal: Disk has at least one partition
   - Abnormal: Partition count is 0 and partition style is RAW -> **Root cause**: Disk not partitioned, **Severity**: Warning
   - Explanation: Newly mounted data disks need to be initialized (select GPT or MBR) before creating partitions

2. Check for large amounts of unallocated space:
   - Normal: Allocated space is close to total disk size (difference less than 1GB)
   - Abnormal: More than 1GB of unallocated space -> **Root cause**: Disk has unallocated space, **Severity**: Warning
   - Explanation: Common after cloud disk expansion without extending the partition, or when partition creation did not use all available space

3. Check MBR disk size limit:
   - Normal: MBR disk total size is less than 2TB (2199023255552 bytes)
   - Abnormal: MBR disk greater than or equal to 2TB -> **Root cause**: MBR disk exceeds 2TB limit, **Severity**: Warning
   - Explanation: MBR partition table uses 32-bit LBA addressing, supporting up to 2TB. The excess portion cannot be used for partitioning; conversion to GPT is required

### Step 3: Partition Status and Mount Check

**Data Collection**:

> Collection target: Obtain partition type identification status, file system format, drive letter mount status, maximum extendable size for each partition, and the system auto-mount (automount) status

> **Localization note**: diskpart output language depends on the OS language environment. English systems output "Enabled"/"Disabled"; systems in other languages output the localized equivalents. Interpret the output based on the actual system language during analysis.

- PowerShell script: [storage-disk.ps1](references/online/scripts/storage-disk.ps1) Section Step 3
- Extendable space can be derived from `GuestOS:Partition` partition offset and `GuestOS:Disk` disk size

**Analysis Approach**:

1. Check whether the partition type is recognizable:
   - Normal: Partition type is Basic, IFS, System Reserved, or other known types
   - Abnormal: Partition type is Unknown -> **Root cause**: Partition type not recognizable, **Severity**: Warning
   - Explanation: Common causes are partition table corruption, or the partition uses a file system format not supported by Windows (e.g., Linux ext4/xfs); the latter is normal behavior

2. Check whether the partition is formatted:
   - Normal: The volume associated with the partition has a valid file system such as NTFS/ReFS/FAT32
   - Abnormal: No file system information -> **Root cause**: Partition not formatted, **Severity**: Warning
   - Note: BitLocker encrypted volumes in locked state will also appear as having no file system. If the partition type is Basic and the partition size matches data volume characteristics, see -> [security-bitlocker.md](references/online/security-bitlocker.md)

3. Check whether data partitions are mounted with a drive letter:
   - Normal: Non-system-reserved partitions (non-MSR, non-EFI, non-Recovery) have a drive letter
   - Abnormal: Data partition without a drive letter -> **Root cause**: Partition not mounted (no drive letter), **Severity**: Warning
   - Explanation: System Reserved, MSR, and EFI partitions having no drive letter is by design
   - If there is no drive letter and automount shows disabled, the root cause of the missing drive letter is that auto-mount is turned off; this will recur after every restart
   - If the drive letter exists but the user cannot see it in File Explorer, the drive may be hidden by Group Policy; see -> [system-gpo.md](references/online/system-gpo.md)

4. Check whether the last partition is extendable:
   - Normal: Maximum extendable size is greater than current size
   - Abnormal: Not extendable -> **Root cause**: Last partition cannot be extended, **Severity**: Warning
   - Common causes: A Recovery Partition exists after the partition blocking extension, the file system does not support online extension (e.g., FAT32), or the disk is a dynamic disk

### Step 4: Volume Capacity and Cluster Size Limit Check

**Data Collection**:

> Collection target: Obtain Cluster Size (allocation unit size) and current capacity for all formatted volumes, and assess whether there is an expansion ceiling due to Cluster Size

- PowerShell script: [storage-disk.ps1](references/online/scripts/storage-disk.ps1) Section Step 4

**Analysis Approach**:

1. Check whether the NTFS volume is approaching the maximum capacity limit corresponding to its Cluster Size:
   - NTFS maximum volume capacity = Cluster Size x 232 (i.e., Cluster Size x 4,294,967,296). For example, the default 4KB Cluster Size corresponds to a maximum volume capacity of 16TB

   - Normal: Current volume size is far below the maximum capacity for its Cluster Size
   - Abnormal: Current volume size is at or near the limit; continued expansion will fail -> **Root cause**: Volume Cluster Size limits expansion, **Severity**: Warning
   - Explanation: Windows uses 4KB Cluster Size by default when formatting; this limit should be noted for large-capacity cloud disk (>16TB) expansion scenarios. Cluster Size cannot be modified online; data must be backed up before reformatting

### Step 5: Volume Space Usage Check

**Data Collection**:

> Collection target: Obtain capacity, free space, and usage for all mounted volumes, with focus on the system disk

- PowerShell script: [storage-disk.ps1](references/online/scripts/storage-disk.ps1) Section Step 5

**Analysis Approach**:

1. Check system disk free space:
   - Normal: System disk (typically C:) has more than 1GB of free space
   - Abnormal: Free space less than or equal to 1GB -> **Root cause**: System disk free space insufficient (<=1GB), **Severity**: Warning
   - Explanation: Insufficient system disk space will cause update installation failures, inability to write temporary files, system log recording to stop; in severe cases, the system may not function normally

### Step 6: File System Health Check

**Data Collection**:

> Collection target: Obtain MFT (Master File Table) size for all NTFS volumes, and CHKDSK/Wininit related event logs from the last 7 days

- PowerShell script: [storage-disk.ps1](references/online/scripts/storage-disk.ps1) Section Step 6

**Analysis Approach**:

1. Check MFT size:
   - Normal: MFT size less than 10GB
   - Abnormal: MFT size greater than or equal to 10GB -> **Root cause**: NTFS MFT too large (>=10GB), **Severity**: Warning
   - Explanation: MFT is the core metadata structure of NTFS; each file/directory corresponds to one MFT record. When a volume has had a large number of small files, the MFT will continue to grow; MFT space is not automatically reclaimed after files are deleted. This manifests as abnormal disk free space statistics (total file size is far less than used space)

2. Check CHKDSK and Ntfs event logs:
   - Normal: No CHKDSK error events, no Ntfs warning/error events
   - Abnormal: File system error events present -> **Root cause**: CHKDSK reports file system errors, **Severity**: Warning
   - Explanation: Event ID 55 (file system structure corruption) and Event ID 98 (volume requires online scan) in the Ntfs event log are common file system corruption indicators; determine whether `chkdsk /f` repair is needed based on event details

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|-------------------|-------------|
| Conditional jump | Step 1 finds disk completely unrecognizable or storage controller abnormal | -> [storage-hardware.md](references/online/storage-hardware.md) |
| Conditional jump | Step 1 UniqueID conflict and suspected VirtIO driver version issue | -> [cloud-driver.md](references/online/cloud-driver.md) |
| Conditional jump | Step 3 partition has no file system and suspected BitLocker encrypted volume | -> [security-bitlocker.md](references/online/security-bitlocker.md) |
| Conditional jump | Step 3 partition extension failed and disk is dynamic disk or driver abnormal | -> [storage-hardware.md](references/online/storage-hardware.md) |
| Chain successor | All steps in this file executed, root cause not confirmed | -> [storage-hardware.md](references/online/storage-hardware.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [storage-disk.md](references/online/fixes/storage-disk.md).
