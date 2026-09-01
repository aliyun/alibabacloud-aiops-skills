$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Windows Update Dependency Service Check ---
try {
    $services = @('wuauserv','BITS','BrokerInfrastructure','CryptSvc','swprv','Schedule','VSS','mpssvc','Winmgmt','TrustedInstaller','w32time')
    Get-Service -Name $services |
      Select-Object Name, DisplayName, Status, StartType |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 wu-services: " + $_.Exception.Message)
}

# --- Step 2: WSUS Configuration Check ---
try {
    # Policy keys absent = WSUS not configured (falls back to public/aliyun WU) - the finding itself
    $wuPolicyPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate'
    if (Test-Path $wuPolicyPath) {
        Get-ItemProperty -Path $wuPolicyPath |
          Select-Object WUServer, WUStatusServer |
          Format-Table -AutoSize
    } else { Write-Output 'WindowsUpdate policy key not found (WSUS not configured)' }
} catch {
    Write-Host ("ERROR step2 wsus-server: " + $_.Exception.Message)
}
try {
    $auPolicyPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU'
    if (Test-Path $auPolicyPath) {
        Get-ItemProperty -Path $auPolicyPath |
          Select-Object UseWUServer, NoAutoUpdate, AUOptions |
          Format-Table -AutoSize
    } else { Write-Output 'WindowsUpdate\AU policy key not found (auto-update policy not configured)' }
} catch {
    Write-Host ("ERROR step2 wsus-au: " + $_.Exception.Message)
}

# --- Step 3: Update Server Reachability Check ---
try {
    $wuPolicyPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate'
    $wu = if (Test-Path $wuPolicyPath) { Get-ItemProperty -Path $wuPolicyPath } else { $null }
    $server = if ($wu -and $wu.WUServer) { $wu.WUServer } else { 'http://update.cloud.aliyuncs.com' }
    Write-Output "WSUS Server: $server"
    $uri = [System.Uri]$server
    # -WarningAction SilentlyContinue only mutes the routine progress warning; the
    # TcpTestSucceeded result (the actual signal) is unaffected.
    Test-NetConnection -ComputerName $uri.Host -Port 80 -WarningAction SilentlyContinue |
      Select-Object ComputerName, RemotePort, TcpTestSucceeded |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 wu-server-reachability: " + $_.Exception.Message)
}

# --- Step 4: Known Problematic Hotfix Check ---
try {
    $problematic = @('KB5009624','KB5009595','KB5009546','KB5009557','KB5009555','KB5014738','KB5014702','KB5014692','KB5014678','KB5060842')
    Get-HotFix | Where-Object { $problematic -contains $_.HotFixID } |
      Select-Object HotFixID, InstalledOn, Description |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 hotfixes: " + $_.Exception.Message)
}

# --- Step 5: WinHTTP Proxy Configuration Check ---
try {
    $netshProxy = netsh winhttp show proxy 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step5 netsh-winhttp-proxy: exit=$LASTEXITCODE $(($netshProxy | Out-String).Trim())" }
    $netshProxy
} catch {
    Write-Host ("ERROR step5 netsh-winhttp-proxy: " + $_.Exception.Message)
}

function Mask-ProxyUrl($val) {
    if ($val -match '://([^:]+):([^@]+)@') { $val -replace '://([^:]+):([^@]+)@', '://***:***@' } else { $val }
}

try {
    $proxyReg = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
    if ($proxyReg) {
      [PSCustomObject]@{
        ProxyEnable   = $proxyReg.ProxyEnable
        ProxyServer   = if ($proxyReg.ProxyServer) { Mask-ProxyUrl $proxyReg.ProxyServer } else { $null }
        ProxyOverride = $proxyReg.ProxyOverride
      } | Format-Table -AutoSize
    }
} catch {
    Write-Host ("ERROR step5 user-proxy: " + $_.Exception.Message)
}

# --- Step 6: update cache and pending operations check ---
try {
    $pending = "$env:SystemRoot\WinSxS\pending.xml"
    [PSCustomObject]@{ Path = $pending; Exists = (Test-Path $pending) } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 pending-xml: " + $_.Exception.Message)
}
try {
    # -ErrorAction Continue: per-item access-denied errors are printed and the scan continues
    @("$env:SystemRoot\SoftwareDistribution\DataStore", "$env:SystemRoot\System32\Catroot2") | ForEach-Object {
      $dir = $_
      $exists = Test-Path $dir
      $size = if ($exists) { (Get-ChildItem $dir -Recurse -Force -ErrorAction Continue | Measure-Object -Property Length -Sum).Sum } else { $null }
      [PSCustomObject]@{ Directory = $dir; Exists = $exists; SizeBytes = $size }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 cache-dirs: " + $_.Exception.Message)
}
try {
    $db = "$env:SystemRoot\SoftwareDistribution\DataStore\DataStore.edb"
    if (Test-Path $db) {
      try { [System.IO.File]::Open($db, 'Open', 'Read', 'None').Close(); Write-Output 'DataStore.edb: readable' }
      catch { Write-Output "DataStore.edb: NOT readable ($($_.Exception.Message))" }
    }
} catch {
    Write-Host ("ERROR step6 datastore-edb: " + $_.Exception.Message)
}

# --- Step 7: update error code and event log analysis ---
try {
    $startTime = (Get-Date).AddDays(-7)
    Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-WindowsUpdateClient'; Id = 19, 20, 1001; StartTime = $startTime } -MaxEvents 50 |
      Select-Object TimeCreated, Id, LevelDisplayName, @{ N = 'MessageHead'; E = { ($_.Message -split "`n")[0] } } |
      Format-List
} catch {
    Write-Host ("ERROR step7 wu-client-events: " + $_.Exception.Message)
}
try {
    $startTime = (Get-Date).AddDays(-7)
    Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Servicing'; Level = 2; StartTime = $startTime } -MaxEvents 20 |
      Select-Object TimeCreated, Id, @{ N = 'MessageHead'; E = { ($_.Message -split "`n")[0] } } |
      Format-List
} catch {
    Write-Host ("ERROR step7 servicing-events: " + $_.Exception.Message)
}

# --- Step 8: disk space and system file integrity ---
try {
    $sysDrive = $env:SystemDrive
    Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$sysDrive'" |
      Select-Object DeviceID, @{ N = 'FreeGB'; E = { [math]::Round($_.FreeSpace / 1GB, 2) } }, @{ N = 'SizeGB'; E = { [math]::Round($_.Size / 1GB, 2) } } |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step8 sysdrive-space: " + $_.Exception.Message)
}
# CBS.log error analysis moved to scripts/system-cbs.ps1 (authority: system-cbs.md)
