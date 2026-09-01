# CBS Component Servicing Diagnostics (IIS/.NET/Windows Features/Update Installation Failures)

## Function Description

Based on the CBS (Component Based Servicing) component servicing system, diagnoses Windows component/feature installation failure issues: IIS and other server role installation failures, .NET Framework installation or enablement failures, DISM feature enablement errors, Windows package/update installation errors (0x800f series), component store corruption. Core methods include CBS.log / DISM.log error analysis, feature and package installation status check, and component store health check.

**Input**: User problem description (required, should extract: name of failed feature/role/component, error code, installation method -- Server Manager / DISM / Add-WindowsFeature / Windows Update)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| IIS / server role installation failure (Server Manager, Add-WindowsFeature, DISM) | Step 1 -> Step 2 -> Step 4 |
| .NET Framework installation or enablement failure (error 0x800f081f / 0x800f0906 / 0x800f0907) | Step 2 -> Step 3 -> Step 5 |
| Update or package installation error 0x800f0831 / 0x80073712 / indicates component store corruption | Step 2 -> Step 5 |
| Prompts "restart required to complete previous installation" or feature stuck at InstallPending | Step 1 -> Step 4 |
| Installation failure cause unknown | Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5 |
| Component store severely corrupted, DISM/SFC repair ineffective (including manifest missing, component conflict, package metadata database lost) | Step 2 -> Step 5 -> Fix 6 |

## Diagnostic Steps

### Step 1: CBS Service and Pending State Check

**Data Collection**:

> Collection target: TrustedInstaller (Windows Modules Installer) and other component service status; RebootPending flag and PackagesPending pending package count in CBS registry

- PowerShell script: [system-cbs.ps1](references/online/scripts/system-cbs.ps1) Section Step 1

**Analysis Approach**:

1. Check component installation service:
   - Normal: TrustedInstaller is Manual or Automatic and can start (Stopped is normal in on-demand start scenarios); msiserver/BITS/CryptSvc not disabled
   - Abnormal: TrustedInstaller disabled or start failure -> **Root cause**: CBS component installation service abnormal (CbsInstallerServiceInvalid), **Severity**: Critical, fix per Fix 1
2. Check pending state:
   - RebootPending flag does not exist and PackagesPending is empty -> Normal
   - RebootPending=1 or pending packages exist -> **Root cause**: Unfinished component installation operations exist; need to restart first to complete pending operations then retry installation (CbsRebootPending), **Severity**: Warning; still stuck after restart -> go to [system-update.md](references/online/system-update.md) Step 6 to handle pending operations

### Step 2: CBS.log Error Analysis (Core Step)

**Data Collection**:

> Collection target: Installation failure related error lines in `C:\Windows\Logs\CBS\CBS.log` (Failed / Corruption / Duplicate object / 0x800f and 0x80073712 error codes)

- PowerShell script: [system-cbs.ps1](references/online/scripts/system-cbs.ps1) Section Step 2

**Analysis Approach**:

1. Locate failure records: Extract timestamps, package/feature names, and HRESULT error codes from error lines; prioritize matching records near the user-reported installation failure time point with package names related to the feature the user installed (e.g., IIS-related packages, NetFx3, target KB)
2. Identify characteristic error patterns (common error patterns seen in practice; after a hit, handle according to the corresponding direction):
   - `Store corruption, manifest missing for package: <package name>` -> Component store corrupted and package manifest missing, Step 5 -> Fix 3; if DISM repair ineffective and cannot determine the missing package's corresponding KB -> Fix 6
   - `Failed to get store state [HRESULT = 0x80070bc9 - ERROR_FAIL_REBOOT_REQUIRED]` accompanied by pending.xml error -> Pending restart not completed, Step 1 -> restart then retry; still present after restart -> Fix 6
   - `does not have a winner but has N other components` accompanied by ERROR_INVALID_DATA -> Component version conflict (common in incremental patch application failure), faithfully record conflicting component names; conventional repair methods are usually ineffective -> Fix 6
   - `CBS.log` reports a missing dependency KB (target patch installation failed and log points to another missing KB) -> go to [system-update.md](references/online/system-update.md), manually install the missing dependency KB from the update catalog then retry
3. **Error code mapping determination** (error codes extracted from CBS.log and user-reported errors merged for comparison):

   | Error Code | Meaning | Handling Direction |
   |--------|------|---------|
   | `0x800f081f` | CBS_E_SOURCE_MISSING: Cannot find installation source for package/files (.NET 3.5 enablement, feature source missing common) | Fix 4 (specify installation source) |
   | `0x800f0906` | CBS_E_DOWNLOAD_FAILURE: Cannot download source files from update service (FoD/component repair scenarios) | Check network/WSUS, -> [system-update.md](references/online/system-update.md) (update source configuration) |
   | `0x800f0907` | No alternate installation source specified or source invalid, and policy blocks downloading payload from Windows Update | Fix 4 (adjust policy or configure alternate source) |
   | `0x800f0831` | CBS_E_STORE_CORRUPTION: Component store corrupted (often accompanied by Duplicate object registry error) | Step 5 -> Fix 3 (DISM/SFC repair) |
   | `0x80073712` | ERROR_SXS_COMPONENT_STORE_CORRUPT: Component store state inconsistent | Step 5 -> Fix 3 |
   | `0x80070002` | ERROR_FILE_NOT_FOUND: Required file missing | Verify installation source integrity -> Fix 4 |
   | `0x800736cc` | ERROR_SXS_FILE_HASH_MISMATCH: Component file does not match manifest checksum information | Step 5 -> Fix 3 |
   | `0x80070005` | Access denied | -> [identity-permission.md](references/online/identity-permission.md); investigate third-party security software interception |
   | `0x80073701` | ERROR_SXS_ASSEMBLY_MISSING: Cannot find referenced assembly (common in IIS and other role installations) | Step 5 -> Fix 3; if repair ineffective -> Fix 6 |
   | `0x80070bc9` | ERROR_FAIL_REBOOT_REQUIRED: Unfinished pending operations exist, store state not readable | Step 1 (restart to complete pending operations) |
   | `0x80d02002` | Server Manager role/feature installation failure (component corruption, update service abnormal or source missing) | Step 1 + Step 5 -> Fix 3 |
   | `0xc004000d` | Cannot read configuration registry key (component/configuration registry corrupted) | Step 5 -> Fix 3; if ineffective -> Fix 6 |

   - Hit in the table above -> jump to corresponding handling direction, return to this file to continue verification
   - Not hit (including 0x8007000D / 0x800705b9 / 0x8007370x / 0x800b0100 / 0x800f098x and other corruption error codes) -> faithfully present the error line original text and error code, combine with other Step results for comprehensive judgment
4. `Corruption` / `Duplicate object` / `manifest missing` type errors appear -> component store corruption signal, enter Step 5 to confirm and fix per Fix 3
5. No relevant error lines and no recent failure records in CBS.log -> installation request may not have reached CBS (check the output of the installation command itself and DISM.log, see Step 3)

### Step 3: DISM.log Error Analysis

**Data Collection**:

> Collection target: Error records in `C:\Windows\Logs\DISM\dism.log` for feature enablement/package installation

- PowerShell script: [system-cbs.ps1](references/online/scripts/system-cbs.ps1) Section Step 3

**Analysis Approach**:

1. Extract error segments matching the user's operation time (HRESULT, OpenPackage failure, EnableFeature failure, etc.):
   - DISM.log has clear errors -> determine based on HRESULT compared to Step 2 error code mapping table
   - DISM.log points to CBS failure (e.g., "The DISM log file can be found at..." accompanied by CBS error code) -> use CBS.log evidence from Step 2 as authoritative
2. No error records in DISM.log -> installation command may not have actually executed (command syntax error, insufficient permissions, etc.), verify user's execution method and error original text

### Step 4: Feature and Package Installation Status Check

**Data Collection**:

> Collection target: Installation status of target features (Absent / InstallPending / Staged / Enabled etc.) and pending package list

- PowerShell script: [system-cbs.ps1](references/online/scripts/system-cbs.ps1) Section Step 4

**Analysis Approach**:

1. Check target feature status:
   - Feature is in `InstallPending` / `Staged` / `PartiallyInstalled` intermediate state -> **Root cause**: Feature installation pending incomplete (FeatureInstallPending), **Severity**: Warning, restart first to complete pending operations; still in intermediate state after restart -> Step 2 to locate CBS error
   - Feature is `Absent` / `Disabled` and user reports installation failure -> installation did not persist, use Step 2/3 log evidence to locate cause
   - Feature is `Enabled` / `Installed` -> installation actually completed, confirm with user whether the symptom is a side effect (e.g., service not started, port not listening)
2. Check whether packages with `Install Pending` / `Resolving Pending` status exist in package list -> cross-verify with Step 1 pending state
3. Check CBS package metadata database integrity: `DISM /Online /Get-Packages` returns (No packages found) and `Get-Hotfix` is empty, `C:\Windows\Servicing\Packages` only has baseline entries -> **Root cause**: CBS package metadata database lost, updates/feature installation will report "not applicable to this computer" (WU_E_NOT_APPLICABLE), SFC/DISM cannot rebuild this database (CbsPackageDatabaseLost), **Severity**: Critical, handle per Fix 6

> Collection channel constraint: Full enumeration of Windows features (`Get-WindowsFeature` / `Get-WindowsOptionalFeature`) may time out; if script execution times out, MUST fall back to presenting commands for user to execute manually.

### Step 5: Component Store Health Check

**Data Collection**:

> Collection target: Component store (WinSxS) health status (DISM CheckHealth / ScanHealth)

- PowerShell script: [system-cbs.ps1](references/online/scripts/system-cbs.ps1) Section Step 5

**Analysis Approach**:

1. Check component store health:
   - CheckHealth reports no corruption -> Normal
   - Reports component store corruption (combined with Step 2 Corruption / Duplicate object / manifest missing evidence) -> **Root cause**: Component store corrupted (ComponentStoreCorrupted), **Severity**: Critical, fix per Fix 3; if DISM repair still fails, handle per Fix 6 (ISO in-place upgrade repair); if still not feasible, faithfully inform user that system disk reset or image reinstallation may need to be considered
2. CheckHealth reports error cannot execute (e.g., service unavailable) -> return to Step 1 to restore component installation service first

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Error code 0x80070005 (permission/security software interception) | -> [identity-permission.md](references/online/identity-permission.md) |
| Conditional jump | Error code 0x800f0906 or repair source needs to be obtained from update service | -> [system-update.md](references/online/system-update.md) (update source and server reachability) |
| Conditional jump | Pending operations still stuck after restart | -> [system-update.md](references/online/system-update.md) Step 6 (update cache and pending operation reset) |
| Conditional jump | Failed object is a Windows update patch (KB) itself rather than a role/feature | -> [system-update.md](references/online/system-update.md) (update chain diagnostics) |

## Fix Recommendations

Fix plans for root causes confirmed in this file are in [system-cbs.md](references/online/fixes/system-cbs.md); Fix numbers mentioned in the text all refer to the numbered fix operations in that file.
