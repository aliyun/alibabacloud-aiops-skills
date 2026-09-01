# Cloud Driver Diagnostics

## Function Description

Diagnose Windows VirtIO driver version, presence, driver installation policy, and Xen driver residuals. Covers 3 known root causes.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Phenomenon | Recommended Steps |
|-------------|---------------|
| Virtual disk or NIC performance issues, intermittent disconnection | Step 1 (VirtIO driver package) -> Step 2 (VirtIO driver version) |
| Disk or network unavailable after migration to KVM platform | Step 1 (VirtIO driver package) -> Step 4 (Xen driver residual) |
| Device Manager still shows old driver after installing new driver | Step 3 (Driver installation policy) |
| NIC or disk not working after migration from Xen to KVM | Step 4 (Xen driver residual) |
| Corresponding virtual device cannot work properly | Step 1 (VirtIO driver package) -> Step 2 (VirtIO driver version) |

## Diagnostic Steps

### Step 1: VirtIO Driver Package Check

**Data Collection**:

> Collection target: Get all installed third-party driver packages in the system, filter for storage, network, system category drivers

**Analysis Approach**:

- PowerShell script: [cloud-driver.ps1](references/online/scripts/cloud-driver.ps1) Section Step 1

1. Check whether VirtIO core drivers exist:
   - Normal: Output contains the following key driver packages
     - `viostor.inf`: VirtIO storage driver
     - `netkvm.inf`: VirtIO network driver
     - `balloon.inf`: VirtIO memory balloon driver
     - `vioser.inf`: VirtIO serial port driver
   - Abnormal: Missing viostor.inf or netkvm.inf -> may cause disk or network unavailability on KVM platform, **severity**: Critical

2. Identify ProviderName to confirm driver source:
   - Alibaba Cloud official VirtIO driver ProviderName typically contains "Red Hat" or "Alibaba"

### Step 2: VirtIO Driver Version Check

**Data Collection**:

> Collection target: Enumerate installed VirtIO driver packages; when multiple versions exist for the same INF, take the best package (SelectBestDriver: newest date -> highest version)

**Analysis Approach**:

- PowerShell script: [cloud-driver.ps1](references/online/scripts/cloud-driver.ps1) Section Step 2

1. Version determination is based on the **best package** version in the driver repository (DriverStore):
   - Reason: When multiple driver package versions coexist, Windows PnP automatically selects the active package at boot by priority Rank -> Date -> Version; which version is actually active is guaranteed by the OS internal mechanism; therefore the diagnostic side **does not check the actually active/loaded .sys version** (the service ImagePath or device-bound driver may point to an old package, which is a transient state)
   - Best package selection simulates the PnP selection algorithm (SelectBestDriver): for the same INF with multiple packages, Rank is usually the same, selection is by **newest date -> highest version**; note that you cannot simply take the package with the highest version number (a higher version package may have an older date, and PnP will not select it)
   - When only one package exists for an INF, that package is the determination object

2. Check whether VirtIO driver version is too old:
   - Normal: Best package version number's 4th segment >= 58017 (e.g., `100.86.104.58200`, 4th segment is 58200 >= 58017)
   - Abnormal: Best package version number's 4th segment < 58017 -> **Root cause**: VirtIO driver version too old, **severity**: Warning
   - Note: Version threshold 58017 is the minimum version recommended by Alibaba Cloud; old versions may have performance issues or known bugs

### Step 3: Driver Installation Policy Check

**Data Collection**:

> Collection target: Check whether driver auto-installation is disabled via Group Policy or registry

**Analysis Approach**:

- PowerShell script: [cloud-driver.ps1](references/online/scripts/cloud-driver.ps1) Section Step 3

1. Check whether driver installation is disabled:
   - Normal: Registry key does not exist, or value is 0
   - Abnormal: `DeviceInstallDisabled` value is non-0 -> **Root cause**: Driver installation disabled by policy, **severity**: Warning
   - Note: Different Windows versions use different registry paths (`DeviceInstall\Parameters` or `PlugPlay\Parameters`), value name is always `DeviceInstallDisabled`

### Step 4: Xen Driver Residual Check

**Data Collection**:

> Collection target: Check for residual driver packages and services from Xen platform migration

**Analysis Approach**:

- PowerShell script: [cloud-driver.ps1](references/online/scripts/cloud-driver.ps1) Section Step 4

1. Check Xen driver package residual:
   - Normal: No Xen-related driver packages (xennet.inf, xenpci.inf, xenscsi.inf, xenstub.inf, xenvbd.inf)
   - Abnormal: Xen driver packages exist and XenPCI service's `hide_devices` parameter is non-empty -> **Root cause**: Xen driver residual, **severity**: Warning
   - Note: Xen driver's `hide_devices` parameter hides VirtIO devices, causing disk, NIC, and other virtual devices to be invisible on KVM platform

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Driver policy disabled by GPO | -> [system-gpo.md](references/online/system-gpo.md) (diagnose Group Policy configuration) |
| Conditional jump | Disk not visible but driver normal | -> [storage-hardware.md](references/online/storage-hardware.md) (diagnose storage hardware issues) |
| Conditional jump | Network unreachable but driver normal | -> [networking-tcpip.md](references/online/networking-tcpip.md) (diagnose network configuration) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [cloud-driver.md](references/online/fixes/cloud-driver.md).
