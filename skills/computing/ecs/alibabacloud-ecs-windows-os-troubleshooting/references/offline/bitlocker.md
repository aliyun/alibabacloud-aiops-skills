# BitLocker Encrypted Volume Identification

## Function Description

Detects whether the target system disk is BitLocker encrypted and in a locked state. This file is a conditional extension of environment.md **Step 6 BitLocker Encryption Detection**: triggered when Step 5 completes drive letter assignment and finds that a key partition's FileSystem is RAW, `Test-Path <Letter>:\Windows\System32` fails, or drive letter assignment persistently fails, to directly rule out BitLocker as a blocking root cause before entering disk-partition.md.

**Input**: Unreadable partition drive letter or disk number + partition number found in environment.md
**Output**: Confirms whether it is BitLocker encrypted -> if yes, terminate diagnostics and inform user

## Step Selection Guide

This file contains only 1 step; always execute when triggered.

## Diagnostic Steps

### Step 1: BitLocker Encryption Status Detection

**Data Collection**:

> Collection target: Read the first 16 bytes of the partition VBR (Volume Boot Record) to check for the BitLocker characteristic signature `-FVE-FS-`

```powershell
$exitCode = 0
try {
    # Get all partitions of the target disk
    $targetDiskNumber = <TargetDiskNumber>
    $partitions = Get-Partition -DiskNumber $targetDiskNumber | Where-Object { $_.Type -ne 'Reserved' -and $_.Size -gt 100MB }

    foreach ($part in $partitions) {
        Write-Host "=== Disk $($part.DiskNumber) Partition $($part.PartitionNumber) (Size: $([math]::Round($part.Size/1GB, 1)) GB) ==="

        # Check if partition already has a drive letter and is accessible
        if ($part.DriveLetter) {
            $testPath = "$($part.DriveLetter):\Windows\System32"
            if (Test-Path $testPath) {
                Write-Host "  Status: Accessible (not encrypted or already unlocked)"
                continue
            }
        }

        # Read first 16 bytes of partition VBR to check BitLocker signature
        $accessPath = "\\.\PhysicalDrive$($part.DiskNumber)"
        $stream = $null
        try {
            $stream = [System.IO.File]::Open($accessPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            $partOffset = $part.Offset
            [void]$stream.Seek($partOffset, [System.IO.SeekOrigin]::Begin)
            $buffer = New-Object byte[] 16
            [void]$stream.Read($buffer, 0, 16)

            # BitLocker VBR signature: "-FVE-FS-" (8 bytes) at offset 3
            $signature = [System.Text.Encoding]::ASCII.GetString($buffer, 3, 8)
            Write-Host "  VBR Signature at offset 3: '$signature'"

            if ($signature -eq '-FVE-FS-') {
                Write-Host "  ** BitLocker DETECTED - Volume is encrypted **"
            } else {
                Write-Host "  Not BitLocker (signature: $signature)"
            }
        } catch {
            Write-Host "  Error reading VBR: $($_.Exception.Message)"
        } finally {
            if ($stream) { $stream.Close() }
        }
        Write-Host ""
    }
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    $exitCode = 1
}
if ($exitCode -ne 0) { Exit $exitCode }
```

**Analysis Approach**:

1. Check VBR signature partition by partition:
   - Signature is `-FVE-FS-` -> Confirmed as BitLocker encrypted volume, **terminate diagnostics and inform user**
   - Signature is `NTFS    ` / `MSDOS5.0` / `EXFAT   ` etc. -> Not BitLocker; partition unreadable is due to other causes (filesystem corruption, etc.), continue subsequent diagnostics
   - Partition already accessible (Test-Path succeeds) -> Not encrypted or already unlocked, skip

2. If BitLocker is detected, record the affected partition information (disk number + partition number + size) for reporting to the user

---

## Fix Recommendations

### Root Cause: System disk is BitLocker encrypted, offline diagnostics cannot continue

**Action Plan**: The current offline environment cannot unlock the BitLocker encrypted volume. It is recommended that the user take one of the following measures:

1. Enter the recovery key when booting in the original instance VNC to unlock and enter the system
2. Mount the disk to a complete Windows system (with BitLocker feature), and use the recovery key to unlock
3. Install the BitLocker feature module in the original system, then retry offline diagnostics

**Risk notes**:
- Session impact: No offline modifications are made; diagnostics are terminated because BitLocker cannot be unlocked without the recovery key
- Persistence scope: N/A -- no changes are made to the target system
- Rollback: N/A -- no changes to undo; user must provide the BitLocker recovery key to proceed with any further diagnostics or recovery

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Prerequisite dependency | Requires prerequisite chain to complete drive letter assignment | -- |
| Blocking | Confirms BitLocker encryption | -> Terminate diagnostics, inform user (do not enter disk-partition.md / registry.md) |
| Non-BitLocker | VBR signature is not -FVE-FS- | -> Return to fixed prerequisite chain [disk-partition.md](references/offline/disk-partition.md) |
