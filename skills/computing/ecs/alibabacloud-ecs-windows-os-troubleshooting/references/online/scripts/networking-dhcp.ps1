$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: DHCP Client Service Status Check ---

try {
    Get-Service -Name Dhcp |
        Select-Object Name, Status, StartType |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 dhcp-service: " + $_.Exception.Message)
}

# --- Step 2: Network Adapter DHCP Enable Status Check ---

try {
    Get-NetIPInterface -AddressFamily IPv4 |
        Where-Object { $_.ConnectionState -eq 'Connected' } |
        Select-Object InterfaceAlias, InterfaceIndex, Dhcp, ConnectionState |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 ip-interface: " + $_.Exception.Message)
}

# --- Step 3: DHCP Lease Status Check ---

try {
    Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.InterfaceAlias -notlike 'Loopback*' } |
        Select-Object InterfaceAlias, IPAddress, PrefixLength, AddressState, SuffixOrigin, ValidLifetime |
        Format-List
} catch {
    Write-Host ("ERROR step3 net-ipaddress: " + $_.Exception.Message)
}

try {
    Get-CimInstance -ClassName Win32_NetworkAdapterConfiguration |
        Where-Object { $_.IPEnabled -eq $true } |
        Select-Object Description, DHCPEnabled, DHCPServer, DHCPLeaseObtained, DHCPLeaseExpires, IPAddress, DefaultIPGateway |
        Format-List
} catch {
    Write-Host ("ERROR step3 adapter-config: " + $_.Exception.Message)
}

# --- Step 4: DHCP Client Event Log Check ---

try {
    Get-WinEvent -LogName 'Microsoft-Windows-Dhcp-Client/Admin' -MaxEvents 30 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-List
} catch {
    Write-Host ("ERROR step4 dhcp-eventlog: " + $_.Exception.Message)
}

# --- Step 5: Network Adapter Driver and Link Status Check ---

try {
    Get-NetAdapter |
        Select-Object Name, InterfaceDescription, Status, LinkSpeed, MediaConnectionState, DriverVersion |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 net-adapter: " + $_.Exception.Message)
}

# --- Step 6: DHCP Server Connectivity Check ---

try {
    $dhcpServers = Get-CimInstance -ClassName Win32_NetworkAdapterConfiguration |
        Where-Object { $_.DHCPEnabled -eq $true -and $_.DHCPServer } |
        Select-Object Description, DHCPServer
    $dhcpServers | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 dhcp-server-list: " + $_.Exception.Message)
}

if ($dhcpServers) {
    foreach ($item in $dhcpServers) {
        if ($item.DHCPServer -and $item.DHCPServer -ne '255.255.255.255') {
            try {
                Test-Connection -ComputerName $item.DHCPServer -Count 2 |
                    Select-Object Address, StatusCode, ResponseTime |
                    Format-Table -AutoSize
            } catch {
                Write-Host ("ERROR step6 dhcp-server-ping " + $item.DHCPServer + ": " + $_.Exception.Message)
            }
        }
    }
}

try {
    $ipconfigAll = ipconfig /all 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step6 ipconfig: exit=$LASTEXITCODE $(($ipconfigAll | Out-String).Trim())" }
    $ipconfigAll
} catch {
    Write-Host ("ERROR step6 ipconfig: " + $_.Exception.Message)
}
