# DHCP Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: DHCP Client service abnormal

**Fix operation**:

```powershell
# Set DHCP Client service to automatic startup and start it
Set-Service -Name Dhcp -StartupType Automatic
Start-Service -Name Dhcp
```

**Verification**:

```powershell
Get-Service -Name Dhcp | Select-Object Name, Status, StartType
```

Expected result: Status = Running, StartType = Automatic

**Risk notes**:

- **Session impact**: None, starting the service does not disconnect existing connections.
- **Persistence scope**: Writes service startup type, persisted across reboot.
- **Rollback command**: `Set-Service -Name Dhcp -StartupType Disabled; Stop-Service -Name Dhcp`

---

### Root cause: Network adapter does not have DHCP enabled

**Fix operation**:

```powershell
# Get target adapter (replace <AdapterName> with actual name)
$ifIndex = (Get-NetAdapter -Name '<AdapterName>').InterfaceIndex

# Enable DHCP (remove static IP, switch to DHCP)
Set-NetIPInterface -InterfaceIndex $ifIndex -Dhcp Enabled

# Remove manually configured DNS (allow DHCP-assigned DNS to take effect)
Set-DnsClientServerAddress -InterfaceIndex $ifIndex -ResetServerAddresses

# Trigger DHCP acquisition
ipconfig /release
ipconfig /renew
```

**Verification**:

```powershell
Get-NetIPInterface -InterfaceIndex $ifIndex -AddressFamily IPv4 | Select-Object Dhcp | Format-Table -AutoSize
Get-NetIPAddress -InterfaceIndex $ifIndex -AddressFamily IPv4 | Select-Object IPAddress, SuffixOrigin | Format-Table -AutoSize
```

Expected result: Dhcp = Enabled, SuffixOrigin = Dhcp

**Risk notes**:

- **Session impact**: Immediately loses the original static IP, disconnecting all TCP/RDP sessions based on that IP.
- **Persistence scope**: Writes to adapter configuration, persisted across reboot.
- **Rollback command**: `New-NetIPAddress -InterfaceIndex $ifIndex -IPAddress '<OriginalStaticIP>' -PrefixLength <OriginalPrefix> -DefaultGateway '<OriginalGateway>'; Set-NetIPInterface -InterfaceIndex $ifIndex -Dhcp Disabled`
- **Note**: Record current IP/gateway/DNS before the operation for rollback.

---

### Root cause: DHCP acquisition failed (APIPA address)

**Fix operation**:

```powershell
# Restart DHCP Client service
Restart-Service -Name Dhcp

# Release current address and reacquire
ipconfig /release
ipconfig /renew
```

**Verification**:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike 'Loopback*'} | Select-Object InterfaceAlias, IPAddress, SuffixOrigin
```

Expected result: IP address is not in the 169.254.x.x range, SuffixOrigin is Dhcp

**Risk notes**:

- **Session impact**: After release, immediately loses current IP, disconnecting all TCP/RDP sessions; if DHCP server is unavailable, briefly no network at all.
- **Persistence scope**: Only current lease cycle, does not modify persistent configuration.
- **Rollback command**: `ipconfig /renew`

---

### Root cause: DHCP lease expired and renewal failed

**Fix operation**:

```powershell
# Restart DHCP Client service
Restart-Service -Name Dhcp

# Force lease renewal
ipconfig /release
ipconfig /renew

# If still failing, reset Winsock and TCP/IP stack (requires reboot to take effect)
netsh winsock reset
netsh int ip reset
```

**Verification**:

```powershell
Get-CimInstance -ClassName Win32_NetworkAdapterConfiguration | Where-Object {$_.DHCPEnabled -eq $true} | Select-Object Description, DHCPServer, DHCPLeaseObtained, DHCPLeaseExpires
```

Expected result: DHCPLeaseExpires is later than current time

**Risk notes**:

- **Session impact**: After reboot takes effect, all existing network connections will be disconnected.
- **Persistence scope**: Writes to system configuration, requires reboot to take effect, persisted across reboot.
- **Rollback command**: No single-command rollback, requires manual reconfiguration of network parameters.
- **Note**: Winsock/TCP-IP reset clears all custom network configurations (including proxy, static routes, etc.), use only when basic DHCP fixes are ineffective.

---

### Root cause: DHCP server unreachable

**Fix operation**:

```powershell
# Check network adapter link status
Get-NetAdapter | Select-Object Name, Status, MediaConnectionState | Format-Table -AutoSize

# Try to reacquire DHCP lease
ipconfig /release
ipconfig /renew

# If still failing, temporarily configure static IP to restore network connectivity (replace <> with actual values)
# New-NetIPAddress -InterfaceAlias '<AdapterName>' -IPAddress '<IPAddress>' -PrefixLength <SubnetPrefix> -DefaultGateway '<Gateway>'
# Set-DnsClientServerAddress -InterfaceAlias '<AdapterName>' -ServerAddresses @('<DNS1>', '<DNS2>')
```

**Verification**:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike 'Loopback*'} | Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize
Test-Connection -ComputerName 100.100.2.136 -Count 2
```

Expected result: Has valid IP and can ping gateway

**Risk notes**:

- **Session impact**: Brief network loss after release; immediately restored after configuring static IP.
- **Persistence scope**: Static IP written to adapter configuration, persisted across reboot.
- **Rollback command**: `Set-NetIPInterface -InterfaceAlias '<AdapterName>' -Dhcp Enabled; ipconfig /renew`
- **Note**: Static IP is only a temporary solution; contact the network administrator to troubleshoot DHCP server issues.

---

### Root cause: Network adapter disabled

**Fix operation**:

```powershell
# Enable network adapter (replace <AdapterName> with actual name)
Enable-NetAdapter -Name '<AdapterName>'

# Wait for adapter to be ready, then acquire DHCP
Start-Sleep -Seconds 3
ipconfig /renew
```

**Verification**:

```powershell
Get-NetAdapter -Name '<AdapterName>' | Select-Object Name, Status, MediaConnectionState
Get-NetIPAddress -InterfaceAlias '<AdapterName>' -AddressFamily IPv4 | Select-Object IPAddress
```

Expected result: Status = Up, has valid IP address

**Risk notes**:

- **Session impact**: None, enabling the adapter does not affect existing connections.
- **Persistence scope**: Takes effect immediately, persisted across reboot.
- **Rollback command**: `Disable-NetAdapter -Name '<AdapterName>' -Confirm:$false`

---

### Root cause: DHCP server did not assign default gateway

**Fix operation**:

```powershell
# Manually add default gateway (replace <> with actual values)
$ifIndex = (Get-NetAdapter -Name '<AdapterName>').InterfaceIndex
New-NetRoute -InterfaceIndex $ifIndex -DestinationPrefix '0.0.0.0/0' -NextHop '<GatewayAddress>'
```

**Verification**:

```powershell
Get-NetRoute -InterfaceIndex $ifIndex -DestinationPrefix '0.0.0.0/0' | Select-Object NextHop
Test-Connection -ComputerName www.aliyun.com -Count 2
```

Expected result: Has default route and can ping external network

**Risk notes**:

- **Session impact**: None, adding a route does not disconnect existing connections.
- **Persistence scope**: Written to routing table, persisted across reboot; but may be overwritten by next DHCP renewal.
- **Rollback command**: `Remove-NetRoute -InterfaceIndex $ifIndex -DestinationPrefix '0.0.0.0/0' -Confirm:$false`
- **Note**: Only a temporary solution; contact the network administrator to fix the DHCP server gateway assignment configuration.
