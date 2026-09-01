# Registry HIVE Loading and Integrity Verification

## Function Description

Loads the target system's registry HIVE files offline and verifies file existence and integrity. This file is the on-demand registry tier (Tier 2) of the offline prerequisite chain: it is NOT part of the mandatory Tier 1 (environment -> disk-partition) and MUST NOT run preemptively -- execute it lazily, at most once per session, only when the scenario actually needs offline registry access (the first script referencing `<CcsPath>` / `<CsName>` / `<SysPath>` / `<SoftPath>`, or a DISM cmdlet that requires loaded HIVEs). See WORKFLOW-GUIDE "Path Planning" for the trigger rule.

**Input**: Boot partition drive letter
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix) + loaded HIVE path mapping

## Step Selection Guide

All steps in this file **must be executed in sequence**.

## Diagnostic Steps

### Step 1: HIVE File Existence and Structural Pre-Check

**Data Collection**:

> Collection target: Check whether all registry HIVE files that need to be loaded exist, and run a byte-level structural pre-check on every existing HIVE (regf signature, header checksum, dirty state, size alignment, transaction log presence)

```powershell
$bootLetter = '<BootLetter>'
# HIVE file list (shared by Step 1/Step 2; this troubleshooting file requires all steps to be executed in sequence)
$files = @(
    "${bootLetter}:\Windows\System32\config\SYSTEM",
    "${bootLetter}:\Windows\System32\config\SOFTWARE",
    "${bootLetter}:\Windows\System32\config\SAM",
    "${bootLetter}:\Windows\System32\config\SECURITY",
    "${bootLetter}:\Windows\System32\config\DRIVERS",
    "${bootLetter}:\Windows\System32\config\DEFAULT",
    "${bootLetter}:\Windows\System32\config\COMPONENTS",
    "${bootLetter}:\Users\Default\NTUSER.DAT",
    "${bootLetter}:\Windows\System32\SMI\Store\Machine\SCHEMA.DAT"
)
$files | ForEach-Object {
    $f = $_
    $info = Get-Item $f -Force -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        Path = $f
        Exists = ($null -ne $info)
        Size = if ($info) { $info.Length } else { 0 }
        LastWrite = if ($info) { $info.LastWriteTime } else { $null }
    }
} | Format-List

# Structural pre-check: read the 4096-byte HBASE_BLOCK header of every existing HIVE.
# regf format rules used here: 4-byte "regf" signature; header checksum = XOR of the
# first 127 DWORDs (bytes 0-507) stored at offset 0x1FC; two sequence numbers whose
# mismatch means unflushed writes pending LOG replay; file size = 4096-byte header
# plus whole 4096-byte bins.
$struct = foreach ($f in $files) {
    $item = Get-Item $f -Force -ErrorAction SilentlyContinue
    if (-not $item) { continue }
    $verdict = 'STRUCT_OK'
    $detail = ''
    $dirty = $false
    if ($item.Length -eq 0) {
        $verdict = 'STRUCT_CORRUPT'; $detail = 'zero-byte file'
    } else {
        $buf = New-Object byte[] ([Math]::Min(4096, [int]$item.Length))
        $fs = [System.IO.File]::Open($f, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        try { $fs.Read($buf, 0, $buf.Length) | Out-Null } finally { $fs.Close() }
        if ($buf.Length -lt 4096) {
            $verdict = 'STRUCT_CORRUPT'; $detail = 'smaller than one 4096-byte header block (truncated)'
        } else {
            $sigOK = ($buf[0] -eq 0x72) -and ($buf[1] -eq 0x65) -and ($buf[2] -eq 0x67) -and ($buf[3] -eq 0x66)
            $xor = 0
            for ($i = 0; $i -lt 127; $i++) { $xor = $xor -bxor [BitConverter]::ToInt32($buf, $i * 4) }
            $sumOK = ($xor -eq [BitConverter]::ToInt32($buf, 0x1FC))
            $seq1 = [BitConverter]::ToInt32($buf, 4)
            $seq2 = [BitConverter]::ToInt32($buf, 8)
            $dirty = ($seq1 -ne $seq2)
            $aligned = ((($item.Length - 4096) % 4096) -eq 0)
            if (-not $sigOK) { $verdict = 'STRUCT_CORRUPT'; $detail = 'regf signature missing' }
            elseif (-not $sumOK) { $verdict = 'STRUCT_CORRUPT'; $detail = 'header checksum mismatch' }
            elseif (-not $aligned) { $verdict = 'STRUCT_CORRUPT'; $detail = 'size not 4096-aligned (truncated)' }
            elseif ($dirty) { $verdict = 'DIRTY'; $detail = "sequence mismatch ($seq1 vs $seq2), unflushed writes pending LOG replay" }
        }
    }
    # Transaction logs sit next to the HIVE with .LOG1/.LOG2 suffixes (SYSTEM -> SYSTEM.LOG1)
    $log1 = Get-Item "${f}.LOG1" -Force -ErrorAction SilentlyContinue
    $log2 = Get-Item "${f}.LOG2" -Force -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        File     = Split-Path $f -Leaf
        Verdict  = $verdict
        Detail   = $detail
        Log1Size = if ($log1) { $log1.Length } else { 'MISSING' }
        Log2Size = if ($log2) { $log2.Length } else { 'MISSING' }
    }
}
$struct | Format-Table File, Verdict, Detail, Log1Size, Log2Size -AutoSize
```

**Analysis**:

1. Check file existence:
   - Normal: All files exist and Size > 0
   - Abnormal: Any of SYSTEM/SOFTWARE/SAM/SECURITY missing -> **Root cause**: Critical registry HIVE file missing, **Severity**: Critical
   - DRIVERS file only exists on Server 2012+; missing on lower versions can be ignored
   - Size > 512MB -> **Root cause**: Registry HIVE file too large, **Severity**: Warning
2. Check structural verdicts (per existing file):
   - `STRUCT_CORRUPT` (bad signature / checksum mismatch / truncated / zero-byte) -> **Root cause**: Registry HIVE structurally corrupted, **Severity**: Critical. This file will also fail `reg load`; do not retry the load for it -- record it and jump to Fix Recommendations
   - `DIRTY` with Log1Size/Log2Size MISSING or 0 -> **Root cause**: HIVE has unflushed writes but its transaction log is gone, recent changes are lost, **Severity**: Warning. Loading can continue, but treat any "configuration lost" symptom found later as consistent with this evidence
   - `DIRTY` with healthy LOG files -> informational only; the loader replays the log, no root cause
   - `STRUCT_OK` -> normal, proceed to Step 2

### Step 2: HIVE Loading

**Data Collection**:

> Collection target: Load all HIVE files into HKLM using the GUID path format

#### Mount Path Format (Key Constraint)

```
reg load "HKLM\{bf1a281b-ad7b-4476-ac95-f47682990ce7}<Absolute path to HIVE file, backslashes replaced with forward slashes>" <HIVE file path>
```

Example (boot partition drive letter is E:):
```
reg load "HKLM\{bf1a281b-ad7b-4476-ac95-f47682990ce7}E:/Windows/System32/config/SYSTEM" E:\Windows\System32\config\SYSTEM
```

The mount path format is fixed as `GUID + absolute path to HIVE file (backslashes replaced with forward slashes)`, where the GUID is the fixed value `{bf1a281b-ad7b-4476-ac95-f47682990ce7}`, and neither part may be modified. This format is also used internally by the DISM module; path inconsistency will cause DISM operations to fail (see dism.md for details).

Unload command:
```
reg unload "HKLM\{bf1a281b-ad7b-4476-ac95-f47682990ce7}E:/Windows/System32/config/SYSTEM"
```

#### Pre-check

Before executing the load, first check whether the above GUID path already exists:
- HIVE already loaded to the expected GUID path -> skip loading, directly use the loaded path
- HIVE already loaded but path does not match expectations (e.g., loaded to a different path by another tool or manual operation) -> **report error and terminate the entire diagnostic flow**, explain the path conflict reason

#### Load Script

```powershell
# Reuse $bootLetter and $files defined in Step 1 (this troubleshooting file requires Step 1->Step 2 to be executed in sequence)
$guid = '{bf1a281b-ad7b-4476-ac95-f47682990ce7}'
# Note: foreach statement cannot directly follow a pipeline; must assign first then output (see WORKFLOW-GUIDE.md PowerShell Collection Script Rules)
$loaded = foreach ($f in $files) {
    if (Test-Path $f) {
        $loadPath = $guid + ($f -replace '\\','/')
        $result = reg load "HKLM\$loadPath" $f 2>&1
        [PSCustomObject]@{ File = (Split-Path $f -Leaf); LoadPath = $loadPath; Result = ($result -join ' ').Trim() }
    }
}
$loaded | Format-List
```

**Analysis**:

1. Check load result:
   - Normal: All existing files loaded successfully
   - Abnormal: Load failure -> **Root cause**: Registry HIVE file corrupted (cannot be mounted), **Severity**: Critical
   - NTUSER.DAT load failure can continue after backing up the original file (does not block subsequent diagnostics)
2. **Cases where HIVE files may not exist** (not considered abnormal, just skip):
   - `DRIVERS`: Only exists on Windows 8 / Server 2012 and above; does not exist in Windows 7 / Server 2008 R2 images
   - `BBI`: Only exists on Windows 10 1607+
   - `COMPONENTS`: May not be generated yet after Sysprep or during OOBE phase
   - During the load phase, skip missing files with `Test-Path`; do not interrupt the diagnostic flow because of this

**[CTX] Session Memory Backfill** (not displayed to the user): After completing this step, the model MUST remember the literal form of the following placeholders (all prefixed with the loaded GUID path):

| Placeholder | Value Template |
|-------------|----------------|
| `<SysPath>` | `HKLM:\{bf1a281b-ad7b-4476-ac95-f47682990ce7}<BootLetter>:/Windows/System32/config/SYSTEM` |
| `<SoftPath>` | `HKLM:\{bf1a281b-ad7b-4476-ac95-f47682990ce7}<BootLetter>:/Windows/System32/config/SOFTWARE` |

`<BcdPath>` is NOT produced here -- it is a Tier 1 constant derived in [disk-partition.md](references/offline/disk-partition.md) Step 3 from boot mode + `<SystemLetter>`, with no HIVE loading involved.

When generating subsequent scripts, you MUST first replace the `<BootLetter>` literal from session memory into the templates above, then execute.

### Step 3: HIVE Integrity Verification

**Data Collection**:

> Collection target: Verify each HIVE's data integrity by reading key subkeys

```powershell
$guid = '{bf1a281b-ad7b-4476-ac95-f47682990ce7}'
$bootLetter = '<BootLetter>'
$configBase = "HKLM:\${guid}${bootLetter}:/Windows/System32/config"
$sysPath = "${configBase}/SYSTEM"
$softPath = "${configBase}/SOFTWARE"
$samPath = "${configBase}/SAM"
$secPath = "${configBase}/SECURITY"
$drvPath = "${configBase}/DRIVERS"
$results = @()

# SYSTEM: Select -> ControlSet -> Enum / Services -> Environment
$select = Get-ItemProperty "${sysPath}\Select" -ErrorAction SilentlyContinue
$csName = "ControlSet00$($select.Current)"
$results += [PSCustomObject]@{ Hive='SYSTEM'; Test='Select\Current'; Result=if($select.Current){"OK ($csName)"}else{'MISSING'} }
$results += [PSCustomObject]@{ Hive='SYSTEM'; Test="${csName}\Enum"; Result=if(Test-Path "${sysPath}\${csName}\Enum"){'OK'}else{'MISSING'} }
$svcPath = "${sysPath}\${csName}\Services"
if (Test-Path $svcPath) {
    $svcCount = @(Get-ChildItem $svcPath -ErrorAction SilentlyContinue).Count
    $results += [PSCustomObject]@{ Hive='SYSTEM'; Test="${csName}\Services"; Result=if($svcCount -gt 0){"OK ($svcCount entries)"}else{'EMPTY'} }
} else {
    $results += [PSCustomObject]@{ Hive='SYSTEM'; Test="${csName}\Services"; Result='MISSING' }
}
$envPath = Get-ItemProperty "${sysPath}\${csName}\Control\Session Manager\Environment" -Name Path -ErrorAction SilentlyContinue
$results += [PSCustomObject]@{ Hive='SYSTEM'; Test='Environment\Path'; Result=if($envPath.Path){'OK'}else{'MISSING'} }

# SOFTWARE: CurrentVersion + CBS store
$cv = Get-ItemProperty "${softPath}\Microsoft\Windows NT\CurrentVersion" -ErrorAction SilentlyContinue
$results += [PSCustomObject]@{ Hive='SOFTWARE'; Test='CurrentVersion'; Result=if($cv.ProductName){"OK ($($cv.ProductName))"}else{'MISSING'} }
$cbsExists = Test-Path "${softPath}\Microsoft\Windows\CurrentVersion\Component Based Servicing"
$results += [PSCustomObject]@{ Hive='SOFTWARE'; Test='CBS Store'; Result=if($cbsExists){'OK'}else{'MISSING'} }

# SAM: Domains\Account\Users (may require SYSTEM privilege)
try {
    $samUsers = Get-ChildItem "${samPath}\SAM\Domains\Account\Users" -ErrorAction Stop
    $results += [PSCustomObject]@{ Hive='SAM'; Test='Domains\Account\Users'; Result="OK ($($samUsers.Count) entries)" }
} catch [System.Security.SecurityException],[System.UnauthorizedAccessException] {
    $results += [PSCustomObject]@{ Hive='SAM'; Test='Domains\Account\Users'; Result='ACCESS_DENIED (skip)' }
} catch {
    $results += [PSCustomObject]@{ Hive='SAM'; Test='Domains\Account\Users'; Result='MISSING' }
}

# SECURITY: Policy\Accounts - check expected SIDs (may require SYSTEM privilege)
try {
    $accounts = (Get-ChildItem "${secPath}\Policy\Accounts" -ErrorAction Stop).PSChildName
    $expectedSids = @('S-1-1-0','S-1-5-19','S-1-5-20','S-1-5-6')
    $missingSids = $expectedSids | Where-Object { $_ -notin $accounts }
    $results += [PSCustomObject]@{ Hive='SECURITY'; Test='Policy\Accounts'; Result=if($missingSids.Count -eq 0){'OK'}else{"MISSING SIDs: $($missingSids -join ', ')"} }
} catch [System.Security.SecurityException],[System.UnauthorizedAccessException] {
    $results += [PSCustomObject]@{ Hive='SECURITY'; Test='Policy\Accounts'; Result='ACCESS_DENIED (skip)' }
} catch {
    $results += [PSCustomObject]@{ Hive='SECURITY'; Test='Policy\Accounts'; Result='MISSING' }
}

# DRIVERS: DriverDatabase (Server 2012+ only)
if (Test-Path $drvPath) {
    $drvDb = Get-ChildItem "${drvPath}\DriverDatabase" -ErrorAction SilentlyContinue
    $results += [PSCustomObject]@{ Hive='DRIVERS'; Test='DriverDatabase'; Result=if($drvDb.Count -gt 0){"OK ($($drvDb.Count) subkeys)"}else{'MISSING'} }
}

# SYSTEM: boot-critical Session Manager values
$smPath = "${sysPath}\${csName}\Control\Session Manager"
$bootExec = Get-ItemProperty $smPath -Name BootExecute -ErrorAction SilentlyContinue
$results += [PSCustomObject]@{ Hive='SYSTEM'; Test='Session Manager\BootExecute'; Result=if($bootExec.BootExecute){"OK ($($bootExec.BootExecute -join ' '))"}else{'MISSING'} }
$sysRoot = Get-ItemProperty $smPath -Name SystemRoot -ErrorAction SilentlyContinue
$results += [PSCustomObject]@{ Hive='SYSTEM'; Test='Session Manager\SystemRoot'; Result=if($sysRoot.SystemRoot){"OK ($($sysRoot.SystemRoot))"}else{'MISSING'} }

# DEFAULT / NTUSER.DAT / COMPONENTS / SCHEMA.DAT: light enumerability check
# (loaded in Step 2 but not otherwise validated; an unloadable-but-present file
# shows up here as EMPTY/NOT_LOADED instead of passing silently)
$lightChecks = @(
    @{ Name='DEFAULT';    Path="${configBase}/DEFAULT" },
    @{ Name='NTUSER';     Path="HKLM:\${guid}${bootLetter}:/Users/Default/NTUSER.DAT" },
    @{ Name='COMPONENTS'; Path="${configBase}/COMPONENTS" },
    @{ Name='SCHEMA';     Path="HKLM:\${guid}${bootLetter}:/Windows/System32/SMI/Store/Machine/SCHEMA.DAT" }
)
foreach ($c in $lightChecks) {
    if (Test-Path $c.Path) {
        $kids = @(Get-ChildItem $c.Path -ErrorAction SilentlyContinue).Count
        $results += [PSCustomObject]@{ Hive=$c.Name; Test='Root enumerable'; Result=if($kids -gt 0){"OK ($kids subkeys)"}else{'EMPTY'} }
    } else {
        $results += [PSCustomObject]@{ Hive=$c.Name; Test='Root enumerable'; Result='NOT_LOADED (source file missing, skipped in Step 2)' }
    }
}

$results | Format-Table Hive, Test, Result -AutoSize

# [CTX] Session memory backfill: output is for model parsing only, not directly displayed to the user
Write-Host "[CTX] CsName=$csName"
Write-Host "[CTX] CcsPath=$($sysPath)\$csName"
```

**Analysis**:

1. SYSTEM integrity:
   - Select key does not exist or Current value is empty -> SYSTEM HIVE corrupted
   - ControlSet00X\Enum does not exist -> device enumeration data lost
   - ControlSet00X\Services MISSING or EMPTY -> service and driver start configuration lost. Services holds the start config of every kernel driver and Windows service (disk/storage/bus drivers included), so an OS cannot boot without it -- treat both MISSING and EMPTY as Critical (a healthy installation always has hundreds of entries)
   - Environment\Path does not exist -> environment variable data lost
   - Session Manager\BootExecute or Session Manager\SystemRoot MISSING -> boot-critical session configuration lost (BootExecute drives boot-time autochk; SystemRoot tells the loader where Windows lives); treat as SYSTEM HIVE content corruption, Critical
2. SOFTWARE integrity:
   - CurrentVersion does not exist or no ProductName -> SOFTWARE HIVE corrupted
   - CBS Store does not exist -> Component Based Servicing data lost, may affect Windows Update diagnostics
3. SAM integrity:
   - Users subkey cannot be enumerated -> SAM HIVE corrupted
   - ACCESS_DENIED -> insufficient permissions, not considered corruption (normal when not running with SYSTEM privileges)
4. SECURITY integrity:
   - Policy\Accounts missing expected SIDs (S-1-1-0/S-1-5-19/S-1-5-20/S-1-5-6) -> SECURITY HIVE corrupted
   - ACCESS_DENIED -> insufficient permissions, not considered corruption
5. DRIVERS integrity (only exists on Server 2012+):
   - DriverDatabase has no subkeys -> DRIVERS HIVE corrupted
6. DEFAULT / NTUSER / COMPONENTS / SCHEMA light checks:
   - EMPTY -> hive loads but holds no data -> content corruption, **Severity**: Warning (these hives are not individually boot-blocking, except DEFAULT for first-logon paths)
   - NOT_LOADED -> source file was missing in Step 1; skip, already reported there
7. Any critical subkey result is MISSING -> **Root cause**: Registry HIVE data corrupted (some subkeys inaccessible), **Severity**: Critical

**[CTX] Session Memory Backfill** (not displayed to the user): Extract the literal values of the following placeholders from the `[CTX]` output lines at the end of the script:

| Placeholder | Semantics |
|-------------|-----------|
| `<CsName>` | Active ControlSet name (e.g., `ControlSet001`) |
| `<CcsPath>` | Full registry path of the active ControlSet (e.g., `HKLM:\{bf1a281b-...}E:/Windows/System32/config/SYSTEM\ControlSet001`) |

In subsequent scripts, `<CsName>` / `<CcsPath>` MUST be replaced with the above literals before execution. Note: After each DISM call, the HIVE will be unloaded; you MUST re-execute the Step 2 load script to remount the HIVE; after remounting, the mount path remains the fixed GUID path and the ControlSet number does not change, so the `<CcsPath>` / `<SoftPath>` / `<SysPath>` literals remain valid and do not need to be refreshed by re-running this step.

## Cross-References

| Type | Trigger Condition | Target |
|------|-------------------|--------|
| Depended upon | When any troubleshooting file needs to access the registry | This file must be executed first as a prerequisite |
| Chain successor | HIVE loading complete, continue boot chain diagnostics | -> [bcd-boot.md](references/offline/bcd-boot.md) |
| Chain successor | HIVE loading complete, continue driver diagnostics | -> [driver.md](references/offline/driver.md) |
| Conditional jump | SYSTEM HIVE corrupted and cannot be fixed individually | -> Inform user that backup restore needs to be considered |
| Conditional jump | RegBack backup is valid | -> Provide backup restore solution |

## Fix Recommendations

### Root Cause: Registry HIVE Missing or Corrupted (Structural or Content)

**Repair Principles** (present all of these to the user before executing):

1. Single-hive damage: replace ONLY that hive. Multiple damaged hives: they MUST be restored as one consistent set from the SAME source and the SAME timestamp -- SYSTEM/SOFTWARE/SAM/SECURITY cross-reference each other (machine GUID, driver database, account SIDs), and mixing backups taken at different times creates new failures that are harder to diagnose than the original one
2. Never overwrite a damaged file in place: rename it to `<name>.corrupt` first so the original evidence survives the fix and rollback stays possible
3. Filesystem prerequisite: if the disk-tier check found filesystem damage on the boot volume, run `chkdsk <BootLetter>: /f` and let it finish before trusting any restore operation -- hive corruption is often a symptom of disk damage, and writing restore copies onto a damaged filesystem can corrupt them again

**Restore Source Priority**:

| Priority | Source | Availability Check |
|----------|--------|--------------------|
| 1 | `config\RegBack` directory | Windows Server and pre-1803 client editions keep real backups there. MUST verify the candidate files are non-zero first: Win10 1803+ client editions write 0-byte placeholders by default, which are useless |
| 2 | User's own backups (disk snapshot, image, offline backup disk) | Ask the user whether such a backup exists; copy the matching hive file(s) out of it |
| 3 | No usable source | Tell the user honestly that offline repair has no safe restore source left; the remaining options are system reset/reinstall or restoring the whole instance from a cloud-level backup -- do NOT invent substitute fixes |

**Fix Operation**:

```powershell
$bootLetter = '<BootLetter>'
$configDir = "${bootLetter}:\Windows\System32\config"
$backupDir = "${configDir}\RegBack"

# 1. Verify the RegBack candidates are usable (non-zero) before promising this source
if (Test-Path $backupDir) {
    Get-ChildItem $backupDir | Format-Table Name, Length, LastWriteTime -AutoSize
} else {
    Write-Host "RegBack directory not found"
}

# 2. After user confirmation, per damaged hive (repeat for each <HiveName>:
#    SYSTEM / SOFTWARE / SAM / SECURITY / DEFAULT ...), keeping all files
#    from the same source and timestamp:
# $hive = '<HiveName>'
# Rename-Item "${configDir}\$hive" "${configDir}\${hive}.corrupt" -Force
# Copy-Item "${backupDir}\$hive" "${configDir}\$hive" -Force
```

**Verification (mandatory loop)**:

After replacement, the fix is NOT complete until the restored hive passes the full chain again: re-run the Step 2 load script, then re-run the Step 3 integrity verification -- the restored hive must both load and pass its content checks. A hive that loads but still fails content checks means the backup itself is stale or damaged: fall back to the next restore source.

**Rollback command** (per replaced hive): `Move-Item <configDir>\<HiveName>.corrupt <configDir>\<HiveName> -Force`

**Risk Notes**:

- Restored data is never newer than the backup timestamp; configuration changes made after it are lost
- Win10 1803+ client editions no longer populate RegBack by default (0-byte files); Windows Server editions typically retain RegBack backups
- Mixed-source restore (different timestamps per hive) risks cross-hive inconsistency -- avoid it; see Repair Principles item 1
- Session impact: none (executed in offline environment). Persistence scope: written to disk file, persists across reboot

## HIVE Unloading

After diagnostics are complete, **all loaded HIVEs must be unloaded** (including HIVEs not directly accessed during diagnostics). Incomplete unloading will prevent the target disk from being safely detached.

### Unload Script

```powershell
$guid = '{bf1a281b-ad7b-4476-ac95-f47682990ce7}'
$bootLetter = '<BootLetter>'
$files = @(
    "${bootLetter}:\Windows\System32\config\SYSTEM",
    "${bootLetter}:\Windows\System32\config\SOFTWARE",
    "${bootLetter}:\Windows\System32\config\SAM",
    "${bootLetter}:\Windows\System32\config\SECURITY",
    "${bootLetter}:\Windows\System32\config\DRIVERS",
    "${bootLetter}:\Windows\System32\config\DEFAULT",
    "${bootLetter}:\Windows\System32\config\COMPONENTS",
    "${bootLetter}:\Users\Default\NTUSER.DAT",
    "${bootLetter}:\Windows\System32\SMI\Store\Machine\SCHEMA.DAT"
)
$results = @()
foreach ($f in $files) {
    $loadPath = $guid + ($f -replace '\\','/')
    $output = reg unload "HKLM\$loadPath" 2>&1
    $results += [PSCustomObject]@{
        File   = Split-Path $f -Leaf
        Result = if ($LASTEXITCODE -eq 0) { 'OK' } else { $output }
    }
}
$results | Format-Table -AutoSize
```

### Unload Verification (Must Execute)

After unloading, you **must verify** that no residual keys with the GUID prefix remain under HKLM:

```powershell
$guid = '{bf1a281b-ad7b-4476-ac95-f47682990ce7}'
$remaining = reg query HKLM 2>&1 | Select-String $guid
if ($remaining) {
    Write-Host "WARNING: The following HIVEs are still not unloaded:" -ForegroundColor Red
    $remaining | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    # Retry unloading for each residual item
    foreach ($line in $remaining) {
        $key = ($line -replace '^\s*HKEY_LOCAL_MACHINE\\','').Trim()
        if ($key) { reg unload "HKLM\$key" 2>&1 }
    }
} else {
    Write-Host "OK: All HIVEs have been successfully unloaded" -ForegroundColor Green
}
```

**Notes**:
- Common causes of unload failure: a process or handle is still accessing the HIVE (e.g., regedit editor not closed)
- When encountering unload failures, first close all processes that may hold handles, then retry
- **You must** verify pass before performing disk detach operations

**Analysis Determination**: The unload script output results need to be distinguished into three states:
- `OK` (exit code 0) = unload successful
- Output contains `ERROR_FILE_NOT_FOUND` / `not found` / `not loaded` etc. = the HIVE was never loaded, no need to unload, considered normal
- Other non-zero exit codes = actual unload failure, need to retry or investigate handle occupation
