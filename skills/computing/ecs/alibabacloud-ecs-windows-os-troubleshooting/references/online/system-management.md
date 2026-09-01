# System Management Diagnostics

## Overview

Diagnoses Windows PowerShell execution policy, WinRM, WMI repository, Event Log service, and MMC console. Covers 5 known issue items.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Symptom | Recommended Steps |
|-------------|---------------|
| Remote management connection failed, WinRM cannot connect | Step 2 (WinRM service) |
| Script cannot run, execution policy restriction prompt | Step 1 (PowerShell execution policy) |
| WMI query failed, monitoring tool cannot retrieve system information | Step 3 (WMI repository status) |
| Event Viewer cannot open or logs corrupted | Step 4 (Event Log service) |
| Device Manager, Disk Management and other tools cannot open | Step 5 (MMC console) |

## Diagnostic Steps

### Step 1: PowerShell Execution Policy Check

**Data Collection**:

> Collection target: Retrieve current PowerShell execution policy configuration

- PowerShell script: [system-management.ps1](references/online/scripts/system-management.ps1) Section Step 1

**Analysis Approach**:

1. Check execution policy level:
   - Normal: MachinePolicy/LocalMachine is RemoteSigned or Unrestricted
   - Abnormal: Any level is Restricted or AllSigned -> May block script execution, **Severity**: Warning
   - Any level is Undefined (and effective policy is Restricted): Need to confirm the actually effective policy level

### Step 2: WinRM Service Check

**Data Collection**:

> Collection target: Check WinRM service status and configuration

- PowerShell script: [system-management.ps1](references/online/scripts/system-management.ps1) Section Step 2

**Analysis Approach**:

1. Check WinRM service status:
   - Normal: WinRM Running
   - Abnormal: WinRM stopped or disabled -> **Root cause**: Remote management may fail, **Severity**: Critical
2. Check WinRM listener:
   - Normal: Listener configured (need to further check transport protocol)
   - No listener:
     - If the user explicitly reports a WinRM failure -> **Root cause**: WinRM has no listening port configured, service cannot accept remote requests, **Severity**: Warning
     - If the user has not reported a WinRM issue -> This is expected configuration, not an anomaly
3. Check listener transport protocol (when listener exists):
   - Normal: Only HTTPS listening configured (port 5986)
   - Attention: HTTP listening configured (port 5985) -> Remote management credentials transmitted in plaintext, security risk, **Severity**: Warning

### Step 3: WMI Repository Status Check

**Data Collection**:

> Collection target: Verify WMI repository integrity and service status

- PowerShell script: [system-management.ps1](references/online/scripts/system-management.ps1) Section Step 3

**Analysis Approach**:

1. Check WMI service status:
   - Normal: Winmgmt Running and /verifyrepository output indicates repository is consistent
   - Abnormal: Winmgmt stopped -> **Root cause**: WMI service not running, **Severity**: Critical
2. Check WMI repository integrity:
   - Normal: Repository consistent
   - Abnormal: /verifyrepository output indicates repository inconsistent -> **Root cause**: WMI repository corrupted, **Severity**: Warning
3. Check WMI query availability:
   - Normal: Get-CimInstance query succeeds
   - Abnormal: Get-CimInstance reports error -> **Root cause**: WMI query failed, **Severity**: Critical

### Step 4: Event Log Service Check

**Data Collection**:

> Collection target: Check Event Log service status

- PowerShell script: [system-management.ps1](references/online/scripts/system-management.ps1) Section Step 4

**Analysis Approach**:

1. Check Event Log service:
   - Normal: EventLog Running and log not full
   - Abnormal: EventLog stopped -> **Root cause**: Event Log service not running, **Severity**: Warning
   - Abnormal: IsLogFull=True -> **Root cause**: Log file is full, new events cannot be recorded, **Severity**: Warning

### Step 5: MMC Console Check

**Data Collection**:

> Collection target: Check MMC related components and .NET Framework status

- PowerShell script: [system-management.ps1](references/online/scripts/system-management.ps1) Section Step 5

**Analysis Approach**:

1. Check MMC component integrity:
   - Normal: mmc.exe exists and .NET Framework is installed
   - Abnormal: mmc.exe does not exist -> System file missing
   - Abnormal: .NET Framework not installed or version too low -> MMC snap-ins may not load

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | WMI service anomaly affects Cloud Assistant | -> [cloud-vminit.md](references/online/cloud-vminit.md) (vminit service check) |
| Conditional jump | Execution policy blocks script execution | -> [system-gpo.md](references/online/system-gpo.md) (Group Policy check) |
| Chain successor | No root cause confirmed in this file | -> [cloud-vminit.md](references/online/cloud-vminit.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [system-management.md](references/online/fixes/system-management.md).
