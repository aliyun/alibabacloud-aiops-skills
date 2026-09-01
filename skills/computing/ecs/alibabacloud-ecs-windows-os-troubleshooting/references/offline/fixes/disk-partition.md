# Disk Partition Identification and Attribute Verification Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Boot partition hidden

**Fix operation**:

```powershell
$diskNum = <TargetDiskNumber>
$partNum = <BootPartitionNumber>
$script = @"
select disk $diskNum
select partition $partNum
attribute volume clear hidden
"@
$script | diskpart.exe
if ($LASTEXITCODE -ne 0) { Exit $LASTEXITCODE }
```

**Verification**: `Get-Partition -DiskNumber $diskNum -PartitionNumber $partNum | Select-Object IsHidden` -> IsHidden=False

**Risk notes**:
- Session impact: Clears the hidden attribute on the boot partition of the offline disk using diskpart
- Persistence scope: Survives reboot -- the partition attribute change persists on the target system
- Rollback: Re-set the hidden flag using `diskpart` with `attribute volume set hidden` on the same partition

---

### Root cause: System partition has no Active flag set

**Fix operation**:

```powershell
$diskNum = <TargetDiskNumber>
$partNum = <SystemPartitionNumber>
$script = @"
select disk $diskNum
select partition $partNum
active
"@
$script | diskpart.exe
if ($LASTEXITCODE -ne 0) { Exit $LASTEXITCODE }
```

**Verification**: `Get-Partition -DriveLetter <SystemLetter> | Select-Object IsActive` -> IsActive=True

**Risk notes**:
- Session impact: Sets the Active flag on the system partition of the offline disk using diskpart (BIOS boot mode only)
- Persistence scope: Survives reboot -- the partition attribute change persists on the target system
- Rollback: Clear the Active flag using `diskpart` with `inactive`. Setting the wrong partition as Active may cause boot failure

---

### Root cause: Insufficient permissions on boot partition root directory

**Fix operation**:

```powershell
function AddAllowAccess {
    param (
        [System.Security.AccessControl.FileSystemSecurity]$acl,
        [System.Security.Principal.NTAccount]$identity,
        [System.Security.AccessControl.FileSystemRights]$rights,
        [switch]$RemoveOnly
    )
    # Remove Deny rules
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity, $rights, "Deny")
    $acl.RemoveAccessRuleAll($rule)
    if (-not $RemoveOnly) {
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity, $rights, "Allow")
        $acl.AddAccessRule($rule)
    }
}

$bootLetter = '<BootLetter>'
$path = "${bootLetter}:\"
try {
    $acl = Get-Acl $path
    AddAllowAccess $acl "NT AUTHORITY\SERVICE" "Read" -RemoveOnly
    AddAllowAccess $acl "BUILTIN\Users" "ReadAndExecute"
    AddAllowAccess $acl "NT AUTHORITY\SYSTEM" "FullControl"
    Set-Acl -Path $path -AclObject $acl
} catch {
    Write-Error "Failed to set acl: $($_.Exception.Message)"
    Exit 1
}
```

**Verification**:

```powershell
(Get-Acl "<BootLetter>:\").Access | Where-Object { $_.IdentityReference -match 'Users|SYSTEM' } | Format-List IdentityReference, FileSystemRights, AccessControlType, IsInherited, InheritanceFlags, PropagationFlags
```

Expected result: Users has ReadAndExecute, SYSTEM has FullControl

**Risk notes**:
- Session impact: Modifies ACLs on the boot partition root directory of the offline disk; grants SYSTEM FullControl and Users ReadAndExecute, non-recursive
- Persistence scope: Survives reboot -- ACL changes persist on the target system
- Rollback: Restore original ACLs using `icacls "${bootLetter}:\" /reset`

---

### Root cause: Partition has no drive letter or access path

Applies when a partition exists and is healthy but is invisible to the user (e.g. missing from Explorer) because it has no drive letter or mount path. Note: in the offline rescue session, drive letter assignment is a diagnostic prerequisite (environment.md Step 5) required to access partition contents for inspection — this does not require separate user confirmation. This fix entry documents the root cause and remediation for the user's original system where a persistently missing drive letter was the problem.

**Fix operation**:

```powershell
$diskNum = <TargetDiskNumber>
$partNum = <PartitionNumber>
try {
    $part = Get-Partition -DiskNumber $diskNum -PartitionNumber $partNum
    if ($part.DriveLetter) {
        Write-Output "Partition already has drive letter $($part.DriveLetter) -- nothing to do"
    } else {
        $part | Add-PartitionAccessPath -AssignDriveLetter
    }
    Get-Partition -DiskNumber $diskNum -PartitionNumber $partNum |
        Select-Object PartitionNumber, DriveLetter, AccessPaths | Format-List
} catch {
    Write-Error "Failed to assign access path: $($_.Exception.Message)"
    Exit 1
}
```

**Verification**: `Get-Partition -DiskNumber $diskNum -PartitionNumber $partNum | Select-Object PartitionNumber, DriveLetter, AccessPaths` -> a drive letter (or mount path) is present, and the volume is readable (e.g. `Get-ChildItem <AssignedLetter>:\` lists content).

**Risk notes**:
- Session impact: Assigns a drive letter / access path to the target partition of the offline disk; metadata-only change -- no file data on the partition is modified
- Persistence scope: Effective in the current rescue session; it does not rewrite the faulty system's own drive-letter layout, which is re-resolved when that system boots
- Rollback: Remove the assignment with `Remove-PartitionAccessPath -DriveLetter <AssignedLetter>` on the same partition
