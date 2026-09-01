# BCD Boot Configuration Diagnostics

## Function Description

Verifies BCD (Boot Configuration Data) file integrity, Boot Manager file existence and signature validity, and OS Loader boot entry configuration correctness.

Diagnostic capabilities are divided into two major categories:

1. **BCD File Existence and Integrity**: Verifies whether the BCD file exists and can be properly parsed by `bcdedit`. This is the prerequisite for all subsequent BCD configuration item checks.
2. **BCD Detail Check**: Under the premise that BCD is parseable, verifies the specific configuration of the Boot Manager file itself, Boot Manager BCD entries, and OS Loader entries item by item.

On top of the BCD checks, this file also collects **boot log evidence** (`ntbtlog.txt`, the per-driver load record written when boot logging is enabled) to localize driver-level boot failures -- see Step 6.

**Input**: System partition drive letter, boot partition drive letter, boot mode (UEFI/BIOS)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

Step 1-4 are common BCD checks, **MUST all be executed in order**; if Step 1 finds the BCD file missing or unparseable, subsequent Step 2-4 can still check the Boot Manager file itself, but checks involving BCD content parsing can be skipped.

Step 5 is only executed when `<BootMode>` = `BIOS`; in UEFI mode, the system loads `bootmgfw.efi` directly from ESP and does not depend on MBR boot code; this step is skipped.

Step 6 (boot log) is read-only and **always executed**, regardless of BCD validity -- it is independent evidence about where the boot actually stopped.

## Diagnostic Steps

Diagnostic steps are divided into four categories: first execute "BCD File Existence and Integrity" check (Step 1), then enter "BCD Detail Check" (Step 2-4) after passing; if `<BootMode>` = `BIOS`, enter "BIOS Boot Code Check" (Step 5); finally always execute "Boot Log Evidence Collection" (Step 6).

### BCD File Existence and Integrity

As the prerequisite for all subsequent BCD configuration item checks, first confirm the BCD file itself is usable.

#### Step 1: BCD File Existence and Validity Check

**Data Collection**:

> Collection target: Check whether the BCD file exists and is parseable

BCD file path depends on boot mode:
- UEFI: `<SystemLetter>:\EFI\Microsoft\Boot\BCD`
- BIOS: `<SystemLetter>:\Boot\BCD`

```powershell
$bcdPath = '<BcdPath>'

# Check BCD file existence
$bcdFile = Get-Item $bcdPath -Force -ErrorAction SilentlyContinue
[PSCustomObject]@{
    BcdPath = $bcdPath
    Exists  = ($null -ne $bcdFile)
    Size    = if ($bcdFile) { $bcdFile.Length } else { 0 }
}

# Attempt to parse BCD (validate integrity)
if ($bcdFile) {
    try {
        bcdedit /store $bcdPath /enum ALL 2>&1
    } catch {
        "BCD parse error: $_"
    }
}
```

**Analysis Approach**:

1. BCD file does not exist:
   - -> **Root cause**: BCD file missing, **severity**: Critical
   - Record expected path for fix
2. BCD file exists but bcdedit cannot parse:
   - -> **Root cause**: BCD file corrupted, **severity**: Critical
3. Normal: BCD exists and is parseable -> Continue to subsequent steps

### BCD Detail Check

Under the premise that BCD is parseable, verify the Boot Manager file itself, Boot Manager BCD entries (including default pointer), and OS Loader entry device/osdevice configuration item by item.

#### Step 2: Boot Manager File Check

**Data Collection**:

> Collection target: Verify bootmgr/bootmgfw.efi existence and signature validity

```powershell
$bootMode = '<BootMode>'

if ($bootMode -eq 'UEFI') {
    $bootmgrPath = "<SystemLetter>:\EFI\Microsoft\Boot\bootmgfw.efi"
} else {
    $bootmgrPath = "<SystemLetter>:\bootmgr"
}

# File existence
$mgr = Get-Item $bootmgrPath -Force -ErrorAction SilentlyContinue
[PSCustomObject]@{
    Path   = $bootmgrPath
    Exists = ($null -ne $mgr)
    Size   = if ($mgr) { $mgr.Length } else { 0 }
}

# Verify digital signature in UEFI mode
if ($bootMode -eq 'UEFI' -and $mgr) {
    $sig = Get-AuthenticodeSignature $bootmgrPath
    [PSCustomObject]@{
        Status     = $sig.Status
        SignerCert = $sig.SignerCertificate.Subject
    }
}
```

**Analysis Approach**:

1. Boot Manager file does not exist:
   - -> **Root cause**: Boot Manager file missing (bootmgr/bootmgfw.efi), **severity**: Critical
2. Signature verification failed in UEFI mode (Status != Valid):
   - -> **Root cause**: Boot Manager file corrupted (invalid signature), **severity**: Critical
   - In BIOS mode, bootmgr is not signed; no verification needed
3. Normal: File exists and signature is valid -> Continue to Step 3

#### Step 3: Boot Manager BCD Configuration Check

**Data Collection**:

> Collection target: Check the Device configuration in the {bootmgr} entry

```powershell
$bcdPath = '<BcdPath>'

# Get {bootmgr} entry
bcdedit /store $bcdPath /enum "{bootmgr}" 2>&1
```

**Analysis Approach**:

1. Parse {bootmgr} entry:
   - device field is empty or value is "unknown" -> **Root cause**: Boot Manager device configuration error, **severity**: Critical
   - Normal: device points to a valid partition
2. Record the default value (i.e., the Identifier of the default OS Loader) for use in Step 4

#### Step 4: OS Loader Entry Check

**Data Collection**:

> Collection target: Check the Device and OSDevice configuration of OS Loader boot entries

```powershell
$bcdPath = '<BcdPath>'

# Enumerate all OS Loader entries
$output = bcdedit /store $bcdPath /enum OSLOADER 2>&1
$output
```

**Analysis Approach**:

> **Determination Principle**: Whether the system can boot depends on whether the OS Loader entry pointed to by `{default}` is normal. Other abnormal entries in displayorder only affect the boot menu display and do not affect the default boot path.

1. Exclude WinPE entries: If an entry has the `winpe Yes` flag, ignore it
2. If after excluding WinPE there are no OS Loader entries:
   - -> **Root cause**: OS Loader entry missing (no bootable operating system), **severity**: Critical
3. Locate the default Loader: Identifier matches the default value of {bootmgr}. If no match is found in the OS Loader list -> **Root cause**: The OS Loader entry pointed to by default does not exist, **severity**: Critical
4. Check the device and osdevice fields of the **default Loader** (this one only):
   - If either is empty or contains "unknown" -> **Root cause**: Default OS Loader device configuration corrupted, **severity**: Critical
   - Normal: Both device and osdevice point to valid partitions, **determine system boot path is normal**
5. Check **other non-default OS Loader entries** (menu hygiene check only):
   - If entries exist with empty or "unknown" device or osdevice -> **severity**: Warning (boot menu has residual corrupted entries, does not affect default boot, but will fail if user manually selects that entry)
   - List the Identifier and Description of such entries as evidence; recommend cleanup but **do not block boot determination**

### BIOS Boot Code Check

#### Step 5: MBR / VBR Boot Code Check (BIOS Mode Only)

**Prerequisite**: `<BootMode>` = `BIOS`. In UEFI mode, the firmware loads `bootmgfw.efi` directly from ESP and is unrelated to MBR / VBR boot code; this step is skipped.

**Boot Chain Principle**:

Second-stage boot chain in BIOS mode:

```
Firmware -> MBR boot code (first 440 bytes of sector 0) -> System partition VBR (sector 0 of that partition) -> \bootmgr or \NTLDR
```

- **MBR boot code responsibility**: Scan MBR partition table -> find the single valid active partition (0x80) -> read its sector 0 (VBR) to 0x7C00 -> JMP to execute. **It does not itself decide whether to load `\bootmgr` or `\NTLDR`**.
- **VBR responsibility**: Based on volume type and style, load `\bootmgr` (NT60 style VBR) or `\NTLDR` (NT52 style VBR). **Whether `\bootmgr` is loaded is directly determined by the VBR**, so VBR is the most direct evidence of whether the boot chain can reach BCD / bootmgr.
- **Implicit assumption**: In practice, MBR and VBR styles appear in pairs (NT52+NT52 or NT60+NT60), because `bootsect /nt5x` refreshes the VBR, and with `/mbr` also refreshes the MBR. However, the two may be inconsistent due to manual partial fixes or third-party writes, **must be independently collected and determined**.

This step simultaneously determines **MBR boot code style** and **system partition VBR boot code style**. If either is non-NT60, corrupted, or non-Windows style, even if BCD and bootmgr files are both normal, the system will still stop at "Missing operating system" / "BOOTMGR is missing" / "NTLDR is missing".

**Collection Principle Explanation**:

(1) **MBR**: Microsoft NT52 (Win2k/XP/Server 2003) and NT60 (Vista/Win7/8/10/11) MBR boot code have a plaintext-readable code+string layout (can be visually identified in `Format-Hex` output):

| ASCII Feature | NT52 (Win2k/XP) | NT60 (Vista/7/8/10/11) | Description |
|-----------|-----------------|------------------------|------|
| `TCPA` | Not present | **Present** (near offset 0x0F0-0x0F4) | In NT60, `cmp ebx, 'TCPA'` detects TCG/TPM BIOS interface, leaving 4-byte literal `54 43 50 41`; NT52 predates TCG spec and does not contain it. **Key plaintext for distinguishing NT52/NT60** |
| `Invalid partition table` | Present | Present | Windows-style MBR error message; distinguishes Windows-style vs non-Windows boot loader |
| `Error loading operating system` | Present | Present | Same as above |
| `Missing operating system` | Present | Present | Same as above |

MBR differentiation: **`TCPA` present -> NT60**; Windows error messages present but `TCPA` not present -> NT52; Windows error messages also not present -> Non-Windows MBR; 0x55AA signature missing or boot code all 0 -> Damaged.

(2) **VBR**: Sector 0 of the system partition (`<SystemLetter>`). NTFS / FAT32 VBR also has a code+string layout; key ASCII literals directly reflect VBR style:

| ASCII Feature | NT52 Style VBR | NT60 Style VBR | Description |
|-----------|--------------|--------------|------|
| `BOOTMGR` | Not present | **Present** | NT60 VBR will load `\BOOTMGR` file and display errors such as `BOOTMGR is missing` / `BOOTMGR is compressed`, leaving 7-byte ASCII `42 4F 4F 54 4D 47 52` |
| `NTLDR` | **Present** | Not present | NT52 VBR will load `\NTLDR` file and display errors such as `NTLDR is missing`, leaving 5-byte ASCII `4E 54 4C 44 52` |
| OEM ID (offset 0x03-0x0A)| `NTFS    ` or `MSWIN4.1` | Same | Distinguishes NTFS / FAT32 volume filesystem type, does not distinguish NT52/NT60 |
| Last two bytes 0x55AA | Must be present | Must be present | VBR boot sector signature |

VBR differentiation: **`BOOTMGR` present -> NT60**; `BOOTMGR` not present but `NTLDR` present -> NT52; neither present but signature valid -> Non-Windows VBR; signature missing -> Damaged.

(3) **System partition localization**: In standard BIOS Windows layout, the system partition (`<SystemLetter>`, containing bootmgr / BCD) is set as the active partition in MBR (first byte 0x80), and the two are consistent. This step obtains the byte offset of the partition on the physical disk (`.Offset`) via `Get-Partition -DriveLetter $systemLetter`, and directly reading its sector 0 gives the system partition VBR. If no entry in MBR has first byte 0x80, or the active partition points to another partition, this is a partition table anomaly, which is handled by [disk-partition.md](references/offline/disk-partition.md) check; this step does not duplicate the determination.

**Data Collection**:

> Collection target: Read the MBR (sector 0) of the physical disk where the system partition resides, and the system partition VBR (sector 0 of the system partition), two 512-byte blocks each, and print the full hex dump with `Format-Hex` for manual cross-check; simultaneously output the raw attribute properties of MBR / VBR respectively. **Category determination is derived by the analysis approach based on these raw attributes; the collection script does not output conclusion text.**

```powershell
$systemLetter = '<SystemLetter>'

# Locate the physical disk and the system partition byte offset
$partition = Get-Partition -DriveLetter $systemLetter -ErrorAction Stop
$diskNumber = $partition.DiskNumber
$diskPath = "\\.\PhysicalDrive$diskNumber"
$systemPartitionOffset = [int64]$partition.Offset
$systemStartLBA = [uint64]([math]::Floor($systemPartitionOffset / 512))

# Open disk and read MBR (sector 0) + system partition VBR (sector 0 of the partition)
$mbr = New-Object byte[] 512
$vbr = New-Object byte[] 512

$handle = [System.IO.File]::Open(
    $diskPath,
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Read,
    [System.IO.FileShare]::ReadWrite
)
try {
    $handle.Seek(0, [System.IO.SeekOrigin]::Begin) | Out-Null
    $handle.Read($mbr, 0, 512) | Out-Null

    $handle.Seek($systemPartitionOffset, [System.IO.SeekOrigin]::Begin) | Out-Null
    $handle.Read($vbr, 0, 512) | Out-Null
} finally {
    $handle.Close()
}

# 1. Full hex dumps (for human cross-check)
Write-Host '--- MBR HEX DUMP (sector 0, 512 bytes) ---'
$mbr | Format-Hex
Write-Host '--- VBR HEX DUMP (system partition, 512 bytes) ---'
$vbr | Format-Hex

# 2. MBR raw attributes
$mbrSigOK = ($mbr[510] -eq 0x55) -and ($mbr[511] -eq 0xAA)
$mbrBootCode = $mbr[0..439]
$mbrNonZero = 0
foreach ($b in $mbrBootCode) { if ($b -ne 0) { $mbrNonZero++ } }

$sbM = New-Object System.Text.StringBuilder
foreach ($b in $mbrBootCode) {
    if ($b -ge 0x20 -and $b -le 0x7E) { [void]$sbM.Append([char]$b) } else { [void]$sbM.Append('.') }
}
$mbrAscii = $sbM.ToString()

# 3. VBR raw attributes
$vbrSigOK = ($vbr[510] -eq 0x55) -and ($vbr[511] -eq 0xAA)

$sbO = New-Object System.Text.StringBuilder
foreach ($b in $vbr[3..10]) {
    if ($b -ge 0x20 -and $b -le 0x7E) { [void]$sbO.Append([char]$b) } else { [void]$sbO.Append('.') }
}
$vbrOemId = $sbO.ToString()

$sbV = New-Object System.Text.StringBuilder
foreach ($b in $vbr) {
    if ($b -ge 0x20 -and $b -le 0x7E) { [void]$sbV.Append([char]$b) } else { [void]$sbV.Append('.') }
}
$vbrAscii = $sbV.ToString()
$vbrHasBootmgr = $vbrAscii.Contains('BOOTMGR')
$vbrHasNtldr   = $vbrAscii.Contains('NTLDR')

# 4. Output raw attributes (no conclusion text)
[PSCustomObject]@{
    DiskNumber           = $diskNumber
    SystemStartLBA       = $systemStartLBA
    # MBR
    MbrSignatureOK       = $mbrSigOK
    MbrNonZeroBytes      = $mbrNonZero
    MbrHasTCPA           = $mbrAscii.Contains('TCPA')
    MbrHasInvalidPartTbl = $mbrAscii.Contains('Invalid partition table')
    MbrHasMissingOS      = $mbrAscii.Contains('Missing operating system')
    # VBR
    VbrSignatureOK       = $vbrSigOK
    VbrOemId             = $vbrOemId
    VbrHasBOOTMGR        = $vbrHasBootmgr
    VbrHasNTLDR          = $vbrHasNtldr
} | Format-List
```

**Analysis Approach**:

Derived in two steps: first independently determine MBR category and VBR category, then synthesize to obtain the boot chain conclusion. All determinations MUST be visually cross-checked against the hex dump printed by `Format-Hex` in the ASCII column (confirming that `TCPA` / `Invalid partition table` / `Missing operating system` / `BOOTMGR` / `NTLDR` strings are actually present).

(1) **MBR Category Derivation**:

| Category | Raw Attribute Combination | Severity |
|------|------------|---------|
| NT60 | `MbrSignatureOK=True` and `MbrHasTCPA=True` and (`MbrHasInvalidPartTbl=True` or `MbrHasMissingOS=True`) | Normal |
| NT52 | `MbrSignatureOK=True` and `MbrHasTCPA=False` and (`MbrHasInvalidPartTbl=True` or `MbrHasMissingOS=True`) | Critical |
| Damaged | `MbrSignatureOK=False` or `MbrNonZeroBytes=0` | Critical |
| NonWindows | `MbrSignatureOK=True` and `MbrHasInvalidPartTbl=False` and `MbrHasMissingOS=False` | Critical |

(2) **VBR Category Derivation**:

| Category | Raw Attribute Combination | Severity |
|------|------------|---------|
| NT60 | `VbrSignatureOK=True` and `VbrHasBOOTMGR=True` | Normal |
| NT52 | `VbrSignatureOK=True` and `VbrHasBOOTMGR=False` and `VbrHasNTLDR=True` | Critical |
| Damaged | `VbrSignatureOK=False` | Critical |
| NonWindows | `VbrSignatureOK=True` and `VbrHasBOOTMGR=False` and `VbrHasNTLDR=False` | Critical |

(3) **Comprehensive Boot Chain Conclusion**:

- Only when **MBR=NT60 and VBR=NT60** is the BIOS boot chain fully normal for Vista+ Windows, **severity**: Normal.
- When either is `NT52` / `Damaged` / `NonWindows`, **severity**: Critical, **root cause** is consolidated per the following priority:
  - VBR anomaly takes priority (VBR directly determines whether `\bootmgr` is loaded): `VBR=NT52` -> "VBR is NT52 style, loads `\NTLDR` instead of `\bootmgr`"; `VBR=Damaged` -> "System partition VBR corrupted (signature missing), boot chain interrupted"; `VBR=NonWindows` -> "VBR is non-Windows style, will not hand control to `\bootmgr`".
  - MBR anomaly supplement: `MBR=NT52` -> "MBR is NT52 style (lacks TCG/TPM detection), typically accompanied by NT52 VBR in production"; `MBR=Damaged` -> "MBR boot code corrupted, BIOS cannot find executable boot code"; `MBR=NonWindows` -> "MBR overwritten by third-party boot loader (GRUB / SYSLINUX, etc.)".
  - Fix method (applies only when MBR / VBR styles are inconsistent or non-NT60): `bootsect /nt60 ... /mbr` simultaneously rewrites MBR and VBR to NT60 style. `NonWindows` scenario MUST first be manually confirmed whether it is a multi-boot configuration that needs to be preserved.

Evidence MUST include: the full 512-byte `Format-Hex` hex dump of MBR and VBR respectively, the above 11 raw attributes (`DiskNumber` / `SystemStartLBA` / `MbrSignatureOK` / `MbrNonZeroBytes` / `MbrHasTCPA` / `MbrHasInvalidPartTbl` / `MbrHasMissingOS` / `VbrSignatureOK` / `VbrOemId` / `VbrHasBOOTMGR` / `VbrHasNTLDR`), and the MBR category, VBR category, and comprehensive boot chain conclusion derived by the LLM based on the above table.

### Boot Log Evidence Collection

#### Step 6: Boot Log Read and Analysis (ntbtlog.txt)

When boot logging is enabled (`bootlog Yes` in the OS Loader entry), Windows records every driver load attempt of the last boot into `\Windows\ntbtlog.txt` on the boot partition, one line per driver: `Loaded driver <path>` or `Did not load driver <path>`. Read from the offline disk, it is direct evidence of which driver the boot stopped at -- no running instance required.

**Data Collection**:

> Collection target: Read `<BootLetter>:\Windows\ntbtlog.txt` if present; extract all failed-driver entries and the last successfully loaded driver

```powershell
$bootLetter = '<BootLetter>'
$ntbtlog = "${bootLetter}:\Windows\ntbtlog.txt"
$f = Get-Item $ntbtlog -Force -ErrorAction SilentlyContinue
if (-not $f) {
    "ntbtlog.txt NOT FOUND: boot logging was never enabled on this installation"
} else {
    [PSCustomObject]@{ Size = $f.Length; LastWrite = $f.LastWriteTime } | Format-List
    $lines = Get-Content $ntbtlog -ErrorAction SilentlyContinue
    # Line format tolerates an optional colon after the verb
    $loaded = @($lines | Where-Object { $_ -match '^Loaded driver\s*:?\s*(.+)$' } |
        ForEach-Object { ($_ -replace '^Loaded driver\s*:?\s*', '').Trim() })
    $failed = @($lines | Where-Object { $_ -match '^Did not load driver\s*:?\s*(.+)$' } |
        ForEach-Object { ($_ -replace '^Did not load driver\s*:?\s*', '').Trim() })
    "Total loaded entries   : $($loaded.Count)"
    "Last loaded (stop point): $(if ($loaded.Count) { $loaded[-1] } else { 'none' })"
    "Did-not-load entries   : $($failed.Count)"
    $failed | ForEach-Object { "  FAILED: $_" }
}
```

**Analysis Approach**:

1. File does not exist -> boot logging was never enabled; this step yields no evidence. Suggest to the user: enable it offline with `bcdedit /store '<BcdPath>' /set {default} bootlog Yes`, then perform exactly one boot of the target Windows (either the standard detach/reattach flow or the in-place boot verification fast path from the workflow guide), then remount and re-run this step; after diagnosis completes, restore `bootlog No`. This modifies the target disk's BCD, so present it as a plan with risk notes and wait for explicit user confirmation before executing (SKILL.md Principle 6)
2. File exists but `LastWrite` is clearly earlier than the reported fault time -> stale evidence: it only reflects an older boot attempt, not the failing one. Mark it as low-weight evidence and offer the enable-bootlog suggestion from item 1 to capture the failing boot
3. `Did not load driver` entries are the suspect list. To distinguish "driver failed to initialize" from "driver file missing", correlate each suspect against the loaded SYSTEM hive when available: check `<CcsPath>\Services\<driver>` Start value in the registry tier and the driver file's existence under `<BootLetter>:\Windows\System32\drivers`; follow-up repair routes to the driver diagnostics file
4. The last `Loaded driver` line marks where the boot stopped; a suspect driver appearing right after it is the prime candidate for the boot-blocking fault
5. A `Did not load driver` entry alone is not automatically a root cause -- some optional drivers legitimately fail on every boot. Report it as a **Root cause** (driver load failure at boot, **severity**: Critical) only when it correlates with the stop point or with a boot-critical service (storage/bus/display class)

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Prerequisite dependency | Requires system partition and boot mode information | -- |
| Chain successor | BCD normal, continue driver diagnostics | -> [driver.md](references/offline/driver.md) |
| Conditional jump | BCD points to non-existent partition | -> [disk-partition.md](references/offline/disk-partition.md) confirm partition status (if already executed, terminate and report error) |
| Conditional jump | Boot manager normal but BSOD after OS loading | -> [driver.md](references/offline/driver.md) |
| Chain successor | Boot log shows boot-blocking failed driver | -> [driver.md](references/offline/driver.md) |
| Conditional jump | ntbtlog.txt missing or stale | -> Suggest enabling boot logging and performing one boot verification to capture the failing boot (see Step 6), then re-analyze |


## Fix Recommendations

The fix plans for root causes confirmed in this file are documented in [bcd-boot.md](references/offline/fixes/bcd-boot.md).
