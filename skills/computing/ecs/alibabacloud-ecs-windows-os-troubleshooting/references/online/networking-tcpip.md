# Network TCP/IP Diagnostics

## Function Description

Diagnoses Windows network adapter and TCP/IP protocol stack configuration issues. Covers network adapter status, IP configuration, routing table, protocol binding, proxy configuration, end-to-end connectivity, and 11 known problem items.

**Input**: User problem description (required), error code/event ID/screenshot (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

**Platform-side precheck (remote channel only)**: for "public targets unreachable" symptoms, the workflow runs platform-side triage before this file's steps (public IP/EIP presence, outbound bandwidth, security-group rules -- see [platform-evidence.md](references/online/platform-evidence.md) Section L2). If that triage concludes a platform-side root cause, this file's steps are skipped; do not duplicate those platform checks inside the steps below.

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Network completely unreachable | Step 6 (raw ping output, read error text first) -> trace back Step 1-5 -> [networking-firewall.md](references/online/networking-firewall.md) Steps 3-5 + Step 7 (WFP) -- **mandatory, not conditional on "config all normal"** |
| Internal-to-public network failure but inbound reachable (outbound ping/TCP fails, RDP/SSH inbound normal) | Step 4 (includes multiple default route check + forced source IP comparison ping) -> Step 3 (includes SkipAsSource check) -> Step 6 (connectivity fallback) |
| Any ping / connectivity failure | FIRST read the per-reply error text from Step 6 raw output (never summarize it away to "100% loss"): "General failure" -> quick Step 1-3 sanity glance -> [networking-firewall.md Step 7](references/online/networking-firewall.md) immediately (highest priority); "Request timed out" -> Step 4 -> firewall Step 7; "Destination host unreachable" -> Step 4; "Transmission failed" -> Step 3/4 (match each against its OS-language localized equivalent) |
| Network icon abnormal / occasional disconnection | Step 1 (Network adapter status) -> Step 2 (Protocol binding) |
| Cannot obtain IP address | Step 3 (IP config) -> Step 4 (Default route) -> If APIPA, jump to [networking-dhcp.md](references/online/networking-dhcp.md) |
| Some websites inaccessible | Step 5 (DNS) -> Step 8 (Proxy) |
| Network slow / High latency | Step 6 (Connectivity test latency) |
| Application cannot connect to network but ping normal | Step 8 (Proxy config) -> [networking-firewall.md Step 7](references/online/networking-firewall.md) (WFP packet drop localization) |
| Application cannot bind port / Error port in use | Step 7 (TCP port range) |
| Large number of concurrent connection failures | Step 7 (TCP port range) -> Step 6 (Connectivity) |

## Diagnostic Steps

### Step 1: Network Adapter Status Check

**Data Collection**:

> Collection target: Obtain basic status information for all network adapters, including name, description, connection status, MAC address, and link speed

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 1

**Analysis Approach**:

1. Check for network adapters:
   - Normal: At least one adapter exists
   - Abnormal: No adapters -> **Root cause**: No network adapter, **Severity**: Critical

2. Check adapter enable status:
   - Normal: Adapter is in enabled or started state
   - Abnormal: Adapter disabled -> **Root cause**: Network adapter disabled, **Severity**: Warning
   - Abnormal: Adapter status unknown -> **Root cause**: Network adapter status unknown, **Severity**: Warning

3. Check adapter connection status:
   - Normal: Adapter is connected
   - Abnormal: Adapter disconnected or underlying link down -> **Root cause**: Network adapter not connected or underlying link disconnected, **Severity**: Critical

4. Check link speed:
   - Normal: Link speed greater than 0
   - Abnormal: Link speed is 0 -> **Root cause**: Network adapter link not established, **Severity**: Critical
> If a network adapter status is Down, may need to check driver in Device Manager -> See [device-driver.md](references/online/device-driver.md)

### Step 2: Network Protocol Binding Check

**Data Collection**:

> Collection target: Obtain protocol components bound to all network adapters, used to check TCP/IP protocol binding status and third-party protocols

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 2

**Analysis Approach**:

1. Check whether TCP/IP protocol is bound to active network adapters:
   - Normal: Active network adapter has TCP/IP protocol bound
   - Abnormal: TCP/IP protocol not bound -> **Root cause**: TCP/IP protocol not bound to network adapter, **Severity**: Critical

2. Check for third-party protocol bindings:
   - Normal: Only Microsoft standard protocols bound
   - Abnormal: Non-Microsoft protocols exist -> **Root cause**: Third-party network protocol binding detected, may cause network access anomalies, **Severity**: Warning
   - Common third-party protocols: Antivirus network filter drivers, VPN client protocols, virtualization network protocols, traffic monitoring tools, etc.

### Step 3: IP Address Configuration Check

**Data Collection**:

> Collection target: Obtain all IPv4 address configurations, including IP address, prefix length, address state, allocation source, and whether participating in source address selection (SkipAsSource)

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 3

**Analysis Approach**:

1. Check for IPv4 address:
   - Normal: At least one IPv4 address in preferred state
   - Abnormal: No IPv4 address -> **Root cause**: No IPv4 address assigned, **Severity**: Critical

2. Check for APIPA address (169.254.x.x):
   - Normal: Not in 169.254.x.x range
   - Abnormal: IP address starts with 169.254 -> **Root cause**: DHCP acquisition failed, using automatic private address, **Severity**: Warning

3. Check address state:
   - Normal: Address state is preferred
   - Abnormal: Address state is tentative or deprecated -> **Root cause**: IP address state abnormal, **Severity**: Warning

4. Check source address selection policy in multi-IP scenarios (only execute when >= 2 active IPv4 addresses with different ifIndex exist):
   - Prerequisite: Need to find out which private IP is associated with public network egress; this information is not visible inside the OS and must be obtained from the cloud platform side: Use console / CLI / OpenAPI / SDK to query the network adapter and public IP binding relationship according to the actual environment, or request from the operations personnel responsible for the instance. If unavailable, can also use the "forced source IP comparison ping" additionally collected in Step 4 to reverse-derive the unique private IP that can reach the public network.
   - Normal: All IPs not associated with public network egress have `SkipAsSource=True`, or only the network adapter associated with public network egress participates in source selection
   - Abnormal: All IPs have `SkipAsSource=False` and only some network adapters are associated with public network egress -> **Root cause**: Network adapter IPs not associated with public network egress participating in source selection causing public network egress failure, **Severity**: Critical
   - Explanation: Mainstream public cloud VPC / software-defined network public network egress typically relies on cloud router performing SNAT, requiring source IP to equal the private IP associated with public network egress, otherwise packets will be silently dropped at the cloud platform side (the phenomenon seen inside the OS is 100% packet loss).

If APIPA address is found, check DHCP service -> See [networking-dhcp.md](references/online/networking-dhcp.md)

### Step 4: Default Route Check

**Data Collection**:

> Collection target: Obtain the egress interface and source IP actually selected by the kernel for external network targets (quick determination of main path), all default route (0.0.0.0/0) configurations, and each network adapter's InterfaceMetric (for tracing when abnormal)

**Additional Collection -- Multi-NIC Forced Source IP Comparison Ping** (only execute when multiple NICs / multiple default routes exist, and point 1 `Find-NetRoute` takes fallback path or determines possible "wrong egress selection"):

> Collection target: Use `ping -S` to force each local IP as source address, localize which IP can reach public network; serves as the only route verification basis when `Find-NetRoute` is unavailable, and cross-validation for wrong egress selection with multiple default routes

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 4 (includes additional collection)
- `Find-NetRoute` has no direct collector; egress is derived from `GuestOS:NetRoute` + `GuestOS:NetIpInterface` metrics

**Analysis Approach**:

> Prerequisite: In multi-default-route scenarios, need to determine from the cloud platform side which network adapter the public network egress is bound to (not visible inside the OS; use console / CLI / OpenAPI / SDK to query according to the actual environment)

1. Determine the egress actually selected by the kernel (`IPAddress` / `ifIndex` / `NextHop`):
   - Preferred: Read directly from `Find-NetRoute` output
   - Fallback (cmdlet unavailable, typical for Windows Server 2008 R2 / PSv2-3): Derive from the network adapter with lowest `RouteMetric + InterfaceMetric`; in case of tie, check interface binding order; **derived results MUST be cross-validated by the "forced source IP comparison ping" additionally collected in this Step before being used as root cause determination basis**

2. Determine based on egress results (enumerate by scenario, match and conclude):
   - Single default route + valid `NextHop` -> **This Step passes**
   - Multiple default routes + selected egress private IP == private IP associated with public network egress -> **This Step passes**
   - No 0.0.0.0/0 route at all -> **Root cause**: Default route missing, **Severity**: Critical
   - `NextHop` is `0.0.0.0` or invalid -> **Root cause**: Default gateway configuration invalid, **Severity**: Warning
   - Multiple default routes + selected egress private IP != private IP associated with public network egress (fallback path requires additional collection to confirm) -> **Root cause**: Multi-NIC default route priority conflict, wrong egress selected for public network, **Severity**: Critical; proceed to point 3 for configuration tracing

3. Multi-NIC configuration tracing (only execute when point 2 determines "wrong egress selection", **does not participate in root cause determination**, only provides metric adjustment input for fix solutions):
   - Observation items: Each network adapter's `InterfaceMetric`, default route `RouteMetric`, whether the network adapter associated with public network egress has the lowest metric
   - Typical pattern: Same metrics (default `AutomaticMetric=Enabled` calculation results are identical) -> Manually set metrics to differentiate primary/backup; network adapter associated with public network egress has higher metric -> Set its metric to lowest
   - Explanation: Same metrics != necessarily wrong egress (the kernel selects a unique egress based on secondary rules such as `RouteMetric`, interface binding order in case of tie); this section is only used as fix input

4. Interpret the additionally collected forced source IP comparison ping (only execute when additional collection was performed):
   - Normal: All source IPs can ping public network (or only the IP associated with public network egress is reachable and other IPs set to `SkipAsSource`)
   - Abnormal: Only one private IP is reachable, other private IPs have 100% packet loss -> Can reverse-derive that IP as the private IP associated with public network egress; combined with point 1 fallback derivation / point 2 preliminary determination results, confirm **Root cause**: Multi-NIC default route priority conflict, wrong egress selected for public network (**Severity**: Critical); also satisfies **Root cause**: Network adapter IPs not associated with public network egress participating in source selection causing public network egress failure

### Step 5: DNS Configuration and Resolution Check

**Data Collection**:

> Collection target: Obtain DNS server address configuration for all network interfaces, and verify whether DNS resolution function is normal

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 5

**Analysis Approach**:

1. Check whether DNS server is configured:
   - Normal: At least one DNS server IP configured
   - Abnormal: No DNS server configured -> **Root cause**: No DNS server configured, **Severity**: Warning

2. Check DNS server reachability (optional):
   - Normal: Can ping DNS server
   - Abnormal: DNS server unreachable -> **Root cause**: DNS server unreachable, **Severity**: Warning

3. Check DNS resolution function:
   - Normal: Can resolve domain names to IP addresses
   - Abnormal: Resolution failed but DNS server reachable -> **Root cause**: DNS resolution failed, **Severity**: Warning

If DNS configuration abnormalities are found, execute DNS diagnostics -> See [networking-dns.md](references/online/networking-dns.md)

### Step 6: End-to-End Connectivity Probe

**Data Collection**:

> Collection target: Test ICMP connectivity to gateway and external network (in multi-default-route scenarios, each gateway needs to be tested separately)

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 6

**Analysis Approach**:

1. Read the per-reply error text in the raw ping output FIRST -- it is the primary triage signal; the "100% loss" summary line alone is NOT sufficient for any conclusion:

   | Error text (EN; match against the OS-language localized equivalent) | Meaning | Direction |
   |---|---|---|
   | General failure | Packet rejected by local stack or filtering layer before leaving the host | Quick Step 1-3 sanity glance -> [networking-firewall.md Step 7](references/online/networking-firewall.md) (WFP / local filtering) immediately |
   | Request timed out | Packet left the host, no reply returned | Step 4 (route) -> firewall Step 7, then path/peer/platform direction |
   | Destination host unreachable | No route or ARP resolution failed | -> Step 4 (route/gateway) |
   | Transmission failed | Source address or interface problem (typical of `ping -S` with wrong source) | -> Step 3/4 |

   Note: GuestOS evidence can only POSITIVELY confirm in-instance causes (error text, WFP drop events). A clean in-instance chain only EXCLUDES local causes -- purely platform-side drops (SNAT / security group / platform rate limiting / upstream link) leave no record or event inside the OS. State external findings as "suspected platform/path issue, verify with platform-side evidence (security group / flow logs / bandwidth metrics)", never as a definitive root cause from GuestOS alone.

2. Check gateway connectivity:
   - Normal: Can ping gateway
   - Abnormal: Gateway unreachable -> **Root cause**: Gateway unreachable, **Severity**: Critical

3. Check external network connectivity:
   - Normal: Can ping external network address
   - Abnormal: External network unreachable -> First investigate in the following order: (a) Error-text triage table in point 1; (b) Review Step 4 "Multi-NIC forced source IP comparison ping" additional collection; (c) [networking-firewall.md](references/online/networking-firewall.md) Steps 3-5 + Step 7 -- mandatory; "some targets fail while others succeed" does NOT justify skipping it (selective third-party WFP filters produce exactly this pattern)

### Step 7: TCP Port Range Check

**Data Collection**:

> Collection target: Obtain TCP/UDP dynamic port range and system reserved (excluded) port range, check whether abnormally modified

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 7

**Analysis Approach**:

1. Check TCP dynamic port range:
   - Normal: Start port 49152, port count 16384 (range 49152-65535)
   - Abnormal: Port count too few (< 10000) -> **Root cause**: TCP dynamic port range too small, **Severity**: Warning

2. Check excluded port range:
   - Normal: Excluded port count reasonable (< 50)
   - Abnormal: Excluded ports too many (> 100) -> **Root cause**: Too many TCP excluded ports, **Severity**: Warning
   - Abnormal: Common ports excluded (e.g., 80, 443, 3389) -> **Root cause**: Critical ports reserved by system, **Severity**: Critical

### Step 8: Proxy Configuration Check

**Data Collection**:

> Collection target: Obtain WinHTTP proxy, IE proxy registry configuration, and proxy settings in environment variables

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 8

**Analysis Approach**:

1. Check whether proxy is enabled:
   - Normal: No proxy enabled (direct connection)
   - Abnormal: Proxy enabled and proxy server valid -> Confirm whether proxy server is reachable
   - Abnormal: Proxy enabled but proxy server unreachable -> **Root cause**: Proxy configuration error causing network unreachable, **Severity**: Warning

2. Check whether WinHTTP and IE proxy are consistent:
   - Normal: Both consistent or both empty
   - Abnormal: Inconsistent -> **Root cause**: WinHTTP proxy and IE proxy inconsistent, Windows Update and other services may be affected, **Severity**: Warning

3. Check proxy configuration in environment variables:
   - Normal: No proxy environment variables configured
   - Abnormal: Proxy environment variables configured -> **Root cause**: Environment variable proxy configuration detected, may affect network access for some applications, **Severity**: Warning

### Step 9: MTU and Interface Configuration Check

**Data Collection**:

> Collection target: Obtain each network adapter's MTU and RSS/Offload and other key interface configuration items, check whether non-standard configuration causes fragmentation packet loss or performance anomalies

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 9

**Analysis Approach**:

1. Check each network adapter's MTU (`Get-NetIPInterface` NlMtu):
   - Normal: VPC network adapter MTU = 1500
   - Abnormal: MTU < 1500 (e.g., manually reduced, PPPoE/tunnel legacy configuration) -> Large packets fragmented or dropped, manifested as some website timeouts, slow large file transfers -> **Root cause**: Network adapter MTU non-standard configuration causing fragmentation packet loss, **Severity**: Warning
   - Abnormal: Multiple network adapters with inconsistent MTU and cross-adapter routing exists -> Path MTU inconsistency causing intermittent packet loss, **Severity**: Warning
2. Check RSS/Offload advanced properties (`Get-NetAdapterAdvancedProperty`):
   - Normal: RSS enabled, Checksum/LSO offload enabled (VirtIO network adapter default values)
   - Abnormal: RSS disabled and CPU single-core soft interrupt saturated -> **Root cause**: RSS disabled causing multi-queue failure, single-core bottleneck under high traffic, **Severity**: Warning
   - Abnormal: Offload abnormally disabled -> Record as configuration anomaly (may be temporary troubleshooting operation), **Severity**: Info

### Step 10: Interface Counter Before/After Comparison (Packet Loss Direction Localization)

**Data Collection**:

> Collection target: Collect network adapter send/receive counters (Discards/Errors/bytes/packets) and TCP/UDP protocol stack counters, **collect once before and after fault reproduction each**, through incremental comparison to localize packet loss direction and layer

- PowerShell script: [networking-tcpip.ps1](references/online/scripts/networking-tcpip.ps1) Section Step 10

**Analysis Approach**:

1. A single snapshot has no diagnostic value (counters are cumulative since boot), MUST execute according to the "baseline collection -> wait for fault reproduction -> re-collect after reproduction" process, comparing the two increments:
   - `ReceivedDiscardedPackets` / `ReceivedPacketErrors` increment > 0 -> **Receive direction packet loss**: Localized to inbound link (platform-side inbound rate limiting / network adapter receive queue / inbound filter driver)
   - `OutboundDiscardedPackets` / `OutboundPacketErrors` increment > 0 -> **Send direction packet loss**: Localized to outbound link (outbound bandwidth/PPS ceiling, CIPU fragmentation limit, outbound filter driver)
   - Network adapter counters have no increment but TCP retransmission counters (`netstat -s` retransmitted segments) grow -> Packet loss is outside GuestOS (peer / link / platform forwarding layer), transfer to platform-side localization
2. Counter comparison conclusions MUST annotate the two collection time points and interval as part of the evidence chain; when no reproduction window is available, truthfully state that localization is not possible, guide the user to arrange a reproduction time

### Step 11: Deep Packet Capture (Fallback Deep Investigation, Requires User Confirmation)

**Data Collection**:

> Collection target: When the preset sequence has not found root cause and the fault is reproducible, capture network packets for protocol-layer analysis. Packet capture has performance overhead and produces large files; MUST first explain to the user and obtain confirmation

**Analysis Approach**:

1. Select packet capture tool based on system version (`BuildNumber >= 17763`, i.e., Server 2019 / Win10 1809 and above, including 2022/2025):
   ```powershell
   pktmon start --capture -f C:\capture.etl
   # ... reproduce the issue, then:
   pktmon stop
   pktmon etl2pcap C:\capture.etl -o C:\capture.pcapng
   ```
   pktmon has built-in etl2pcap conversion, produces pcapng that can be directly analyzed with Wireshark
2. Old systems (Server 2016 and earlier, `BuildNumber < 17763`):
   ```powershell
   netsh trace start capture=yes tracefile=C:\capture.etl
   # ... reproduce the issue, then:
   netsh trace stop
   ```
   Produces .etl format, **old systems have no built-in conversion capability** (pktmon does not exist) -- MUST truthfully inform the user: need to backhaul .etl and parse with Network Monitor / Message Analyzer, or convert on a machine that has pktmon; do not promise that pcap can be obtained directly within the instance
3. Packet capture analysis focuses on: whether the target five-tuple has packets sent with no response (outbound interception), has inbound packets but protocol stack not responding (local filtering), TCP retransmission pattern (link quality); analysis conclusions are linked back to the corresponding domain (firewall / platform side / peer)

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 3 finds APIPA address (169.254.x.x) | -> [networking-dhcp.md](references/online/networking-dhcp.md) |
| Conditional jump | Step 5 DNS resolution failed | -> [networking-dns.md](references/online/networking-dns.md) |
| Mandatory jump | Step 6 connectivity test failed (any config state) | -> [networking-firewall.md Step 7](references/online/networking-firewall.md) (WFP packet drop localization) |
| Mandatory jump | Ping reports "General Failure" (any OS-language localized equivalent) | -> [networking-firewall.md Step 7](references/online/networking-firewall.md) (WFP packet drop localization) |
| Conditional jump | Symptom reports "General Failure" (network settings/firewall operation error, connection prompt general failure) | -> [networking-firewall.md](references/online/networking-firewall.md) (Firewall service and configuration check + Step 7 WFP) |
| Prerequisite dependency | Step 3/4 multi-NIC scenario determination | -> Need to obtain network adapter and public network egress binding relationship from cloud platform side (specific tool selected by model based on actual cloud environment using console / CLI / OpenAPI / SDK) |
| Chained successor | This file did not confirm root cause, user reports network issue | -> [networking-firewall.md](references/online/networking-firewall.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [networking-tcpip.md](references/online/fixes/networking-tcpip.md).
