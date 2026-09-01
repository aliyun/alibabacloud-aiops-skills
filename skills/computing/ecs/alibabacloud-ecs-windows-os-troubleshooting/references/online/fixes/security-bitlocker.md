# Security BitLocker Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: BitLocker triggered recovery mode

**Fix operation**:

```powershell
# If recovery key is available, use it to unlock
manage-bde -unlock C: -RecoveryPassword <48DigitRecoveryKey>
# Re-enable normal protection after unlock
manage-bde -protectors -enable C:
```

**Verification**:

```powershell
manage-bde -status C:
```

Expected result: Protection Status shows "Protection On", Lock Status is "Unlocked"

**Risk notes**:

- **Session impact**: None; only unlocking the encrypted volume.
- **Persistence scope**: Data is accessible after unlock; may need to re-unlock after reboot.
- **Rollback command**: `Lock-BitLocker -MountPoint '<DriveLetter>'`
- **Note**: If the recovery key cannot be obtained, the encrypted volume cannot be unlocked. It is recommended to back up the recovery key to AD or Microsoft account in advance.

### Root cause: BitLocker encryption incomplete

**Fix operation**:

```powershell
# Resume the paused encryption process
manage-bde -resume C:
```

**Verification**:

```powershell
manage-bde -status C:
```

Expected result: Conversion Status shows "Fully Encrypted" or encryption is in progress

**Risk notes**:

- **Session impact**: Encryption process incurs additional disk I/O overhead.
- **Persistence scope**: Encryption state is persistent.
- **Rollback command**: `Disable-BitLocker -MountPoint '<DriveLetter>'` (decrypt the disk).
- **Note**: Recommended to execute during off-peak business hours.
