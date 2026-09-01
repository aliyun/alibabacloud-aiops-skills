# Identity User Profiles Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Fix 1: Fix Corrupted User Profile

**Applicable scenario**: Profile corrupted, temporary profile loaded

1. In the registry, navigate to `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList`
2. Locate the entry for the corresponding user SID
3. If a `.bak` copy exists:
   - Delete the entry without `.bak`
   - Rename the `.bak` entry by removing the `.bak` suffix
   - Set the `State` value to `0`
4. Restart the system

**Verification**:

```powershell
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\<UserSID>" -Name State, ProfileImagePath -ErrorAction SilentlyContinue | Select-Object State, ProfileImagePath
```

Expected result: `State` value is `0`, `ProfileImagePath` points to the correct path, no `.bak` suffix entry

**Risk notes**:
- **Session impact**: Requires system restart; all sessions including RDP will be disconnected during reboot.
- **Persistence scope**: Survives reboot (registry changes in ProfileList are persistent).
- **Rollback command**: Restore the original registry entries -- re-create the non-`.bak` entry, re-add `.bak` suffix to the backup entry, and restore the original `State` value.

### Fix 2: Fix Folder Redirection

**Applicable scenario**: Redirection target unreachable

```powershell
# Redirect Desktop back to local default path
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -Name 'Desktop' -Value '%USERPROFILE%\Desktop'
# Also handle other folders (Documents, etc.)
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -Name 'Personal' -Value '%USERPROFILE%\Documents'
```

**Verification**:

```powershell
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -Name Desktop, Personal | Select-Object Desktop, Personal
```

Expected result: `Desktop` value is `%USERPROFILE%\Desktop`, `Personal` value is `%USERPROFILE%\Documents`

**Risk notes**:
- **Session impact**: None for current session; changes take effect on next logon or Explorer restart.
- **Persistence scope**: Survives reboot (registry change in user hive HKCU).
- **Rollback command**: `Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -Name 'Desktop' -Value '<original_path>'; Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -Name 'Personal' -Value '<original_path>'`

### Fix 3: Clear WebCache Lock Copies in Default Profile and Affected Users

**Applicable scenario**: WebCacheLock.dat / WebCache folder exists in Default profile or user profiles

**Step 1: Log in as administrator, delete hidden files and folders in the Default profile**

Delete the following files and folders (if they exist):
- `C:\Users\Default\AppData\Local\Microsoft\Windows\WebCacheLock.dat`
- `C:\Users\Default\AppData\Local\Microsoft\Windows\WebCache`

```powershell
#requires -RunAsAdministrator
# Fix Step 1: Remove WebCacheLock.dat and WebCache from Default profile
# Risk: File deletion is irreversible
# Verify: New users can log on without performance issues

$defaultLock  = "$env:SystemDrive\Users\Default\AppData\Local\Microsoft\Windows\WebCacheLock.dat"
$defaultCache = "$env:SystemDrive\Users\Default\AppData\Local\Microsoft\Windows\WebCache"

if (Test-Path $defaultLock)  { Remove-Item -Path $defaultLock  -Force; Write-Host "Removed: $defaultLock" }
if (Test-Path $defaultCache) { Remove-Item -Path $defaultCache -Recurse -Force; Write-Host "Removed: $defaultCache" }
```

**Step 2: Ensure each affected user is fully logged off, then delete hidden files and folders in their profiles**

For each affected user, delete the following files and folders (replace `<affectedUserFolder>` with the actual user folder name, e.g., `Administrator`):
- `C:\Users\<affectedUserFolder>\AppData\Local\Microsoft\Windows\WebCacheLock.dat`
- `C:\Users\<affectedUserFolder>\AppData\Local\Microsoft\Windows\WebCache`

```powershell
#requires -RunAsAdministrator
# Fix Step 2: Remove WebCacheLock.dat and WebCache from affected user profiles
# Prerequisite: ensure the affected user is fully logged off before running

$profileRoot = "$env:SystemDrive\Users"
Get-ChildItem -Path $profileRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $lockFile    = Join-Path $_.FullName 'AppData\Local\Microsoft\Windows\WebCacheLock.dat'
    $cacheFolder = Join-Path $_.FullName 'AppData\Local\Microsoft\Windows\WebCache'
    if (Test-Path $lockFile)    { Remove-Item -Path $lockFile    -Force;          Write-Host "Removed: $lockFile" }
    if (Test-Path $cacheFolder) { Remove-Item -Path $cacheFolder -Recurse -Force; Write-Host "Removed: $cacheFolder" }
}
```

**Verification**:

```powershell
# Verify all WebCacheLock.dat and WebCache have been removed
$profileRoot = "$env:SystemDrive\Users"
Get-ChildItem -Path $profileRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $lockFile    = Join-Path $_.FullName 'AppData\Local\Microsoft\Windows\WebCacheLock.dat'
    $cacheFolder = Join-Path $_.FullName 'AppData\Local\Microsoft\Windows\WebCache'
    [PSCustomObject]@{
        UserFolder      = $_.Name
        WebCacheLockDat = Test-Path -Path $lockFile
        WebCacheFolder  = Test-Path -Path $cacheFolder
    }
} | Format-Table -AutoSize
```

Expected result: WebCacheLockDat = False, WebCacheFolder = False; after new user login, login speed is normal with no Event ID 454 errors

**Risk notes**:

- **Session impact**: None, but the affected user must be fully logged off.
- **Persistence scope**: Deletion is irreversible.
- **Rollback command**: Not reversible (profile already deleted).
- **Note**: Before executing, ensure the affected user is fully logged off (profile unloaded), otherwise deletion may fail or cause data loss.
