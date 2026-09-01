# BCD Boot Configuration Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

> **Terminology Mapping** (MUST confirm before fixing BCD):
> - `<BootLetter>` = "Boot partition drive letter" in global context = **The partition containing Windows OS files** (contains `\Windows`) = Microsoft term "Boot Partition"
> - `<SystemLetter>` = "System partition drive letter" in global context = **The small partition containing bootmgr/BCD** (UEFI: ESP; BIOS: System Reserved) = Microsoft term "System Partition"
> - BCD field mapping: `{bootmgr}` `device` -> system partition drive letter; `{default}` `device` and `osdevice` -> boot partition drive letter. The Chinese terms "System Partition / Boot Partition" are **reversed** compared to Microsoft terminology. **Never use them interchangeably based on the Chinese literal meaning**.
>
> **Execution Rules**: When fixing, directly reuse the scripts below, only replacing the variable assignments (`$bootLetter` / `$systemLetter` / `$bootMode`) with actual environment values. **Never** modify the internal script logic, adjust `device` / `osdevice` pointers, or skip any commands.

### Root cause: BCD file missing or corrupted

**Fix operation**:

```powershell
$bootLetter = '<BootLetter>'
$systemLetter = '<SystemLetter>'
$bootMode = '<UEFI|BIOS>'

# Delete corrupted BCD file before rebuild
if ($bootMode -eq 'UEFI') {
    $bcdPath = "${systemLetter}:\EFI\Microsoft\Boot\BCD"
} else {
    $bcdPath = "${systemLetter}:\Boot\BCD"
}
if (Test-Path $bcdPath) {
    Remove-Item $bcdPath -Force
    Write-Host "Removed corrupted BCD: $bcdPath"
}

# Rebuild using bcdboot
$winRoot = "${bootLetter}:\Windows"
bcdboot $winRoot /s "${systemLetter}:" /f $bootMode
if ($LASTEXITCODE -ne 0) { Exit $LASTEXITCODE }
```

**Verification**: `bcdedit /store <BCDPath> /enum ALL` to confirm entries are complete

**Risk notes**:
- Session impact: Deletes and rebuilds the BCD file on the offline system partition using bcdboot
- Persistence scope: Survives reboot -- the new BCD takes effect on next boot
- Rollback: Restore the original BCD from backup if available; multi-boot configurations may lose non-default boot entries

---

### Root cause: Boot Manager file missing or invalid signature

**Fix operation**: Rebuild using bcdboot, which also copies bootmgr/bootmgfw.efi:

```powershell
$bootLetter = '<BootLetter>'
$systemLetter = '<SystemLetter>'
$bootMode = '<UEFI|BIOS>'

bcdboot "${bootLetter}:\Windows" /s "${systemLetter}:" /f $bootMode
if ($LASTEXITCODE -ne 0) { Exit $LASTEXITCODE }
```

**Risk notes**:
- Session impact: Rebuilds the BCD database and copies boot manager files (bootmgr/bootmgfw.efi) to the offline system partition using bcdboot
- Persistence scope: Survives reboot -- the new BCD and boot manager files take effect on next boot
- Rollback: Restore the original BCD and boot manager files from backup; multi-boot configurations may lose non-default boot entries

---

### Root cause: OS Loader entry missing

**Fix operation**:

```powershell
$bootLetter = '<BootLetter>'
$systemLetter = '<SystemLetter>'
$bootMode = '<UEFI|BIOS>'

bcdboot "${bootLetter}:\Windows" /s "${systemLetter}:" /f $bootMode
if ($LASTEXITCODE -ne 0) { Exit $LASTEXITCODE }
```

**Risk notes**:
- Session impact: Rebuilds the complete BCD on the offline system partition using bcdboot
- Persistence scope: Survives reboot -- the new BCD takes effect on next boot
- Rollback: Restore the original BCD from backup; multi-boot configurations may lose non-default boot entries

---

### Root cause: Default OS Loader corrupted

**Fix operation**: Delete the corrupted entry and rebuild:

```powershell
$systemLetter = '<SystemLetter>'
$bootLetter = '<BootLetter>'
$bootMode = '<UEFI|BIOS>'

if ($bootMode -eq 'UEFI') {
    $bcdPath = "${systemLetter}:\EFI\Microsoft\Boot\BCD"
} else {
    $bcdPath = "${systemLetter}:\Boot\BCD"
}

# Get default OS Loader Identifier
$output = bcdedit /store $bcdPath /enum "{bootmgr}" 2>&1
$defaultLine = $output | Select-String -Pattern '^default'
if ($defaultLine -match '\{([^}]+)\}') {
    $loader = "{$($Matches[1])}"
    # Delete corrupted OS Loader entry
    Write-Host "Deleting corrupted OS loader: $loader"
    bcdedit /store $bcdPath /delete $loader
}

# Rebuild BCD
bcdboot "${bootLetter}:\Windows" /s "${systemLetter}:" /f $bootMode
if ($LASTEXITCODE -ne 0) { Exit $LASTEXITCODE }
```

**Verification**: `bcdedit /store $bcdPath /enum "{default}"` to confirm device/osdevice has no "unknown"

**Risk notes**:
- Session impact: Deletes the corrupted OS Loader entry from the offline BCD store and rebuilds it using bcdboot
- Persistence scope: Survives reboot -- the new BCD takes effect on next boot
- Rollback: Restore the original BCD from backup; deleting the wrong entry will cause loss of multi-boot configurations; low risk for single-OS scenarios

---

### Root cause: OS Loader device configuration corrupted

**Fix operation**:

```powershell
$systemLetter = '<SystemLetter>'
$bootLetter = '<BootLetter>'
$bootMode = '<UEFI|BIOS>'

if ($bootMode -eq 'UEFI') {
    $bcdPath = "${systemLetter}:\EFI\Microsoft\Boot\BCD"
} else {
    $bcdPath = "${systemLetter}:\Boot\BCD"
}

# Fix device and osdevice pointers
bcdedit /store $bcdPath /set "{default}" device "partition=${bootLetter}:"
bcdedit /store $bcdPath /set "{default}" osdevice "partition=${bootLetter}:"
```

**Verification**: `bcdedit /store $bcdPath /enum "{default}"` to confirm device/osdevice points to the correct partition

**Risk notes**:
- Session impact: Modifies device and osdevice pointers in the offline BCD store; no file system operations involved
- Persistence scope: Survives reboot -- BCD changes take effect on next boot
- Rollback: `bcdedit /store $bcdPath /set "{default}" device partition=<OriginalPartition>` and `bcdedit /store $bcdPath /set "{default}" osdevice partition=<OriginalPartition>`. Pointing to the wrong partition will cause boot failure; MUST confirm the partition drive letter matches the identification results from the prerequisite chain

---

### Root cause: Residual corrupted entries in boot menu (Warning)

> Only clean up non-default corrupted OS Loader entries in displayorder (where device/osdevice is unknown). **Never delete `{default}` or {bootmgr} itself**.

**Fix operation**:

```powershell
$bcdPath = '<BcdPath>'
$staleLoaders = @('<StaleLoaderIdentifier1>', '<StaleLoaderIdentifier2>')  # Only fill in the residual corrupted entry Identifiers listed in Step 4

foreach ($id in $staleLoaders) {
    Write-Host "Deleting stale OS loader: $id"
    bcdedit /store $bcdPath /delete $id /cleanup
    if ($LASTEXITCODE -ne 0) { Exit $LASTEXITCODE }
}
```

**Verification**: `bcdedit /store $bcdPath /enum OSLOADER` to confirm only default and normal entries remain

**Risk notes**:
- Session impact: Deletes stale corrupted OS Loader entries from the offline BCD store using bcdedit /cleanup
- Persistence scope: Survives reboot -- BCD changes take effect on next boot
- Rollback: Rebuild the BCD using bcdboot if entries were mistakenly deleted. Accidentally deleting default or bootmgr will cause boot failure; only cleans up menu redundancy and does not affect the default boot path

---

### Root cause: MBR / VBR Boot Code corrupted or non-NT60 version (BIOS only)

> Applies to scenarios where Step 5 analysis deduces **MBR or VBR** category as `NT52` / `Damaged` (`bootsect /nt60 ... /mbr` rewrites both simultaneously). Not applicable to UEFI mode. If either is `NonWindows` (third-party boot loader), MUST first manually confirm whether it is a multi-boot scenario that needs to be preserved before deciding whether to rewrite to NT60.

**Fix operation**: Use `bootsect /nt60 ... /mbr` to simultaneously rewrite NT60 standard MBR boot code and system partition VBR on the target disk:

```powershell
$systemLetter = '<SystemLetter>'

# bootsect rewrites both the volume boot record (VBR of the specified volume)
# and (with /mbr) the MBR boot code of the disk hosting that volume.
# /nt60 selects the bootmgr-compatible code; /force dismounts open handles.
bootsect /nt60 "${systemLetter}:" /mbr /force
if ($LASTEXITCODE -ne 0) { Exit $LASTEXITCODE }
```

**Verification**: Re-run the Step 5 collection script and confirm:
- MBR: `MbrSignatureOK=True`, `MbrHasTCPA=True`, `MbrHasInvalidPartTbl=True`, `MbrHasMissingOS=True` (analysis can deduce as NT60)
- VBR: `VbrSignatureOK=True`, `VbrHasBOOTMGR=True` (analysis can deduce as NT60)

**Risk notes**:

- **Session impact**: Offline fix, no active TCP/RDP sessions, does not affect existing sessions.
- **Persistence scope**: Writes to both the first 440 bytes of MBR boot code and the full 512 bytes of system partition VBR on the disk. Takes permanent effect after reboot.
- **Rollback command**: Before execution, MUST back up both MBR and VBR. MBR can be backed up using `Get-Content -Path "\\.\PhysicalDrive$N" -Encoding Byte -ReadCount 512 -TotalCount 512 | Set-Content -Path mbr.bak -Encoding Byte` (usable in offline environments). VBR needs to read 512 bytes starting from the system partition offset (`Get-Partition -DriveLetter $systemLetter | Select-Object -ExpandProperty Offset`) and save it. To roll back, write both backups back in reverse.
- **Note**: `bootsect /mbr` overwrites the first 440 bytes of MBR boot code. If the original disk uses Linux/Windows dual-boot with GRUB as the entry point, the GRUB menu will be lost after execution and GRUB needs to be reinstalled on the Linux side afterward. **Does not** modify the partition table (0x1BE-0x1FD) or disk signature (0x1B8-0x1BB) in the MBR. Only applicable to MBR disks; GPT disks do not use MBR boot code, do not execute on GPT disks.
