# DISM Offline Operations

## Function Description

Provides a unified interface for DISM offline image operations, including driver query/add, package query/uninstall, and Feature query. All DISM operations will cause already-loaded registry HIVEs to be unloaded and must be reloaded afterward.

**Input**: Boot partition drive letter
**Output**: DISM command output results

## Step Selection Guide

This file is a tool interface reference (not a diagnostic step), with no step selection logic. Call the corresponding operations based on the diagnostic needs of other troubleshooting files:

- **Driver query/add**: Called when driver.md or network.md needs to check or fix drivers
- **Package query/uninstall**: Called when update.md needs to remove problematic updates
- **Note**: DISM operations will unload already-loaded registry HIVEs. After calling during the diagnostic phase, you MUST immediately re-execute the registry.md Step 2 load script to remount the HIVE; during the fix phase, reloading is not required (see "DISM Mandatory Rules" below for details)

## DISM Mandatory Rules

Any DISM cmdlet (`Get-WindowsDriver`, `Get-WindowsPackage`, `Add-WindowsDriver`, `Remove-WindowsPackage`, `Get-WindowsOptionalFeature`) call MUST follow the rules below. The workflow is fixed; callers must not skip steps, must not deviate, and must not bypass for "performance" or "skip" reasons.

### Rule 0: Do Not Skip DISM Steps

Diagnostic Steps that reference DISM **must not be skipped**. They must not be bypassed for any of the following reasons:
- "`reg query` can obtain equivalent information" -- **No**, DISM provides driver package metadata and CBS package status that cannot be obtained through the registry
- "Too much overhead in remote execution scenarios" -- DISM cmdlets are single-line commands that can be executed remotely directly
- "Previous steps already confirmed driver/patch is normal" -- Different steps check different dimensions and are not interchangeable

### Rule 1: HIVE Mount Path MUST Follow Fixed Path Rules

All registry mount operations MUST use a fixed path format:

```
reg load "HKLM\{bf1a281b-ad7b-4476-ac95-f47682990ce7}<Absolute path to HIVE file, backslashes replaced with forward slashes>" <HIVE file path>
```

The GUID and path concatenation rules are consistent with DISM's internal occupancy path; inconsistency will cause DISM calls to fail. See [registry.md](references/offline/registry.md) Step 2. Callers MUST directly call DISM cmdlets and **must not** assume failure and use alternative paths such as registry enumeration.

### Rule 2: MUST Remount HIVE After `Get-WindowsPackage` / `Get-WindowsDriver` Calls (Diagnostic Phase Only)

After a DISM cmdlet returns, all loaded HIVEs will inevitably be unloaded by DISM internally.

- **Diagnostic phase**: Callers MUST immediately re-execute the [registry.md](references/offline/registry.md) Step 2 load script to remount the HIVE; otherwise, subsequent registry access will fail
- **Fix phase**: No need to reload. The fix is the final operation; HIVE unloading does not affect subsequent workflow

**Fixed diagnostic phase workflow**:

1. Call `Get-WindowsPackage` or `Get-WindowsDriver` (or any other DISM cmdlet)
2. After the cmdlet returns, immediately execute the [registry.md](references/offline/registry.md) Step 2 load script (remount using the fixed path from Rule 1)
3. Only then can subsequent diagnostic steps that access the registry continue

Do not skip the reload during the diagnostic phase on the grounds that "the registry won't be accessed later"; query result objects cached in the global cross-step context do not depend on the HIVE and do not need to be re-collected, but the HIVE itself MUST still be remounted.

### Cross-Step Deduplication

The same DISM query result should be called only once per session. Steps that need the same data later **MUST read from the cross-step cache** and must not repeatedly call DISM.

### Standard Disk Cache Pattern

Large objects produced during diagnostics (such as `Get-WindowsDriver` / `Get-WindowsPackage` return results, `bcdedit /enum all` output, etc.) cannot survive across step calls through PowerShell in-memory variables and MUST be serialized to cache files for reuse by subsequent steps. The cache directory expression is fixed to `Join-Path $env:SystemRoot 'Temp\diag-cache'` in the template below (MUST NOT hardcode drive letters); steps that need to reuse large objects MUST follow this template:

```powershell
$cacheDir = Join-Path $env:SystemRoot 'Temp\diag-cache'
New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
$cacheFile = Join-Path $cacheDir '<CacheKey>.json'
if (Test-Path $cacheFile) {
    $result = Get-Content $cacheFile -Raw | ConvertFrom-Json
} else {
    $result = <DISM cmdlet call>
    $result | ConvertTo-Json -Depth 4 | Set-Content $cacheFile -Encoding UTF8
}
```

Cache key naming conventions:

| Cache Key | Corresponding cmdlet | Used by |
|-----------|---------------------|----------|
| `WindowsDriver` | `Get-WindowsDriver -Path "<BootLetter>:\"` | driver.md / network.md |
| `WindowsPackage` | `Get-WindowsPackage -Path "<BootLetter>:\"` | update.md |

At the end of diagnostics, you MUST execute the following script to delete the entire disk cache directory:

```powershell
Remove-Item (Join-Path $env:SystemRoot 'Temp\diag-cache') -Recurse -Force -ErrorAction SilentlyContinue
```

## Operation Capabilities

### Driver Query

Query installed third-party drivers in the offline image:

```powershell
$bootLetter = '<BootLetter>'
Get-WindowsDriver -Path "${bootLetter}:\" | Format-List Driver, OriginalFileName, ClassName, ProviderName, Date, Version
```

Filter by driver class (e.g., network adapters):

```powershell
Get-WindowsDriver -Path "${bootLetter}:\" | Where-Object { $_.ClassName -eq 'Net' } | Format-Table Driver, ProviderName, Date, Version -AutoSize
```

### Driver Add

Add drivers to the offline image (recursively scan all .inf files in the directory):

```powershell
$bootLetter = '<BootLetter>'
$driverPath = '<DriverDirectoryPath>'
Add-WindowsDriver -Path "${bootLetter}:\" -Driver $driverPath -Recurse -ForceUnsigned
```

### Package Query

Get the list of installed update packages:

```powershell
$bootLetter = '<BootLetter>'
Get-WindowsPackage -Path "${bootLetter}:\" | Format-List PackageName, PackageState, InstallTime
```

Filter packages in Pending state:

```powershell
Get-WindowsPackage -Path "${bootLetter}:\" | Where-Object { $_.PackageState -match 'Pending' } | Format-List PackageName, PackageState
```

### Package Uninstall

Uninstall a specified update package:

```powershell
$bootLetter = '<BootLetter>'
Remove-WindowsPackage -Path "${bootLetter}:\" -PackageName '<FullPackageName>'
```

### Feature Query

Query Windows feature status in the offline image:

```powershell
$bootLetter = '<BootLetter>'
Get-WindowsOptionalFeature -Path "${bootLetter}:\" | Format-List FeatureName, State
```

## Cross-References

| Type | Trigger Condition | Target |
|------|-------------------|--------|
| Side-effect recovery | Registry access needed after DISM execution during diagnostic phase | -> [registry.md](references/offline/registry.md) Step 2 |
