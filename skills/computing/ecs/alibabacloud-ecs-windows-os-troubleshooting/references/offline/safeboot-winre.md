# SafeBoot Residual and WinRE Auto-Repair Loop

## Function Description

Diagnoses two types of issues: residual SafeBoot flags in BCD that force the system to boot only in safe mode, and WinRE auto-repair loops (recoverysequence repeatedly triggered). Both belong to abnormal boot behavior in the OS Loader late phase.

**Input**: Safe mode / auto-repair loop symptoms identified by boot-triage.md
**Output**: Root cause determination (BCD SafeBoot residual / WinRE configuration abnormal) and fix plan

## Step Selection Guide

| User Symptom | Recommended Steps |
|-------------|---------------|
| Enters safe mode on every boot | Step 1 -> Step 2 |
| Cannot revert after setting safe mode | Step 1 |
| BSOD even in safe mode | Step 2 (check whether SafeBoot registry key was deleted) |
| Auto-repair loop | Step 3 -> Step 4 -> Step 5 |
| Recovery interface frozen | Step 3 -> Step 4 |
| Full troubleshooting | Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5 |

## Diagnostic Steps

### Step 1: BCD SafeBoot Flag Detection

**Data Collection**:

> Collection target: Check whether safeboot boot flag exists in BCD

```powershell
$bcdPath = '<BcdPath>'

if (-not (Test-Path $bcdPath)) {
    Write-Host "ERROR: BCD file not found at $bcdPath"
    Exit 1
}

Write-Host "=== BCD Default Entry ==="
bcdedit /store $bcdPath /enum "{default}" 2>&1 | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "=== BCD All Entries ==="
# DISM disk cache: bcdedit enum ALL output is large, persist to disk as cross-step cache for reuse by subsequent steps
$cacheDir = Join-Path $env:SystemRoot 'Temp\diag-cache'
New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
$cacheFile = Join-Path $cacheDir 'BcdEnumAll.json'
$bcdEnumAll = bcdedit /store $bcdPath /enum ALL 2>&1
@{ Lines = @($bcdEnumAll | ForEach-Object { "$_" }) } | ConvertTo-Json -Depth 4 | Set-Content $cacheFile -Encoding UTF8
$bcdEnumAll | ForEach-Object { Write-Host $_ }
```

**Analysis**:

1. Check the `{default}` entry:
   - `safeboot  Minimal` -> BCD forces safe mode (minimal), this is the root cause
   - `safeboot  Network` -> BCD forces safe mode (with networking)
   - `safebootalternateshell  Yes` -> Safe mode command prompt
   - No safeboot line -> No issue at BCD level, **continue to Step 2** to check registry level

2. If safeboot flag is found, directly provide fix plan (see Fix Recommendations section)

---

### Step 2: Registry SafeBoot Option Verification

**Data Collection**:

> Collection target: Check whether SafeBoot infrastructure in registry is intact (malicious deletion will cause BSOD in safe mode)

```powershell
$exitCode = 0
try {

    # Verify SYSTEM HIVE is loaded
    if (-not (Test-Path '<SysPath>')) {
        Write-Host "ERROR: SYSTEM HIVE not loaded at <SysPath>"
        Exit 1
    }

    $ccsPath = "<CcsPath>\Control\SafeBoot"

    Write-Host "=== SafeBoot Registry Check (<CsName>) ==="

    # Check SafeBoot\Option key
    $optionPath = "${ccsPath}\Option"
    if (Test-Path $optionPath) {
        $optionKey = Get-ItemProperty $optionPath -ErrorAction SilentlyContinue
        Write-Host "SafeBoot\Option exists: True"
        Write-Host "  OptionValue: $($optionKey.OptionValue)"
        Write-Host "  (1=Minimal, 2=Network, 3=AlternateShell)"
    } else {
        Write-Host "SafeBoot\Option exists: False (normal - no pending safe mode)"
    }

    # Check Minimal and Network subkeys
    $minimal = Test-Path "${ccsPath}\Minimal"
    $network = Test-Path "${ccsPath}\Network"
    Write-Host ""
    Write-Host "SafeBoot\Minimal subkey exists: $minimal"
    Write-Host "SafeBoot\Network subkey exists: $network"

    if (-not $minimal -or -not $network) {
        Write-Host "WARNING: SafeBoot infrastructure damaged! Safe mode will BSOD."
    }

    # Check entry count under Minimal and Network (normally dozens of service/driver groups)
    if ($minimal) {
        $minCount = (Get-ChildItem "${ccsPath}\Minimal" -ErrorAction SilentlyContinue).Count
        Write-Host "SafeBoot\Minimal entries: $minCount (normal: 50+)"
    }
    if ($network) {
        $netCount = (Get-ChildItem "${ccsPath}\Network" -ErrorAction SilentlyContinue).Count
        Write-Host "SafeBoot\Network entries: $netCount (normal: 60+)"
    }
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    $exitCode = 1
}
if ($exitCode -ne 0) { Exit $exitCode }
```

**Analysis**:

1. `SafeBoot\Option` exists and OptionValue has a value:
   - Indicates the last boot entered safe mode, the system recorded this state in the registry
   - If BCD also has safeboot at the same time -> Both set simultaneously, confirm root cause is at BCD level

2. `Minimal` or `Network` subkey does not exist or has too few entries (<30):
   - SafeBoot infrastructure is damaged (malware/accidental deletion)
   - Entering safe mode will trigger BSOD (kernel cannot determine which drivers/services to load in safe mode)
   - Fix requires exporting complete SafeBoot key from a system of the same version

3. Both normal -> Not a SafeBoot registry issue, exclude this step

---

### Step 3: WinRE BCD Entry Check

**Data Collection**:

> Collection target: Check WinRE auto-recovery configuration in BCD, determine whether a repair loop is triggered

```powershell
$bcdPath = '<BcdPath>'

if (-not (Test-Path $bcdPath)) {
    Write-Host "ERROR: BCD file not found at $bcdPath"
    Exit 1
}

Write-Host "=== BCD Default Entry ==="
bcdedit /store $bcdPath /enum "{default}" 2>&1 | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "=== BCD All Entries ==="
# Prefer reusing BcdEnumAll.json persisted by Step 1; if not found, re-collect and write back
$cacheDir = Join-Path $env:SystemRoot 'Temp\diag-cache'
New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
$cacheFile = Join-Path $cacheDir 'BcdEnumAll.json'
if (Test-Path $cacheFile) {
    $bcdEnumAll = (Get-Content $cacheFile -Raw | ConvertFrom-Json).Lines
} else {
    $bcdEnumAll = bcdedit /store $bcdPath /enum ALL 2>&1
    @{ Lines = @($bcdEnumAll | ForEach-Object { "$_" }) } | ConvertTo-Json -Depth 4 | Set-Content $cacheFile -Encoding UTF8
}
$bcdEnumAll | ForEach-Object { Write-Host $_ }
```

**Analysis**:

1. `recoveryenabled  Yes` + `recoverysequence {GUID}` -> WinRE is configured:
   - If recovery entry device is `unknown` -> WinRE partition is missing, this causes boot loop (system tries to enter WinRE but cannot find it)
   - If recovery entry is normal -> **Continue to Step 4** to check WinRE files

2. `recoveryenabled  No` -> WinRE is disabled, will not trigger auto-repair loop

3. No `recoverysequence` -> WinRE is not configured

4. `bootstatuspolicy` value:
   - `IgnoreAllFailures` -> Even if boot fails, WinRE is not triggered
   - `DisplayAllFailures` -> Any boot failure shows recovery interface, more likely to trigger repair loop

---

### Step 4: WinRE Partition and File Verification

**Data Collection**:

> Collection target: Verify whether the partition and Winre.wim file required by WinRE exist

```powershell
$exitCode = 0
try {

    Write-Host "=== Recovery Partitions ==="
    $recoveryPartitions = Get-Partition | Where-Object { $_.Type -eq 'Recovery' }
    if ($recoveryPartitions) {
        foreach ($part in $recoveryPartitions) {
            Write-Host "  Disk $($part.DiskNumber), Partition $($part.PartitionNumber), Size $([math]::Round($part.Size / 1MB)) MB"
        }
    } else {
        Write-Host "  No Recovery type partition found"
    }

    Write-Host ""
    Write-Host "=== Winre.wim Search ==="
    $winrePaths = @(
        "<BootLetter>:\Windows\System32\Recovery\Winre.wim",
        "<BootLetter>:\Recovery\WindowsRE\Winre.wim"
    )
    $found = $false
    foreach ($path in $winrePaths) {
        if (Test-Path $path) {
            $item = Get-Item $path
            Write-Host "  Found: $path"
            Write-Host "    Size: $([math]::Round($item.Length / 1MB)) MB"
            Write-Host "    Modified: $($item.LastWriteTime)"
            $found = $true
        }
    }
    if (-not $found) {
        Write-Host "  Winre.wim NOT found in standard locations"
    }

    Write-Host ""
    Write-Host "=== ReAgent.xml ==="
    $reagentXml = "<BootLetter>:\Windows\System32\Recovery\ReAgent.xml"
    if (Test-Path $reagentXml) {
        $content = Get-Content $reagentXml -Raw
        Write-Host $content
    } else {
        Write-Host "  ReAgent.xml not found"
    }
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    $exitCode = 1
}
if ($exitCode -ne 0) { Exit $exitCode }
```

**Analysis**:

1. Recovery partition existence:
   - Does not exist + BCD recoverysequence points to this partition -> Root cause confirmed: Recovery partition missing causes loop
   - Exists but no drive letter assigned -> Normal (Recovery partitions are usually hidden)

2. Winre.wim existence:
   - Does not exist + recoveryenabled=Yes -> WinRE is triggered but cannot load, causing repeated restarts
   - Exists + reasonable size (>200MB) -> WinRE file itself is intact

3. ReAgent.xml analysis:
   - `<WinreBCD id="{...}"/>` -> WinRE entry ID in BCD
   - `<WinreLocation path="..." id="..." offset="..."/>` -> WinRE physical location
   - File does not exist or content is empty -> WinRE configuration is lost

---

### Step 5: Auto-Repair Trigger State Check

**Data Collection**:

> Collection target: Check whether the system is in a continuous boot failure state (condition for triggering auto-repair)

```powershell
$exitCode = 0
try {

    $ccsBase = "<CcsPath>\Control"

    Write-Host "=== Auto-Recovery Trigger State ==="

    # CrashControl configuration
    $crashPath = "${ccsBase}\CrashControl"
    if (Test-Path $crashPath) {
        $crash = Get-ItemProperty $crashPath -ErrorAction SilentlyContinue
        Write-Host "AutoReboot: $($crash.AutoReboot)"
    }

    # Session Manager state
    $smPath = "${ccsBase}\Session Manager"
    $sm = Get-ItemProperty $smPath -ErrorAction SilentlyContinue
    Write-Host "BootExecute: $($sm.BootExecute -join ', ')"
    $pending = $sm.PendingFileRenameOperations
    Write-Host "PendingFileRenameOperations: $(if ($pending) { 'EXISTS (' + $pending.Count + ' entries)' } else { 'None' })"

    # Windows Error Reporting (consecutive crash counter)
    $werPath = "<CcsPath>\Services\WerSvc"
    if (Test-Path $werPath) {
        Write-Host "WerSvc service exists: True"
    }

    # Check if LastKnownGood is in use
    $selectPath = "<SysPath>\Select"
    $lastKnown = (Get-ItemProperty $selectPath).LastKnownGood
    $failed = (Get-ItemProperty $selectPath).Failed
    Write-Host "Select\Current: <CsName>"
    Write-Host "Select\LastKnownGood: $lastKnown"
    Write-Host "Select\Failed: $failed"
    if ("ControlSet00$lastKnown" -ne '<CsName>') {
        Write-Host "NOTE: Current != LastKnownGood, system may be using fallback ControlSet"
    }
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    $exitCode = 1
}
if ($exitCode -ne 0) { Exit $exitCode }
```

**Analysis**:

1. `AutoReboot=1` -> System auto-restarts after BSOD (default behavior), combined with WinRE can cause loop
2. `PendingFileRenameOperations` exists -> May be pending update operations causing boot failure
3. `Select\Current != LastKnownGood` -> System has attempted LastKnownGood rollback
4. `Select\Failed` has a value -> Records the failed ControlSet number

Comprehensive judgment: If recoveryenabled=Yes + continuous boot failure + WinRE partition/file abnormal -> Root cause is WinRE auto-repair loop

---


## Fix Recommendations

The fix plans corresponding to the root causes confirmed in this file are in [safeboot-winre.md](references/offline/fixes/safeboot-winre.md).


## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Prerequisite | BCD operations require disk partitions already identified | -- |
| Prerequisite | Registry checks require HIVE already loaded -- triggers the on-demand registry tier ([registry.md](references/offline/registry.md)) if not yet executed | -- |
| Conditional jump | SafeBoot key deleted and no backup | -> Inform user that recovery from installation media or reinstall is needed |
| Conditional jump | Still BSOD after excluding SafeBoot/WinRE | -> [bcd-boot.md](references/offline/bcd-boot.md) / [driver.md](references/offline/driver.md) |
| Conditional jump | PendingFileRenameOperations causing loop | -> [update.md](references/offline/update.md) |
