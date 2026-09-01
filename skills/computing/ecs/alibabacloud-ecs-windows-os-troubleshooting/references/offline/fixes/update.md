# Update and Patch Status Diagnosis Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Problematic patch installed

**Fix**:

```powershell
$bootLetter = '<BootLetter>'
$kbNumber = '<KBNumber>'  # e.g. KB5009624

# 1. Find full package name
$pkg = Get-WindowsPackage -Path "${bootLetter}:\" | Where-Object { $_.PackageName -match $kbNumber }
if ($pkg) {
    # 2. Remove problematic patch
    Write-Host "Removing package: $($pkg.PackageName)"
    Remove-WindowsPackage -Path "${bootLetter}:\" -PackageName $pkg.PackageName
} else {
    Write-Host "Package containing $kbNumber not found"
}
```

**Known problematic patch list**:
- KB5009624, KB5009595, KB5009546, KB5009557, KB5009555
- KB5014738, KB5014702, KB5014692, KB5014678
- KB5060842

**Verification**: `Get-WindowsPackage -Path "${bootLetter}:\" | Where-Object { $_.PackageName -match $kbNumber }` -> no results

**Risk notes**:
- Session impact: Removes the specified Windows update package from the offline disk via DISM
- Persistence scope: Survives reboot -- the patch removal persists on the target system
- Rollback: Reinstall the removed patch using `Add-WindowsPackage -Path "${bootLetter}:\" -PackagePath <OriginalPackagePath>`

---

### Root cause: Missing SHA-256 support patch

**Fix**: Install KB3033929 offline via DISM (applicable to Windows 7 / Server 2008 R2):

```powershell
$bootLetter = '<BootLetter>'
$arch = '<x64|x86>'  # Match target OS architecture

# 1. Download KB3033929 MSU from Microsoft
# x64: https://download.microsoft.com/download/C/8/7/C87AE67E-A228-48FB-8F02-B2A9A1238099/Windows6.1-KB3033929-x64.msu
# x86: https://download.microsoft.com/download/3/7/4/37473f39-5728-4153-9a25-64c09de9ed52/Windows6.1-KB3033929-x86.msu
#
# Warning: Downloading will generate public network traffic; MUST notify the user and wait for confirmation before proceeding
if ($arch -eq 'x64') {
    $url = 'https://download.microsoft.com/download/C/8/7/C87AE67E-A228-48FB-8F02-B2A9A1238099/Windows6.1-KB3033929-x64.msu'
} else {
    $url = 'https://download.microsoft.com/download/3/7/4/37473f39-5728-4153-9a25-64c09de9ed52/Windows6.1-KB3033929-x86.msu'
}
$msuPath = Join-Path $env:TEMP 'KB3033929.msu'
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri $url -OutFile $msuPath -UseBasicParsing -TimeoutSec 300
if (-not (Test-Path $msuPath)) {
    Write-Host "ERROR: Download failed from $url"
    Exit 1
}

# 2. Install via DISM
dism.exe /image:"${bootLetter}:\" /add-package /PackagePath:$msuPath /quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: DISM install failed with exit code $LASTEXITCODE"
    Exit $LASTEXITCODE
}

# 3. Clean up
Remove-Item -Path $msuPath -Force -ErrorAction SilentlyContinue
```

**Verification**: `Get-WindowsPackage -Path "${bootLetter}:\" | Where-Object { $_.PackageName -match '3033929' }` -> PackageState=Installed

**Risk notes**:
- Session impact: Downloads KB3033929 from Microsoft and installs it on the offline disk via DISM; generates public network traffic -- MUST notify the user and wait for explicit confirmation before proceeding
- Persistence scope: Survives reboot -- the patch installation persists on the target system
- Rollback: Remove the patch using `Remove-WindowsPackage -Path "${bootLetter}:\" -PackageName <PackageName>`. If the target system is already in a pending update state, installing on top may worsen component store inconsistency

---

### Root cause: Pending system updates exist

**Fix**: Thoroughly clean up pending state (DISM uninstall pending packages + clean CBS registry keys + delete pending.xml):

```powershell
$bootLetter = '<BootLetter>'

# 1. Uninstall packages in Pending state
$pendingPkgs = Get-WindowsPackage -Path "${bootLetter}:\" | Where-Object { $_.PackageState -match 'Pending' }
foreach ($pkg in $pendingPkgs) {
    Write-Host "Removing pending package: $($pkg.PackageName)"
    try {
        Remove-WindowsPackage -Path "${bootLetter}:\" -PackageName $pkg.PackageName
    } catch {
        Write-Host "Remove $($pkg.PackageName) failed, continuing..."
    }
}

# 2. Clean up CBS PackagesPending registry key
# DISM cmdlets unload mounted HIVEs, so mount the SOFTWARE hive here (self-contained)
$softHive = "${bootLetter}:\Windows\System32\config\SOFTWARE"
$hivePath = "HKLM\_SOFTWARE"
& reg load $hivePath $softHive
if ($LASTEXITCODE -ne 0) { throw "Failed to load SOFTWARE hive." }

try {
    $cbsPath = "HKLM:\_SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing"
    $baseKey = [Microsoft.Win32.Registry]::LocalMachine
    $cbsRelPath = $cbsPath -replace '^HKLM:\\', ''
    $cbsKey = $baseKey.OpenSubKey($cbsRelPath, $true)
    if ($cbsKey) {
        foreach ($name in $cbsKey.GetSubKeyNames()) {
            if ($name -like '*Pending*') {
                Write-Host "Deleting CBS pending subkey: $name"
                try { $cbsKey.DeleteSubKeyTree($name, $true) } catch {
                    Write-Host "Failed to delete $name: $($_.Exception.Message)"
                }
            }
        }
        $cbsKey.Close()
        $cbsKey.Dispose()
    }
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
}

# 3. Delete WinSxS\pending.xml
$pendingXml = "${bootLetter}:\Windows\WinSxS\pending.xml"
if (Test-Path $pendingXml) {
    Rename-Item $pendingXml "${pendingXml}.bak" -Force
    Write-Host "Renamed pending.xml to pending.xml.bak"
}

# 4. Clean up Session Manager PendingFileRenameOperations (optional, high risk)
# $sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
# & reg load "HKLM\_SYSTEM" $sysHive
# $select = Get-ItemProperty "HKLM:\_SYSTEM\Select" -ErrorAction SilentlyContinue
# $csName = "ControlSet00$($select.Current)"
# Remove-ItemProperty "HKLM:\_SYSTEM\${csName}\Control\Session Manager" -Name PendingFileRenameOperations -ErrorAction SilentlyContinue
# & reg unload "HKLM\_SYSTEM"
```

**Verification**:
- `Get-WindowsPackage -Path "${bootLetter}:\" | Where-Object { $_.PackageState -match 'Pending' }` -> no results
- `Test-Path "${bootLetter}:\Windows\WinSxS\pending.xml"` -> False

**Risk notes**:
- Session impact: Removes pending Windows packages via DISM, cleans CBS registry keys in the offline SOFTWARE hive, and renames pending.xml on the offline disk
- Persistence scope: Survives reboot -- changes persist on the target system; deleting pending.xml may cause component store inconsistency, so it is recommended to prioritize attempting a normal boot to complete the updates
- Rollback: Restore pending.xml from `pending.xml.bak` and reinstall removed packages. The script is self-contained for HIVE mount/unmount; if interrupted midway, MUST confirm that `HKLM\_SOFTWARE` has been unloaded
