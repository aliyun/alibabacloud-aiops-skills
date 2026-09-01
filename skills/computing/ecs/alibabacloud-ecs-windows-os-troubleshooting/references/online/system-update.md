# System Update Diagnostics

## Function Description

Diagnoses Windows Update dependent services, WSUS configuration, update server reachability, known problematic patches, WinHTTP proxy configuration, update cache and pending operations, update error codes and event logs, disk space and system file integrity. CBS log and component store errors are uniformly redirected to [system-cbs.md](references/online/system-cbs.md) for handling. Covers 8 known issue items.

**Input**: User problem description (required; when update error codes are included, they should be extracted as well)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Update check failed, error 0x80070422 | Step 1 (Windows Update dependent services) |
| Incorrect update source, cannot find available updates | Step 2 (WSUS configuration) |
| Update download stuck or timed out | Step 3 (Update server reachability) |
| BSOD or functional abnormality after installing a specific KB | Step 4 (Known problematic patches) |
| Error 0x800f0826 / stuck at "Installing updates" / repeated "Reverting changes" | Step 6 (Update cache and pending operations) |
| Error 0x80070005 / 0x800f0831 / 0x800f081f or other unknown error codes | Step 7 (Error code and event log analysis) |
| Error 0x800f0831 / 0x800f081f, or suspected system file/component store corruption | Step 8 -> [system-cbs.md](references/online/system-cbs.md) (CBS log and component store) |
| Insufficient disk space, Temp write failure prompt | Step 8 -> [identity-permission.md](references/online/identity-permission.md) (Temp permissions) |
| Updates repeatedly fail for unknown reasons | Step 1 -> Step 7 -> Step 6 -> Step 8 |

## Diagnostic Steps

### Step 1: Windows Update Dependent Service Check

**Data Collection**:

> Collection target: Check the status of core services that Windows Update depends on

- PowerShell script: [system-update.ps1](references/online/scripts/system-update.ps1) Section Step 1

**Analysis Approach**:

1. Check core dependent services (wuauserv/CryptSvc/TrustedInstaller/BrokerInfrastructure):
   - Normal: All are Running, no services Disabled
   - Abnormal: Any stopped or disabled -> **Root cause**: Update core dependent service abnormal (UpdateDependentServiceInvalid), **Severity**: Critical
2. Check auxiliary services (BITS/swprv/VSS/Schedule/w32time/mpssvc/Winmgmt):
   - Normal: Manual and Stopped -> These services start on demand; Stopped is a normal state
   - Abnormal: Any disabled -> **Root cause**: Update auxiliary service disabled, **Severity**: Warning

> Key service descriptions: wuauserv=Windows Update main service, BITS=Background Intelligent Transfer Service, CryptSvc=Cryptographic service, TrustedInstaller=Module installation service

### Step 2: WSUS Configuration Check

**Data Collection**:

> Collection target: Check Windows Update server configuration (registry)

- PowerShell script: [system-update.ps1](references/online/scripts/system-update.ps1) Section Step 2

**Analysis Approach**:

1. Check WSUS configuration:
   - Normal: UseWUServer=1 and WUServer/WUStatusServer point to the correct WSUS
   - Abnormal: UseWUServer=0 or WUServer/WUStatusServer mismatch -> **Root cause**: WSUS configuration error (WUServerConfigError), **Severity**: Warning
   - Registry key does not exist: WSUS not configured, system uses Microsoft Update default source

### Step 3: Update Server Reachability Check

**Data Collection**:

> Collection target: Test network connectivity to the WSUS server

- PowerShell script: [system-update.ps1](references/online/scripts/system-update.ps1) Section Step 3

**Analysis Approach**:

1. Check update server reachability:
   - Normal: TcpTestSucceeded=True -> Update server is reachable
   - Abnormal: TcpTestSucceeded=False -> **Root cause**: Update server unreachable (UpdateServerUnReachable), **Severity**: Critical

### Step 4: Known Problematic Patch Check

**Data Collection**:

> Collection target: Check whether known problematic patches are installed

- PowerShell script: [system-update.ps1](references/online/scripts/system-update.ps1) Section Step 4

**Analysis Approach**:

1. Check known problematic patches:
   - Normal: No problematic patches found
   - Abnormal: Known problematic patch found -> **Root cause**: Patch that may cause problems is installed (ProblematicHotfixInstalled), **Severity**: Warning

> These patches are known to cause issues such as RDP disconnection, service crashes, or boot failures.

### Step 5: WinHTTP Proxy Configuration Check

**Data Collection**:

> Collection target: Check whether WinHTTP system-level proxy and IE user-level proxy configurations are consistent

- PowerShell script: [system-update.ps1](references/online/scripts/system-update.ps1) Section Step 5

**Analysis Approach**:

1. Check WinHTTP proxy configuration:
   - Normal: WinHTTP proxy and IE proxy are consistent (or neither configured)
   - Abnormal: IE has a proxy configured but WinHTTP does not -> **Root cause**: WinHTTP proxy inconsistency (WinhttpConfigError), **Severity**: Warning

> Windows Update uses WinHTTP (system-level) rather than IE proxy (user-level). If a proxy is only configured in IE, Windows Update will not be able to use that proxy.

### Step 6: Update Cache and Pending Operations Check

**Data Collection**:

> Collection target: SoftwareDistribution / Catroot2 update cache directory status, pending.xml pending operations file

- PowerShell script: [system-update.ps1](references/online/scripts/system-update.ps1) Section Step 6

**Analysis Approach**:

1. Check pending operations file:
   - `C:\Windows\WinSxS\pending.xml` does not exist -> Normal, no pending operations
   - pending.xml exists and updates repeatedly fail (especially error 0x800f0826, meaning pending package installation failure) -> **Root cause**: Update pending operations stuck or pending package corrupted (UpdatePendingOperationStuck), **Severity**: Critical, reset per Fix 5
2. Check update cache directory:
   - `C:\Windows\SoftwareDistribution\DataStore` exists and DataStore.edb is accessible -> Normal
   - Directory missing, DataStore.edb corrupted, or access denied (update log write failure) -> **Root cause**: Update cache corrupted (UpdateCacheCorrupted), **Severity**: Critical, reset per Fix 5
   - `C:\Windows\System32\Catroot2` is empty or access denied -> Signature verification cache abnormal, also reset per Fix 5

### Step 7: Update Error Code and Event Log Analysis

**Data Collection**:

> Collection target: Error events from WindowsUpdateClient / Servicing sources in the System log (e.g., Event ID 20 installation failure, Event ID 1001 failure reporting; note: Event ID 19 is an installation **success** event and MUST NOT be used as error evidence); error codes provided by the user

- PowerShell script: [system-update.ps1](references/online/scripts/system-update.ps1) Section Step 7

**Analysis Approach**:

1. Extract error events: Event ID 20 (installation failure) and Event ID 1001 (failure reporting) from source `WindowsUpdateClient` in the System log, and error events from source `Servicing`; extract error codes from event descriptions (note: Event ID 19 is an installation success event and can only be used as update history circumstantial evidence, MUST NOT be determined as failure evidence)
2. **Error code mapping evaluation** (combining user-provided error codes with error codes extracted from events):

   | Error Code | Meaning | Resolution Direction |
   |--------|------|---------|
   | `0x80070005` | Access denied / insufficient permissions | -> [identity-permission.md](references/online/identity-permission.md) (Temp and update directory permissions); investigate third-party security software blocking |
   | `0x800f0826` | Pending package installation failure | Step 6 -> Fix 5 (Reset update cache) |
   | `0x800f0831` | Update source file missing / component store corrupted | Step 8 -> [system-cbs.md](references/online/system-cbs.md) (CBS log analysis and component store repair) |
   | `0x800f081f` | Repair source file not found | -> [system-cbs.md](references/online/system-cbs.md) (Need to specify repair source) |
   | `0x80070422` | Update service disabled | Step 1 -> Fix 1 |
   | `0x80244022` / `0x80244019` | Update server unreachable / refused | Step 3 (WSUS reachability) |
   | `0xC1900101` | Driver compatibility issue (upgrade/reinstall scenario) | -> [device-driver.md](references/online/device-driver.md) |

   - Match found in table -> Jump to corresponding resolution direction, then return to this file to continue verification
   - No match -> Present error codes and event evidence to the user as-is, and comprehensively evaluate combined with other Step results
3. No WindowsUpdateClient error events and user provided no error codes -> Normal, no failure records in the update chain

### Step 8: Disk Space and System File Integrity

**Data Collection**:

> Collection target: System disk free space, SFC system file integrity

- PowerShell script: [system-update.ps1](references/online/scripts/system-update.ps1) Section Step 8

**Analysis Approach**:

1. Check system disk free space:
   - System disk free space >= 2GB -> Normal
   - Free space < 2GB -> **Root cause**: System disk space insufficient, update temporary files cannot be created (UpdateDiskSpaceNotEnough), **Severity**: Critical
2. Check system file integrity (SFC results):
   - SFC finds no integrity violations -> Normal
   - SFC reports unrepairable file corruption -> **Root cause**: System file corruption preventing patch application (SystemFileCorrupted), **Severity**: Critical, handle per [system-cbs.md](references/online/fixes/system-cbs.md) component store and system file repair solution
3. CBS log errors and component store health: Redirect to [system-cbs.md](references/online/system-cbs.md) Step 2 and Step 5 (collection, evaluation, and repair are all authoritative there)

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 3 server unreachable and involves firewall blocking | -> [networking-firewall.md](references/online/networking-firewall.md) |
| Conditional jump | WSUS configuration points to metadata service | -> [cloud-metaserver.md](references/online/cloud-metaserver.md) (Metadata WSUS check) |
| Conditional jump | Error code 0x800f0831 / 0x800f081f, or CBS log/component store errors | -> [system-cbs.md](references/online/system-cbs.md) (CBS log analysis and component store repair) |
| Conditional jump | Temp folder permission issue causing update failure (including error code 0x80070005) | -> [identity-permission.md](references/online/identity-permission.md) (Temp permission check) |
| Conditional jump | Error code 0xC1900101 (upgrade/reinstall scenario driver compatibility) | -> [device-driver.md](references/online/device-driver.md) |
| Chain successor | Root cause not confirmed in this file | -> [networking-firewall.md](references/online/networking-firewall.md) |


## Fix Recommendations

Fix solutions for root causes confirmed in this file are found in [system-update.md](references/online/fixes/system-update.md); Fix numbers referenced in the text all refer to the numbered fix operations in that file. DISM/SFC repair for SystemFileCorrupted / ComponentStoreCorrupted is found in [system-cbs.md](references/online/fixes/system-cbs.md) Fix 3.
