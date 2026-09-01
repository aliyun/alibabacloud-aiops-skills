$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Network Adapter Status Check ---

try {
    Get-NetAdapter |
        Select-Object Name, InterfaceDescription, Status, MacAddress, LinkSpeed |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 net-adapter: " + $_.Exception.Message)
}

# --- Step 2: Network Protocol Binding Check ---

try {
    Get-NetAdapterBinding |
        Select-Object Name, ComponentID, Enabled, DisplayName |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 adapter-binding: " + $_.Exception.Message)
}

# --- Step 3: IP Address Configuration Check ---

try {
    Get-NetIPAddress -AddressFamily IPv4 |
        Select-Object InterfaceAlias, ifIndex, IPAddress, PrefixLength, AddressState, PrefixOrigin, SuffixOrigin, SkipAsSource |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 net-ipaddress: " + $_.Exception.Message)
}

# --- Step 4: Default Route Check ---

# 1. Kernel routing result (preferred egress, available on Windows 8 / Server 2012+)
try {
    $null = Get-Command Find-NetRoute
    Find-NetRoute -RemoteIPAddress 223.5.5.5 |
        Select-Object IPAddress, InterfaceAlias, ifIndex, NextHop, DestinationPrefix |
        Format-Table -AutoSize
} catch {
    Write-Output "Find-NetRoute not available; fallback to route print, infer egress by lowest (RouteMetric + InterfaceMetric), MUST cross-validate by forced-source ping below"
    $routePrint = route print 0.0.0.0 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step4 route-print: exit=$LASTEXITCODE $(($routePrint | Out-String).Trim())" }
    $routePrint
}

# 2. All default routes (do not use -First 1)
try {
    Get-NetRoute -DestinationPrefix "0.0.0.0/0" -AddressFamily IPv4 |
        Select-Object ifIndex, InterfaceAlias, NextHop, RouteMetric, InterfaceMetric, Protocol |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 default-routes: " + $_.Exception.Message)
}

# 3. InterfaceMetric per network adapter (multi-adapter routing tracing)
try {
    Get-NetIPInterface -AddressFamily IPv4 |
        Select-Object ifIndex, InterfaceAlias, InterfaceMetric, AutomaticMetric, ConnectionState |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 ip-interface-metrics: " + $_.Exception.Message)
}

# --- Step 4 Additional: Multi-Adapter Forced Source IP Comparison Ping ---
# Symptom command: raw `ping` full output is the diagnostic signal, never filtered
try {
    Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.AddressState -eq 'Preferred' -and $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -notlike '127.*' } |
        ForEach-Object {
            Write-Output "=== Source $($_.IPAddress) (ifIndex=$($_.ifIndex)) ==="
            & ping -S $_.IPAddress -n 2 223.5.5.5 2>&1
        }
} catch {
    Write-Host ("ERROR step4 forced-source-ping: " + $_.Exception.Message)
}

# --- Step 5: DNS Configuration and Resolution Check ---

# 1. DNS server configuration per interface
try {
    Get-DnsClientServerAddress -AddressFamily IPv4 |
        Where-Object { $_.ServerAddresses -ne $null } |
        Select-Object InterfaceAlias, ServerAddresses |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 dns-server-config: " + $_.Exception.Message)
}

# 2. DNS resolution function verification
try {
    Resolve-DnsName -Name www.example.com -Type A |
        Select-Object Name, IPAddress |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 resolve-test: " + $_.Exception.Message)
}

# --- Step 6: End-to-End Connectivity Probe ---

try {
    # All default gateways (not just the first one)
    $gateways = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -AddressFamily IPv4 |
        Select-Object -ExpandProperty NextHop -Unique
    $gateways
} catch {
    Write-Host ("ERROR step6 gateway-list: " + $_.Exception.Message)
}

# Per-gateway and external connectivity test.
# MUST use raw `ping` and return FULL output unfiltered: the per-reply error text
# ("General failure", "Request timed out", etc., in any OS language) is the primary
# triage signal. Do NOT replace with Test-Connection: its object output drops the
# localized failure text.
try {
    foreach ($gw in $gateways) {
        Write-Output "=== ping gateway $gw ==="
        & ping -n 4 $gw 2>&1
    }
    Write-Output "=== ping external 223.5.5.5 ==="
    & ping -n 4 223.5.5.5 2>&1
} catch {
    Write-Host ("ERROR step6 connectivity-ping: " + $_.Exception.Message)
}

# --- Step 7: TCP Port Range Check ---

try {
    $ns1 = netsh int ipv4 show dynamicport tcp 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step7 netsh-dynamicport-tcp4: exit=$LASTEXITCODE $(($ns1 | Out-String).Trim())" }
    $ns1
    $ns2 = netsh int ipv6 show dynamicport tcp 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step7 netsh-dynamicport-tcp6: exit=$LASTEXITCODE $(($ns2 | Out-String).Trim())" }
    $ns2
    $ns3 = netsh int ipv4 show excludedportrange tcp 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step7 netsh-excluded-tcp: exit=$LASTEXITCODE $(($ns3 | Out-String).Trim())" }
    $ns3
    $ns4 = netsh int ipv4 show dynamicport udp 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step7 netsh-dynamicport-udp: exit=$LASTEXITCODE $(($ns4 | Out-String).Trim())" }
    $ns4
    $ns5 = netsh int ipv4 show excludedportrange udp 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step7 netsh-excluded-udp: exit=$LASTEXITCODE $(($ns5 | Out-String).Trim())" }
    $ns5
} catch {
    Write-Host ("ERROR step7 netsh-port-range: " + $_.Exception.Message)
}

# --- Step 8: Proxy Configuration Check ---

try {
    $winhttpProxy = netsh winhttp show proxy 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step8 netsh-winhttp-proxy: exit=$LASTEXITCODE $(($winhttpProxy | Out-String).Trim())" }
    $winhttpProxy
} catch {
    Write-Host ("ERROR step8 netsh-winhttp-proxy: " + $_.Exception.Message)
}

function Mask-ProxyUrl($val) {
    if ($val -match '://([^:]+):([^@]+)@') { $val -replace '://([^:]+):([^@]+)@', '://***:***@' } else { $val }
}

try {
    $proxyReg = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    if ($proxyReg) {
        [PSCustomObject]@{
            ProxyEnable   = $proxyReg.ProxyEnable
            ProxyServer   = if ($proxyReg.ProxyServer) { Mask-ProxyUrl $proxyReg.ProxyServer } else { $null }
            ProxyOverride = $proxyReg.ProxyOverride
            AutoConfigURL = if ($proxyReg.AutoConfigURL) { Mask-ProxyUrl $proxyReg.AutoConfigURL } else { $null }
        } | Format-List
    }
} catch {
    Write-Host ("ERROR step8 proxy-registry: " + $_.Exception.Message)
}

Write-Output "HTTP_PROXY=$(Mask-ProxyUrl $env:HTTP_PROXY)"
Write-Output "HTTPS_PROXY=$(Mask-ProxyUrl $env:HTTPS_PROXY)"
Write-Output "NO_PROXY=$(Mask-ProxyUrl $env:NO_PROXY)"

# --- Step 9: MTU and interface config check ---

try {
    Get-NetIPInterface -AddressFamily IPv4 |
        Select-Object InterfaceAlias, InterfaceIndex, NlMtu, Forwarding |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step9 ip-interface-mtu: " + $_.Exception.Message)
}

try {
    Get-NetAdapter | ForEach-Object {
        Get-NetAdapterAdvancedProperty -Name $_.Name |
            Where-Object { $_.DisplayName -match 'RSS|Checksum Offload|Large Send Offload|Receive Segment Coalescing' } |
            Select-Object @{n='Adapter';e={$_.Name}}, DisplayName, DisplayValue
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step9 adapter-advanced-properties: " + $_.Exception.Message)
}

# --- Step 10: Interface counters snapshot (take BEFORE and AFTER issue reproduction, compare deltas) ---

try {
    Get-NetAdapterStatistics |
        Select-Object Name, ReceivedBytes, SentBytes, ReceivedUnicastPackets, SentUnicastPackets,
            ReceivedDiscardedPackets, ReceivedPacketErrors, OutboundDiscardedPackets, OutboundPacketErrors |
        Format-List
} catch {
    Write-Host ("ERROR step10 adapter-statistics: " + $_.Exception.Message)
}

try {
    $nsTcp = netstat -s -p tcp 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step10 netstat-tcp: exit=$LASTEXITCODE $(($nsTcp | Out-String).Trim())" }
    $nsTcp
    $nsUdp = netstat -s -p udp 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step10 netstat-udp: exit=$LASTEXITCODE $(($nsUdp | Out-String).Trim())" }
    $nsUdp
} catch {
    Write-Host ("ERROR step10 netstat: " + $_.Exception.Message)
}
