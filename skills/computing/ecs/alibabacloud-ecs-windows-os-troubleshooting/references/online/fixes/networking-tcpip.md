# Network TCP/IP Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Network adapter disabled

**Fix operation**:

```powershell
# Enable network adapter (replace <AdapterName> with actual name)
Enable-NetAdapter -Name "<AdapterName>" -Confirm:$false
```

**Verification**:

```powershell
Get-NetAdapter -Name "<AdapterName>" | Select-Object Name, State, Status
```

Expected result: Adapter status is enabled and connected

**Risk notes**:

- **Session impact**: None, enabling the adapter does not disconnect existing connections.
- **Persistence scope**: Takes effect immediately, persisted across reboot.
- **Rollback command**: `Disable-NetAdapter -Name "<AdapterName>" -Confirm:$false`
- **Note**: If the adapter driver has issues, enabling may not succeed.

---

### Root cause: TCP/IP protocol not bound

**Fix operation**:

```powershell
# Re-bind TCP/IP protocol (replace <AdapterName> with actual name)
Enable-NetAdapterBinding -Name "<AdapterName>" -ComponentID ms_tcpip
```

**Verification**:

```powershell
Get-NetAdapterBinding -Name "<AdapterName>" -ComponentID ms_tcpip | Select-Object Name, ComponentID, Enabled
```

Expected result: TCP/IP protocol binding is enabled

**Risk notes**:

- **Session impact**: May cause brief network interruption.
- **Persistence scope**: Takes effect immediately, persisted across reboot.
- **Rollback command**: `Disable-NetAdapterBinding -Name "<AdapterName>" -ComponentID ms_tcpip`

---

### Root cause: No network adapter

**Fix operation**:

Scan for hardware changes in Device Manager, or check whether the virtualization platform has correctly attached the virtual network adapter

```powershell
# Scan for hardware changes
pnputil /scan-devices
```

**Verification**:

```powershell
Get-NetAdapter | Select-Object Name, InterfaceDescription, Status
```

Expected result: At least one network adapter is displayed

**Risk notes**:

- **Session impact**: None, hardware scan does not disconnect existing connections.
- **Persistence scope**: Current session only, auto re-scan after reboot.
- **Rollback command**: No rollback needed.
- **Note**: If in a virtualized environment, check the instance network configuration in the cloud console.

---

### Root cause: Network adapter status unknown

**Fix operation**:

```powershell
# Disable then re-enable the network adapter (replace <AdapterName> with actual name)
Disable-NetAdapter -Name "<AdapterName>" -Confirm:$false
Start-Sleep -Seconds 2
Enable-NetAdapter -Name "<AdapterName>" -Confirm:$false
```

**Verification**:

```powershell
Get-NetAdapter -Name "<AdapterName>" | Select-Object Name, State, Status
```

Expected result: Adapter status changes from unknown to enabled

**Risk notes**:

- **Session impact**: Resetting the adapter causes brief network interruption, disconnecting existing TCP/RDP sessions.
- **Persistence scope**: Current session only, adapter auto recovers after reboot.
- **Rollback command**: No rollback needed, adapter will auto recover.

---

### Root cause: Network adapter not connected or underlying link down

**Fix operation**:

```powershell
# 1. Check network adapter physical connection status
Get-NetAdapter | Where-Object {$_.MediaConnectionState -eq 'Disconnected'} | Select-Object Name, MediaConnectionState, InterfaceDescription | Format-Table -AutoSize

# 2. Try to enable the adapter (if it was disabled)
$disconnectedAdapter = Get-NetAdapter | Where-Object {$_.MediaConnectionState -eq 'Disconnected' -and $_.State -eq 'Disabled'}
if ($disconnectedAdapter) {
    Enable-NetAdapter -Name $disconnectedAdapter.Name -Confirm:$false
}

# 3. If in a virtualized environment, check VirtIO network adapter driver status
Get-PnpDevice -Class Net | Where-Object {$_.FriendlyName -like '*VirtIO*'} | Select-Object FriendlyName, Status | Format-Table -AutoSize
```

**Verification**:

```powershell
Get-NetAdapter | Select-Object Name, MediaConnectionState, LinkSpeed
```

Expected result: Adapter connection status shows connected, link speed shows a specific value (not 0)

**Risk notes**:

- **Session impact**: None, connection status check does not affect existing sessions.
- **Persistence scope**: No modifications involved, diagnostic operation only.
- **Rollback command**: No rollback needed.
- **Note**: If the cloud platform network configuration is abnormal, check in the cloud console or contact technical support.

---

### Root cause: Network adapter link not established

**Fix operation**:

```powershell
# Reset network adapter driver (replace <AdapterName> with actual name)
Restart-NetAdapter -Name "<AdapterName>"

# If still failing, check driver status
Get-PnpDevice | Where-Object {$_.FriendlyName -like "*<AdapterName>*"} | Select-Object Status, Class
```

**Verification**:

```powershell
Get-NetAdapter -Name "<AdapterName>" | Select-Object Name, LinkSpeed
```

Expected result: LinkSpeed > 0

**Risk notes**:

- **Session impact**: Restarting the adapter causes brief network interruption, disconnecting existing TCP/RDP sessions.
- **Persistence scope**: Current session only, adapter recovers immediately.
- **Rollback command**: No rollback needed.
- **Note**: If the driver has issues, updating the driver may be required.

---

### Root cause: Third-party network protocol binding detected

**Fix operation**:

```powershell
# View third-party protocols (replace <AdapterName> with actual name)
Get-NetAdapterBinding -Name "<AdapterName>" | Where-Object {$_.ComponentID -notlike 'ms_*'} | Select-Object Name, ComponentID, DisplayName

# Disable suspicious third-party protocol (proceed with caution)
# Disable-NetAdapterBinding -Name "<AdapterName>" -ComponentID <ThirdPartyProtocolID>
```

**Verification**:

```powershell
Get-NetAdapterBinding -Name "<AdapterName>" | Select-Object Name, ComponentID, Enabled
```

Expected result: Only Microsoft standard protocols retained

**Risk notes**:

- **Session impact**: Disabling third-party protocols may affect VPN, antivirus software, and other functions.
- **Persistence scope**: Takes effect immediately, persisted across reboot.
- **Rollback command**: `Enable-NetAdapterBinding -Name "<AdapterName>" -ComponentID <ThirdPartyProtocolID>`
- **Note**: Confirm the protocol's purpose before the operation to avoid affecting security software.

---

### Root cause: No IPv4 address assigned

**Fix operation**:

```powershell
# If using DHCP, release and renew IP (replace <AdapterName> with actual name)
ipconfig /release
ipconfig /renew

# If using static IP, manually configure IP (example)
# New-NetIPAddress -InterfaceAlias "<AdapterName>" -IPAddress "192.168.1.100" -PrefixLength 24 -DefaultGateway "192.168.1.1"
```

**Verification**:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, IPAddress, AddressState
```

Expected result: At least one IPv4 address in Preferred state

**Risk notes**:

- **Session impact**: None, configuring IP does not disconnect existing connections (but static IP must be confirmed correct).
- **Persistence scope**: DHCP only current lease cycle; static IP written to adapter configuration, persisted across reboot.
- **Rollback command**: `ipconfig /release` (DHCP scenario)

---

### Root cause: DHCP acquisition failed, using APIPA address

**Fix operation**:

```powershell
# Check DHCP service status
Get-Service -Name Dhcp | Select-Object Name, Status, StartType

# Restart DHCP client service
if ((Get-Service -Name Dhcp).Status -ne 'Running') {
    Start-Service -Name Dhcp
}

# Renew IP
ipconfig /release
ipconfig /renew
```

**Verification**:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '169.254.*'} | Select-Object IPAddress
```

Expected result: IP address is not in the 169.254.x.x range

**Risk notes**:

- **Session impact**: None, starting the service does not disconnect existing connections.
- **Persistence scope**: DHCP only current lease cycle.
- **Rollback command**: `ipconfig /release`
- **Note**: If the DHCP server is unavailable, check the network infrastructure.

---

### Root cause: IP address state abnormal

**Fix operation**:

```powershell
# Reset network adapter (replace <AdapterName> with actual name)
Reset-NetAdapterAdvancedProperty -Name "<AdapterName>" -All
Restart-NetAdapter -Name "<AdapterName>"
```

**Verification**:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, IPAddress, AddressState
```

Expected result: AddressState = Preferred

**Risk notes**:

- **Session impact**: Resetting advanced properties and restarting the adapter causes brief network loss, disconnecting existing TCP/RDP sessions.
- **Persistence scope**: Restores default settings, persisted across reboot.
- **Rollback command**: No single-command rollback, requires manual reconfiguration of custom properties.
- **Note**: Clears all custom adapter advanced property configurations.

---

### Root cause: NIC IP not associated with public egress participating in source selection causing public egress failure

**Fix operation**:

```powershell
# Set SkipAsSource=True for every private IP that is NOT associated with the public egress
# Replace <NoPubIfIndex> and <NoPubIp> with the actual ifIndex and IP of the NIC without public egress
Set-NetIPAddress -InterfaceIndex <NoPubIfIndex> -IPAddress <NoPubIp> -SkipAsSource $true
```

**Verification**:

```powershell
# 1. Verify SkipAsSource is in effect
Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, ifIndex, IPAddress, SkipAsSource

# 2. Kernel egress should now resolve to the private IP associated with the public egress
Find-NetRoute -RemoteIPAddress 223.5.5.5 | Select-Object IPAddress, InterfaceAlias, ifIndex

# 3. Default-source ping to public target should succeed
ping -n 3 223.5.5.5
```

Expected result: `IPAddress` returned by `Find-NetRoute` equals the private IP associated with the public egress; `ping 223.5.5.5` 0% packet loss

**Risk notes**:

- **Session impact**: Immediately disconnects any current TCP connections established with these IPs as the local source (inbound connections using these IPs as the local endpoint are not affected). RDP inbound session source IP is already locked, not affected.
- **Persistence scope**: Written to persistent configuration, persisted across reboot.
- **Rollback command**: `Set-NetIPAddress -InterfaceIndex <ifIndex> -IPAddress <IP> -SkipAsSource $false`
- **Applicable conditions**: Use only when it is clear that these NICs not associated with a public egress are used solely for inbound reception on the internal network and do not actively initiate outbound connections. If these NICs also need public egress (e.g., each has its own independent public egress), use the "Adjust InterfaceMetric" approach instead.

---

### Root cause: Default route missing, cannot access external network

**Fix operation**:

```powershell
# Add default route (replace <GatewayIP> and <AdapterName> with actual values)
New-NetRoute -DestinationPrefix "0.0.0.0/0" -NextHop "<GatewayIP>" -InterfaceAlias "<AdapterName>"
```

**Verification**:

```powershell
Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Select-Object InterfaceAlias, NextHop
```

Expected result: Default route exists, NextHop is a valid gateway address

**Risk notes**:

- **Session impact**: None, adding a route does not disconnect existing connections.
- **Persistence scope**: Written to routing table, persisted across reboot.
- **Rollback command**: `Remove-NetRoute -DestinationPrefix "0.0.0.0/0" -InterfaceAlias "<AdapterName>" -Confirm:$false`
- **Note**: Ensure the gateway address is correct; incorrect configuration will cause external network to be unreachable.

---

### Root cause: Multi-NIC default route priority conflict, wrong egress selected for public access

**Fix operation**:

```powershell
# Set the NIC associated with public egress to the lowest InterfaceMetric; raise the metric of other NICs
# Replace <PubEgressIfIndex> with the ifIndex of the NIC associated with the public egress
# Replace <NoPubIfIndex1/2> with the ifIndex of NICs NOT associated with the public egress
Set-NetIPInterface -InterfaceIndex <PubEgressIfIndex> -InterfaceMetric 10
Set-NetIPInterface -InterfaceIndex <NoPubIfIndex1>    -InterfaceMetric 100
Set-NetIPInterface -InterfaceIndex <NoPubIfIndex2>    -InterfaceMetric 100
```

**Verification**:

```powershell
# 1. Verify metric values are applied
Get-NetIPInterface -AddressFamily IPv4 | Select-Object ifIndex, InterfaceAlias, InterfaceMetric, AutomaticMetric

# 2. Kernel egress should now go through the NIC associated with public egress
Find-NetRoute -RemoteIPAddress 223.5.5.5 | Select-Object IPAddress, InterfaceAlias, ifIndex

# 3. Default-source ping to public target should succeed
ping -n 3 223.5.5.5
Test-NetConnection -ComputerName www.example.com -Port 443 | Select-Object ComputerName, RemoteAddress, TcpTestSucceeded
```

Expected result: `ifIndex` returned by `Find-NetRoute` equals the NIC associated with the public egress; `ping 223.5.5.5` 0% packet loss; TCP 443 probe `TcpTestSucceeded=True`

**Risk notes**:

- **Session impact**: Only changes route priority, **does not disconnect existing TCP/RDP sessions** (the 4-tuple source IP of established connections is already locked).
- **Persistence scope**: Written to persistent routing table, persisted across reboot.
- **Rollback command**: `Set-NetIPInterface -InterfaceIndex <ifIndex> -InterfaceMetric 15` (or restore to `AutomaticMetric=Enabled`).
- **Choosing between approaches**: This approach is suitable for scenarios where multiple NICs may need public egress; if NICs not associated with a public egress are strictly for internal network use only, using the "Set SkipAsSource for NIC IPs not associated with public egress" approach is more thorough.

---

### Root cause: Invalid default gateway configuration

**Fix operation**:

```powershell
# Remove invalid route (replace <AdapterName> with actual name)
Get-NetRoute -DestinationPrefix "0.0.0.0/0" -InterfaceAlias "<AdapterName>" | Remove-NetRoute -Confirm:$false

# Re-add correct default route (replace <GatewayIP> with actual gateway)
New-NetRoute -DestinationPrefix "0.0.0.0/0" -NextHop "<GatewayIP>" -InterfaceAlias "<AdapterName>"
```

**Verification**:

```powershell
Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Select-Object InterfaceAlias, NextHop
```

Expected result: NextHop is a valid IP address (not 0.0.0.0)

**Risk notes**:

- **Session impact**: Deleting the old route may briefly disconnect connections dependent on that route; restored after adding the new route.
- **Persistence scope**: Written to routing table, persisted across reboot.
- **Rollback command**: `Remove-NetRoute -DestinationPrefix "0.0.0.0/0" -InterfaceAlias "<AdapterName>" -Confirm:$false; New-NetRoute -DestinationPrefix "0.0.0.0/0" -NextHop "<OriginalGatewayIP>" -InterfaceAlias "<AdapterName>"`
- **Note**: Incorrect gateway configuration will cause external network to be unreachable.

---

### Root cause: No DNS server configured

**Fix operation**:

```powershell
# Get active network adapter (replace <AdapterName> with actual name)
$adapter = Get-NetAdapter -Name "<AdapterName>"
if ($adapter) {
    # Set DNS servers
    Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses @("100.100.2.136", "100.100.2.138")
}
```

**Verification**:

```powershell
Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object {$_.ServerAddresses -ne $null} | Select-Object InterfaceAlias, ServerAddresses
```

Expected result: ServerAddresses contains valid DNS server IP

**Risk notes**:

- **Session impact**: None, modifying DNS does not disconnect existing connections.
- **Persistence scope**: Written to adapter configuration, persisted across reboot.
- **Rollback command**: `Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ResetServerAddresses`
- **Note**: Incorrect DNS configuration will cause domain resolution failure.

---

### Root cause: DNS server unreachable

**Fix operation**:

```powershell
# Change DNS servers (replace <AdapterName> with actual name)
$adapter = Get-NetAdapter -Name "<AdapterName>"
if ($adapter) {
    Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses @("100.100.2.136", "100.100.2.138")
}
```

**Verification**:

```powershell
Test-Connection -ComputerName 100.100.2.136 -Count 2
```

Expected result: DNS server reachable

**Risk notes**:

- **Session impact**: None, modifying DNS does not disconnect existing connections.
- **Persistence scope**: Written to adapter configuration, persisted across reboot.
- **Rollback command**: `Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses @('<OriginalDNS1>', '<OriginalDNS2>')`
- **Note**: Using public DNS may be restricted by firewall policy.

---

### Root cause: TCP dynamic port range too small

**Fix operation**:

```powershell
# Restore default dynamic port range (49152-65535, 16384 ports total)
netsh int ipv4 set dynamicport tcp start=49152 num=16384
netsh int ipv6 set dynamicport tcp start=49152 num=16384
netsh int ipv4 set dynamicport udp start=49152 num=16384
netsh int ipv6 set dynamicport udp start=49152 num=16384
```

**Verification**:

```powershell
# Verify dynamic port range restored
netsh int ipv4 show dynamicport tcp
```

Expected result: Start port = 49152, number of ports = 16384

**Risk notes**:

- **Session impact**: None, only affects port allocation for new connections.
- **Persistence scope**: Takes effect immediately, persisted across reboot.
- **Rollback command**: `netsh int ipv4 set dynamicport tcp start=<OriginalStartPort> num=<OriginalPortCount>`

---

### Root cause: Too many TCP excluded ports

**Description**:

TCP excluded ports are automatically managed by system services (Hyper-V, NAT, Windows Update, etc.) to reserve specific port ranges for system service use. Too many excluded ports are usually due to the following reasons:

1. **Hyper-V services**: Dynamically allocates excluded ports when creating virtual machines or containers
2. **Windows NAT services**: WSL2, Docker, etc. register port exclusion ranges
3. **Other system services**: Some Windows services request port reservations at startup

Excluded ports are normal system behavior; manual deletion is not recommended as it may cause related services to malfunction. If excluded ports affect application operation, try restarting the related service to release ports.

---

### Root cause: Gateway unreachable

**Fix operation**:

```powershell
# Check ARP table
# Check ARP table
Get-NetNeighbor | Where-Object { $_.AddressFamily -eq 'IPv4' } | Select-Object IPAddress, LinkLayerAddress, State | Format-Table -AutoSize

# Check network adapter configuration
Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object Name, InterfaceDescription

# If in a virtualized environment, check cloud platform routing table configuration
```

**Verification**:

```powershell
Test-Connection -ComputerName <GatewayIP> -Count 2
```

Expected result: Gateway reachable

**Risk notes**:

- **Session impact**: None, only viewing ARP table and adapter status.
- **Persistence scope**: No modifications involved, diagnostic operation only.
- **Rollback command**: No rollback needed.
- **Note**: Gateway unreachable may be a network infrastructure issue; contact the network administrator.

---

### Root cause: DNS resolution failure

**Fix operation**:

```powershell
# Clear DNS cache
Clear-DnsClientCache

# Refresh DNS registration
ipconfig /flushdns
ipconfig /registerdns
```

**Verification**:

```powershell
Resolve-DnsName -Name www.aliyun.com -Type A | Select-Object Name, IPAddress
```

Expected result: Can successfully resolve domain

**Risk notes**:

- **Session impact**: None, clearing cache does not disconnect existing connections.
- **Persistence scope**: Current session only, cache will be automatically rebuilt.
- **Rollback command**: No rollback needed, cache will be automatically rebuilt.

---

### Root cause: WinHTTP proxy inconsistent with IE proxy

**Fix operation**:

```powershell
# Sync WinHTTP proxy with IE settings
netsh winhttp import proxy source=ie
```

**Verification**:

```powershell
netsh winhttp show proxy
```

Expected result: WinHTTP proxy consistent with IE proxy configuration

**Risk notes**:

- **Session impact**: May affect network connections of services that depend on proxy.
- **Persistence scope**: Written to system proxy configuration, persisted across reboot.
- **Rollback command**: `netsh winhttp set proxy <OriginalProxyAddress>`

---

### Root cause: Environment variable proxy configuration detected

**Fix operation**:

```powershell
# View current proxy environment variables
Write-Output "HTTP_PROXY=$($env:HTTP_PROXY)"
Write-Output "HTTPS_PROXY=$($env:HTTPS_PROXY)"

# Clear proxy environment variables (temporary, current session)
$env:HTTP_PROXY = $null
$env:HTTPS_PROXY = $null
$env:NO_PROXY = $null

# To permanently remove, modify system environment variables
# [Environment]::SetEnvironmentVariable("HTTP_PROXY", $null, "Machine")
# [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "Machine")
```

**Verification**:

```powershell
Write-Output "HTTP_PROXY=$($env:HTTP_PROXY)"
Write-Output "HTTPS_PROXY=$($env:HTTPS_PROXY)"
```

Expected result: Environment variable proxy is empty

**Risk notes**:

- **Session impact**: May affect network connections of applications that depend on proxy.
- **Persistence scope**: Current session only; permanent deletion requires uncommenting the `SetEnvironmentVariable` command.
- **Rollback command**: `$env:HTTP_PROXY='<OriginalProxy>'; $env:HTTPS_PROXY='<OriginalProxy>'`

---

### Root cause: Proxy configuration error

**Fix operation**:

```powershell
netsh winhttp reset proxy

# Disable IE proxy (registry)
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name ProxyEnable -Value 0 -ErrorAction SilentlyContinue
```

**Verification**:

```powershell
netsh winhttp show proxy
Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name ProxyEnable, ProxyServer | Select-Object ProxyEnable, ProxyServer
```

Expected result: Proxy disabled, configured for direct connection

**Risk notes**:

- **Session impact**: If the network environment actually requires a proxy, disabling it will cause external network to be unreachable.
- **Persistence scope**: WinHTTP written to system configuration, persisted across reboot; IE proxy written to registry, persisted across reboot.
- **Rollback command**: `netsh winhttp set proxy <OriginalProxy>; Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1`

---

### Root cause: Non-standard NIC MTU causing fragmented packet loss

**Fix operation**:

```powershell
# Reset MTU of the affected adapter to standard 1500 (replace <InterfaceAlias>)
Set-NetIPInterface -InterfaceAlias '<InterfaceAlias>' -NlMtu 1500
```

**Verification**:

```powershell
Get-NetIPInterface -InterfaceAlias '<InterfaceAlias>' | Select-Object InterfaceAlias, NlMtu
```

Expected result: NlMtu = 1500

**Risk notes**:

- **Session impact**: MTU change takes effect immediately; in-flight large packets may be momentarily lost; if the actual link MTU is less than 1500 (tunnel/PPPoE environment), changing to 1500 will introduce fragmentation instead; set according to the actual link MTU.
- **Persistence scope**: Written to interface configuration, persisted across reboot.
- **Rollback command**: `Set-NetIPInterface -InterfaceAlias '<InterfaceAlias>' -NlMtu <OriginalMTUValue>`
