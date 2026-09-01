# Disk Partition Identification and Attribute Verification

## Function Description

Identify boot mode (UEFI/BIOS), locate boot partition and system partition, verify partition attributes (size, file system, ACL, physical parameters).

**Input**: Partition list (with drive letters) output by environment.md
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

This file contains 5 diagnostic steps, **all recommended to be executed** (partition identification is the foundation for all subsequent diagnosis).

| User Problem Phenomenon | Recommended Steps |
|------------------------|-------------------|
| Any boot failure | Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5 |
| Disk/partition related BSOD | Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5 |
| Permission related abnormality | Step 1 -> Step 2 -> Step 3 -> Step 5 |

## Diagnostic Steps

### Step 1: Boot Mode Determination

**Data Collection**:

> Collection target: Determine disk partition table type and ESP partition existence, determine boot mode

```powershell
$diskNum = <TargetDiskNumber>
Get-Disk -Number $diskNum | Format-Table Number, PartitionStyle -AutoSize
Get-Partition -DiskNumber $diskNum | Format-Table PartitionNumber, DriveLetter, Size, Type, IsActive -AutoSize
```

**Analysis Approach**:

1. Determine boot mode:
   - UEFI: PartitionStyle=GPT **and** a partition with Type=System (ESP) exists
   - BIOS: PartitionStyle=MBR (including MBR without active partition; missing active is reported by Step 3)
   - GPT but no ESP partition: Still treat as **UEFI** (GPT disks do not have a BIOS+active boot form), MUST NOT fall back to BIOS criteria; the root cause of missing ESP is reported by Step 3 UEFI branch as "Missing ESP partition" (Critical), and must not be misreported as "Active flag not set"
2. Record the boot mode; subsequent steps depend on this conclusion

**[CTX] Session Memory Backfill** (not displayed to user): Based on the above determination result, record `<BootMode>` as the literal value `UEFI` or `BIOS`.

### Step 2: Identify Boot Partition

**Data Collection**:

> Collection target: Traverse each partition's root directory to find the partition containing Windows system files

```powershell
$diskNum = <TargetDiskNumber>
Get-Partition -DiskNumber $diskNum | Where-Object { $_.DriveLetter } | ForEach-Object {
    $letter = $_.DriveLetter
    $root = "${letter}:\"
    $hasWindows = Test-Path "${root}Windows" -PathType Container
    $hasProgramData = Test-Path "${root}ProgramData" -PathType Container
    $hasSystem32 = Test-Path "${root}Windows\System32" -PathType Container
    [PSCustomObject]@{
        DriveLetter = $letter
        HasWindows = $hasWindows
        HasProgramData = $hasProgramData
        HasSystem32 = $hasSystem32
        IsBootPartition = ($hasWindows -and $hasProgramData -and $hasSystem32)
    }
} | Format-Table -AutoSize
```

**Analysis Approach**:

1. Boot partition identification rule: Must contain all three directories: `Windows/` + `ProgramData/` + `Windows/System32/`
   - Normal: Exactly 1 partition matches
   - Abnormal: No match -> **Root cause**: Boot partition unidentifiable (directory structure corrupted or mount issue), **Severity**: Critical

**[CTX] Session Memory Backfill** (not displayed to user): Record the drive letter of the uniquely matching partition as `<BootLetter>` (e.g., `E`). In subsequent scripts, `<BootLetter>` always refers to this drive letter.

### Step 3: Identify System Partition

**Data Collection**:

> Collection target: Based on boot mode, locate the system partition using partition attributes (primary criterion), then use boot files as secondary verification

```powershell
$diskNum = <TargetDiskNumber>
Get-Partition -DiskNumber $diskNum | ForEach-Object {
    $part = $_
    $letter = $part.DriveLetter
    $hasEFI = $false
    $hasBoot = $false
    if ($letter) {
        $root = "${letter}:\"
        $hasEFI = Test-Path "${root}EFI" -PathType Container
        $hasBoot = Test-Path "${root}Boot" -PathType Container
    }
    [PSCustomObject]@{
        PartitionNumber = $part.PartitionNumber
        DriveLetter     = $letter
        PartitionType   = $part.Type
        IsActive        = $part.IsActive
        HasEFI          = $hasEFI
        HasBoot         = $hasBoot
    }
} | Format-Table -AutoSize
```

**Analysis Approach**:

System partition identification uses **partition attributes as the primary criterion**; boot files (`EFI/` / `Boot/` etc.) are only used as secondary verification conditions.

1. **UEFI Mode**: Primary criterion = `Type=System` (ESP partition)
   - Single ESP partition exists -> That is the system partition
   - Multiple ESP partitions exist -> Prefer the one containing `EFI/Microsoft/Boot/`
   - No ESP partition -> **Root cause**: Missing ESP partition, **Severity**: Critical
2. **BIOS Mode**: Primary criterion = the **first `IsActive=True` partition** on the same disk
   - Take the first active partition in ascending `PartitionNumber` order -> That is the system partition
   - No active partition at all -> **Root cause**: System partition Active flag not set, **Severity**: Critical
3. **Secondary Verification** (only used to supplement evidence, not as identification basis):
   - In UEFI mode, the ESP partition is expected to contain `EFI/` directory; primary criterion matches but `HasEFI=False` -> **Root cause**: Boot directory missing inside ESP, **Severity**: Critical
   - In BIOS mode, the active partition is expected to contain `Boot/` directory; primary criterion matches but `HasBoot=False` -> **Root cause**: Boot directory missing inside system partition, **Severity**: Critical

**[CTX] Session Memory Backfill** (not displayed to user): Record the identified system partition drive letter as `<SystemLetter>`. In subsequent scripts, `<SystemLetter>` refers to this drive letter. Also derive and record `<BcdPath>` from the boot mode and `<SystemLetter>` -- this needs no registry HIVE loading:

- **UEFI Mode**: `<BcdPath>` = `<SystemLetter>:\EFI\Microsoft\Boot\BCD`
- **BIOS Mode**: `<BcdPath>` = `<SystemLetter>:\Boot\BCD`

> `<BootLetter>` and `<SystemLetter>` are each independently collected and assigned; whether they are the same depends on the actual collection result:
>
> - **UEFI Mode**: ESP (system partition) and OS partition (boot partition) are two independent partitions; `<BootLetter>` and `<SystemLetter>` must not be the same; if they are the same -> **Collection or identification error**, MUST re-verify
> - **BIOS Mode**: The two may be the same drive letter (single partition) or different drive letters (dual partition); both are valid forms

### Step 4: Partition Attribute Verification

**Data Collection**:

> Collection target: Obtain detailed attributes of boot partition and system partition

```powershell
# Boot partition attributes
$bootLetter = '<BootLetter>'
$bootPart = Get-Partition -DriveLetter $bootLetter
$bootVol = Get-Volume -DriveLetter $bootLetter
$bootDisk = Get-Disk -Number $bootPart.DiskNumber
[PSCustomObject]@{
    DriveLetter   = $bootLetter
    FileSystem    = $bootVol.FileSystemType
    Size          = $bootVol.Size
    SizeRemaining = $bootVol.SizeRemaining
    IsReadOnly    = $bootDisk.IsReadOnly
    IsHidden      = $bootPart.IsHidden
} | Format-Table -AutoSize

# System partition attributes
$sysLetter = '<SystemLetter>'
$sysVol = Get-Volume -DriveLetter $sysLetter
$sysPart = Get-Partition -DriveLetter $sysLetter
[PSCustomObject]@{
    DriveLetter = $sysLetter
    FileSystem  = $sysVol.FileSystemType
    Size        = $sysVol.Size
    IsActive    = $sysPart.IsActive
    IsHidden    = $sysPart.IsHidden
} | Format-Table -AutoSize

# Disk physical parameters
$diskNum = <TargetDiskNumber>
Get-Disk -Number $diskNum | Format-Table Number, IsReadOnly, LogicalSectorSize, PhysicalSectorSize -AutoSize
```

Obtain SectorsPerTrack (requires WMI):
```powershell
Get-CimInstance -ClassName Win32_DiskDrive | Where-Object { $_.Index -eq $diskNum } | Format-Table SectorsPerTrack -AutoSize
```

**Analysis Approach**:

1. Boot partition size: < 20GB -> **Root cause**: Boot partition too small, **Severity**: Warning
2. Boot partition file system: Not NTFS -> **Root cause**: Boot partition file system abnormal, **Severity**: Critical
3. Boot partition remaining space: <= 1GB -> **Root cause**: Insufficient system disk space, **Severity**: Warning
4. Boot partition hidden attribute: IsHidden=True -> **Root cause**: Boot partition hidden, **Severity**: Critical
5. System partition file system: Not FAT/FAT32/NTFS -> **Root cause**: System partition file system abnormal, **Severity**: Critical
6. System partition size: < 100MB -> **Root cause**: System partition too small, **Severity**: Warning
7. System partition hidden in BIOS mode: IsHidden=True -> **Root cause**: System partition hidden, **Severity**: Critical
8. SectorsPerTrack: != 63 -> **Root cause**: SectorsPerTrack compatibility issue, **Severity**: Warning
9. LogicalSectorSize: Not 512 and not 4096 -> **Root cause**: SectorSize abnormal, **Severity**: Warning

### Step 5: ACL Permission Check

**Data Collection**:

> Collection target: Check key permission configuration of boot partition root directory

```powershell
$bootLetter = '<BootLetter>'
$acl = Get-Acl "${bootLetter}:\"
$acl.Access | Format-List IdentityReference, FileSystemRights, AccessControlType, IsInherited, InheritanceFlags, PropagationFlags
```

**Analysis Approach**:

1. Check BUILTIN\Users permissions: Must have ReadAndExecute
   - Abnormal: Missing Read+Execute -> **Root cause**: Insufficient Users permissions on boot partition root directory, **Severity**: Critical
2. Check NT AUTHORITY\SYSTEM permissions: Must have FullControl
   - Abnormal: Missing FullControl -> **Root cause**: Insufficient SYSTEM permissions on boot partition root directory, **Severity**: Critical

## Cross-References

| Type | Trigger Condition | Target |
|------|-------------------|--------|
| Chain successor | Partition identification complete, continue diagnosis | -> [registry.md](references/offline/registry.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are described in [disk-partition.md](references/offline/fixes/disk-partition.md).

**Drive letter / access path assignment is a fix action**: when diagnosis finds a partition without a drive letter or access path (the typical root cause behind "partition disappeared / not visible"), restoring access via `Add-PartitionAccessPath`, `Set-Partition -NewDriveLetter`, or `diskpart assign` is a FIX, not a collection step -- even though it is reversible and metadata-only. Present it in the fix plan with risk notes and execute only after the user's explicit confirmation (Principle 6). Embedding it inside a collection script to "verify accessibility" or "check whether the partition is readable" is prohibited; the collection phase stays strictly read-only.
