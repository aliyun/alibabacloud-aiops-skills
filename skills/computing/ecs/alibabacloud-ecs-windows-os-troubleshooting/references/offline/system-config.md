# System Configuration and Service Diagnostics

## Function Description

Checks operating system version information, Sysprep state, system environment variables, critical system file integrity, crash dump configuration, memory management settings, IFEO stack configuration, scheduled task execution state, BootExecute abnormal entries, time zone configuration, CcProtect abnormal services, and Winlogon/Shell configuration with shell-critical file integrity (stage P4/P5 coverage). Also checks Auto-Start services with ErrorControl set to Critical/Severe, and third-party services/drivers with boot type Boot/System (Start=0/1).

**Input**: Boot partition drive letter, registry HIVE already loaded
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

All steps in this file **MUST be executed in sequence**.

Stage attribution (per the Boot/Session Stage Determination in SKILL.md): Steps 2/8/11/13 serve P2/P3 (kernel load / session init); Step 7 and Step 14 serve P4/P5 (Winlogon/logon UI and Shell/user desktop). When routed here by a specific stage, still run the full sequence -- the steps are cheap and cross-stage findings are common.

## Diagnostic Steps

### Step 1: Operating System Version Information

**Data Collection**:

> Collection target: Obtain OS version, product name, and architecture information

```powershell

# OS version
$cv = Get-ItemProperty "<SoftPath>\Microsoft\Windows NT\CurrentVersion" -ErrorAction SilentlyContinue
$osInfo = [PSCustomObject]@{
    ProductName    = $cv.ProductName
    Major          = $cv.CurrentMajorVersionNumber
    Minor          = $cv.CurrentMinorVersionNumber
    Build          = $cv.CurrentBuildNumber
    UBR            = $cv.UBR
    DisplayVersion = $cv.DisplayVersion
    EditionID      = $cv.EditionID
    InstallType    = $cv.InstallationType
}
$osInfo

# Architecture
$env = Get-ItemProperty "<CcsPath>\Control\Session Manager\Environment" -ErrorAction SilentlyContinue
$env.PROCESSOR_ARCHITECTURE

# Cache for downstream version/architecture-related checks
# Context memory: Model MUST remember $osInfo and $env.PROCESSOR_ARCHITECTURE, subsequent steps read from session memory when needed, no repeated collection
```

**Analysis**:

1. Version compatibility handling:
   - When Major=0 and Minor=0 (Win2012R2 and earlier), fall back to reading `CurrentVersion` string to parse Major.Minor
   - When UBR=0 or does not exist, try parsing from `BuildLabEx` field (format `Build.UBR.arch...`, take second segment)
2. OS version too old (Major < 6 or Major=6 and Minor <= 3, i.e., Win2008R2 and below):
   - -> **Root cause**: Operating system version too old, **Severity**: Warning
3. Record OS info (including UBR, DisplayVersion, EditionID) for version-related judgments in subsequent steps

### Step 2: Sysprep State Check

**Data Collection**:

> Collection target: Check system sealing/deployment state

```powershell

$state = Get-ItemProperty "<SoftPath>\Microsoft\Windows\CurrentVersion\Setup\State" -ErrorAction SilentlyContinue
$state.ImageState

# Context memory: Model MUST remember ImageState value, network.md Step 2 reads from session memory when needed, no repeated collection

# If UNDEPLOYABLE, get Sysprep error log
if ($state.ImageState -eq 'IMAGE_STATE_UNDEPLOYABLE') {
    $logPath = "<BootLetter>:\Windows\System32\Sysprep\Panther\setuperr.log"
    if (Test-Path $logPath) {
        Get-Content $logPath -Tail 50
    }
}
```

**Analysis**:

1. ImageState = IMAGE_STATE_UNDEPLOYABLE:
   - -> **Root cause**: Sysprep unrecoverable error (system undeployable), **Severity**: Critical
   - Attach last 50 lines of setuperr.log as evidence
2. ImageState = IMAGE_STATE_GENERALIZE_RESEAL_TO_AUDIT or IMAGE_STATE_SPECIALIZE_RESEAL_TO_AUDIT:
   - -> **Root cause**: System is in audit mode, **Severity**: Warning (may cause abnormal first boot behavior)

### Step 3: System PATH Environment Variable Check

**Data Collection**:

> Collection target: Check whether system PATH environment variable includes required Windows directories

```powershell

$env = Get-ItemProperty "<CcsPath>\Control\Session Manager\Environment" -ErrorAction SilentlyContinue
$pathValue = $env.Path
"Current PATH: $pathValue"

# Check required paths
$required = @(
    'windows',
    'windows\system32',
    'windows\system32\windowspowershell\v1.0',
    'windows\system32\wbem'
)
$paths = $pathValue.ToLower() -split ';'
$required | ForEach-Object {
    $req = $_
    $found = $paths | Where-Object {
        ($_ -replace '%systemroot%','windows' -replace 'c:\\windows','windows').TrimEnd('\') -like "*$req"
    }
    [PSCustomObject]@{ Required = $req; Found = ($null -ne $found) }
} | Format-Table -AutoSize
```

**Analysis**:

1. Any of the following paths missing -> **Root cause**: System PATH environment variable tampered, **Severity**: Warning
   - `%SystemRoot%` or `C:\Windows`
   - `%SystemRoot%\System32`
   - `%SystemRoot%\System32\WindowsPowerShell\v1.0`
   - `%SystemRoot%\System32\Wbem`

### Step 4: Critical System File Integrity Check

**Data Collection**:

> Collection target: Check existence and SYSTEM account execution permission of critical system executables and DLLs

```powershell
$sys32 = "<BootLetter>:\Windows\System32"

$criticalFiles = @(
    "$sys32\cmd.exe", "$sys32\reg.exe", "$sys32\schtasks.exe",
    "$sys32\sc.exe", "$sys32\net.exe", "$sys32\netsh.exe",
    "$sys32\wbem\wmiprvse.exe", "$sys32\msiexec.exe",
    "$sys32\bcdedit.exe", "$sys32\shutdown.exe",
    "$sys32\ntdll.dll", "$sys32\kernel32.dll", "$sys32\advapi32.dll"
)

$criticalFiles | ForEach-Object {
    $f = $_
    $info = Get-Item $f -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        File   = Split-Path $f -Leaf
        Exists = ($null -ne $info)
        Size   = if ($info) { $info.Length } else { 0 }
    }
} | Format-Table -AutoSize
```

**Analysis**:

1. Critical .exe file missing -> **Root cause**: System command missing, **Severity**: Warning
2. Critical .dll file missing -> **Root cause**: System file missing, **Severity**: Critical
3. File exists but SYSTEM account has no execution permission -> **Root cause**: System command not executable (ACL tampered), **Severity**: Warning

### Step 5: Crash Dump Configuration Check

**Data Collection**:

> Collection target: Check system crash dump (CrashDump) configuration

```powershell

$crashCtrl = Get-ItemProperty "<CcsPath>\Control\CrashControl" -ErrorAction SilentlyContinue
[PSCustomObject]@{
    CrashDumpEnabled = $crashCtrl.CrashDumpEnabled
    DumpFile         = $crashCtrl.DumpFile
    MinidumpDir      = $crashCtrl.MinidumpDir
    AutoReboot       = $crashCtrl.AutoReboot
}
```

**Analysis**:

1. CrashDumpEnabled = 0 -> **Root cause**: Crash dump not enabled, **Severity**: Warning
   - Does not affect boot, but affects troubleshooting capability after BSOD

### Step 6: Memory Management Configuration Check

**Data Collection**:

> Collection target: Check page file configuration and Spectre mitigation settings

```powershell

$mm = Get-ItemProperty "<CcsPath>\Control\Session Manager\Memory Management" -ErrorAction SilentlyContinue
[PSCustomObject]@{
    PagingFiles                 = $mm.PagingFiles
    ExistingPageFiles           = $mm.ExistingPageFiles
    FeatureSettingsOverride     = $mm.FeatureSettingsOverride
    FeatureSettingsOverrideMask  = $mm.FeatureSettingsOverrideMask
}
```

**Analysis**:

1. Both PagingFiles and ExistingPageFiles empty -> **Root cause**: Page file not configured, **Severity**: Warning
2. FeatureSettingsOverrideMask = 0x2048 and FeatureSettingsOverride = 0x3:
   - -> **Root cause**: Hyper-threading disabled via registry (Spectre mitigation), **Severity**: Info (inform user of possible performance impact)

### Step 7: IFEO MinimumStackCommitInBytes Check

**Data Collection**:

> Collection target: Check abnormal stack size settings in Image File Execution Options

```powershell

$ifeoPath = "<SoftPath>\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
$items = Get-ChildItem $ifeoPath -ErrorAction SilentlyContinue
$items | ForEach-Object {
    $item = $_
    $props = Get-ItemProperty $item.PSPath -ErrorAction SilentlyContinue
    if ($props.MinimumStackCommitInBytes -and $props.MinimumStackCommitInBytes -ge 0x02000000) {
        [PSCustomObject]@{
            Name  = $item.PSChildName
            Stack = '0x{0:X}' -f $props.MinimumStackCommitInBytes
        }
    }
} | Format-Table -AutoSize
```

**Analysis**:

1. MinimumStackCommitInBytes >= 0x02000000 (32MB):
   - -> **Root cause**: IFEO stack commit size too large (may cause process launch failure), **Severity**: Warning
   - Common in malware or misconfiguration

### Step 8: Auto-Start Critical Error Control Services

**Data Collection**:

> Collection target: Check abnormal Auto-Start services with ErrorControl set to Critical/Severe

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

$services = Get-ChildItem "<CcsPath>\Services" -ErrorAction SilentlyContinue
$services | ForEach-Object {
    $svc = $_
    $props = Get-ItemProperty $svc.PSPath -ErrorAction SilentlyContinue
    # Type contains WIN32 (0x10 or 0x20), Start=2(Auto), ErrorControl>=2(Severe/Critical)
    if (($props.Type -band 0x30) -ne 0 -and $props.Start -eq 2 -and $props.ErrorControl -ge 2) {
        [PSCustomObject]@{
            Name         = $svc.PSChildName
            Start        = $props.Start
            ErrorControl = $props.ErrorControl
            ImagePath    = (Get-RawRegValue $svc.PSPath 'ImagePath')
        }
    }
} | Format-List
```

**Analysis**:

1. Auto-Start service ErrorControl = 3 (Critical) or 2 (Severe):
   - If this service fails to start, Windows will trigger Last Known Good rollback or BSOD
   - -> **Root cause**: Auto-Start service set to Critical/Severe error control level, **Severity**: Warning (flagged as risk item)

### Step 9: Time Zone Configuration Check

**Data Collection**:

> Collection target: Check time zone and RTC clock configuration

```powershell

$tz = Get-ItemProperty "<CcsPath>\Control\TimeZoneInformation" -ErrorAction SilentlyContinue
[PSCustomObject]@{
    TimeZoneKeyName     = $tz.TimeZoneKeyName
    RealTimeIsUniversal = $tz.RealTimeIsUniversal
}
```

**Analysis**:

1. RealTimeIsUniversal = 0 or does not exist -> **Root cause**: RTC clock is local time (not UTC), **Severity**: Info
   - Alibaba Cloud ECS uses UTC time by default; local time may cause time deviation

### Step 10: Scheduled Task Execution State Check

**Data Collection**:

> Collection target: Get last execution result of scheduled tasks from SOFTWARE registry

```powershell

# Scheduled task registry location
$taskRoot = "<SoftPath>\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tasks"
$treeRoot = "<SoftPath>\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tree"

# Iterate Tasks subkeys for execution history
$failedTasks = @()
Get-ChildItem $taskRoot -ErrorAction SilentlyContinue | ForEach-Object {
    $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
    # DynamicInfo binary field contains LastActionResult (offset 28, 4 bytes LE)
    $dynInfo = $props.DynamicInfo
    if ($dynInfo -and $dynInfo.Length -ge 32) {
        $lastResult = [BitConverter]::ToUInt32($dynInfo, 28)
        if ($lastResult -ne 0) {
            $failedTasks += [PSCustomObject]@{
                TaskGuid   = $_.PSChildName
                Path       = $props.Path
                LastResult = '0x{0:X8}' -f $lastResult
            }
        }
    }
}
$failedTasks | Format-List
```

**Analysis**:

1. LastActionResult != 0 (task last execution failed):
   - -> **Root cause**: Scheduled task execution failed, **Severity**: Info
   - Record failed task path and result code for manual investigation
2. This is auxiliary information collection, does not directly block boot, but may reflect potential system runtime issues

### Step 11: BootExecute Abnormal Entry Check

**Data Collection**:

> Collection target: Read Session Manager BootExecute value, check for non-standard entries and their binary file existence

```powershell

$smPath = "<CcsPath>\Control\Session Manager"
$props = Get-ItemProperty $smPath -Name BootExecute -ErrorAction SilentlyContinue
$bootExec = $props.BootExecute

# Standard value filter
$standard = @('autocheck autochk *')
$nonStandard = @()
foreach ($entry in $bootExec) {
    $trimmed = $entry.Trim()
    if ($trimmed -eq '' -or $standard -contains $trimmed) { continue }
    # Check corresponding binary file existence
    $exeName = ($trimmed -split '\s+')[0]
    # BootExecute programs reside under System32
    $exePath = "<BootLetter>:\Windows\System32\$exeName"
    if (-not $exePath.EndsWith('.exe')) { $exePath += '.exe' }
    $exists = Test-Path $exePath -ErrorAction SilentlyContinue
    $nonStandard += [PSCustomObject]@{
        Entry    = $trimmed
        Binary   = $exePath
        Exists   = $exists
    }
}

[PSCustomObject]@{ BootExecute = $bootExec; StandardOnly = ($nonStandard.Count -eq 0) }
$nonStandard | Format-List
```

**Analysis**:

1. Check whether BootExecute contains non-standard entries:
   - Normal: only contains `autocheck autochk *`
   - Abnormal (non-standard entry and binary file does not exist) -> **Root cause**: BootExecute abnormal entry references non-existent program, **Severity**: Critical (Smss execution failure can cause system hang or BSOD)
   - Abnormal (non-standard entry but binary file exists) -> **Root cause**: BootExecute contains non-standard program, **Severity**: Warning (may be security software or disk tool residual)
2. BootExecute is empty or missing:
   - -> **Root cause**: BootExecute value missing (autochk will not run), **Severity**: Info

### Step 12: CcProtect Abnormal Service Check

**Data Collection**:

> Collection target: Check existence and startup mode of `Services\CcProtect` service

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

$svcPath = "<CcsPath>\Services\CcProtect"
$svc = Get-ItemProperty $svcPath -ErrorAction SilentlyContinue
if ($svc) {
    [PSCustomObject]@{
        ServiceName = 'CcProtect'
        Start       = $svc.Start
        ImagePath   = (Get-RawRegValue $svcPath 'ImagePath')
        Type        = $svc.Type
    }
} else {
    [PSCustomObject]@{
        ServiceName = 'CcProtect'
        Exists      = $false
    }
}
```

**Analysis**:

1. CcProtect service exists and Start != 4 (not disabled):
   - -> **Root cause**: Third-party file filter driver CcProtect is active (historical experience shows this driver may be abused; mounting on the storage stack can cause system sluggishness, elevated I/O latency), **Severity**: Warning
2. CcProtect service does not exist or Start == 4:
   - No action needed

### Step 13: Boot/System-Start Third-Party Service Check

**Data Collection**:

> Collection target: Enumerate services/drivers with boot type Boot (Start=0) or System (Start=1), exclude built-in Microsoft entries, and output suspected third-party entries. These entries load before session manager initialization / in early kernel phase; if a third-party driver has a corrupted or incompatible file, it can directly cause BSOD (0x7B/0x7E, etc.) or boot hang

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

# Enumerate Boot-Start (0) and System-Start (1) services, filter out built-in Microsoft entries
$services = Get-ChildItem "<CcsPath>\Services" -ErrorAction SilentlyContinue
$suspects = @()
$services | ForEach-Object {
    $svc = $_
    $props = Get-ItemProperty $svc.PSPath -ErrorAction SilentlyContinue
    $start = $props.Start
    if ($null -eq $start -or ($start -ne 0 -and $start -ne 1)) { return }
    $image = "$(Get-RawRegValue $svc.PSPath 'ImagePath')"
    # Treat driver entries without ImagePath as boot-start drivers, keep for review
    $pathOnly = "$($image -replace '\\SystemRoot\\', '<BootLetter>:\' -replace '\?\?\\', '<BootLetter>:\')"
    $inSystem32 = $pathOnly -match '(?i)\\windows\\system32\\'
    $msGroup = "$($props.Group)"
    # Heuristics for built-in Microsoft entries: system32 path, no binary path (core driver),
    # or well-known boot groups (e.g. Boot Bus Extender, System Bus Extender, SCSI miniport)
    $looksBuiltin = $inSystem32 -or [string]::IsNullOrWhiteSpace($image) -or ($msGroup -ne '')
    if ($looksBuiltin) { return }
    $exists = $false
    if ($pathOnly -ne '') { $exists = Test-Path $pathOnly -ErrorAction SilentlyContinue }
    $suspects += [PSCustomObject]@{
        Name       = $svc.PSChildName
        Start      = $start
        Type       = $props.Type
        ErrorControl = $props.ErrorControl
        Group      = $msGroup
        ImagePath  = $image
        FileExists = $exists
    }
}
$suspects | Format-List
"Suspect count: $($suspects.Count)"
```

**Analysis**:

1. Confirm each suspected third-party entry in the output:
   - ImagePath points to third-party software directory (not `\Windows\System32`, e.g., security software, backup software, virtualization/storage tool driver directory) -> Confirmed as third-party Boot/System-Start service
   - Cross-reference with user's symptom (cannot boot after installing certain security software/driver, BSOD fault module is non-Microsoft file)
2. Determination:
   - Third-party Boot/System-Start service exists and its file does not exist (FileExists=False) -> **Root cause**: Boot-Start third-party driver file missing (BootStartDriverMissing), **Severity**: Critical
   - Third-party Boot/System-Start service exists and symptoms are related to it (file exists but version incompatible/corrupted, or user confirms abnormality started after installation) -> **Root cause**: Boot-Start third-party driver abnormal (BootStartThirdPartyDriver), **Severity**: Warning (flagged as high-priority investigation item)
   - No suspected third-party entries -> No findings in this step, continue subsequent investigation
3. Note: This check is heuristic filtering and may miss third-party drivers disguised in the system32 directory; if output is empty but the BSOD fault module is a third-party driver name, further comparison should be made with the driver list in driver.md

### Step 14: Winlogon/Shell Configuration Check (Stage P4/P5)

**Data Collection**:

> Collection target: Read Winlogon Shell/Userinit/AutoRestartShell values as stored (path-like values use raw read), check existence of shell-critical files, and detect IFEO Debugger hijacks on shell-critical images

```powershell

# Raw registry value read (WORKFLOW-GUIDE Section 13): read values as stored;
# Get-ItemProperty would expand them against the RUNNING environment.
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

# Winlogon key: Shell/Userinit decide what runs after logon (P5), misconfiguration can also break the logon UI (P4)
$wlPath = "<SoftPath>\Microsoft\Windows NT\CurrentVersion\Winlogon"
$wl = Get-ItemProperty $wlPath -ErrorAction SilentlyContinue
[PSCustomObject]@{
    Shell            = (Get-RawRegValue $wlPath 'Shell')
    Userinit         = (Get-RawRegValue $wlPath 'Userinit')
    AutoRestartShell = $wl.AutoRestartShell
} | Format-List

# Shell-critical file existence
$sys32 = "<BootLetter>:\Windows\System32"
$shellFiles = @(
    "$sys32\LogonUI.exe",
    "$sys32\userinit.exe",
    "$sys32\winlogon.exe",
    "<BootLetter>:\Windows\explorer.exe"
)
$shellFiles | ForEach-Object {
    $f = $_
    $info = Get-Item $f -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        File    = Split-Path $f -Leaf
        Exists  = ($null -ne $info)
        Version = if ($info) { $info.VersionInfo.FileVersion } else { '' }
    }
} | Format-Table -AutoSize

# IFEO Debugger hijack on shell-critical images (classic P5 shell hijack)
$ifeoPath = "<SoftPath>\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
foreach ($img in @('explorer.exe', 'userinit.exe', 'LogonUI.exe', 'winlogon.exe')) {
    $dbg = Get-ItemProperty "$ifeoPath\$img" -Name Debugger -ErrorAction SilentlyContinue
    if ($dbg.Debugger) {
        [PSCustomObject]@{ Image = $img; Debugger = $dbg.Debugger }
    }
}
```

**Analysis**:

1. Shell value is not `explorer.exe` (or contains extra entries) -> **Root cause**: Shell hijack/tampering (post-logon black screen, no desktop), **Severity**: Critical, stage P5
2. Userinit value deviates from the standard `C:\Windows\system32\userinit.exe,` (extra entries, wrong path) -> **Root cause**: Userinit tampering, **Severity**: Critical, stage P5
3. AutoRestartShell = 0 -> **Root cause**: explorer auto-restart disabled (desktop gone after explorer crash), **Severity**: Warning, stage P5
4. LogonUI.exe or winlogon.exe missing -> **Root cause**: logon UI component missing (black screen after/instead of logon UI), **Severity**: Critical, stage P4
5. userinit.exe or explorer.exe missing -> **Root cause**: shell component missing, **Severity**: Critical, stage P5
6. IFEO Debugger present on any shell-critical image -> **Root cause**: IFEO shell hijack (target image replaced by debugger program), **Severity**: Critical, stage P5
7. Display driver suspicion (logon UI flashes then black, resolution-dependent) -> this file does not cover display drivers; cross-reference to driver.md

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Prerequisite | Registry HIVE must be loaded -- this file triggers the on-demand registry tier ([registry.md](references/offline/registry.md)) if not yet executed | -- |
| Related | Sysprep state affects network IP check | -> [network.md](references/offline/network.md) |
| Related | Page file configuration affects crash dump | -- |
| Conditional jump | Missing critical patch (KB3033929) | -> [update.md](references/offline/update.md) Step 3 |
| Conditional jump | IFEO hijack shows signs of malware | -> Inform user of possible security risk |
| Conditional jump | Vminit/AliyunService abnormal | -> [cloud-agent.md](references/offline/cloud-agent.md) |
| Conditional jump | Logon UI flashes then black, display driver suspicion (stage P4) | -> [driver.md](references/offline/driver.md) |
| Conditional jump | Pending update packages | -> [update.md](references/offline/update.md) Step 4/5 |


## Fix Recommendations

The fix plans corresponding to the root causes confirmed in this file are in [system-config.md](references/offline/fixes/system-config.md).
