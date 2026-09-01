# Storage Hardware and Drivers Diagnostics

## Function Description

Diagnoses Windows storage hardware and driver stack issues: SCSI controller status, disk driver status, residual registry filter drivers, disk class driver configuration, storage-related event logs (VirtIO errors, device removal failures). Covers 10 known issue items.

**Input**: User problem description (required), error code/Event ID/screenshot (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Disk controller abnormal, yellow exclamation mark | Step 1 (SCSI Controller) -> Step 2 (Disk Driver) |
| Disk mounted in console but not visible in system | Step 1 (SCSI Controller) -> Step 2 (Disk Driver) -> Step 4 (Class Driver) |
| Disk driver error, BSOD | Step 2 (Disk Driver) -> Step 3 (Registry Filter Driver) -> Step 4 (Class Driver) |
| Disk inaccessible after uninstalling security software | Step 3 (Registry Filter Driver) -> Step 4 (Class Driver) |
| Intermittent disk I/O failures, Event ID 11 | Step 5 (Storage Event Log) |
| Resource leak after hot-detaching cloud disk, Event 225 | Step 5 (Storage Event Log) |

## Diagnostic Steps

### Step 1: SCSI Controller Status Check

**Data Collection**:

> Collection target: Obtain status, driver names, and Device Manager error codes for all SCSI controllers, as well as associated disk devices

- PowerShell script: [storage-hardware.ps1](references/online/scripts/storage-hardware.ps1) Section Step 1

**Analysis Approach**:

1. Check SCSI controller status:
   - Normal: Status is OK, no error codes
   - Abnormal: Status is not OK or error codes exist -> **Root cause**: SCSI controller status abnormal, **Severity**: Critical
   - Note: Exclude Microsoft Storage Spaces controller (ROOT\SPACEPORT), it is normal for it to have no associated disks

2. Check whether the controller has associated disks:
   - Normal: Each non-SPACEPORT controller has at least one associated disk
   - Abnormal: Controller is normal but has no associated disks -> **Root cause**: SCSI controller has no associated disks, **Severity**: Critical

If SCSI controller abnormality is found and it is a VirtIO driver, see -> [cloud-driver.md](references/online/cloud-driver.md)

### Step 2: Disk Driver Status Check

**Data Collection**:

> Collection target: Obtain status, driver service names, and error codes for all disk drive devices

- PowerShell script: [storage-hardware.ps1](references/online/scripts/storage-hardware.ps1) Section Step 2

**Analysis Approach**:

1. Check disk driver status:
   - Normal: Status is OK, no error codes
   - Abnormal: Status is not OK or non-zero error codes exist -> **Root cause**: Disk driver status abnormal, **Severity**: Critical
   - Common error codes: 10 (cannot start), 28 (driver not installed), 31 (device not working properly), 43 (device has been stopped)

If driver status abnormality is found, see -> [device-driver.md](references/online/device-driver.md) (Device Manager error code troubleshooting)

### Step 3: Registry Filter Driver Check

**Data Collection**:

> Collection target: Obtain registry filter driver configuration for disk device instances under the SCSI bus, check for residual third-party filter drivers

- PowerShell script: [storage-hardware.ps1](references/online/scripts/storage-hardware.ps1) Section Step 3

**Analysis Approach**:

1. Check whether filter drivers exist:
   - Normal: No filter drivers, or filter drivers correspond to normally running services
   - Abnormal: Filter driver exists but corresponding service does not exist or has stopped -> **Root cause**: Residual filter driver in registry, **Severity**: Critical
   - Common scenario: Residual storage filter driver after uninstalling antivirus software (e.g., Symantec, McAfee, Kaspersky)

### Step 4: Disk Class Driver Check

**Data Collection**:

> Collection target: Obtain class-level filter driver configuration for disk-related device classes (SCSIAdapter, DiskDrive, Volume)

- PowerShell script: [storage-hardware.ps1](references/online/scripts/storage-hardware.ps1) Section Step 4

**Analysis Approach**:

1. Check SCSIAdapter class filter driver:
   - Normal: No filter drivers (standard configuration)
   - Abnormal: Filter driver exists and corresponding service is abnormal -> **Root cause**: Disk class filter driver abnormal, **Severity**: Critical

2. Check DiskDrive class filter driver:
   - Normal standard configuration: UpperFilters includes `partmgr`; Win8 and above LowerFilters includes `EhStorClass`; `dump_*` (dump filter drivers, e.g., dump_dumpfve/dump_stordumpnvme) are system standard configuration
   - Abnormal (class driver not found): DiskDrive class registry key does not exist -> **Root cause**: Disk class driver not found, **Severity**: Critical
   - Abnormal (filter driver abnormal): Filter driver outside the standard whitelist (partmgr/EhStorClass/dump_*) exists and corresponding service is abnormal -> **Root cause**: Disk class filter driver abnormal, **Severity**: Critical
   - Abnormal (non-standard filter driver): Filter driver outside the standard whitelist exists but service is normal -> **Root cause**: Non-standard filter driver present, **Severity**: Warning
   - Abnormal (standard filter driver missing): `partmgr` or `EhStorClass` missing -> **Root cause**: Standard filter driver missing, **Severity**: Critical

3. Check Volume class filter driver:
   - Normal standard configuration: Win10 and above UpperFilters includes `volsnap`; when system has BitLocker feature, LowerFilters includes `fvevol` (BitLocker volume filter driver, installed by default on Windows Server, not an abnormality); `dump_*` are system standard configuration
   - Abnormal (class driver not found): Volume class registry key does not exist -> **Root cause**: Disk class driver not found, **Severity**: Critical
   - Abnormal (filter driver abnormal): Filter driver outside the standard whitelist (volsnap/fvevol/dump_*) exists and corresponding service is abnormal -> **Root cause**: Disk class filter driver abnormal, **Severity**: Critical
   - Abnormal (non-standard filter driver): Filter driver outside the standard whitelist exists but service is normal -> **Root cause**: Non-standard filter driver present, **Severity**: Warning
   - Abnormal (standard filter driver missing): `volsnap` missing -> **Root cause**: Standard filter driver missing, **Severity**: Critical

### Step 5: Storage Event Log Check

**Data Collection**:

> Collection target: Obtain VirtIO storage driver error events (Event ID 11) and PnP device removal failure events (Event ID 225) from the last 7 days

- PowerShell script: [storage-hardware.ps1](references/online/scripts/storage-hardware.ps1) Section Step 5

**Analysis Approach**:

1. Check VirtIO storage driver errors (Event ID 11):
   - Normal: No Event ID 11 events
   - Abnormal: Event ID 11 events exist -> **Root cause**: VirtIO storage driver internal error (Event ID 11), **Severity**: Warning
   - Note: Usually I/O errors reported by the VirtIO storage driver (viostor/vioscsi), may be due to outdated driver version or transient underlying storage abnormalities

2. Check PnP device removal failures (Event ID 225):
   - Normal: No Event ID 225 events, or events do not involve VirtIO devices
   - Abnormal: Event 225 targeting VirtIO devices (PCI\VEN_1AF4&DEV_1001 or PCI\VEN_8086&DEV_5845) exists -> **Root cause**: Disk device removal failure (Event 225), **Severity**: Warning
   - Note: Usually occurs during hot-detach of cloud disk when a process still holds the disk handle, causing removal failure

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 1/2 finds VirtIO driver-related abnormality | -> [cloud-driver.md](references/online/cloud-driver.md) |
| Conditional jump | Step 2 finds Device Manager error code | -> [device-driver.md](references/online/device-driver.md) |
| Chained successor | Root cause not confirmed in this file, user reports disk not visible | -> [device-driver.md](references/online/device-driver.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [storage-hardware.md](references/online/fixes/storage-hardware.md).
