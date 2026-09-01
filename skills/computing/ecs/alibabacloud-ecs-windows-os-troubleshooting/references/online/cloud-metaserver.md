# Cloud MetaServer Diagnostics

## Function Description

Diagnose Windows cloud platform metadata service reachability (100.100.100.200), whether firewall blocks the metadata service, NTP time server assignment, KMS activation server reachability, WSUS update server reachability, and hostname and metadata consistency. Covers 6 diagnostic steps.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Phenomenon | Recommended Steps |
|-------------|---------------|
| Cloud Assistant not working, automated operations failure, metadata acquisition failure | Step 1 (Firewall blocking check) -> Step 2 (Metadata service reachability) |
| Inaccurate system time, time drift causing authentication failure | Step 2 (Metadata service reachability) -> Step 3 (NTP server assignment) |
| Windows activation failure, activation error | Step 2 (Metadata service reachability) -> Step 4 (KMS server reachability) |
| Cannot install updates via WSUS, update check failure | Step 2 (Metadata service reachability) -> Step 5 (WSUS server reachability) |
| Hostname in monitoring alerts inconsistent with console, hostname not taking effect after setting | Step 6 (Hostname consistency) |
| Cloud platform services comprehensively abnormal | Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5 -> Step 6 |

## Diagnostic Steps

### Step 1: Firewall Blocking Metadata Service Check

**Data Collection**:

> Collection target: Whether Windows Firewall has block rules targeting metadata service address 100.100.100.200

**Analysis Approach**:

- PowerShell script: [cloud-metaserver.ps1](references/online/scripts/cloud-metaserver.ps1) Section Step 1

1. Check whether firewall rules blocking the metadata service address exist:
   - No output -> Normal, firewall is not blocking the metadata service
   - Block rules exist (output contains Block rules for 100.100.100.200) -> **Root cause**: Firewall rules blocking metadata service address 100.100.100.200, causing metadata service unreachable, **severity**: Warning

> If you need to further check the complete firewall configuration, see -> [networking-firewall.md](references/online/networking-firewall.md)

### Step 2: Metadata Service Reachability

**Data Collection**:

> Collection target: Network connectivity and HTTP response status of metadata service endpoint 100.100.100.200

**Analysis Approach**:

- PowerShell script: [cloud-metaserver.ps1](references/online/scripts/cloud-metaserver.ps1) Section Step 2

1. Check TCP connection test result:
   - TcpTestSucceeded is True -> Network layer reachable
   - TcpTestSucceeded is False -> **Root cause**: Metadata service 100.100.100.200 unreachable, all cloud platform services depending on metadata (NTP, KMS, WSUS) will fail, **severity**: Critical

2. Check HTTP response:
   - Returns StatusCode 200 and contains instance ID -> Metadata service normal
   - TCP reachable but HTTP request failed -> First classify by error type below, then determine root cause

3. **Error type classification (network unreachable vs hardened mode/access control blocking)**: When collection errors occur, MUST first distinguish the error type; the two categories of root causes are completely different:

   | Error Characteristics | Determination | Direction |
   | --- | --- | --- |
   | Connection timeout, unable to connect, `Test-NetConnection` TcpTestSucceeded=False, ping failure | **Network layer unreachable** | Root cause: Metadata service unreachable (Critical); diagnose routing (networking-tcpip.md), firewall (Step 1), security groups |
   | TCP reachable but HTTP returns 403 Forbidden / 401 / Access Denied | **Hardened mode or access control blocking** | Root cause: Metadata hardened mode or access control blocking (MetaServerHardenedModeBlocked, Warning); see determination rules below |

   **Hardened mode determination rules**:
   - Network layer reachable (TcpTestSucceeded=True) but metadata HTTP requests consistently return 403/401/access denied -> Determine that the instance has metadata hardened mode enabled or access control policies configured; this is expected protective behavior, not a fault
   - At this point, all collection depending on metadata (NTP/KMS/WSUS assignment, hostname comparison, etc.) will report permission errors; **MUST NOT** report individual "service abnormal" root causes based on these; should merge into a single root cause MetaServerHardenedModeBlocked
   - Verification: Confirm with the user whether the instance has metadata hardened mode/access control enabled; or compare whether different metadata paths on the same instance uniformly return 403 (hardened mode applies to all paths)
   - Conclusion note: Under hardened mode, metadata must be accessed per platform-specified methods (e.g., specified request headers/credentials), or the user adjusts instance metadata access configuration in the console; the OS internally cannot and should not bypass this

> If the metadata service is completely unreachable, first confirm firewall rules (Step 1) and network routing configuration. See -> [networking-tcpip.md](references/online/networking-tcpip.md) (check routing for 100.100.100.200 in the routing table)

### Step 3: NTP Server Assignment

**Data Collection**:

> Collection target: NTP server address obtained from metadata service, NTP server configured by local Windows Time service

**Analysis Approach**:

- PowerShell script: [cloud-metaserver.ps1](references/online/scripts/cloud-metaserver.ps1) Section Step 3

1. Check whether NTP server is assigned in metadata:
   - Returns a valid NTP server address (e.g., ntp.cloud.aliyuncs.com) -> Normal
   - Returns empty or request failed -> **Root cause**: Metadata service has not assigned an NTP server, system time may not auto-sync, **severity**: Warning

2. Check local NTP configuration:
   - NtpServer contains a valid server address -> Normal
   - NtpServer is empty -> **Root cause**: No NTP server configured locally, system time may drift causing Kerberos authentication, certificate validation, and other time-dependent service abnormalities, **severity**: Warning
   - Check the meaning of Type value:
     - `NTP`: Uses external time source configured in NtpServer (standalone server or workgroup scenario)
     - `NT5DS`: Syncs time from domain hierarchy (default for domain members)
     - `NoSync`: Does not sync with any time source
     - `AllSync`: Uses both domain hierarchy and manually configured time source
   - If Type is NoSync -> Time sync is explicitly disabled and needs to be modified

3. Check Windows Time service status:
   - Service is Running -> Normal
   - Service not running and StartType is Disabled -> Time service disabled and will not run, time sync cannot work, should be fixed together with NTP configuration
   - Service not running and StartType is Manual or Automatic -> Service can start on demand or at boot; Stopped state when no time sync is in progress is not abnormal in itself

4. Check w32tm /query /status output:
   - Source shows a valid time source -> Normal
   - Source shows "Local CMOS Clock" or "Free-running System Clock" -> System is using local clock instead of network time source, time may drift
   - Last Successful Sync Time is too far from current time (over 24 hours) -> Time sync may have issues

### Step 4: KMS Activation Server Reachability

**Data Collection**:

> Collection target: KMS activation server address and network connectivity (port 1688)

**Analysis Approach**:

- PowerShell script: [cloud-metaserver.ps1](references/online/scripts/cloud-metaserver.ps1) Section Step 4

1. Check whether KMS server address is configured:
   - KMS server address exists in metadata or registry -> Normal
   - Both empty -> **Root cause**: KMS activation server not configured, Windows cannot complete auto-activation, **severity**: Warning

2. Check `cscript //Nologo C:\windows\system32\slmgr.vbs /dli` license status:
   - License Status: Licensed -> Activation normal
   - License Status: Notification -> Activation grace period expired, needs activation ASAP
   - License Status: Initial grace period -> In initial grace period, not yet activated
   - KMS machine name is empty in output -> KMS server not configured
   - Remaining Windows rearm count is 0 in output -> Reset activation count exhausted

3. Check KMS server connectivity (TCP port 1688):
   - TcpTestSucceeded is True -> KMS server reachable
   - TcpTestSucceeded is False -> **Root cause**: KMS activation server unreachable (port 1688), Windows activation will fail, **severity**: Warning

> If you suspect the firewall is blocking KMS communication, see -> [networking-firewall.md](references/online/networking-firewall.md) (check outbound TCP port 1688 rules)
> If you need to deeply diagnose Windows activation issues, see -> [system-activation.md](references/online/system-activation.md)

### Step 5: WSUS Update Server Reachability

**Data Collection**:

> Collection target: WSUS update server address and HTTP connectivity

**Analysis Approach**:

- PowerShell script: [cloud-metaserver.ps1](references/online/scripts/cloud-metaserver.ps1) Section Step 5

1. Check whether WSUS server address is configured:
   - WSUS server address exists in metadata or registry -> Normal
   - Both empty -> System will use Microsoft Update online (not an error, but if the user expects intranet updates, configuration is needed)

2. Check UseWUServer registry value:
   - UseWUServer = 1 -> WSUS configuration is active, client will use the server specified by WUServer
   - UseWUServer = 0 or not configured -> Even if WUServer is filled in, the client will still connect to Microsoft Update instead of the WSUS server
   - If WUServer is configured but UseWUServer != 1 -> **Root cause**: WSUS server address configured but not enabled, need to set UseWUServer to 1 to take effect, **severity**: Warning

3. Check WSUS server connectivity:
   - TcpTestSucceeded is True -> WSUS server reachable
   - TcpTestSucceeded is False -> **Root cause**: WSUS update server unreachable, Windows Update cannot get updates from intranet server, **severity**: Warning

> If you need to deeply diagnose Windows Update issues, see -> [system-update.md](references/online/system-update.md)

### Step 6: Hostname Consistency

**Data Collection**:

> Collection target: System's current hostname and hostname recorded in metadata service

**Analysis Approach**:

- PowerShell script: [cloud-metaserver.ps1](references/online/scripts/cloud-metaserver.ps1) Section Step 6

1. Compare system hostname with metadata hostname:
   - Both match (Match is True) -> Normal
   - Both do not match (Match is False) -> **Root cause**: System hostname inconsistent with hostname recorded in metadata service, may cause monitoring alert and instance identification confusion, **severity**: Warning

2. If metadata acquisition fails:
   - Indicates metadata service is unreachable, return to Step 2 to check metadata service reachability

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Firewall blocking metadata service address | -> [networking-firewall.md](references/online/networking-firewall.md) |
| Conditional jump | Metadata unreachable and routing abnormal | -> [networking-tcpip.md](references/online/networking-tcpip.md) |
| Conditional jump | KMS port blocked by firewall | -> [networking-firewall.md](references/online/networking-firewall.md) (check outbound TCP port 1688 rules) |
| Conditional jump | In-depth KMS activation diagnosis | -> [system-activation.md](references/online/system-activation.md) |
| Conditional jump | In-depth WSUS update diagnosis | -> [system-update.md](references/online/system-update.md) |
| Chain successor | No root cause confirmed in this file | -> [networking-firewall.md](references/online/networking-firewall.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [cloud-metaserver.md](references/online/fixes/cloud-metaserver.md).
