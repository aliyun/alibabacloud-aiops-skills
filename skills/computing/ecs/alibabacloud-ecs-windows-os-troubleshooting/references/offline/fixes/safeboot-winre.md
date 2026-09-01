# SafeBoot Residue and WinRE Automatic Repair Loop Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: BCD SafeBoot flag residue

**Fix**: Delete the safeboot and safebootalternateshell values in BCD

```powershell
$systemLetter = '<SystemLetter>'
$bootMode = '<UEFI|BIOS>'

if ($bootMode -eq 'UEFI') {
    $bcdPath = "${systemLetter}:\EFI\Microsoft\Boot\BCD"
} else {
    $bcdPath = "${systemLetter}:\Boot\BCD"
}

bcdedit /store $bcdPath /deletevalue "{default}" safeboot
bcdedit /store $bcdPath /deletevalue "{default}" safebootalternateshell
```

**Verification**: `bcdedit /store $bcdPath /enum "{default}"` to confirm no safeboot-related lines remain

**Risk notes**:
- Session impact: Modifies the offline BCD store to delete safeboot and safebootalternateshell values
- Persistence scope: Survives reboot -- BCD changes take effect on next boot
- Rollback: `bcdedit /store $bcdPath /set "{default}" safeboot <OriginalValue>` and `bcdedit /store $bcdPath /set "{default}" safebootalternateshell <OriginalValue>`

---

### Root cause: SafeBoot registry key deleted

**Fix**: This fix is more complex and requires exporting SafeBoot registry keys from a same-version system. Basic recovery guidance for offline environments:

```powershell
# Need to restore SafeBoot registry keys from a same-version Windows system.
# The .reg export file must be prepared in advance from a matching Windows version.
#
# Offline approach: load the target system's SYSTEM HIVE, then import keys into it.
$bootLetter = '<BootLetter>'
$systemHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$hivePath = "HKLM\_OFFLINE_SYSTEM"

# Load the offline SYSTEM HIVE
& reg load $hivePath $systemHive
if ($LASTEXITCODE -ne 0) { throw "Failed to load offline SYSTEM hive" }

try {
    # Use reg import with the loaded HIVE path (reg files must reference HKLM\_OFFLINE_SYSTEM\...)
    # Ensure the .reg files use the offline hive path, e.g.:
    #   [HKEY_LOCAL_MACHINE\_OFFLINE_SYSTEM\ControlSet001\Control\SafeBoot\Minimal]
    & reg import SafeBoot_Minimal.reg
    & reg import SafeBoot_Network.reg
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
}
```

**Verification**: Confirm `SafeBoot\Minimal` and `SafeBoot\Network` subkeys exist and have >30 entries

**Risk notes**:
- Session impact: Loads the offline SYSTEM hive and imports SafeBoot registry keys from a same-version Windows system
- Persistence scope: Survives reboot -- registry changes persist on the target system
- Rollback: Delete the imported SafeBoot keys from the offline SYSTEM hive. Version must match strictly (SafeBoot entries differ across Windows versions)

---

### Root cause: WinRE automatic repair loop

**Fix**: Disable automatic recovery

```powershell
$systemLetter = '<SystemLetter>'
$bootMode = '<UEFI|BIOS>'

if ($bootMode -eq 'UEFI') {
    $bcdPath = "${systemLetter}:\EFI\Microsoft\Boot\BCD"
} else {
    $bcdPath = "${systemLetter}:\Boot\BCD"
}

# Disable automatic recovery
bcdedit /store $bcdPath /set "{default}" recoveryenabled No

# Optional: ignore all boot failures (suppress WinRE trigger)
# bcdedit /store $bcdPath /set "{default}" bootstatuspolicy IgnoreAllFailures
```

**Verification**: `bcdedit /store $bcdPath /enum "{default}"` to confirm `recoveryenabled  No`

**Risk notes**:
- Session impact: Modifies the offline BCD store to disable automatic recovery (recoveryenabled No)
- Persistence scope: Survives reboot -- BCD changes take effect on next boot; the system no longer has automatic repair capability and boot failures will require manual intervention
- Rollback: `bcdedit /store $bcdPath /set "{default}" recoveryenabled Yes`

---

### Root cause: WinRE BCD entry corrupted (device=unknown)

**Fix**: Delete the corrupted recovery BCD entry and disable automatic recovery

```powershell
$systemLetter = '<SystemLetter>'
$bootMode = '<UEFI|BIOS>'

if ($bootMode -eq 'UEFI') {
    $bcdPath = "${systemLetter}:\EFI\Microsoft\Boot\BCD"
} else {
    $bcdPath = "${systemLetter}:\Boot\BCD"
}

# Get recoverysequence GUID
$output = bcdedit /store $bcdPath /enum "{default}" 2>&1
$seqLine = $output | Select-String "recoverysequence"

if ($seqLine) {
    $seqGuid = ($seqLine -replace '.*recoverysequence\s+','').Trim()
    # Delete corrupted recovery entry
    bcdedit /store $bcdPath /delete $seqGuid
}

# Clear recoverysequence reference from {default}
bcdedit /store $bcdPath /deletevalue "{default}" recoverysequence
bcdedit /store $bcdPath /set "{default}" recoveryenabled No
```

**Verification**: `bcdedit /store $bcdPath /enum ALL` to confirm no unknown device entry remains

**Risk notes**:
- Session impact: Modifies the offline BCD store to delete the corrupted recovery entry and disable automatic recovery
- Persistence scope: Survives reboot -- BCD changes take effect on next boot
- Rollback: `bcdedit /store $bcdPath /set "{default}" recoveryenabled Yes` and recreate the recovery entry if needed. Only the already-corrupted entry is deleted
