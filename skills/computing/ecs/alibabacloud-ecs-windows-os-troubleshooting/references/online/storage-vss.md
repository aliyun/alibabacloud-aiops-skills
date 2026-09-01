# Storage VSS (Volume Shadow Copy Service) Diagnostics

## Function Description

Diagnoses Windows Volume Shadow Copy Service (VSS) related issues: VSS service and its dependency service status abnormalities, VSS Writer status abnormalities (Failed / Unstable / Waiting for completion), VSS Provider registration issues, VSS snapshot creation failures and insufficient storage space, VSS-related event log errors (Event ID 8193 / 12289 / 12293), Windows Server Backup execution failures. Covers 9 known issue items.

**Input**: User problem description (required), error code/Event ID/screenshot (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Backup failure, VSS error reported | Step 1 (VSS service and dependencies) -> Step 2 (VSS Writer status) -> Step 5 (VSS event log) |
| VSS Writer status Failed / Unstable | Step 1 (VSS service and dependencies) -> Step 2 (VSS Writer status) |
| Snapshot creation failure, restore point cannot be created | Step 1 (VSS service and dependencies) -> Step 3 (VSS Provider) -> Step 4 (VSS snapshot and storage) |
| VSS errors in event log (8193 / 12289 / 12293) | Step 5 (VSS event log) -> Step 1 (VSS service and dependencies) -> Step 2 (VSS Writer status) |
| Windows Server Backup errors | Step 1 (VSS service and dependencies) -> Step 2 (VSS Writer status) -> Step 6 (backup software) |
| Third-party backup software (Veeam / Acronis etc.) failure | Step 2 (VSS Writer status) -> Step 3 (VSS Provider) -> Step 5 (VSS event log) |

## Diagnostic Steps

### Step 1: VSS Service and Dependency Service Check

**Data Collection**:

> Collection target: Obtain running status and startup type of VSS service and its core dependency services (COM+ Event System, RPC, DCOM Server Process Launcher)

- PowerShell script: [storage-vss.ps1](references/online/scripts/storage-vss.ps1) Section Step 1

**Analysis Approach**:

1. Check VSS service status and startup type:
   - Normal: VSS service startup type is Manual, can start on demand; Stopped state when no backup or snapshot operation is in progress is normal
   - Abnormal: VSS service startup type is Disabled -> **Root cause**: VSS service disabled, **Severity**: Critical

2. Check COM+ Event System service:
   - Normal: Service is in Running state, startup type is Automatic
   - Abnormal: Service not running or disabled -> **Root cause**: VSS dependency service abnormal, **Severity**: Critical
   - Note: VSS depends on COM+ Event System for inter-component communication; abnormality in this service will cause all VSS operations to fail

3. Check RPC and DCOM services:
   - Normal: Both RpcSs and DcomLaunch are in Running state
   - Abnormal: Either service not running -> **Root cause**: VSS dependency service abnormal, **Severity**: Critical

4. Check Software Shadow Copy Provider service (swprv):
   - Normal: Startup type is Manual, starts on demand
   - Abnormal: Disabled -> **Root cause**: VSS service disabled, **Severity**: Critical
   - Note: swprv is the Windows built-in VSS software shadow copy provider; when disabled, snapshots cannot be created

### Step 2: VSS Writer Status Check

**Data Collection**:

> Collection target: Obtain name, status, and error information of all VSS Writers, identify Writers in abnormal states

- PowerShell script: [storage-vss.ps1](references/online/scripts/storage-vss.ps1) Section Step 2

**Analysis Approach**:

1. Check the running status of all Writers:
   - Normal: All Writer statuses show Stable
   - Abnormal: Any Writer status is one of the following values -> **Root cause**: VSS Writer status abnormal, **Severity**: Warning
     - **Failed**: Writer encountered an error, needs restart of the corresponding control service
     - **Unstable**: Writer is in an unstable state, needs restart of the corresponding control service
     - **Waiting for completion**: Writer is being held by a process, or the previous operation did not complete normally; if no backup is currently running, it means the Writer is stuck and also needs a restart

2. Identify abnormal Writers and determine the corresponding control service:
   - Each VSS Writer is controlled by a specific Windows service; restarting that service can restore the Writer to Stable state
   - Common Writer-to-control-service mapping (used to guide fixes):

     | Writer Name | Control Service |
     |------------|--------|
     | System Writer | Cryptographic Services (CryptSvc) |
     | WMI Writer | Windows Management Instrumentation (Winmgmt) |
     | COM+ REGDB Writer | COM+ System Application (COMSysApp) |
     | Task Scheduler Writer | Task Scheduler (Schedule) |
     | Registry Writer | VSS (VSS) |
     | VSS Metadata Store Writer | VSS (VSS) |
     | Performance Counters Writer | VSS (VSS) |
     | SqlServerWriter | SQL Server (MSSQLSERVER) |
     | BITS Writer | Background Intelligent Transfer (BITS) |
     | IIS Config Writer | IIS Admin Service (IISADMIN) |
     | Hyper-V Writer | Hyper-V Virtual Machine Management (vmms) |

   - Note: If the Writer name is not in the table above, you can find the corresponding service in the Windows service list using the Writer's Instance information

3. Check whether multiple Writers are abnormal simultaneously:
   - If only a single Writer is abnormal, it is usually a problem with the service/application corresponding to that Writer
   - If many Writers are abnormal simultaneously, it is usually a problem with the VSS infrastructure (VSS service itself or COM+ Event System); prioritize checking Step 1

### Step 3: VSS Provider Check

**Data Collection**:

> Collection target: Obtain all VSS Providers registered in the system, identify whether third-party Providers exist and whether Providers are properly registered

- PowerShell script: [storage-vss.ps1](references/online/scripts/storage-vss.ps1) Section Step 3

**Analysis Approach**:

1. Check whether the built-in system Provider exists:
   - Normal: At least Microsoft Software Shadow Copy provider 1.0 exists (Provider Id: {b5946137-7b9f-4925-af80-51abd60b20d5})
   - Abnormal: Built-in Provider missing -> **Root cause**: VSS Provider registration abnormal, **Severity**: Critical

2. Check whether third-party Providers exist:
   - Normal: Only Microsoft built-in Provider
   - Note: Third-party backup software (e.g., Veeam, Acronis, Veritas) may register their own VSS Provider
   - Abnormal: Third-party Provider exists but corresponding software has been uninstalled; residual Provider registration information may cause VSS snapshot creation failure -> **Root cause**: Residual third-party VSS Provider, **Severity**: Warning

### Step 4: VSS Snapshot and Storage Space Check

**Data Collection**:

> Collection target: Obtain the VSS snapshot list on the current system, VSS storage space usage, and configuration limits

- PowerShell script: [storage-vss.ps1](references/online/scripts/storage-vss.ps1) Section Step 4

**Analysis Approach**:

1. Check VSS snapshot list:
   - Normal: Snapshots can be listed normally, or the list is empty (no automatic snapshots configured is normal)
   - Abnormal: Command execution error -> check VSS service status with Step 1

2. Check VSS storage space usage:
   - Normal: Used storage space is far less than the maximum limit
   - Abnormal: Used space is close to or at the maximum limit (Used Shadow Copy Storage approaching Maximum Shadow Copy Storage) -> **Root cause**: VSS snapshot storage space insufficient, **Severity**: Warning
   - Note: When snapshot storage space is exhausted, new snapshot creation will fail, and the oldest snapshots may be automatically deleted

3. Check snapshot count:
   - Normal: Snapshot count per volume has not reached the limit (Windows supports up to 512 snapshots per volume)
   - Abnormal: Too many snapshots (approaching 512) -> **Root cause**: VSS snapshot storage space insufficient, **Severity**: Warning

### Step 5: VSS Event Log Analysis

**Data Collection**:

> Collection target: Obtain VSS-related error and warning events from Application log and System log within the last 7 days

- PowerShell script: [storage-vss.ps1](references/online/scripts/storage-vss.ps1) Section Step 5

**Analysis Approach**:

1. Check whether VSS error events exist, focusing on the following common Event IDs:

   | Event ID | Meaning | Typical Root Cause |
   |----------|------|--------|
   | 8193 | VSS operation call failed | Permission issues, COM component registration abnormal, dependency service unavailable |
   | 8194 | VSS could not get Writer information | Writer's corresponding service abnormal |
   | 12289 | VSS Provider operation failed | Third-party Provider abnormal, disk I/O error |
   | 12293 | VSS Shadow Copy Provider call timed out | Disk I/O too high causing snapshot timeout |
   | 12298 | VSS snapshot creation timed out | High system load, slow disk response |

   - Normal: No VSS error or warning events
   - Abnormal: Any of the above events exist -> **Root cause**: VSS event log reports error, **Severity**: Warning
   - Note: Event ID 12293 / 12298 are usually related to disk I/O performance; during high load periods, the disk cannot complete snapshot operations within the timeout window

2. Check volsnap events:
   - volsnap is the Windows snapshot driver, recording issues at the snapshot storage layer
   - Abnormal: Events indicating insufficient diff area space -> link to Step 4 storage space check

If event log points to disk I/O performance issues, see -> [storage-hardware.md](references/online/storage-hardware.md)

### Step 6: Backup Software Status Check

**Data Collection**:

> Collection target: Obtain Windows Server Backup feature installation status and recent backup execution results

- PowerShell script: [storage-vss.ps1](references/online/scripts/storage-vss.ps1) Section Step 6

**Analysis Approach**:

1. Check backup feature installation status:
   - Normal: Windows-Server-Backup feature installed
   - Abnormal: Feature not installed -> inform user that the feature needs to be installed first

2. Check backup execution results:
   - Normal: Recent backup events show success
   - Abnormal: Backup events show failure -> **Root cause**: Backup execution failed, **Severity**: Warning
   - Note: Backup failures are usually related to VSS Writer abnormalities; combine with Step 2 Writer status for comprehensive judgment; if the backup log explicitly mentions a Writer name, you can directly locate the corresponding Writer and control service

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 4 finds insufficient snapshot storage space, need to check volume free space | -> [storage-disk.md](references/online/storage-disk.md) (check volume space usage) |
| Conditional jump | Step 5 event log points to disk I/O performance or storage driver abnormality | -> [storage-hardware.md](references/online/storage-hardware.md) |
| Parameterized reference | Step 3 finds residual third-party Provider involving driver/device issues | -> [device-driver.md](references/online/device-driver.md) (check third-party backup software related drivers) |
| Chained successor | All steps in this file completed, root cause not confirmed | -> [storage-disk.md](references/online/storage-disk.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [storage-vss.md](references/online/fixes/storage-vss.md).
