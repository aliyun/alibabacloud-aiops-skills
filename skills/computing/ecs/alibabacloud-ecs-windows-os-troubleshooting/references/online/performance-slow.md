# Performance Slow Diagnostics

## Feature Description

Diagnoses Windows system performance issues: CPU usage, memory usage, system handle count, page file configuration, hardware reserved memory, hyper-threading status, CPU/memory limits in BCD boot configuration, power plan, third-party file system filter drivers. Covers 8 diagnostic steps.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Symptom | Recommended Steps |
|-------------|---------------|
| System sluggish, slow response | Step 1 (CPU Usage) -> Step 2 (Memory Usage and Handle Count) |
| New programs cannot start, insufficient memory | Step 2 (Memory Usage and Handle Count) -> Step 3 (Page File Configuration) |
| Applications cannot open new windows or files | Step 2 (Memory Usage and Handle Count) |
| Available memory significantly less than total physical memory | Step 4 (Hardware Reserved Memory) |
| CPU core count/memory less than instance specification | Step 5 (Hyper-Threading Status) -> Step 6 (BCD Boot Limits) |
| Slow file/program opening, noticeable delay after double-click | Step 8 (File System Filter Driver) |
| Overall performance anomaly, slow but no clear direction | Step 1 -> Step 2 -> Step 3 -> Step 7 (Power Plan) -> Step 8 (File System Filter Driver) |

## Diagnostic Steps

### Step 1: CPU Usage

**Data Collection**:

> Collection target: Overall CPU usage, per-core usage, Top 5 CPU-consuming processes

> **Performance note**: CPU sampling window is 1 second (1 sample), prioritizing diagnostic speed. For more accurate long-term CPU trends, adjust `-SampleInterval` to 5 seconds and `-MaxSamples` to 3 or more.

- PowerShell script: [performance-slow.ps1](references/online/scripts/performance-slow.ps1) Section Step 1
- PowerShell auxiliary collection:
  - PowerShell collects CPU usage (`Get-Counter '\Processor(_Total)\% Processor Time'`) to query CPU usage within a specified time window
  - PowerShell collects Top-N processes (`Get-Process | Sort-Object CPU -Descending | Select-Object -First 5`) to identify the consuming processes

**Analysis**:

1. Check overall CPU usage (_Total instance):
   - Below 85% -> Normal
   - Above 85% -> **Root cause**: Overall CPU usage too high, combined with Top 5 process analysis to identify the source, **Severity**: Warning

2. Check per-core CPU usage:
   - All cores below 85% -> Normal
   - Single core consistently above 85% -> **Root cause**: Some CPU cores overloaded, possible single-threaded application or interrupt affinity issue, **Severity**: Warning

3. Check Top 5 CPU-consuming processes:
   - If third-party antivirus software processes have high usage -> See [desktop-app.md](references/online/desktop-app.md) (antivirus software resource consumption)

### Step 2: Memory Usage and Handle Count

**Data Collection**:

> Collection target: Total physical memory, available memory, usage, total system handle count, Top 5 memory/handle-consuming processes

- PowerShell script: [performance-slow.ps1](references/online/scripts/performance-slow.ps1) Section Step 2
- PowerShell auxiliary collection:
  - PowerShell collects memory usage (`Get-Counter '\Memory\Available MBytes'`) to query memory usage trends, parameters and return semantics same as Step 1
  - PowerShell collects Top-N memory-consuming processes (`Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5`)

**Analysis**:

1. Check memory usage:
   - Usage below 80% and available memory above 512MB -> Normal
   - Usage above 80% or available memory below 512MB -> **Root cause**: Memory usage too high, combined with Top 5 process analysis to identify memory consumption source, **Severity**: Warning

2. Check total system handle count:
   - Below 100000 -> Normal
   - Above 100000 -> **Root cause**: System handle count too high, possible handle leak in an application, **Severity**: Warning

### Step 3: Page File Configuration

**Data Collection**:

> Collection target: Page file (virtual memory) configuration status, including memory management registry configuration and current page file usage

- PowerShell script: [performance-slow.ps1](references/online/scripts/performance-slow.ps1) Section Step 3

**Analysis**:

1. Check automatic page file management status:
   - AutomaticManagedPagefile is True -> System automatically manages page file size (Microsoft recommended configuration), normal. Note: In automatic management mode, the registry PagingFiles field may not contain a fixed configuration value, and Win32_PageFileSetting may also return empty; do not determine "not configured" based on this; check actual page file allocation and usage via Win32_PageFileUsage
   - AutomaticManagedPagefile is False -> Manual configuration mode, proceed to step 2 to check configuration status

2. Check whether the page file actually exists:
   - Win32_PageFileUsage returns non-empty result -> Page file is configured and in use, regardless of automatic or manual management
   - Win32_PageFileUsage returns empty result -> Proceed to step 3

3. Check manually configured page file registry entries (only applicable when AutomaticManagedPagefile = False):
   - Both PagingFiles and ExistingPageFiles are empty -> **Root cause**: Page file not configured in manual management mode; when physical memory is exhausted, applications will crash directly, **Severity**: Warning
   - PagingFiles contains a valid path -> Page file is manually configured, need to check whether the size is reasonable combined with Win32_PageFileSetting

4. Check whether page file settings are reasonable in manual configuration mode:
   - Win32_PageFileSetting returns empty but Win32_PageFileUsage has data -> Page file is managed by the system automatically or created through other means
   - Both InitialSize and MaximumSize are valid -> Page file size range is manually configured
   - InitialSize = MaximumSize -> Fixed-size page file, note whether the size is sufficient
   - InitialSize < MaximumSize -> Dynamic expansion, system automatically adjusts within the range

5. Check current page file usage:
   - CurrentUsage close to AllocatedBaseSize -> Page file nearly exhausted, determine whether expansion is needed combined with memory usage
   - PeakUsage much higher than AllocatedBaseSize -> Page file was previously insufficient

6. Check crash dump dependencies:
   - CrashDumpEnabled = 1 (complete memory dump) -> Page file must be >= physical memory + 1MB
   - CrashDumpEnabled = 2 (kernel dump) -> Page file recommended >= 1/3 of physical memory
   - CrashDumpEnabled = 7 (automatic memory dump, Server 2012+ default) -> System automatically calculates required size
   - When page file is not configured, crash dump cannot be generated, BSOD dump file will be lost

### Step 4: Hardware Reserved Memory

**Data Collection**:

> Collection target: OS-visible physical memory and the SMBIOS installed-memory probe result (raw values; hardware reserved is derived in analysis against the instance-type baseline)

- PowerShell script: [performance-slow.ps1](references/online/scripts/performance-slow.ps1) Section Step 4

**Analysis**:

1. Compute hardware reserved as: instance-type memory (from `aliyun ecs describe-instances`, `Memory` field, MB) - `VisiblePhysicalMB` (script Section Step 4 output). Do NOT compute it as `SMBIOSInstalledMB - VisiblePhysicalMB`: `GetPhysicallyInstalledSystemMemory` is SMBIOS-based and on ECS VMs has been observed to return the OS-visible amount (Installed == Visible, e.g. both 8046 MB on an 8 GB instance), so that difference is always ~0 -- a zero there is a measurement artifact, never evidence of "no hardware reservation". Judge the reserved amount:
   - Hardware reserved less than 2GB -> Normal
   - Hardware reserved exceeds 2GB and visible physical memory does not exceed 2GB -> **Root cause**: Hardware reserved memory too high, possibly due to Windows activation anomaly or driver allocation issue causing system available memory to be far less than physical memory, **Severity**: Warning

2. Common causes of high hardware reserved memory:
   - Windows not activated or license anomaly -> See [system-activation.md](references/online/system-activation.md)
   - "Maximum memory" limit set in msconfig (Boot Advanced Options -> Maximum Memory) -> Check whether truncatememory or removememory configuration exists in bcdedit /enum (see Step 6)
   - 32-bit OS memory addressing limit (max 4GB, Server editions and PAE can extend)
   - BIOS/UEFI configuration allocating memory to integrated graphics or other peripherals (usually not applicable in cloud server scenarios)

### Step 5: Hyper-Threading Status

**Data Collection**:

> Collection target: CPU physical core count and logical processor count, to determine whether hyper-threading is enabled

- PowerShell script: [performance-slow.ps1](references/online/scripts/performance-slow.ps1) Section Step 5

**Analysis**:

1. Check hyper-threading status (compare physical core count and logical processor count):
   - Logical processor count > Physical core count -> Hyper-threading enabled, normal
   - Logical processor count = Physical core count -> **Root cause**: Hyper-threading not enabled, system visible CPU core count is half of the instance specification, **Severity**: Warning

2. Check registry mitigation configuration:
   - FeatureSettingsOverride and FeatureSettingsOverrideMask are used to control mitigation strategies for CPU microarchitecture vulnerabilities such as Spectre, Meltdown, L1TF, MDS
   - When mitigation configuration includes a value that disables hyper-threading (e.g., in L1TF/MDS mitigation, FeatureSettingsOverride includes bit 6, i.e., 0x40 or higher value) -> **Root cause**: CPU microarchitecture security mitigation applied via registry, this configuration disables hyper-threading, **Severity**: Warning
   - Not configured or value does not include the bit that disables hyper-threading -> Normal
   - Note: These registry entries are located at `HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management`; removing mitigations will reduce system protection against CPU microarchitecture vulnerabilities, requiring a trade-off between performance and security risk

### Step 6: BCD Boot Configuration Limits

**Data Collection**:

> Collection target: Whether CPU count or memory size limits exist in BCD boot configuration

- PowerShell script: [performance-slow.ps1](references/online/scripts/performance-slow.ps1) Section Step 6

**Analysis**:

1. Check processor limits in the current BCD boot entry:
   - No numproc or usebootprocessoronly configuration -> Normal, system uses all available CPUs
   - numproc configuration exists (e.g., `numproc  1`) -> **Root cause**: BCD boot configuration limits the number of available processors, system can only use partial CPUs, **Severity**: Warning
   - usebootprocessoronly exists and value is Yes -> **Root cause**: BCD configured to use only the boot processor, system can only use 1 CPU, **Severity**: Warning
   - Note: These configurations can also be set through msconfig -> Boot -> Advanced options -> "Number of processors" checkbox

2. Check memory limits in BCD:
   - No truncatememory or removememory configuration -> Normal
   - truncatememory or removememory exists -> **Root cause**: BCD boot configuration truncates or removes part of the memory, system available memory is less than actual physical memory, **Severity**: Warning
   - Note: truncatememory can also be set through msconfig -> Boot -> Advanced options -> "Maximum memory" checkbox

### Step 7: Power Plan

**Data Collection**:

> Collection target: Currently active power plan

- PowerShell script: [performance-slow.ps1](references/online/scripts/performance-slow.ps1) Section Step 7

**Analysis**:

1. Check current power plan:
   - High Performance (GUID: `8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c`) or Ultimate Performance -> Normal, CPU will run at maximum frequency
   - Balanced (GUID: `381b4222-f694-41f0-9685-ff5bb260df2e`) -> Windows Server 2016+ default power plan, dynamically adjusts frequency based on CPU load; for latency-sensitive server scenarios (e.g., databases, real-time processing), switching to High Performance is recommended
   - Power Saver (GUID: `a1841308-3541-4fab-bc81-f71556f20b4a`) -> **Root cause**: Power plan set to Power Saver mode, CPU is limited to low frequency, **Severity**: Warning

2. Additional notes for server scenarios:
   - Microsoft officially recommends using Balanced or High Performance power plan for servers
   - Windows Server 2016+ Balanced scheme has been optimized for server scenarios, response speed is close to High Performance
   - However, if the user confirms performance issues exist and currently using Balanced, switching to High Performance can eliminate the frequency adjustment latency factor

### Step 8: File System Filter Driver Check

**Data Collection**:

> Collection target: Get all registered file system minifilter driver lists, check for third-party filter drivers

- PowerShell script: [performance-slow.ps1](references/online/scripts/performance-slow.ps1) Section Step 8

**Analysis**:

1. Check for third-party filter drivers not signed by Microsoft:
   - Normal: Only contains Microsoft standard filter drivers (e.g., WdFilter, fvevol, luafv, FileInfo, Dedup, wcifs, etc.)
   - Abnormal: Non-Microsoft filter driver exists -> Check whether the driver is known to cause performance issues
   - Explanation: Third-party file system filter drivers intercept all file I/O operations (open, read/write, delete, etc.); driver anomalies or improper design can significantly slow down file operations and program startup speed

2. Third-party filter drivers known to cause system slowness:
   - **CcProtect**: A security software filter driver that delays all file open operations, manifesting as long unresponsiveness after double-clicking a file or program
   - Filter drivers from other security software, backup software, and encryption software may also cause similar issues

3. Check Num Instances column:
   - Normal: Each driver's instance count is within its expected range
   - Abnormal: A driver's instance count is abnormally high, possible resource leak

If a third-party filter driver is found and confirmed as the source of performance issues, see -> [desktop-app.md](references/online/desktop-app.md) (security software process/filter driver troubleshooting)

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | Antivirus software in top CPU-consuming processes | -> [desktop-app.md](references/online/desktop-app.md) |
| Conditional jump | Hardware reserved memory too high and suspected activation anomaly | -> [system-activation.md](references/online/system-activation.md) |
| Conditional jump | Slow system startup, frequent unexpected restarts | -> [performance-lifecycle.md](references/online/performance-lifecycle.md) |
| Conditional jump | Third-party file system filter driver found and suspected as performance issue source | -> [desktop-app.md](references/online/desktop-app.md) |
| Chain successor | No root cause confirmed in this file | -> [performance-lifecycle.md](references/online/performance-lifecycle.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [performance-slow.md](references/online/fixes/performance-slow.md).
