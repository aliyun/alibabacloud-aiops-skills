$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: DNS Client Service Status Check ---

try {
    Get-Service -Name Dnscache |
        Select-Object Name, Status, StartType |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 dnscache-service: " + $_.Exception.Message)
}

# --- Step 2: DNS Server Configuration Check ---

try {
    Get-DnsClientServerAddress -AddressFamily IPv4 |
        Where-Object { $_.ServerAddresses -ne $null } |
        Select-Object InterfaceAlias, InterfaceIndex, ServerAddresses |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 dns-server-config: " + $_.Exception.Message)
}

# --- Step 3: DNS Cache Status Check ---

try {
    Get-DnsClientCache |
        Select-Object Name, Type, Status, DataLength, TimeToLive, Section |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 dns-cache: " + $_.Exception.Message)
}

# --- Step 4: Hosts File Check ---

try {
    $hostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"
    Get-Content $hostsPath |
        Where-Object { $_ -notmatch '^\s*#' -and $_ -notmatch '^\s*$' }
} catch {
    Write-Host ("ERROR step4 hosts-content: " + $_.Exception.Message)
}

try {
    Get-Acl $hostsPath |
        Select-Object Owner, Access |
        Format-List
} catch {
    Write-Host ("ERROR step4 hosts-acl: " + $_.Exception.Message)
}

# --- Step 5: Domain Name Resolution Test ---

try {
    Resolve-DnsName -Name www.aliyun.com -Type A |
        Select-Object Name, IPAddress, Type |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 resolve-aliyun: " + $_.Exception.Message)
}
try {
    Resolve-DnsName -Name www.baidu.com -Type A |
        Select-Object Name, IPAddress, Type |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 resolve-baidu: " + $_.Exception.Message)
}

try {
    $nslookupOut = nslookup www.aliyun.com 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step5 nslookup: exit=$LASTEXITCODE $(($nslookupOut | Out-String).Trim())" }
    $nslookupOut
} catch {
    Write-Host ("ERROR step5 nslookup: " + $_.Exception.Message)
}

try {
    Resolve-DnsName -Name www.aliyun.com -Server 100.100.2.136 -Type A |
        Select-Object Name, IPAddress |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 resolve-specified-server: " + $_.Exception.Message)
}

# --- Step 6: DNS Suffix and NRPT Check ---

try {
    Get-DnsClientGlobalSetting |
        Select-Object SuffixSearchList, UseSuffixSearchList |
        Format-List
} catch {
    Write-Host ("ERROR step6 dns-global-setting: " + $_.Exception.Message)
}

try {
    Get-DnsClient |
        Select-Object InterfaceAlias, ConnectionSpecificSuffix, ConnectionSpecificSuffixSearchList |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 dns-client: " + $_.Exception.Message)
}

try {
    Get-DnsClientNrptPolicy |
        Select-Object Namespace, NameServers, DirectAccessServerAddresses |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 nrpt-policy: " + $_.Exception.Message)
}
