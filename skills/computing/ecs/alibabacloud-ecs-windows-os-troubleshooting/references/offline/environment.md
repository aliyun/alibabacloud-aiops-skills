# Environment Verification and Disk Preparation

## Function Description

Verifies offline environment readiness, locates the target disk, and completes preparation work including disk online, read-only clearing, and partition drive letter assignment. This file is a prerequisite for all subsequent diagnostics.

**Input**: Disk identification info (serial number/DiskNumber/drive letter, optional)
**Output**: Ready target disk partition list (with drive letters)

## Step Selection Guide

All steps in this file **must be executed in sequence**, no skipping allowed.

**Fallback Scenario Exemption**: If already in the user manual execution phase of the collection fallback chain (where the user manually executes commands in the offline environment and pastes results back), then Step 1 (PowerShell channel verification) and Step 2 (Storage module verification) are automatically considered passed, and execution starts directly from Step 3. The availability of the Storage module is naturally determined in subsequent steps based on actual command execution results (if Get-Disk fails, fall back to diskpart).

## Diagnostic Steps

### Step 1: PowerShell Channel Verification

> If Get-Date channel probing has already been completed and passed in a preceding phase, this step can be skipped.

**Data Collection**:

> Collection target: Confirm that the cloud assistant channel is available and PowerShell can return results normally

```powershell
Get-Date
```

**Analysis**:

1. Check command return:
   - Normal: Returns current date and time
   - Abnormal: Timeout or error -> cloud assistant channel unavailable, cannot continue diagnostics

### Step 2: Storage Module Verification

**Data Collection**:

> Collection target: Confirm that the Storage module is available in the offline environment

```powershell
Get-Command Get-Disk -ErrorAction SilentlyContinue | Select-Object Name, Source
```

**Analysis**:

1. Check whether the Get-Disk command exists:
   - Normal: Returns command info (Source is the Storage module)
   - Abnormal: No output -> offline environment lacks the Storage module, subsequent disk operations need to fall back to diskpart

### Step 3: Target Disk Location

**Data Collection**:

> Collection target: List all disks in the system and locate the target system disk

If disk serial number is known:
```powershell
Get-Disk | Where-Object { $_.SerialNumber -like '*<SerialNumber>*' } | Select-Object Number, FriendlyName, SerialNumber, OperationalStatus, Size, PartitionStyle, IsOffline, IsReadOnly
```

If no identification info provided, list all non-system disks:
```powershell
Get-Disk | Where-Object { -not $_.IsSystem -and -not $_.IsBoot } | Format-List Number, FriendlyName, SerialNumber, OperationalStatus, Size, PartitionStyle, IsOffline, IsReadOnly
```

**Analysis**:

1. Disk location strategy:
   - If the user/external has provided a disk serial number, DiskNumber, or drive letter, locate based on that info
   - If not provided, request disk identification from the user (can query the instance disk serial number via `Get-Disk` as a comparison baseline)
   - If the user also cannot provide, filter candidates from non-system disks (exclude disks with IsSystem=True and IsBoot=True) and present them to the user for confirmation
2. **Disk not present determination (location failure branch)**:
   - **Candidate disks exist but ownership cannot be confirmed** (multiple non-system disks, no serial number for comparison) -> Request the system disk serial number from the user (SerialNumber from `Get-Disk`) for comparison one by one; no modification operations may be performed on any candidate disk until confirmed
   - **No candidate disks at all, or all candidate disk serial numbers do not match the control plane system disk** -> **Root cause: System disk not mounted to the instance (severity=Critical)**. In this case, you MUST terminate the offline prerequisite chain (disk-partition / registry and all subsequent checks depend on the target disk existing; continuing is meaningless and may cause misoperations on offline disks), and transition to platform-side triage:
     - Guide the user to check the system disk mount status in the console (whether it was unmounted, whether it was mounted to another instance, whether a disk swap / migration was recently performed)
     - If the console confirms the mount is normal but the offline disk is still not visible, faithfully record the full `Get-Disk` output from the instance side as evidence, and recommend contacting support for platform-side troubleshooting (host-side disk presentation path)
     - The fix direction is for the platform side to remount the system disk and then re-trigger boot; this is not within the scope of GuestOS internal fixes, and no GuestOS fix scripts should be output

### Step 4: Disk Online and Read-Only Processing

**Data Collection**:

> Collection target: Restore the offline or read-only target disk to an accessible state

If Storage module is available:
```powershell
$diskNum = <TargetDiskNumber>
$d = Get-Disk -Number $diskNum
if ($d.IsOffline) { Set-Disk -Number $diskNum -IsOffline $false }
if ($d.IsReadOnly) { Set-Disk -Number $diskNum -IsReadOnly $false }
Get-Disk -Number $diskNum | Select-Object Number, OperationalStatus, IsOffline, IsReadOnly
```

If Storage module is not available, use diskpart:
```
select disk <TargetDiskNumber>
online disk
attributes disk clear readonly
```

**Analysis**:

1. Check operation result:
   - Normal: IsOffline=False, IsReadOnly=False
   - Abnormal: Still Offline or ReadOnly -> Disk has hardware issues or is locked by another process

### Step 5: Partition Drive Letter Assignment

**Data Collection**:

> Collection target: Assign drive letters to partitions on the target disk that do not have one

```powershell
$diskNum = <TargetDiskNumber>
Get-Partition -DiskNumber $diskNum | ForEach-Object {
    if (-not $_.DriveLetter -and $_.Type -notin @('Reserved','MSR','Unknown')) {
        $_ | Add-PartitionAccessPath -AssignDriveLetter -ErrorAction SilentlyContinue
    }
}
Get-Partition -DiskNumber $diskNum | Format-Table PartitionNumber, DriveLetter, Size, Type -AutoSize
```

**Analysis**:

1. Check assignment result:
   - Normal: Main partitions (Basic Data, System) have been assigned drive letters
   - Partial failures can be ignored: Recovery, MSR, Reserved partition assignment failures are normal
   - All failures: Fall back to diskpart assign for individual assignment
2. Output the list of partitions with assigned drive letters as input for subsequent diagnostic steps

**[CTX] Session Memory Backfill** (not displayed to the user, for model reference in subsequent steps):

| Placeholder | Value | Source |
|--------------|-------|--------|
| `<DiskNumber>` | The actual value of `$diskNum` above | Target disk number inferred in Step 3 |

The model MUST remember the literal values in the table above after completing this step. `<DiskNumber>` / `<TargetDiskNumber>` appearing in subsequent scripts MUST be replaced with this value before execution.

### Step 6: BitLocker Encryption Detection (Conditional Trigger)

**Trigger condition**: **Any critical partition** (Type is `Basic` or `IFS`, Size > 1GB) in Step 5 results meets any of the following:

- `DriveLetter` is assigned but both `Test-Path "<DriveLetter>:\Windows\System32"` and `Test-Path "<DriveLetter>:\Windows"` fail
- `Get-Volume -DriveLetter <Letter>` returns `FileSystem` as `RAW` or empty
- `Add-PartitionAccessPath` fails and `diskpart assign` also cannot assign a drive letter

Trigger condition met -> immediately jump to [bitlocker.md](references/offline/bitlocker.md) Step 1 for VBR signature identification, **do not enter [disk-partition.md](references/offline/disk-partition.md)**.

**Not triggered** -> directly proceed to the next station in the fixed prerequisite chain [disk-partition.md](references/offline/disk-partition.md).

**Why execute at this stage**: Both `disk-partition.md` and `registry.md` depend on the system disk's `Windows` / `Windows\System32\config` paths being readable. On encrypted partitions, these two steps will only produce a series of Test-Path failures, misleading the diagnostic direction; completing identification at this step can eliminate the "BitLocker locked" blocking root cause within 30 seconds.

## Cross-References

| Type | Trigger Condition | Target |
|------|-------------------|--------|
| Chain successor | Step 6 detects no encryption signs | -> [disk-partition.md](references/offline/disk-partition.md) |
| Conditional jump | Step 6 triggered: partition FileSystem is RAW / critical path Test-Path fails / drive letter assignment fails | -> [bitlocker.md](references/offline/bitlocker.md) |
