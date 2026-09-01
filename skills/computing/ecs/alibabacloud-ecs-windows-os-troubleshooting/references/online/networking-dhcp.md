# DHCP Diagnostics

## Function Description

Diagnoses Windows DHCP client service and automatic IP address acquisition issues. Covers DHCP Client service status, network adapter DHCP enable status, lease acquisition and renewal, APIPA address detection, DHCP client event logs, DHCP server connectivity verification, and other scenarios.

**Input**: User problem description (required), network adapter name or IP address (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Cannot obtain IP address / All IPs lost | Step 1 (DHCP service) -> Step 2 (Network adapter DHCP config) -> Step 3 (Lease status) |
| 169.254.x.x (APIPA) address | Step 3 (Lease status) -> Step 4 (DHCP event log) -> Step 6 (DHCP server connectivity) |
| IP address frequently changes / Lease renewal failure | Step 3 (Lease status) -> Step 4 (DHCP event log) |
| Some network adapters cannot obtain IP | Step 2 (Network adapter DHCP config) -> Step 5 (Network adapter driver and link status) |
| Cannot access internet after obtaining IP via DHCP | Step 3 (Lease status) -> Step 6 (DHCP server connectivity) |
| Firewall blocking DHCP traffic | -> [networking-firewall.md](references/online/networking-firewall.md) (Check inbound UDP 67/68 port rules) |

## Diagnostic Steps

### Step 1: DHCP Client Service Status Check

**Data Collection**:

> Collection target: Obtain the running status and startup type of the DHCP Client service (Dhcp)

- PowerShell script: [networking-dhcp.ps1](references/online/scripts/networking-dhcp.ps1) Section Step 1

**Analysis Approach**:

1. Check DHCP Client service status:
   - Normal: Service is running
   - Abnormal: Service not running -> **Root cause**: DHCP Client service not running, cannot automatically obtain IP address, **Severity**: Critical
   - Abnormal: Service startup type is Disabled -> **Root cause**: DHCP Client service disabled, **Severity**: Critical

### Step 2: Network Adapter DHCP Enable Status Check

**Data Collection**:

> Collection target: Obtain DHCP enable status and IP configuration method for all active network adapters

- PowerShell script: [networking-dhcp.ps1](references/online/scripts/networking-dhcp.ps1) Section Step 2

**Analysis Approach**:

1. Check DHCP enable status for each network adapter:
   - Normal: DHCP is Enabled
   - Abnormal: DHCP is Disabled -> **Root cause**: Network adapter has DHCP disabled, using static IP configuration, **Severity**: Warning

2. Check if all active network adapters have DHCP disabled:
   - Abnormal: All active network adapters are static configured and user expects to use DHCP -> **Root cause**: DHCP not enabled on any network adapter, **Severity**: Critical

### Step 3: DHCP Lease Status Check

**Data Collection**:

> Collection target: Obtain current IP address allocation information, including DHCP server address, lease acquisition time, lease expiration time

- PowerShell script: [networking-dhcp.ps1](references/online/scripts/networking-dhcp.ps1) Section Step 3

**Analysis Approach**:

1. Check for APIPA address (169.254.x.x):
   - Normal: No 169.254.x.x address
   - Abnormal: 169.254.x.x address exists (SuffixOrigin is Link) -> **Root cause**: DHCP acquisition failed, system assigned APIPA automatic private address, **Severity**: Critical

2. Check DHCP lease information:
   - Normal: DHCPServer has valid address, lease time within validity period
   - Abnormal: DHCPServer is empty or invalid -> **Root cause**: Failed to obtain lease from DHCP server, **Severity**: Critical
   - Abnormal: Lease expired (DHCPLeaseExpires earlier than current time) -> **Root cause**: DHCP lease expired and renewal failed, **Severity**: Warning

3. Check for missing default gateway:
   - Normal: DefaultIPGateway has valid gateway address
   - Abnormal: DHCP assigned IP but no gateway assigned -> **Root cause**: DHCP server did not deliver default gateway, **Severity**: Warning

If APIPA address appears and DHCP service is normal, the firewall may be blocking DHCP traffic, see -> [networking-firewall.md](references/online/networking-firewall.md) (Check inbound UDP 67/68 port rules)

### Step 4: DHCP Client Event Log Check

**Data Collection**:

> Collection target: Obtain DHCP client management log events, focusing on Event ID 1001 (lease acquisition failure), 1002 (lease renewal failure), 1003 (DHCP service error)

- PowerShell script: [networking-dhcp.ps1](references/online/scripts/networking-dhcp.ps1) Section Step 4

**Analysis Approach**:

1. Check Event ID 1001 events:
   - Meaning: Your computer was not assigned an address from the network (by the DHCP Server)
   - Abnormal: Frequent occurrences -> **Root cause**: DHCP server not responding to address requests, may be server unreachable or address pool exhausted, **Severity**: Critical

2. Check Event ID 1002 events:
   - Meaning: The IP address lease for the Network Card has been denied by the DHCP server
   - Abnormal: Occurs -> **Root cause**: DHCP server rejected lease renewal request, **Severity**: Warning

3. Check Event ID 1003 events:
   - Meaning: DHCP service encountered an error
   - Abnormal: Occurs -> **Root cause**: DHCP client service encountered internal error, **Severity**: Warning

4. Check event time patterns:
   - Abnormal: Large number of failure events in short time -> May be network infrastructure problem
   - Abnormal: Only occurs during specific time periods -> May be intermittent network failure

### Step 5: Network Adapter Driver and Link Status Check

**Data Collection**:

> Collection target: Obtain network adapter connection status and driver information, rule out physical layer issues

- PowerShell script: [networking-dhcp.ps1](references/online/scripts/networking-dhcp.ps1) Section Step 5

**Analysis Approach**:

1. Check network adapter connection status:
   - Normal: Status is Up, MediaConnectionState is Connected
   - Abnormal: Status is Disabled -> **Root cause**: Network adapter disabled, cannot perform DHCP communication, **Severity**: Critical
   - Abnormal: MediaConnectionState is Disconnected -> **Root cause**: Network adapter physical link disconnected, **Severity**: Critical

If network adapter driver is abnormal, see -> [device-driver.md](references/online/device-driver.md)

### Step 6: DHCP Server Connectivity Check

**Data Collection**:

> Collection target: Check network connectivity to DHCP server, attempt to re-acquire DHCP lease

- PowerShell script: [networking-dhcp.ps1](references/online/scripts/networking-dhcp.ps1) Section Step 6
- NetworkPing target must first be obtained from NetAdapterConfiguration's DHCPServer address before filling in

**Analysis Approach**:

1. Check DHCP server address:
   - Normal: Has valid DHCP server address
   - Abnormal: No DHCP server record -> **Root cause**: Never successfully obtained DHCP lease, **Severity**: Critical

2. Check DHCP server connectivity:
   - Normal: Can ping DHCP server
   - Abnormal: Cannot ping -> **Root cause**: DHCP server unreachable, may be network link issue or server failure, **Severity**: Critical

3. Check DHCP-related information in ipconfig /all output:
   - Confirm Autoconfiguration Enabled status
   - Confirm DHCP Enabled status
   - Check Lease Obtained and Lease Expires time

If DHCP server is reachable but cannot obtain IP, may be server-side issue (address pool exhausted, MAC filtering, etc.), need to contact network administrator.

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 2 network adapter is static configured and IP config abnormal | -> [networking-tcpip.md](references/online/networking-tcpip.md) (Check static IP config) |
| Conditional jump | Step 5 network adapter driver abnormal | -> [device-driver.md](references/online/device-driver.md) (Check driver status) |
| Parameterized reference | Step 3 APIPA address and DHCP service normal, suspect firewall blocking | -> [networking-firewall.md](references/online/networking-firewall.md) (Check inbound UDP 67/68 port rules) |
| Chained successor | This file did not confirm root cause | -> [networking-tcpip.md](references/online/networking-tcpip.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [networking-dhcp.md](references/online/fixes/networking-dhcp.md).
