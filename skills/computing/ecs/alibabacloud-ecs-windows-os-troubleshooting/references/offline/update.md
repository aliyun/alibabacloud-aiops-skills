# Update and Patch Status Diagnostics

## Function Description

Checks Windows Update server configuration, installed problematic patches (known-bad hotfix), SHA-256 patch requirement (Win7/2008R2), and pending update package status.

**Input**: Boot partition drive letter, registry HIVE already loaded
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

All steps in this file **MUST be executed in sequence**.

## Diagnostic Steps

### Step 1: Windows Update Server Configuration Check

**Data Collection**:

> Collection target: Check WSUS configuration and connectivity

```powershell

$wuPolicy = Get-ItemProperty "<SoftPath>\Policies\Microsoft\Windows\WindowsUpdate" -ErrorAction SilentlyContinue
$wuAU = Get-ItemProperty "<SoftPath>\Policies\Microsoft\Windows\WindowsUpdate\AU" -ErrorAction SilentlyContinue

[PSCustomObject]@{
    WUServer       = $wuPolicy.WUServer
    WUStatusServer = $wuPolicy.WUStatusServer
    UseWUServer    = $wuAU.UseWUServer
}
```

**Analysis**:

1. UseWUServer = 1 but WUServer or WUStatusServer is empty:
   - -> **Root cause**: Windows Update server configuration error, **Severity**: Warning
2. WUServer is configured but unreachable (record address for reference, cannot actually Ping in offline environment):
   - -> **Root cause**: Windows Update server unreachable, **Severity**: Info (cannot verify offline, flagged as pending confirmation)

### Step 2: Problematic Patch Check

> **DISM Mandatory Rule**: This step calls `Get-WindowsPackage`, MUST strictly follow the two rules in [dism.md](references/offline/dism.md) "DISM Mandatory Rules" -- after the call, HIVE is unloaded, before entering the next step MUST immediately reload HIVE per [registry.md](references/offline/registry.md) Step 2.
>
> **No Substitution**: Do not substitute `ntoskrnl.exe` version number, registry query, or any other method for this step. Reason: `Get-WindowsPackage` returns the CBS package manager's **complete package state** (Installed/Staged/Superseded/InstallPending), which is the only data source for identifying "pending update causing boot failure"; registry queries cannot obtain equivalent information.

**Data Collection**:

> Collection target: Use DISM to check installed known problematic patches

```powershell

# DISM disk cache (see dism.md "Standard Disk Cache Pattern"): get package list, for reuse by Step 4
$cacheDir = Join-Path $env:SystemRoot 'Temp\diag-cache'
New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
$cacheFile = Join-Path $cacheDir 'WindowsPackage.json'
if (Test-Path $cacheFile) {
    $packages = Get-Content $cacheFile -Raw | ConvertFrom-Json
} else {
    $packages = Get-WindowsPackage -Path "<BootLetter>:\"
    $packages | ConvertTo-Json -Depth 4 | Set-Content $cacheFile -Encoding UTF8
}
$packages | Format-List PackageName, PackageState, InstallTime

# Known problematic patch list
$badKBs = @(
    'KB5009624', 'KB5009595', 'KB5009546', 'KB5009557', 'KB5009555',
    'KB5014738', 'KB5014702', 'KB5014692', 'KB5014678', 'KB5060842'
)

$badKBs | ForEach-Object {
    $kb = $_
    $found = $packages | Where-Object { $_.PackageName -match $kb }
    if ($found) {
        [PSCustomObject]@{ KB = $kb; Status = 'Installed'; PackageName = $found.PackageName }
    }
} | Format-List
```

**Analysis**:

1. Known problematic patch installed:
   - -> **Root cause**: Problematic patch installed (may cause boot failure), **Severity**: Critical
   - The involved patches are KBs known to potentially cause BSOD such as 0xc000021a

### Step 3: SHA-256 Patch Requirement Check (Win7/2008R2)

**Data Collection**:

> Collection target: Check whether Win7/2008R2 kernel includes SHA-256 support

```powershell

# Get ntoskrnl.exe version
$ntoskrnl = Get-Item "<BootLetter>:\Windows\System32\ntoskrnl.exe" -ErrorAction SilentlyContinue
if ($ntoskrnl) {
    $ver = $ntoskrnl.VersionInfo.FileVersion
    [PSCustomObject]@{
        Path    = $ntoskrnl.FullName
        Version = $ver
    }
}
```

**Analysis**:

1. ntoskrnl.exe version < 6.1.7601.18741 (Win7/2008R2 kernel):
   - -> **Root cause**: Missing SHA-256 support patch (KB3033929), **Severity**: Warning
   - Reference: https://support.microsoft.com/en-us/topic/microsoft-security-advisory-availability-of-sha-2-code-signing-support-for-windows-7-and-windows-server-2008-r2
2. ntoskrnl.exe version >= 6.2 (Win8+) -> No check needed

### Step 4: Pending Update Package Status Check

> **DISM Mandatory Rule**: This step preferentially reuses the `WindowsPackage.json` disk cache from Step 2 (see [dism.md](references/offline/dism.md) "Standard Disk Cache Pattern"); if cache miss and `Get-WindowsPackage` was actually called, MUST follow [dism.md](references/offline/dism.md) "DISM Mandatory Rules" to immediately reload HIVE per [registry.md](references/offline/registry.md) Step 2 after the call.

**Data Collection**:

> Collection target: Check for pending updates, CBS packages, and WinSxS pending.xml

```powershell

# Check PendingFileRenameOperations
$smPath = "<CcsPath>\Control\Session Manager"
$pendingRename = (Get-ItemProperty $smPath -ErrorAction SilentlyContinue).PendingFileRenameOperations
"PendingFileRenameOperations count: $(if ($pendingRename) { $pendingRename.Count } else { 0 })"

# Check CBS pending key
$cbsPath = "<SoftPath>\Microsoft\Windows\CurrentVersion\Component Based Servicing"
$cbsPending = Get-ChildItem "${cbsPath}\PackagesPending" -ErrorAction SilentlyContinue
"CBS PackagesPending count: $(if ($cbsPending) { $cbsPending.Count } else { 0 })"

# Check WindowsUpdate pending key
$wuauPath = "<SoftPath>\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update"
$rebootRequired = Test-Path "${wuauPath}\RebootRequired" -ErrorAction SilentlyContinue
"WU RebootRequired: $rebootRequired"

# Check WinSxS\pending.xml
$pendingXml = "<BootLetter>:\Windows\WinSxS\pending.xml"
$xmlExists = Test-Path $pendingXml
"WinSxS\pending.xml exists: $xmlExists"
if ($xmlExists) {
    $xmlInfo = Get-Item $pendingXml
    "Size: $($xmlInfo.Length) bytes, LastWrite: $($xmlInfo.LastWriteTime)"
}

# Get pending packages via DISM module (see dism.md for package query)
# DISM disk cache: prefer reusing WindowsPackage.json persisted by Step 2; if cache miss, call DISM and write back
$cacheDir = Join-Path $env:SystemRoot 'Temp\diag-cache'
$cacheFile = Join-Path $cacheDir 'WindowsPackage.json'
if (Test-Path $cacheFile) {
    $packages = Get-Content $cacheFile -Raw | ConvertFrom-Json
} else {
    New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
    $packages = Get-WindowsPackage -Path "<BootLetter>:\"
    $packages | ConvertTo-Json -Depth 4 | Set-Content $cacheFile -Encoding UTF8
}
$packages | Where-Object { $_.PackageState -match 'Pending' } | Format-List PackageName, PackageState
```

**Analysis**:

1. CBS PackagesPending key exists or WU RebootRequired key exists -> Pending reboot required
2. WinSxS\pending.xml exists -> Component service has pending operations at reboot
3. Any pending condition met -> **Root cause**: Pending system updates exist (may cause boot abnormality), **Severity**: Warning
4. DISM output has packages with "Install Pending" / "Uninstall Pending" status:
   - -> **Root cause**: Update package installation/uninstallation not completed, **Severity**: Warning
   - List specific package names and status as evidence

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Prerequisite | Registry HIVE must be loaded -- this file triggers the on-demand registry tier ([registry.md](references/offline/registry.md)) if not yet executed | -- |
| Prerequisite | DISM uninstall update package operation | -> [dism.md](references/offline/dism.md) |
| Conditional jump | Update caused critical driver replacement | -> [driver.md](references/offline/driver.md) |
| Conditional jump | Update interruption caused component store corruption | -> [dism.md](references/offline/dism.md) (SFC/DISM repair) |


## Fix Recommendations

The fix plans corresponding to the root causes confirmed in this file are in [update.md](references/offline/fixes/update.md).
