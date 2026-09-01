# Performance Lifecycle Diagnostics

## Function Description

Diagnoses Windows shutdown stuck/timeout, pending reboot operation status, system boot duration, boot phase breakdown, shutdown duration analysis, and abnormal shutdown/reboot events -- 6 diagnostic steps.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Shutdown slow, stuck on shutting down screen | Step 1 (Shutdown timeout config and auto-termination policy) |
| Update installation failed, prompted to restart first | Step 1 -> Step 2 (Pending reboot operation status) |
| System boot slow, long boot time | Step 3 (Boot duration and uptime) -> Step 5 (Boot phase breakdown) -> Step 4 (Shutdown/reboot event analysis) |
| System rebooted unexpectedly, abnormal shutdown | Step 3 -> Step 4 |
| Unsure whether system was unexpectedly shut down | Step 3 -> Step 4 |
| Shutdown process takes long, shutdown slow | Step 6 (Shutdown duration analysis) -> Step 1 (Shutdown timeout config) |
| Boot stuck at a certain phase (e.g., "Starting Windows") | Step 5 (Boot phase breakdown) -> Step 3 -> [device-driver.md](references/online/device-driver.md) |

## Diagnostic Steps

### Step 1: Shutdown Timeout Configuration and Auto-Termination Policy

**Data Collection**:

> Collection target: WaitToKillServiceTimeout, WaitToKillAppTimeout, HungAppTimeout, AutoEndTasks, GPO machine-level shutdown scripts

- PowerShell script: [performance-lifecycle.ps1](references/online/scripts/performance-lifecycle.ps1) Section Step 1

**Analysis Approach**:

1. Check WaitToKillServiceTimeout (service wait timeout, unit ms):
   - Default 5000 (5 seconds); when not configured, system uses default value -> Normal
   - Value set extremely large (>= 600000, i.e., 10 minutes) -> **Root cause**: Shutdown service wait timeout too long, a single service stuck can cause prolonged shutdown wait, **Severity**: Warning
   - Value set extremely small (< 2000) -> **Root cause**: Shutdown service wait timeout too short, services may be forcibly terminated causing data loss, **Severity**: Warning

2. Check WaitToKillAppTimeout (application wait timeout, unit ms):
   - Default 20000 (20 seconds); not configured -> Normal
   - Value set extremely large (>= 120000, i.e., 2 minutes) -> **Root cause**: Shutdown application wait timeout too long, **Severity**: Warning

3. Check HungAppTimeout (hung application determination timeout, unit ms):
   - Default 5000 (5 seconds) -> Normal
   - Value abnormally large (>= 30000) -> **Root cause**: System wait time for determining application "not responding" too long, hung applications will delay the shutdown process, **Severity**: Warning

4. Check AutoEndTasks (auto-terminate unresponsive tasks):
   - Value is 1 -> System auto-terminates unresponsive tasks, shutdown process will not get stuck waiting for user action
   - Value is 0 or not present (default value) -> Shutdown may pop up "waiting for program to close" dialog, requiring user to manually click to continue
   - In unattended server scenarios, default value causes shutdown to get stuck at waiting for user action interface -> **Root cause**: Auto-terminate task policy not enabled, unattended shutdown may get stuck at waiting for user action interface, **Severity**: Warning

5. Check GPO shutdown scripts:
   - Shutdown script is empty -> Normal
   - Shutdown script exists and shutdown is stuck -> Script may be executing timeout or hung

> If GPO shutdown script is blocking the shutdown process, see -> [system-gpo.md](references/online/system-gpo.md) (Group Policy application issues)

### Step 2: Pending Reboot Operation Status

**Data Collection**:

> Collection target: PendingFileRenameOperations (pending file rename/delete list), CBS (Component Based Servicing) RebootPending flag, Windows Update RebootRequired flag, number of incomplete operations in CBS Sessions

- PowerShell script: [performance-lifecycle.ps1](references/online/scripts/performance-lifecycle.ps1) Section Step 2

**Analysis Approach**:

1. Check PendingFileRenameOperations:
   - Empty output -> Normal, no pending file replacement or delete operations
   - Non-empty (has output) -> **Root cause**: Pending file operations exist (rename or delete), require restart to complete, **Severity**: Info
   - List contains .sys driver files -> Usually produced by Windows Update or driver installation, restart to complete driver replacement
   - Same batch of file operations still exists after multiple restarts -> **Root cause**: Pending file operations persistently cannot complete, possibly due to file lock or permission issues, **Severity**: Warning

2. Check CBS RebootPending:
   - No output -> Normal, component service has no pending reboot operations
   - RebootPending = 1 -> **Root cause**: Component service (CBS) has pending update operations, requires restart to complete installation, **Severity**: Warning

3. Check Windows Update RebootRequired:
   - No output -> Normal
   - RebootRequired = True -> **Root cause**: Windows Update has installed patches, requires restart to take effect, **Severity**: Info

4. Check CBS Sessions for PendingOperations > 0:
   - No output -> Normal
   - PendingOperations > 0 -> **Root cause**: Component service session has incomplete operations, requires restart to continue execution, **Severity**: Info

> If confirmed that Windows Update caused the pending reboot, see -> [system-update.md](references/online/system-update.md) (Windows Update diagnostics)

### Step 3: Boot Duration and Uptime Analysis

**Data Collection**:

> Collection target: System last boot time, uptime, boot performance diagnostic events (Event ID 100: boot duration and degradation)

- PowerShell script: [performance-lifecycle.ps1](references/online/scripts/performance-lifecycle.ps1) Section Step 3

**Analysis Approach**:

1. Check system uptime (UptimeDays):
   - Less than 1 day with no obvious operations activity -> May have experienced unexpected reboot -> Proceed to Step 4 to confirm cause with event logs
   - Normal uptime days -> Rule out frequent unexpected reboot issues

2. Check Event ID 100 (boot duration diagnostic event):
   - Extract boot duration from Message (unit ms):
     - < 30000 -> Normal
     - 30000~60000 -> Slow, needs attention
     - 60000~120000 -> **Root cause**: System boot duration too long, may have driver loading delay or service startup bottleneck, **Severity**: Warning
     - > 120000 -> **Root cause**: System boot severely slow, seriously affecting server availability, **Severity**: Critical
   - Extract boot degradation amount from Message (unit ms):
     - <= 0 -> Boot speed normal or better than baseline
     - > 0 and continuously increasing -> Boot performance continuously degrading, need to locate degradation source
   - Extract from Message whether boot was triggered by system event (e.g., Windows Update restart) -> If it is the first boot after patch installation, boot duration includes patch configuration time, which is a normal phenomenon

3. Check whether Event ID 100 is marked as critical performance degradation:
   - Marked as IsDegradation = true -> This boot is significantly slower than the system's recorded baseline boot time
   - Also marked as IsCritical = true -> Boot degradation has reached critical level
   - Consecutive multiple occurrences -> Problem persists, not occasional

> If boot duration is too long, prioritize -> Step 5 (Boot phase breakdown) to localize bottleneck phase
> If driver loading delay is found, see -> [device-driver.md](references/online/device-driver.md) (Device driver check)

### Step 4: Shutdown/Reboot Event Analysis

**Data Collection**:

> Collection target: System normal shutdown events (Event ID 6006), user/process initiated shutdown events (Event ID 1074), unexpected shutdown events (Event ID 6008), kernel power anomaly events (Event ID 41)

- PowerShell script: [performance-lifecycle.ps1](references/online/scripts/performance-lifecycle.ps1) Section Step 4

**Analysis Approach**:

1. Check Event ID 6006 (Event Log service stopped):
   - Records "Event log service was stopped" time = last record of system normal shutdown
   - No 6006 event but has 41 event -> System did not go through normal shutdown process, directly powered off or crashed

2. Check Event ID 1074 (user/process initiated shutdown):
   - Extract process name and Reason Code that initiated shutdown from Message
   - Normal operations restart (e.g., `C:\Windows\system32\wlms\wlms.exe` expected restart after hotpatch) -> Info
   - Unknown process initiated -> **Root cause**: Unexpected user or process triggered system reboot, **Severity**: Warning

3. Check Event ID 6008 (previous shutdown was unexpected):
   - Record time and frequency of each unexpected shutdown
   - If frequent and paired with Event ID 41 -> **Root cause**: System frequently shutting down unexpectedly, may be caused by BSOD, power loss, hardware failure, **Severity**: Critical

4. Check Event ID 41 (kernel power event):
   - BugcheckCode = 0: Not caused by BSOD (power loss, forced shutdown, or hardware failure)
   - BugcheckCode != 0: BSOD-caused restart -> See [system-crash.md](references/online/system-crash.md)
   - PowerButtonTimestamp = 0: System did not record power button press, ruling out manual operation

> If Event ID 41's BugcheckCode != 0, see -> [system-crash.md](references/online/system-crash.md) (BugCheck BSOD event)
> If frequent unexpected shutdowns accompanied by storage driver event anomalies, see -> [storage-hardware.md](references/online/storage-hardware.md) (Storage driver check)

### Step 5: Boot Phase Breakdown

**Data Collection**:

> Collection target: Boot phase duration breakdown (Event ID 101), including specific durations for kernel initialization, driver loading, device initialization, service startup, and other phases

- PowerShell script: [performance-lifecycle.ps1](references/online/scripts/performance-lifecycle.ps1) Section Step 5

**Analysis Approach**:

1. Check whether Event ID 101 (boot phase breakdown event) is available:
   - No output -> This log channel is not enabled or system has not yet recorded boot phase events (after first boot, need to wait for next restart to generate)
   - Has output -> Extract each phase duration from Message

2. Extract key phase durations from Message and analyze each one (all units in ms):

   | Phase | Description | Normal Range | Abnormal Threshold |
   |------|------|---------|--------|
   | Kernel Initialization (KernelInit) | From kernel loading to Smss.exe startup | < 5000 | > 10000 |
   | Driver Initialization (DriversInit) | Loading duration for all boot-type drivers | < 10000 | > 30000 |
   | Device Initialization (DevicesInit) | Plug and Play device enumeration and initialization | < 5000 | > 15000 |
   | Prefetch (PrefetchInit) | Boot file prefetch completion duration | < 10000 | > 30000 |
   | Session Initialization (SessionInit) | User session manager initialization | < 15000 | > 60000 |
   | Post-Login Initialization (PostBoot) | Post-login background service startup | < 30000 | > 60000 |

3. Per-phase diagnostic determination:
   - Driver initialization phase duration abnormally high -> **Root cause**: Slow-loading driver exists during boot, may be caused by driver initialization timeout or driver conflict, **Severity**: Warning
     - Combined with driver loading delay to localize specific driver -> See [device-driver.md](references/online/device-driver.md)
   - Device initialization phase duration abnormally high -> **Root cause**: Plug and Play device enumeration taking too long, may have non-existent or faulty devices causing prolonged wait, **Severity**: Warning
     - Check whether unconnected SAN storage or iSCSI targets cause device enumeration timeout -> See [storage-hardware.md](references/online/storage-hardware.md)
   - Prefetch phase duration abnormally high -> May be related to disk I/O performance, see -> [storage-disk.md](references/online/storage-disk.md)
   - Session initialization or post-login initialization phase duration abnormally high -> **Root cause**: Service startup phase taking too long, some service or startup program blocking the boot process, **Severity**: Warning
     - Combined with service startup timeout diagnosis: enumerate non-Microsoft service startup types, locate slow-starting services
       ```powershell
       Get-Service | Where-Object { $_.StartType -eq 'Automatic' -and $_.Status -ne 'Running' } | Select-Object Name, DisplayName, StartType, Status
       Get-CimInstance Win32_Service | Where-Object { $_.PathName -notmatch 'system32' } | Select-Object Name, StartMode, State, PathName
       ```
   - Multiple phases simultaneously abnormal -> May have system-level performance bottleneck (e.g., insufficient disk I/O, CPU resource contention)

4. Check whether boot phase events are marked as critical performance degradation:
   - Marked as IsDegradation = true -> All phases of this boot are overall slower than baseline
   - Consecutive multiple degradation records -> Boot performance continuously declining, not occasional

> If Event ID 101 is unavailable, can boot into Safe Mode to observe whether still slow, to rule out the influence of third-party drivers and services

### Step 6: Shutdown Duration Analysis

**Data Collection**:

> Collection target: Shutdown performance diagnostic events (Event ID 200), including total shutdown duration and degradation flags

- PowerShell script: [performance-lifecycle.ps1](references/online/scripts/performance-lifecycle.ps1) Section Step 6

**Analysis Approach**:

1. Check whether Event ID 200 (shutdown performance event) is available:
   - No output -> Possible reasons: System did not shut down normally (unexpected power loss), log channel not enabled, or log service stopped before shutdown
   - Has output -> Extract shutdown duration from Message

2. Extract shutdown duration from Message (unit ms):
   - < 5000 -> Normal, shutdown process smooth
   - 5000~30000 -> Slow, may have individual services or applications responding slowly to shutdown signal
   - 30000~120000 -> **Root cause**: Shutdown duration significantly too long, services or processes hindering the shutdown process exist, **Severity**: Warning
   - > 120000 -> **Root cause**: Shutdown severely slow, system may have forcibly terminated services or processes, **Severity**: Critical

3. Check shutdown degradation flags:
   - Marked as IsDegradation = true -> This shutdown is significantly slower than the system's recorded baseline shutdown time
   - Also marked as IsCritical = true -> Shutdown degradation has reached critical level
   - Consecutive multiple degradations -> **Root cause**: Shutdown performance continuously degrading, need to locate services or applications hindering shutdown, **Severity**: Warning

4. Correlation analysis of shutdown duration and abnormal shutdown events:
   - Shutdown duration abnormal and Event ID 6008 frequently appears -> System was forcibly powered off due to shutdown timeout, may have caused file system damage
   - Shutdown duration abnormal but no subsequent Event ID 6008 -> Shutdown process eventually completed, but taking too long affects operations efficiency

5. Common causes of slow shutdown investigation directions:
   - Shutdown timeout configuration improper (WaitToKillServiceTimeout / WaitToKillAppTimeout too large) -> See Step 1
   - Pending Windows Update operations exist -> See Step 2
   - Third-party services refusing to respond to shutdown signal: enumerate running services and locate abnormal processes
   - Group policy shutdown script execution timeout -> See [system-gpo.md](references/online/system-gpo.md)
   - User profile unloading slow (User Profile Service) -> See [identity-user-profiles.md](references/online/identity-user-profiles.md)

> If Event ID 200 is unavailable but user clearly reports slow shutdown, prioritize investigation -> Step 1 (Shutdown timeout config)
> If shutdown duration abnormal and accompanied by disk-related events, see -> [storage-disk.md](references/online/storage-disk.md)

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Event ID 41's BugcheckCode != 0 (BSOD-caused restart) | -> [system-crash.md](references/online/system-crash.md) |
| Conditional jump | Frequent unexpected shutdowns accompanied by storage driver event anomalies | -> [storage-hardware.md](references/online/storage-hardware.md) |
| Conditional jump | Windows Update caused pending reboot operations | -> [system-update.md](references/online/system-update.md) |
| Conditional jump | GPO shutdown script blocking shutdown process | -> [system-gpo.md](references/online/system-gpo.md) |
| Conditional jump | Driver loading delay in boot duration | -> [device-driver.md](references/online/device-driver.md) |
| Conditional jump | Shutdown duration abnormal and continuously degrading | -> Enumerate non-Microsoft services to locate blocking items (`Get-Service` \| `Where-Object StartType -eq Automatic`) |
| Conditional jump | Shutdown duration abnormal and involving user profile unloading | -> [identity-user-profiles.md](references/online/identity-user-profiles.md) |
| Chained successor | This file did not confirm root cause | -> [desktop-shell.md](references/online/desktop-shell.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [performance-lifecycle.md](references/online/fixes/performance-lifecycle.md).
