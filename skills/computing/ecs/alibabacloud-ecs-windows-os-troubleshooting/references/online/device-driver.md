# Device Driver Diagnostics

## Function Description

Diagnoses Windows device driver status, including driver installation, version, signature status, Device Manager anomalies (yellow exclamation mark/error codes), driver service status. Covers general device driver issues.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Yellow exclamation mark in Device Manager | Step 1 (Device status and error codes) |
| Device cannot start (error codes 10/28/31/39/43) | Step 2 (Driver installation and signature status) |
| Driver not installed or version too old | Step 3 (Driver version and update status) |
| Driver signature verification failed | Step 2 (Driver installation and signature status) |

## Diagnostic Steps

### Step 1: Check Device Status and Error Codes

**Data Collection**:

> Collection target: Obtain status of all PnP devices in Device Manager, identify abnormal devices (error codes not 0)

**Analysis Approach**:

- PowerShell script: [device-driver.ps1](references/online/scripts/device-driver.ps1) Section Step 1

1. Check device error codes:
   - Normal: All device error codes are 0
   - Abnormal: Non-zero error code appears -> determine issue type based on error code:
     - Code 1: Device not correctly configured -> **Root cause**: Device configuration abnormal, **Severity**: Warning
     - Code 10: Device cannot start -> **Root cause**: Device cannot start, possibly driver incompatibility or hardware failure, **Severity**: Critical
     - Code 28: Driver not installed -> **Root cause**: Device driver not installed, **Severity**: Critical
     - Code 31: Device not working properly -> **Root cause**: Device working abnormally, **Severity**: Critical
     - Code 39: Driver corrupted -> **Root cause**: Driver program corrupted, **Severity**: Critical
     - Code 43: Driver reported device failure -> **Root cause**: Driver reported device failure, **Severity**: Critical
     - Other codes: Refer to Microsoft documentation to determine specific issue

> If network adapter driver abnormality is found, see -> [networking-tcpip.md](references/online/networking-tcpip.md)
> If storage controller driver abnormality is found, see -> [storage-hardware.md](references/online/storage-hardware.md)
> If VirtIO/Xen driver issues are found, see -> [cloud-driver.md](references/online/cloud-driver.md)

### Step 2: Check Driver Installation and Signature Status

**Data Collection**:

> Collection target: Obtain list of installed third-party driver packages, check driver signature status

**Analysis Approach**:

- PowerShell script: [device-driver.ps1](references/online/scripts/device-driver.ps1) Section Step 2

1. Check third-party driver packages:
   - Normal: All drivers have valid signatures
   - Abnormal: Unsigned or invalid signature drivers found -> **Root cause**: Driver signature abnormal, may be rejected by system from loading, **Severity**: Warning
2. Check Test Signing mode:
   - Normal: Test Signing not enabled
   - Abnormal: Test Signing enabled -> **Root cause**: Test signing mode enabled, security risk, **Severity**: Warning

### Step 3: Check Driver Version and Update Status

**Data Collection**:

> Collection target: Obtain driver version information and driver service status for abnormal devices

**Analysis Approach**:

- PowerShell script: [device-driver.ps1](references/online/scripts/device-driver.ps1) Section Step 3

1. Check driver service status:
   - Normal: All non-disabled driver services are running
   - Abnormal: Driver service that should be running but is not -> **Root cause**: Driver service not started properly, corresponding device will not work properly, **Severity**: Critical

### Step 4: Check Driver Installation Policy

> This step is the same as [cloud-driver.md](references/online/cloud-driver.md) Step 3. If cloud-driver.md Step 3 has already been executed, directly reuse its results; otherwise jump to execute -> [cloud-driver.md Step 3](references/online/cloud-driver.md) (Driver installation policy check).

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | Step 1 found network adapter driver abnormality | -> [networking-tcpip.md](references/online/networking-tcpip.md) |
| Conditional jump | Step 1 found storage controller driver abnormality | -> [storage-hardware.md](references/online/storage-hardware.md) |
| Conditional jump | Step 1 found VirtIO/Xen driver issues | -> [cloud-driver.md](references/online/cloud-driver.md) |
| Chain successor | No root cause confirmed in this file | -> [system-management.md](references/online/system-management.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [device-driver.md](references/online/fixes/device-driver.md).
