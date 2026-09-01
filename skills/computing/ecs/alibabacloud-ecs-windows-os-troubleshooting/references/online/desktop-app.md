# Desktop Application Diagnostics

## Function Description

Diagnoses Windows .NET Framework status, MSI install/uninstall, and COM/DCOM component registration. Covers 3 known issues.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Application startup error "Could not load file or assembly" | Step 1 (.NET Framework status) |
| Software installation interrupted or uninstall residuals | Step 2 (MSI install/uninstall status) |
| Application error COM component not registered or insufficient permissions | Step 3 (COM/DCOM component registration) |

## Diagnostic Steps

### Step 1: Check .NET Framework Status

**Data Collection**:

> Collection target: Obtain installed .NET Framework versions and installation status

**Analysis Approach**:

- PowerShell script: [desktop-app.ps1](references/online/scripts/desktop-app.ps1) Section Step 1

1. Check .NET Framework 4.x installation status:
   - Normal: Installed and version meets application requirements
   - Abnormal: Not installed or version too low -> **Root cause**: .NET Framework not installed or version does not meet application requirements, **Severity**: Critical
2. Check .NET Framework 3.5:
   - Some legacy applications require 3.5, if not installed and application errors -> **Root cause**: .NET Framework 3.5 not installed, **Severity**: Warning

### Step 2: Check MSI Install/Uninstall Status

**Data Collection**:

> Collection target: Check Windows Installer service status and recent installation failure events

**Analysis Approach**:

- PowerShell script: [desktop-app.ps1](references/online/scripts/desktop-app.ps1) Section Step 2

1. Check MSI service status:
   - Normal: msiserver service startup type is Manual (start on demand)
   - Abnormal: Service disabled -> **Root cause**: Windows Installer service disabled, cannot install/uninstall programs, **Severity**: Critical
2. Check MSI failure events:
   - Focus on specific error codes and product names in error events
3. Check incomplete file replacement operations:
   - If large number of PendingFileRenameOperations exist -> **Root cause**: Installation residual operations incomplete, may require restart, **Severity**: Warning

### Step 3: Check COM/DCOM Component Registration

**Data Collection**:

> Collection target: Check COM/DCOM configuration and common issues

**Analysis Approach**:

- PowerShell script: [desktop-app.ps1](references/online/scripts/desktop-app.ps1) Section Step 3

1. Check RPC service status:
   - Normal: RpcSs service running
   - Abnormal: RpcSs not running -> **Root cause**: RPC service not started, COM/DCOM component calls will fail, **Severity**: Critical
2. Check DCOM permission events:
   - EventID 10016 is a common DCOM permission warning, affects calls to specific COM components
   - Frequent occurrence -> **Root cause**: DCOM permission misconfiguration, related application functionality may be affected, **Severity**: Warning
3. Check whether DCOM is enabled:
   - Normal: EnableDCOM is Y
   - Abnormal: EnableDCOM is N -> **Root cause**: DCOM disabled, remote COM component calls will fail, **Severity**: Critical
4. Check DCOM authentication level:
   - Normal: LegacyAuthenticationLevel does not exist (using system default), or value is 2 (Connect) or above
   - Abnormal: LegacyAuthenticationLevel is 1 (None) -> **Root cause**: DCOM authentication level too low, COM component calls do not verify identity, may cause application startup failure or security policy conflict, **Severity**: Warning

> If antivirus software is suspected of interfering with application operation, see -> [security-malware.md](references/online/security-malware.md)

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | Antivirus software suspected of interfering with application operation | -> [security-malware.md](references/online/security-malware.md) |
| Chain successor | No root cause confirmed in this file | -> [desktop-printing.md](references/online/desktop-printing.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [desktop-app.md](references/online/fixes/desktop-app.md).
