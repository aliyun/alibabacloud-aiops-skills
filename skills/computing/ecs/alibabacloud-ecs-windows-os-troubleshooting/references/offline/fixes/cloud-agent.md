# Cloud Agent and Application Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Vminit not installed / files missing / version too old

**Fix operation**: Download the latest Vminit package from OSS, clear the target directory, extract, and register the service

```powershell
$bootLetter = '<BootLetter>'

# ========== Step 1: Download Vminit package ==========
# Prefer user-provided URL; if not available, generate by rule:
# http://windows-driver-{region}.oss-{region}-internal.aliyuncs.com/vminit/vminit.zip
$region = '<Region>'   # e.g. cn-hangzhou
$url = '<UserProvidedURL>'
if (-not $url -or $url -like '<*>') {
    $url = "http://windows-driver-${region}.oss-${region}-internal.aliyuncs.com/vminit/vminit.zip"
}
$zipPath = Join-Path $env:TEMP 'vminit.zip'
try {
    Write-Host "Downloading vminit package from [$url]..."
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -TimeoutSec 300
} catch {
    Write-Host "Download failed: $($_.Exception.Message)"
    Exit 1
}

# ========== Step 2: Clear target directory ==========
$dst = "${bootLetter}:\ProgramData\aliyun\vminit"
if (Test-Path $dst) {
    Write-Host "Removing existing directory [$dst]..."
    Remove-Item -Path $dst -Recurse -Force
}

# ========== Step 3: Extract ==========
try {
    Write-Host "Extracting [$zipPath] to [$dst]..."
    Expand-Archive -Path $zipPath -DestinationPath $dst -Force
} catch {
    Write-Host "Extract failed: $($_.Exception.Message)"
    Exit 1
}

# ========== Step 4: Register service (offline registry write) ==========
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    Write-Host "Loading SYSTEM registry hive..."
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to load SYSTEM hive."
    }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    if (-not $select) { throw "Unable to open SYSTEM\Select" }
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()
    Write-Host "Current control set: $csName"

    # Locate vminit.exe
    $binary = Get-ChildItem -Path $dst -Recurse -Filter 'vminit.exe'
    if (!$binary) { throw "vminit.exe not found in extracted package" }
    $imagePath = $binary.FullName + ' service'

    # Create service key
    $servicesBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Services", $true)
    $serviceKey = $servicesBase.CreateSubKey('vminit')
    $servicesBase.Close(); $servicesBase.Dispose()

    $serviceKey.SetValue('ImagePath', $imagePath, [Microsoft.Win32.RegistryValueKind]::String)
    $serviceKey.SetValue('DisplayName', 'vminit service', [Microsoft.Win32.RegistryValueKind]::String)
    $serviceKey.SetValue('Start', 2, [Microsoft.Win32.RegistryValueKind]::DWord)        # Auto
    $serviceKey.SetValue('Type', 16, [Microsoft.Win32.RegistryValueKind]::DWord)        # WIN32_OWN_PROCESS
    $serviceKey.Close(); $serviceKey.Dispose()

    Write-Host "Vminit service registered successfully."
} catch {
    Write-Host "Register vminit service failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    # Cleanup zip
    Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Risk notes**:
- Session impact: Downloads and replaces Vminit files on the offline disk; loads and modifies the offline SYSTEM registry hive to register the vminit service
- Persistence scope: Survives reboot -- file and registry changes persist on the target system
- Rollback: Delete the `${bootLetter}:\ProgramData\aliyun\vminit` directory and remove the `vminit` service key from `ControlSet\Services` in the offline SYSTEM hive

### Root cause: DONOT_RUN_CLOUDINIT_AFTER_REBOOT flag file exists

**Fix operation**: Delete the flag file

```powershell
$bootLetter = '<BootLetter>'
$flagFile = "${bootLetter}:\ProgramData\aliyun\vminit\DONOT_RUN_CLOUDINIT_AFTER_REBOOT"

if (Test-Path $flagFile) {
    Write-Host "Removing DONOT_RUN flag file: $flagFile"
    Remove-Item -Path $flagFile -Force
    Write-Host "Flag file removed."
} else {
    Write-Host "Flag file not found, nothing to do."
}
```

**Risk notes**:
- Session impact: Deletes a flag file on the offline disk; no registry changes
- Persistence scope: Survives reboot -- the flag file remains deleted and Vminit will run on next boot
- Rollback: Recreate the flag file: `New-Item -Path "${bootLetter}:\ProgramData\aliyun\vminit\DONOT_RUN_CLOUDINIT_AFTER_REBOOT" -ItemType File`

### Root cause: Vminit service disabled

**Fix operation**: Change the service Start type to Auto (2)

```powershell
$bootLetter = '<BootLetter>'
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    $servicesBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Services", $true)
    $serviceKey = $servicesBase.OpenSubKey('vminit', $true)
    if ($serviceKey) {
        Write-Host "Setting vminit Start = 2 (Auto)"
        $serviceKey.SetValue('Start', 2, [Microsoft.Win32.RegistryValueKind]::DWord)
        $serviceKey.Close(); $serviceKey.Dispose()
    } else {
        Write-Host "vminit service key not found"
        $exitCode = 1
    }
    $servicesBase.Close(); $servicesBase.Dispose()
} catch {
    Write-Host "Enable vminit failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Risk notes**:
- Session impact: Loads and modifies the offline SYSTEM registry hive to set the vminit service Start type to Auto (2)
- Persistence scope: Survives reboot -- registry change persists on the target system
- Rollback: Set the service Start value back to 4 (Disabled) in the offline SYSTEM hive: load the hive, set `ControlSet\Services\vminit` Start to 4, unload the hive

### Root cause: Cloud Assistant not installed / files missing

**Fix operation**: Download the Cloud Assistant package from OSS, clear the target directory, extract, and register the service

```powershell
$bootLetter = '<BootLetter>'

# ========== Step 1: Download Cloud Assist package ==========
# Prefer user-provided URL; if not available, generate by rule:
# http://aliyun-client-assist-{region}.oss-{region}-internal.aliyuncs.com/aliyun-client-assist/windows/{version}_update.zip
$region = '<Region>'   # e.g. cn-hangzhou
$version = '2.1.4.1007'
$url = '<UserProvidedURL>'
if (-not $url -or $url -like '<*>') {
    $url = "http://aliyun-client-assist-${region}.oss-${region}-internal.aliyuncs.com/aliyun-client-assist/windows/${version}_update.zip"
}
$zipPath = Join-Path $env:TEMP 'assist.zip'
try {
    Write-Host "Downloading Cloud Assist package from [$url]..."
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -TimeoutSec 300
} catch {
    Write-Host "Download failed: $($_.Exception.Message)"
    Exit 1
}

# ========== Step 2: Clear target directory ==========
$dst = "${bootLetter}:\ProgramData\aliyun\assist"
if (Test-Path $dst) {
    Write-Host "Removing existing directory [$dst]..."
    Remove-Item -Path $dst -Recurse -Force
}

# ========== Step 3: Extract ==========
try {
    Write-Host "Extracting [$zipPath] to [$dst]..."
    Expand-Archive -Path $zipPath -DestinationPath $dst -Force
} catch {
    Write-Host "Extract failed: $($_.Exception.Message)"
    Exit 1
}

# ========== Step 4: Register service (offline registry write) ==========
$sysHive = "${bootLetter}:\Windows\System32\config\SYSTEM"
$exitCode = 0

try {
    Write-Host "Loading SYSTEM registry hive..."
    $hivePath = "HKLM\_SYSTEM"
    & reg load $hivePath $sysHive
    if ($LASTEXITCODE -ne 0) { throw "Failed to load SYSTEM hive." }

    $select = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\Select", $false)
    if (-not $select) { throw "Unable to open SYSTEM\Select" }
    $csName = "ControlSet00$($select.GetValue('Current'))"
    $select.Close(); $select.Dispose()

    # Locate aliyun_assist_service.exe
    $binary = Get-ChildItem -Path $dst -Recurse -Filter 'aliyun_assist_service.exe'
    if (!$binary) { throw "aliyun_assist_service.exe not found in extracted package" }
    $imagePath = $binary.FullName

    # Create service key
    $servicesBase = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("_SYSTEM\${csName}\Services", $true)
    $serviceKey = $servicesBase.CreateSubKey('AliyunService')
    $servicesBase.Close(); $servicesBase.Dispose()

    $serviceKey.SetValue('ImagePath', $imagePath, [Microsoft.Win32.RegistryValueKind]::String)
    $serviceKey.SetValue('DisplayName', 'Aliyun Assist Service', [Microsoft.Win32.RegistryValueKind]::String)
    $serviceKey.SetValue('Start', 2, [Microsoft.Win32.RegistryValueKind]::DWord)        # Auto
    $serviceKey.SetValue('Type', 16, [Microsoft.Win32.RegistryValueKind]::DWord)        # WIN32_OWN_PROCESS
    $serviceKey.Close(); $serviceKey.Dispose()

    Write-Host "AliyunService registered successfully."
} catch {
    Write-Host "Register AliyunService failed: $($_.Exception.Message)"
    $exitCode = 1
} finally {
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    & reg unload $hivePath
    # Cleanup zip
    Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
    if ($exitCode -ne 0) { Exit $exitCode }
}
```

**Risk notes**:
- Session impact: Downloads and replaces Cloud Assistant files on the offline disk; loads and modifies the offline SYSTEM registry hive to register the AliyunService
- Persistence scope: Survives reboot -- file and registry changes persist on the target system
- Rollback: Delete the `${bootLetter}:\ProgramData\aliyun\assist` directory and remove the `AliyunService` service key from `ControlSet\Services` in the offline SYSTEM hive

### Root cause: Vminit/Cloud Assistant working directory or file permissions insufficient

**Fix operation**: Grant SYSTEM account full control permissions

```powershell
$bootLetter = '<BootLetter>'
# Select target path based on actual root cause
$targetPaths = @(
    "${bootLetter}:\ProgramData\aliyun\vminit",
    "${bootLetter}:\ProgramData\aliyun\assist"
)

foreach ($targetPath in $targetPaths) {
    if (-not (Test-Path $targetPath)) { continue }

    Write-Host "Fixing ACL for: $targetPath"
    $acl = Get-Acl $targetPath

    # Remove all Deny rules for SYSTEM
    $denyRules = $acl.Access | Where-Object {
        $_.IdentityReference.Value -eq 'NT AUTHORITY\SYSTEM' -and
        $_.AccessControlType -eq 'Deny'
    }
    foreach ($rule in $denyRules) {
        $acl.RemoveAccessRule($rule) | Out-Null
    }

    # Add SYSTEM FullControl (with inheritance)
    $identity = [System.Security.Principal.NTAccount]'NT AUTHORITY\SYSTEM'
    $rights = [System.Security.AccessControl.FileSystemRights]::FullControl
    $inherit = [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
               [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
    $propagation = [System.Security.AccessControl.PropagationFlags]::None
    $type = [System.Security.AccessControl.AccessControlType]::Allow
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $identity, $rights, $inherit, $propagation, $type
    )
    $acl.SetAccessRule($rule)
    Set-Acl -Path $targetPath -AclObject $acl

    Write-Host "ACL fixed for $targetPath"
}
```

**Risk notes**:
- Session impact: Modifies ACLs on Vminit and Cloud Assistant directories on the offline disk; grants SYSTEM account full control
- Persistence scope: Survives reboot -- ACL changes persist on the target system
- Rollback: Restore original ACLs using `icacls "${bootLetter}:\ProgramData\aliyun\vminit" /reset` and `icacls "${bootLetter}:\ProgramData\aliyun\assist" /reset`
