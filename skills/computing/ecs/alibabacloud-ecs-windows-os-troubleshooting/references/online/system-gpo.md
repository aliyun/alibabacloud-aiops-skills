# System Group Policy Diagnostics

## Overview

Diagnoses Windows Group Policy application status, AppLocker/Software Restriction Policies, drive mapping, and driver installation policies. Covers 4 known issue items.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Symptom | Recommended Steps |
|-------------|---------------|
| gpupdate errors, logon scripts not running, policy settings not taking effect | Step 1 (Group Policy application status) |
| Application blocked from running, "has been blocked by the system administrator" prompt | Step 2 (AppLocker/Software Restriction Policies) |
| Network drives do not appear at logon | Step 3 (Drive mapping) |
| Cannot install new drivers, new devices show exclamation mark in Device Manager | Step 4 (Driver installation policy) |

## Diagnostic Steps

### Step 1: Group Policy Application Status Check

**Data Collection**:

> Collection target: Retrieve Group Policy application results and check for policies that failed to apply

- PowerShell script: [system-gpo.ps1](references/online/scripts/system-gpo.ps1) Section Step 1

**Analysis Approach**:

1. Check Group Policy application status:
   - Normal: gpresult returns normally with no errors -> Group Policy applied successfully
   - Abnormal: gpresult reports errors or event log contains Error/Warning -> **Root cause**: Group Policy application failed, **Severity**: Warning

### Step 2: AppLocker/Software Restriction Policy Check

**Data Collection**:

> Collection target: Check for block events in AppLocker event logs

- PowerShell script: [system-gpo.ps1](references/online/scripts/system-gpo.ps1) Section Step 2

**Analysis Approach**:

1. Check AppLocker block events:
   - Normal: No block events in AppLocker logs
   - Abnormal: Block events exist in AppLocker logs -> **Root cause**: AppLocker is blocking application execution (AppLockerBlockEvent), **Severity**: Warning
2. Check SRP default security level:
   - Normal: SRP not configured or DefaultLevel is not Disallowed
   - Abnormal: SRP DefaultLevel=0 (Disallowed) -> **Root cause**: Software Restriction Policy is set to disallow execution, **Severity**: Warning

### Step 3: Drive Mapping Check

**Data Collection**:

> Collection target: Check drive mapping configured by Group Policy

- PowerShell script: [system-gpo.ps1](references/online/scripts/system-gpo.ps1) Section Step 3

**Analysis Approach**:

1. Check network drive mapping:
   - Normal: Network drives mapped successfully
   - Abnormal: Mapping configured but no actual network connection established -> May be due to network unreachable or credentials invalid

### Step 4: Driver Installation Policy Check

**Data Collection**:

> Collection target: Check whether device driver installation is disabled via Group Policy

- PowerShell script: [system-gpo.ps1](references/online/scripts/system-gpo.ps1) Section Step 4

**Analysis Approach**:

1. Check DeviceInstallDisabled configuration:
   - Normal: DeviceInstallDisabled does not exist or is 0 -> Driver installation is not disabled
   - Abnormal: DeviceInstallDisabled is non-zero -> **Root cause**: Driver installation has been disabled by policy (DriverInstallDisabled), **Severity**: Warning

> This policy prevents automatic installation of new hardware drivers and affects scenarios such as VirtIO driver updates.

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | Step 4 finds driver installation disabled | -> [cloud-driver.md](references/online/cloud-driver.md) (driver installation policy check) |
| Conditional jump | AppLocker blocks application execution | -> [security-malware.md](references/online/security-malware.md) (IFEO check to rule out malware) |

## Fix Recommendations

### Fix 1: Force Refresh Group Policy

**Applicable scenario**: Group Policy application failed

```powershell
gpupdate /force
```

### Fix 2: Handle AppLocker Block (AppLockerBlockEvent)

**Applicable root cause**: AppLockerBlockEvent

1. Review the blocked application path and confirm whether it is a legitimate application
2. If the application needs to be allowed, add an exemption rule in Local Security Policy:
   ```powershell
   # Open Local Security Policy editor
   secpol.msc
   # Navigate to: Application Control Policies -> AppLocker -> Executable Rules
   ```
3. If the policy is pushed by domain, contact the domain administrator to modify it

### Fix 3: Remove Driver Installation Restriction (DriverInstallDisabled)

**Applicable root cause**: DriverInstallDisabled

```powershell
# Windows 2016+
Remove-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\DeviceInstall\Parameters' -Name 'DeviceInstallDisabled' -ErrorAction SilentlyContinue
# If set by Group Policy, modify via gpedit.msc:
# Computer Configuration -> Administrative Templates -> System -> Device Installation -> Set to "Not Configured"
```
