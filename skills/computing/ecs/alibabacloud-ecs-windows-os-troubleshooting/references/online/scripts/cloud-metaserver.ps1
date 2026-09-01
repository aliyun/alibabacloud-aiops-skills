$ProgressPreference = 'SilentlyContinue'

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Firewall Blocking Metadata Service Check ---
try {
    Get-NetFirewallRule -Enabled True -Action Block | ForEach-Object {
        $addrFilter = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $_
        if ($addrFilter.RemoteAddress -match '100\.100\.100\.200') {
            [PSCustomObject]@{
                DisplayName    = $_.DisplayName
                Name           = $_.Name
                Direction      = $_.Direction
                Action         = $_.Action
                RemoteAddress  = $addrFilter.RemoteAddress
            }
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 firewall-block-rules: " + $_.Exception.Message)
}

# --- Step 2: Metadata Service Reachability ---
try {
    Test-NetConnection -ComputerName 100.100.100.200 -Port 80 -WarningAction SilentlyContinue | Select-Object ComputerName, RemotePort, TcpTestSucceeded, PingSucceeded | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 metadata-tcp-test: " + $_.Exception.Message)
}
try {
    try {
        $response = Invoke-WebRequest -Uri "http://100.100.100.200/latest/meta-data/instance-id" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        [PSCustomObject]@{
            StatusCode = $response.StatusCode
            InstanceId = $response.Content
        } | Format-List
    } catch {
        [PSCustomObject]@{
            Error = $_.Exception.Message
        } | Format-List
    }
} catch {
    Write-Host ("ERROR step2 metadata-http: " + $_.Exception.Message)
}

# --- Step 3: NTP Server Assignment ---
try {
    $ntpMeta = (Invoke-WebRequest -Uri "http://100.100.100.200/latest/meta-data/ntp-server" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop).Content
    [PSCustomObject]@{ MetadataNtpServer = $ntpMeta } | Format-List
} catch {
    Write-Host "ERROR step3 ntp-metadata: $($_.Exception.Message)"
}
try {
    $ntpConfig = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Parameters"
    [PSCustomObject]@{
        NtpServer = $ntpConfig.NtpServer
        Type      = $ntpConfig.Type
    } | Format-List
} catch {
    Write-Host ("ERROR step3 ntp-registry: " + $_.Exception.Message)
}
try {
    Get-Service W32Time | Select-Object Name, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 w32time-service: " + $_.Exception.Message)
}
try {
    $w32status = w32tm /query /status 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step3 w32tm-status: exit=$LASTEXITCODE $(($w32status | Out-String).Trim())" }
    $w32status
} catch {
    Write-Host ("ERROR step3 w32tm-status: " + $_.Exception.Message)
}
try {
    $w32peers = w32tm /query /peers 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step3 w32tm-peers: exit=$LASTEXITCODE $(($w32peers | Out-String).Trim())" }
    $w32peers
} catch {
    Write-Host ("ERROR step3 w32tm-peers: " + $_.Exception.Message)
}

# --- Step 4: KMS Activation Server Reachability ---
try {
    $kmsMeta = (Invoke-WebRequest -Uri "http://100.100.100.200/latest/meta-data/kms-server" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop).Content
    [PSCustomObject]@{ MetadataKmsServer = $kmsMeta } | Format-List
} catch {
    Write-Host "ERROR step4 kms-metadata: $($_.Exception.Message)"
}
try {
    $kmsReg = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SoftwareProtectionPlatform"
    [PSCustomObject]@{
        KeyManagementServiceName = $kmsReg.KeyManagementServiceName
        KeyManagementServicePort = $kmsReg.KeyManagementServicePort
    } | Format-List
} catch {
    Write-Host ("ERROR step4 kms-registry: " + $_.Exception.Message)
}
try {
    $slmgrOut = cscript //nologo "$env:SystemRoot\system32\slmgr.vbs" /dli 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step4 slmgr-dli: exit=$LASTEXITCODE $(($slmgrOut | Out-String).Trim())" }
    $slmgrOut
} catch {
    Write-Host ("ERROR step4 slmgr-dli: " + $_.Exception.Message)
}
try {
    $kmsHost = if ($kmsReg.KeyManagementServiceName) { $kmsReg.KeyManagementServiceName } else { "kms.cloud.aliyuncs.com" }
    $kmsPort = if ($kmsReg.KeyManagementServicePort) { $kmsReg.KeyManagementServicePort } else { 1688 }
    Test-NetConnection -ComputerName $kmsHost -Port $kmsPort -WarningAction SilentlyContinue | Select-Object ComputerName, RemotePort, TcpTestSucceeded | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 kms-tcp-test: " + $_.Exception.Message)
}

# --- Step 5: WSUS Update Server Reachability ---
try {
    $wsusMeta = (Invoke-WebRequest -Uri "http://100.100.100.200/latest/meta-data/wsus-server" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop).Content
    [PSCustomObject]@{ MetadataWsusServer = $wsusMeta } | Format-List
} catch {
    Write-Host "ERROR step5 wsus-metadata: $($_.Exception.Message)"
}
try {
    $wuPolicy = Get-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate"
    $wuAU = Get-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
    [PSCustomObject]@{
        WUServer       = $wuPolicy.WUServer
        WUStatusServer = $wuPolicy.WUStatusServer
        UseWUServer    = $wuAU.UseWUServer
    } | Format-List
} catch {
    Write-Host ("ERROR step5 wsus-registry: " + $_.Exception.Message)
}
try {
    $wsusUrl = if ($wuPolicy.WUServer) { $wuPolicy.WUServer } else { "http://update.cloud.aliyuncs.com" }
    try {
        $uri = [System.Uri]$wsusUrl
        $port = if ($uri.Port -gt 0 -and $uri.Port -ne 80) { $uri.Port } else { 80 }
        Test-NetConnection -ComputerName $uri.Host -Port $port -WarningAction SilentlyContinue | Select-Object ComputerName, RemotePort, TcpTestSucceeded | Format-Table -AutoSize
    } catch {
        Write-Host "ERROR step5 wsus-url-parse: $($_.Exception.Message)"
    }
} catch {
    Write-Host ("ERROR step5 wsus-tcp-test: " + $_.Exception.Message)
}

# --- Step 6: Hostname Consistency ---
try {
    $osHostname = (Get-CimInstance Win32_OperatingSystem).CSName
} catch {
    Write-Host ("ERROR step6 os-hostname: " + $_.Exception.Message)
}
try {
    $metaHostname = (Invoke-WebRequest -Uri "http://100.100.100.200/latest/meta-data/hostname" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop).Content
} catch {
    $metaHostname = "(Fetch failed: $($_.Exception.Message))"
}
# Normalize to short names (strip FQDN) for comparison
$osShort = if ($osHostname) { ($osHostname -split '\.')[0] } else { '' }
$metaShort = if ($metaHostname -and $metaHostname -notlike '(Fetch failed*') { ($metaHostname -split '\.')[0] } else { $metaHostname }
[PSCustomObject]@{
    SystemHostname   = $osHostname
    MetadataHostname = $metaHostname
    Match            = ($osShort -eq $metaShort)
} | Format-List
