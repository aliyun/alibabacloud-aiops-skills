# Cloud Agent and Application Diagnosis

## Function Description

Check the installation status, version, file permissions, and runtime configuration of Vminit (Alibaba Cloud initialization service) and Cloud Assist (AliyunService); check user desktop configuration integrity.

**Input**: Boot partition drive letter, registry HIVE loaded
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

All steps in this file **MUST be executed in order**.

## Diagnostic Steps

### Step 1: Vminit Service Check

**Data Collection**:

> Collection target: Check Vminit service registration, file existence, version, permissions, and runtime flags

```powershell

# Raw registry value read (WORKFLOW-GUIDE Section 13): read ImagePath as stored;
# Get-ItemProperty would expand it against the RUNNING environment.
function Get-RawRegValue {
    param([string]$Path, [string]$Name)
    $item = Get-Item -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $item) { return $null }
    if ($ExecutionContext.SessionState.LanguageMode -eq 'ConstrainedLanguage') {
        # .NET method calls are blocked in this mode; reg query returns raw stored data
        $line = reg query $item.Name /v $Name 2>&1 | Select-String -Pattern ('\s' + $Name + '\s+REG_')
        if (-not $line) { return $null }
        return (($line | Select-Object -First 1).Line -replace ('^.*?\s' + $Name + '\s+REG_\w+\s+'), '').Trim()
    }
    $subKey = $item.Name -replace '^HKEY_LOCAL_MACHINE\\', ''
    $key = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($subKey)
    if (-not $key) { return $null }
    try {
        $key.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
    } finally { $key.Close() }
}

# 1. Service registration
$select = Get-ItemProperty "<SysPath>\Select" -ErrorAction SilentlyContinue
if (-not $select -or -not $select.Current) {
    "ERROR: SYSTEM HIVE not loaded at expected path. Run registry.md Step 2 to reload."
    return
}
$svc = Get-ItemProperty "<CcsPath>\Services\vminit" -ErrorAction SilentlyContinue
$rawImg = Get-RawRegValue "<CcsPath>\Services\vminit" 'ImagePath'
if ($svc) {
    [PSCustomObject]@{
        Name      = 'vminit'
        Start     = $svc.Start
        ImagePath = $rawImg
        Type      = $svc.Type
    }
} else {
    "Vminit service NOT registered"
}

# 2. File existence and version
if ($rawImg) {
    $imgPath = $rawImg
    # Resolve ImagePath to offline absolute path
    $imgPath = $imgPath.Trim('"')
    $imgPath = $imgPath -replace '/', '\'
    if ($imgPath -match '[A-Za-z]:\\(.+)') { $imgPath = $Matches[1] }
    if ($imgPath -match '^(.+\.\w+)') { $imgPath = $Matches[1] }
    if ($imgPath -match '(?i).*%?SystemRoot%?\\(.+)') { $imgPath = $Matches[1] }
    if ($imgPath -match '(?i)^System32') { $imgPath = "Windows\$imgPath" }
    $imgPath = "<BootLetter>:\$imgPath"

    $file = Get-Item $imgPath -ErrorAction SilentlyContinue
    if ($file) {
        [PSCustomObject]@{
            Path    = $imgPath
            Exists  = $true
            Version = $file.VersionInfo.FileVersion
            Size    = $file.Length
        }
    } else {
        [PSCustomObject]@{ Path = $imgPath; Exists = $false }
    }

    # 3. Signature verification
    if ($file) { Get-AuthenticodeSignature $imgPath | Select-Object Status }

    # 4. ACL check
    if ($file) {
        $acl = Get-Acl $imgPath
        $acl.Access | Where-Object { $_.IdentityReference -like '*SYSTEM*' } |
            Select-Object IdentityReference, FileSystemRights
        # Directory permissions
        $dir = Split-Path $imgPath
        $dirAcl = Get-Acl $dir
        $dirAcl.Access | Where-Object { $_.IdentityReference -like '*SYSTEM*' } |
            Select-Object IdentityReference, FileSystemRights
    }

    # 5. Check DONOT_RUN_CLOUDINIT_AFTER_REBOOT flag file
    $dir = Split-Path $imgPath
    $flagFile = Join-Path $dir "DONOT_RUN_CLOUDINIT_AFTER_REBOOT"
    [PSCustomObject]@{ FlagFile = $flagFile; Exists = (Test-Path $flagFile) }
}
```

**Analysis Approach**:

1. Vminit service not registered (key does not exist):
   - -> **Root cause**: Vminit not installed, **Severity**: Warning
2. Service disabled (Start = 4):
   - -> **Root cause**: Vminit service disabled, **Severity**: Warning
3. File does not exist:
   - -> **Root cause**: Vminit executable missing, **Severity**: Warning
4. Version too old (FileVersion < 2.0.1.0):
   - -> **Root cause**: Vminit version too old, **Severity**: Warning
5. SYSTEM account has no directory write permission:
   - -> **Root cause**: Vminit working directory not writable (SYSTEM has no Write permission), **Severity**: Warning
6. SYSTEM account has no file execute permission:
   - -> **Root cause**: Vminit executable not executable (SYSTEM has no Execute permission), **Severity**: Warning
7. DONOT_RUN_CLOUDINIT_AFTER_REBOOT flag file exists:
   - -> **Root cause**: Vminit has do-not-run-after-reboot flag set (residual from C++ to Go version upgrade), **Severity**: Warning

### Step 2: Cloud Assist Service Check

**Data Collection**:

> Collection target: Check AliyunService service registration, file existence, and permissions

```powershell

# Raw registry value read (WORKFLOW-GUIDE Section 13): read ImagePath as stored;
# Get-ItemProperty would expand it against the RUNNING environment.
function Get-RawRegValue {
    param([string]$Path, [string]$Name)
    $item = Get-Item -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $item) { return $null }
    if ($ExecutionContext.SessionState.LanguageMode -eq 'ConstrainedLanguage') {
        # .NET method calls are blocked in this mode; reg query returns raw stored data
        $line = reg query $item.Name /v $Name 2>&1 | Select-String -Pattern ('\s' + $Name + '\s+REG_')
        if (-not $line) { return $null }
        return (($line | Select-Object -First 1).Line -replace ('^.*?\s' + $Name + '\s+REG_\w+\s+'), '').Trim()
    }
    $subKey = $item.Name -replace '^HKEY_LOCAL_MACHINE\\', ''
    $key = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($subKey)
    if (-not $key) { return $null }
    try {
        $key.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
    } finally { $key.Close() }
}

# 1. Service registration
$select = Get-ItemProperty "<SysPath>\Select" -ErrorAction SilentlyContinue
if (-not $select -or -not $select.Current) {
    "ERROR: SYSTEM HIVE not loaded at expected path. Run registry.md Step 2 to reload."
    return
}
$svc = Get-ItemProperty "<CcsPath>\Services\AliyunService" -ErrorAction SilentlyContinue
$rawImg = Get-RawRegValue "<CcsPath>\Services\AliyunService" 'ImagePath'
if ($svc) {
    [PSCustomObject]@{
        Name      = 'AliyunService'
        Start     = $svc.Start
        ImagePath = $rawImg
        Type      = $svc.Type
    }
} else {
    "AliyunService NOT registered"
}

# 2. File existence
if ($rawImg) {
    $imgPath = $rawImg
    # Resolve ImagePath to offline absolute path
    $imgPath = $imgPath.Trim('"')
    $imgPath = $imgPath -replace '/', '\'
    if ($imgPath -match '[A-Za-z]:\\(.+)') { $imgPath = $Matches[1] }
    if ($imgPath -match '^(.+\.\w+)') { $imgPath = $Matches[1] }
    if ($imgPath -match '(?i).*%?SystemRoot%?\\(.+)') { $imgPath = $Matches[1] }
    if ($imgPath -match '(?i)^System32') { $imgPath = "Windows\$imgPath" }
    $imgPath = "<BootLetter>:\$imgPath"

    $file = Get-Item $imgPath -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        Path   = $imgPath
        Exists = ($null -ne $file)
        Size   = if ($file) { $file.Length } else { 0 }
    }

    # 3. ACL check
    if ($file) {
        $acl = Get-Acl $imgPath
        $acl.Access | Where-Object { $_.IdentityReference -like '*SYSTEM*' } |
            Select-Object IdentityReference, FileSystemRights
        $dir = Split-Path $imgPath
        $dirAcl = Get-Acl $dir
        $dirAcl.Access | Where-Object { $_.IdentityReference -like '*SYSTEM*' } |
            Select-Object IdentityReference, FileSystemRights
    }
}
```

**Analysis Approach**:

1. AliyunService service not registered:
   - -> **Root cause**: Cloud Assist not installed, **Severity**: Warning
2. File does not exist:
   - -> **Root cause**: Cloud Assist executable missing, **Severity**: Warning
3. SYSTEM account has no directory write permission:
   - -> **Root cause**: Cloud Assist working directory not writable, **Severity**: Warning
4. SYSTEM account has no file execute permission:
   - -> **Root cause**: Cloud Assist executable not executable, **Severity**: Warning

### Step 3: User Desktop Configuration Check

**Data Collection**:

> Collection target: Enumerate all user directories and check whether desktop configuration files exist for each user

```powershell

# Enumerate all user profile directories and check desktop.ini
$usersPath = "<BootLetter>:\Users"
$userDirs = Get-ChildItem $usersPath -Directory -ErrorAction SilentlyContinue
$userDirs | ForEach-Object {
    $dir = $_
    $iniPath = Join-Path $dir.FullName "Desktop\desktop.ini"
    [PSCustomObject]@{
        User   = $dir.Name
        Path   = $iniPath
        Exists = (Test-Path $iniPath)
    }
} | Format-List
```

**Analysis Approach**:

1. No Desktop\desktop.ini found in any user directory:
   - -> **Root cause**: User desktop configuration missing, **Severity**: Info
   - May affect user login experience

## Cross-References

| Type | Trigger Condition | Target |
|------|-------------------|--------|
| Prerequisite | Requires registry HIVE to be loaded -- this file triggers the on-demand registry tier ([registry.md](references/offline/registry.md)) if not yet executed | -- |
| Conditional jump | Vminit driver installation failed | -> [driver.md](references/offline/driver.md) Step 2 |
| Conditional jump | Cloud Assist binary missing, needs reinstallation | -> Inform user that reinstallation requires an online environment |
| Termination | This file does not confirm root cause | -> Record Info-level conclusion, return to main sequence to continue |


## Fix Recommendations

Fix plans for root causes confirmed in this file are described in [cloud-agent.md](references/offline/fixes/cloud-agent.md).
