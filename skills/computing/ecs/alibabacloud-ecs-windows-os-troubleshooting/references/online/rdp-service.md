# RDP Service Diagnostics

## Feature Description

Diagnoses Remote Desktop Service (TermService) and its related component issues. Covers TermService service status and dependent services, RDP listener (WinStation) configuration and port listening, RDP enable status and Group Policy, UMBus device enumeration, totaling 4 diagnostic steps.

**Input**: User problem description (required), RDP connection error message (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

**Platform-side precheck (remote channel only)**: for "connection timeout / unreachable from outside" symptoms, the workflow runs platform-side triage before this file's steps (public entry point, security-group ingress rule for 3389 -- see [platform-evidence.md](references/online/platform-evidence.md) Section L2). If that triage concludes a platform-side root cause, this file's steps are skipped; do not duplicate those platform checks inside the steps below.

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Symptom | Recommended Steps |
|-------------|---------------|
| RDP connection directly rejected | Step 1 (TermService) -> Step 2 (WinStation and Port) |
| Prompt "This computer can't connect" | Step 2 (WinStation and Port) -> Step 3 (Enable Status and Group Policy) |
| RDP port occupied | Step 2 (WinStation and Port) -> Step 1 (Service Status) |
| RDP connection timeout | Step 2 (WinStation and Port) -> [networking-firewall.md](references/online/networking-firewall.md) (check inbound TCP port rules) |
| Prompt "Remote Desktop has been disabled" or Group Policy disables remote desktop | Step 3 (Enable Status and Group Policy) |
| Multiple users prompted about exceeding maximum connections | Step 2 (WinStation and Port, check MaxInstanceCount) -> Step 3 (Group Policy MaxInstanceCount) |
| RDP abnormal after installing third-party remote software | Step 2 (WinStation and Port, check third-party Station) |
| mstsc remote connection crashes (disconnects immediately after connecting) | Step 2 (WinStation and Port, focus on third-party WinStation and RDP-Tcp port/configuration conflict) |
| Device mapping failure after RDP connection | Step 4 (UMBus Device) |

## Diagnostic Steps

### Step 1: TermService Status Check

**Data Collection**: Get running status and startup type of TermService and its dependent services

- PowerShell script: [rdp-service.ps1](references/online/scripts/rdp-service.ps1) Section Step 1

**Analysis**:

1. Check TermService status:
   - Normal: Service is running
   - Abnormal: Service stopped -> **Root cause**: TermService stopped, remote desktop cannot connect, **Severity**: Critical
   - Abnormal: Service startup type is Disabled -> **Root cause**: TermService disabled, **Severity**: Critical

2. Check dependent service status:
   - Normal: All dependent services running
   - Abnormal: Dependent service not running -> **Root cause**: TermService dependent service abnormal (e.g., RpcSs), **Severity**: Critical

### Step 2: RDP Listener (WinStation) and Port Check

> WARNING **MUST**: You must iterate **ALL** sub-keys under `..\WinStations\` (excluding `Console`). **DO NOT** stop at `RDP-Tcp` or assume a single listener exists. Multi-listener configurations (e.g., `RDP-Tcp-3389`) are common.

**Data Collection**: Enumerate all WinStation registry configurations, check listening status and occupying process for each port, check Session Listener status and WinStation registry ACL, collect TerminalServices session layer key event logs

> WinStation registry ACL is obtained via PowerShell `Get-Acl`

- PowerShell script: [rdp-service.ps1](references/online/scripts/rdp-service.ps1) Section Step 2

**Analysis**:

1. Check whether any WinStation exists:
   - Normal: At least one WinStation exists (usually RDP-Tcp)
   - Abnormal: No WinStation -> **Root cause**: RDP listener configuration missing, **Severity**: Critical

2. Check whether RDP is enabled (check fEnableWinStation for each WinStation):
   - Normal: fEnableWinStation = 1
   - Abnormal: fEnableWinStation = 0 or not configured -> **Root cause**: WinStation disabled or enable flag not configured (annotate StationName and current value), listener not effective, **Severity**: Critical

3. Check Session Listener status (qwinsta output):
   - Normal: rdp-tcp session with State = Listen exists
   - Abnormal: No session in Listen state -> **Root cause**: RDP listener not running, cannot accept new RDP connections, **Severity**: Critical

4. For each WinStation, check consistency between configured port and actual listening:
   - Normal: Configured port has active TCP listening, and ServiceName = TermService
   - Abnormal: Configured port has no listening -> **Root cause**: RDP port not being listened on (annotate StationName and PortNumber), **Severity**: Critical
   - Abnormal: Configured port occupied by non-TermService process -> **Root cause**: RDP port occupied by another process (annotate StationName, PortNumber and ServiceName), **Severity**: Critical
   - Abnormal: All WinStations not configured with 3389 but 3389 is listening -> Possible residual listener or configuration inconsistency, **Severity**: Warning

5. Global check: whether any WinStation is configured with standard port 3389:
   - Normal: At least one WinStation has PortNumber = 3389
   - Abnormal: All WinStations use non-standard ports -> **Root cause**: RDP listening port changed to non-standard port, clients need to specify port to connect, **Severity**: Warning

6. For each WinStation, check whether WdName is a Microsoft standard component:
   - Normal: WdName contains "Microsoft" (e.g., "Microsoft RDP") or WdName is "RDPWD"
   - Abnormal: WdName does not contain "Microsoft" and is not "RDPWD" -> **Root cause**: Third-party remote component (annotate StationName and WdName), may conflict with standard RDP, **Severity**: Warning

7. For each WinStation, check MaxInstanceCount:
   - Normal: MaxInstanceCount not set or value is large (e.g., 0xFFFFFFFF)
   - Abnormal: MaxInstanceCount value too low (e.g., 1 or 2) -> **Root cause**: Concurrent connection count limited (annotate StationName and current value), may prevent connections in multi-user scenarios, **Severity**: Warning

8. For each WinStation, check registry ACL:
   - Normal: BUILTIN\Users has Read permission (ReadKey)
   - Abnormal: BUILTIN\Users has no Read permission -> **Root cause**: WinStation registry read permission abnormal (annotate StationName), users cannot query RDP configuration, **Severity**: Warning

9. Check third-party WinStation and RDP-Tcp port conflict (mstsc crash scenario):
   - Abnormal: Multiple non-Console WinStations configured with the same PortNumber (e.g., third-party Station and RDP-Tcp both on 3389) -> **Root cause**: Third-party WinStation and RDP-Tcp port conflict causing crash (annotate conflicting StationName and port), mstsc session initialization fails and disconnects immediately, **Severity**: Critical
   - Abnormal: RDP-Tcp WdName overridden by third-party driver (WdName is not "RDPWD" and not "Microsoft" prefix), and user reports mstsc crash -> **Root cause**: Third-party driver overrides RDP-Tcp WdName causing crash (annotate current WdName), mstsc cannot complete session negotiation with non-standard protocol driver, **Severity**: Warning

> If the port is listening normally but still cannot connect, the firewall may be blocking, see -> [networking-firewall.md](references/online/networking-firewall.md) (check inbound TCP port rules)

10. Check TerminalServices session layer event logs (Event ID 1035/1036/1042/1103):
    - Normal: No error events with the above IDs in the logs
    - Abnormal: Event 1035/1036 (connection request rejected), Event 1042 (layer failed), Event 1103 (connection terminated), and associated with the corresponding WinStation or port conflict root cause, **Severity**: Warning
    - Note: Event 261 is an information-level "Listener has received a connection", indicating the listener is working normally, **must not** be determined as a listener failure; can only be used as corroborating evidence that "the listener is receiving connections"

### Step 3: RDP Enable Status and Group Policy Check

**Data Collection**: Check local registry configuration and Group Policy configuration for RDP enable status

- PowerShell script: [rdp-service.ps1](references/online/scripts/rdp-service.ps1) Section Step 3

**Analysis**:

1. Check whether RDP is disabled via local registry:
   - Normal: fDenyTSConnections = 0 (Remote Desktop enabled)
   - Abnormal: fDenyTSConnections = 1 -> **Root cause**: Remote Desktop disabled (via registry), **Severity**: Critical

2. Check whether Group Policy overrides local configuration:
   - Normal: No entry at Group Policy path (no Group Policy restriction configured) or fDenyTSConnections = 0
   - Abnormal: Group Policy fDenyTSConnections = 1 -> **Root cause**: Group Policy disables remote desktop connections, **Severity**: Critical
   - Abnormal: Group Policy conflicts with local configuration (Group Policy disables but local enables) -> **Root cause**: Group Policy overrides local configuration, RDP is actually disabled, **Severity**: Critical

3. Check whether Group Policy overrides RDP security configuration:
   - SecurityLayer set by policy -> **Root cause**: Group Policy overrides RDP security layer configuration (annotate policy value: 0=RDP Security, 1=Negotiate, 2=TLS), may be incompatible with client, **Severity**: Warning
   - UserAuthentication set by policy -> **Root cause**: Group Policy enforces NLA (Network Level Authentication) configuration (annotate policy value: 0=Not required, 1=Required), legacy clients may be unable to connect, **Severity**: Warning
   - MaxInstanceCount set by policy -> **Root cause**: Group Policy limits maximum concurrent connections (annotate policy value), may prevent connections in multi-user scenarios, **Severity**: Warning
   - fDisableCdm / fDisableClip set by policy -> Feature limitation notice (not a connectivity issue), **Severity**: Info

### Step 4: UMBus Device Enumeration Check

**Data Collection**: Check UMBus device and remote desktop related device status

- PowerShell script: [rdp-service.ps1](references/online/scripts/rdp-service.ps1) Section Step 4

**Analysis**:

1. Check UMBus device status:
   - Normal: Device status normal
   - Abnormal: Device status abnormal -> **Root cause**: UMBus device enumeration abnormal, device mapping may fail after RDP connection, **Severity**: Warning

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Parameterized reference | Firewall blocking RDP port | -> [networking-firewall.md](references/online/networking-firewall.md) (check inbound TCP port 3389 rules) |
| Conditional jump | Step 1 TermService dependent service abnormal | -> [networking-tcpip.md](references/online/networking-tcpip.md) (if dependent on network services) |
| Chain successor | No root cause confirmed in this file, user reports RDP issue | -> [rdp-auth.md](references/online/rdp-auth.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [rdp-service.md](references/online/fixes/rdp-service.md).


## Gotchas

- **Missing non-default WinStations**: Administrators often create additional WinStations (e.g., `RDP-Tcp-3389`) for multi-port RDP listening. Diagnostics must fully traverse `Get-ChildItem` results, not just check `RDP-Tcp`.
- **Multi-listener port conflicts**: When multiple WinStations are configured with the same port, only one can actually bind and listen, the other silently fails; must verify `IsListening` status one by one.
- **Script execution integrity**: The data collection script outputs `Total WinStations found` at the end; if the count is 0 or 1, be alert to possible omissions or configuration loss.
- **WinStation registry ACL retrieval**: Use PowerShell `Get-Acl` to directly obtain the ACL of the WinStations key and its sub-keys
